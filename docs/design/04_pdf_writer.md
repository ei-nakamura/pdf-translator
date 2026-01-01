# pdf_writer.py（PDF出力モジュール）設計書

## 1. 概要

翻訳済みテキストをPDF形式で出力するモジュール。
**元のPDFを複製し、テキスト部分のみを置換する方式**で、レイアウトを完全に保持しながらPDFを生成する。

## 2. 責務

- **元PDFの複製と保持**（背景、描画要素、画像をすべて維持）
- テキストブロックの消去と翻訳テキストの配置
- フォントの管理（日英対応フォント）
- 文字数変化への対応（フォントサイズ調整）

## 3. 依存関係

```
pdf_writer.py
├── fitz (PyMuPDF)
├── modules/layout_manager.py (レイアウト情報)
└── config.py (フォント設定)
```

## 4. 実装方式

### 4.1 元PDF複製＋テキスト置換方式

従来の「新規PDFを作成」方式ではなく、以下の方式を採用：

```
1. 元PDFを開く（fitz.open()）
2. 各ページに対して：
   a. テキストブロックの位置を特定
   b. 元のテキスト領域を消去（redact機能または白色矩形で覆う）
   c. 同じ位置に翻訳テキストを配置
3. 変更されたPDFを保存
```

### 4.2 この方式のメリット

| 要素 | 従来方式 | 新方式 |
| --- | --- | --- |
| ベクターグラフィック | 手動で再描画が必要 | 自動保持 |
| 背景画像 | 手動で配置が必要 | 自動保持 |
| 複雑なレイアウト | 崩れやすい | 維持される |
| 実装の複雑さ | 高い | 低い |

## 5. フォント設定

### 5.1 使用フォント

```python
# 日本語対応フォント
FONTS = {
    "japanese": {
        "regular": "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "bold": "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    },
    "english": {
        "regular": "helv",  # PyMuPDF組み込み
        "bold": "hebo",
    },
    "fallback": {
        "regular": "/app/fonts/NotoSansJP-Regular.ttf",
    }
}

# フォントサイズ調整
MIN_FONT_SIZE = 6.0
MAX_FONT_SIZE = 72.0
DEFAULT_FONT_SIZE = 12.0
```

## 6. クラス設計

### 6.1 PDFWriter クラス

```python
class PDFWriter:
    """PDF出力クラス（元PDF複製＋テキスト置換方式）"""

    def __init__(self, font_config: Optional[Dict] = None):
        """
        Args:
            font_config: フォント設定（オプション）
        """
        self._document: Optional[fitz.Document] = None
        self._source_document: Optional[fitz.Document] = None
        self._font_config = font_config or FONTS

    def open_source(self, source_path: str) -> None:
        """
        元PDFを開いて複製用に保持

        Args:
            source_path: 元PDFファイルパス
        """
        pass

    def replace_text_on_page(self, page_num: int,
                             text_blocks: List[TextBlock],
                             target_language: str) -> None:
        """
        1ページ分のテキストを置換

        Args:
            page_num: ページ番号
            text_blocks: 翻訳済みテキストブロック
            target_language: 出力言語（'ja' or 'en'）
        """
        pass

    def _clear_text_area(self, page: fitz.Page, bbox: Tuple[float, float, float, float],
                         bg_color: Tuple[float, float, float] = (1, 1, 1)) -> None:
        """
        テキスト領域を消去（背景色で塗りつぶし）

        Args:
            page: ページオブジェクト
            bbox: 消去する領域
            bg_color: 背景色（デフォルト: 白）
        """
        pass

    def _write_text(self, page: fitz.Page, block: TextBlock,
                    target_language: str) -> None:
        """
        翻訳テキストを配置

        Args:
            page: ページオブジェクト
            block: テキストブロック
            target_language: 出力言語
        """
        pass

    def save(self, output_path: str, compress: bool = True) -> None:
        """
        PDFファイルを保存

        Args:
            output_path: 出力ファイルパス
            compress: 圧縮フラグ
        """
        pass

    def close(self) -> None:
        """リソースをクリーンアップ"""
        pass

    def _calculate_font_size(self, text: str, bbox: Tuple[float, float, float, float],
                             original_size: float) -> float:
        """
        テキスト長に応じてフォントサイズを調整

        Args:
            text: 出力テキスト
            bbox: 配置領域
            original_size: 元のフォントサイズ

        Returns:
            float: 調整後のフォントサイズ
        """
        pass

    def _get_font(self, target_language: str, is_bold: bool = False) -> str:
        """
        適切なフォントを取得

        Args:
            target_language: 言語
            is_bold: 太字フラグ

        Returns:
            str: フォント名またはパス
        """
        pass

    def _is_japanese(self, text: str) -> bool:
        """
        テキストが日本語かどうか判定

        Args:
            text: 判定対象テキスト

        Returns:
            bool: 日本語の場合True
        """
        pass

    # 後方互換性のためのメソッド（既存テスト対応）
    def create_document(self, page_count: int,
                        page_sizes: List[Tuple[float, float]]) -> None:
        """
        新規ドキュメントを作成（後方互換性用）

        Args:
            page_count: ページ数
            page_sizes: 各ページのサイズ [(width, height), ...]
        """
        pass

    def write_page(self, page_num: int, page_data: PageData,
                   translated_blocks: List[TextBlock]) -> None:
        """
        1ページ分を出力（後方互換性用）

        Args:
            page_num: ページ番号
            page_data: 元ページデータ
            translated_blocks: 翻訳済みテキストブロック
        """
        pass

    def write_text_block(self, page: fitz.Page, block: TextBlock,
                         target_language: str) -> None:
        """
        テキストブロックを配置（後方互換性用）

        Args:
            page: 出力ページ
            block: テキストブロック
            target_language: 出力言語（'ja' or 'en'）
        """
        pass

    def write_image(self, page: fitz.Page, image_info: ImageInfo) -> None:
        """
        画像を配置（後方互換性用）

        Args:
            page: 出力ページ
            image_info: 画像情報
        """
        pass
```

## 7. 処理詳細

### 7.1 テキスト置換フロー

```
1. 元PDFを開く
   └── fitz.open(source_path)

2. 各ページのテキスト置換
   ├── テキストブロックごとにループ
   │   ├── 元のテキスト領域を消去
   │   │   └── page.draw_rect(rect, color=white, fill=white)
   │   └── 翻訳テキストを配置
   │       └── page.insert_textbox(rect, text, ...)
   └── 次のページへ

3. 保存
   └── document.save(output_path, garbage=4, deflate=True)
```

### 7.2 テキスト領域消去の詳細

```python
def _clear_text_area(self, page: fitz.Page, bbox: Tuple[float, float, float, float],
                     bg_color: Tuple[float, float, float] = (1, 1, 1)) -> None:
    """
    テキスト領域を背景色で塗りつぶして消去

    方法1: draw_rect（シンプルだが重ね描き）
    方法2: redact（テキストを完全削除、より確実）
    """
    rect = fitz.Rect(bbox)

    # 方法1: 白色矩形で覆う
    page.draw_rect(rect, color=bg_color, fill=bg_color)

    # 方法2: redact機能を使用（より確実）
    # page.add_redact_annot(rect, fill=bg_color)
    # page.apply_redactions()
```

### 7.3 フォントサイズ自動調整

```python
def _calculate_font_size(self, text: str, bbox: Tuple[float, float, float, float],
                         original_size: float) -> float:
    """
    テキストが領域に収まるようにフォントサイズを調整

    アルゴリズム:
    1. 元のフォントサイズでテキスト幅を概算
    2. bbox幅と比較
    3. はみ出す場合はサイズを縮小
    4. 最小サイズ以下にはしない
    """
    x0, y0, x1, y1 = bbox
    available_width = x1 - x0

    # 平均文字幅を使用して概算（フォントサイズの約0.5倍）
    avg_char_width = original_size * 0.5
    estimated_width = len(text) * avg_char_width

    if estimated_width <= available_width:
        return original_size

    # 縮小率を計算
    scale = available_width / estimated_width
    adjusted_size = original_size * scale

    # 最小サイズ制限
    return max(adjusted_size, MIN_FONT_SIZE)
```

## 8. エラーハンドリング

### 8.1 カスタム例外

```python
class PDFWriteError(Exception):
    """PDF書き込みエラー"""
    pass

class FontError(PDFWriteError):
    """フォントエラー"""
    pass

class LayoutError(PDFWriteError):
    """レイアウトエラー"""
    pass
```

### 8.2 エラー対応

| エラー | 対応 |
| --- | --- |
| 元PDF読み込み失敗 | PDFWriteError発生 |
| フォント読み込み失敗 | フォールバックフォント使用 |
| テキスト配置失敗 | LayoutError発生、ログ出力 |
| ディスク書き込み失敗 | PDFWriteError発生 |
| メモリ不足 | ページ単位で処理、メモリ解放 |

## 9. 使用例

### 9.1 新方式（元PDF複製＋テキスト置換）

```python
from modules.pdf_writer import PDFWriter

# 初期化
writer = PDFWriter()

# 元PDFを開く
writer.open_source("/app/input/document.pdf")

# 各ページのテキストを置換
for page_num, translated_blocks in enumerate(all_translated):
    writer.replace_text_on_page(page_num, translated_blocks, target_language="ja")

# 保存
writer.save("/app/output/translated.pdf")
writer.close()
```

### 9.2 後方互換性用（既存テスト対応）

```python
from modules.pdf_writer import PDFWriter

# 初期化
writer = PDFWriter()

# 新規ドキュメント作成
page_sizes = [(595, 842), (595, 842)]  # A4サイズ × 2ページ
writer.create_document(page_count=2, page_sizes=page_sizes)

# ページ出力
for page_num, (page_data, translated_blocks) in enumerate(zip(pages, all_translated)):
    writer.write_page(page_num, page_data, translated_blocks)

# 保存
writer.save("/app/output/translated.pdf")
writer.close()
```

## 10. 出力オプション

| オプション | デフォルト | 説明 |
| --- | --- | --- |
| compress | True | PDF圧縮 |
| garbage | 4 | 不要オブジェクト削除レベル |
| deflate | True | ストリーム圧縮 |

## 11. テスト項目

### 11.1 既存テスト（後方互換性）

- [x] 正常系：PDFWriter生成
- [x] 正常系：フォント設定付きPDFWriter生成
- [x] 正常系：ドキュメント作成
- [x] 正常系：異なるサイズのページでドキュメント作成
- [x] 正常系：ドキュメント保存
- [x] 正常系：ページ書き込み
- [x] 正常系：テキストブロック書き込み
- [x] 正常系：画像書き込み
- [x] 正常系：フォントサイズ調整
- [x] 正常系：フォント取得

### 11.2 新方式テスト

- [ ] 正常系：元PDFを開く
- [ ] 正常系：テキスト領域消去
- [ ] 正常系：翻訳テキスト配置
- [ ] 正常系：元PDFのレイアウト保持確認
- [ ] 正常系：ベクターグラフィック保持確認
- [ ] 異常系：元PDF読み込み失敗

---

**作成日**: 2026-01-01
**バージョン**: 2.0
**更新履歴**:

- v1.0: 初版作成（新規PDF作成方式）
- v2.0: 元PDF複製＋テキスト置換方式に変更
