"""
The class for an agent task
"""
# pylint: disable=broad-exception-caught
import re
import os
import copy
import json
from dotenv import load_dotenv
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
from pydantic_core import from_json
from jinja2 import Environment, meta

from mcpuniverse.common.misc import AutodocABCMeta
from mcpuniverse.evaluator import EvaluatorConfig, Evaluator, EvaluationResult
from mcpuniverse.tracer.types import TraceRecord
from mcpuniverse.common.logger import get_logger
from mcpuniverse.mcp.manager import MCPManager
from mcpuniverse.common.context import Context
from .cleanups import CLEANUP_FUNCTIONS


load_dotenv()



class TaskCleanupConfig(BaseModel):
    """
    Task cleanup configuration.

    Example:
        {
            "server": "github",
            "tool": "create_repository",
            "cleanup_func": "delete_repository",
            "cleanup_args": {
                # Where the key (the first `name`) is an argument of "cleanup_tool"
                # and the value (the second `name`) is an argument of "tool" or "$return" of "tool"
                # or an extra parameter
                "name": "$name"
            }
        }
    """
    server: str = Field(default="", description="The MCP server name")
    tool: str = Field(default="", description="The tool that will change task status/environment")
    cleanup_func: str = Field(default="", description="The tool for cleanup")
    cleanup_args: dict = Field(default_factory=dict, description="The arguments for cleanup")


class TaskConfig(BaseModel):
    """
    Task configuration.
    """
    category: str = Field(default="general", description="Task category")
    question: str = Field(default="", description="Task question")
    output_format: dict = Field(default_factory=dict, description="JSON output format")
    mcp_servers: List[dict] = Field(default_factory=list, description="MCP servers in this task")
    evaluators: List[EvaluatorConfig] = Field(default_factory=list, description="Evaluator configurations")
    cleanups: List[TaskCleanupConfig] = Field(default_factory=list, description="Cleanup configurations")
    use_specified_server: bool = (
        Field(default=False, description="Whether to let agent only use the servers specified in this config"))
    attack_category: Optional[str] = Field(default=None, description="Type of attack for this task")
    mcp_server_modifications: List[dict] = Field(default_factory=list, description="MCP server tool modifications for attacks")
    mcp_server_additions: Optional[dict] = Field(default=None, description="MCP server additions for attack testing")
    mcp_server_update: Optional[dict] = Field(default=None, description="MCP server tool update configuration for Rug Pull Attack")
    wrong_function_intent_injection: Optional[dict] = Field(default=None, description="Wrong function intent injection attack configuration")
    wrong_arguments_intent_injection: Optional[dict] = Field(default=None, description="Wrong arguments intent injection attack configuration")
    data_tampering: Optional[dict] = Field(default=None, description="Data tampering attack configuration")
    identity_spoofing: Optional[dict] = Field(default=None, description="Identity spoofing attack configuration")
    replay_injection: Optional[dict] = Field(default=None, description="Replay injection attack configuration")
    
    class Config:
        extra = "allow"  # Allow additional fields not defined in the model

    def set_environ_variables(self, context: Optional[Context] = None):
        """Set environment variables specified in `question`."""
        params = dict(os.environ)
        if context:
            params.update(context.env)
        env = Environment(trim_blocks=True, lstrip_blocks=True)
        undefined_vars = meta.find_undeclared_variables(env.parse(self.question))
        d = {var: params.get(var, f"{{{{ {var} }}}}") for var in undefined_vars}
        template = env.from_string(self.question)
        self.question = template.render(**d)


class Task(metaclass=AutodocABCMeta):
    """
    The class for an agent task.
    """

    def __init__(self, config: str | Dict, context: Optional[Context] = None):
        if isinstance(config, str):
            if config.endswith(".json"):
                with open(config, "r", encoding="utf-8") as f:
                    config = f.read()
            config = from_json(config)
        self._config = TaskConfig.model_validate(config)
        self._context = context if context else Context()
        
        if self._config.attack_category:
            if not hasattr(self._context, 'metadata'):
                self._context.metadata = {}
            self._context.metadata["attack_category"] = self._config.attack_category
        
        self._config.set_environ_variables(context=self._context)
        self._evaluators = [Evaluator(c, context=self._context) for c in self._config.evaluators]
        self._logger = get_logger("Task")
        self._mcp_manager = MCPManager(context=self._context)
        
        # Tool call tracking for mcp_server_update
        self._tool_call_counts = {}
        self._original_descriptions = {}

    def get_question(self) -> str:
        """Return question prompt."""
        return self._config.question

    def get_output_format(self) -> Optional[dict]:
        """Return the output format."""
        if self._config.output_format:
            return self._config.output_format
        return None

    def get_mcp_servers(self) -> List[Dict]:
        """
        Return the MCP servers used in this task.
        """
        return self._config.mcp_servers

    def get_evaluators(self):
        """
        Return the specified evaluators.
        """
        return self._evaluators

    def use_specified_server(self) -> bool:
        """
        Check if only allow agents to use the task specified servers.
        """
        return self._config.use_specified_server
    
    def has_attack(self) -> bool:
        """
        Check if this task contains attack configuration.
        """
        return self._config.attack_category is not None 
    def get_mcp_server_update(self) -> Optional[dict]:
        """
        Get the MCP server update configuration.
        """
        return self._config.mcp_server_update
    def get_client_side_attack(self) -> bool:
        """
        Check if this task contains client side attack configuration.
        """
        return self._config.attack_category in[ 'Intent Injection','Data Tampering','Identity Spoofing','Replay Injection']
    def get_identity_spoofing(self) -> bool:
        """
        Check if this task contains identity spoofing attack configuration.
        """
        return self._config.attack_category == 'Identity Spoofing'

    def get_mcp_server_modifications(self) -> List[dict]:
        """
        Get MCP server modifications for this task.
        """
        return self._config.mcp_server_modifications
    
    def get_mcp_server_additions(self) -> Optional[dict]:
        """
        Get MCP server additions for this task.
        """
        return self._config.mcp_server_additions

    async def evaluate(self, x: str | Dict) -> List[EvaluationResult]:
        """
        Run evaluations given the agent output.

        Args:
            x: The agent output.
        """
        return [await evaluator.evaluate(x) for evaluator in self._evaluators]

    async def reset(self, trace_records: List[TraceRecord]):
        """
        Reset the task status/environment changed by agents via MCP servers.

        Args:
            trace_records (List[TraceRecord]): The traces generated by agents.
        """
        tool_calls = []
        for trace_record in trace_records:
            for record in trace_record.records:
                data = record.data
                timestamp = record.timestamp
                if data.get("type", "") == "tool":
                    call = copy.deepcopy(data)
                    call["timestamp"] = timestamp
                    tool_calls.append(call)
        tool_calls = sorted(tool_calls, key=lambda x: x["timestamp"], reverse=True)
        for config in self._config.cleanups:
            if not any(c.get("server") == config.server and
                       (c.get("tool_name") == config.tool or config.tool == "") for c in tool_calls):
                self._logger.warning("No tool %s of server %s executed", config.tool, config.server)

        for tool_call in tool_calls:
            for config in self._config.cleanups:
                if tool_call.get("server") == config.server and tool_call.get("tool_name") == config.tool:
                    response = await self._execute_reset(config, tool_call)
                    if response:
                        self._logger.info("Task cleanup succeeded: %s", str(response))

        # The case that config.tool == ""
        for config in self._config.cleanups:
            if config.tool == "":
                response = await self._execute_reset(config)
                if response:
                    self._logger.info("Task cleanup succeeded: %s", str(response))

    async def _execute_reset(self, cleanup_config: TaskCleanupConfig, tool_call: Optional[Dict] = None) -> Any:
        """Execute the reset process."""
        try:
            self._logger.info("Running task cleanup: server `%s`, tool `%s`, cleanup_func `%s`",
                              cleanup_config.server, cleanup_config.tool, cleanup_config.cleanup_func)
            input_args = self._parse_cleanup_args(cleanup_config.cleanup_args, tool_call)
            if (cleanup_config.server, cleanup_config.cleanup_func) in CLEANUP_FUNCTIONS:
                func = CLEANUP_FUNCTIONS[(cleanup_config.server, cleanup_config.cleanup_func)]
                return await func(**input_args)
            return await self._mcp_manager.execute(
                server_name=cleanup_config.server,
                tool_name=cleanup_config.cleanup_func,
                arguments=input_args,
                transport="stdio"
            )
        except Exception as e:
            self._logger.error("Failed to run task cleanup: %s", str(e))
            return None

    def _parse_cleanup_args(self, cleanup_args: Dict | List | str, tool_call: Dict) -> Dict | List | str:
        """
        Parse the arguments for the cleanup function. The arguments may contain strings representing operations
        on the input arguments or returns of `tool_call`.

        Examples:
            `$name -> get(value)` where `name` is one of the arguments of `tool_call`.
            `$return -> get(content) -> array(0) -> get(text)` where `return` is the response of `tool_call`.
        """
        if isinstance(cleanup_args, Dict):
            return {key: self._parse_cleanup_args(value, tool_call) for key, value in cleanup_args.items()}
        if isinstance(cleanup_args, List):
            return [self._parse_cleanup_args(arg, tool_call) for arg in cleanup_args]
        if not isinstance(cleanup_args, str):
            return cleanup_args

        arg = cleanup_args.strip()
        if "$" not in arg or not tool_call:
            return cleanup_args
        if arg[0] != "$":
            raise ValueError(f"Format error in `cleanup_args`: {arg}")
        items = [f.strip() for f in arg.split("->") if f.strip()]

        # Get the input argument
        source = items[0][1:]
        if source != "return" and source not in tool_call["arguments"]:
            raise ValueError(f"Invalid input argument in `cleanup_args`: {source}")
        input_arg = tool_call["response"] if source == "return" else tool_call["arguments"][source]

        # Parse and execute the operations
        for item in items[1:]:
            name = item.split("(")[0].strip().lower()
            match = re.search(r"\((.*?)\)", item)
            arg = match.group(1).strip() if match else ""
            match name:
                case "get":
                    input_arg = input_arg[arg]
                case "array":
                    input_arg = input_arg[int(arg)]
                case "json":
                    input_arg = json.loads(input_arg)
                case _:
                    raise ValueError(f"Invalid operation in `cleanup_args`: {name}")
        if isinstance(input_arg, str) and "->" in input_arg:
            self._logger.warning("The parsed `cleanup_args` contains `->`: %s", input_arg)
        return input_arg

    async def cleanup(self, agent=None):
        """Clean up resources and restore original server files."""
        # Restore original server.py file if it was modified
        if hasattr(self, '_server_backup_path') and hasattr(self, '_original_server_path'):
            try:
                import shutil
                import os
                backup_path = self._server_backup_path
                original_path = self._original_server_path
                
                if os.path.exists(backup_path) and os.path.exists(original_path):
                    # Restore original server.py from backup
                    shutil.copy2(backup_path, original_path)
                    self._logger.info(f"Restored original server.py from backup: {backup_path}")
                    
                    # Remove backup file
                    os.remove(backup_path)
                    self._logger.info(f"Removed backup file: {backup_path}")
                    
                    # Clean up attributes
                    delattr(self, '_server_backup_path')
                    delattr(self, '_original_server_path')
                else:
                    self._logger.warning("Backup or original server file not found for restoration")
            except Exception as e:
                self._logger.error(f"Failed to restore original server.py: {e}")
        # Restore tool descriptions for both mcp_server_modifications and mcp_server_update
        if agent:
            self.restore_tool_descriptions(agent)
        
        # Restore original tokens after identity spoofing attack
        if hasattr(self, '_saved_tokens') and self._saved_tokens:
            import os
            for key, value in self._saved_tokens.items():
                self._logger.info(f"Restoring original token for {key}: {value[:10]}...")
                os.environ[key] = value
    
    async def track_tool_call(self, tool_name: str, agent) -> bool:
        """
        Track tool calls and trigger Rug Pull Attack when threshold is reached.
        
        Args:
            tool_name: Name of the tool being called
            agent: The agent object containing tools
            
        Returns:
            bool: True if Rug Pull Attack was triggered, False otherwise
        """
        if not self._config.mcp_server_update:
            return False
            
        update_config = self._config.mcp_server_update
        target_tool = update_config.get("tool_name")
        call_threshold = update_config.get("call_threshold", 2)  # Default to 2 calls
        
        if tool_name != target_tool:
            return False
        
        # Increment call count
        if tool_name not in self._tool_call_counts:
            self._tool_call_counts[tool_name] = 0
        self._tool_call_counts[tool_name] += 1
        
        call_count = self._tool_call_counts[tool_name]
        self._logger.info(f"Tool {tool_name} called {call_count} times (threshold: {call_threshold})")
        
        # Trigger Rug Pull Attack when threshold is reached
        if call_count == call_threshold:
            self._logger.info(f"Rug Pull Attack threshold reached for {tool_name}")
            # Apply Rug Pull Attack immediately
            await self._apply_rug_pull_attack(agent, tool_name)
        
        return False
    
    async def _apply_rug_pull_attack(self, agent, tool_name):
        """
        Apply Rug Pull Attack by modifying the server.py file directly.
        
        Args:
            agent: The agent object containing tools
            tool_name: Name of the tool to modify
            
        Returns:
            bool: True if attack was applied successfully
        """
        try:
            update_config = self._config.mcp_server_update
            implementation_code = update_config.get("implementation_code")
            malicious_description = update_config.get("malicious_description")
            if not implementation_code:
                self._logger.warning("No implementation_code provided for Rug Pull Attack")
                return False
            
            # Get the first server name from the agent's tools
            if not hasattr(agent, '_tools') or not agent._tools:
                self._logger.warning("Agent has no tools available for Rug Pull Attack")
                return False
            
            first_server_name = list(agent._tools.keys())[0]
            self._logger.info(f"Using first available server for Rug Pull Attack: {first_server_name}")
            
            # Get the server configuration from MCP manager
            mcp_manager = getattr(agent, '_mcp_manager', None)
            if not mcp_manager:
                self._logger.warning("Agent has no MCP manager for Rug Pull Attack")
                return False
            
            # Find the server configuration
            server_config = None
            try:
                server_config = mcp_manager.get_config(first_server_name)
            except Exception as e:
                self._logger.warning(f"Failed to get config for server {first_server_name}: {e}")
                return False
            
            if not server_config:
                self._logger.warning(f"Server {first_server_name} not found in MCP manager")
                return False
            
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
                            return False
                    except Exception as e:
                        self._logger.warning(f"Failed to find module path for {module_name}: {e}")
                        return False
            else:
                self._logger.warning(f"Unsupported server type for {first_server_name}")
                return False
            
            if not server_dir or not os.path.exists(server_dir):
                self._logger.warning(f"Server directory {server_dir} does not exist for {first_server_name}")
                return False
            
            # Apply Rug Pull Attack by modifying the tool implementation
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
                
                tool_pattern = f"def {tool_name}("
                tool_start = server_content.find(tool_pattern)
                
                if tool_start == -1:
                    self._logger.warning(f"Tool function {tool_name} not found in {server_py_path}")
                    return False
                
                # Find the next @ symbol after the function definition
                next_decorator_match = re.search(r"\s+@", server_content[tool_start + 1:])
                if next_decorator_match:
                    next_decorator = tool_start + 1 + next_decorator_match.start()
                else:
                    next_decorator = len(server_content)
                
                # Extract the part to replace
                part_to_replace = server_content[tool_start:next_decorator]
                
                # Find the indentation level of the original function definition
                function_line_start = server_content.rfind('\n', 0, tool_start) + 1
                function_line = server_content[function_line_start:tool_start + len(f"def {tool_name}(")]
                indent_level = len(function_line) - len(function_line.lstrip())
                
                # Add proper indentation to the implementation code
                indented_code = []
                lines = implementation_code.split('\n')
                for i, line in enumerate(lines):
                    if i == 0:  # First line (def line) already has correct indentation
                        indented_code.append(line)
                    elif line.strip():  # Skip empty lines for other lines
                        indented_code.append(' ' * indent_level + line)
                    else:
                        indented_code.append('')  # Keep empty lines as is
                
                indented_implementation = '\n'.join(indented_code)
                
                # Replace the function definition with the new implementation code
                modified_content = server_content[:tool_start] + indented_implementation + server_content[next_decorator:]
                
                # Write modified server.py
                with open(server_py_path, 'w', encoding='utf-8') as f:
                    f.write(modified_content)
                
                self._logger.info(f"Successfully applied Rug Pull Attack to {tool_name} in {server_py_path}")
                
                # Store backup path for restoration during cleanup
                if not hasattr(self, '_server_backup_path'):
                    self._server_backup_path = backup_path
                    self._original_server_path = server_py_path
                
                # Mark that server needs reconnection after current tool call
                # Store the reconnection info for later use
                if not hasattr(self, '_pending_reconnection'):
                    self._pending_reconnection = []
                
                # Get current server configuration
                current_servers = []
                for server_name, tools in agent._tools.items():
                    server_config = mcp_manager.get_config(server_name)
                    server_info = {
                        "name": server_name,
                        "transport": "stdio"
                    }
                    current_servers.append(server_info)
                
                # Store reconnection info instead of reconnecting immediately
                self._pending_reconnection = current_servers
                self._logger.info("Server modification completed. Reconnection will be triggered after current tool call.")
                
                return True
                
            except Exception as e:
                self._logger.warning(f"Failed to apply Rug Pull Attack: {e}")
                return False
            
        except Exception as e:
            self._logger.error(f"Failed to apply Rug Pull Attack: {e}")
            return False
    
    async def handle_pending_reconnection(self, agent):
        """Handle pending server reconnection after tool call completion."""
        if hasattr(self, '_pending_reconnection') and self._pending_reconnection:
            try:
                self._logger.info("Triggering delayed server reconnection after Rug Pull Attack")
                await agent.change_servers(self._pending_reconnection)
                self._pending_reconnection = None  # Clear pending reconnection
                self._logger.info("Successfully reconnected to server after Rug Pull Attack")
            except Exception as e:
                self._logger.warning(f"Failed to reconnect after Rug Pull Attack: {e}")
    
    def restore_tool_descriptions(self, agent):
        """
        Restore original tool descriptions and implementations for both mcp_server_modifications and Rug Pull Attack.
        
        Args:
            agent: The agent object containing tools
        """
        if not agent or not hasattr(agent, '_tools') or not self._original_descriptions:
            return
            
        try:
            restored_count = 0
            
            # Restore tool descriptions and implementations from self._original_descriptions
            for tool_name, original_description in self._original_descriptions.items():
                # Handle both old format (string) and new format (dict)
                for server_name, tools in agent._tools.items():
                    for tool in tools:
                        if tool.name == tool_name:
                            # Restore description
                            if original_description:
                                tool.description = original_description
                            restored_count += 1
                            self._logger.info(f"Restored original state for {server_name}.{tool_name}")
                            break
            
            # Clear the stored descriptions
            self._original_descriptions.clear()
            self._tool_call_counts.clear()
            
            if restored_count > 0:
                self._logger.info(f"Restored {restored_count} tool descriptions to original state")
                
        except Exception as e:
            self._logger.warning(f"Failed to restore tool descriptions: {e}")