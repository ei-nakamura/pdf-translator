# pdf_reader.py（PDF読み込みモジュール）設計書

## 1. 概要

PDFファイルからテキストとレイアウト情報を抽出するモジュール。
PyMuPDF（fitz）を使用して、テキストの位置情報、フォント情報、ページ構造を取得する。

## 2. 責務

- PDFファイルの読み込みとバリデーション
- ページ単位でのテキスト抽出
- テキストブロックの位置情報（座標）取得
- フォント情報（サイズ、スタイル、色）の取得
- 画像・図形要素の位置情報取得
- ページメタデータ（サイズ、向き）の取得

## 3. 依存関係

```
pdf_reader.py
├── fitz (PyMuPDF)
└── modules/layout_manager.py (データクラス参照)
```

## 4. データ構造

### 4.1 TextBlock（テキストブロック）

```python
@dataclass
class TextBlock:
    """テキストブロック情報"""
    text: str                    # テキスト内容
    bbox: Tuple[float, float, float, float]  # 境界ボックス (x0, y0, x1, y1)
    font_name: str               # フォント名
    font_size: float             # フォントサイズ
    font_flags: int              # フォントフラグ（太字、斜体等）
    color: Tuple[int, int, int]  # RGB色情報
    block_type: str              # ブロックタイプ（text/image）
    line_count: int              # 行数
    char_count: int              # 文字数
```

### 4.2 PageData（ページデータ）

```python
@dataclass
class PageData:
    """1ページ分のデータ"""
    page_number: int             # ページ番号（0始まり）
    width: float                 # ページ幅（ポイント）
    height: float                # ページ高さ（ポイント）
    rotation: int                # 回転角度
    text_blocks: List[TextBlock] # テキストブロックリスト
    images: List[ImageInfo]      # 画像情報リスト
    drawings: List[DrawingInfo]  # 図形情報リスト
```

### 4.3 ImageInfo（画像情報）

```python
@dataclass
class ImageInfo:
    """画像情報"""
    bbox: Tuple[float, float, float, float]  # 境界ボックス
    image_data: bytes            # 画像バイナリデータ
    image_type: str              # 画像形式（png, jpeg等）
    xref: int                    # PDF内部参照番号
```

### 4.4 DocumentInfo（ドキュメント情報）

```python
@dataclass
class DocumentInfo:
    """PDFドキュメント全体の情報"""
    file_path: str               # ファイルパス
    page_count: int              # 総ページ数
    title: Optional[str]         # タイトル（メタデータ）
    author: Optional[str]        # 作者（メタデータ）
    pages: List[PageData]        # 全ページデータ
```

## 5. クラス設計

### 5.1 PDFReader クラス

```python
class PDFReader:
    """PDF読み込みクラス"""

    def __init__(self):
        """初期化"""
        self._document: Optional[fitz.Document] = None

    def open(self, file_path: str) -> DocumentInfo:
        """
        PDFファイルを開く

        Args:
            file_path: PDFファイルパス

        Returns:
            DocumentInfo: ドキュメント情報

        Raises:
            FileNotFoundError: ファイルが存在しない
            PDFReadError: PDF読み込みエラー
        """
        pass

    def close(self) -> None:
        """ドキュメントを閉じる"""
        pass

    def get_page(self, page_num: int) -> PageData:
        """
        指定ページのデータを取得

        Args:
            page_num: ページ番号（0始まり）

        Returns:
            PageData: ページデータ
        """
        pass

    def extract_text_blocks(self, page: fitz.Page) -> List[TextBlock]:
        """
        ページからテキストブロックを抽出

        Args:
            page: PyMuPDFページオブジェクト

        Returns:
            List[TextBlock]: テキストブロックリスト
        """
        pass

    def extract_images(self, page: fitz.Page) -> List[ImageInfo]:
        """
        ページから画像を抽出

        Args:
            page: PyMuPDFページオブジェクト

        Returns:
            List[ImageInfo]: 画像情報リスト
        """
        pass

    def detect_language(self, text: str) -> str:
        """
        テキストの言語を検出

        Args:
            text: 検出対象テキスト

        Returns:
            str: 言語コード（'ja' or 'en'）
        """
        pass

    def __enter__(self) -> 'PDFReader':
        """コンテキストマネージャー対応"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """リソースのクリーンアップ"""
        self.close()
```

## 6. 処理詳細

### 6.1 テキストブロック抽出アルゴリズム

```python
def extract_text_blocks(self, page: fitz.Page) -> List[TextBlock]:
    """
    PyMuPDFのget_text("dict")を使用してテキストブロックを抽出

    処理手順:
    1. page.get_text("dict")でページ内容を辞書形式で取得
    2. "blocks"キーからブロックリストを取得
    3. 各ブロックを解析してTextBlockオブジェクトを生成
    4. ブロックタイプ（テキスト/画像）を判定
    5. テキストブロックの場合、spans情報からフォント情報を取得
    """
    blocks = []
    page_dict = page.get_text("dict")

    for block in page_dict["blocks"]:
        if block["type"] == 0:  # テキストブロック
            # lines -> spans からテキストとフォント情報を抽出
            text_content = ""
            font_info = None

            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    text_content += span["text"]
                    if font_info is None:
                        font_info = {
                            "font": span["font"],
                            "size": span["size"],
                            "flags": span["flags"],
                            "color": span["color"]
                        }

            blocks.append(TextBlock(
                text=text_content,
                bbox=tuple(block["bbox"]),
                font_name=font_info["font"] if font_info else "",
                font_size=font_info["size"] if font_info else 12.0,
                font_flags=font_info["flags"] if font_info else 0,
                color=self._int_to_rgb(font_info["color"]) if font_info else (0, 0, 0),
                block_type="text",
                line_count=len(block.get("lines", [])),
                char_count=len(text_content)
            ))

    return blocks
```

### 6.2 言語検出ロジック

```python
def detect_language(self, text: str) -> str:
    """
    シンプルな言語検出（日本語/英語）

    判定基準:
    - 日本語文字（ひらがな、カタカナ、漢字）の割合で判定
    - 30%以上が日本語文字なら日本語と判定
    """
    if not text:
        return "en"

    japanese_chars = 0
    total_chars = 0

    for char in text:
        if char.strip():  # 空白以外
            total_chars += 1
            # ひらがな、カタカナ、漢字の判定
            if '\u3040' <= char <= '\u309F':  # ひらがな
                japanese_chars += 1
            elif '\u30A0' <= char <= '\u30FF':  # カタカナ
                japanese_chars += 1
            elif '\u4E00' <= char <= '\u9FFF':  # CJK統合漢字
                japanese_chars += 1

    if total_chars == 0:
        return "en"

    return "ja" if (japanese_chars / total_chars) >= 0.3 else "en"
```

## 7. エラーハンドリング

### 7.1 カスタム例外

```python
class PDFReadError(Exception):
    """PDF読み込みエラー"""
    pass

class EncryptedPDFError(PDFReadError):
    """暗号化PDFエラー"""
    pass

class CorruptedPDFError(PDFReadError):
    """破損PDFエラー"""
    pass
```

### 7.2 エラー対応

| エラー | 対応 |
| --- | --- |
| ファイル不存在 | FileNotFoundError発生 |
| 暗号化PDF | EncryptedPDFError発生 |
| 破損PDF | CorruptedPDFError発生 |
| 読み込み不可ページ | 警告ログ出力、スキップして継続 |

## 8. パフォーマンス考慮

- 大きなPDFの場合はページ単位で遅延読み込み
- 画像データは必要時のみ展開
- メモリ使用量を考慮したバッチ処理

## 9. 使用例

```python
# 基本的な使用
reader = PDFReader()
doc_info = reader.open("/app/input/document.pdf")

print(f"Total pages: {doc_info.page_count}")

for page_data in doc_info.pages:
    print(f"Page {page_data.page_number + 1}:")
    for block in page_data.text_blocks:
        print(f"  Text: {block.text[:50]}...")
        print(f"  Position: {block.bbox}")
        print(f"  Font: {block.font_name} {block.font_size}pt")

reader.close()

# コンテキストマネージャー使用
with PDFReader() as reader:
    doc_info = reader.open("/app/input/document.pdf")
    # 処理...
```

## 10. テスト項目

- [ ] 正常系：テキストのみのPDF読み込み
- [ ] 正常系：画像を含むPDF読み込み
- [ ] 正常系：複数ページPDF読み込み
- [ ] 正常系：日本語テキストの抽出
- [ ] 正常系：英語テキストの抽出
- [ ] 正常系：言語自動検出（日本語）
- [ ] 正常系：言語自動検出（英語）
- [ ] 異常系：存在しないファイル
- [ ] 異常系：暗号化PDF
- [ ] 異常系：破損PDF
- [ ] 異常系：空のPDF

---

**作成日**: 2026-01-01
**バージョン**: 1.0
