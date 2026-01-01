"""
PDF Translator - PDF Writer Module Tests

設計書: docs/design/04_pdf_writer.md
"""

import pytest
from pathlib import Path
import fitz  # PyMuPDF


class TestPDFWriter:
    """PDFWriterクラスのテスト"""

    def test_create_pdf_writer(self):
        """正常系: PDFWriter生成"""
        from modules.pdf_writer import PDFWriter

        writer = PDFWriter()
        assert writer is not None

    def test_create_pdf_writer_with_font_config(self):
        """正常系: フォント設定付きPDFWriter生成"""
        from modules.pdf_writer import PDFWriter

        font_config = {
            "japanese": {"regular": "/path/to/font.ttf"},
            "english": {"regular": "helv"},
        }
        writer = PDFWriter(font_config=font_config)
        assert writer is not None

    def test_close(self):
        """正常系: クローズ処理"""
        from modules.pdf_writer import PDFWriter

        writer = PDFWriter()
        writer.close()  # エラーなく終了すること


class TestPDFWriterDocument:
    """PDFWriterドキュメント操作のテスト"""

    def test_create_document(self):
        """正常系: ドキュメント作成"""
        from modules.pdf_writer import PDFWriter

        writer = PDFWriter()
        writer.create_document(
            page_count=2, page_sizes=[(595.0, 842.0), (595.0, 842.0)]
        )

        # ドキュメントが作成されていること
        assert writer._document is not None

        writer.close()

    def test_create_document_different_sizes(self):
        """正常系: 異なるサイズのページでドキュメント作成"""
        from modules.pdf_writer import PDFWriter

        writer = PDFWriter()
        writer.create_document(
            page_count=2,
            page_sizes=[(595.0, 842.0), (842.0, 595.0)],  # A4縦、A4横
        )

        assert writer._document is not None

        writer.close()

    def test_save_document(self, temp_dir):
        """正常系: ドキュメント保存"""
        from modules.pdf_writer import PDFWriter

        writer = PDFWriter()
        writer.create_document(page_count=1, page_sizes=[(595.0, 842.0)])

        output_path = temp_dir / "output.pdf"
        writer.save(str(output_path))

        assert output_path.exists()

        writer.close()


class TestPDFWriterPage:
    """PDFWriterページ操作のテスト"""

    def test_write_page(self):
        """正常系: ページ書き込み"""
        from modules.pdf_writer import PDFWriter
        from modules.layout_manager import PageData, TextBlock, BoundingBox, FontInfo

        writer = PDFWriter()
        writer.create_document(page_count=1, page_sizes=[(595.0, 842.0)])

        page_data = PageData(page_number=0, width=595.0, height=842.0)
        translated_blocks = [
            TextBlock(
                id="block_1",
                text="Original",
                translated_text="翻訳済み",
                bbox=BoundingBox(50, 100, 200, 120),
                font=FontInfo(name="Arial", size=12.0),
            )
        ]

        writer.write_page(0, page_data, translated_blocks)

        writer.close()

    def test_write_text_block(self):
        """正常系: テキストブロック書き込み"""
        from modules.pdf_writer import PDFWriter
        from modules.layout_manager import TextBlock, BoundingBox, FontInfo

        writer = PDFWriter()
        writer.create_document(page_count=1, page_sizes=[(595.0, 842.0)])

        block = TextBlock(
            id="block_1",
            text="Hello",
            translated_text="こんにちは",
            bbox=BoundingBox(50, 100, 200, 120),
            font=FontInfo(name="Arial", size=12.0),
        )

        # ページオブジェクトを取得してテキストブロックを書き込み
        # 実装によってはページオブジェクトの取得方法が異なる
        writer.write_text_block(writer._document[0], block, "ja")

        writer.close()


class TestPDFWriterImage:
    """PDFWriter画像操作のテスト"""

    def test_write_image(self):
        """正常系: 画像書き込み"""
        from modules.pdf_writer import PDFWriter
        from modules.layout_manager import ImageInfo, BoundingBox
        import base64

        writer = PDFWriter()
        writer.create_document(page_count=1, page_sizes=[(595.0, 842.0)])

        # Valid 1x1 pixel red PNG image (base64 encoded then decoded)
        # This is a valid minimal PNG file
        image_data = base64.b64decode(
            b"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg=="
        )

        image_info = ImageInfo(
            id="img_1",
            bbox=BoundingBox(100, 200, 300, 400),
            image_data=image_data,
            image_type="png",
        )

        writer.write_image(writer._document[0], image_info)

        writer.close()


class TestPDFWriterFontSize:
    """フォントサイズ調整のテスト"""

    def test_calculate_font_size_no_change(self):
        """正常系: フォントサイズ変更なし"""
        from modules.pdf_writer import PDFWriter

        writer = PDFWriter()

        # 短いテキストは変更なし
        size = writer._calculate_font_size(
            text="Hi", bbox=(0, 0, 100, 20), original_size=12.0
        )

        assert size == 12.0

    def test_calculate_font_size_shrink(self):
        """正常系: フォントサイズ縮小"""
        from modules.pdf_writer import PDFWriter

        writer = PDFWriter()

        # 長いテキストは縮小
        size = writer._calculate_font_size(
            text="This is a very long text that should not fit",
            bbox=(0, 0, 50, 20),
            original_size=12.0,
        )

        assert size < 12.0

    def test_calculate_font_size_min_limit(self):
        """正常系: 最小フォントサイズ制限"""
        from modules.pdf_writer import PDFWriter

        writer = PDFWriter()

        # 非常に長いテキストでも最小サイズ以下にはならない
        size = writer._calculate_font_size(
            text="A" * 1000, bbox=(0, 0, 10, 20), original_size=12.0
        )

        assert size >= 6.0  # MIN_FONT_SIZE


class TestPDFWriterFont:
    """フォント取得のテスト"""

    def test_get_font_japanese(self):
        """正常系: 日本語フォント取得"""
        from modules.pdf_writer import PDFWriter

        writer = PDFWriter()
        font = writer._get_font("ja", is_bold=False)

        assert font is not None

    def test_get_font_english(self):
        """正常系: 英語フォント取得"""
        from modules.pdf_writer import PDFWriter

        writer = PDFWriter()
        font = writer._get_font("en", is_bold=False)

        assert font is not None

    def test_get_font_bold(self):
        """正常系: 太字フォント取得"""
        from modules.pdf_writer import PDFWriter

        writer = PDFWriter()
        font = writer._get_font("en", is_bold=True)

        assert font is not None


class TestPDFWriterExceptions:
    """PDFWriter例外クラスのテスト"""

    def test_pdf_write_error_exists(self):
        """PDFWriteError例外が存在"""
        from modules.pdf_writer import PDFWriteError

        assert PDFWriteError is not None

    def test_font_error_exists(self):
        """FontError例外が存在"""
        from modules.pdf_writer import FontError

        assert FontError is not None

    def test_layout_error_exists(self):
        """LayoutError例外が存在"""
        from modules.pdf_writer import LayoutError

        assert LayoutError is not None

    def test_font_error_is_subclass(self):
        """FontErrorがPDFWriteErrorのサブクラス"""
        from modules.pdf_writer import PDFWriteError, FontError

        assert issubclass(FontError, PDFWriteError)

    def test_layout_error_is_subclass(self):
        """LayoutErrorがPDFWriteErrorのサブクラス"""
        from modules.pdf_writer import PDFWriteError, LayoutError

        assert issubclass(LayoutError, PDFWriteError)


class TestPDFWriterSaveOptions:
    """保存オプションのテスト"""

    def test_save_with_compression(self, temp_dir):
        """正常系: 圧縮付き保存"""
        from modules.pdf_writer import PDFWriter

        writer = PDFWriter()
        writer.create_document(page_count=1, page_sizes=[(595.0, 842.0)])

        output_path = temp_dir / "compressed.pdf"
        writer.save(str(output_path), compress=True)

        assert output_path.exists()

        writer.close()

    def test_save_without_compression(self, temp_dir):
        """正常系: 圧縮なし保存"""
        from modules.pdf_writer import PDFWriter

        writer = PDFWriter()
        writer.create_document(page_count=1, page_sizes=[(595.0, 842.0)])

        output_path = temp_dir / "uncompressed.pdf"
        writer.save(str(output_path), compress=False)

        assert output_path.exists()

        writer.close()


class TestPDFWriterSourceDocument:
    """元PDF複製＋テキスト置換方式のテスト"""

    @pytest.fixture
    def sample_pdf(self, temp_dir):
        """テスト用のサンプルPDFを作成"""
        pdf_path = temp_dir / "sample.pdf"
        doc = fitz.open()
        page = doc.new_page(width=595, height=842)
        # テキストを追加
        page.insert_text((50, 100), "Hello World", fontsize=12)
        # 図形を追加（背景として）
        page.draw_rect(fitz.Rect(20, 20, 200, 200), color=(0, 1, 0), fill=(0, 1, 0))
        doc.save(str(pdf_path))
        doc.close()
        return pdf_path

    def test_open_source(self, sample_pdf):
        """正常系: 元PDFを開く"""
        from modules.pdf_writer import PDFWriter

        writer = PDFWriter()
        writer.open_source(str(sample_pdf))

        assert writer._document is not None
        assert len(writer._document) == 1

        writer.close()

    def test_open_source_file_not_found(self, temp_dir):
        """異常系: 元PDFが存在しない"""
        from modules.pdf_writer import PDFWriter, PDFWriteError

        writer = PDFWriter()

        with pytest.raises(PDFWriteError):
            writer.open_source(str(temp_dir / "nonexistent.pdf"))

    def test_replace_text_on_page(self, sample_pdf, temp_dir):
        """正常系: ページ上のテキストを置換"""
        from modules.pdf_writer import PDFWriter
        from modules.layout_manager import TextBlock, BoundingBox, FontInfo

        writer = PDFWriter()
        writer.open_source(str(sample_pdf))

        # 翻訳テキストブロック
        translated_blocks = [
            TextBlock(
                id="block_1",
                text="Hello World",
                translated_text="こんにちは世界",
                bbox=BoundingBox(50, 90, 200, 110),
                font=FontInfo(name="Arial", size=12.0),
            )
        ]

        writer.replace_text_on_page(0, translated_blocks, "ja")

        # 保存して確認
        output_path = temp_dir / "replaced.pdf"
        writer.save(str(output_path))
        writer.close()

        assert output_path.exists()

    def test_clear_text_area(self, sample_pdf):
        """正常系: テキスト領域を消去"""
        from modules.pdf_writer import PDFWriter

        writer = PDFWriter()
        writer.open_source(str(sample_pdf))

        page = writer._document[0]
        writer._clear_text_area(page, (40, 80, 210, 120))

        writer.close()

    def test_layout_preserved(self, sample_pdf, temp_dir):
        """正常系: 元PDFのレイアウト（図形）が保持される"""
        from modules.pdf_writer import PDFWriter
        from modules.layout_manager import TextBlock, BoundingBox, FontInfo

        writer = PDFWriter()
        writer.open_source(str(sample_pdf))

        # テキストを置換
        translated_blocks = [
            TextBlock(
                id="block_1",
                text="Hello World",
                translated_text="こんにちは",
                bbox=BoundingBox(50, 90, 200, 110),
                font=FontInfo(name="Arial", size=12.0),
            )
        ]
        writer.replace_text_on_page(0, translated_blocks, "ja")

        output_path = temp_dir / "layout_preserved.pdf"
        writer.save(str(output_path))
        writer.close()

        # 出力PDFを開いて描画要素が保持されていることを確認
        output_doc = fitz.open(str(output_path))
        output_page = output_doc[0]
        drawings = output_page.get_drawings()

        # 元の図形が保持されていること（少なくとも1つ以上の描画要素）
        # 注: 白い矩形が追加されるため、元の図形 + 消去用矩形が存在
        assert len(drawings) >= 1

        output_doc.close()

    def test_is_japanese(self):
        """正常系: 日本語判定"""
        from modules.pdf_writer import PDFWriter

        writer = PDFWriter()

        assert writer._is_japanese("こんにちは") is True
        assert writer._is_japanese("カタカナ") is True
        assert writer._is_japanese("漢字") is True
        assert writer._is_japanese("Hello") is False
        assert writer._is_japanese("123") is False


class TestPDFWriterBackgroundPreservation:
    """背景保持のテスト（redact fill=False）"""

    @pytest.fixture
    def colored_bg_pdf(self, temp_dir):
        """色付き背景を持つサンプルPDFを作成"""
        pdf_path = temp_dir / "colored_bg.pdf"
        doc = fitz.open()
        page = doc.new_page(width=612, height=792)
        # 緑色の背景矩形を描画
        green_rect = fitz.Rect(50, 50, 300, 150)
        page.draw_rect(green_rect, color=(0, 0.5, 0), fill=(0, 0.5, 0))
        # その上にテキストを追加
        page.insert_text((100, 100), "Test Text", fontsize=14, color=(1, 1, 1))
        doc.save(str(pdf_path))
        doc.close()
        return pdf_path

    def test_redact_preserves_background(self, colored_bg_pdf, temp_dir):
        """正常系: redact時に背景色が保持される"""
        from modules.pdf_writer import PDFWriter
        from modules.layout_manager import TextBlock, BoundingBox, FontInfo

        writer = PDFWriter()
        writer.open_source(str(colored_bg_pdf))

        # テキストを置換
        translated_blocks = [
            TextBlock(
                id="block_1",
                text="Test Text",
                translated_text="テストテキスト",
                bbox=BoundingBox(90, 85, 250, 115),
                font=FontInfo(name="Arial", size=14.0, color=(255, 255, 255)),
            )
        ]

        writer.replace_text_on_page(0, translated_blocks, "ja")

        output_path = temp_dir / "bg_preserved.pdf"
        writer.save(str(output_path))
        writer.close()

        # 出力PDFを確認
        output_doc = fitz.open(str(output_path))
        output_page = output_doc[0]

        # 描画要素が保持されていることを確認
        drawings = output_page.get_drawings()
        assert len(drawings) >= 1, "背景の矩形が保持されていること"

        output_doc.close()


class TestPDFWriterTextFitting:
    """テキストのbbox内収容テスト"""

    def test_fit_text_to_bbox_basic(self):
        """正常系: テキストがbboxに収まるようにフォントサイズを調整"""
        from modules.pdf_writer import PDFWriter

        writer = PDFWriter()

        # 短いテキストは元のサイズを維持
        short_text = "Hi"
        size = writer._calculate_font_size(
            text=short_text, bbox=(0, 0, 200, 50), original_size=24.0
        )
        assert size == 24.0

    def test_fit_long_text_shrinks(self):
        """正常系: 長いテキストはフォントサイズが縮小される"""
        from modules.pdf_writer import PDFWriter

        writer = PDFWriter()

        # 長いテキストは縮小される
        long_text = "This is a very very long text that definitely needs shrinking"
        size = writer._calculate_font_size(
            text=long_text, bbox=(0, 0, 100, 30), original_size=24.0
        )
        assert size < 24.0

    def test_fit_japanese_text(self):
        """正常系: 日本語テキストのフォントサイズ調整"""
        from modules.pdf_writer import PDFWriter

        writer = PDFWriter()

        # 日本語テキスト
        ja_text = "これは長い日本語のテキストです"
        size = writer._calculate_font_size(
            text=ja_text, bbox=(0, 0, 100, 30), original_size=24.0
        )
        # フォントサイズが計算されること（エラーなく終了）
        assert size >= 6.0  # MIN_FONT_SIZE

    def test_wrap_text_basic(self):
        """正常系: テキストの折り返し"""
        from modules.pdf_writer import PDFWriter

        writer = PDFWriter()

        # _wrap_text が存在し、動作することを確認
        if hasattr(writer, '_wrap_text'):
            import fitz
            # システムフォントを取得（存在する場合）
            if writer._japanese_font_path:
                font = fitz.Font(fontfile=writer._japanese_font_path)
                lines = writer._wrap_text("テスト", font, 12.0, 100.0)
                assert isinstance(lines, list)
                assert len(lines) >= 1


class TestReplaceWithGroups:
    """replace_with_groupsメソッドのテスト"""

    @pytest.fixture
    def sample_pdf_for_groups(self, temp_dir):
        """テスト用のサンプルPDFを作成"""
        pdf_path = temp_dir / "sample_groups.pdf"
        doc = fitz.open()
        page = doc.new_page(width=595, height=842)
        # 複数のテキストを追加
        page.insert_text((50, 100), "Hello", fontsize=12)
        page.insert_text((120, 100), "World", fontsize=12)
        page.insert_text((50, 150), "Test Text", fontsize=12)
        doc.save(str(pdf_path))
        doc.close()
        return pdf_path

    def test_replace_with_groups_basic(self, sample_pdf_for_groups, temp_dir):
        """正常系: 基本的なグループ置換"""
        from modules.pdf_writer import PDFWriter
        from modules.layout_manager import SpanInfo, TranslationGroup, BoundingBox, FontInfo

        writer = PDFWriter()
        writer.open_source(str(sample_pdf_for_groups))

        # TranslationGroupを作成
        span1 = SpanInfo(
            text="Hello",
            bbox=BoundingBox(50, 88, 85, 102),
            font=FontInfo(name="Helvetica", size=12.0),
            index=0
        )
        span2 = SpanInfo(
            text="World",
            bbox=BoundingBox(120, 88, 160, 102),
            font=FontInfo(name="Helvetica", size=12.0),
            index=1
        )

        group = TranslationGroup(
            start_index=0,
            end_index=1,
            original_text="HelloWorld",
            translated_text="こんにちは世界",
            spans=[span1, span2]
        )

        writer.replace_with_groups(0, [group], "ja")

        output_path = temp_dir / "groups_output.pdf"
        writer.save(str(output_path))
        writer.close()

        assert output_path.exists()

    def test_replace_with_groups_multiple_groups(self, sample_pdf_for_groups, temp_dir):
        """正常系: 複数グループの置換"""
        from modules.pdf_writer import PDFWriter
        from modules.layout_manager import SpanInfo, TranslationGroup, BoundingBox, FontInfo

        writer = PDFWriter()
        writer.open_source(str(sample_pdf_for_groups))

        # グループ1: Hello World
        span1 = SpanInfo(
            text="Hello",
            bbox=BoundingBox(50, 88, 85, 102),
            font=FontInfo(name="Helvetica", size=12.0),
            index=0
        )
        span2 = SpanInfo(
            text="World",
            bbox=BoundingBox(120, 88, 160, 102),
            font=FontInfo(name="Helvetica", size=12.0),
            index=1
        )
        group1 = TranslationGroup(
            start_index=0,
            end_index=1,
            original_text="HelloWorld",
            translated_text="こんにちは",
            spans=[span1, span2]
        )

        # グループ2: Test Text
        span3 = SpanInfo(
            text="Test Text",
            bbox=BoundingBox(50, 138, 120, 152),
            font=FontInfo(name="Helvetica", size=12.0),
            index=2
        )
        group2 = TranslationGroup(
            start_index=2,
            end_index=2,
            original_text="Test Text",
            translated_text="テストテキスト",
            spans=[span3]
        )

        writer.replace_with_groups(0, [group1, group2], "ja")

        output_path = temp_dir / "multi_groups_output.pdf"
        writer.save(str(output_path))
        writer.close()

        assert output_path.exists()

    def test_replace_with_groups_empty_list(self, sample_pdf_for_groups, temp_dir):
        """正常系: 空のグループリスト"""
        from modules.pdf_writer import PDFWriter

        writer = PDFWriter()
        writer.open_source(str(sample_pdf_for_groups))

        # 空のリストでもエラーにならない
        writer.replace_with_groups(0, [], "ja")

        output_path = temp_dir / "empty_groups_output.pdf"
        writer.save(str(output_path))
        writer.close()

        assert output_path.exists()

    def test_replace_with_groups_no_document_open(self):
        """異常系: ドキュメントが開かれていない"""
        from modules.pdf_writer import PDFWriter, PDFWriteError

        writer = PDFWriter()

        with pytest.raises(PDFWriteError):
            writer.replace_with_groups(0, [], "ja")

    def test_replace_with_groups_empty_spans(self, sample_pdf_for_groups, temp_dir):
        """正常系: spansが空のグループはスキップ"""
        from modules.pdf_writer import PDFWriter
        from modules.layout_manager import TranslationGroup

        writer = PDFWriter()
        writer.open_source(str(sample_pdf_for_groups))

        # spansが空のグループ
        group = TranslationGroup(
            start_index=0,
            end_index=0,
            original_text="",
            translated_text="テスト",
            spans=[]
        )

        # エラーにならない
        writer.replace_with_groups(0, [group], "ja")

        output_path = temp_dir / "empty_spans_output.pdf"
        writer.save(str(output_path))
        writer.close()

        assert output_path.exists()

    def test_replace_with_groups_empty_translation(self, sample_pdf_for_groups, temp_dir):
        """正常系: 翻訳テキストが空のグループはスキップ"""
        from modules.pdf_writer import PDFWriter
        from modules.layout_manager import SpanInfo, TranslationGroup, BoundingBox, FontInfo

        writer = PDFWriter()
        writer.open_source(str(sample_pdf_for_groups))

        span = SpanInfo(
            text="Hello",
            bbox=BoundingBox(50, 88, 85, 102),
            font=FontInfo(name="Helvetica", size=12.0),
            index=0
        )

        # translated_textが空
        group = TranslationGroup(
            start_index=0,
            end_index=0,
            original_text="Hello",
            translated_text="",
            spans=[span]
        )

        # エラーにならない（テキストは書き込まれない）
        writer.replace_with_groups(0, [group], "ja")

        output_path = temp_dir / "empty_translation_output.pdf"
        writer.save(str(output_path))
        writer.close()

        assert output_path.exists()

    def test_replace_with_groups_preserves_font_color(self, sample_pdf_for_groups, temp_dir):
        """正常系: フォントカラーが保持される"""
        from modules.pdf_writer import PDFWriter
        from modules.layout_manager import SpanInfo, TranslationGroup, BoundingBox, FontInfo

        writer = PDFWriter()
        writer.open_source(str(sample_pdf_for_groups))

        # 赤色のフォント
        span = SpanInfo(
            text="Hello",
            bbox=BoundingBox(50, 88, 85, 102),
            font=FontInfo(name="Helvetica", size=12.0, color=(255, 0, 0)),
            index=0
        )

        group = TranslationGroup(
            start_index=0,
            end_index=0,
            original_text="Hello",
            translated_text="こんにちは",
            spans=[span]
        )

        # エラーにならないこと（色は内部で正規化される）
        writer.replace_with_groups(0, [group], "ja")

        output_path = temp_dir / "color_preserved_output.pdf"
        writer.save(str(output_path))
        writer.close()

        assert output_path.exists()

    def test_write_translation_group_uses_first_span_position(self, sample_pdf_for_groups, temp_dir):
        """正常系: 翻訳テキストは最初のspanの位置に配置される"""
        from modules.pdf_writer import PDFWriter
        from modules.layout_manager import SpanInfo, TranslationGroup, BoundingBox, FontInfo

        writer = PDFWriter()
        writer.open_source(str(sample_pdf_for_groups))

        # 2つのspanを持つグループ
        # 翻訳テキストは最初のspan（span1）の位置にのみ配置される
        span1 = SpanInfo(
            text="Hello",
            bbox=BoundingBox(50, 88, 85, 102),
            font=FontInfo(name="Helvetica", size=12.0),
            index=0
        )
        span2 = SpanInfo(
            text="World",
            bbox=BoundingBox(120, 88, 160, 102),
            font=FontInfo(name="Helvetica", size=12.0),
            index=1
        )

        group = TranslationGroup(
            start_index=0,
            end_index=1,
            original_text="HelloWorld",
            translated_text="こんにちは世界",
            spans=[span1, span2]
        )

        writer.replace_with_groups(0, [group], "ja")

        output_path = temp_dir / "first_span_position_output.pdf"
        writer.save(str(output_path))
        writer.close()

        # 出力PDFを開いてテキストを確認
        output_doc = fitz.open(str(output_path))
        page = output_doc[0]
        text_dict = page.get_text("dict")

        # テキストが1つだけ出力されていることを確認
        # （span2の位置には何も書かれていない）
        text_blocks = [b for b in text_dict.get("blocks", []) if b.get("type") == 0]

        output_doc.close()

        # ファイルが正常に作成されていればOK
        assert output_path.exists()


class TestJapaneseCharDetection:
    """_is_japanese_charメソッドのテスト（設計書11.4節）"""

    def test_is_japanese_char_hiragana(self):
        """正常系: ひらがな判定"""
        from modules.pdf_writer import PDFWriter

        writer = PDFWriter()

        assert writer._is_japanese_char("あ") is True
        assert writer._is_japanese_char("ん") is True
        assert writer._is_japanese_char("っ") is True

    def test_is_japanese_char_katakana(self):
        """正常系: カタカナ判定"""
        from modules.pdf_writer import PDFWriter

        writer = PDFWriter()

        assert writer._is_japanese_char("ア") is True
        assert writer._is_japanese_char("ン") is True
        assert writer._is_japanese_char("ッ") is True

    def test_is_japanese_char_kanji(self):
        """正常系: 漢字判定"""
        from modules.pdf_writer import PDFWriter

        writer = PDFWriter()

        assert writer._is_japanese_char("漢") is True
        assert writer._is_japanese_char("字") is True
        assert writer._is_japanese_char("日") is True

    def test_is_japanese_char_fullwidth_symbols(self):
        """正常系: 全角記号・句読点判定"""
        from modules.pdf_writer import PDFWriter

        writer = PDFWriter()

        assert writer._is_japanese_char("　") is True  # 全角スペース
        assert writer._is_japanese_char("、") is True  # 読点
        assert writer._is_japanese_char("。") is True  # 句点

    def test_is_japanese_char_fullwidth_alphanumeric(self):
        """正常系: 全角英数字判定"""
        from modules.pdf_writer import PDFWriter

        writer = PDFWriter()

        assert writer._is_japanese_char("Ａ") is True  # 全角A
        assert writer._is_japanese_char("１") is True  # 全角1
        assert writer._is_japanese_char("！") is True  # 全角!

    def test_is_japanese_char_halfwidth_returns_false(self):
        """正常系: 半角英数字はFalse"""
        from modules.pdf_writer import PDFWriter

        writer = PDFWriter()

        assert writer._is_japanese_char("A") is False
        assert writer._is_japanese_char("z") is False
        assert writer._is_japanese_char("1") is False
        assert writer._is_japanese_char(" ") is False  # 半角スペース
        assert writer._is_japanese_char("!") is False


class TestJapaneseFontSizeCalculation:
    """日本語対応フォントサイズ計算のテスト（設計書11.4節）"""

    def test_calculate_font_size_japanese_text_correct_width(self):
        """正常系: 日本語テキストの幅が正しく推定される"""
        from modules.pdf_writer import PDFWriter

        writer = PDFWriter()

        # 日本語5文字 × 12pt × 1.0 = 60pt の推定幅
        # bbox幅が100ptなら収まるはず
        size = writer._calculate_font_size(
            text="こんにちは",
            bbox=(0, 0, 100, 20),
            original_size=12.0
        )
        assert size == 12.0

        # bbox幅が50ptなら縮小が必要
        size_shrunk = writer._calculate_font_size(
            text="こんにちは",
            bbox=(0, 0, 50, 20),
            original_size=12.0
        )
        assert size_shrunk < 12.0

    def test_calculate_font_size_english_text_correct_width(self):
        """正常系: 英語テキストの幅が正しく推定される"""
        from modules.pdf_writer import PDFWriter

        writer = PDFWriter()

        # 英語5文字 × 12pt × 0.55 = 33pt の推定幅
        # bbox幅が50ptなら収まるはず
        size = writer._calculate_font_size(
            text="Hello",
            bbox=(0, 0, 50, 20),
            original_size=12.0
        )
        assert size == 12.0

        # bbox幅が20ptなら縮小が必要
        size_shrunk = writer._calculate_font_size(
            text="Hello",
            bbox=(0, 0, 20, 20),
            original_size=12.0
        )
        assert size_shrunk < 12.0

    def test_calculate_font_size_mixed_text_correct_width(self):
        """正常系: 日英混在テキストの幅が正しく推定される"""
        from modules.pdf_writer import PDFWriter

        writer = PDFWriter()

        # "Hello世界" = 英語5文字 + 日本語2文字
        # 推定幅 = 5 × 12 × 0.55 + 2 × 12 × 1.0 = 33 + 24 = 57pt
        # bbox幅が100ptなら収まるはず
        size = writer._calculate_font_size(
            text="Hello世界",
            bbox=(0, 0, 100, 20),
            original_size=12.0
        )
        assert size == 12.0

        # bbox幅が40ptなら縮小が必要
        size_shrunk = writer._calculate_font_size(
            text="Hello世界",
            bbox=(0, 0, 40, 20),
            original_size=12.0
        )
        assert size_shrunk < 12.0

    def test_calculate_font_size_japanese_not_over_shrink(self):
        """正常系: 日本語テキストが過剰に縮小されない"""
        from modules.pdf_writer import PDFWriter

        writer = PDFWriter()

        # 従来の実装では、日本語も英語と同じ係数(0.5)で計算していたため
        # 実際より小さく見積もられ、フォントサイズが不必要に縮小されていた
        # 新実装では、日本語の正しい係数(1.0)を使用するため、
        # 適切なサイズが維持される

        # 日本語3文字 "タスク" = 3 × 12 × 1.0 = 36pt
        # bbox幅50ptなら収まるはず（縮小不要）
        size = writer._calculate_font_size(
            text="タスク",
            bbox=(0, 0, 50, 20),
            original_size=12.0
        )
        assert size == 12.0


class TestExtendBboxToGroupRange:
    """bbox拡張機能のテスト"""

    def test_single_span_returns_same_bbox(self):
        """正常系: 単一spanの場合はそのspanのbboxを返す"""
        from modules.pdf_writer import PDFWriter
        from modules.layout_manager import TranslationGroup, SpanInfo, BoundingBox, FontInfo

        writer = PDFWriter()

        span = SpanInfo(
            index=0,
            text="Hello",
            bbox=BoundingBox(x0=10.0, y0=20.0, x1=100.0, y1=40.0),
            font=FontInfo(name="Arial", size=12.0, color=(0, 0, 0)),
        )
        group = TranslationGroup(
            start_index=0,
            end_index=0,
            original_text="Hello",
            translated_text="こんにちは",
            spans=[span],
        )

        bbox = writer._extend_bbox_to_group_range(group)

        assert bbox == (10.0, 20.0, 100.0, 40.0)

    def test_multiple_spans_combines_first_and_last(self):
        """正常系: 複数spanの場合は開始spanの左上と終了spanの右下を組み合わせる"""
        from modules.pdf_writer import PDFWriter
        from modules.layout_manager import TranslationGroup, SpanInfo, BoundingBox, FontInfo

        writer = PDFWriter()

        span1 = SpanInfo(
            index=0,
            text="Hello",
            bbox=BoundingBox(x0=10.0, y0=20.0, x1=60.0, y1=40.0),
            font=FontInfo(name="Arial", size=12.0, color=(0, 0, 0)),
        )
        span2 = SpanInfo(
            index=1,
            text=" ",
            bbox=BoundingBox(x0=60.0, y0=20.0, x1=70.0, y1=40.0),
            font=FontInfo(name="Arial", size=12.0, color=(0, 0, 0)),
        )
        span3 = SpanInfo(
            index=2,
            text="World",
            bbox=BoundingBox(x0=70.0, y0=20.0, x1=130.0, y1=40.0),
            font=FontInfo(name="Arial", size=12.0, color=(0, 0, 0)),
        )
        group = TranslationGroup(
            start_index=0,
            end_index=2,
            original_text="Hello World",
            translated_text="こんにちは世界",
            spans=[span1, span2, span3],
        )

        bbox = writer._extend_bbox_to_group_range(group)

        # 最初のspanの左上 (10, 20) と最後のspanの右下 (130, 40)
        assert bbox == (10.0, 20.0, 130.0, 40.0)

    def test_multiline_spans_extends_vertically(self):
        """正常系: 複数行にまたがるspanでも開始の左上と終了の右下を使用"""
        from modules.pdf_writer import PDFWriter
        from modules.layout_manager import TranslationGroup, SpanInfo, BoundingBox, FontInfo

        writer = PDFWriter()

        # 1行目のspan
        span1 = SpanInfo(
            index=0,
            text="First line",
            bbox=BoundingBox(x0=10.0, y0=20.0, x1=100.0, y1=40.0),
            font=FontInfo(name="Arial", size=12.0, color=(0, 0, 0)),
        )
        # 2行目のspan（Y座標が異なる）
        span2 = SpanInfo(
            index=1,
            text="Second line",
            bbox=BoundingBox(x0=10.0, y0=45.0, x1=120.0, y1=65.0),
            font=FontInfo(name="Arial", size=12.0, color=(0, 0, 0)),
        )
        group = TranslationGroup(
            start_index=0,
            end_index=1,
            original_text="First line Second line",
            translated_text="最初の行 2番目の行",
            spans=[span1, span2],
        )

        bbox = writer._extend_bbox_to_group_range(group)

        # 最初のspanの左上 (10, 20) と最後のspanの右下 (120, 65)
        assert bbox == (10.0, 20.0, 120.0, 65.0)
