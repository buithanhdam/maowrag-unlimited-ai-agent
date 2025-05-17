from itertools import islice
import re
from typing import Any, List
import tiktoken
from llama_index.core.node_parser import (
    SentenceSplitter,
    SemanticSplitterNodeParser,
)
from llama_index.core import Document
from llama_index.core.constants import DEFAULT_CHUNK_SIZE
from llama_index.embeddings.openai import OpenAIEmbedding
from src.config import global_config
from src.llm.embed_model._gemini_embed_model import GeminiEmbedding
def sanitize_json_string(s: str) -> str:
    # Loại bỏ ký tự control: ASCII từ 0 đến 31, ngoại trừ tab (09), newline (0A), carriage return (0D)
    return re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', s)
def clean_json_response(response: str) -> str:
    """Clean and extract JSON from LLM response"""
    # Remove any markdown code block markers
    response = response.replace("```json", "").replace("```", "").strip()
        
    # Find the first '{' and last '}'
    start = response.find('{')
    end = response.rfind('}')
        
    if start == -1 or end == -1:
        raise ValueError("No valid JSON object found in response")   
    # Extract just the JSON object
    return response[start:end + 1]
def batch_iterable(iterable, batch_size):
    """Yield successive batch_size-sized chunks from iterable."""
    it = iter(iterable)
    while True:
        batch = list(islice(it, batch_size))
        if not batch:
            break
        yield batch
def count_tokens_from_string(string: str, encoding_name: str = "cl100k_base") -> int:
    """Returns the number of tokens in a text string."""
    try:
        encoding = tiktoken.get_encoding(encoding_name)
        num_tokens = len(encoding.encode(string))
        return num_tokens
    except Exception as e:
        # Fallback: rough estimate of 4 characters per token
        return len(string)
def text_splitter(
    text: Any,
    chunk_size : int =DEFAULT_CHUNK_SIZE,
    active: str = "sentence",
    embed_model: str = "google"
) -> List[str]:
    """Splitter doc text to chunks

    Args:
        text (Any): document text
        chunk_size (int, optional): chunk_size to split. Defaults to DEFAULT_CHUNK_SIZE.
        active (str, optional): splitter type active. Defaults to "sentence" or "semantic".
        embed_model (str, optional): embed model for sematic splitter. Defaults to "gemini" or "openai".

    Returns:
        List[str]: list of doc chunk
    """
    text = str(text)
    doc = Document(text=text,doc_id ="1",extra_info={})
    if active == "semantic":
        if embed_model == "openai":
            model =OpenAIEmbedding(
                api_key=global_config.OPENAI_CONFIG.api_key,
            )
        else:
            model =GeminiEmbedding(
                api_key=global_config.GEMINI_CONFIG.api_key,
                model_name="models/text-embedding-004",
                output_dimensionality=768
            )
        splitter = SemanticSplitterNodeParser(
            buffer_size=1, breakpoint_percentile_threshold=95, embed_model=model
        )    
    else:
        splitter = SentenceSplitter(chunk_size)
    nodes =splitter.get_nodes_from_documents([doc])
    results = [node.get_content() for node in nodes]
    return results
    