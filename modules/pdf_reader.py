"""
PDF Translator - PDF Reader Module

PDFファイルからテキストとレイアウト情報を抽出
"""

from typing import List, Optional, Tuple
import fitz  # PyMuPDF
from pathlib import Path

from modules.layout_manager import (
    BoundingBox, FontInfo, TextBlock, ImageInfo, PageData, DocumentData
)


class PDFReadError(Exception):
    """PDF読み込みエラー"""
    pass


class EncryptedPDFError(PDFReadError):
    """暗号化PDFエラー"""
    pass


class CorruptedPDFError(PDFReadError):
    """破損PDFエラー"""
    pass


class PDFReader:
    """PDF読み込みクラス"""

    def __init__(self):
        self._document: Optional[fitz.Document] = None
        self._file_path: Optional[str] = None
        self._block_id_counter: int = 0

    def open(self, file_path: str) -> DocumentData:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        try:
            self._document = fitz.open(file_path)
        except Exception as e:
            raise PDFReadError(f"Failed to open PDF: {e}")

        if self._document.is_encrypted:
            self._document.close()
            self._document = None
            raise EncryptedPDFError("PDF is encrypted")

        self._file_path = file_path
        metadata = self._document.metadata or {}

        doc_data = DocumentData(
            file_path=file_path,
            page_count=len(self._document),
            title=metadata.get("title"),
            author=metadata.get("author"),
        )

        for page_num in range(len(self._document)):
            page_data = self.get_page(page_num)
            doc_data.pages.append(page_data)

        return doc_data

    def close(self) -> None:
        if self._document:
            self._document.close()
            self._document = None

    def get_page(self, page_num: int) -> PageData:
        if self._document is None:
            raise PDFReadError("No document is open")

        page = self._document[page_num]
        rect = page.rect

        page_data = PageData(
            page_number=page_num,
            width=rect.width,
            height=rect.height,
            rotation=page.rotation,
        )

        page_data.text_blocks = self._extract_text_blocks(page)
        page_data.images = self._extract_images(page)

        return page_data

    def _extract_text_blocks(self, page: fitz.Page) -> List[TextBlock]:
        blocks = []
        page_dict = page.get_text("dict")

        for block in page_dict.get("blocks", []):
            if block.get("type") == 0:  # text block
                text_content = ""
                font_info = None
                line_count = 0

                for line in block.get("lines", []):
                    line_count += 1
                    for span in line.get("spans", []):
                        text_content += span.get("text", "")
                        if font_info is None:
                            color_int = span.get("color", 0)
                            r = (color_int >> 16) & 0xFF
                            g = (color_int >> 8) & 0xFF
                            b = color_int & 0xFF
                            font_info = FontInfo(
                                name=span.get("font", ""),
                                size=span.get("size", 12.0),
                                is_bold=bool(span.get("flags", 0) & 16),
                                is_italic=bool(span.get("flags", 0) & 2),
                                color=(r, g, b),
                            )

                if text_content.strip():
                    self._block_id_counter += 1
                    bbox = block.get("bbox", (0, 0, 0, 0))
                    blocks.append(TextBlock(
                        id=f"block_{self._block_id_counter:06d}",
                        text=text_content,
                        bbox=BoundingBox(x0=bbox[0], y0=bbox[1], x1=bbox[2], y1=bbox[3]),
                        font=font_info or FontInfo(name="", size=12.0),
                        line_count=line_count,
                    ))

        return blocks

    def _extract_images(self, page: fitz.Page) -> List[ImageInfo]:
        images = []
        image_list = page.get_images()

        for img_index, img in enumerate(image_list):
            xref = img[0]
            try:
                img_rect = page.get_image_rects(xref)
                if img_rect:
                    rect = img_rect[0]
                    self._block_id_counter += 1
                    images.append(ImageInfo(
                        id=f"img_{self._block_id_counter:06d}",
                        bbox=BoundingBox(x0=rect.x0, y0=rect.y0, x1=rect.x1, y1=rect.y1),
                        xref=xref,
                    ))
            except Exception:
                pass

        return images

    def detect_language(self, text: str) -> str:
        if not text:
            return "en"

        japanese_chars = 0
        total_chars = 0

        for char in text:
            if char.strip():
                total_chars += 1
                if "\u3040" <= char <= "\u309F":  # hiragana
                    japanese_chars += 1
                elif "\u30A0" <= char <= "\u30FF":  # katakana
                    japanese_chars += 1
                elif "\u4E00" <= char <= "\u9FFF":  # kanji
                    japanese_chars += 1

        if total_chars == 0:
            return "en"

        return "ja" if (japanese_chars / total_chars) >= 0.3 else "en"

    def __enter__(self) -> "PDFReader":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
