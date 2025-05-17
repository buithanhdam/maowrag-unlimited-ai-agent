from typing import Any, AsyncGenerator, Dict, Generator, List
import asyncio
from llama_index.core.llms import ChatMessage
from llama_index.core.tools import FunctionTool

from src.llm import BaseLLM
from .base import BaseMultiAgent
from src.agents.design import (
    AgentOptions,
)
from src.agents.base import BaseAgent


INTEGRATION_PROMPT = """\
You are responsible for combining outputs from multiple specialized agents into a coherent response.
Each agent has provided structured data related to its expertise domain.

Your task is to synthesize this information into a comprehensive response that addresses the original query.

Original User Query: {user_query}

Agent Outputs:
{agent_outputs}

If an output schema was provided, please ensure your response conforms to this structure:
{output_schema}

Please provide a comprehensive response that integrates all the information from the specialized agents.
Be concise and ensure all critical information is included.
"""

class ParallelAgent(BaseMultiAgent):
    """ParallelAgent that executes multiple agents in parallel and combines their results"""
    
    def __init__(
        self, 
        llm: BaseLLM, 
        options: AgentOptions, 
        system_prompt: str = "", 
        tools: List[FunctionTool] = [],
        validation_threshold: float = 0.7,
    ):
        super().__init__(llm, options, system_prompt, tools, validation_threshold)
    
    async def _execute_parallel(
        self,
        query: str,
        agents_to_execute: List[BaseAgent],
        chat_history: List[ChatMessage] = [],
        verbose: bool = False,
        additional_params: Dict[str, Any] = {}
    ) -> Dict[str, Any]:
        """Execute multiple agents in parallel and collect their results"""
        if verbose:
            self._log_info(f"Executing {len(agents_to_execute)} agents in parallel")
            
        # Create tasks for each agent
        tasks = []
        for agent in agents_to_execute:
            if verbose:
                self._log_info(f"Creating task for agent: {agent.name}")
            task = asyncio.create_task(
                agent.achat(
                    query=query,
                    verbose=verbose,
                    chat_history=chat_history,
                    **additional_params
                )
            )
            tasks.append((agent.name, task))
            
        # Wait for all tasks to complete
        results = {}
        for agent_name, task in tasks:
            try:
                result = await task
                results[agent_name] = result
                if verbose:
                    self._log_info(f"Agent {agent_name} completed successfully")
            except Exception as e:
                self._log_error(f"Error executing agent {agent_name}: {str(e)}")
                results[agent_name] = f"Error: {str(e)}"
                
        return results
    
    async def _integrate_results(
        self,
        query: str,
        agent_results: Dict[str, Any],
        chat_history: List[ChatMessage] = [],
        verbose: bool = False
    ) -> str:
        """Integrate results from multiple agents into a coherent response"""
        # Format agent outputs for integration
        formatted_outputs = []
        for agent_name, result in agent_results.items():
            formatted_outputs.append(f"--- {agent_name} Output ---\n{result}\n")
            
        agent_outputs = "\n".join(formatted_outputs)
        output_schema = self._get_output_schema()
        
        integration_prompt = INTEGRATION_PROMPT.format(
            user_query=query,
            agent_outputs=agent_outputs,
            output_schema=output_schema
        )
        
        if verbose:
            self._log_info("Integrating results from multiple agents")
            
        try:
            # If an output model is defined, use structured output
            integration_result = await self._output_parser(output=integration_prompt, chat_history=chat_history)
                
            if verbose:
                self._log_info("Integration completed successfully")
                
            return integration_result
        except Exception as e:
            error_msg = f"Error integrating results: {str(e)}"
            self._log_error(error_msg)
            return error_msg
    
    async def _run_parallel(
        self,
        query: str,
        chat_history: List[ChatMessage] = [],
        verbose: bool = False,
        additional_params: Dict[str, Any] = {},
        max_retries: int = 1
    ) -> str:
        """Process user request by executing multiple agents in parallel"""
        try:
            if self.callbacks:
                self.callbacks.on_agent_start(self.name)
                
            # Use all registered agents if none specified
            agents_to_execute = list(self.agent_registry.values())
                
            if not agents_to_execute:
                if verbose:
                    self._log_info("No agents available for execution")
                response = await self.llm.achat("Answer this question: " + query, chat_history=chat_history)
                await asyncio.sleep(2)
                if self.callbacks:
                    self.callbacks.on_agent_end(self.name)
                return response
                
            # Execute agents in parallel
            agent_results = await self._execute_parallel(
                query=query,
                agents_to_execute=agents_to_execute,
                chat_history=chat_history,
                verbose=verbose,
                additional_params=additional_params
            )
            await asyncio.sleep(2)
            # Integrate results
            final_response = await self._integrate_results(
                query=query,
                agent_results=agent_results,
                chat_history=chat_history,
                verbose=verbose
            )
            await asyncio.sleep(2)
            if self.callbacks:
                self.callbacks.on_agent_end(self.name)
                
            return final_response
            
        except Exception as e:
            self._log_error(f"Error in parallel execution: {str(e)}")
            if self.callbacks:
                self.callbacks.on_agent_end(self.name)
                
            return (
                "I encountered an error while processing your request in parallel mode. "
                f"Error: {str(e)}"
            )
    
    # Override the achat method to support parallel execution
    async def achat(
        self,
        query: str,
        verbose: bool = False,
        chat_history: List[ChatMessage] = [],
        parallel: bool = True,
        *args,
        **kwargs
    ) -> str:
        """Async chat implementation that supports both parallel and sequential execution"""
        additional_params = kwargs.get("additional_params", {})
        max_retries = kwargs.get("max_retries", 1)
        
        # If parallel mode is enabled, use parallel execution
        if parallel:
            return await self._run_parallel(
                query=query,
                chat_history=chat_history,
                verbose=verbose,
                additional_params=additional_params,
                max_retries=max_retries
            )
        # Otherwise fall back to the sequential manager behavior
        else:
            return await super().achat(
                query=query,
                verbose=verbose,
                chat_history=chat_history,
                *args,
                **kwargs
            )
    
    # Override the chat method to support parallel execution
    def chat(
        self,
        query: str,
        verbose: bool = False,
        chat_history: List[ChatMessage] = [],
        parallel: bool = True,
        *args,
        **kwargs
    ) -> str:
        """Sync chat implementation that supports both parallel and sequential execution"""
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
                parallel=parallel,
                *args,
                **kwargs
            )
        )
    def stream_chat(
        self,
        query: str,
        verbose: bool = False,
        chat_history: List[ChatMessage] = [],
        parallel: bool = True,
        *args,
        **kwargs,
    ) -> Generator[str, None, None]:
        pass

    async def astream_chat(
        self,
        query: str,
        verbose: bool = False,
        chat_history: List[ChatMessage] = [],
        parallel: bool = True,
        *args,
        **kwargs,
    ) -> AsyncGenerator[str, None]:
        pass