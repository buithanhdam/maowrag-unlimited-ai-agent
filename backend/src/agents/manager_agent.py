from typing import Any, Dict, List, Optional, Tuple, Generator, AsyncGenerator
from llama_index.core.llms import ChatMessage
from llama_index.core.tools import FunctionTool
from src.llm import BaseLLM
from src.logger import get_formatted_logger
import json
import asyncio
from src.agents.base import BaseAgent, AgentOptions
from src.agents.utils import clean_json_response, ChatHistory

logger = get_formatted_logger(__file__)

CLASSIFY_PROMPT = """\
You are AgentMatcher, an intelligent assistant designed to analyze user queries and match them with 
the most suitable agent or department. Your task is to understand the user request,
identify key entities and intents, and determine which agent or department would be best equipped
to handle the query.

Important: The user input may be a follow-up response to a previous interaction.
The conversation history, including the name of the previously selected agent, is provided.
If the user's input appears to be a continuation of the previous conversation
(e.g., 'yes', 'ok', 'I want to know more', '1'), select the same agent as before.

Available agents and their capabilities: {agent_descriptions}

Based on the user input and chat history, determine the most appropriate agent and provide a confidence score (0-1).

Respond in JSON format:
{{
    "selected_agent": "agent_id",
    "confidence": 0.0,
    "reasoning": "brief explanation"
}}
        
User input: {user_input}
Recent chat history: {chat_history}
\
"""

VALIDATION_PROMPT = """\
You are a ValidatorAgent, responsible for evaluating the quality and relevance of agent responses to user queries.

Your task is to assess whether the agent's response appropriately addresses the user's query, both in terms of content and context.

User Query: {user_query}
Selected Agent: {agent_name}
Agent Response: {agent_response}
Chat History: {chat_history}

Please evaluate and respond in JSON format:
{{
    "is_valid": true/false,
    "score": 0.0,  // Score between 0-1, where 1 is perfect
    "reasoning": "your reasoning here",
    "needs_refinement": true/false,
    "refinement_suggestions": "specific suggestions if needed"
}}
"""

REFINEMENT_PROMPT = """\
You are a response refinement expert. A user query was answered by an agent, but the response needs improvement.

User Query: {user_query}
Original Agent Response: {agent_response}
Validation Feedback: {validation_feedback}

Please provide an improved response that addresses the issues mentioned in the validation feedback.
Maintain the same level of expertise and style as the original agent, but fix the identified problems.
And only give the answer about User Query asked.
"""

class ManagerAgent(BaseAgent):
    def __init__(self, llm: BaseLLM, options: AgentOptions, system_prompt:str = "", tools: List[FunctionTool] = [],validation_threshold = 0.7):
        super().__init__(llm, options, system_prompt, tools)
        self.agent_registry: Dict[str, BaseAgent] = {}
        self.validation_threshold = validation_threshold # Minimum validation score to accept response
        
    def register_agent(self, agent: BaseAgent) -> None:
        """Register a new agent with the manager"""
        self.agent_registry[agent.id] = agent
        logger.info(f"Registered agent: {agent.id} ({agent.name})")

    def _get_agent_descriptions(self) -> str:
        """Generate formatted descriptions of all registered agents"""
        descriptions = []
        for agent_id, agent in self.agent_registry.items():
            descriptions.append(f"- {agent.name} (ID: {agent_id}): {agent.description}")
        return "\n".join(descriptions)

    def _format_chat_history(self, chat_history: List[ChatMessage]) -> str:
        """Format recent chat history for context"""
        if not chat_history:
            return "No recent chat history"
        
        # Take last 3 messages for context
        recent_msgs = chat_history[-6:] if len(chat_history) > 6 else chat_history
        formatted = []
        for msg in recent_msgs:
            formatted.append(f"{msg.role}: {msg.content}")
        return "\n".join(formatted)

    async def classify_request(
        self,
        user_input: str,
        chat_history: List[ChatMessage]
    ) -> Tuple[Optional[BaseAgent], float, str]:
        """Classify user request using LLM and return appropriate agent with confidence score and reasoning"""
        try:
            # Prepare classification prompt
            classification_prompt = CLASSIFY_PROMPT.format(
                agent_descriptions=self._get_agent_descriptions(),
                user_input=user_input,
                chat_history=self._format_chat_history(chat_history)
            )
            
            if len(self.agent_registry) == 0:
                logger.warning("No agents registered with manager")
                return None, 0.0, "No agents available"
                
            # Get classification from LLM
            response = await self.llm.achat(classification_prompt)
            response = clean_json_response(response)
            
            try:
                # Parse LLM response
                classification = json.loads(response)
                selected_agent_id = classification["selected_agent"]
                confidence = float(classification["confidence"])
                reasoning = classification["reasoning"]
                
                # Get selected agent
                selected_agent = self.agent_registry.get(selected_agent_id)
                
                if selected_agent:
                    logger.info(
                        f"Request classified to {selected_agent.name} "
                        f"(confidence: {confidence:.2f}). Reasoning: {reasoning}"
                    )
                    return selected_agent, confidence, reasoning
                else:
                    logger.warning(f"Selected agent {selected_agent_id} not found in registry")
                    default_agent = next(iter(self.agent_registry.values())) if self.agent_registry else None
                    return default_agent, 0.5, f"Selected agent {selected_agent_id} not found, using default"
                    
            except (json.JSONDecodeError, KeyError) as e:
                logger.error(f"Error parsing LLM classification response: {str(e)}")
                default_agent = next(iter(self.agent_registry.values())) if self.agent_registry else None
                return default_agent, 0.5, f"Error in classification: {str(e)}"
                
        except Exception as e:
            logger.error(f"Error during request classification: {str(e)}")
            default_agent = next(iter(self.agent_registry.values())) if self.agent_registry else None
            return default_agent, 0.5, f"Exception in classification: {str(e)}"

    async def validate_response(
        self,
        user_query: str,
        agent_name: str,
        agent_response: str,
        chat_history: List[ChatMessage],
        verbose: bool = False
    ) -> Dict[str, Any]:
        """Validate an agent's response to ensure it properly addresses the user query"""
        try:
            validation_prompt = VALIDATION_PROMPT.format(
                user_query=user_query,
                agent_name=agent_name,
                agent_response=agent_response,
                chat_history=self._format_chat_history(chat_history)
            )
            
            validation_response = await self.llm.achat(validation_prompt)
            validation_response = clean_json_response(validation_response)
            
            try:
                validation_result = json.loads(validation_response)
                if verbose:
                    logger.info(f"Validation result: {validation_result}")
                return validation_result
            except json.JSONDecodeError as e:
                if verbose:
                    logger.error(f"Error parsing validation response: {str(e)}")
                return {
                    "is_valid": True,  # Default to accepting the response
                    "score": 0.75,
                    "reasoning": "Failed to parse validation result",
                    "needs_refinement": False,
                    "refinement_suggestions": ""
                }
                
        except Exception as e:
            if verbose:
                logger.error(f"Error during response validation: {str(e)}")
            return {
                "is_valid": True,  # Default to accepting the response
                "score": 0.75,
                "reasoning": f"Validation error: {str(e)}",
                "needs_refinement": False,
                "refinement_suggestions": ""
            }
            
    async def refine_response(
        self,
        user_query: str,
        agent_response: str,
        validation_feedback: Dict[str, Any],
        verbose: bool = False
    ) -> str:
        """Refine an agent's response based on validation feedback"""
        try:
            refinement_prompt = REFINEMENT_PROMPT.format(
                user_query=user_query,
                agent_response=agent_response,
                validation_feedback=json.dumps(validation_feedback, indent=2)
            )
            
            refined_response = await self.llm.achat(refinement_prompt)
            if verbose:
                logger.info(f"Response refined successfully")
            return refined_response
            
        except Exception as e:
            if verbose:
                logger.error(f"Error during response refinement: {str(e)}")
            return agent_response  # Return original response if refinement fails

    async def run(
        self,
        query: str,
        chat_history: List[ChatMessage] = [],
        verbose: bool = False,
        additional_params: Dict[str, Any] = {},
        max_retries: int = 1
    ) -> str:
        """Process user request by classifying and delegating to appropriate agent"""
        try:
            if self.callbacks:
                self.callbacks.on_agent_start(self.name)
                
            # Classify the request
            selected_agent, confidence, reasoning = await self.classify_request(query, chat_history)
            
            if not selected_agent:
                if verbose:
                    logger.info("No appropriate agent found, falling back to LLM")
                response = await self.llm.achat("Answer this question: " + query, chat_history=chat_history)
                
                if self.callbacks:
                    self.callbacks.on_agent_end(self.name)
                return response
            
            # If confidence is too low, maybe ask for clarification or fall back to LLM
            if confidence < 0.6:
                if verbose:
                    logger.info(
                        f"Low confidence classification ({confidence:.2f}). "
                        f"Falling back to LLM."
                    )
                response = await self.llm.achat("Answer this question: " + query, chat_history=chat_history)
                
                if self.callbacks:
                    self.callbacks.on_agent_end(self.name)
                return response
            
            # Log the classification
            if verbose:
                logger.info(
                    f"Request classified to {selected_agent.name} "
                    f"with confidence {confidence:.2f}"
                )
            
            # Execute the request with the selected agent
            agent_response = await selected_agent.achat(
                query=query,
                verbose=verbose,
                chat_history=chat_history,
                **additional_params
            )
            
            # Validate the response
            validation_result = await self.validate_response(
                user_query=query,
                agent_name=selected_agent.name,
                agent_response=agent_response,
                chat_history=chat_history,
                verbose=verbose
            )
            
            if verbose:
                logger.info(f"Validation score: {validation_result['score']:.2f}")
                
            # Check if refinement is needed
            if (validation_result.get("needs_refinement", False) and 
                validation_result.get("score", 1.0) < self.validation_threshold):
                
                if verbose:
                    logger.info(f"Refining response based on validation feedback")
                
                refined_response = await self.refine_response(
                    user_query=query,
                    agent_response=agent_response,
                    validation_feedback=validation_result,
                    verbose=verbose
                )
                
                final_response = refined_response
            else:
                final_response = agent_response
                
            if self.callbacks:
                self.callbacks.on_agent_end(self.name)
                
            return final_response
            
        except Exception as e:
            logger.error(f"Error processing request: {str(e)}")
            if self.callbacks:
                self.callbacks.on_agent_end(self.name)
                
            return (
                "I encountered an error while processing your request. "
                "Please try again or rephrase your question."
            )

    async def get_agent_status(self) -> Dict[str, Any]:
        """Get status information about all registered agents"""
        return {
            "total_agents": len(self.agent_registry),
            "registered_agents": [
                {
                    "id": agent_id,
                    "name": agent.name,
                    "description": agent.description,
                    "status": "active"  # Could be expanded to check actual agent status
                }
                for agent_id, agent in self.agent_registry.items()
            ]
        }
        
    # Required BaseAgent implementations
    async def achat(
        self,
        query: str,
        verbose: bool = False,
        chat_history: List[ChatMessage] = [],
        *args,
        **kwargs
    ) -> str:
        """Async chat implementation for BaseAgent"""
        additional_params = kwargs.get("additional_params", {})
        max_retries = kwargs.get("max_retries", 1)
        
        return await self.run(
            query=query,
            chat_history=chat_history,
            verbose=verbose,
            additional_params=additional_params,
            max_retries=max_retries
        )
        
    def chat(
        self,
        query: str,
        verbose: bool = False,
        chat_history: List[ChatMessage] = [],
        *args,
        **kwargs
    ) -> str:
        """Sync chat implementation for BaseAgent"""
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
        """Async streaming chat implementation for BaseAgent"""
        chat_history = chat_history or []
        additional_params = kwargs.get("additional_params", {})
        max_retries = kwargs.get("max_retries", 1)
        
        if self.callbacks:
            self.callbacks.on_agent_start(self.name)
            
        try:
            response = await self.run(
                query=query,
                chat_history=chat_history,
                verbose=verbose,
                additional_params=additional_params,
                max_retries=max_retries
            )  
            # Simulate streaming by yielding chunks
            chunk_size = 5  # Characters per chunk
            for i in range(0, len(response), chunk_size):
                chunk = response[i:i+chunk_size]
                if self.callbacks:
                    self.callbacks.on_llm_new_token(chunk)
                yield chunk
                await asyncio.sleep(0.01)  # Small delay to simulate streaming
                    
        except Exception as e:
            logger.error(f"Error in streaming: {str(e)}")
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
        """Sync streaming chat implementation for BaseAgent"""
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