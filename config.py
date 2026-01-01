"""
PDF Translator - Configuration Module

アプリケーション設定の管理
"""

from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path
import os
from dotenv import load_dotenv


class ConfigError(Exception):
    """設定エラーの基底クラス"""
    pass


class MissingConfigError(ConfigError):
    """必須設定が未設定"""
    pass


class InvalidConfigError(ConfigError):
    """設定値が不正"""
    pass


@dataclass
class APIConfig:
    """API設定"""
    api_key: str
    model: str = "claude-3-5-sonnet-20241022"
    max_tokens: int = 4000
    temperature: float = 0.3
    timeout: int = 60
    max_retries: int = 3


@dataclass
class PDFConfig:
    """PDF設定"""
    input_dir: Path = field(default_factory=lambda: Path("/app/input"))
    output_dir: Path = field(default_factory=lambda: Path("/app/output"))
    max_file_size: int = 104857600
    max_pages: int = 100


@dataclass
class FontConfig:
    """フォント設定"""
    font_dir: Path = field(default_factory=lambda: Path("/app/fonts"))
    japanese_font: str = "NotoSansCJK-Regular.ttc"
    english_font: str = "helv"
    min_font_size: float = 6.0
    max_font_size: float = 72.0

    @property
    def japanese_font_path(self) -> Path:
        system_path = Path("/usr/share/fonts/opentype/noto") / self.japanese_font
        if system_path.exists():
            return system_path
        return self.font_dir / self.japanese_font


@dataclass
class LogConfig:
    """ログ設定"""
    level: str = "INFO"
    file: Optional[Path] = None
    format: str = "[%(asctime)s] [%(levelname)s] %(message)s"


class ConfigLoader:
    """設定読み込みユーティリティ"""

    def __init__(self, env_file: Optional[str] = None):
        self._env_file = env_file
        self._loaded = False

    def load_env(self) -> None:
        if self._env_file:
            load_dotenv(self._env_file, override=True)
        else:
            load_dotenv(override=True)
        self._loaded = True

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        if not self._loaded:
            self.load_env()
        return os.getenv(key, default)

    def get_required(self, key: str) -> str:
        value = self.get(key)
        if value is None:
            raise MissingConfigError(f"Required environment variable \'{key}\' is not set")
        return value

    def get_int(self, key: str, default: int) -> int:
        value = self.get(key)
        if value is None:
            return default
        try:
            return int(value)
        except ValueError:
            raise InvalidConfigError(f"Environment variable \'{key}\' must be an integer")

    def get_float(self, key: str, default: float) -> float:
        value = self.get(key)
        if value is None:
            return default
        try:
            return float(value)
        except ValueError:
            raise InvalidConfigError(f"Environment variable \'{key}\' must be a float")

    def get_bool(self, key: str, default: bool) -> bool:
        value = self.get(key)
        if value is None:
            return default
        return value.lower() in ("true", "1", "yes", "on")

    def get_path(self, key: str, default: Optional[Path] = None) -> Optional[Path]:
        value = self.get(key)
        if value is None:
            return default
        return Path(value)


@dataclass
class Config:
    """アプリケーション設定"""
    api: APIConfig
    pdf: PDFConfig = field(default_factory=PDFConfig)
    font: FontConfig = field(default_factory=FontConfig)
    log: LogConfig = field(default_factory=LogConfig)

    @classmethod
    def load(cls, env_file: Optional[str] = None) -> "Config":
        loader = ConfigLoader(env_file=env_file)
        loader.load_env()

        api_key = loader.get("ANTHROPIC_API_KEY", "")
        api_config = APIConfig(
            api_key=api_key,
            model=loader.get("CLAUDE_MODEL", "claude-3-5-sonnet-20241022"),
            max_tokens=loader.get_int("MAX_TOKENS", 4000),
            temperature=loader.get_float("TEMPERATURE", 0.3),
            timeout=loader.get_int("API_TIMEOUT", 60),
            max_retries=loader.get_int("MAX_RETRIES", 3),
        )

        pdf_config = PDFConfig(
            input_dir=loader.get_path("INPUT_DIR", Path("/app/input")),
            output_dir=loader.get_path("OUTPUT_DIR", Path("/app/output")),
            max_file_size=loader.get_int("MAX_FILE_SIZE", 104857600),
            max_pages=loader.get_int("MAX_PAGES", 100),
        )

        font_config = FontConfig(
            font_dir=loader.get_path("FONT_DIR", Path("/app/fonts")),
            japanese_font=loader.get("JAPANESE_FONT", "NotoSansCJK-Regular.ttc"),
            min_font_size=loader.get_float("MIN_FONT_SIZE", 6.0),
            max_font_size=loader.get_float("MAX_FONT_SIZE", 72.0),
        )

        log_file = loader.get("LOG_FILE")
        log_config = LogConfig(
            level=loader.get("LOG_LEVEL", "INFO"),
            file=Path(log_file) if log_file else None,
        )

        return cls(api=api_config, pdf=pdf_config, font=font_config, log=log_config)

    def validate(self) -> None:
        errors = []
        if not self.api.api_key:
            errors.append("ANTHROPIC_API_KEY is required")
        elif not self.api.api_key.startswith("sk-ant-"):
            errors.append("ANTHROPIC_API_KEY format is invalid")
        if self.api.max_tokens < 1 or self.api.max_tokens > 100000:
            errors.append("MAX_TOKENS must be between 1 and 100000")
        if self.api.temperature < 0 or self.api.temperature > 1:
            errors.append("TEMPERATURE must be between 0 and 1")
        if errors:
            raise InvalidConfigError("\n".join(errors))
