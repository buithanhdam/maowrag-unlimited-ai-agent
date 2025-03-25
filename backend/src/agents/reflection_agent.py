import asyncio
from typing import List, Any, Generator, Optional, AsyncGenerator, Union
from llama_index.core.llms import ChatMessage
from llama_index.core.tools import FunctionTool
from src.logger import get_formatted_logger
from src.llm import BaseLLM
from src.agents.base import BaseAgent, AgentOptions
from src.agents.utils import ChatHistory

logger = get_formatted_logger(__name__)

BASE_GENERATION_SYSTEM_PROMPT = """
Your task is to Generate the best content possible for the user's request.
If the user provides critique, respond with a revised version of your previous attempt.
You must always output the revised content.
"""

BASE_REFLECTION_SYSTEM_PROMPT = """
You are tasked with generating critique and recommendations to the user's generated content.
If the user content has something wrong or something to be improved, output a list of recommendations and critiques.
If the user content is ok and there's nothing to change, output this: <OK>
Utilize available tools if necessary to improve or validate the content.
"""

class ReflectionAgent(BaseAgent):
    def __init__(self, llm: BaseLLM, options: AgentOptions, system_prompt:str = "", tools: List[FunctionTool] = []):
        logger.debug("Initializing ReflectionAgent")
        super().__init__(llm, options,system_prompt, tools)

    def _extract_tool_recommendations(self, critique: str,  verbose:bool) -> List[tuple]:
        """
        Extract tool recommendations from critique.
        Looks for patterns like: "Use [tool_name] to [description]"
        """
        tool_recommendations = []
        if verbose:
            logger.info(f"Extracting tool recommendations from critique: {critique}")
        # Basic pattern matching for tool recommendations
        for tool_name in self.tools_dict.keys():
            if tool_name.lower() in critique.lower():
                # Try to extract the description after the tool name
                import re
                match = re.search(rf"{tool_name}\s+to\s+(.+)", critique, re.IGNORECASE)
                if match:
                    tool_recommendations.append((tool_name, match.group(1)))
                else:
                    # Fallback recommendation
                    tool_recommendations.append((tool_name, "Improve the content"))
        if verbose:
            logger.info(f"Tool recommendations extracted: {tool_recommendations}")
        return tool_recommendations

    async def agenerate_response(self, chat_history: List[ChatMessage],verbose: bool) -> str:
        if verbose:
            logger.debug("Generating async response")
        try:
            response = await self.llm.achat(query=chat_history[-1].content, chat_history=chat_history[:-1])
            if verbose:
                logger.info("Async response generated successfully")
            return response
        except Exception as e:
            if verbose:
                logger.error(f"Error generating response: {str(e)}")
            raise

    def generate_response(self, chat_history: List[ChatMessage], verbose: bool) -> str:
        if verbose:
            logger.debug("Generating sync response")
        try:
            response = self.llm.chat(query=chat_history[-1].content, chat_history=chat_history[:-1])
            if verbose:
                logger.info("Sync response generated successfully")
            return response
        except Exception as e:
            if verbose:
                logger.error(f"Error generating response: {str(e)}")
            raise

    async def agenerate(self, history: ChatHistory, verbose: bool = False) -> str:
        if verbose:
            logger.debug("Calling async generate")
        return await self.agenerate_response(history.get_messages(), verbose)

    def generate(self, history: ChatHistory, verbose: bool = False) -> str:
        if verbose:
            logger.debug("Calling generate")
        return self.generate_response(history.get_messages(), verbose)

    async def areflect(self, history: ChatHistory, verbose: bool = False) -> str:
        if verbose:
            logger.debug("Calling async reflect")
        if self.tools:
            history.get_messages()[-1].content += f"\nAvailable tools:\n{self._format_tool_signatures()}"
        return await self.agenerate_response(history.get_messages(), verbose)

    def reflect(self, history: ChatHistory, verbose: bool = False) -> str:
        if verbose:
            logger.debug("Calling reflect")
        if self.tools:
            history.get_messages()[-1].content += f"\nAvailable tools:\n{self._format_tool_signatures()}"
        return self.generate_response(history.get_messages(), verbose)


    async def aloop(
        self,
        generation_history: ChatHistory,
        reflection_history: ChatHistory,
        n_steps: int,
        max_tool_steps: int,
        verbose: bool = False
    ) -> str:
        tool_steps_count = 0
        final_generation = ""

        for step in range(n_steps):
            if verbose:
                logger.info(f"Step {step + 1}/{n_steps}")

            # Generate content
            generation = await self.agenerate(generation_history, verbose=verbose)
            generation_history.add("assistant", generation)
            reflection_history.add("user", generation)

            # Reflect on the generation
            critique = await self.areflect(reflection_history, verbose=verbose)
            
            if "<OK>" in critique:
                if verbose:
                    logger.info("\nReflection complete - content is satisfactory\n")
                final_generation = generation
                break

            # Check for tool recommendations in critique
            tool_recommendations = self._extract_tool_recommendations(critique,verbose)
            
            for tool_name, tool_description in tool_recommendations:
                if tool_steps_count < max_tool_steps:
                    try:
                        tool_result = await self._execute_tool(tool_name, tool_description,True)
                        if not tool_result:
                            critique += f"\nTool {tool_name} did not return any result"
                        else:
                            critique += f"\nTool {tool_name} result: {tool_result}"
                        tool_steps_count += 1
                    except Exception as e:
                        critique += f"\nTool {tool_name} execution failed: {str(e)}"
            generation_history.add("user", critique)
            reflection_history.add("assistant", critique)
            final_generation = generation
            if verbose:
                logger.info(f"Step {step + 1}/{n_steps} completed")
        if verbose:
            logger.info(f"\n\nFinal generation: {final_generation}\n\n")
        return final_generation

    # Implement the required methods from BaseAgent
    async def run(
        self,
        query: str,
        n_steps: int = 3,
        max_tool_steps: int = 2,
        verbose: bool = False,
        chat_history: List[ChatMessage] = []
    ) -> str:
        # Initialize system prompts
        full_gen_prompt = self.system_prompt + "\n"  + BASE_GENERATION_SYSTEM_PROMPT
        full_ref_prompt = self.system_prompt + "\n"  + BASE_REFLECTION_SYSTEM_PROMPT

        # Initialize chat histories
        generation_history = ChatHistory(
            initial_messages=[
                self._create_system_message(full_gen_prompt),
                ChatMessage(role="user", content=query)
            ],
            max_length=3
        )

        reflection_history = ChatHistory(
            initial_messages=[self._create_system_message(full_ref_prompt)],
            max_length=3
        )

        # Incorporate existing chat history if provided
        if chat_history:
            for msg in chat_history:
                if msg.role == "user":
                    generation_history.add("user", msg.content)
                elif msg.role == "assistant":
                    generation_history.add("assistant", msg.content)

        return await self.aloop(
            generation_history,
            reflection_history,
            n_steps,
            max_tool_steps,
            verbose
        )

    # Implement BaseAgent abstract methods
    async def achat(
        self,
        query: str,
        verbose: bool = False,
        chat_history: List[ChatMessage] = [],
        *args,
        **kwargs
    ) -> str:
        # Get additional parameters or use defaults
        n_steps = kwargs.get("n_steps", 3)
        max_tool_steps = kwargs.get("max_tool_steps", 2)

        if self.callbacks:
            self.callbacks.on_agent_start(self.name)

        result = await self.run(
            query=query,
            n_steps=n_steps,
            max_tool_steps=max_tool_steps,
            verbose=verbose,
            chat_history=chat_history
        )

        if self.callbacks:
            self.callbacks.on_agent_end(self.name)

        return result

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

    async def astream_chat(
        self,
        query: str,
        verbose: bool = False,
        chat_history: Optional[List[ChatMessage]] = None,
        *args,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        # Get parameters
        n_steps = kwargs.get("n_steps", 3)
        max_tool_steps = kwargs.get("max_tool_steps", 2)
        chat_history = chat_history or []

        if self.callbacks:
            self.callbacks.on_agent_start(self.name)

        try:
            # First perform the reflection loop to get the final content
            final_content = await self.run(
                query=query,
                n_steps=n_steps,
                max_tool_steps=max_tool_steps,
                verbose=verbose,
                chat_history=chat_history
            )
            
            # If no final polish, just yield the final content in chunks
            # This simulates streaming for consistency
            chunk_size = 5  # Adjust as needed
            for i in range(0, len(final_content), chunk_size):
                chunk = final_content[i:i+chunk_size]
                yield chunk
                await asyncio.sleep(0.01)  # Small delay to simulate streaming
        except Exception as e:
            raise e           
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