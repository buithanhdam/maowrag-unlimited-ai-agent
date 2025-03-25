import json
from typing import AsyncGenerator, Generator, List,Any, Optional
from colorama import Fore
from llama_index.core.tools import FunctionTool
from llama_index.core.llms import ChatMessage
from src.llm import BaseLLM
from src.agents.utils import PlanStep, ExecutionPlan, clean_json_response
from src.agents.base import BaseAgent, AgentOptions
import asyncio
from src.logger import get_formatted_logger

logger = get_formatted_logger(__name__)


class ReActAgent(BaseAgent):
    """Agent that creates and executes plans using available tools"""
    
    def __init__(self, llm: BaseLLM, options: AgentOptions, system_prompt:str = "", tools: List[FunctionTool] = []):
        super().__init__(llm, options, system_prompt, tools)

    async def _get_initial_plan(self, task: str, verbose:bool) -> ExecutionPlan:
        """Generate initial execution plan with focus on available tools"""
        prompt = f"""
        You are a planning assistant with access to specific tools. Create a focused plan using ONLY the tools listed below.
        
        Task to accomplish: {task}
        
        Available tools and specifications:
        {self._format_tool_signatures()}
        
        Important rules:
        1. ONLY use the tools listed above - do not assume any other tools exist
        2. If a tool doesn't exist for a specific need, use your general knowledge to provide information
        3. For information retrieval tasks, immediately use the RAG search tool if available
        4. Keep the plan simple and focused - avoid unnecessary steps
        5. Never include web searches or external tool usage in the plan
        
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
                logger.info("Generating initial plan...")
            response = await self.llm.achat(query=prompt)
            response = clean_json_response(response)
            plan_data = json.loads(response)
            
            plan = ExecutionPlan()
            for step_data in plan_data['steps']:
                # Validate tool name if step requires tool
                if step_data['requires_tool']:
                    tool_name = step_data.get('tool_name')
                    if tool_name not in self.tools_dict:
                        # Skip invalid tool steps
                        continue
                
                plan.add_step(PlanStep(
                    description=step_data['description'],
                    tool_name=step_data.get('tool_name'),
                    requires_tool=step_data.get('requires_tool', True)
                ))
            if verbose:
                logger.info(f"Initial plan generated successfully with: {len(plan.steps)} step.")
            return plan
            
        except Exception as e:
            if verbose:
                logger.error(f"Error generating initial plan: {str(e)}")
            raise e

    async def _generate_summary(self, task: str, results: List[Any], verbose:bool) -> str:
        """Generate a coherent summary of the results"""
        prompt = f"""
        Create a clear and concise summary based on the following:
        
        Original task: {task}
        Results from execution: {results}
        
        Rules:
        1. If no relevant information was found, clearly state that
        2. Don't mention the internal steps or tools used
        3. Focus on providing a direct, informative answer
        4. If the information seems insufficient, acknowledge that
        """
        
        if verbose:
            logger.info("Generating summary...")
        
        summary_prompt = self.system_prompt + "\n" + prompt
        
        try:
            result = await self.llm.achat(query=summary_prompt)
            if verbose:
                logger.info(f"Summary generated successfully with final result: {result}.")
            return result
        except Exception as e:
            if verbose:
                logger.error(f"Error generating summary: {str(e)}")
            raise e

    async def run(
        self,
        query: str,
        max_steps: int = 3,
        verbose: bool = False,
        chat_history: List[ChatMessage] = []
    ) -> str:
        """Execute the plan and generate response"""
        if verbose:
            logger.info(f"\nProcessing query: {query}")
        
        try:
            # Generate plan
            plan = await self._get_initial_plan(query,verbose)
            
            if verbose:
                logger.info("\nExecuting plan...")
            
            # Execute all steps and collect results
            results = []
            for step_num, step in enumerate(plan.steps, 1):
                if step_num > max_steps:
                    break
                    
                if verbose:
                    logger.info(f"\nStep {step_num}/{len(plan.steps)}: {step.description}")
                
                try:
                    if step.requires_tool:
                        result = await self._execute_tool(step.tool_name, step.description,step.requires_tool)
                        if verbose:
                            logger.info(f"Tool {step.tool_name} executed successfully with arguments: {result}")
                        if result is not None:
                            results.append(result)
                    else:
                        # Non-tool step - use LLM directly
                        result = await self.llm.achat(query=step.description)
                        results.append(result)
                        
                except Exception as e:
                    if verbose:
                        logger.error(f"Error in step {step_num}: {str(e)}")
                    if step.requires_tool:
                        if verbose:
                            logger.error(f"Error executing tool {step.tool_name}: {str(e)}")
                        raise
                if verbose:
                    logger.info(f"Step {step_num}/{len(plan.steps)} completed.")
                        
            # Generate final summary
            return await self._generate_summary(query, results, verbose)
            
        except Exception as e:
            if verbose:
                logger.error(f"Error in run: {str(e)}")
            raise f"I apologize, but I encountered an error while processing your request: {str(e)}"

    # New methods for chat, stream, achat, and astream implementation
    async def achat(
        self,
        query: str,
        verbose: bool = False,
        chat_history: List[ChatMessage] = [],
        *args,
        **kwargs
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
                chat_history=chat_history
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
        **kwargs
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
                query=query,
                verbose=verbose,
                chat_history=chat_history,
                *args,
                **kwargs
            )
        )

    async def _stream_plan_execution(
        self,
        query: str,
        max_steps: int,
        verbose: bool,
        chat_history: List[ChatMessage]
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
                        result = await self._execute_tool(step.tool_name, step.description, step.requires_tool)
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
                    logger.error(error_msg)
                    if step.requires_tool:
                        raise
            
            # Generate and stream final summary
            yield "\nGenerating final response based on collected information...\n\n"
            
                # Fallback if streaming is not available
            summary = await self._generate_summary(query, results, verbose)
            # Simulate streaming by yielding chunks
            chunk_size = 15
            for i in range(0, len(summary), chunk_size):
                yield summary[i:i+chunk_size]
                await asyncio.sleep(0.01)
                
        except Exception as e:
            error_msg = f"Error during plan execution: {str(e)}"
            logger.error(error_msg)
            yield f"\n{error_msg}\n"

    async def astream_chat(
        self,
        query: str,
        verbose: bool = False,
        chat_history: Optional[List[ChatMessage]] = None,
        *args,
        **kwargs
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
                    chat_history=chat_history
                ):
                    yield token
            else:
                # Otherwise, just run the normal flow and stream the final result
                result = await self.run(
                    query=query,
                    max_steps=max_steps,
                    verbose=verbose,
                    chat_history=chat_history
                )
                
                # Stream the final result in chunks to simulate streaming
                chunk_size = 5
                for i in range(0, len(result), chunk_size):
                    yield result[i:i+chunk_size]
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
        **kwargs
    ) -> Generator[str, None, None]:
        # Create an event loop if one doesn't exist
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # Get the async generator
        async_gen = self.astream_chat(
            query=query,
            verbose=verbose,
            chat_history=chat_history,
            *args,
            **kwargs
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