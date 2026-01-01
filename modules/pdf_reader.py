"""
PDF Translator - PDF Reader Module

PDFファイルからテキストとレイアウト情報を抽出
"""

from typing import List, Optional, Tuple
import fitz  # PyMuPDF
from pathlib import Path

from modules.layout_manager import (
    BoundingBox, FontInfo, TextBlock, ImageInfo, PageData, DocumentData, SpanInfo
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

    def __init__(self, merge_overlapping: bool = True, extraction_mode: str = "hybrid"):
        """
        Args:
            merge_overlapping: 重複するブロックをマージするかどうか（デフォルト: True）
            extraction_mode: 抽出モード
                - "block": block単位で抽出（従来方式）
                - "line": line単位で抽出
                - "span": span単位で抽出（細粒度）
                - "hybrid": block単位で翻訳、span座標で書き込み（推奨）
        """
        self._document: Optional[fitz.Document] = None
        self._file_path: Optional[str] = None
        self._block_id_counter: int = 0
        self._merge_overlapping = merge_overlapping
        self._extraction_mode = extraction_mode

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

        # 抽出モードに応じてテキストブロックを抽出
        if self._extraction_mode == "hybrid":
            text_blocks = self._extract_text_hybrid(page)
        elif self._extraction_mode == "span":
            text_blocks = self._extract_text_spans(page)
        elif self._extraction_mode == "line":
            text_blocks = self._extract_text_lines(page)
        else:
            text_blocks = self._extract_text_blocks(page)

        # 重複ブロックをマージ
        if self._merge_overlapping:
            text_blocks = self._merge_overlapping_blocks(text_blocks)

        page_data.text_blocks = text_blocks
        page_data.images = self._extract_images(page)

        return page_data

    def _extract_text_blocks(self, page: fitz.Page) -> List[TextBlock]:
        """block単位でテキストを抽出（従来方式）"""
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

    def _extract_text_spans(self, page: fitz.Page) -> List[TextBlock]:
        """span単位でテキストを抽出（細粒度）"""
        blocks = []
        page_dict = page.get_text("dict")

        for block in page_dict.get("blocks", []):
            if block.get("type") == 0:  # text block
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        text = span.get("text", "")
                        if text.strip():
                            bbox = span.get("bbox", (0, 0, 0, 0))
                            color_int = span.get("color", 0)
                            r = (color_int >> 16) & 0xFF
                            g = (color_int >> 8) & 0xFF
                            b = color_int & 0xFF

                            self._block_id_counter += 1
                            blocks.append(TextBlock(
                                id=f"span_{self._block_id_counter:06d}",
                                text=text,
                                bbox=BoundingBox(x0=bbox[0], y0=bbox[1], x1=bbox[2], y1=bbox[3]),
                                font=FontInfo(
                                    name=span.get("font", ""),
                                    size=span.get("size", 12.0),
                                    is_bold=bool(span.get("flags", 0) & 16),
                                    is_italic=bool(span.get("flags", 0) & 2),
                                    color=(r, g, b),
                                ),
                                line_count=1,
                            ))

        return blocks

    def _extract_text_lines(self, page: fitz.Page) -> List[TextBlock]:
        """line単位でテキストを抽出（中粒度）"""
        blocks = []
        page_dict = page.get_text("dict")

        for block in page_dict.get("blocks", []):
            if block.get("type") == 0:  # text block
                for line in block.get("lines", []):
                    line_bbox = line.get("bbox", (0, 0, 0, 0))
                    text_content = ""
                    font_info = None

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
                        blocks.append(TextBlock(
                            id=f"line_{self._block_id_counter:06d}",
                            text=text_content,
                            bbox=BoundingBox(x0=line_bbox[0], y0=line_bbox[1], x1=line_bbox[2], y1=line_bbox[3]),
                            font=font_info or FontInfo(name="", size=12.0),
                            line_count=1,
                        ))

        return blocks

    def _extract_text_hybrid(self, page: fitz.Page) -> List[TextBlock]:
        """
        ハイブリッド方式でテキストを抽出

        block単位でTextBlockを作成し、各spanの座標情報をspansリストに保持。
        これにより:
        - 翻訳はblock単位で効率的に行える（API呼び出し回数削減）
        - 書き込みはspan座標を使って正確な位置に配置できる
        """
        blocks = []
        page_dict = page.get_text("dict")

        for block in page_dict.get("blocks", []):
            if block.get("type") == 0:  # text block
                text_content = ""
                font_info = None
                line_count = 0
                span_list: List[SpanInfo] = []

                for line in block.get("lines", []):
                    line_count += 1
                    for span in line.get("spans", []):
                        span_text = span.get("text", "")
                        if not span_text.strip():
                            continue

                        text_content += span_text

                        # spanの座標とフォント情報を取得
                        span_bbox = span.get("bbox", (0, 0, 0, 0))
                        color_int = span.get("color", 0)
                        r = (color_int >> 16) & 0xFF
                        g = (color_int >> 8) & 0xFF
                        b = color_int & 0xFF

                        span_font = FontInfo(
                            name=span.get("font", ""),
                            size=span.get("size", 12.0),
                            is_bold=bool(span.get("flags", 0) & 16),
                            is_italic=bool(span.get("flags", 0) & 2),
                            color=(r, g, b),
                        )

                        span_list.append(SpanInfo(
                            text=span_text,
                            bbox=BoundingBox(
                                x0=span_bbox[0], y0=span_bbox[1],
                                x1=span_bbox[2], y1=span_bbox[3]
                            ),
                            font=span_font,
                        ))

                        if font_info is None:
                            font_info = span_font

                if text_content.strip() and span_list:
                    self._block_id_counter += 1
                    bbox = block.get("bbox", (0, 0, 0, 0))
                    blocks.append(TextBlock(
                        id=f"hybrid_{self._block_id_counter:06d}",
                        text=text_content,
                        bbox=BoundingBox(x0=bbox[0], y0=bbox[1], x1=bbox[2], y1=bbox[3]),
                        font=font_info or FontInfo(name="", size=12.0),
                        line_count=line_count,
                        spans=span_list,
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

    def _merge_overlapping_blocks(self, blocks: List[TextBlock]) -> List[TextBlock]:
        """
        重複するテキストブロックをマージする

        重複判定:
        - X軸とY軸の両方で50%以上重複している場合のみマージ対象
        - テキストが長い方を残し、短い方を削除（より多くの情報を保持）

        Args:
            blocks: テキストブロックのリスト

        Returns:
            マージ後のテキストブロックリスト
        """
        if not blocks:
            return blocks

        # ブロックをテキスト長の長い順にソート（長いテキストを優先して残す）
        sorted_blocks = sorted(
            blocks,
            key=lambda b: len(b.text.strip()),
            reverse=True
        )

        result = []
        removed_indices = set()

        for i, block1 in enumerate(sorted_blocks):
            if i in removed_indices:
                continue

            for j, block2 in enumerate(sorted_blocks):
                if i >= j or j in removed_indices:
                    continue

                # X軸とY軸の両方で重複をチェック
                x_overlap_ratio = self._calculate_axis_overlap_ratio(
                    block1.bbox.x0, block1.bbox.x1,
                    block2.bbox.x0, block2.bbox.x1
                )
                y_overlap_ratio = self._calculate_axis_overlap_ratio(
                    block1.bbox.y0, block1.bbox.y1,
                    block2.bbox.y0, block2.bbox.y1
                )

                # 両軸で80%以上重複している場合のみマージ（厳密な判定で誤マージを防ぐ）
                if x_overlap_ratio > 0.8 and y_overlap_ratio > 0.8:
                    # 短いテキスト（block2）を削除対象に
                    removed_indices.add(j)

        # 削除されなかったブロックを結果に追加
        for i, block in enumerate(sorted_blocks):
            if i not in removed_indices:
                result.append(block)

        # 元の順序（Y座標→X座標）でソートし直す
        result.sort(key=lambda b: (b.bbox.y0, b.bbox.x0))

        return result

    def _calculate_axis_overlap_ratio(
        self, a_start: float, a_end: float, b_start: float, b_end: float
    ) -> float:
        """
        1軸上での重複率を計算（小さい方の長さに対する比率）

        Args:
            a_start, a_end: 1つ目の範囲
            b_start, b_end: 2つ目の範囲

        Returns:
            重複率（0.0-1.0）
        """
        overlap = max(0, min(a_end, b_end) - max(a_start, b_start))
        if overlap == 0:
            return 0.0

        length_a = a_end - a_start
        length_b = b_end - b_start
        smaller_length = min(length_a, length_b)

        if smaller_length == 0:
            return 0.0

        return overlap / smaller_length

    def _calculate_overlap_ratio(self, bbox1: BoundingBox, bbox2: BoundingBox) -> float:
        """
        2つのbboxの重複率を計算（小さい方の面積に対する比率）

        Args:
            bbox1: 1つ目のbbox
            bbox2: 2つ目のbbox

        Returns:
            重複率（0.0-1.0）
        """
        # 交差領域を計算
        x_overlap = max(0, min(bbox1.x1, bbox2.x1) - max(bbox1.x0, bbox2.x0))
        y_overlap = max(0, min(bbox1.y1, bbox2.y1) - max(bbox1.y0, bbox2.y0))
        overlap_area = x_overlap * y_overlap

        if overlap_area == 0:
            return 0.0

        # 小さい方の面積を計算
        area1 = (bbox1.x1 - bbox1.x0) * (bbox1.y1 - bbox1.y0)
        area2 = (bbox2.x1 - bbox2.x0) * (bbox2.y1 - bbox2.y0)
        smaller_area = min(area1, area2)

        if smaller_area == 0:
            return 0.0

        return overlap_area / smaller_area

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
