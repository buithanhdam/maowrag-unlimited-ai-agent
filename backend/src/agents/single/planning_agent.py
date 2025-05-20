import json
from typing import AsyncGenerator, Generator, List, Any, Optional
from llama_index.core.tools import FunctionTool
from llama_index.core.llms import ChatMessage
import asyncio

from src.llm import BaseLLM
from src.agents.design import (
    clean_json_response,
    AgentCallbacks,
    AgentOptions,
    ExecutionPlan,
    PlanContext,
    PlanStep,
    retry_on_error,
)
from src.agents.base import BaseAgent


class PlanningAgent(BaseAgent):
    """Agent that creates and executes plans using available tools"""

    def __init__(
        self,
        llm: BaseLLM,
        options: AgentOptions,
        system_prompt: str = "",
        tools: List[FunctionTool] = [],
    ):
        super().__init__(llm, options, system_prompt, tools)

    async def _refine_plan(
        self, plan: ExecutionPlan, current_results: List[Any]
    ) -> ExecutionPlan:
        """Điều chỉnh kế hoạch dựa trên kết quả hiện tại"""
        # Cập nhật kế hoạch dựa trên kết quả của các bước trước
        # Thêm/xóa/thay đổi các bước nếu cần
        return "updated_plan"

    async def _evaluate_step_success(self, step: PlanStep, result: Any) -> bool:
        """Đánh giá liệu bước có thành công hay không"""
        # Nếu bước yêu cầu dữ liệu cụ thể, kiểm tra xem kết quả có chứa dữ liệu đó không
        return "evaluation_result"

    async def _decide_next_action(
        self, plan: ExecutionPlan, current_step: int, context: PlanContext
    ) -> int:
        """Quyết định bước tiếp theo cần thực hiện"""
        # Có thể bỏ qua các bước, quay lại, hoặc kết thúc sớm
        return "next_step_index"

    async def _process_tool_output(self, tool_name: str, output: Any) -> Any:
        """Xử lý kết quả từ công cụ dựa trên loại công cụ"""
        # Xử lý đầu ra tùy thuộc vào loại công cụ
        return "processed_output"

    async def _find_relevant_tools(self, query: str) -> List[str]:
        """Tìm các công cụ liên quan đến truy vấn"""
        # Sử dụng vector search để tìm công cụ phù hợp nhất
        return "relevant_tool_names"

    @retry_on_error()
    async def _get_initial_plan(
        self, task: str, verbose: bool, chat_history: List[ChatMessage] = []
    ) -> ExecutionPlan:
        """Generate initial execution plan with focus on available tools"""
        prompt = f"""
        Acting as a planning assistant with access to specific tools. Create a focused plan using ONLY the tools listed below.
        
        Task to accomplish: {task}
        
        Available tools and specifications:
        {self._format_tool_signatures()}
        
        Important rules:
        1. ONLY use the tools listed above - do not assume any other tools exist
        2. If a tool doesn't exist for a specific need, use your general knowledge to provide information
        3. For information retrieval tasks, immediately use the RAG search tool if available
        4. Keep the plan simple and focused - avoid unnecessary steps
        5. Never include web searches or external tool usage in the plan
        6. If no tools are needed, create a single step with requires_tool: false
        
        Format your response as JSON:
        {{
            "steps": [
                {{
                    "description": "step description",
                    "requires_tool": true/false,
                    "tool_name": "tool_name or null"
                }},
                ...
            ]
        }}
        """

        try:
            if verbose:
                self._log_info("Generating initial plan...")
            response = await self.llm.achat(query=prompt, chat_history=chat_history)
            response = clean_json_response(response)
            plan_data = json.loads(response)

            plan = ExecutionPlan()
            for step_data in plan_data["steps"]:
                # Validate tool name if step requires tool
                if step_data["requires_tool"]:
                    tool_name = step_data.get("tool_name")
                    if tool_name not in self.tools_dict:
                        # Skip invalid tool steps
                        continue

                plan.add_step(
                    PlanStep(
                        description=step_data["description"],
                        tool_name=step_data.get("tool_name"),
                        requires_tool=step_data.get("requires_tool", True),
                    )
                )
            if verbose:
                self._log_info(
                    f"Initial plan generated successfully with: {len(plan.steps)} step. Plan details: {plan_data}"
                )
            return plan

        except Exception as e:
            if verbose:
                self._log_error(f"Error generating initial plan: {str(e)}")
            raise e

    @retry_on_error()
    async def _generate_summary(
        self,
        task: str,
        results: List[Any],
        verbose: bool,
        chat_history: List[ChatMessage] = [],
    ) -> str:
        """Generate a coherent summary of the results"""
        SUMMARY_PROMPT = f"""\
        You are responsible for combining Task Results into a coherent response.
        Original task: {task}
        Task Results:
        {results}
        If an output schema was provided, please ensure your response conforms to this structure:
        {self._get_output_schema()}

        Please provide a comprehensive response that integrates all the information.
        Be concise and ensure all critical information is included.
        """
        if verbose:
            self._log_info("Generating summary...")

        try:
            result = await self._output_parser(
                output=SUMMARY_PROMPT, chat_history=chat_history
            )
            if verbose:
                self._log_info(
                    f"Summary generated successfully with final result: {result}."
                )
            return result
        except Exception as e:
            if verbose:
                self._log_error(f"Error generating summary: {str(e)}")
            raise e

    @retry_on_error()
    async def run(
        self,
        query: str,
        max_steps: int = 3,
        verbose: bool = False,
        chat_history: List[ChatMessage] = [],
    ) -> str:
        """Execute the plan and generate response"""
        if verbose:
            self._log_info(f"\nProcessing query: {query}")

        try:
            # Generate plan
            plan = await self._get_initial_plan(query, verbose, chat_history)
            await asyncio.sleep(0.1)

            if verbose:
                self._log_info("\nExecuting plan...")

            # Execute all steps and collect results
            results = []
            for step_num, step in enumerate(plan.steps, 1):
                if step_num > max_steps:
                    break

                if verbose:
                    self._log_info(
                        f"\nStep {step_num}/{len(plan.steps)}: {step.description}"
                    )

                try:
                    if step.requires_tool:
                        result = await self._execute_tool(
                            step.tool_name, step.description, step.requires_tool
                        )
                        if verbose:
                            self._log_info(
                                f"Tool {step.tool_name} executed successfully with arguments: {result}"
                            )
                        if result is not None:
                            results.append(result)
                    else:
                        # Non-tool step - use LLM directly
                        result = await self.llm.achat(
                            query=step.description, chat_history=chat_history
                        )
                        results.append(result)
                    await asyncio.sleep(0.1)
                except Exception as e:
                    if verbose:
                        self._log_error(f"Error in step {step_num}: {str(e)}")
                    if step.requires_tool:
                        if verbose:
                            self._log_error(
                                f"Error executing tool {step.tool_name}: {str(e)}"
                            )
                        raise e
                if verbose:
                    self._log_info(f"Step {step_num}/{len(plan.steps)} completed.")

            # Generate final summary
            final_result = await self._generate_summary(query, results, verbose, chat_history)
            await asyncio.sleep(0.1)
            return final_result

        except Exception as e:
            if verbose:
                self._log_error(f"Error in run: {str(e)}")
            raise f"I apologize, but I encountered an error while processing your request: {str(e)}"

    # New methods for chat, stream, achat, and astream implementation
    async def achat(
        self,
        query: str,
        verbose: bool = False,
        chat_history: List[ChatMessage] = [],
        *args,
        **kwargs,
    ) -> str:
        # Get additional parameters or use defaults
        max_steps = kwargs.get("max_steps", 3)

        if self.callbacks:
            self.callbacks.on_agent_start(self.name)

        try:
            # Run the planning and execution flow
            result = await self.run(
                query=query,
                max_steps=max_steps,
                verbose=verbose,
                chat_history=chat_history,
            )

            return result

        finally:
            if self.callbacks:
                self.callbacks.on_agent_end(self.name)

    def chat(
        self,
        query: str,
        verbose: bool = False,
        chat_history: List[ChatMessage] = [],
        *args,
        **kwargs,
    ) -> str:
        # Create an event loop if one doesn't exist
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # Run the async chat method in the event loop
        return loop.run_until_complete(
            self.achat(
                query=query, verbose=verbose, chat_history=chat_history, *args, **kwargs
            )
        )

    @retry_on_error()
    async def _stream_plan_execution(
        self, query: str, max_steps: int, verbose: bool, chat_history: List[ChatMessage]
    ) -> AsyncGenerator[str, None]:
        """Stream the plan execution process with status updates"""
        try:
            # Start with planning notification
            yield "Planning your request...\n"

            # Generate plan
            plan = await self._get_initial_plan(query, verbose)

            yield f"Created plan with {len(plan.steps)} steps.\n"

            # Execute all steps and collect results
            results = []
            for step_num, step in enumerate(plan.steps, 1):
                if step_num > max_steps:
                    yield "\nReached maximum number of steps. Finalizing results...\n"
                    break

                # Stream step information
                yield f"\nExecuting step {step_num}: {step.description}\n"

                try:
                    if step.requires_tool:
                        yield f"Using tool: {step.tool_name}\n"
                        result = await self._execute_tool(
                            step.tool_name, step.description, step.requires_tool
                        )
                        if result is not None:
                            yield "Tool execution complete.\n"
                            results.append(result)
                    else:
                        yield "Processing with general knowledge...\n"
                        result = await self.llm.achat(query=step.description)
                        results.append(result)

                except Exception as e:
                    error_msg = f"Error in step {step_num}: {str(e)}\n"
                    yield error_msg
                    self._log_error(error_msg)
                    if step.requires_tool:
                        raise

            # Generate and stream final summary
            yield "\nGenerating final response based on collected information...\n\n"

            # Fallback if streaming is not available
            summary = await self._generate_summary(query, results, verbose)
            # Simulate streaming by yielding chunks
            chunk_size = 15
            for i in range(0, len(summary), chunk_size):
                yield summary[i : i + chunk_size]
                await asyncio.sleep(0.01)

        except Exception as e:
            error_msg = f"Error during plan execution: {str(e)}"
            self._log_error(error_msg)
            yield f"\n{error_msg}\n"

    async def astream_chat(
        self,
        query: str,
        verbose: bool = False,
        chat_history: Optional[List[ChatMessage]] = None,
        *args,
        **kwargs,
    ) -> AsyncGenerator[str, None]:
        # Get additional parameters
        max_steps = kwargs.get("max_steps", 3)
        chat_history = chat_history or []
        detailed_stream = kwargs.get("detailed_stream", False)
        if self.callbacks:
            self.callbacks.on_agent_start(self.name)

        try:
            # If detailed_stream is True, show the entire planning process
            if detailed_stream:
                async for token in self._stream_plan_execution(
                    query=query,
                    max_steps=max_steps,
                    verbose=verbose,
                    chat_history=chat_history,
                ):
                    yield token
            else:
                # Otherwise, just run the normal flow and stream the final result
                result = await self.run(
                    query=query,
                    max_steps=max_steps,
                    verbose=verbose,
                    chat_history=chat_history,
                )

                # Stream the final result in chunks to simulate streaming
                chunk_size = 5
                for i in range(0, len(result), chunk_size):
                    yield result[i : i + chunk_size]
                    await asyncio.sleep(0.01)

        finally:
            if self.callbacks:
                self.callbacks.on_agent_end(self.name)

    def stream_chat(
        self,
        query: str,
        verbose: bool = False,
        chat_history: Optional[List[ChatMessage]] = None,
        *args,
        **kwargs,
    ) -> Generator[str, None, None]:
        # Create an event loop if one doesn't exist
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # Get the async generator
        async_gen = self.astream_chat(
            query=query, verbose=verbose, chat_history=chat_history, *args, **kwargs
        )

        # Helper function to convert async generator to sync generator
        def sync_generator():
            agen = async_gen.__aiter__()
            while True:
                try:
                    yield loop.run_until_complete(agen.__anext__())
                except StopAsyncIteration:
                    break

        return sync_generator()
