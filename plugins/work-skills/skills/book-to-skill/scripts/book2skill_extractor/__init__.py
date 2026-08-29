"""Self-contained extraction backend bundled with the Book2Skill agent skill."""

from .api import ExtractionError, ExtractionResult, extract_book

__all__ = ["ExtractionError", "ExtractionResult", "extract_book"]
