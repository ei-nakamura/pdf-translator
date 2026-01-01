"""
PDF Translator - Config Module Tests

設計書: docs/design/06_config.md
"""

import pytest
import os
from pathlib import Path


class TestConfigLoader:
    """ConfigLoaderクラスのテスト"""

    def test_load_env_from_file(self, env_with_api_key):
        """正常系: .envファイルからの読み込み"""
        from config import ConfigLoader

        loader = ConfigLoader(env_file=str(env_with_api_key))
        loader.load_env()
        api_key = loader.get("ANTHROPIC_API_KEY")

        assert api_key is not None
        assert api_key.startswith("sk-ant-")

    def test_get_required_raises_on_missing(self):
        """異常系: 必須環境変数が未設定"""
        from config import ConfigLoader, MissingConfigError

        loader = ConfigLoader()
        with pytest.raises(MissingConfigError):
            loader.get_required("NONEXISTENT_VARIABLE_FOR_TEST")

    def test_get_with_default(self):
        """正常系: デフォルト値の適用"""
        from config import ConfigLoader

        loader = ConfigLoader()
        value = loader.get("NONEXISTENT_VARIABLE", default="default_value")

        assert value == "default_value"

    def test_get_int(self, temp_dir):
        """正常系: 整数値として取得"""
        from config import ConfigLoader

        env_file = temp_dir / ".env"
        env_file.write_text("TEST_INT=42\n")

        loader = ConfigLoader(env_file=str(env_file))
        loader.load_env()
        value = loader.get_int("TEST_INT", default=0)

        assert value == 42

    def test_get_int_invalid_raises(self, temp_dir):
        """異常系: 無効な整数値"""
        from config import ConfigLoader, InvalidConfigError

        env_file = temp_dir / ".env"
        env_file.write_text("TEST_INT=not_an_int\n")

        loader = ConfigLoader(env_file=str(env_file))
        loader.load_env()

        with pytest.raises(InvalidConfigError):
            loader.get_int("TEST_INT", default=0)

    def test_get_float(self, temp_dir):
        """正常系: 浮動小数点として取得"""
        from config import ConfigLoader

        env_file = temp_dir / ".env"
        env_file.write_text("TEST_FLOAT=3.14\n")

        loader = ConfigLoader(env_file=str(env_file))
        loader.load_env()
        value = loader.get_float("TEST_FLOAT", default=0.0)

        assert value == pytest.approx(3.14)

    def test_get_bool_true(self, temp_dir):
        """正常系: 真偽値として取得（true）"""
        from config import ConfigLoader

        env_file = temp_dir / ".env"
        env_file.write_text("TEST_BOOL=true\n")

        loader = ConfigLoader(env_file=str(env_file))
        loader.load_env()
        value = loader.get_bool("TEST_BOOL", default=False)

        assert value is True

    def test_get_bool_false(self, temp_dir):
        """正常系: 真偽値として取得（false）"""
        from config import ConfigLoader

        env_file = temp_dir / ".env"
        env_file.write_text("TEST_BOOL=false\n")

        loader = ConfigLoader(env_file=str(env_file))
        loader.load_env()
        value = loader.get_bool("TEST_BOOL", default=True)

        assert value is False

    def test_get_path(self, temp_dir):
        """正常系: パスとして取得"""
        from config import ConfigLoader

        env_file = temp_dir / ".env"
        env_file.write_text("TEST_PATH=/app/input\n")

        loader = ConfigLoader(env_file=str(env_file))
        loader.load_env()
        value = loader.get_path("TEST_PATH")

        assert value == Path("/app/input")


class TestAPIConfig:
    """APIConfigクラスのテスト"""

    def test_create_api_config(self, mock_api_key):
        """正常系: APIConfig生成"""
        from config import APIConfig

        config = APIConfig(api_key=mock_api_key)

        assert config.api_key == mock_api_key
        assert config.model == "claude-3-5-sonnet-20241022"
        assert config.max_tokens == 4000
        assert config.temperature == 0.3

    def test_api_config_custom_values(self, mock_api_key):
        """正常系: カスタム値でAPIConfig生成"""
        from config import APIConfig

        config = APIConfig(
            api_key=mock_api_key,
            model="claude-3-haiku-20240307",
            max_tokens=2000,
            temperature=0.5,
        )

        assert config.model == "claude-3-haiku-20240307"
        assert config.max_tokens == 2000
        assert config.temperature == 0.5


class TestPDFConfig:
    """PDFConfigクラスのテスト"""

    def test_create_pdf_config_defaults(self):
        """正常系: デフォルト値でPDFConfig生成"""
        from config import PDFConfig

        config = PDFConfig()

        assert config.input_dir == Path("/app/input")
        assert config.output_dir == Path("/app/output")
        assert config.max_file_size == 104857600
        assert config.max_pages == 100


class TestFontConfig:
    """FontConfigクラスのテスト"""

    def test_create_font_config_defaults(self):
        """正常系: デフォルト値でFontConfig生成"""
        from config import FontConfig

        config = FontConfig()

        assert config.min_font_size == 6.0
        assert config.max_font_size == 72.0


class TestConfig:
    """Configクラスのテスト"""

    def test_load_config(self, env_with_api_key):
        """正常系: 設定の読み込み"""
        from config import Config

        config = Config.load(env_file=str(env_with_api_key))

        assert config.api.api_key is not None

    def test_validate_missing_api_key(self, temp_dir):
        """異常系: APIキー未設定"""
        from config import Config, InvalidConfigError

        env_file = temp_dir / ".env"
        env_file.write_text("")  # 空の.envファイル

        with pytest.raises(InvalidConfigError):
            config = Config.load(env_file=str(env_file))
            config.validate()

    def test_validate_invalid_api_key_format(self, temp_dir):
        """異常系: 無効なAPIキー形式"""
        from config import Config, InvalidConfigError

        env_file = temp_dir / ".env"
        env_file.write_text("ANTHROPIC_API_KEY=invalid-key-format\n")

        with pytest.raises(InvalidConfigError):
            config = Config.load(env_file=str(env_file))
            config.validate()

    def test_validate_invalid_max_tokens(self, temp_dir, mock_api_key):
        """異常系: 無効なトークン数"""
        from config import Config, InvalidConfigError

        env_file = temp_dir / ".env"
        env_file.write_text(f"ANTHROPIC_API_KEY={mock_api_key}\nMAX_TOKENS=0\n")

        with pytest.raises(InvalidConfigError):
            config = Config.load(env_file=str(env_file))
            config.validate()

    def test_validate_invalid_temperature(self, temp_dir, mock_api_key):
        """異常系: 無効なtemperature"""
        from config import Config, InvalidConfigError

        env_file = temp_dir / ".env"
        env_file.write_text(f"ANTHROPIC_API_KEY={mock_api_key}\nTEMPERATURE=2.0\n")

        with pytest.raises(InvalidConfigError):
            config = Config.load(env_file=str(env_file))
            config.validate()
