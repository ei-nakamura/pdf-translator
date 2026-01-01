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
class SpanInfo:
    """span単位のテキスト情報（座標精度を保持）"""
    text: str
    bbox: BoundingBox
    font: FontInfo
    index: int = 0  # ページ内でのインデックス

    def to_dict(self) -> Dict[str, Any]:
        return {"text": self.text, "bbox": self.bbox.to_dict(), "font": self.font.to_dict(), "index": self.index}

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "SpanInfo":
        return cls(text=d["text"], bbox=BoundingBox.from_dict(d["bbox"]), font=FontInfo.from_dict(d["font"]), index=d.get("index", 0))


@dataclass
class TranslationGroup:
    """翻訳グループ: 一塊として翻訳されたspan群"""
    start_index: int  # 開始spanインデックス
    end_index: int    # 終了spanインデックス（含む）
    original_text: str  # 元テキスト（結合）
    translated_text: str  # 翻訳テキスト
    spans: List[SpanInfo] = field(default_factory=list)  # 対象span

    def to_dict(self) -> Dict[str, Any]:
        return {
            "start_index": self.start_index,
            "end_index": self.end_index,
            "original_text": self.original_text,
            "translated_text": self.translated_text,
            "spans": [s.to_dict() for s in self.spans]
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "TranslationGroup":
        return cls(
            start_index=d["start_index"],
            end_index=d["end_index"],
            original_text=d["original_text"],
            translated_text=d["translated_text"],
            spans=[SpanInfo.from_dict(s) for s in d.get("spans", [])]
        )


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
    spans: List["SpanInfo"] = field(default_factory=list)  # ハイブリッドモード用

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
        return {"id": self.id, "text": self.text, "translated_text": self.translated_text, "bbox": self.bbox.to_dict(), "font": self.font.to_dict(), "block_type": self.block_type, "line_count": self.line_count, "paragraph_index": self.paragraph_index, "spans": [s.to_dict() for s in self.spans]}

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "TextBlock":
        return cls(id=d["id"], text=d["text"], translated_text=d.get("translated_text"), bbox=BoundingBox.from_dict(d["bbox"]), font=FontInfo.from_dict(d["font"]), block_type=d.get("block_type", "text"), line_count=d.get("line_count", 1), paragraph_index=d.get("paragraph_index", 0), spans=[SpanInfo.from_dict(s) for s in d.get("spans", [])])


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
