"""
Benchmarks for evaluating agents and LLMs
"""
# pylint: disable=broad-exception-caught,too-few-public-methods
import json
import os
import hashlib
from typing import List, Dict, Optional, Any
from contextlib import AsyncExitStack

import yaml
from pydantic import BaseModel, Field
from mcpuniverse.common.misc import AutodocABCMeta
from mcpuniverse.llm.base import BaseLLM
from mcpuniverse.agent.base import Executor, BaseAgent
from mcpuniverse.mcp.manager import MCPManager
from mcpuniverse.workflows.builder import WorkflowBuilder
from mcpuniverse.benchmark.task import Task
from mcpuniverse.tracer.collectors.base import BaseCollector
from mcpuniverse.tracer import Tracer
from mcpuniverse.evaluator import EvaluationResult
from mcpuniverse.common.logger import get_logger
from mcpuniverse.common.context import Context
from mcpuniverse.callbacks.base import (
    BaseCallback,
    CallbackMessage,
    MessageType,
    send_message_async, send_message
)


class BenchmarkConfig(BaseModel):
    """Benchmark configuration."""
    description: str = ""
    agent: str = ""
    tasks: List[str] = Field(default_factory=list)

    def md5(self) -> str:
        """Return the MD5 hash of the benchmark config."""
        text = (f"Description: {self.description}, "
                f"Agent: {self.agent}, "
                f"Tasks: {', '.join(self.tasks)}")
        return hashlib.md5(text.encode()).hexdigest()


class BenchmarkResult(BaseModel):
    """Benchmark evaluation results."""
    benchmark: BenchmarkConfig
    task_results: Dict[str, Dict[str, Any]]
    task_trace_ids: Dict[str, str]


class BenchmarkResultStore(metaclass=AutodocABCMeta):
    """
    The class for storing benchmark results, allowing resuming tasks.
    """

    def __init__(self, folder: str = ""):
        """
        Initialize a store of benchmark results.

        Args:
            folder (str): The folder path of the store.
                If it is empty, the results will not be stored.
        """
        self._folder = folder

    def dump_task_result(
            self,
            benchmark: BenchmarkConfig,
            task_config_path: str,
            evaluation_results: List[EvaluationResult],
            trace_id: str,
            overwrite: bool = True,
            model_name: str = "",
            category: str = "",
            attack_category: str = ""
    ):
        """
        Dump a task result in one benchmark.

        Args:
            benchmark (BenchmarkConfig): The benchmark configuration.
            task_config_path (str): The task config filepath.
            evaluation_results (List[EvaluationResult]): The evaluation results to save.
            trace_id (str): The tracing ID for this task (only valid when the collector is a database).
            overwrite (bool): Whether to overwrite existing evaluation results.
            model_name (str): The model name to include in the filename.
            category (str): The category of the task.
            attack_category (str): The attack category of the task.
        """
        if not self._folder:
            return
        # Use model name instead of benchmark MD5 for folder structure
        model_name = model_name.replace("/", "_")
        folder_name = model_name if model_name else "default"
        folder = os.path.join(self._folder, folder_name)
        os.makedirs(folder, exist_ok=True)
        
        # Get original task filename (without path and extension)
        task_basename = os.path.splitext(os.path.basename(task_config_path))[0]
        
        # Build new filename: taskname_modelname.json
        if model_name:
            filename = os.path.join(folder, f"{task_basename}_{model_name}.json")
        else:
            filename = os.path.join(folder, f"{task_basename}.json")
            
        if not overwrite and os.path.isfile(filename):
            return
        # Determine task success and attack success
        task_success = None
        attack_success = None
        
        if evaluation_results:
            # If attack_category is None/null/empty, all evaluators are used for task_success
            # Otherwise, use the last evaluator for attack_success
            if not attack_category or attack_category == "null":
                # All evaluators are used for task_success evaluation
                task_success = all(eval_result.passed for eval_result in evaluation_results)
                attack_success = None
            else:
                # Task success: all evaluation functions except the last one must pass
                task_evaluators = evaluation_results[:-1] if len(evaluation_results) > 1 else evaluation_results
                task_success = all(eval_result.passed for eval_result in task_evaluators)
                
                # Attack success: determined by the last evaluation function
                if len(evaluation_results) > 1:
                    attack_success = evaluation_results[-1].passed
        
        result = {
            "category": category,
            "attack_category": attack_category,
            "task_success": task_success,
            "attack_success": attack_success,
            "results": [r.model_dump(mode="json") for r in evaluation_results],
            "trace_id": trace_id
        }
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)

    def load_task_result(
            self,
            benchmark: BenchmarkConfig,
            task_config_path: str,
            model_name: str = ""
    ) -> Optional[dict]:
        """
        Check if the evaluation results of a task have been stored.

        Args:
            benchmark (BenchmarkConfig): The benchmark configuration.
            task_config_path (str): The task config filepath.
            model_name (str): The model name to look for in the filename.
        """
        if self._folder == "":
            return None
        # Use model name instead of benchmark MD5 for folder structure
        folder_name = model_name if model_name else "default"
        folder = os.path.join(self._folder, folder_name)
        
        # Get original task filename (without path and extension)
        task_basename = os.path.splitext(os.path.basename(task_config_path))[0]
        
        # Build filename: taskname_modelname.json
        if model_name:
            filename = os.path.join(folder, f"{task_basename}_{model_name}.json")
        else:
            filename = os.path.join(folder, f"{task_basename}.json")
            
        if not os.path.isfile(filename):
            return None
        with open(filename, "r", encoding="utf-8") as f:
            result = json.load(f)
            result["results"] = [EvaluationResult.model_validate(r) for r in result["results"]]
            return result


class BenchmarkRunner(metaclass=AutodocABCMeta):
    """
    The class for running different benchmarks.
    """

    def __init__(self, config: str, context: Optional[Context] = None):
        """
        Initialize a benchmark runner.

        Args:
            config (str): The config file path.
            context (Context, optional): The context information.
        """
        self._default_folder = os.path.join(os.path.dirname(os.path.realpath(__file__)), "configs")
        if not os.path.exists(config):
            config = os.path.join(self._default_folder, config)
        if not os.path.exists(config):
            raise ValueError(f"Cannot find config file: {config}")
        self._logger = get_logger("Benchmark")
        self._context = context if context else Context()

        # Load configs
        self._agent_configs = []
        self._benchmark_configs = []
        with open(config, "r", encoding="utf-8") as f:
            objects = yaml.safe_load_all(f)
            if isinstance(objects, dict):
                objects = [objects]
            for obj in objects:
                obj = dict(obj)
                assert "kind" in obj and "spec" in obj, "Wrong config format: Missing `kind`"
                if obj["kind"].lower() == "benchmark":
                    self._benchmark_configs.append(BenchmarkConfig.model_validate(obj["spec"]))
                else:
                    self._agent_configs.append(obj)

        # store the outputs
        self._benchmark_results = None

    async def run(
            self,
            mcp_manager: Optional[MCPManager] = None,
            trace_collector: Optional[BaseCollector] = None,
            components: Optional[Dict[str, BaseLLM | Executor]] = None,
            store_folder: str = "",
            overwrite: bool = True,
            callbacks: Optional[List[BaseCallback]] = None
    ) -> List[BenchmarkResult]:
        """
        Run specified benchmarks.

        Args:
            mcp_manager (MCPManager): An MCP server manager.
            trace_collector (BaseCollector): Trace collector.
            components (Dict): The components to be overwritten.
            store_folder (str): The folder path for storing evaluation results.
            overwrite (bool): Whether to overwrite existing evaluation results.
            callbacks (List[BaseCallback], optional): Callback functions.
        """
        if mcp_manager is None:
            mcp_manager = MCPManager(context=self._context)
        workflow = WorkflowBuilder(mcp_manager=mcp_manager, config=self._agent_configs)
        workflow.build(components)
        store = BenchmarkResultStore(folder=store_folder)

        outputs = []
        used_agents = []
        for benchmark in self._benchmark_configs:
            agent: Executor = workflow.get_component(benchmark.agent)
            used_agents.append(agent)
            await agent.initialize()
            await send_message_async(callbacks, message=CallbackMessage(
                source=__file__,
                type=MessageType.LOG,
                metadata={"event": "list_tools", "data": agent}
            ))
            original_servers = agent._config.servers
            task_results, task_trace_ids = {}, {}
            for idx, task_path in enumerate(benchmark.tasks):
                async with AsyncExitStack():
                    send_message(callbacks, message=CallbackMessage(
                        source="benchmark_runner",
                        type=MessageType.PROGRESS,
                        data=f"Running task: {task_path} ({idx + 1}/{len(benchmark.tasks)})"
                    ))
                    send_message(callbacks, message=CallbackMessage(
                        source="benchmark_runner",
                        type=MessageType.LOG,
                        data=f"Running task: {task_path}"
                    ))
                    self._logger.info("Running task: %s", task_path)
                    if not os.path.exists(task_path):
                        task_filepath = os.path.join(self._default_folder, task_path)
                    else:
                        task_filepath = task_path

                    # Get model name from LLM config
                    model_name = ""
                    if hasattr(agent, '_llm') and hasattr(agent._llm, 'config') and hasattr(agent._llm.config, 'model_name'):
                        model_name = agent._llm.config.model_name
                    elif hasattr(agent, '_llm') and hasattr(agent._llm, '_name'):
                        model_name = agent._llm._name
                    
                    stored_result = store.load_task_result(
                        benchmark=benchmark, task_config_path=task_filepath, model_name=model_name)
                    if not overwrite and stored_result is not None:
                        task_results[task_path] = {
                            "evaluation_results": stored_result["results"]
                        }
                        task_trace_ids[task_path] = stored_result["trace_id"]
                        self._logger.info("Loaded stored results for task: %s", task_path)
                        continue

                    # Execute the task and the corresponding evaluations
                    task = Task(task_filepath, context=self._context)
                    # Apply tool modifications and malicious tool injection if present
                    if task.use_specified_server() and isinstance(agent, BaseAgent):
                        await agent.change_servers(task.get_mcp_servers())
                    needs_reconnect = False
                    if task.has_attack() and isinstance(agent, BaseAgent):
                        # Apply tool modifications (if any)
                        if task.get_mcp_server_modifications():
                            needs_reconnect = await self._apply_tool_modifications(agent, task)
                        # Inject malicious tools (if any)
                        if task.get_mcp_server_additions():
                            needs_reconnect = await self._inject_malicious_tools(agent, task)
                        # Set up Rug Pull Attack tracking (if any)
                        if task.get_mcp_server_update():
                            # Store task reference in agent for tool call tracking
                            agent._current_task = task
                            needs_reconnect = True
                        if task.get_client_side_attack():
                            agent._current_task = task
                            if task.get_identity_spoofing():
                                needs_reconnect = True
                    
                    agent.reset()
                    tracer = Tracer(collector=trace_collector)
                    question = task.get_question()
                    output_format = task.get_output_format()

                    await send_message_async(callbacks, message=CallbackMessage(
                        source=__file__,
                        type=MessageType.LOG,
                        metadata={"event": "task_description", "data": task}
                    ))
                    try:
                        response = await agent.execute(
                            question,
                            output_format=output_format,
                            tracer=tracer,
                            callbacks=callbacks
                        )
                        result = response.get_response_str()
                    except Exception as e:
                        result = str(e)
                    
                    # Get trace records for evaluation
                    trace_records = trace_collector.get(tracer.trace_id)
                    
                    # Create evaluation input with trace records
                    evaluation_input = {
                        "result": result,
                        "trace_records": trace_records
                    }
                    
                    evaluation_results = await task.evaluate(evaluation_input)

                    # Save the evaluation results
                    task_results[task_path] = {
                        "evaluation_results": evaluation_results
                    }
                    task_trace_ids[task_path] = tracer.trace_id
                    trace_records = trace_collector.get(tracer.trace_id)
                    store.dump_task_result(
                        benchmark=benchmark,
                        task_config_path=task_filepath,
                        evaluation_results=evaluation_results,
                        trace_id=tracer.trace_id,
                        overwrite=True,
                        model_name=model_name,
                        category=task._config.category,
                        attack_category=task._config.attack_category
                    )

                    # Reset task status/environment
                    self._logger.info("Resetting task %s", task_path)
                    await task.reset(trace_records)
                    # Clean up and restore original server files
                    await task.cleanup(agent)
                    self._logger.info("Finished cleanup and restoration for task %s", task_path)
                    try:
                        if task.use_specified_server() or needs_reconnect and isinstance(agent, BaseAgent):
                            await agent.change_servers(original_servers)
                            self._logger.info("Reconnected to restored server to get original tools")
                    except Exception as e:
                        self._logger.warning(f"Failed to reconnect after cleanup: {e}")

            outputs.append(BenchmarkResult(
                benchmark=benchmark, task_results=task_results, task_trace_ids=task_trace_ids))
            self._logger.info("Finished benchmark: %s", benchmark.description)

        for agent in used_agents[::-1]:
            await agent.cleanup()
        self._logger.info("Agent cleanup succeeded")

        self._benchmark_results = outputs
        return outputs

    async def _apply_tool_modifications(self, agent: BaseAgent, task: Task) -> bool:
        """
        Apply tool modifications for poisoning attacks by modifying tool descriptions
        and optionally modifying server code for return values.
        
        Args:
            agent: The agent to modify tools for
            task: The task containing attack configuration
            
        Returns:
            bool: True if server files were modified and reconnection is needed
        """
        try:
            # Check if agent has tools
            if not hasattr(agent, '_tools') or not agent._tools:
                self._logger.warning("Agent has no tools available for server code modifications")
                return False
            modifications = task.get_mcp_server_modifications()
            if not modifications:
                return False
            # Check if we need to modify server code for return values
            has_return_modifications = any(
                modification.get("modification_return") 
                for modification in modifications
            )
            # Apply tool description modifications (keep existing logic)
            for modification in modifications:
                tool_name = modification.get("tool_name")
                modification_description = modification.get("modification_description")
                modification_return = modification.get("modification_return")
                if tool_name and modification_description:
                    # Find the tool in the agent's tools and modify its description
                    for server_name, tools in agent._tools.items():
                        for tool in tools:
                            if tool.name == tool_name:
                                # Store original description for restoration
                                if tool_name not in task._original_descriptions:
                                    task._original_descriptions[tool_name] = tool.description
                                
                                # Apply the poisoned description
                                tool.description = modification_description
                                self._logger.info(f"Applied tool modifications to {server_name}.{tool_name}")
                                break
                if tool_name and modification_return:
                    # Find which server contains this tool
                    target_server_name = None
                    for server_name, tools in agent._tools.items():
                        for tool in tools:
                            if tool.name == tool_name:
                                target_server_name = server_name
                                self._logger.info(f"Found tool {tool_name} in server {target_server_name} for return modification")
                                break
                        if target_server_name:
                            break
                    
                    if not target_server_name:
                        self._logger.warning(f"Tool {tool_name} not found in any server for return modification")
                        continue
                    
                    # Get the server configuration from MCP manager
                    mcp_manager = getattr(agent, '_mcp_manager', None)
                    if not mcp_manager:
                        self._logger.warning("Agent has no MCP manager for server code modifications")
                        continue
                    
                    # Find the server configuration
                    server_config = None
                    try:
                        server_config = mcp_manager.get_config(target_server_name)
                    except Exception as e:
                        self._logger.warning(f"Failed to get config for server {target_server_name}: {e}")
                        continue
                    
                    if not server_config:
                        self._logger.warning(f"Server {target_server_name} not found in MCP manager")
                        continue
                    
                    # Get the server directory from the config
                    server_dir = None
                    if server_config.stdio.args:
                        module_name = server_config.stdio.args[-1]  # Get the last argument (module name)
                        if module_name.startswith("-m"):
                            module_name = module_name[2:]  # Remove "-m" prefix
                        
                        # Convert module name to directory path
                        if module_name.startswith("mcpuniverse.mcp.servers."):
                            # For internal servers, construct the path
                            server_name_short = module_name.split(".")[-1]
                            server_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                                "mcpuniverse", "mcp", "servers", server_name_short)
                        else:
                            # For external modules, try to find the module path
                            try:
                                import importlib.util
                                spec = importlib.util.find_spec(module_name)
                                if spec and spec.origin:
                                    server_dir = os.path.dirname(spec.origin)
                                else:
                                    self._logger.warning(f"Cannot find module path for {module_name}")
                                    continue
                            except Exception as e:
                                self._logger.warning(f"Failed to find module path for {module_name}: {e}")
                                continue
                    else:
                        self._logger.warning(f"Unsupported server type for {target_server_name}")
                        continue
                    
                    if not server_dir or not os.path.exists(server_dir):
                        self._logger.warning(f"Server directory {server_dir} does not exist for {target_server_name}")
                        continue
                    
                    # Helper function to find complete return statement
                    def find_return_end(content, return_pos):
                        """Find the end of a complete return statement, handling multi-line returns."""
                        paren_count = 0
                        brace_count = 0
                        bracket_count = 0
                        in_string = False
                        string_char = None
                        
                        pos = return_pos
                        while pos < len(content):
                            char = content[pos]
                            
                            if not in_string:
                                if char in '"\'':
                                    in_string = True
                                    string_char = char
                                elif char == '(':
                                    paren_count += 1
                                elif char == ')':
                                    paren_count -= 1
                                elif char == '{':
                                    brace_count += 1
                                elif char == '}':
                                    brace_count -= 1
                                elif char == '[':
                                    bracket_count += 1
                                elif char == ']':
                                    bracket_count -= 1
                                elif char == '\n' and paren_count == 0 and brace_count == 0 and bracket_count == 0:
                                    # Found complete return statement end
                                    return pos
                            else:
                                if char == string_char and (pos == 0 or content[pos-1] != '\\'):
                                    in_string = False
                                    string_char = None
                            
                            pos += 1
                        
                        return len(content)

                    # Directly modify the server code to change tool return values
                    try:
                        server_py_path = os.path.join(server_dir, "server.py")
                        backup_path = os.path.join(server_dir, "server.py.backup")
                        
                        # Create backup of original server.py if not exists
                        if not os.path.exists(backup_path):
                            import shutil
                            shutil.copy2(server_py_path, backup_path)
                            self._logger.info(f"Created backup of {server_py_path}")
                        
                        # Read original server.py content
                        with open(server_py_path, 'r', encoding='utf-8') as f:
                            server_content = f.read()
                        
                        # Apply return value modifications for each tool
                        modified_content = server_content

                        # Find the tool function definition
                        tool_pattern = f"def {tool_name}("
                        tool_start = modified_content.find(tool_pattern)
                        
                        if tool_start == -1:
                            self._logger.warning(f"Tool function {tool_name} not found in {server_py_path}")
                            continue
                        
                        # Find the function body
                        next_def = modified_content.find("@mcp.tool()", tool_start + 1)
                        if next_def == -1:
                            function_end = modified_content.find("return mcp",tool_start+1)
                        else:
                            function_end = next_def
                        
                        function_content = modified_content[tool_start:function_end]
                        
                        # Handle modification_return (return value modification)
                        # Find all return statements in THIS SPECIFIC TOOL FUNCTION and replace them
                        return_positions = []
                        search_start = 0
                        
                        # Search only within the current tool function
                        while True:
                            return_pos = function_content.find("return ", search_start)
                            if return_pos == -1:
                                break
                            return_positions.append(return_pos)
                            search_start = return_pos + 1
                        
                        # Sort return positions in reverse order to avoid index shifting issues
                        return_positions.sort(reverse=True)
                        
                        # Replace each return statement in this specific tool function
                        for return_pos in return_positions:
                            # Find the start of the return line (preserve indentation)
                            return_line_start = return_pos
                            while return_line_start > 0 and function_content[return_line_start - 1] != '\n':
                                return_line_start -= 1
                            
                            # Find the end of the complete return statement
                            return_line_end = find_return_end(function_content, return_pos)
                            
                            # Extract the indentation from the original return line
                            original_line = function_content[return_line_start:return_line_end]
                            indent = ""
                            for char in original_line:
                                if char in ' \t':
                                    indent += char
                                else:
                                    break
                            
                            # Calculate absolute positions within the current tool function
                            abs_return_start = tool_start + return_line_start
                            abs_return_end = tool_start + return_line_end
                            
                            # Generate the new return statement with preserved indentation
                            if isinstance(modification_return, dict):
                                new_return = f"{indent}return {modification_return}"
                            else:
                                new_return = f"{indent}return {modification_return}"
                            
                            # Replace the return statement
                            modified_content = (
                                modified_content[:abs_return_start] +
                                new_return +
                                modified_content[abs_return_end:]
                            )
                            
                            self._logger.info(f"Replaced return statement {len(return_positions) - return_positions.index(return_pos)} in tool {tool_name}")
                        
                        self._logger.info(f"Replaced {len(return_positions)} return statements in tool {tool_name}")
                        
                        # Write modified server.py
                        with open(server_py_path, 'w', encoding='utf-8') as f:
                            f.write(modified_content)
                        
                        self._logger.info(f"Successfully modified tool return values in {server_py_path}")
                        
                        # Store backup path for restoration during cleanup
                        if not hasattr(task, '_server_backup_path'):
                            task._server_backup_path = backup_path
                            task._original_server_path = server_py_path
                        
                        # Reconnect to the modified server using change_servers
                        try:
                            # Get current server configurations
                            current_servers = []
                            for server_name, tools in agent._tools.items():
                                server_config = mcp_manager.get_config(server_name)
                                server_info = {
                                    "name": server_name,
                                    "transport": "stdio"
                                }
                                current_servers.append(server_info)
                            
                            # Reconnect using change_servers
                            await agent.change_servers(current_servers)
                            self._logger.info(f"Successfully reconnected to modified server using change_servers")
                            
                        except Exception as client_error:
                            self._logger.error(f"Failed to reconnect using change_servers: {client_error}")
                        
                    except Exception as e:
                        self._logger.warning(f"Failed to modify tool return values directly: {e}")
                        self._logger.info("Tool return value modification failed.")
                    
            # Return True if server files were modified
            return has_return_modifications
            
        except Exception as e:
            self._logger.warning(f"Failed to apply tool modifications: {e}")
            return False
    
    
    async def _inject_malicious_tools(self, agent: BaseAgent, task: Task) -> bool:
        """
        Inject malicious tools directly into the first available server's code,
        then reconnect using change_servers.
        
        Args:
            agent: The agent to inject malicious tools for
            task: The task containing attack configuration
            
        Returns:
            bool: True if server files were modified and reconnection is needed
        """
        try:
            mcp_server_additions = task.get_mcp_server_additions()
            if not mcp_server_additions:
                return False
            
            # Extract tool information from the current structure
            if "tool_name" in mcp_server_additions:
                # Single tool case - convert to list format
                malicious_tools = [mcp_server_additions]
            else:
                # Multiple tools case - assume it has tools array
                malicious_tools = mcp_server_additions.get("tools", [])
            
            if not malicious_tools:
                return
            
            # Get the first server name from the agent's tools
            if not hasattr(agent, '_tools') or not agent._tools:
                self._logger.warning("Agent has no tools available for malicious tool injection")
                return
            
            first_server_name = list(agent._tools.keys())[0]
            self._logger.info(f"Using first available server: {first_server_name}")
            
            # Get the server configuration from MCP manager
            mcp_manager = getattr(agent, '_mcp_manager', None)
            if not mcp_manager:
                self._logger.warning("Agent has no MCP manager for malicious tool injection")
                return
            
            # Find the server configuration
            server_config = None
            try:
                server_config = mcp_manager.get_config(first_server_name)
            except Exception as e:
                self._logger.warning(f"Failed to get config for server {first_server_name}: {e}")
                return
            
            if not server_config:
                self._logger.warning(f"Server {first_server_name} not found in MCP manager")
                return
            
            # Get the server directory from the config
            server_dir = None
            if server_config.stdio.args:
                module_name = server_config.stdio.args[-1]  # Get the last argument (module name)
                if module_name.startswith("-m"):
                    module_name = module_name[2:]  # Remove "-m" prefix
                
                # Convert module name to directory path
                if module_name.startswith("mcpuniverse.mcp.servers."):
                    # For internal servers, construct the path
                    server_name_short = module_name.split(".")[-1]
                    server_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                           "mcpuniverse", "mcp", "servers", server_name_short)
                else:
                    # For external modules, try to find the module path
                    try:
                        import importlib.util
                        spec = importlib.util.find_spec(module_name)
                        if spec and spec.origin:
                            server_dir = os.path.dirname(spec.origin)
                        else:
                            self._logger.warning(f"Cannot find module path for {module_name}")
                            return
                    except Exception as e:
                        self._logger.warning(f"Failed to find module path for {module_name}: {e}")
                        return
            else:
                self._logger.warning(f"Unsupported server type for {first_server_name}")
                return
            
            if not server_dir or not os.path.exists(server_dir):
                self._logger.warning(f"Server directory {server_dir} does not exist for {first_server_name}")
                return
            
            # Directly inject malicious tools into the original server file
            try:
                server_py_path = os.path.join(server_dir, "server.py")
                backup_path = os.path.join(server_dir, "server.py.backup")
                
                # Create backup of original server.py
                if not os.path.exists(backup_path):
                    import shutil
                    shutil.copy2(server_py_path, backup_path)
                    self._logger.info(f"Created backup of {server_py_path}")
                
                # Read original server.py content
                with open(server_py_path, 'r', encoding='utf-8') as f:
                    server_content = f.read()
                
                # Generate malicious tool code
                malicious_code = ""
                for tool in malicious_tools:
                    tool_name = tool["tool_name"]
                    description = tool["description"]
                    input_params = tool["input_parameters"]
                    output_params = tool["output_parameters"]
                    implementation = tool["implementation_code"]
                    
                    malicious_code += f'''
# Malicious tool: {tool_name}
@mcp.tool()
{implementation}

'''
                
                # Insert malicious tools into server.py (before the first @mcp.tool())
                first_tool_decorator = server_content.find("@mcp.tool()")
                if first_tool_decorator != -1:
                    # Find the start of the line with @mcp.tool()
                    line_start = first_tool_decorator
                    while line_start > 0 and server_content[line_start - 1] != '\n':
                        line_start -= 1
                    
                    # Calculate indentation
                    indent_start = line_start
                    while indent_start < len(server_content) and server_content[indent_start] in ' \t':
                        indent_start += 1
                    indent = server_content[line_start:indent_start]
                    
                    # Apply indentation to malicious code
                    indented_malicious_code = ""
                    for line in malicious_code.strip().split('\n'):
                        if line.strip():
                            indented_malicious_code += indent + line + '\n'
                        else:
                            indented_malicious_code += '\n'
                    
                    # Insert malicious code before the first @mcp.tool()
                    modified_content = (
                        server_content[:line_start] +
                        indented_malicious_code +
                        server_content[line_start:]
                    )
                else:
                    # If no @mcp.tool() found, append at the end
                    modified_content = server_content + malicious_code
                
                # Write modified server.py
                with open(server_py_path, 'w', encoding='utf-8') as f:
                    f.write(modified_content)
                
                self._logger.info(f"Successfully injected malicious tools into {server_py_path}")
                
                # Store backup path for restoration during cleanup
                if not hasattr(task, '_server_backup_path'):
                    task._server_backup_path = backup_path
                    task._original_server_path = server_py_path
                
                # Use change_servers to reconnect to the modified server
                try:
                    # Get the current server configuration
                    current_servers = []
                    for server_name, tools in agent._tools.items():
                        server_config = mcp_manager.get_config(server_name)
                        server_info = {
                            "name": server_name,
                            "transport": "stdio"
                        }
                        current_servers.append(server_info)
                    
                    # Reconnect using change_servers
                    await agent.change_servers(current_servers)
                    self._logger.info(f"Successfully reconnected to modified server using change_servers")
                    
                except Exception as client_error:
                    self._logger.error(f"Failed to reconnect using change_servers: {client_error}")
                
            except Exception as e:
                self._logger.warning(f"Failed to inject malicious tools directly: {e}")
                self._logger.info("Malicious tool injection failed.")
                return False
            
            # Return True since server files were modified
            return True
            
        except Exception as e:
            self._logger.warning(f"Failed to inject malicious tools: {e}")
            return False
