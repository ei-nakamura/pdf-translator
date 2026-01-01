"""
PDF Translator - PDF Reader Module Tests

設計書: docs/design/02_pdf_reader.md
"""

import pytest
from pathlib import Path


class TestPDFReader:
    """PDFReaderクラスのテスト"""

    def test_create_pdf_reader(self):
        """正常系: PDFReader生成"""
        from modules.pdf_reader import PDFReader

        reader = PDFReader()
        assert reader is not None

    def test_open_pdf_file_not_found(self, temp_dir):
        """異常系: 存在しないファイル"""
        from modules.pdf_reader import PDFReader

        reader = PDFReader()
        non_existent = temp_dir / "nonexistent.pdf"

        with pytest.raises(FileNotFoundError):
            reader.open(str(non_existent))

    def test_open_encrypted_pdf(self):
        """異常系: 暗号化PDF"""
        from modules.pdf_reader import PDFReader, EncryptedPDFError

        # 暗号化PDFのテストはモックまたは実際のファイルが必要
        # ここではEncryptedPDFErrorが定義されていることを確認
        reader = PDFReader()
        assert hasattr(reader, "open")

    def test_context_manager(self):
        """正常系: コンテキストマネージャー対応"""
        from modules.pdf_reader import PDFReader

        with PDFReader() as reader:
            assert reader is not None

    def test_close(self):
        """正常系: クローズ処理"""
        from modules.pdf_reader import PDFReader

        reader = PDFReader()
        reader.close()  # エラーなく終了すること


class TestPDFReaderWithMockPDF:
    """モックPDFを使用したPDFReaderのテスト"""

    @pytest.fixture
    def mock_pdf_file(self, temp_dir):
        """PyMuPDFでテスト用PDFを作成"""
        try:
            import fitz

            pdf_path = temp_dir / "test.pdf"
            doc = fitz.open()
            page = doc.new_page(width=595, height=842)
            page.insert_text((50, 100), "Hello, World!", fontsize=12)
            page.insert_text((50, 150), "こんにちは", fontsize=12)
            doc.save(str(pdf_path))
            doc.close()
            return pdf_path
        except ImportError:
            pytest.skip("PyMuPDF not installed")

    def test_open_valid_pdf(self, mock_pdf_file):
        """正常系: 有効なPDFを開く"""
        from modules.pdf_reader import PDFReader

        reader = PDFReader()
        doc_info = reader.open(str(mock_pdf_file))

        assert doc_info is not None
        assert doc_info.page_count >= 1

        reader.close()

    def test_get_page(self, mock_pdf_file):
        """正常系: ページデータ取得"""
        from modules.pdf_reader import PDFReader

        reader = PDFReader()
        reader.open(str(mock_pdf_file))
        page_data = reader.get_page(0)

        assert page_data is not None
        assert page_data.page_number == 0
        assert page_data.width > 0
        assert page_data.height > 0

        reader.close()

    def test_extract_text_blocks(self, mock_pdf_file):
        """正常系: テキストブロック抽出"""
        from modules.pdf_reader import PDFReader

        reader = PDFReader()
        reader.open(str(mock_pdf_file))
        page_data = reader.get_page(0)

        assert len(page_data.text_blocks) > 0

        reader.close()

    def test_text_block_has_bbox(self, mock_pdf_file):
        """正常系: テキストブロックにbbox情報"""
        from modules.pdf_reader import PDFReader

        reader = PDFReader()
        reader.open(str(mock_pdf_file))
        page_data = reader.get_page(0)

        if page_data.text_blocks:
            block = page_data.text_blocks[0]
            assert block.bbox is not None

        reader.close()

    def test_text_block_has_font_info(self, mock_pdf_file):
        """正常系: テキストブロックにフォント情報"""
        from modules.pdf_reader import PDFReader

        reader = PDFReader()
        reader.open(str(mock_pdf_file))
        page_data = reader.get_page(0)

        if page_data.text_blocks:
            block = page_data.text_blocks[0]
            assert block.font is not None
            assert block.font.size > 0

        reader.close()


class TestLanguageDetection:
    """言語検出のテスト"""

    def test_detect_japanese(self, sample_japanese_text):
        """正常系: 日本語検出"""
        from modules.pdf_reader import PDFReader

        reader = PDFReader()
        result = reader.detect_language(sample_japanese_text)

        assert result == "ja"

    def test_detect_english(self, sample_english_text):
        """正常系: 英語検出"""
        from modules.pdf_reader import PDFReader

        reader = PDFReader()
        result = reader.detect_language(sample_english_text)

        assert result == "en"

    def test_detect_empty_text(self):
        """正常系: 空テキスト"""
        from modules.pdf_reader import PDFReader

        reader = PDFReader()
        result = reader.detect_language("")

        assert result == "en"  # デフォルトは英語

    def test_detect_mixed_text(self):
        """正常系: 混在テキスト"""
        from modules.pdf_reader import PDFReader

        reader = PDFReader()
        # 日本語が多い場合
        result = reader.detect_language("これはテストです。Hello!")

        assert result == "ja"


class TestOverlappingBlockMerge:
    """重複ブロックマージのテスト"""

    @pytest.fixture
    def overlapping_pdf_file(self, temp_dir):
        """重複するテキストブロックを持つPDFを作成"""
        try:
            import fitz

            pdf_path = temp_dir / "overlapping.pdf"
            doc = fitz.open()
            page = doc.new_page(width=595, height=842)

            # 重複する位置にテキストを挿入
            # Block A: 大きい範囲
            page.insert_text((50, 100), "Context Task:", fontsize=12)
            # Block B: Block Aと重複する位置に別テキスト
            page.insert_text((67, 100), "Task", fontsize=12)

            # 離れた位置にテキスト
            page.insert_text((50, 200), "Separate Text", fontsize=12)

            doc.save(str(pdf_path))
            doc.close()
            return pdf_path
        except ImportError:
            pytest.skip("PyMuPDF not installed")

    def test_merge_overlapping_enabled(self, overlapping_pdf_file):
        """正常系: 重複ブロックのマージが有効"""
        from modules.pdf_reader import PDFReader

        reader = PDFReader(merge_overlapping=True)
        reader.open(str(overlapping_pdf_file))
        page_data = reader.get_page(0)

        # 重複ブロックがマージされ、ブロック数が減少していること
        block_count_merged = len(page_data.text_blocks)

        reader.close()

        # マージ無効で再読み込み
        reader2 = PDFReader(merge_overlapping=False)
        reader2.open(str(overlapping_pdf_file))
        page_data2 = reader2.get_page(0)
        block_count_unmerged = len(page_data2.text_blocks)
        reader2.close()

        # マージ有効時のブロック数はマージ無効時以下
        assert block_count_merged <= block_count_unmerged

    def test_merge_overlapping_disabled(self, overlapping_pdf_file):
        """正常系: 重複ブロックのマージが無効"""
        from modules.pdf_reader import PDFReader

        reader = PDFReader(merge_overlapping=False)
        reader.open(str(overlapping_pdf_file))
        page_data = reader.get_page(0)

        # すべてのブロックが保持されること
        assert len(page_data.text_blocks) >= 1

        reader.close()

    def test_overlap_ratio_calculation(self):
        """正常系: 重複率の計算"""
        from modules.pdf_reader import PDFReader
        from modules.layout_manager import BoundingBox

        reader = PDFReader()

        # 完全に重複するbbox
        bbox1 = BoundingBox(0, 0, 100, 100)
        bbox2 = BoundingBox(0, 0, 50, 50)
        ratio = reader._calculate_overlap_ratio(bbox1, bbox2)
        assert ratio == 1.0  # 小さい方が完全に内包

        # 部分的に重複するbbox
        bbox3 = BoundingBox(0, 0, 100, 100)
        bbox4 = BoundingBox(50, 50, 150, 150)
        ratio2 = reader._calculate_overlap_ratio(bbox3, bbox4)
        assert 0 < ratio2 < 1.0

        # 重複しないbbox
        bbox5 = BoundingBox(0, 0, 50, 50)
        bbox6 = BoundingBox(100, 100, 150, 150)
        ratio3 = reader._calculate_overlap_ratio(bbox5, bbox6)
        assert ratio3 == 0.0


class TestPDFReaderExceptions:
    """PDFReader例外クラスのテスト"""

    def test_pdf_read_error_exists(self):
        """PDFReadError例外が存在"""
        from modules.pdf_reader import PDFReadError

        assert PDFReadError is not None

    def test_encrypted_pdf_error_exists(self):
        """EncryptedPDFError例外が存在"""
        from modules.pdf_reader import EncryptedPDFError

        assert EncryptedPDFError is not None

    def test_corrupted_pdf_error_exists(self):
        """CorruptedPDFError例外が存在"""
        from modules.pdf_reader import CorruptedPDFError

        assert CorruptedPDFError is not None

    def test_encrypted_pdf_error_is_subclass(self):
        """EncryptedPDFErrorがPDFReadErrorのサブクラス"""
        from modules.pdf_reader import PDFReadError, EncryptedPDFError

        assert issubclass(EncryptedPDFError, PDFReadError)

    def test_corrupted_pdf_error_is_subclass(self):
        """CorruptedPDFErrorがPDFReadErrorのサブクラス"""
        from modules.pdf_reader import PDFReadError, CorruptedPDFError

        assert issubclass(CorruptedPDFError, PDFReadError)


class TestExtractSortedSpans:
    """extract_sorted_spansメソッドのテスト"""

    @pytest.fixture
    def multi_span_pdf_file(self, temp_dir):
        """複数のspanを持つテスト用PDFを作成"""
        try:
            import fitz

            pdf_path = temp_dir / "multi_span.pdf"
            doc = fitz.open()
            page = doc.new_page(width=595, height=842)

            # 異なる位置にテキストを挿入（ソートテスト用）
            # 上から下、左から右の順で配置
            page.insert_text((100, 100), "First", fontsize=12)  # 左上
            page.insert_text((300, 100), "Second", fontsize=12)  # 右上
            page.insert_text((100, 200), "Third", fontsize=12)  # 左下
            page.insert_text((300, 200), "Fourth", fontsize=12)  # 右下

            doc.save(str(pdf_path))
            doc.close()
            return pdf_path
        except ImportError:
            pytest.skip("PyMuPDF not installed")

    def test_extract_sorted_spans_returns_list(self, multi_span_pdf_file):
        """正常系: SpanInfoのリストを返す"""
        from modules.pdf_reader import PDFReader

        reader = PDFReader()
        reader.open(str(multi_span_pdf_file))
        spans = reader.extract_sorted_spans(0)

        assert isinstance(spans, list)
        assert len(spans) > 0

        reader.close()

    def test_extract_sorted_spans_sorted_by_position(self, multi_span_pdf_file):
        """正常系: 位置順（y0, x0）でソートされる"""
        from modules.pdf_reader import PDFReader

        reader = PDFReader()
        reader.open(str(multi_span_pdf_file))
        spans = reader.extract_sorted_spans(0)

        # y座標 → x座標の順でソートされていることを確認
        for i in range(1, len(spans)):
            prev = spans[i - 1]
            curr = spans[i]
            # y0が小さいか、y0が同じならx0が小さい方が先
            assert (prev.bbox.y0, prev.bbox.x0) <= (curr.bbox.y0, curr.bbox.x0)

        reader.close()

    def test_extract_sorted_spans_has_index(self, multi_span_pdf_file):
        """正常系: 各spanにインデックスが付与される"""
        from modules.pdf_reader import PDFReader

        reader = PDFReader()
        reader.open(str(multi_span_pdf_file))
        spans = reader.extract_sorted_spans(0)

        for i, span in enumerate(spans):
            assert span.index == i

        reader.close()

    def test_extract_sorted_spans_has_span_info(self, multi_span_pdf_file):
        """正常系: SpanInfoに必要な情報が含まれる"""
        from modules.pdf_reader import PDFReader
        from modules.layout_manager import SpanInfo, BoundingBox, FontInfo

        reader = PDFReader()
        reader.open(str(multi_span_pdf_file))
        spans = reader.extract_sorted_spans(0)

        for span in spans:
            assert isinstance(span, SpanInfo)
            assert isinstance(span.text, str)
            assert len(span.text) > 0
            assert isinstance(span.bbox, BoundingBox)
            assert isinstance(span.font, FontInfo)

        reader.close()

    def test_extract_sorted_spans_no_document_open(self):
        """異常系: ドキュメントが開かれていない"""
        from modules.pdf_reader import PDFReader, PDFReadError

        reader = PDFReader()

        with pytest.raises(PDFReadError):
            reader.extract_sorted_spans(0)

    def test_extract_sorted_spans_empty_whitespace_filtered(self, temp_dir):
        """正常系: 空白のみのspanはフィルタリングされる"""
        try:
            import fitz

            pdf_path = temp_dir / "whitespace.pdf"
            doc = fitz.open()
            page = doc.new_page(width=595, height=842)

            # 通常のテキスト
            page.insert_text((100, 100), "Visible", fontsize=12)
            # 空白のみのテキスト（strip()で空になる）は挿入しても
            # PDF内部では別spanになる可能性があるが、フィルタされる

            doc.save(str(pdf_path))
            doc.close()

            from modules.pdf_reader import PDFReader

            reader = PDFReader()
            reader.open(str(pdf_path))
            spans = reader.extract_sorted_spans(0)

            # 空白のみのspanが含まれていないことを確認
            for span in spans:
                assert span.text.strip() != ""

            reader.close()
        except ImportError:
            pytest.skip("PyMuPDF not installed")

    def test_extract_sorted_spans_font_info(self, temp_dir):
        """正常系: フォント情報が正しく抽出される"""
        try:
            import fitz

            pdf_path = temp_dir / "font_info.pdf"
            doc = fitz.open()
            page = doc.new_page(width=595, height=842)

            # 異なるフォントサイズでテキストを挿入
            page.insert_text((100, 100), "Small", fontsize=10)
            page.insert_text((100, 150), "Large", fontsize=20)

            doc.save(str(pdf_path))
            doc.close()

            from modules.pdf_reader import PDFReader

            reader = PDFReader()
            reader.open(str(pdf_path))
            spans = reader.extract_sorted_spans(0)

            # フォントサイズが設定されていることを確認
            for span in spans:
                assert span.font.size > 0
                assert isinstance(span.font.name, str)

            reader.close()
        except ImportError:
            pytest.skip("PyMuPDF not installed")
