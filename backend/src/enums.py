import enum
class CommunicationRoleType(enum.Enum):
    MANAGER = "manager"
    MEMBER = "member"
class MultiAgentType(enum.Enum):
    ROUTER = "router"
    PARALLEL = "parallel"
    
class RoleType(enum.Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

class AgentType(enum.Enum):
    REACT = "react"
    PLANNING = "planning"
    REFLECTION = "reflection"
    # Add more agent types as needed

class LLMProviderType(enum.Enum):
    OPENAI = "openai"
    GOOGLE = "google"
    ANTHROPIC = "anthropic"

class MessageType(enum.Enum):
    COMMUNICATION = "communication"
    AGENT = "agent"

class TaskType(enum.Enum):
    UPLOAD_DOCUMENT = "upload"
    PARSE_DOCUMENT = "parse_document"

class TaskStatusType(enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class DocumentStatusType(enum.Enum):
    PENDING = "pending"
    UPLOADING = "uploading"
    UPLOADED = "uploaded"
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
    
class SearchEngineType(enum.Enum):
    TAVILY = "Tavily"
    ARXIV = "ArXiv"
    WIKI = "Wikipedia"
    
class RAGType(enum.Enum):
    NORMAL = "normal_rag"
    HYBRID = "hybrid_rag"
    CONTEXTUAL = "contextual_rag"
    FUSION = "fusion_rag"
    HYDE = "hyde_rag"
    NAIVE = "naive_rag"