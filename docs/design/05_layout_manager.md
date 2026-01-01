# layout_manager.py（レイアウト管理モジュール）設計書

## 1. 概要

PDFのレイアウト情報を管理するモジュール。
PDF読み込み時に抽出したレイアウト情報を保持し、翻訳後のPDF出力時に参照される。
各モジュール間で共有されるデータ構造（データクラス）も本モジュールで定義する。

## 2. 責務

- レイアウト情報用データクラスの定義
- ページ・ブロック単位でのレイアウト情報管理
- 翻訳前後のテキストブロック対応付け
- レイアウト調整計算（フォントサイズ、位置）
- レイアウト情報のシリアライズ/デシリアライズ

## 3. 依存関係

```
layout_manager.py
└── (標準ライブラリのみ)
    ├── dataclasses
    ├── typing
    └── json
```

## 4. データクラス定義

### 4.1 座標・サイズ関連

```python
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict, Any

@dataclass
class BoundingBox:
    """境界ボックス"""
    x0: float  # 左端X座標
    y0: float  # 上端Y座標
    x1: float  # 右端X座標
    y1: float  # 下端Y座標

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
    def from_tuple(cls, t: Tuple[float, float, float, float]) -> 'BoundingBox':
        return cls(x0=t[0], y0=t[1], x1=t[2], y1=t[3])
```

### 4.2 フォント情報

```python
@dataclass
class FontInfo:
    """フォント情報"""
    name: str                     # フォント名
    size: float                   # フォントサイズ（pt）
    is_bold: bool = False         # 太字フラグ
    is_italic: bool = False       # 斜体フラグ
    color: Tuple[int, int, int] = (0, 0, 0)  # RGB色

    @classmethod
    def from_flags(cls, name: str, size: float, flags: int,
                   color: Tuple[int, int, int]) -> 'FontInfo':
        """PyMuPDFのフラグから生成"""
        return cls(
            name=name,
            size=size,
            is_bold=bool(flags & 2**4),    # bit 4: bold
            is_italic=bool(flags & 2**1),  # bit 1: italic
            color=color
        )
```

### 4.3 スパン情報（span単位のテキスト）

```python
@dataclass
class SpanInfo:
    """span単位のテキスト情報（座標精度を保持）"""
    text: str                     # テキスト内容
    bbox: BoundingBox             # 境界ボックス
    font: FontInfo                # フォント情報
    index: int = 0                # ページ内でのインデックス（位置順）

    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            "text": self.text,
            "bbox": self.bbox.to_dict(),
            "font": self.font.to_dict(),
            "index": self.index
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> 'SpanInfo':
        """辞書形式から生成"""
        return cls(
            text=d["text"],
            bbox=BoundingBox.from_dict(d["bbox"]),
            font=FontInfo.from_dict(d["font"]),
            index=d.get("index", 0)
        )
```

### 4.4 翻訳グループ

```python
@dataclass
class TranslationGroup:
    """翻訳グループ: 一塊として翻訳されたspan群"""
    start_index: int              # 開始spanインデックス
    end_index: int                # 終了spanインデックス（含む）
    original_text: str            # 元テキスト（結合）
    translated_text: str          # 翻訳テキスト
    spans: List[SpanInfo] = field(default_factory=list)  # 対象span

    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            "start_index": self.start_index,
            "end_index": self.end_index,
            "original_text": self.original_text,
            "translated_text": self.translated_text,
            "spans": [s.to_dict() for s in self.spans]
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> 'TranslationGroup':
        """辞書形式から生成"""
        return cls(
            start_index=d["start_index"],
            end_index=d["end_index"],
            original_text=d["original_text"],
            translated_text=d["translated_text"],
            spans=[SpanInfo.from_dict(s) for s in d.get("spans", [])]
        )
```

### 4.5 テキストブロック

```python
@dataclass
class TextBlock:
    """テキストブロック"""
    id: str                       # 一意識別子
    text: str                     # テキスト内容
    translated_text: Optional[str] = None  # 翻訳後テキスト
    bbox: BoundingBox = None      # 境界ボックス
    font: FontInfo = None         # フォント情報
    block_type: str = "text"      # ブロックタイプ
    line_count: int = 1           # 行数
    paragraph_index: int = 0      # 段落インデックス

    @property
    def char_count(self) -> int:
        return len(self.text)

    @property
    def translated_char_count(self) -> int:
        return len(self.translated_text) if self.translated_text else 0

    @property
    def expansion_ratio(self) -> float:
        """翻訳による文字数変化率"""
        if not self.translated_text or self.char_count == 0:
            return 1.0
        return self.translated_char_count / self.char_count
```

### 4.6 画像情報

```python
@dataclass
class ImageInfo:
    """画像情報"""
    id: str                       # 一意識別子
    bbox: BoundingBox             # 境界ボックス
    image_data: bytes = None      # 画像バイナリ（オプション）
    image_type: str = "png"       # 画像形式
    xref: int = 0                 # PDF内部参照
```

### 4.7 図形情報

```python
@dataclass
class DrawingInfo:
    """図形情報"""
    id: str                       # 一意識別子
    drawing_type: str             # 図形タイプ（line, rect, circle等）
    bbox: BoundingBox             # 境界ボックス
    stroke_color: Optional[Tuple[int, int, int]] = None  # 線の色
    fill_color: Optional[Tuple[int, int, int]] = None    # 塗りつぶし色
    stroke_width: float = 1.0     # 線幅
    path_data: Optional[str] = None  # パスデータ
```

### 4.8 ページデータ

```python
@dataclass
class PageData:
    """1ページ分のデータ"""
    page_number: int              # ページ番号（0始まり）
    width: float                  # ページ幅（pt）
    height: float                 # ページ高さ（pt）
    rotation: int = 0             # 回転角度
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
```

### 4.9 ドキュメントデータ

```python
@dataclass
class DocumentData:
    """ドキュメント全体のデータ"""
    file_path: str                # ファイルパス
    page_count: int               # 総ページ数
    title: Optional[str] = None   # タイトル
    author: Optional[str] = None  # 作者
    pages: List[PageData] = field(default_factory=list)
    source_language: Optional[str] = None  # 元言語
    target_language: Optional[str] = None  # 翻訳先言語
```

## 5. LayoutManager クラス

```python
class LayoutManager:
    """レイアウト情報管理クラス"""

    def __init__(self):
        self._document: Optional[DocumentData] = None
        self._block_id_counter: int = 0

    def set_document(self, document: DocumentData) -> None:
        """
        ドキュメントデータを設定

        Args:
            document: ドキュメントデータ
        """
        self._document = document

    def get_document(self) -> Optional[DocumentData]:
        """ドキュメントデータを取得"""
        return self._document

    def get_page(self, page_num: int) -> Optional[PageData]:
        """
        指定ページのデータを取得

        Args:
            page_num: ページ番号

        Returns:
            PageData: ページデータ（存在しない場合None）
        """
        pass

    def add_page(self, page_data: PageData) -> None:
        """ページデータを追加"""
        pass

    def generate_block_id(self) -> str:
        """一意のブロックIDを生成"""
        self._block_id_counter += 1
        return f"block_{self._block_id_counter:06d}"

    def update_translated_text(self, block_id: str, translated_text: str) -> None:
        """
        翻訳済みテキストを更新

        Args:
            block_id: ブロックID
            translated_text: 翻訳済みテキスト
        """
        pass

    def calculate_adjusted_font_size(self, block: TextBlock) -> float:
        """
        翻訳後のテキストに適したフォントサイズを計算

        Args:
            block: テキストブロック

        Returns:
            float: 調整後のフォントサイズ
        """
        pass

    def get_layout_statistics(self) -> Dict[str, Any]:
        """
        レイアウト統計情報を取得

        Returns:
            Dict: 統計情報（ブロック数、平均拡張率等）
        """
        pass

    def to_dict(self) -> Dict[str, Any]:
        """辞書形式にシリアライズ"""
        pass

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LayoutManager':
        """辞書形式からデシリアライズ"""
        pass

    def save_to_json(self, file_path: str) -> None:
        """JSONファイルに保存"""
        pass

    @classmethod
    def load_from_json(cls, file_path: str) -> 'LayoutManager':
        """JSONファイルから読み込み"""
        pass
```

## 6. レイアウト調整ロジック

### 6.1 フォントサイズ調整

```python
def calculate_adjusted_font_size(self, block: TextBlock) -> float:
    """
    翻訳後のテキスト長に応じてフォントサイズを調整

    アルゴリズム:
    1. 元のテキスト長と翻訳後テキスト長の比率を計算
    2. 比率が1.0より大きい（テキストが長くなった）場合、フォントサイズを縮小
    3. 最小フォントサイズ制限を適用
    4. 比率が1.0以下の場合は元のサイズを維持
    """
    if not block.translated_text:
        return block.font.size

    expansion = block.expansion_ratio

    if expansion <= 1.0:
        return block.font.size

    # 縮小率を計算（平方根で緩やかに）
    scale = 1.0 / (expansion ** 0.5)
    adjusted_size = block.font.size * scale

    # 最小サイズ制限
    MIN_FONT_SIZE = 6.0
    return max(adjusted_size, MIN_FONT_SIZE)
```

### 6.2 ブロック位置調整

```python
def calculate_adjusted_position(self, block: TextBlock,
                                 available_height: float) -> BoundingBox:
    """
    行数変化に応じてブロック位置を調整

    Args:
        block: テキストブロック
        available_height: 利用可能な高さ

    Returns:
        BoundingBox: 調整後の境界ボックス
    """
    # 行数が増加した場合の対応
    # 基本的には元の位置を維持し、フォントサイズで調整
    return block.bbox
```

## 7. 統計情報

```python
def get_layout_statistics(self) -> Dict[str, Any]:
    """
    レイアウト統計情報

    Returns:
        {
            "total_pages": int,
            "total_blocks": int,
            "total_images": int,
            "avg_expansion_ratio": float,
            "max_expansion_ratio": float,
            "blocks_needing_adjustment": int,
            "pages_with_overflow_risk": List[int]
        }
    """
    stats = {
        "total_pages": 0,
        "total_blocks": 0,
        "total_images": 0,
        "avg_expansion_ratio": 1.0,
        "max_expansion_ratio": 1.0,
        "blocks_needing_adjustment": 0,
        "pages_with_overflow_risk": []
    }

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
                if ratio > 1.5:  # 50%以上の拡張
                    stats["blocks_needing_adjustment"] += 1
                    page_has_overflow_risk = True

        if page_has_overflow_risk:
            stats["pages_with_overflow_risk"].append(page.page_number)

    if expansion_ratios:
        stats["avg_expansion_ratio"] = sum(expansion_ratios) / len(expansion_ratios)
        stats["max_expansion_ratio"] = max(expansion_ratios)

    return stats
```

## 8. シリアライズ/デシリアライズ

### 8.1 JSON形式

```json
{
    "file_path": "/app/input/document.pdf",
    "page_count": 2,
    "title": "Sample Document",
    "source_language": "ja",
    "target_language": "en",
    "pages": [
        {
            "page_number": 0,
            "width": 595.0,
            "height": 842.0,
            "rotation": 0,
            "text_blocks": [
                {
                    "id": "block_000001",
                    "text": "こんにちは",
                    "translated_text": "Hello",
                    "bbox": {"x0": 50, "y0": 100, "x1": 200, "y1": 120},
                    "font": {
                        "name": "NotoSansJP",
                        "size": 12.0,
                        "is_bold": false,
                        "color": [0, 0, 0]
                    }
                }
            ],
            "images": [],
            "drawings": []
        }
    ]
}
```

## 9. 使用例

```python
from modules.layout_manager import LayoutManager, DocumentData, PageData, TextBlock

# 初期化
manager = LayoutManager()

# ドキュメント作成
doc = DocumentData(
    file_path="/app/input/document.pdf",
    page_count=1,
    source_language="ja",
    target_language="en"
)

# ページ作成
page = PageData(
    page_number=0,
    width=595.0,
    height=842.0
)

# テキストブロック追加
block = TextBlock(
    id=manager.generate_block_id(),
    text="こんにちは、世界！",
    bbox=BoundingBox(50, 100, 200, 120),
    font=FontInfo(name="NotoSansJP", size=12.0)
)
page.text_blocks.append(block)
doc.pages.append(page)

manager.set_document(doc)

# 翻訳後テキスト更新
manager.update_translated_text(block.id, "Hello, World!")

# 調整後フォントサイズ取得
adjusted_size = manager.calculate_adjusted_font_size(block)

# 統計情報
stats = manager.get_layout_statistics()
print(f"平均拡張率: {stats['avg_expansion_ratio']:.2f}")

# JSON保存
manager.save_to_json("/app/output/layout.json")
```

## 10. テスト項目

- [x] 正常系：データクラスの生成
- [x] 正常系：ブロックID生成（一意性）
- [x] 正常系：翻訳テキスト更新
- [x] 正常系：フォントサイズ調整計算
- [x] 正常系：統計情報取得
- [x] 正常系：JSONシリアライズ
- [x] 正常系：JSONデシリアライズ
- [ ] 正常系：SpanInfo生成とシリアライズ
- [ ] 正常系：TranslationGroup生成とシリアライズ
- [ ] 異常系：存在しないブロックID
- [ ] 異常系：無効なJSONファイル

---

**作成日**: 2026-01-01
**バージョン**: 2.0
**更新履歴**:

- v1.0: 初版作成
- v2.0: SpanInfo、TranslationGroupデータクラス追加
