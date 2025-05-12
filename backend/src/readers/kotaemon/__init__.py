# Apply From Kotaemon
from llama_index.readers.json import JSONReader
from llama_index.readers.file import (
    PandasCSVReader,
    # PptxReader,  # noqa
    UnstructuredReader,
    MarkdownReader,
    IPYNBReader,
    MboxReader,
    XMLReader,
    RTFReader
)
from src.readers.kotaemon.loaders import (DocxReader,TxtReader,ExcelReader,HtmlReader,MhtmlReader,PDFReader,PDFThumbnailReader,PandasExcelReader)
__all__=[
    "JSONReader", "PandasCSVReader",
    "MarkdownReader",
    "IPYNBReader",
    "MboxReader",
    "XMLReader",
    "RTFReader",
    "DocxReader","TxtReader","ExcelReader","HtmlReader","MhtmlReader","PDFReader","PDFThumbnailReader","PandasExcelReader"
    ]