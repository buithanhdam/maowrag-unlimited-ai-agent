from typing import Any, Dict, List, Optional
from llama_index.core.tools import FunctionTool
from src.llm import BaseLLM
from src.agents.base import BaseAgent, AgentOptions


class BaseMultiAgent(BaseAgent):
    def __init__(self, llm: BaseLLM, options: AgentOptions, system_prompt:str = "", tools: List[FunctionTool] = [],validation_threshold = 0.7):
        super().__init__(llm, options, system_prompt, tools)
        self.agent_registry: Dict[str, BaseAgent] = {}
        self.validation_threshold = validation_threshold # Minimum validation score to accept response
        
    def _register_agent(self, agent: BaseAgent) -> None:
        """Register a new agent with the manager"""
        self.agent_registry[agent.id] = agent
        self.logger.info(f"Registered agent: {agent.id} ({agent.name})")
    def _unregister_agent(self, agent_id: str) -> None:
        """Unregister an agent from the manager"""
        if agent_id in self.agent_registry:
            del self.agent_registry[agent_id]
            self.logger.info(f"Unregistered agent: {agent_id}")
        else:
            self.logger.warning(f"Agent ID {agent_id} not found in registry.")
    def _get_agent(self, agent_id: str) -> Optional[BaseAgent]:
        """Retrieve an agent by its ID"""
        return self.agent_registry.get(agent_id, None)
    def _get_all_agents(self) -> List[BaseAgent]:
        """Get a list of all registered agents"""
        return list(self.agent_registry.values())
    def _get_agent_descriptions(self) -> str:
        """Generate formatted descriptions of all registered agents"""
        descriptions = []
        for agent_id, agent in self.agent_registry.items():
            descriptions.append(f"- {agent.name} (ID: {agent_id}): {agent.description}")
        return "\n".join(descriptions)
    def _get_agent_status(self) -> Dict[str, Any]:
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