# config.py
import enum
from pydantic import BaseModel
from pydantic_settings import BaseSettings
import os
import dotenv

dotenv.load_dotenv()

from src.prompt import LLM_SYSTEM_PROMPT

class RAGType(enum.Enum):
    NORMAL = "normal_rag"
    HYBRID = "hybrid_rag"
    CONTEXTUAL = "contextual_rag"
    FUSION = "fusion_rag"
    HYDE = "hyde_rag"
    NAIVE = "naive_rag"

class ReaderConfig(BaseModel):
    """Configuration for DoclingReader"""
    num_threads: int = 4
    image_resolution_scale: float = 2.0
    enable_ocr: bool = True
    enable_tables: bool = True
    max_pages: int = 100
    max_file_size: int = 20971520  # 20MB
    supported_formats: list[str] = ['.pdf']  # For future extension

class RAGConfig(BaseModel):
    """Configuration for RAG Manager"""
    chunk_size: int = 512
    chunk_overlap: int = 64
    default_collection: str = "documents"
    max_results: int = 5
    similarity_threshold: float = 0.7

class LLMConfig(BaseModel):
    """Configuration for Language Models"""
    api_key: str
    model_name: str
    model_id: str
    temperature: float = 0.7
    max_tokens: int = 2048
    system_prompt: str = "You are a helpful assistant."

class QdrantPayload(BaseModel):
    """Payload for vectors in Qdrant"""
    document_id: str
    text: str
    vector_id: str

class Settings(BaseSettings):
    """Main application settings"""
    QDRANT_URL: str = os.getenv('QDRANT_URL', "http://qdrant:6333")
    GOOGLE_API_KEY: str = os.getenv('GOOGLE_API_KEY', '')
    BACKEND_API_URL: str = os.getenv('BACKEND_API_URL', 'http://localhost:8000')
    MYSQL_USER : str=os.getenv('MYSQL_USER', 'user')
    MYSQL_PASSWORD : str=os.getenv('MYSQL_PASSWORD', '1')
    MYSQL_ROOT_PASSWORD : str=os.getenv('MYSQL_ROOT_PASSWORD', '1')
    MYSQL_HOST : str=os.getenv('MYSQL_HOST', 'mysql')
    MYSQL_PORT : str=os.getenv('MYSQL_PORT', '3306')
    MYSQL_DB : str=os.getenv('MYSQL_DB', 'ragagent')
    MYSQL_ALLOW_EMPTY_PASSWORD: str=os.getenv('MYSQL_ALLOW_EMPTY_PASSWORD', 'yes')
    
    # Component configurations
    READER_CONFIG: ReaderConfig = ReaderConfig()
    RAG_CONFIG: RAGConfig = RAGConfig()
    
    # LLM configurations
    OPENAI_CONFIG: LLMConfig = LLMConfig(
        api_key=os.getenv('OPENAI_API_KEY', ''),
        model_name="GPT",
        model_id="gpt-3.5-turbo",
        temperature=0.7,
        max_tokens=2048,
        system_prompt=LLM_SYSTEM_PROMPT
    )
    
    GEMINI_CONFIG: LLMConfig = LLMConfig(
        api_key=os.getenv('GOOGLE_API_KEY', ''),
        model_name="Gemini",
        model_id="models/gemini-1.5-flash",
        temperature=0.8,
        max_tokens=2048,
        system_prompt=LLM_SYSTEM_PROMPT
    )
    
    CLAUDE_CONFIG: LLMConfig = LLMConfig(
        api_key=os.getenv('ANTHROPIC_API_KEY', ''),
        model_name="Claude",
        model_id="claude-3-haiku-20240307",
        temperature=0.7,
        max_tokens=4000,
        system_prompt=LLM_SYSTEM_PROMPT
    )
    
    class Config:
        env_file = ".env"