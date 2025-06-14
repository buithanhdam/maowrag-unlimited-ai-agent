from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey,
    JSON,
    Enum,
    Boolean,
    Float,
    create_engine,
    Index,
)
from sqlalchemy.orm import relationship, declarative_base, sessionmaker, Session
from sqlalchemy.sql import func
from src.enums import (
    AgentType,
    CommunicationRoleType,
    LLMProviderType,
    RoleType,
    MessageType,
    DocumentStatusType,
    ToolType,
    RAGType,TaskStatusType,MultiAgentType,TaskType
)
from src.config import global_config
from src.logger import get_formatted_logger

logger = get_formatted_logger(__file__)
Base = declarative_base()


class Agent(Base):
    __tablename__ = "agents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    uuid = Column(String(200), unique=True, default=func.uuid4())
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
    conversations = relationship(
        "Conversation", secondary="agent_conversations", back_populates="agents"
    )
    communications = relationship(
        "Communication",
        secondary="communication_agent_members",
        back_populates="agents",
    )
    tools = relationship("Tool", secondary="agent_tools", back_populates="agents")
    knowledge_bases = relationship(
        "KnowledgeBase", secondary="agent_knowledge_bases", back_populates="agents"
    )


class Communication(Base):
    __tablename__ = "communications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    uuid = Column(String(200), unique=True, default=func.uuid4())
    name = Column(String(100))
    description = Column(Text)
    type = Column(Enum(MultiAgentType), default=MultiAgentType.ROUTER)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_active = Column(Boolean, default=True)
    configuration = Column(JSON)  # Store communication-specific configuration

    # Relationships
    agents = relationship(
        "Agent",
        secondary="communication_agent_members",
        back_populates="communications",
    )
    conversations = relationship(
        "Conversation",
        secondary="communication_conversations",
        back_populates="communications",
    )


class CommunicationAgentMember(Base):
    __tablename__ = "communication_agent_members"

    communication_id = Column(
        Integer, ForeignKey("communications.id"), primary_key=True
    )
    agent_id = Column(Integer, ForeignKey("agents.id"), primary_key=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class CommunicationConversation(Base):
    __tablename__ = "communication_conversations"

    communication_id = Column(
        Integer, ForeignKey("communications.id"), primary_key=True
    )
    conversation_id = Column(Integer, ForeignKey("conversations.id"), primary_key=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class LLMFoundation(Base):
    __tablename__ = "llm_foundations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    uuid = Column(String(200), unique=True, default=func.uuid4())
    provider = Column(Enum(LLMProviderType), nullable=False)
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
    uuid = Column(String(200), unique=True, default=func.uuid4())
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
    uuid = Column(String(200), unique=True, default=func.uuid4())
    title = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_active = Column(Boolean, default=True)

    # Relationships
    messages = relationship(
        "Message", back_populates="conversation", cascade="all, delete-orphan"
    )
    agents = relationship(
        "Agent", secondary="agent_conversations", back_populates="conversations"
    )
    communications = relationship(
        "Communication",
        secondary="communication_conversations",
        back_populates="conversations",
    )


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    uuid = Column(String(200), unique=True, default=func.uuid4())
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
    uuid = Column(String(200), unique=True, default=func.uuid4())
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
    uuid = Column(String(200), unique=True, default=func.uuid4())
    rag_config_id = Column(Integer, ForeignKey("rag_configs.id"))
    name = Column(String(100), nullable=False)
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_active = Column(Boolean, default=True)
    extra_info = Column(JSON)

    # Relationships
    documents = relationship("Document", back_populates="knowledge_base")
    rag_config = relationship("RAGConfig", back_populates="knowledge_bases")
    agents = relationship(
        "Agent", secondary="agent_knowledge_bases", back_populates="knowledge_bases"
    )

class Task(Base):
    __tablename__ = "tasks"
    id = Column(String(200), unique=True,primary_key=True, default=func.uuid4())
    name = Column(String(50))
    retry = Column(Integer)
    type = Column(Enum(TaskType), default=TaskType.UPLOAD_DOCUMENT)
    status = Column(Enum(TaskStatusType), default=TaskStatusType.PENDING)
    extra_info = Column(JSON)
    message = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    

class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    uuid = Column(String(200), unique=True, default=func.uuid4())
    knowledge_base_id = Column(Integer, ForeignKey("knowledge_bases.id"))
    task_id = Column(String(255))
    name = Column(String(255), nullable=False)
    source = Column(String(255))
    extension = Column(String(50))
    original_content = Column(Text, nullable=True)
    processed_content = Column(Text, nullable=True)
    status = Column(Enum(DocumentStatusType), default=DocumentStatusType.PENDING)
    tokens = Column(Integer)
    extra_info = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    knowledge_base = relationship("KnowledgeBase", back_populates="documents")
    chunks = relationship(
        "DocumentChunk", back_populates="document", cascade="all, delete-orphan"
    )

class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    uuid = Column(String(200), unique=True, default=func.uuid4())
    document_id = Column(Integer, ForeignKey("documents.id"))
    content = Column(Text, nullable=False)
    chunk_index = Column(Integer)
    dense_embedding = Column(JSON, nullable=True)
    sparse_embedding = Column(JSON, nullable=True)
    tokens = Column(Integer)
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
    knowledge_base_id = Column(
        Integer, ForeignKey("knowledge_bases.id"), primary_key=True
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class AgentTool(Base):
    __tablename__ = "agent_tools"

    agent_id = Column(Integer, ForeignKey("agents.id"), primary_key=True)
    tool_id = Column(Integer, ForeignKey("tools.id"), primary_key=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


SQLALCHEMY_DATABASE_URL = f"""postgresql+psycopg2://{global_config.DB_USER}:{global_config.DB_PASSWORD}@{global_config.DB_HOST}:{global_config.DB_PORT}/{global_config.DB_NAME}"""
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def create_db_tables():
    Base.metadata.create_all(engine)
    logger.info("✅ Database tables created successfully!")


def initialize_all_databases():
    """Initialize all database tables for app architecture."""
    try:
        logger.info("🔄 Initializing database...")
        create_db_tables()
        logger.info("✅ All databases initialized successfully!")
        return True
    except Exception as e:
        logger.error(f"❌ Error initializing databases: {str(e)}")
        return False


def get_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_local_session() -> Session:
    """Function to get a database session for Celery tasks"""
    return SessionLocal()
