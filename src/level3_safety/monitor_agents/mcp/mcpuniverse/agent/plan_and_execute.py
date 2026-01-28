"""
A Plan-and-Execute agent implementation.

This module contains the PlanAndExecute agent class, which implements a two-phase
approach: first planning the steps needed to solve a task, then executing those steps.
"""
# pylint: disable=broad-exception-caught
import os
import json
from typing import Optional, Union, Dict, List
from collections import OrderedDict
from dataclasses import dataclass
from mcp.types import TextContent

from mcpuniverse.mcp.manager import MCPManager
from mcpuniverse.llm.base import BaseLLM
from mcpuniverse.common.logger import get_logger
from mcpuniverse.tracer import Tracer
from mcpuniverse.callbacks.base import (
    send_message,
    send_message_async,
    CallbackMessage,
    MessageType
)
from .base import BaseAgentConfig, BaseAgent
from .utils import build_system_prompt
from .types import AgentResponse

DEFAULT_CONFIG_FOLDER = os.path.join(os.path.dirname(os.path.realpath(__file__)), "configs")


@dataclass
class PlanAndExecuteConfig(BaseAgentConfig):
    """
    Configuration class for Plan-and-Execute agents.

    Attributes:
        system_prompt (str): The system prompt template file or string.
        plan_prompt (str): The prompt template for planning phase.
        execute_prompt (str): The prompt template for execution phase.
        max_plan_steps (int): Maximum number of steps in the plan.
        max_execution_iterations (int): Maximum number of iterations for executing each step.
        summarize_tool_response (bool): Whether to summarize tool responses using the LLM.
    """
    system_prompt: str = os.path.join(DEFAULT_CONFIG_FOLDER, "system_prompt.j2")
    plan_prompt: str = os.path.join(DEFAULT_CONFIG_FOLDER, "plan_prompt.j2")
    execute_prompt: str = os.path.join(DEFAULT_CONFIG_FOLDER, "execute_prompt.j2")
    max_plan_steps: int = 10
    max_execution_iterations: int = 5
    summarize_tool_response: bool = False


class PlanAndExecute(BaseAgent):
    """
    Plan-and-Execute agent implementation.

    This agent works in two phases:
    1. Planning phase: Generates a detailed step-by-step plan to solve the task
    2. Execution phase: Executes each step of the plan sequentially

    Attributes:
        config_class (Type[PlanAndExecuteConfig]): The configuration class for this agent.
        alias (List[str]): Alternative names for this agent type.
    """
    config_class = PlanAndExecuteConfig
    alias = ["plan-and-execute", "plan_and_execute", "plan-and-exec"]

    def __init__(
            self,
            mcp_manager: MCPManager,
            llm: BaseLLM,
            config: Optional[Union[Dict, str]] = None
    ):
        """
        Initialize a Plan-and-Execute agent.

        Args:
            mcp_manager (MCPManager): An MCP server manager for handling tool interactions.
            llm (BaseLLM): A language model for generating responses.
            config (Optional[Union[Dict, str]]): Agent configuration as a dictionary or file path.
        """
        super().__init__(mcp_manager=mcp_manager, llm=llm, config=config)
        self._logger = get_logger(f"{self.__class__.__name__}:{self._name}")
        self._plan: List[Dict[str, str]] = []
        self._execution_history: List[str] = []

    def _build_plan_prompt(self, question: str) -> str:
        """
        Build the prompt for the planning phase.

        Args:
            question (str): The user's question or task.

        Returns:
            str: The constructed planning prompt.
        """
        params = {
            "QUESTION": question,
            "MAX_PLAN_STEPS": self._config.max_plan_steps
        }
        params.update(self._config.template_vars)
        prompt = build_system_prompt(
            system_prompt_template=self._config.plan_prompt,
            tool_prompt_template=self._config.tools_prompt,
            safety_prompt_template=self._config.safety_prompt,
            enable_safety_prompt=self._config.enable_safety_prompt,
            tools=self._tools,
            **params
        )
        # Merge instruction directly into prompt after the first line
        if self._config.instruction:
            instruction_text = f"\n{self._config.instruction}\n"
            # Insert instruction after the first line (usually the role description)
            lines = prompt.split('\n', 1)
            if len(lines) > 1:
                prompt = lines[0] + instruction_text + lines[1]
            else:
                prompt = lines[0] + instruction_text
        return prompt

    def _build_execute_prompt(self, question: str, step: Dict[str, str], step_index: int) -> str:
        """
        Build the prompt for the execution phase.

        Args:
            question (str): The original user question.
            step (Dict[str, str]): The current step to execute.
            step_index (int): The index of the current step.

        Returns:
            str: The constructed execution prompt.
        """
        params = {
            "QUESTION": question,
            "STEP_INDEX": step_index + 1,
            "TOTAL_STEPS": len(self._plan),
            "STEP_DESCRIPTION": step.get("description", ""),
            "STEP_GOAL": step.get("goal", ""),
            "MAX_ITERATIONS": self._config.max_execution_iterations
        }
        if self._execution_history:
            params["EXECUTION_HISTORY"] = "\n\n".join(self._execution_history)
        params.update(self._config.template_vars)
        prompt = build_system_prompt(
            system_prompt_template=self._config.execute_prompt,
            tool_prompt_template=self._config.tools_prompt,
            safety_prompt_template=self._config.safety_prompt,
            enable_safety_prompt=self._config.enable_safety_prompt,
            tools=self._tools,
            **params
        )
        # Merge instruction directly into prompt after the first line
        if self._config.instruction:
            instruction_text = f"\n{self._config.instruction}\n"
            # Insert instruction after the first line (usually the role description)
            lines = prompt.split('\n', 1)
            if len(lines) > 1:
                prompt = lines[0] + instruction_text + lines[1]
            else:
                prompt = lines[0] + instruction_text
        return prompt

    async def _generate_plan(self, question: str, tracer: Tracer, callbacks: List) -> List[Dict[str, str]]:
        """
        Generate a plan to solve the task.

        Args:
            question (str): The user's question or task.
            tracer (Tracer): Tracer for tracking execution.
            callbacks (List): Callbacks for logging.

        Returns:
            List[Dict[str, str]]: A list of plan steps, each containing 'step', 'description', and 'goal'.
        """
        prompt = self._build_plan_prompt(question)
        
        # Add planning-specific instructions
        planning_instructions = f"""

Please analyze the following question and create a detailed step-by-step plan to solve it.

Question: {question}

You need to create a plan with at most {self._config.max_plan_steps} steps. Each step should be clear and actionable.

Respond in the following JSON format:
{{
    "plan": [
        {{
            "step": 1,
            "description": "Brief description of what this step does",
            "goal": "The specific goal or outcome of this step"
        }},
        {{
            "step": 2,
            "description": "Brief description of what this step does",
            "goal": "The specific goal or outcome of this step"
        }}
    ]
}}

The plan should be logical, sequential, and cover all aspects needed to answer the question.
"""
        
        full_prompt = prompt + planning_instructions
        
        send_message(callbacks, message=CallbackMessage(
            source=self.id,
            type=MessageType.LOG,
            data={"phase": "planning", "message": "Generating execution plan..."},
            project_id=self._project_id
        ))

        response = await self._llm.generate_async(
            messages=[{"role": "user", "content": full_prompt}],
            tracer=tracer,
            callbacks=callbacks
        )

        try:
            response = response.strip().strip('`').strip()
            if response.startswith("json"):
                response = response[4:].strip()
            
            parsed_response = json.loads(response)
            if "plan" not in parsed_response or not isinstance(parsed_response["plan"], list):
                raise ValueError("Invalid plan format: missing 'plan' field or not a list")
            
            plan = parsed_response["plan"]
            if not plan:
                raise ValueError("Plan is empty")
            
            # Validate and normalize plan steps
            normalized_plan = []
            for i, step in enumerate(plan):
                if not isinstance(step, dict):
                    continue
                normalized_step = {
                    "step": step.get("step", i + 1),
                    "description": step.get("description", ""),
                    "goal": step.get("goal", "")
                }
                normalized_plan.append(normalized_step)
            
            return normalized_plan

        except json.JSONDecodeError as e:
            self._logger.error("Failed to parse plan response: %s", str(e))
            send_message(callbacks, message=CallbackMessage(
                source=self.id,
                type=MessageType.LOG,
                data={
                    "phase": "planning",
                    "error": f"Failed to parse plan: {str(e)}"
                },
                project_id=self._project_id
            ))
            # Return a simple default plan
            return [{
                "step": 1,
                "description": "Execute the task",
                "goal": "Complete the user's request"
            }]
        except Exception as e:
            self._logger.error("Failed to generate plan: %s", str(e))
            send_message(callbacks, message=CallbackMessage(
                source=self.id,
                type=MessageType.LOG,
                data={
                    "phase": "planning",
                    "error": f"Failed to generate plan: {str(e)}"
                },
                project_id=self._project_id
            ))
            # Return a simple default plan
            return [{
                "step": 1,
                "description": "Execute the task",
                "goal": "Complete the user's request"
            }]

    async def _execute_step(
            self,
            question: str,
            step: Dict[str, str],
            step_index: int,
            tracer: Tracer,
            callbacks: List
    ) -> str:
        """
        Execute a single step from the plan.

        Args:
            question (str): The original user question.
            step (Dict[str, str]): The step to execute.
            step_index (int): The index of the step.
            tracer (Tracer): Tracer for tracking execution.
            callbacks (List): Callbacks for logging.

        Returns:
            str: The result of executing this step.
        """
        prompt = self._build_execute_prompt(question, step, step_index)
        
        for iter_num in range(self._config.max_execution_iterations):
            response = await self._llm.generate_async(
                messages=[{"role": "user", "content": prompt}],
                tracer=tracer,
                callbacks=callbacks
            )

            try:
                response = response.strip().strip('`').strip()
                if response.startswith("json"):
                    response = response[4:].strip()
                
                if not response:
                    raise ValueError("Empty response from LLM")
                
                parsed_response = json.loads(response)
                
                if "answer" in parsed_response:
                    # Step completed with an answer
                    result = parsed_response["answer"]
                    self._execution_history.append(
                        f"Step {step_index + 1}: {step.get('description', '')}\n"
                        f"Result: {result}"
                    )
                    await self._send_callback_message(
                        callbacks=callbacks,
                        step_index=step_index,
                        step=step,
                        result=result,
                        completed=True
                    )
                    return result
                
                if "action" in parsed_response:
                    # Execute tool action
                    action = parsed_response["action"]
                    if not isinstance(action, dict) or "server" not in action or "tool" not in action:
                        error_msg = "Invalid action format"
                        self._execution_history.append(
                            f"Step {step_index + 1}: {step.get('description', '')}\n"
                            f"Error: {error_msg}"
                        )
                        await self._send_callback_message(
                            callbacks=callbacks,
                            step_index=step_index,
                            step=step,
                            action=action,
                            result=error_msg,
                            completed=False
                        )
                        continue
                    
                    try:
                        tool_result = await self.call_tool(action, tracer=tracer, callbacks=callbacks)
                        tool_content = tool_result.content[0]
                        
                        if not isinstance(tool_content, TextContent):
                            raise ValueError("Tool output is not text")
                        
                        tool_summary = None
                        if self._config.summarize_tool_response:
                            context = json.dumps(action, indent=2)
                            tool_summary = await self.summarize_tool_response(
                                tool_content.text,
                                context=context,
                                tracer=tracer
                            )
                            result = tool_summary
                        else:
                            result = tool_content.text
                        
                        self._execution_history.append(
                            f"Step {step_index + 1}: {step.get('description', '')}\n"
                            f"Action: {action.get('tool', '')} on {action.get('server', '')}\n"
                            f"Result: {result[:500]}"
                        )
                        
                        # Update prompt with the result for next iteration
                        prompt = self._build_execute_prompt(question, step, step_index)
                        prompt += f"\n\nPrevious action result: {result}"
                        
                        await self._send_callback_message(
                            callbacks=callbacks,
                            step_index=step_index,
                            step=step,
                            action=action,
                            result=result,
                            completed=False
                        )
                        
                    except Exception as e:
                        error_msg = f"Tool execution failed: {str(e)}"
                        self._logger.error(error_msg)
                        self._execution_history.append(
                            f"Step {step_index + 1}: {step.get('description', '')}\n"
                            f"Error: {error_msg}"
                        )
                        await self._send_callback_message(
                            callbacks=callbacks,
                            step_index=step_index,
                            step=step,
                            action=action,
                            result=error_msg,
                            completed=False
                        )
                        # Continue to next iteration
                        prompt = self._build_execute_prompt(question, step, step_index)
                        prompt += f"\n\nPrevious action failed: {error_msg}"
                
                else:
                    raise ValueError("Invalid response format: missing 'answer' or 'action'")

            except json.JSONDecodeError as e:
                self._logger.error("Failed to parse response: %s", str(e))
                send_message(callbacks, message=CallbackMessage(
                    source=self.id,
                    type=MessageType.LOG,
                    data={
                        "phase": "execution",
                        "step": step_index + 1,
                        "error": f"Failed to parse response: {str(e)}"
                    },
                    project_id=self._project_id
                ))
            except Exception as e:
                self._logger.error("Failed to process response: %s", str(e))
                send_message(callbacks, message=CallbackMessage(
                    source=self.id,
                    type=MessageType.LOG,
                    data={
                        "phase": "execution",
                        "step": step_index + 1,
                        "error": f"Failed to process response: {str(e)}"
                    },
                    project_id=self._project_id
                ))

        # If we exhausted iterations, return a message
        return f"Step {step_index + 1} completed after {self._config.max_execution_iterations} iterations"

    async def _execute(
            self,
            message: Union[str, List[str]],
            output_format: Optional[Union[str, Dict]] = None,
            **kwargs
    ) -> AgentResponse:
        """
        Execute the Plan-and-Execute agent's two-phase process.

        Args:
            message (Union[str, List[str]]): The user's message or a list of messages.
            output_format (Optional[Union[str, Dict]]): Desired format for the output.
            **kwargs: Additional keyword arguments.

        Returns:
            AgentResponse: The agent's final response.
        """
        if isinstance(message, (list, tuple)):
            message = "\n".join(message)
        if output_format is not None:
            message = message + "\n\n" + self._get_output_format_prompt(output_format)
        
        tracer = kwargs.get("tracer", Tracer())
        callbacks = kwargs.get("callbacks", [])

        # Reset state
        self._plan = []
        self._execution_history = []

        # Phase 1: Planning
        send_message(callbacks, message=CallbackMessage(
            source=self.id,
            type=MessageType.LOG,
            data={"phase": "planning", "message": "Starting planning phase..."},
            project_id=self._project_id
        ))
        
        # Display planning start message in terminal
        await send_message_async(
            callbacks,
            message=CallbackMessage(
                source=self.id,
                type=MessageType.LOG,
                metadata={
                    "event": "plain_text",
                    "data": "Planning Phase: Starting plan generation...\n"
                },
                project_id=self._project_id
            )
        )

        self._plan = await self._generate_plan(message, tracer, callbacks)

        send_message(callbacks, message=CallbackMessage(
            source=self.id,
            type=MessageType.LOG,
            data={
                "phase": "planning",
                "message": "Plan generated",
                "plan": self._plan
            },
            project_id=self._project_id
        ))

        # Display plan in terminal
        plan_text = [
            f"{'=' * 66}\n",
            f"Planning Phase: Generated plan...\n",
            f"{'-' * 66}\n",
        ]
        for i, step in enumerate(self._plan):
            plan_text.append(f"Step {i + 1}: {step.get('description', '')}\n")
        plan_text.append("\n")
        
        await send_message_async(
            callbacks,
            message=CallbackMessage(
                source=self.id,
                type=MessageType.LOG,
                metadata={
                    "event": "plain_text",
                    "data": "".join(plan_text)
                },
                project_id=self._project_id
            )
        )

        # Phase 2: Execution
        send_message(callbacks, message=CallbackMessage(
            source=self.id,
            type=MessageType.LOG,
            data={"phase": "execution", "message": "Starting execution phase..."},
            project_id=self._project_id
        ))

        final_results = []
        for i, step in enumerate(self._plan):
            send_message(callbacks, message=CallbackMessage(
                source=self.id,
                type=MessageType.LOG,
                data={
                    "phase": "execution",
                    "message": f"Executing step {i + 1}/{len(self._plan)}",
                    "step": step
                },
                project_id=self._project_id
            ))

            step_result = await self._execute_step(message, step, i, tracer, callbacks)
            final_results.append(f"Step {i + 1}: {step.get('description', '')}\nResult: {step_result}")

        # Generate final answer
        final_answer = "\n\n".join(final_results)
        
        # Optionally, use LLM to synthesize final answer
        if len(final_results) > 1:
            synthesis_prompt = f"""Based on the following execution results, provide a comprehensive final answer to the original question.

Original Question: {message}

Execution Results:
{final_answer}

Please provide a clear, concise final answer that addresses the original question."""
            
            try:
                final_answer = await self._llm.generate_async(
                    messages=[{"role": "user", "content": synthesis_prompt}],
                    tracer=tracer,
                    callbacks=callbacks
                )
            except Exception as e:
                self._logger.error("Failed to synthesize final answer: %s", str(e))
                # Use the concatenated results as fallback

        return AgentResponse(
            name=self._name,
            class_name=self.__class__.__name__,
            response=final_answer,
            trace_id=tracer.trace_id
        )

    def get_plan(self) -> List[Dict[str, str]]:
        """
        Retrieve the current execution plan.

        Returns:
            List[Dict[str, str]]: The execution plan.
        """
        return self._plan

    def get_execution_history(self) -> str:
        """
        Retrieve the execution history.

        Returns:
            str: A string representation of the execution history.
        """
        return "\n".join(self._execution_history)

    def reset(self):
        """Reset the agent state."""
        self._plan = []
        self._execution_history = []

    @staticmethod
    async def _send_callback_message(
            callbacks,
            step_index: int,
            step: Dict[str, str],
            action: Dict = None,
            result: str = "",
            completed: bool = False
    ):
        """Send callback messages for step execution."""
        logs = []
        logs.append(("step", f"{step_index + 1}: {step.get('description', '')}"))
        if action:
            logs.append(("action", action))
        if result:
            logs.append(("result", result))
        if completed:
            logs.append(("status", "completed"))

        data = OrderedDict({"Step": step_index + 1})
        for tag, value in logs:
            data[tag] = value
        
        send_message(callbacks, message=CallbackMessage(
            source=__file__,
            type=MessageType.LOG,
            data=data
        ))
        
        data_text = [
            f"{'=' * 66}\n",
            f"Step {step_index + 1}: {step.get('description', '')}\n",
            f"{'-' * 66}\n",
        ]
        for tag, value in logs:
            if tag != "step":
                data_text.append(f"\033[32m{tag.capitalize()}: {value}\n\n\033[0m")
        
        await send_message_async(
            callbacks,
            message=CallbackMessage(
                source=__file__,
                type=MessageType.LOG,
                metadata={
                    "event": "plain_text",
                    "data": "".join(data_text)
                }
            )
        )

