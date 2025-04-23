# Combine file and media reader
from .extractor import FileExtractor
from .utils import parse_multiple_files
__all__=["FileExtractor","parse_multiple_files"]
# document = parse_multiple_files(
#         str(file_path),
#         extractor=file_extractor.get_extractor_for_file(file_path),
#     ) text, metadata