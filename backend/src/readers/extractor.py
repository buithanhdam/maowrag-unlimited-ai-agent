from pathlib import Path
from .kotaemon import (
    JSONReader,
    PandasCSVReader,
    MarkdownReader,
    IPYNBReader,
    MboxReader,
    XMLReader,
    RTFReader,DocxReader,TxtReader,ExcelReader,HtmlReader,MhtmlReader,PDFReader,PDFThumbnailReader,PandasExcelReader)
from .markitdown import MarkItDown
from google import genai
from src.config import global_config

def get_extractor():
    md = MarkItDown(enable_plugins=False)
    ocr_md = MarkItDown(
        llm_client=genai.Client(api_key=global_config.GEMINI_CONFIG.api_key),
        llm_model=global_config.GEMINI_CONFIG.model_id.split("/")[1]
    )
    return {
        ".pdf": PDFThumbnailReader(),
        ".docx": DocxReader(),
        ".html": HtmlReader(),
        ".csv": md,
        ".xlsx": md,
        ".xls":md,
        ".json": JSONReader(),
        ".txt": TxtReader(),
        # ".pptx": PptxReader(),
        ".md": MarkdownReader(),
        ".ipynb": IPYNBReader(),
        ".mbox": MboxReader(),
        ".xml": XMLReader(),
        ".rtf": RTFReader(),
        ".wav":md,
        ".mp3":md,
        ".m4a":md,
        ".mp4":md,
        ".jpg":ocr_md,
        ".jpeg":ocr_md,
        ".png":ocr_md
    }
    
class FileExtractor:
    def __init__(self) -> None:
        self.extractor = get_extractor()

    def get_extractor_for_file(self, file_path: str | Path) -> dict[str, str]:
        file_suffix = Path(file_path).suffix
        return {
            file_suffix: self.extractor[file_suffix],
        }