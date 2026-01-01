"""
PDF Translator - PDF Writer Module

翻訳済みテキストをPDFに出力
"""

from typing import List, Optional, Dict, Any, Tuple
import fitz  # PyMuPDF
from pathlib import Path
import os
import platform

from modules.layout_manager import (
    BoundingBox, FontInfo, TextBlock, ImageInfo, PageData, SpanInfo, TranslationGroup
)


def _get_system_japanese_font() -> Optional[str]:
    """システムの日本語フォントパスを取得"""
    if platform.system() == "Windows":
        font_dir = os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts")
        # 優先順位順にフォントを探す
        candidates = ["meiryo.ttc", "msgothic.ttc", "YuGothR.ttc", "GOTHIC.TTF"]
        for font_name in candidates:
            font_path = os.path.join(font_dir, font_name)
            if os.path.exists(font_path):
                return font_path
    elif platform.system() == "Linux":
        candidates = [
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/truetype/takao-gothic/TakaoGothic.ttf",
            "/app/fonts/NotoSansJP-Regular.ttf",
        ]
        for font_path in candidates:
            if os.path.exists(font_path):
                return font_path
    elif platform.system() == "Darwin":  # macOS
        candidates = [
            "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc",
            "/Library/Fonts/Arial Unicode.ttf",
        ]
        for font_path in candidates:
            if os.path.exists(font_path):
                return font_path
    return None


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
    """PDF書き込みクラス（元PDF複製＋テキスト置換方式対応）"""

    def __init__(self, font_config: Optional[Dict[str, Any]] = None):
        self._document: Optional[fitz.Document] = None
        self._source_path: Optional[str] = None
        self._font_config = font_config or {}
        self._japanese_font_path: Optional[str] = None
        self._english_font: str = "helv"
        self._registered_fonts: Dict[int, bool] = {}  # page_num -> font registered

        if font_config:
            if "japanese" in font_config:
                self._japanese_font_path = font_config["japanese"].get("regular")
            if "english" in font_config:
                self._english_font = font_config["english"].get("regular", "helv")

        # システムフォントを探す
        if not self._japanese_font_path:
            self._japanese_font_path = _get_system_japanese_font()

    # ========== 新方式: 元PDF複製＋テキスト置換 ==========

    def open_source(self, source_path: str) -> None:
        """
        元PDFを開いて編集用に保持

        Args:
            source_path: 元PDFファイルパス

        Raises:
            PDFWriteError: ファイルが存在しない場合
        """
        path = Path(source_path)
        if not path.exists():
            raise PDFWriteError(f"Source PDF not found: {source_path}")

        try:
            self._document = fitz.open(source_path)
            self._source_path = source_path
        except Exception as e:
            raise PDFWriteError(f"Failed to open source PDF: {e}")

    def replace_text_on_page(
        self,
        page_num: int,
        text_blocks: List[TextBlock],
        target_language: str
    ) -> None:
        """
        1ページ分のテキストを置換

        Args:
            page_num: ページ番号
            text_blocks: 翻訳済みテキストブロック
            target_language: 出力言語（'ja' or 'en'）
        """
        if self._document is None:
            raise PDFWriteError("No document is open")

        page = self._document[page_num]

        # ハイブリッドモード: span座標を使用
        has_spans = any(block.spans for block in text_blocks)

        if has_spans:
            # span座標でredact
            for block in text_blocks:
                for span in block.spans:
                    bbox = span.bbox.to_tuple()
                    self._add_redact_annotation(page, bbox)
        else:
            # 従来方式: block座標でredact
            for block in text_blocks:
                bbox = block.bbox.to_tuple()
                self._add_redact_annotation(page, bbox)

        # redactionを一括適用（テキストを削除）
        page.apply_redactions()

        # 翻訳テキストを配置
        if has_spans:
            # span座標を使って配置
            for block in text_blocks:
                self._write_text_with_spans(page, block, target_language)
        else:
            # 従来方式
            for block in text_blocks:
                self._write_text(page, block, target_language)

    def replace_with_groups(
        self,
        page_num: int,
        groups: List[TranslationGroup],
        target_language: str
    ) -> None:
        """
        TranslationGroupを使ってテキストを置換

        Args:
            page_num: ページ番号
            groups: 翻訳グループのリスト
            target_language: 出力言語
        """
        if self._document is None:
            raise PDFWriteError("No document is open")

        page = self._document[page_num]

        # 全spanの領域をredact
        for group in groups:
            for span in group.spans:
                bbox = span.bbox.to_tuple()
                self._add_redact_annotation(page, bbox)

        # redactionを適用
        page.apply_redactions()

        # 各グループの翻訳テキストを配置
        for group in groups:
            self._write_translation_group(page, group, target_language)

    def _extend_bbox_to_group_range(
        self,
        group: TranslationGroup
    ) -> Tuple[float, float, float, float]:
        """
        グループの開始spanから終了spanまでの拡張bboxを計算

        開始spanの左上座標と終了spanの右下座標を組み合わせて、
        グループ全体をカバーするbboxを生成する。

        Args:
            group: 翻訳グループ

        Returns:
            拡張されたbbox (x0, y0, x1, y1)
        """
        first_span = group.spans[0]
        last_span = group.spans[-1]

        return (
            first_span.bbox.x0,  # 左上X（最初のspanから）
            first_span.bbox.y0,  # 左上Y（最初のspanから）
            last_span.bbox.x1,   # 右下X（最後のspanから）
            last_span.bbox.y1    # 右下Y（最後のspanから）
        )

    def _write_translation_group(
        self,
        page: fitz.Page,
        group: TranslationGroup,
        target_language: str
    ) -> None:
        """
        翻訳グループを書き込む

        グループ内の開始spanから終了spanまでの拡張bboxに翻訳テキストを配置。
        他のspanは既にredactで消去済みなので、テキストを書き込まない。

        Args:
            page: ページオブジェクト
            group: 翻訳グループ
            target_language: 出力言語
        """
        if not group.spans or not group.translated_text:
            return

        # 開始spanから終了spanまでの拡張bboxを計算
        bbox = self._extend_bbox_to_group_range(group)
        text = group.translated_text

        # 最初のspanのフォント情報を使用
        first_span = group.spans[0]
        font = first_span.font
        font_size = self._calculate_font_size(text, bbox, font.size)
        is_japanese = self._is_japanese(text)
        color = tuple(c / 255.0 for c in font.color)

        try:
            if is_japanese and self._japanese_font_path:
                self._write_text_with_font(page, text, bbox, font_size, color)
            else:
                rect = fitz.Rect(bbox[0], bbox[1], bbox[2], bbox[3])
                font_name = "hebo" if font.is_bold else self._english_font
                page.insert_textbox(
                    rect,
                    text,
                    fontsize=font_size,
                    fontname=font_name,
                    color=color,
                    align=fitz.TEXT_ALIGN_LEFT,
                )
        except Exception as e:
            raise LayoutError(f"Failed to write translation group: {e}")

    def _add_redact_annotation(
        self,
        page: fitz.Page,
        bbox: Tuple[float, float, float, float]
    ) -> None:
        """
        テキスト領域にredact注釈を追加

        Args:
            page: ページオブジェクト
            bbox: 消去する領域 (x0, y0, x1, y1)

        Note:
            fill=False を使用して背景を保持する。
            fill=True や fill=(1,1,1) を使うと背景が白で塗りつぶされる。
        """
        rect = fitz.Rect(bbox[0], bbox[1], bbox[2], bbox[3])
        page.add_redact_annot(rect, fill=False)

    def _clear_text_area(
        self,
        page: fitz.Page,
        bbox: Tuple[float, float, float, float],
        bg_color: Tuple[float, float, float] = (1, 1, 1)
    ) -> None:
        """
        テキスト領域を消去（後方互換性用 - draw_rect方式）

        Args:
            page: ページオブジェクト
            bbox: 消去する領域 (x0, y0, x1, y1)
            bg_color: 背景色（デフォルト: 白）
        """
        rect = fitz.Rect(bbox[0], bbox[1], bbox[2], bbox[3])
        # 白色矩形で元のテキストを覆う
        page.draw_rect(rect, color=bg_color, fill=bg_color)

    def _write_text(
        self,
        page: fitz.Page,
        block: TextBlock,
        target_language: str
    ) -> None:
        """
        翻訳テキストを配置

        Args:
            page: ページオブジェクト
            block: テキストブロック
            target_language: 出力言語
        """
        text = block.translated_text or block.text
        if not text:
            return

        bbox = block.bbox.to_tuple()
        font_size = self._calculate_font_size(text, bbox, block.font.size)

        # 翻訳テキストの言語を自動判定（target_languageより実際の文字を優先）
        is_japanese = self._is_japanese(text)

        # 色を正規化
        color = tuple(c / 255.0 for c in block.font.color)

        try:
            if is_japanese and self._japanese_font_path:
                # 日本語の場合はシステムフォントを使用
                self._write_text_with_font(page, text, bbox, font_size, color)
            else:
                # 英語の場合は組み込みフォントを使用
                rect = fitz.Rect(bbox[0], bbox[1], bbox[2], bbox[3])
                font_name = "hebo" if block.font.is_bold else self._english_font
                page.insert_textbox(
                    rect,
                    text,
                    fontsize=font_size,
                    fontname=font_name,
                    color=color,
                    align=fitz.TEXT_ALIGN_LEFT,
                )
        except Exception as e:
            raise LayoutError(f"Failed to write text: {e}")

    def _write_text_with_spans(
        self,
        page: fitz.Page,
        block: TextBlock,
        target_language: str
    ) -> None:
        """
        span座標を使って翻訳テキストを配置（ハイブリッドモード用）

        翻訳テキストを元のspanの位置と比率に応じて分割配置する。
        これにより、元のレイアウトを維持しながら翻訳テキストを配置できる。

        Args:
            page: ページオブジェクト
            block: テキストブロック（spans情報を含む）
            target_language: 出力言語
        """
        translated_text = block.translated_text or block.text
        if not translated_text or not block.spans:
            return

        # 元テキストの合計文字数
        original_total_len = sum(len(span.text) for span in block.spans)
        if original_total_len == 0:
            return

        # 翻訳テキストを元のspan比率で分割して配置
        translated_pos = 0
        translated_total_len = len(translated_text)

        for i, span in enumerate(block.spans):
            # このspanに割り当てる翻訳文字数を計算
            span_ratio = len(span.text) / original_total_len

            if i == len(block.spans) - 1:
                # 最後のspanは残り全部
                span_translated = translated_text[translated_pos:]
            else:
                span_len = int(translated_total_len * span_ratio)
                # 最低1文字は確保
                span_len = max(1, span_len)
                span_translated = translated_text[translated_pos:translated_pos + span_len]
                translated_pos += span_len

            if not span_translated:
                continue

            bbox = span.bbox.to_tuple()
            font_size = self._calculate_font_size(span_translated, bbox, span.font.size)
            is_japanese = self._is_japanese(span_translated)
            color = tuple(c / 255.0 for c in span.font.color)

            try:
                if is_japanese and self._japanese_font_path:
                    self._write_text_with_font(page, span_translated, bbox, font_size, color)
                else:
                    rect = fitz.Rect(bbox[0], bbox[1], bbox[2], bbox[3])
                    font_name = "hebo" if span.font.is_bold else self._english_font
                    page.insert_textbox(
                        rect,
                        span_translated,
                        fontsize=font_size,
                        fontname=font_name,
                        color=color,
                        align=fitz.TEXT_ALIGN_LEFT,
                    )
            except Exception as e:
                raise LayoutError(f"Failed to write span text: {e}")

    def _write_text_with_font(
        self,
        page: fitz.Page,
        text: str,
        bbox: Tuple[float, float, float, float],
        font_size: float,
        color: Tuple[float, float, float]
    ) -> None:
        """
        外部フォントを使用してテキストを配置

        Args:
            page: ページオブジェクト
            text: テキスト
            bbox: 配置領域
            font_size: フォントサイズ（最大サイズとして使用）
            color: 文字色 (r, g, b) 0-1
        """
        if not self._japanese_font_path:
            raise FontError("Japanese font not found")

        font = fitz.Font(fontfile=self._japanese_font_path)

        x0, y0, x1, y1 = bbox
        width = x1 - x0
        height = y1 - y0

        # テキストがbboxに収まるようにフォントサイズを調整
        adjusted_size, lines = self._fit_text_to_bbox(text, font, bbox, font_size)

        # TextWriterを使用してテキストを配置
        tw = fitz.TextWriter(page.rect)
        current_y = y0 + adjusted_size  # 最初の行のベースライン

        for line in lines:
            tw.append((x0, current_y), line, font=font, fontsize=adjusted_size)
            current_y += adjusted_size * 1.2  # 行間

        tw.write_text(page, color=color)

    def _fit_text_to_bbox(
        self,
        text: str,
        font: fitz.Font,
        bbox: Tuple[float, float, float, float],
        max_font_size: float
    ) -> Tuple[float, List[str]]:
        """
        テキストがbbox領域に収まるようにフォントサイズと折り返しを計算

        Args:
            text: 出力テキスト
            font: 使用フォント
            bbox: 配置領域 (x0, y0, x1, y1)
            max_font_size: 最大フォントサイズ

        Returns:
            Tuple[float, List[str]]: (調整後フォントサイズ, 折り返し済み行リスト)
        """
        x0, y0, x1, y1 = bbox
        width = x1 - x0
        height = y1 - y0

        # 最大サイズから最小サイズまで試す
        for font_size in range(int(max_font_size), int(MIN_FONT_SIZE) - 1, -1):
            lines = self._wrap_text(text, font, float(font_size), width)
            line_height = font_size * 1.2
            total_height = len(lines) * line_height

            if total_height <= height:
                return float(font_size), lines

        # 最小サイズでも収まらない場合
        return MIN_FONT_SIZE, self._wrap_text(text, font, MIN_FONT_SIZE, width)

    def _wrap_text(
        self,
        text: str,
        font: fitz.Font,
        font_size: float,
        max_width: float
    ) -> List[str]:
        """
        テキストを指定幅で折り返す

        Args:
            text: テキスト
            font: フォント
            font_size: フォントサイズ
            max_width: 最大幅

        Returns:
            折り返されたテキスト行のリスト
        """
        lines = []
        current_line = ""

        for char in text:
            test_line = current_line + char
            text_width = font.text_length(test_line, fontsize=font_size)

            if text_width <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = char

        if current_line:
            lines.append(current_line)

        return lines if lines else [text]

    # ========== 後方互換性用メソッド ==========

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
        color = tuple(c / 255.0 for c in block.font.color)
        is_japanese = self._is_japanese(text)

        try:
            if is_japanese and self._japanese_font_path:
                # 日本語の場合はシステムフォントを使用
                self._write_text_with_font(page, text, bbox, font_size, color)
            else:
                # 英語の場合は組み込みフォントを使用
                rect = fitz.Rect(bbox[0], bbox[1], bbox[2], bbox[3])
                font_name = "hebo" if block.font.is_bold else self._english_font
                page.insert_textbox(
                    rect,
                    text,
                    fontsize=font_size,
                    fontname=font_name,
                    color=color,
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
        """
        テキストがbbox幅に収まるようにフォントサイズを計算

        Args:
            text: 出力テキスト
            bbox: 配置領域 (x0, y0, x1, y1)
            original_size: 元のフォントサイズ

        Returns:
            調整後のフォントサイズ
        """
        width = bbox[2] - bbox[0]
        height = bbox[3] - bbox[1]

        if not text:
            return original_size

        # 日本語と英語で文字幅の係数を変える
        # 英語: 約0.5〜0.6、日本語: 約1.0（全角文字）
        japanese_count = 0
        english_count = 0
        for char in text:
            if self._is_japanese_char(char):
                japanese_count += 1
            else:
                english_count += 1

        # 加重平均で推定文字幅を計算
        # 日本語は全角なので係数1.0、英語は半角なので係数0.55
        japanese_width = japanese_count * original_size * 1.0
        english_width = english_count * original_size * 0.55
        estimated_text_width = japanese_width + english_width

        if estimated_text_width <= width:
            return original_size

        scale = width / estimated_text_width
        new_size = original_size * scale

        return max(MIN_FONT_SIZE, min(new_size, MAX_FONT_SIZE))

    def _is_japanese_char(self, char: str) -> bool:
        """単一文字が日本語（全角）かどうかを判定"""
        # ひらがな
        if "\u3040" <= char <= "\u309F":
            return True
        # カタカナ
        if "\u30A0" <= char <= "\u30FF":
            return True
        # 漢字
        if "\u4E00" <= char <= "\u9FFF":
            return True
        # 全角記号・句読点
        if "\u3000" <= char <= "\u303F":
            return True
        # 全角英数字
        if "\uFF00" <= char <= "\uFFEF":
            return True
        return False

    def _get_font(self, lang: str, is_bold: bool = False) -> str:
        if lang == "ja":
            if self._japanese_font_path:
                return self._japanese_font_path
            return "japan"
        else:
            if is_bold:
                return "hebo"
            return self._english_font

    def _is_japanese(self, text: str) -> bool:
        for char in text:
            if "\u3040" <= char <= "\u309F":  # hiragana
                return True
            if "\u30A0" <= char <= "\u30FF":  # katakana
                return True
            if "\u4E00" <= char <= "\u9FFF":  # kanji
                return True
        return False

    def __enter__(self) -> "PDFWriter":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
