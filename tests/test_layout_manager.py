"""
PDF Translator - Layout Manager Module Tests

設計書: docs/design/05_layout_manager.md
"""

import pytest
import json
from pathlib import Path


class TestBoundingBox:
    """BoundingBoxクラスのテスト"""

    def test_create_bounding_box(self):
        """正常系: BoundingBox生成"""
        from modules.layout_manager import BoundingBox

        bbox = BoundingBox(x0=50.0, y0=100.0, x1=200.0, y1=120.0)

        assert bbox.x0 == 50.0
        assert bbox.y0 == 100.0
        assert bbox.x1 == 200.0
        assert bbox.y1 == 120.0

    def test_bounding_box_width(self):
        """正常系: 幅の計算"""
        from modules.layout_manager import BoundingBox

        bbox = BoundingBox(x0=50.0, y0=100.0, x1=200.0, y1=120.0)

        assert bbox.width == 150.0

    def test_bounding_box_height(self):
        """正常系: 高さの計算"""
        from modules.layout_manager import BoundingBox

        bbox = BoundingBox(x0=50.0, y0=100.0, x1=200.0, y1=120.0)

        assert bbox.height == 20.0

    def test_bounding_box_center(self):
        """正常系: 中心座標の計算"""
        from modules.layout_manager import BoundingBox

        bbox = BoundingBox(x0=50.0, y0=100.0, x1=200.0, y1=120.0)
        center = bbox.center

        assert center == (125.0, 110.0)

    def test_bounding_box_to_tuple(self):
        """正常系: タプル変換"""
        from modules.layout_manager import BoundingBox

        bbox = BoundingBox(x0=50.0, y0=100.0, x1=200.0, y1=120.0)

        assert bbox.to_tuple() == (50.0, 100.0, 200.0, 120.0)

    def test_bounding_box_from_tuple(self):
        """正常系: タプルからの生成"""
        from modules.layout_manager import BoundingBox

        bbox = BoundingBox.from_tuple((50.0, 100.0, 200.0, 120.0))

        assert bbox.x0 == 50.0
        assert bbox.x1 == 200.0


class TestFontInfo:
    """FontInfoクラスのテスト"""

    def test_create_font_info(self):
        """正常系: FontInfo生成"""
        from modules.layout_manager import FontInfo

        font = FontInfo(name="NotoSansJP", size=12.0)

        assert font.name == "NotoSansJP"
        assert font.size == 12.0
        assert font.is_bold is False
        assert font.is_italic is False

    def test_font_info_with_style(self):
        """正常系: スタイル付きFontInfo"""
        from modules.layout_manager import FontInfo

        font = FontInfo(
            name="NotoSansJP",
            size=14.0,
            is_bold=True,
            is_italic=True,
            color=(255, 0, 0),
        )

        assert font.is_bold is True
        assert font.is_italic is True
        assert font.color == (255, 0, 0)

    def test_font_info_from_flags(self):
        """正常系: フラグからの生成"""
        from modules.layout_manager import FontInfo

        # flags: bit 4 = bold (16), bit 1 = italic (2)
        font = FontInfo.from_flags(
            name="Arial", size=12.0, flags=18, color=(0, 0, 0)  # 16 + 2 = bold + italic
        )

        assert font.is_bold is True
        assert font.is_italic is True


class TestTextBlock:
    """TextBlockクラスのテスト"""

    def test_create_text_block(self):
        """正常系: TextBlock生成"""
        from modules.layout_manager import TextBlock, BoundingBox, FontInfo

        block = TextBlock(
            id="block_000001",
            text="こんにちは",
            bbox=BoundingBox(50.0, 100.0, 200.0, 120.0),
            font=FontInfo(name="NotoSansJP", size=12.0),
        )

        assert block.id == "block_000001"
        assert block.text == "こんにちは"
        assert block.char_count == 5

    def test_text_block_with_translation(self):
        """正常系: 翻訳テキスト付きTextBlock"""
        from modules.layout_manager import TextBlock, BoundingBox, FontInfo

        block = TextBlock(
            id="block_000001",
            text="こんにちは",
            translated_text="Hello",
            bbox=BoundingBox(50.0, 100.0, 200.0, 120.0),
            font=FontInfo(name="NotoSansJP", size=12.0),
        )

        assert block.translated_text == "Hello"
        assert block.translated_char_count == 5

    def test_text_block_expansion_ratio(self):
        """正常系: 拡張率の計算"""
        from modules.layout_manager import TextBlock, BoundingBox, FontInfo

        block = TextBlock(
            id="block_000001",
            text="Hi",  # 2文字
            translated_text="こんにちは",  # 5文字
            bbox=BoundingBox(50.0, 100.0, 200.0, 120.0),
            font=FontInfo(name="NotoSansJP", size=12.0),
        )

        assert block.expansion_ratio == 2.5

    def test_text_block_expansion_ratio_no_translation(self):
        """正常系: 翻訳なしの拡張率"""
        from modules.layout_manager import TextBlock, BoundingBox, FontInfo

        block = TextBlock(
            id="block_000001",
            text="Hello",
            bbox=BoundingBox(50.0, 100.0, 200.0, 120.0),
            font=FontInfo(name="Arial", size=12.0),
        )

        assert block.expansion_ratio == 1.0


class TestPageData:
    """PageDataクラスのテスト"""

    def test_create_page_data(self):
        """正常系: PageData生成"""
        from modules.layout_manager import PageData

        page = PageData(page_number=0, width=595.0, height=842.0)

        assert page.page_number == 0
        assert page.width == 595.0
        assert page.height == 842.0
        assert page.rotation == 0
        assert len(page.text_blocks) == 0

    def test_page_data_size_property(self):
        """正常系: sizeプロパティ"""
        from modules.layout_manager import PageData

        page = PageData(page_number=0, width=595.0, height=842.0)

        assert page.size == (595.0, 842.0)

    def test_page_data_get_block_by_id(self):
        """正常系: IDでブロック取得"""
        from modules.layout_manager import PageData, TextBlock, BoundingBox, FontInfo

        page = PageData(page_number=0, width=595.0, height=842.0)
        block = TextBlock(
            id="block_000001",
            text="Test",
            bbox=BoundingBox(0, 0, 100, 20),
            font=FontInfo(name="Arial", size=12.0),
        )
        page.text_blocks.append(block)

        found = page.get_block_by_id("block_000001")
        assert found is not None
        assert found.text == "Test"

    def test_page_data_get_block_by_id_not_found(self):
        """正常系: 存在しないIDでブロック取得"""
        from modules.layout_manager import PageData

        page = PageData(page_number=0, width=595.0, height=842.0)

        found = page.get_block_by_id("nonexistent")
        assert found is None


class TestDocumentData:
    """DocumentDataクラスのテスト"""

    def test_create_document_data(self):
        """正常系: DocumentData生成"""
        from modules.layout_manager import DocumentData

        doc = DocumentData(file_path="/app/input/test.pdf", page_count=5)

        assert doc.file_path == "/app/input/test.pdf"
        assert doc.page_count == 5
        assert len(doc.pages) == 0


class TestLayoutManager:
    """LayoutManagerクラスのテスト"""

    def test_create_layout_manager(self):
        """正常系: LayoutManager生成"""
        from modules.layout_manager import LayoutManager

        manager = LayoutManager()

        assert manager.get_document() is None

    def test_set_and_get_document(self):
        """正常系: ドキュメント設定と取得"""
        from modules.layout_manager import LayoutManager, DocumentData

        manager = LayoutManager()
        doc = DocumentData(file_path="/app/input/test.pdf", page_count=1)
        manager.set_document(doc)

        assert manager.get_document() is not None
        assert manager.get_document().file_path == "/app/input/test.pdf"

    def test_generate_block_id_unique(self):
        """正常系: ブロックID生成（一意性）"""
        from modules.layout_manager import LayoutManager

        manager = LayoutManager()
        id1 = manager.generate_block_id()
        id2 = manager.generate_block_id()
        id3 = manager.generate_block_id()

        assert id1 != id2
        assert id2 != id3
        assert id1 != id3

    def test_generate_block_id_format(self):
        """正常系: ブロックIDフォーマット"""
        from modules.layout_manager import LayoutManager

        manager = LayoutManager()
        block_id = manager.generate_block_id()

        assert block_id.startswith("block_")

    def test_update_translated_text(self):
        """正常系: 翻訳テキスト更新"""
        from modules.layout_manager import (
            LayoutManager,
            DocumentData,
            PageData,
            TextBlock,
            BoundingBox,
            FontInfo,
        )

        manager = LayoutManager()
        doc = DocumentData(file_path="/test.pdf", page_count=1)
        page = PageData(page_number=0, width=595.0, height=842.0)
        block = TextBlock(
            id="block_000001",
            text="こんにちは",
            bbox=BoundingBox(0, 0, 100, 20),
            font=FontInfo(name="NotoSansJP", size=12.0),
        )
        page.text_blocks.append(block)
        doc.pages.append(page)
        manager.set_document(doc)

        manager.update_translated_text("block_000001", "Hello")

        updated_block = doc.pages[0].get_block_by_id("block_000001")
        assert updated_block.translated_text == "Hello"

    def test_calculate_adjusted_font_size_no_expansion(self):
        """正常系: フォントサイズ調整（拡張なし）"""
        from modules.layout_manager import (
            LayoutManager,
            TextBlock,
            BoundingBox,
            FontInfo,
        )

        manager = LayoutManager()
        block = TextBlock(
            id="block_000001",
            text="Hello",
            translated_text="Hi",  # 短くなった
            bbox=BoundingBox(0, 0, 100, 20),
            font=FontInfo(name="Arial", size=12.0),
        )

        adjusted = manager.calculate_adjusted_font_size(block)
        assert adjusted == 12.0  # 元のサイズを維持

    def test_calculate_adjusted_font_size_with_expansion(self):
        """正常系: フォントサイズ調整（拡張あり）"""
        from modules.layout_manager import (
            LayoutManager,
            TextBlock,
            BoundingBox,
            FontInfo,
        )

        manager = LayoutManager()
        block = TextBlock(
            id="block_000001",
            text="Hi",
            translated_text="Hello World!",  # 長くなった
            bbox=BoundingBox(0, 0, 100, 20),
            font=FontInfo(name="Arial", size=12.0),
        )

        adjusted = manager.calculate_adjusted_font_size(block)
        assert adjusted < 12.0  # 縮小される

    def test_calculate_adjusted_font_size_min_limit(self):
        """正常系: フォントサイズ調整（最小値制限）"""
        from modules.layout_manager import (
            LayoutManager,
            TextBlock,
            BoundingBox,
            FontInfo,
        )

        manager = LayoutManager()
        block = TextBlock(
            id="block_000001",
            text="A",
            translated_text="A" * 1000,  # 非常に長い
            bbox=BoundingBox(0, 0, 100, 20),
            font=FontInfo(name="Arial", size=12.0),
        )

        adjusted = manager.calculate_adjusted_font_size(block)
        assert adjusted >= 6.0  # 最小サイズ以上

    def test_get_layout_statistics(self):
        """正常系: 統計情報取得"""
        from modules.layout_manager import (
            LayoutManager,
            DocumentData,
            PageData,
            TextBlock,
            BoundingBox,
            FontInfo,
        )

        manager = LayoutManager()
        doc = DocumentData(file_path="/test.pdf", page_count=2)

        for i in range(2):
            page = PageData(page_number=i, width=595.0, height=842.0)
            block = TextBlock(
                id=f"block_{i}",
                text="Test",
                translated_text="テスト",
                bbox=BoundingBox(0, 0, 100, 20),
                font=FontInfo(name="Arial", size=12.0),
            )
            page.text_blocks.append(block)
            doc.pages.append(page)

        manager.set_document(doc)

        stats = manager.get_layout_statistics()

        assert stats["total_pages"] == 2
        assert stats["total_blocks"] == 2

    def test_to_dict(self):
        """正常系: 辞書形式にシリアライズ"""
        from modules.layout_manager import LayoutManager, DocumentData, PageData

        manager = LayoutManager()
        doc = DocumentData(file_path="/test.pdf", page_count=1)
        page = PageData(page_number=0, width=595.0, height=842.0)
        doc.pages.append(page)
        manager.set_document(doc)

        result = manager.to_dict()

        assert isinstance(result, dict)
        assert "file_path" in result
        assert "pages" in result

    def test_from_dict(self):
        """正常系: 辞書形式からデシリアライズ"""
        from modules.layout_manager import LayoutManager

        data = {
            "file_path": "/test.pdf",
            "page_count": 1,
            "pages": [{"page_number": 0, "width": 595.0, "height": 842.0, "rotation": 0, "text_blocks": [], "images": [], "drawings": []}],
        }

        manager = LayoutManager.from_dict(data)

        assert manager.get_document() is not None
        assert manager.get_document().file_path == "/test.pdf"

    def test_save_and_load_json(self, temp_dir):
        """正常系: JSONファイルへの保存と読み込み"""
        from modules.layout_manager import LayoutManager, DocumentData, PageData

        manager = LayoutManager()
        doc = DocumentData(file_path="/test.pdf", page_count=1)
        page = PageData(page_number=0, width=595.0, height=842.0)
        doc.pages.append(page)
        manager.set_document(doc)

        json_path = str(temp_dir / "layout.json")
        manager.save_to_json(json_path)

        loaded_manager = LayoutManager.load_from_json(json_path)

        assert loaded_manager.get_document() is not None
        assert loaded_manager.get_document().file_path == "/test.pdf"
