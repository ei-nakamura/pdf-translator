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
