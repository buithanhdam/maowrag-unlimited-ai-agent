# config.py
import enum
from pydantic import BaseModel
from pydantic_settings import BaseSettings
import os
import dotenv

dotenv.load_dotenv()

from src.prompt import LLM_SYSTEM_PROMPT
from src.enums import LLMProviderType

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
    llm_provider: LLMProviderType
    model_id: str
    temperature: float = 0.7
    max_tokens: int = 2048
    system_prompt: str = "You are a helpful assistant."

class QdrantPayload(BaseModel):
    """Payload for vectors in Qdrant"""
    document_id: str | int
    text: str
    vector_id: str
    
class AWSConfig(BaseModel):
    """Configuration for AWS S3"""
    access_key_id: str
    secret_access_key: str
    region_name: str
    storage_type: str
    endpoint_url: str

class Settings:
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
    
    AWS_ACCESS_KEY_ID:str=os.getenv('AWS_ACCESS_KEY_ID', ''),
    AWS_SECRET_ACCESS_KEY:str=os.getenv('AWS_SECRET_ACCESS_KEY', ''),
    AWS_REGION_NAME:str=os.getenv('AWS_REGION_NAME', ''),
    AWS_STORAGE_TYPE:str=os.getenv('AWS_STORAGE_TYPE', ''),
    AWS_ENDPOINT_URL:str="https://s3.ap-southeast-2.amazonaws.com"
    
    TAVILY_API_KEY:str = os.getenv('TAVILY_API_KEY', '')
    # LLM configurations
    OPENAI_CONFIG: LLMConfig = LLMConfig(
        api_key=os.getenv('OPENAI_API_KEY', ''),
        llm_provider=LLMProviderType.OPENAI,
        model_id="gpt-3.5-turbo",
        temperature=0.7,
        max_tokens=2048,
        system_prompt=LLM_SYSTEM_PROMPT
    )
    
    GEMINI_CONFIG: LLMConfig = LLMConfig(
        api_key=os.getenv('GOOGLE_API_KEY', ''),
        llm_provider=LLMProviderType.GOOGLE,
        model_id="models/gemini-2.0-flash",
        temperature=0.8,
        max_tokens=2048,
        system_prompt=LLM_SYSTEM_PROMPT
    )
    
    CLAUDE_CONFIG: LLMConfig = LLMConfig(
        api_key=os.getenv('ANTHROPIC_API_KEY', ''),
        llm_provider=LLMProviderType.ANTHROPIC,
        model_id="claude-3-haiku-20240307",
        temperature=0.7,
        max_tokens=4000,
        system_prompt=LLM_SYSTEM_PROMPT
    )
    
    class Config:
        env_file = ".env"
global_config = Settings()
def get_llm_config(llm_type: LLMProviderType) -> LLMConfig:
    if llm_type == LLMProviderType.OPENAI:
        return global_config.OPENAI_CONFIG
    elif llm_type == LLMProviderType.GOOGLE:
        return global_config.GEMINI_CONFIG
    elif llm_type == LLMProviderType.ANTHROPIC:
        return global_config.CLAUDE_CONFIG
    else:
        raise ValueError(f"Unsupported LLM type: {llm_type}")