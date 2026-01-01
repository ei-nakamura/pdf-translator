#!/usr/bin/env python3
"""Helper script to write module files."""

layout_manager_content = '''\
"""
PDF Translator - Layout Manager Module

レイアウト情報の管理とデータクラス定義
"""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict, Any
import json
from pathlib import Path


@dataclass
class BoundingBox:
    x0: float
    y0: float
    x1: float
    y1: float

    @property
    def width(self) -> float:
        return self.x1 - self.x0

    @property
    def height(self) -> float:
        return self.y1 - self.y0

    @property
    def center(self) -> Tuple[float, float]:
        return ((self.x0 + self.x1) / 2, (self.y0 + self.y1) / 2)

    def to_tuple(self) -> Tuple[float, float, float, float]:
        return (self.x0, self.y0, self.x1, self.y1)

    @classmethod
    def from_tuple(cls, t: Tuple[float, float, float, float]) -> "BoundingBox":
        return cls(x0=t[0], y0=t[1], x1=t[2], y1=t[3])

    def to_dict(self) -> Dict[str, float]:
        return {"x0": self.x0, "y0": self.y0, "x1": self.x1, "y1": self.y1}

    @classmethod
    def from_dict(cls, d: Dict[str, float]) -> "BoundingBox":
        return cls(x0=d["x0"], y0=d["y0"], x1=d["x1"], y1=d["y1"])


@dataclass
class FontInfo:
    name: str
    size: float
    is_bold: bool = False
    is_italic: bool = False
    color: Tuple[int, int, int] = (0, 0, 0)

    @classmethod
    def from_flags(cls, name: str, size: float, flags: int, color: Tuple[int, int, int]) -> "FontInfo":
        return cls(name=name, size=size, is_bold=bool(flags & 16), is_italic=bool(flags & 2), color=color)

    def to_dict(self) -> Dict[str, Any]:
        return {"name": self.name, "size": self.size, "is_bold": self.is_bold, "is_italic": self.is_italic, "color": list(self.color)}

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "FontInfo":
        return cls(name=d["name"], size=d["size"], is_bold=d.get("is_bold", False), is_italic=d.get("is_italic", False), color=tuple(d.get("color", [0, 0, 0])))


@dataclass
class TextBlock:
    id: str
    text: str
    bbox: BoundingBox
    font: FontInfo
    translated_text: Optional[str] = None
    block_type: str = "text"
    line_count: int = 1
    paragraph_index: int = 0

    @property
    def char_count(self) -> int:
        return len(self.text)

    @property
    def translated_char_count(self) -> int:
        return len(self.translated_text) if self.translated_text else 0

    @property
    def expansion_ratio(self) -> float:
        if not self.translated_text or self.char_count == 0:
            return 1.0
        return self.translated_char_count / self.char_count

    def to_dict(self) -> Dict[str, Any]:
        return {"id": self.id, "text": self.text, "translated_text": self.translated_text, "bbox": self.bbox.to_dict(), "font": self.font.to_dict(), "block_type": self.block_type, "line_count": self.line_count, "paragraph_index": self.paragraph_index}

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "TextBlock":
        return cls(id=d["id"], text=d["text"], translated_text=d.get("translated_text"), bbox=BoundingBox.from_dict(d["bbox"]), font=FontInfo.from_dict(d["font"]), block_type=d.get("block_type", "text"), line_count=d.get("line_count", 1), paragraph_index=d.get("paragraph_index", 0))


@dataclass
class ImageInfo:
    id: str
    bbox: BoundingBox
    image_data: Optional[bytes] = None
    image_type: str = "png"
    xref: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {"id": self.id, "bbox": self.bbox.to_dict(), "image_type": self.image_type, "xref": self.xref}

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ImageInfo":
        return cls(id=d["id"], bbox=BoundingBox.from_dict(d["bbox"]), image_type=d.get("image_type", "png"), xref=d.get("xref", 0))


@dataclass
class DrawingInfo:
    id: str
    drawing_type: str
    bbox: BoundingBox
    stroke_color: Optional[Tuple[int, int, int]] = None
    fill_color: Optional[Tuple[int, int, int]] = None
    stroke_width: float = 1.0
    path_data: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {"id": self.id, "drawing_type": self.drawing_type, "bbox": self.bbox.to_dict(), "stroke_color": list(self.stroke_color) if self.stroke_color else None, "fill_color": list(self.fill_color) if self.fill_color else None, "stroke_width": self.stroke_width, "path_data": self.path_data}

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "DrawingInfo":
        return cls(id=d["id"], drawing_type=d["drawing_type"], bbox=BoundingBox.from_dict(d["bbox"]), stroke_color=tuple(d["stroke_color"]) if d.get("stroke_color") else None, fill_color=tuple(d["fill_color"]) if d.get("fill_color") else None, stroke_width=d.get("stroke_width", 1.0), path_data=d.get("path_data"))


@dataclass
class PageData:
    page_number: int
    width: float
    height: float
    rotation: int = 0
    text_blocks: List[TextBlock] = field(default_factory=list)
    images: List[ImageInfo] = field(default_factory=list)
    drawings: List[DrawingInfo] = field(default_factory=list)

    @property
    def size(self) -> Tuple[float, float]:
        return (self.width, self.height)

    def get_block_by_id(self, block_id: str) -> Optional[TextBlock]:
        for block in self.text_blocks:
            if block.id == block_id:
                return block
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {"page_number": self.page_number, "width": self.width, "height": self.height, "rotation": self.rotation, "text_blocks": [b.to_dict() for b in self.text_blocks], "images": [i.to_dict() for i in self.images], "drawings": [d.to_dict() for d in self.drawings]}

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "PageData":
        return cls(page_number=d["page_number"], width=d["width"], height=d["height"], rotation=d.get("rotation", 0), text_blocks=[TextBlock.from_dict(b) for b in d.get("text_blocks", [])], images=[ImageInfo.from_dict(i) for i in d.get("images", [])], drawings=[DrawingInfo.from_dict(dr) for dr in d.get("drawings", [])])


@dataclass
class DocumentData:
    file_path: str
    page_count: int
    title: Optional[str] = None
    author: Optional[str] = None
    pages: List[PageData] = field(default_factory=list)
    source_language: Optional[str] = None
    target_language: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {"file_path": self.file_path, "page_count": self.page_count, "title": self.title, "author": self.author, "source_language": self.source_language, "target_language": self.target_language, "pages": [p.to_dict() for p in self.pages]}

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "DocumentData":
        return cls(file_path=d["file_path"], page_count=d["page_count"], title=d.get("title"), author=d.get("author"), source_language=d.get("source_language"), target_language=d.get("target_language"), pages=[PageData.from_dict(p) for p in d.get("pages", [])])


class LayoutManager:
    MIN_FONT_SIZE = 6.0

    def __init__(self):
        self._document: Optional[DocumentData] = None
        self._block_id_counter: int = 0

    def set_document(self, document: DocumentData) -> None:
        self._document = document

    def get_document(self) -> Optional[DocumentData]:
        return self._document

    def get_page(self, page_num: int) -> Optional[PageData]:
        if self._document is None:
            return None
        if 0 <= page_num < len(self._document.pages):
            return self._document.pages[page_num]
        return None

    def add_page(self, page_data: PageData) -> None:
        if self._document is not None:
            self._document.pages.append(page_data)

    def generate_block_id(self) -> str:
        self._block_id_counter += 1
        return f"block_{self._block_id_counter:06d}"

    def update_translated_text(self, block_id: str, translated_text: str) -> None:
        if self._document is None:
            return
        for page in self._document.pages:
            block = page.get_block_by_id(block_id)
            if block is not None:
                block.translated_text = translated_text
                return

    def calculate_adjusted_font_size(self, block: TextBlock) -> float:
        if not block.translated_text:
            return block.font.size
        expansion = block.expansion_ratio
        if expansion <= 1.0:
            return block.font.size
        scale = 1.0 / (expansion ** 0.5)
        adjusted_size = block.font.size * scale
        return max(adjusted_size, self.MIN_FONT_SIZE)

    def get_layout_statistics(self) -> Dict[str, Any]:
        stats = {"total_pages": 0, "total_blocks": 0, "total_images": 0, "avg_expansion_ratio": 1.0, "max_expansion_ratio": 1.0, "blocks_needing_adjustment": 0, "pages_with_overflow_risk": []}
        if not self._document:
            return stats
        expansion_ratios = []
        for page in self._document.pages:
            stats["total_pages"] += 1
            stats["total_blocks"] += len(page.text_blocks)
            stats["total_images"] += len(page.images)
            page_has_overflow_risk = False
            for block in page.text_blocks:
                if block.translated_text:
                    ratio = block.expansion_ratio
                    expansion_ratios.append(ratio)
                    if ratio > 1.5:
                        stats["blocks_needing_adjustment"] += 1
                        page_has_overflow_risk = True
            if page_has_overflow_risk:
                stats["pages_with_overflow_risk"].append(page.page_number)
        if expansion_ratios:
            stats["avg_expansion_ratio"] = sum(expansion_ratios) / len(expansion_ratios)
            stats["max_expansion_ratio"] = max(expansion_ratios)
        return stats

    def to_dict(self) -> Dict[str, Any]:
        if self._document is None:
            return {}
        return self._document.to_dict()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LayoutManager":
        manager = cls()
        if data:
            manager._document = DocumentData.from_dict(data)
        return manager

    def save_to_json(self, file_path: str) -> None:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)

    @classmethod
    def load_from_json(cls, file_path: str) -> "LayoutManager":
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data)
'''

with open('modules/layout_manager.py', 'w', encoding='utf-8') as f:
    f.write(layout_manager_content)
print('layout_manager.py written successfully')

# config.py
config_content = '''\
"""
PDF Translator - Configuration Module

アプリケーション設定の管理
"""

from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path
import os
from dotenv import load_dotenv


class ConfigError(Exception):
    """設定エラーの基底クラス"""
    pass


class MissingConfigError(ConfigError):
    """必須設定が未設定"""
    pass


class InvalidConfigError(ConfigError):
    """設定値が不正"""
    pass


@dataclass
class APIConfig:
    """API設定"""
    api_key: str
    model: str = "claude-3-5-sonnet-20241022"
    max_tokens: int = 4000
    temperature: float = 0.3
    timeout: int = 60
    max_retries: int = 3


@dataclass
class PDFConfig:
    """PDF設定"""
    input_dir: Path = field(default_factory=lambda: Path("/app/input"))
    output_dir: Path = field(default_factory=lambda: Path("/app/output"))
    max_file_size: int = 104857600
    max_pages: int = 100


@dataclass
class FontConfig:
    """フォント設定"""
    font_dir: Path = field(default_factory=lambda: Path("/app/fonts"))
    japanese_font: str = "NotoSansCJK-Regular.ttc"
    english_font: str = "helv"
    min_font_size: float = 6.0
    max_font_size: float = 72.0

    @property
    def japanese_font_path(self) -> Path:
        system_path = Path("/usr/share/fonts/opentype/noto") / self.japanese_font
        if system_path.exists():
            return system_path
        return self.font_dir / self.japanese_font


@dataclass
class LogConfig:
    """ログ設定"""
    level: str = "INFO"
    file: Optional[Path] = None
    format: str = "[%(asctime)s] [%(levelname)s] %(message)s"


class ConfigLoader:
    """設定読み込みユーティリティ"""

    def __init__(self, env_file: Optional[str] = None):
        self._env_file = env_file
        self._loaded = False

    def load_env(self) -> None:
        if self._env_file:
            load_dotenv(self._env_file)
        else:
            load_dotenv()
        self._loaded = True

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        if not self._loaded:
            self.load_env()
        return os.getenv(key, default)

    def get_required(self, key: str) -> str:
        value = self.get(key)
        if value is None:
            raise MissingConfigError(f"Required environment variable \\'{key}\\' is not set")
        return value

    def get_int(self, key: str, default: int) -> int:
        value = self.get(key)
        if value is None:
            return default
        try:
            return int(value)
        except ValueError:
            raise InvalidConfigError(f"Environment variable \\'{key}\\' must be an integer")

    def get_float(self, key: str, default: float) -> float:
        value = self.get(key)
        if value is None:
            return default
        try:
            return float(value)
        except ValueError:
            raise InvalidConfigError(f"Environment variable \\'{key}\\' must be a float")

    def get_bool(self, key: str, default: bool) -> bool:
        value = self.get(key)
        if value is None:
            return default
        return value.lower() in ("true", "1", "yes", "on")

    def get_path(self, key: str, default: Optional[Path] = None) -> Optional[Path]:
        value = self.get(key)
        if value is None:
            return default
        return Path(value)


@dataclass
class Config:
    """アプリケーション設定"""
    api: APIConfig
    pdf: PDFConfig = field(default_factory=PDFConfig)
    font: FontConfig = field(default_factory=FontConfig)
    log: LogConfig = field(default_factory=LogConfig)

    @classmethod
    def load(cls, env_file: Optional[str] = None) -> "Config":
        loader = ConfigLoader(env_file=env_file)
        loader.load_env()

        api_key = loader.get("ANTHROPIC_API_KEY", "")
        api_config = APIConfig(
            api_key=api_key,
            model=loader.get("CLAUDE_MODEL", "claude-3-5-sonnet-20241022"),
            max_tokens=loader.get_int("MAX_TOKENS", 4000),
            temperature=loader.get_float("TEMPERATURE", 0.3),
            timeout=loader.get_int("API_TIMEOUT", 60),
            max_retries=loader.get_int("MAX_RETRIES", 3),
        )

        pdf_config = PDFConfig(
            input_dir=loader.get_path("INPUT_DIR", Path("/app/input")),
            output_dir=loader.get_path("OUTPUT_DIR", Path("/app/output")),
            max_file_size=loader.get_int("MAX_FILE_SIZE", 104857600),
            max_pages=loader.get_int("MAX_PAGES", 100),
        )

        font_config = FontConfig(
            font_dir=loader.get_path("FONT_DIR", Path("/app/fonts")),
            japanese_font=loader.get("JAPANESE_FONT", "NotoSansCJK-Regular.ttc"),
            min_font_size=loader.get_float("MIN_FONT_SIZE", 6.0),
            max_font_size=loader.get_float("MAX_FONT_SIZE", 72.0),
        )

        log_file = loader.get("LOG_FILE")
        log_config = LogConfig(
            level=loader.get("LOG_LEVEL", "INFO"),
            file=Path(log_file) if log_file else None,
        )

        return cls(api=api_config, pdf=pdf_config, font=font_config, log=log_config)

    def validate(self) -> None:
        errors = []
        if not self.api.api_key:
            errors.append("ANTHROPIC_API_KEY is required")
        elif not self.api.api_key.startswith("sk-ant-"):
            errors.append("ANTHROPIC_API_KEY format is invalid")
        if self.api.max_tokens < 1 or self.api.max_tokens > 100000:
            errors.append("MAX_TOKENS must be between 1 and 100000")
        if self.api.temperature < 0 or self.api.temperature > 1:
            errors.append("TEMPERATURE must be between 0 and 1")
        if errors:
            raise InvalidConfigError("\\n".join(errors))
'''

with open('config.py', 'w', encoding='utf-8') as f:
    f.write(config_content)
print('config.py written successfully')

# pdf_reader.py
pdf_reader_content = '''\
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
                if "\\u3040" <= char <= "\\u309F":  # hiragana
                    japanese_chars += 1
                elif "\\u30A0" <= char <= "\\u30FF":  # katakana
                    japanese_chars += 1
                elif "\\u4E00" <= char <= "\\u9FFF":  # kanji
                    japanese_chars += 1

        if total_chars == 0:
            return "en"

        return "ja" if (japanese_chars / total_chars) >= 0.3 else "en"

    def __enter__(self) -> "PDFReader":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
'''

with open('modules/pdf_reader.py', 'w', encoding='utf-8') as f:
    f.write(pdf_reader_content)
print('pdf_reader.py written successfully')

# translator.py
translator_content = '''\
"""
PDF Translator - Translator Module

Claude APIを使用したテキスト翻訳
"""

from enum import Enum
from typing import List, Optional
import time
import anthropic

from modules.layout_manager import TextBlock


class TranslationDirection(Enum):
    JA_TO_EN = "ja-to-en"
    EN_TO_JA = "en-to-ja"


class TranslationError(Exception):
    """翻訳エラーの基底クラス"""
    pass


class APIConnectionError(TranslationError):
    """API接続エラー"""
    pass


class APIAuthenticationError(TranslationError):
    """API認証エラー"""
    pass


class RateLimitError(TranslationError):
    """レート制限エラー"""
    pass


class TokenLimitError(TranslationError):
    """トークン制限超過エラー"""
    pass


DEFAULT_MODEL = "claude-3-5-sonnet-20241022"
MAX_RETRIES = 3
RETRY_DELAY_BASE = 1.0
RETRY_DELAY_MULTIPLIER = 2.0


SYSTEM_PROMPT_JA_TO_EN = """You are a professional translator specializing in Japanese to English translation.

Rules:
1. Translate the given Japanese text into natural, fluent English
2. Preserve the original meaning and nuance as much as possible
3. Maintain the tone and style of the original text
4. Keep proper nouns, technical terms, and brand names unchanged unless there is a commonly used English equivalent
5. Output ONLY the translated text without any explanations or notes
6. Preserve paragraph structure and line breaks
"""

SYSTEM_PROMPT_EN_TO_JA = """You are a professional translator specializing in English to Japanese translation.

Rules:
1. Translate the given English text into natural, fluent Japanese
2. Preserve the original meaning and nuance as much as possible
3. Maintain the tone and style of the original text
4. Keep proper nouns, technical terms, and brand names unchanged unless there is a commonly used Japanese equivalent
5. Output ONLY the translated text without any explanations or notes
6. Preserve paragraph structure and line breaks
7. Use appropriate Japanese writing style based on the context
"""


class Translator:
    """翻訳クラス"""

    def __init__(self, api_key: str, model: str = DEFAULT_MODEL):
        self._api_key = api_key
        self._model = model
        self._client: Optional[anthropic.Anthropic] = None

    def _get_client(self) -> anthropic.Anthropic:
        if self._client is None:
            self._client = anthropic.Anthropic(api_key=self._api_key)
        return self._client

    def validate_api_key(self) -> bool:
        try:
            client = self._get_client()
            client.messages.create(
                model=self._model,
                max_tokens=10,
                messages=[{"role": "user", "content": "Hi"}],
            )
            return True
        except anthropic.AuthenticationError:
            return False
        except Exception:
            return False

    def translate(self, text: str, direction: TranslationDirection, context: Optional[str] = None) -> str:
        if not text or not text.strip():
            return ""

        prompt = self._build_prompt(text, direction, context)
        return self._call_api_with_retry(prompt, direction)

    def translate_batch(self, texts: List[str], direction: TranslationDirection) -> List[str]:
        if not texts:
            return []
        return [self.translate(t, direction) for t in texts]

    def translate_blocks(self, blocks: List[TextBlock], direction: TranslationDirection) -> List[TextBlock]:
        if not blocks:
            return []

        for block in blocks:
            translated = self.translate(block.text, direction)
            block.translated_text = translated

        return blocks

    def _build_prompt(self, text: str, direction: TranslationDirection, context: Optional[str] = None) -> str:
        prompt = f"Translate the following text:\\n\\n{text}"
        if context:
            prompt = f"Context: {context}\\n\\n{prompt}"
        return prompt

    def _get_system_prompt(self, direction: TranslationDirection) -> str:
        if direction == TranslationDirection.JA_TO_EN:
            return SYSTEM_PROMPT_JA_TO_EN
        else:
            return SYSTEM_PROMPT_EN_TO_JA

    def _call_api(self, prompt: str, direction: TranslationDirection) -> str:
        client = self._get_client()
        system_prompt = self._get_system_prompt(direction)

        response = client.messages.create(
            model=self._model,
            max_tokens=4000,
            system=system_prompt,
            messages=[{"role": "user", "content": prompt}],
        )

        return response.content[0].text

    def _call_api_with_retry(self, prompt: str, direction: TranslationDirection) -> str:
        last_error = None

        for attempt in range(MAX_RETRIES):
            try:
                return self._call_api(prompt, direction)
            except anthropic.RateLimitError as e:
                last_error = RateLimitError(str(e))
                if attempt < MAX_RETRIES - 1:
                    delay = RETRY_DELAY_BASE * (RETRY_DELAY_MULTIPLIER ** attempt)
                    time.sleep(delay)
            except anthropic.AuthenticationError as e:
                raise APIAuthenticationError(str(e))
            except anthropic.APIConnectionError as e:
                last_error = APIConnectionError(str(e))
                if attempt < MAX_RETRIES - 1:
                    delay = RETRY_DELAY_BASE * (RETRY_DELAY_MULTIPLIER ** attempt)
                    time.sleep(delay)
            except Exception as e:
                raise TranslationError(str(e))

        if last_error:
            raise last_error
        raise TranslationError("Translation failed after retries")
'''

with open('modules/translator.py', 'w', encoding='utf-8') as f:
    f.write(translator_content)
print('translator.py written successfully')

# pdf_writer.py
pdf_writer_content = '''\
"""
PDF Translator - PDF Writer Module

翻訳済みテキストをPDFに出力
"""

from typing import List, Optional, Dict, Any, Tuple
import fitz  # PyMuPDF
from pathlib import Path

from modules.layout_manager import (
    BoundingBox, FontInfo, TextBlock, ImageInfo, PageData
)


class PDFWriteError(Exception):
    """PDF書き込みエラーの基底クラス"""
    pass


class FontError(PDFWriteError):
    """フォントエラー"""
    pass


class LayoutError(PDFWriteError):
    """レイアウトエラー"""
    pass


MIN_FONT_SIZE = 6.0
MAX_FONT_SIZE = 72.0


class PDFWriter:
    """PDF書き込みクラス"""

    def __init__(self, font_config: Optional[Dict[str, Any]] = None):
        self._document: Optional[fitz.Document] = None
        self._font_config = font_config or {}
        self._japanese_font: Optional[str] = None
        self._english_font: str = "helv"

        if font_config:
            if "japanese" in font_config:
                self._japanese_font = font_config["japanese"].get("regular")
            if "english" in font_config:
                self._english_font = font_config["english"].get("regular", "helv")

    def create_document(self, page_count: int, page_sizes: List[Tuple[float, float]]) -> None:
        self._document = fitz.open()

        for i in range(page_count):
            width, height = page_sizes[i] if i < len(page_sizes) else page_sizes[-1]
            self._document.new_page(width=width, height=height)

    def close(self) -> None:
        if self._document:
            self._document.close()
            self._document = None

    def save(self, output_path: str, compress: bool = True) -> None:
        if self._document is None:
            raise PDFWriteError("No document to save")

        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        if compress:
            self._document.save(output_path, garbage=4, deflate=True)
        else:
            self._document.save(output_path)

    def write_page(self, page_num: int, page_data: PageData, translated_blocks: List[TextBlock]) -> None:
        if self._document is None:
            raise PDFWriteError("No document is open")

        page = self._document[page_num]

        for block in translated_blocks:
            target_lang = "ja" if self._is_japanese(block.translated_text or "") else "en"
            self.write_text_block(page, block, target_lang)

        for image in page_data.images:
            if image.image_data:
                self.write_image(page, image)

    def write_text_block(self, page: fitz.Page, block: TextBlock, target_lang: str) -> None:
        text = block.translated_text or block.text
        if not text:
            return

        bbox = block.bbox.to_tuple()
        font_size = self._calculate_font_size(text, bbox, block.font.size)
        font_name = self._get_font(target_lang, block.font.is_bold)

        rect = fitz.Rect(bbox[0], bbox[1], bbox[2], bbox[3])

        try:
            page.insert_textbox(
                rect,
                text,
                fontsize=font_size,
                fontname=font_name,
                color=tuple(c / 255.0 for c in block.font.color),
                align=fitz.TEXT_ALIGN_LEFT,
            )
        except Exception as e:
            raise LayoutError(f"Failed to write text block: {e}")

    def write_image(self, page: fitz.Page, image_info: ImageInfo) -> None:
        if not image_info.image_data:
            return

        bbox = image_info.bbox.to_tuple()
        rect = fitz.Rect(bbox[0], bbox[1], bbox[2], bbox[3])

        try:
            page.insert_image(rect, stream=image_info.image_data)
        except Exception as e:
            raise LayoutError(f"Failed to write image: {e}")

    def _calculate_font_size(self, text: str, bbox: Tuple[float, float, float, float], original_size: float) -> float:
        width = bbox[2] - bbox[0]
        height = bbox[3] - bbox[1]

        if not text:
            return original_size

        avg_char_width = original_size * 0.5
        estimated_text_width = len(text) * avg_char_width

        if estimated_text_width <= width:
            return original_size

        scale = width / estimated_text_width
        new_size = original_size * scale

        return max(MIN_FONT_SIZE, min(new_size, MAX_FONT_SIZE))

    def _get_font(self, lang: str, is_bold: bool = False) -> str:
        if lang == "ja":
            if self._japanese_font:
                return self._japanese_font
            return "japan"
        else:
            if is_bold:
                return "hebo"
            return self._english_font

    def _is_japanese(self, text: str) -> bool:
        for char in text:
            if "\\u3040" <= char <= "\\u309F":  # hiragana
                return True
            if "\\u30A0" <= char <= "\\u30FF":  # katakana
                return True
            if "\\u4E00" <= char <= "\\u9FFF":  # kanji
                return True
        return False

    def __enter__(self) -> "PDFWriter":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
'''

with open('modules/pdf_writer.py', 'w', encoding='utf-8') as f:
    f.write(pdf_writer_content)
print('pdf_writer.py written successfully')

# main.py
main_content = '''\
"""
PDF Translator - Main CLI Module

PDF翻訳アプリケーションのエントリーポイント
"""

import argparse
import logging
import sys
import time
from pathlib import Path
from typing import Optional

from config import Config, ConfigError, MissingConfigError
from modules.pdf_reader import PDFReader, PDFReadError
from modules.translator import Translator, TranslationDirection, TranslationError
from modules.pdf_writer import PDFWriter, PDFWriteError
from modules.layout_manager import LayoutManager, PageData


VERSION = "1.0.0"

EXIT_SUCCESS = 0
EXIT_FILE_NOT_FOUND = 1
EXIT_FILE_READ_ERROR = 2
EXIT_API_CONNECTION_ERROR = 3
EXIT_API_AUTH_ERROR = 4
EXIT_FILE_WRITE_ERROR = 5
EXIT_UNKNOWN_ERROR = 99


def setup_logging(verbose: bool = False, log_file: Optional[str] = None) -> logging.Logger:
    logger = logging.getLogger("pdf_translator")
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)

    formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s")

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG if verbose else logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    if log_file:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="PDF Translation Tool - Translate PDF documents using Claude API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("input_file", help="Input PDF file path")
    parser.add_argument("-o", "--output", help="Output PDF file path")
    parser.add_argument(
        "-d", "--direction",
        choices=["ja-to-en", "en-to-ja"],
        help="Translation direction",
    )
    parser.add_argument(
        "-a", "--auto-detect",
        action="store_true",
        help="Auto-detect source language",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument("-l", "--log-file", help="Log file path")
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")

    return parser.parse_args()


def generate_output_path(input_path: str, direction: str) -> str:
    path = Path(input_path)
    suffix = "_translated"
    if direction:
        lang = direction.split("-")[-1]
        suffix = f"_{lang}"
    return str(path.parent / f"{path.stem}{suffix}.pdf")


class PDFTranslatorApp:
    """PDF翻訳アプリケーション"""

    def __init__(self, config: Config, logger: logging.Logger):
        self._config = config
        self._logger = logger
        self._reader: Optional[PDFReader] = None
        self._translator: Optional[Translator] = None
        self._writer: Optional[PDFWriter] = None
        self._layout_manager: Optional[LayoutManager] = None

    def run(self, input_path: str, output_path: str, direction: str, auto_detect: bool) -> bool:
        self._logger.info(f"PDF Translation Tool v{VERSION}")
        self._logger.info("=" * 50)

        try:
            self._reader = PDFReader()
            doc_data = self._reader.open(input_path)
            self._logger.info(f"Input: {input_path} ({doc_data.page_count} pages)")
            self._logger.info(f"Output: {output_path}")

            self._layout_manager = LayoutManager()
            self._layout_manager.set_document(doc_data)

            if auto_detect:
                all_text = " ".join(
                    block.text for page in doc_data.pages for block in page.text_blocks
                )
                detected_lang = self._reader.detect_language(all_text)
                direction = "ja-to-en" if detected_lang == "ja" else "en-to-ja"
                self._logger.info(f"Detected language: {detected_lang}")

            trans_direction = (
                TranslationDirection.JA_TO_EN
                if direction == "ja-to-en"
                else TranslationDirection.EN_TO_JA
            )
            direction_str = "Japanese → English" if direction == "ja-to-en" else "English → Japanese"
            self._logger.info(f"Direction: {direction_str}")

            self._translator = Translator(
                api_key=self._config.api.api_key,
                model=self._config.api.model,
            )

            page_sizes = [(p.width, p.height) for p in doc_data.pages]
            self._writer = PDFWriter()
            self._writer.create_document(page_count=doc_data.page_count, page_sizes=page_sizes)

            self._logger.info("")
            self._logger.info("Processing...")
            start_time = time.time()

            for i, page_data in enumerate(doc_data.pages):
                self._logger.info(f"Processing page {i + 1}/{doc_data.page_count}...")
                translated_page = self._process_page(i, page_data, trans_direction)
                self._writer.write_page(i, translated_page, translated_page.text_blocks)

            self._writer.save(output_path)
            elapsed = time.time() - start_time

            self._logger.info("")
            self._logger.info("Completed!")
            self._logger.info(f"- Total pages: {doc_data.page_count}")
            self._logger.info(f"- Processing time: {elapsed:.1f} seconds")
            self._logger.info(f"- Output file: {output_path}")

            return True

        except FileNotFoundError as e:
            self._logger.error(f"File not found: {e}")
            return False
        except PDFReadError as e:
            self._logger.error(f"PDF read error: {e}")
            return False
        except TranslationError as e:
            self._logger.error(f"Translation error: {e}")
            return False
        except PDFWriteError as e:
            self._logger.error(f"PDF write error: {e}")
            return False
        finally:
            self._cleanup()

    def _process_page(self, page_num: int, page_data: PageData, direction: TranslationDirection) -> PageData:
        if not page_data.text_blocks:
            return page_data

        self._translator.translate_blocks(page_data.text_blocks, direction)
        return page_data

    def _cleanup(self) -> None:
        if self._reader:
            self._reader.close()
        if self._writer:
            self._writer.close()


def main() -> int:
    args = parse_args()

    logger = setup_logging(verbose=args.verbose, log_file=args.log_file)

    input_path = args.input_file
    if not Path(input_path).exists():
        logger.error(f"Input file not found: {input_path}")
        return EXIT_FILE_NOT_FOUND

    try:
        config = Config.load()
    except MissingConfigError as e:
        logger.error(f"Configuration error: {e}")
        return EXIT_API_AUTH_ERROR
    except ConfigError as e:
        logger.error(f"Configuration error: {e}")
        return EXIT_UNKNOWN_ERROR

    if not args.direction and not args.auto_detect:
        logger.error("Please specify --direction or --auto-detect")
        return EXIT_UNKNOWN_ERROR

    output_path = args.output or generate_output_path(input_path, args.direction or "")

    app = PDFTranslatorApp(config, logger)
    success = app.run(input_path, output_path, args.direction or "", args.auto_detect)

    return EXIT_SUCCESS if success else EXIT_UNKNOWN_ERROR


if __name__ == "__main__":
    sys.exit(main())
'''

with open('main.py', 'w', encoding='utf-8') as f:
    f.write(main_content)
print('main.py written successfully')
