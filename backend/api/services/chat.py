from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException
from typing import List, Optional, Dict, Any
from datetime import datetime
from llama_index.core.llms import ChatMessage
from src.db.models import KnowledgeBase, RoleType,Conversation, Message,AgentType, AgentConversation, Agent, LLMConfig, LLMProvider, Communication, CommunicationConversation, MessageType
from api.schemas.chat import (
    CommunicationConversationCreate, ConversationCreate, ConversationUpdate, ConversationResponse,
    MessageCreate, MessageResponse
)
from src.agents import ReActAgent, AgentOptions, ReflectionAgent, ManagerAgent, BaseAgent
from src.llm import UnifiedLLM # Import other LLM providers as needed
from src.tools.tool_manager import tool_manager

class ChatService:
    @staticmethod
    def create_llm_instance(llm_config: LLMConfig):
        """Create LLM instance based on provider and config"""
        provider = llm_config.llm_foundations.provider
        if provider == LLMProvider.GEMINI:
            return UnifiedLLM(
                model_name= LLMProvider.GEMINI.value,
                model_id= llm_config.llm_foundations.model_id,
                temperature= llm_config.temperature,
                max_tokens= llm_config.max_tokens,
                system_prompt= llm_config.system_prompt
            )
        # Add other providers as needed
        raise HTTPException(status_code=400, detail=f"Unsupported LLM provider: {provider}")

    @staticmethod
    async def setup_agent(db: Session, agent_id: int) -> BaseAgent:
        """Setup agent with specified LLM config"""
        # Get agent and config
        agent = db.query(Agent).filter(Agent.id == agent_id).first()
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        # setup agent with kb rag config setup multi tool
        kbs : List[KnowledgeBase] = agent.knowledge_bases    
        from src.tools.rag_tool import RAGToolManager
        rag_tools = RAGToolManager.create_rag_tools_for_agent(kbs)
        simple_tools = tool_manager.get_all_tools()
        
        tools = rag_tools + simple_tools

        llm_config = db.query(LLMConfig).filter(LLMConfig.id == agent.config_id).first()
        if not llm_config:
            raise HTTPException(status_code=404, detail="LLM config not found")

        # Create LLM instance
        llm = ChatService.create_llm_instance(llm_config)

        # Create and return agent
        if agent.agent_type == AgentType.REFLECTION:
            return ReflectionAgent(
                llm=llm,
                options=AgentOptions(
                    id=f"{"".join(str(agent.name).split(" ")).lower()}{agent.id}",
                    name=agent.name,
                    description=agent.description
                ),
                system_prompt=llm_config.system_prompt,
                tools=tools
            )
        else:
            return ReActAgent(
                llm=llm,
                options=AgentOptions(
                    id=f"{"".join(str(agent.name).split(" ")).lower()}{agent.id}",
                    name=agent.name,
                    description=agent.description
                ),
                system_prompt=llm_config.system_prompt,
                tools=tools
            )
    @staticmethod
    async def setup_communication(db: Session, communication_id: int) -> BaseAgent:
        """Setup agent communication with specified multiple agents"""
        # Get agent and config
        communication = db.query(Communication).filter(Communication.id == communication_id).first()
        if not communication:
            raise HTTPException(status_code=404, detail="Communication not found")
        agents : List[Agent] = communication.agents
        system_prompt="You are a intelligent matcher agent"
        manager_agent = ManagerAgent(
            llm=UnifiedLLM(system_prompt=system_prompt),
            options=AgentOptions(
                id="manager",
                name="Manager",
                description="Routes requests to specialized agents"
            ),
            system_prompt=system_prompt,
            validation_threshold=0.7
        )
        for agent in agents:
            manager_agent.register_agent(await ChatService.setup_agent(db, agent.id))

        # Create and return agent
        return manager_agent
    @staticmethod
    async def create_conversation(db: Session, conv_create: ConversationCreate) -> Conversation:
        conversation = Conversation(
            title=conv_create.title
        )
        db.add(conversation)
        db.flush()

        agent_conv = AgentConversation(
            agent_id=conv_create.agent_id,
            conversation_id=conversation.id
        )
        db.add(agent_conv)

        try:
            db.commit()
            db.refresh(conversation)
            return conversation
        except IntegrityError:
            db.rollback()
            raise HTTPException(status_code=400, detail="Invalid agent IDs")
    @staticmethod
    async def create_communication_conversation(
        db: Session,
        conv_create: CommunicationConversationCreate
    ) -> Conversation:
        # Verify communication exists and is active
        communication = db.query(Communication).filter(
            Communication.id == conv_create.communication_id,
            Communication.is_active == True
        ).first()
        if not communication:
            raise HTTPException(status_code=404, detail="Communication not found")
        
        # Create conversation
        conversation = Conversation(title=conv_create.title)
        db.add(conversation)
        db.flush()

        # Link conversation to communication
        comm_conv = CommunicationConversation(
            communication_id=communication.id,
            conversation_id=conversation.id
        )
        db.add(comm_conv)

        # Add all communication agents to conversation
        # for agent in communication.agents:
        #     agent_conv = AgentConversation(
        #         agent_id=agent.id,
        #         conversation_id=conversation.id
        #     )
        #     db.add(agent_conv)

        db.commit()
        db.refresh(conversation)
        return conversation
    @staticmethod
    async def get_conversation(db: Session, conversation_id: int) -> Optional[Conversation]:
        conversation = db.query(Conversation)\
            .filter(Conversation.id == conversation_id)\
            .first()
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return conversation

    @staticmethod
    async def get_all_conversations(db: Session, skip: int = 0, limit: int = 100, agent_id: Optional[int] = None) -> List[Conversation]:
        query = db.query(Conversation)
        if agent_id:
            query = query.join(AgentConversation)\
                        .filter(AgentConversation.agent_id == agent_id)
        return query.offset(skip).limit(limit).all()
    @staticmethod
    async def get_all_communication_conversations(db: Session, skip: int = 0, limit: int = 100, communication_id: Optional[int] = None) -> List[Conversation]:
        query = db.query(Conversation)
        if communication_id:
            query = query.join(CommunicationConversation)\
                        .filter(CommunicationConversation.communication_id == communication_id)
        return query.offset(skip).limit(limit).all()

    @staticmethod
    async def update_conversation(db: Session, conversation_id: int, conv_update: ConversationUpdate) -> Conversation:
        conversation = await ChatService.get_conversation(db, conversation_id)
        update_data = conv_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(conversation, field, value)
        db.commit()
        db.refresh(conversation)
        return conversation

    @staticmethod
    async def delete_conversation(db: Session, conversation_id: int) -> bool:
        conversation = await ChatService.get_conversation(db, conversation_id)
        db.delete(conversation)
        db.commit()
        return True

    @staticmethod
    async def chat(db: Session, message: MessageCreate) -> Message:
        """Add a message to the conversation, optionally using an agent to generate a response."""
        # If the message is from a user and an agent is specified, generate a response
        db_message = Message(conversation_id=message.conversation_id,
                role=message.role,
                content=message.content,
                type=message.type)
        db.add(db_message)
        
        if message.role == "user":
            if message.type == MessageType.AGENT:
                agent_conversation = db.query(AgentConversation)\
                    .filter(AgentConversation.conversation_id == message.conversation_id)\
                    .first()
                    
                agent = await ChatService.setup_agent(db, agent_conversation.agent_id)   
            else:
                communication_conversation = db.query(CommunicationConversation)\
                    .filter(CommunicationConversation.conversation_id == message.conversation_id)\
                    .first()
                    
                agent = await ChatService.setup_communication(db, communication_conversation.communication_id)
            
            history=db.query(Message).filter(
                Message.conversation_id == message.conversation_id
                ).order_by(Message.created_at.desc()).limit(5)
            
            response = await agent.achat(
                    query=message.content,
                    verbose=True,
                    chat_history=[ChatMessage(role= "user" if m.role == RoleType.USER else "assistant", content=m.content) for m in history]
            )     
            
            print(response)
            
            # Add the agent's response as a new message
            agent_message = Message(
                conversation_id=message.conversation_id,
                role="assistant",
                content=response,
                type=MessageType.AGENT
            )
            
            db.add(agent_message)
            db.commit()
            db.refresh(agent_message)
            
            return agent_message
        raise HTTPException(status_code=500, detail="Message should be from user role")