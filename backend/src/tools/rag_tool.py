from llama_index.core.tools import FunctionTool
from src.db.models import KnowledgeBase,RAGConfig
from src.config import global_config
from src.enums import LLMProviderType
from typing import List
from src.logger import get_formatted_logger
logger = get_formatted_logger(__file__)

RAG_DESCRIPTION = """Search through business knowledge base return relevant business information"""
class RAGTool:
    @staticmethod
    def create_rag_tool_for_knowledge_base(knowledge_base: KnowledgeBase) -> FunctionTool:
        """Create a RAG function tool for a specific knowledge base"""
        
        # Get RAG config from knowledge base
        rag_config:RAGConfig = knowledge_base.rag_config
        rag_type = rag_config.rag_type
        
        # Create a function that will search specifically in this knowledge base
        def search_kb(query: str, limit: int = 5) -> str:
            """
            Search through knowledge base and return relevant information
            
            Args:
                query: Search query
                limit: Maximum number of results to return
            """
            from src.rag.rag_manager import RAGManager
            
            rag = RAGManager.create_rag(
                rag_type=rag_type,
                vector_db_url=global_config.QDRANT_URL,
                llm_type= LLMProviderType.GOOGLE,
                chunk_size=rag_config.chunk_size,
                chunk_overlap=rag_config.chunk_overlap,
            )
            
            # Use knowledge_base.specific_id as collection name or other identifier
            collection_name = knowledge_base.specific_id
            
            return rag.search(
                query=query, 
                collection_name=collection_name,
                limit=limit
            )
        logger.info(f"Created RAG tool for knowledge base: {knowledge_base.name} with RAG type: {rag_type}")
        # Create function tool with proper name and description
        return FunctionTool.from_defaults(
            name=f"search_{knowledge_base.name.lower().replace(' ', '_')}",
            description=f"Search through the '{knowledge_base.name}' knowledge base: {knowledge_base.description}",
            fn=search_kb
        )
    
    @staticmethod
    def create_rag_tools_for_agent(knowledge_bases: List[KnowledgeBase]) -> List[FunctionTool]:
        """Create RAG tools for all knowledge bases associated with an agent"""
        return [
            RAGTool.create_rag_tool_for_knowledge_base(kb) 
            for kb in knowledge_bases
        ]