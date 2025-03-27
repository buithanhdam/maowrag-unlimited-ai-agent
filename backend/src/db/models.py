# src/database/models.py
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Enum, Boolean, Float, create_engine, Index
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func
import enum
from src.config import Settings

settings = Settings()
Base = declarative_base()

class CommunicationRole(enum.Enum):
    MANAGER = "manager"
    MEMBER = "member"

class RoleType(enum.Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

class AgentType(enum.Enum):
    REACT = "react"
    REFLECTION = "reflection"
    # Add more agent types as needed

class LLMProvider(enum.Enum):
    OPENAI = "openai"
    GEMINI = "gemini"
    ANTHROPIC = "anthropic"

class MessageType(enum.Enum):
    COMMUNICATION = "communication"
    AGENT = "agent"

class DocumentStatus(enum.Enum):
    UPLOADED = "uploaded"
    PENDING = "pending"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"

class ToolType(enum.Enum):
    SEARCH = "search"
    CALCULATOR = "calculator"
    CODE_INTERPRETER = "code_interpreter"
    WEB_BROWSER = "web_browser"
    FILE_OPERATION = "file_operation"
    API_CALL = "api_call"
    CUSTOM = "custom"

class RAGType(enum.Enum):
    NORMAL = "normal_rag"
    HYBRID = "hybrid_rag"
    CONTEXTUAL = "contextual_rag"
    FUSION = "fusion_rag"
    HYDE = "hyde_rag"
    NAIVE = "naive_rag"
class Agent(Base):
    __tablename__ = "agents"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    foundation_id = Column(Integer, ForeignKey("llm_foundations.id"))
    config_id = Column(Integer, ForeignKey("llm_configs.id"))
    name = Column(String(100))
    agent_type = Column(Enum(AgentType))
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_active = Column(Boolean, default=True)
    configuration = Column(JSON)  # Agent-specific configuration
    
    # Relationships
    llm_foundations = relationship("LLMFoundation", back_populates="agents")
    llm_configs = relationship("LLMConfig", back_populates="agents")
    conversations = relationship("Conversation", secondary="agent_conversations", back_populates="agents")
    communications = relationship("Communication", secondary="communication_agent_members", back_populates="agents")
    tools = relationship("Tool", secondary="agent_tools", back_populates="agents")
    knowledge_bases = relationship("KnowledgeBase", secondary="agent_knowledge_bases", back_populates="agents")

class Communication(Base):
    __tablename__ = "communications"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100))
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_active = Column(Boolean, default=True)
    configuration = Column(JSON)  # Store communication-specific configuration
    
    # Relationships
    agents = relationship("Agent", secondary="communication_agent_members", back_populates="communications")
    conversations = relationship("Conversation", secondary="communication_conversations", back_populates="communications")

class CommunicationAgentMember(Base):
    __tablename__ = "communication_agent_members"
    
    communication_id = Column(Integer, ForeignKey("communications.id"), primary_key=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), primary_key=True)
    role = Column(Enum(CommunicationRole))  # e.g., "leader", "member"
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class CommunicationConversation(Base):
    __tablename__ = "communication_conversations"
    
    communication_id = Column(Integer, ForeignKey("communications.id"), primary_key=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), primary_key=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class LLMFoundation(Base):
    __tablename__ = "llm_foundations"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    provider = Column(Enum(LLMProvider), nullable=False)
    model_name = Column(String(100), nullable=False)
    model_id = Column(String(100), nullable=False, unique=True)
    description = Column(Text)
    capabilities = Column(JSON)  # Store model capabilities
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_active = Column(Boolean, default=True)
    
    # Relationships
    llm_configs = relationship("LLMConfig", back_populates="llm_foundations")
    agents = relationship("Agent", back_populates="llm_foundations")

class LLMConfig(Base):
    __tablename__ = "llm_configs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    foundation_id = Column(Integer, ForeignKey("llm_foundations.id"))
    name = Column(String(100))
    temperature = Column(Float)
    max_tokens = Column(Integer)
    top_p = Column(Float, nullable=True)
    frequency_penalty = Column(Float, nullable=True)
    presence_penalty = Column(Float, nullable=True)
    system_prompt = Column(Text)
    stop_sequences = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    llm_foundations = relationship("LLMFoundation", back_populates="llm_configs")
    agents = relationship("Agent", back_populates="llm_configs")

class Conversation(Base):
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_active = Column(Boolean, default=True)
    
    # Relationships
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")
    agents = relationship("Agent", secondary="agent_conversations", back_populates="conversations")
    communications = relationship("Communication", secondary="communication_conversations", back_populates="conversations")

class Message(Base):
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"))
    role = Column(Enum(RoleType))
    content = Column(Text)
    type = Column(Enum(MessageType))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    # Relationships
    conversation = relationship("Conversation", back_populates="messages")

class AgentConversation(Base):
    __tablename__ = "agent_conversations"
    
    agent_id = Column(Integer, ForeignKey("agents.id"), primary_key=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), primary_key=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class RAGConfig(Base):
    __tablename__ = "rag_configs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    rag_type = Column(Enum(RAGType))
    embedding_model = Column(String(100))
    similarity_type = Column(String(50))
    chunk_size = Column(Integer)
    chunk_overlap = Column(Integer)
    configuration = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_active = Column(Boolean, default=True)
    
    # Relationships
    knowledge_bases = relationship("KnowledgeBase", back_populates="rag_config")

class KnowledgeBase(Base):
    __tablename__ = "knowledge_bases"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    rag_config_id = Column(Integer, ForeignKey("rag_configs.id"))
    name = Column(String(100), nullable=False)
    specific_id = Column(String(200))
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_active = Column(Boolean, default=True)
    extra_info = Column(JSON)
    
    # Relationships
    documents = relationship("Document", back_populates="knowledge_base")
    rag_config = relationship("RAGConfig", back_populates="knowledge_bases")
    agents = relationship("Agent", secondary="agent_knowledge_bases", back_populates="knowledge_bases")

class Document(Base):
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    knowledge_base_id = Column(Integer, ForeignKey("knowledge_bases.id"))
    name = Column(String(255), nullable=False)
    source = Column(String(255))
    extension = Column(String(50))
    original_content = Column(Text, nullable=True)
    processed_content = Column(Text, nullable=True)
    status = Column(Enum(DocumentStatus), default=DocumentStatus.PENDING)
    extra_info = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    knowledge_base = relationship("KnowledgeBase", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")

class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey("documents.id"))
    content = Column(Text, nullable=False)
    chunk_index = Column(Integer)
    dense_embedding = Column(JSON, nullable=True)
    sparse_embedding = Column(JSON, nullable=True)
    extra_info = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    document = relationship("Document", back_populates="chunks")

class Tool(Base):
    __tablename__ = "tools"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    tool_type = Column(Enum(ToolType))
    configuration = Column(JSON)
    parameters = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_active = Column(Boolean, default=True)
    
    # Relationships
    agents = relationship("Agent", secondary="agent_tools", back_populates="tools")

# Association tables
class AgentKnowledgeBase(Base):
    __tablename__ = "agent_knowledge_bases"
    
    agent_id = Column(Integer, ForeignKey("agents.id"), primary_key=True)
    knowledge_base_id = Column(Integer, ForeignKey("knowledge_bases.id"), primary_key=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class AgentTool(Base):
    __tablename__ = "agent_tools"
    
    agent_id = Column(Integer, ForeignKey("agents.id"), primary_key=True)
    tool_id = Column(Integer, ForeignKey("tools.id"), primary_key=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

SQLALCHEMY_DATABASE_URL = f"mysql+pymysql://{settings.MYSQL_USER}:{settings.MYSQL_PASSWORD}@{settings.MYSQL_HOST}:{settings.MYSQL_PORT}/{settings.MYSQL_DB}"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
Base.metadata.create_all(engine)