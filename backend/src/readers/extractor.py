from pathlib import Path
from .file import (
    JSONReader,
    PandasCSVReader,
    MarkdownReader,
    IPYNBReader,
    MboxReader,
    XMLReader,
    RTFReader,DocxReader,TxtReader,ExcelReader,HtmlReader,MhtmlReader,PDFReader,PDFThumbnailReader,PandasExcelReader)
from .media import MarkItDown

def get_extractor():
    md = MarkItDown(enable_plugins=False)
    return {
        ".pdf": PDFReader(),
        ".docx": DocxReader(),
        ".html": HtmlReader(),
        ".csv": PandasCSVReader(pandas_config=dict(on_bad_lines="skip")),
        ".xlsx": ExcelReader(),
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
        # ".jpg":md,
        # ".jpeg":md,
        # ".png":md
    }
    
class FileExtractor:
    def __init__(self) -> None:
        self.extractor = get_extractor()

    def get_extractor_for_file(self, file_path: str | Path) -> dict[str, str]:
        file_suffix = Path(file_path).suffix
        return {
            file_suffix: self.extractor[file_suffix],
        }