"""
PDF Translator - Pytest Configuration and Fixtures
"""

import pytest
from pathlib import Path
import tempfile
import os
import logging


@pytest.fixture(autouse=True)
def clean_env_and_logging():
    """各テスト前後で環境変数とロガーをクリーンアップ"""
    # Save original state
    original_env = os.environ.copy()

    yield

    # Restore environment variables
    os.environ.clear()
    os.environ.update(original_env)

    # Clear logging handlers to prevent file locking issues
    logger = logging.getLogger("pdf_translator")
    for handler in logger.handlers[:]:
        handler.close()
        logger.removeHandler(handler)


@pytest.fixture
def temp_dir():
    """一時ディレクトリを提供"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_pdf_path(temp_dir):
    """サンプルPDFファイルのパスを提供（実際のファイルは作成しない）"""
    return temp_dir / "sample.pdf"


@pytest.fixture
def output_pdf_path(temp_dir):
    """出力PDFファイルのパスを提供"""
    return temp_dir / "output.pdf"


@pytest.fixture
def mock_api_key():
    """モックAPIキーを提供"""
    return "sk-ant-api03-test-key-for-testing-purposes-only"


@pytest.fixture
def env_with_api_key(temp_dir, mock_api_key):
    """APIキーが設定された.envファイルを提供"""
    env_file = temp_dir / ".env"
    env_file.write_text(f"ANTHROPIC_API_KEY={mock_api_key}\n")
    return env_file


@pytest.fixture
def sample_japanese_text():
    """サンプル日本語テキスト"""
    return "こんにちは、世界！これはテストです。"


@pytest.fixture
def sample_english_text():
    """サンプル英語テキスト"""
    return "Hello, World! This is a test."


@pytest.fixture
def sample_text_block_data():
    """サンプルテキストブロックデータ"""
    return {
        "id": "block_000001",
        "text": "こんにちは",
        "bbox": (50.0, 100.0, 200.0, 120.0),
        "font_name": "NotoSansJP",
        "font_size": 12.0,
        "is_bold": False,
        "color": (0, 0, 0),
    }


@pytest.fixture
def sample_page_data():
    """サンプルページデータ"""
    return {
        "page_number": 0,
        "width": 595.0,
        "height": 842.0,
        "rotation": 0,
    }
