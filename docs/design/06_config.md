# config.py（設定モジュール）設計書

## 1. 概要

アプリケーション全体の設定を管理するモジュール。
環境変数、設定ファイル、デフォルト値を統合的に管理し、各モジュールに設定を提供する。

## 2. 責務

- 環境変数の読み込みと管理
- APIキーの安全な管理
- アプリケーション設定の一元管理
- 設定値のバリデーション
- デフォルト値の提供

## 3. 依存関係

```
config.py
├── python-dotenv
├── os (標準ライブラリ)
└── pathlib (標準ライブラリ)
```

## 4. 設定項目

### 4.1 API設定

| 項目 | 環境変数 | デフォルト値 | 説明 |
| --- | --- | --- | --- |
| api_key | ANTHROPIC_API_KEY | (必須) | Claude APIキー |
| model | CLAUDE_MODEL | claude-3-5-sonnet-20241022 | 使用モデル |
| max_tokens | MAX_TOKENS | 4000 | 最大出力トークン数 |
| temperature | TEMPERATURE | 0.3 | 生成の多様性 |
| timeout | API_TIMEOUT | 60 | APIタイムアウト（秒） |
| max_retries | MAX_RETRIES | 3 | 最大リトライ回数 |

### 4.2 PDF設定

| 項目 | 環境変数 | デフォルト値 | 説明 |
| --- | --- | --- | --- |
| input_dir | INPUT_DIR | /app/input | 入力ディレクトリ |
| output_dir | OUTPUT_DIR | /app/output | 出力ディレクトリ |
| max_file_size | MAX_FILE_SIZE | 104857600 | 最大ファイルサイズ（100MB） |
| max_pages | MAX_PAGES | 100 | 最大ページ数 |

### 4.3 フォント設定

| 項目 | 環境変数 | デフォルト値 | 説明 |
| --- | --- | --- | --- |
| font_dir | FONT_DIR | /app/fonts | フォントディレクトリ |
| japanese_font | JAPANESE_FONT | NotoSansCJK-Regular.ttc | 日本語フォント |
| english_font | ENGLISH_FONT | helv | 英語フォント |
| min_font_size | MIN_FONT_SIZE | 6.0 | 最小フォントサイズ |
| max_font_size | MAX_FONT_SIZE | 72.0 | 最大フォントサイズ |

### 4.4 ログ設定

| 項目 | 環境変数 | デフォルト値 | 説明 |
| --- | --- | --- | --- |
| log_level | LOG_LEVEL | INFO | ログレベル |
| log_file | LOG_FILE | None | ログファイルパス |
| log_format | LOG_FORMAT | (下記参照) | ログフォーマット |

## 5. クラス設計

### 5.1 Config クラス

```python
from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path
import os
from dotenv import load_dotenv

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
    input_dir: Path = Path("/app/input")
    output_dir: Path = Path("/app/output")
    max_file_size: int = 104857600  # 100MB
    max_pages: int = 100

@dataclass
class FontConfig:
    """フォント設定"""
    font_dir: Path = Path("/app/fonts")
    japanese_font: str = "NotoSansCJK-Regular.ttc"
    english_font: str = "helv"
    min_font_size: float = 6.0
    max_font_size: float = 72.0

    @property
    def japanese_font_path(self) -> Path:
        """日本語フォントの完全パス"""
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

@dataclass
class Config:
    """アプリケーション設定"""
    api: APIConfig
    pdf: PDFConfig = field(default_factory=PDFConfig)
    font: FontConfig = field(default_factory=FontConfig)
    log: LogConfig = field(default_factory=LogConfig)

    @classmethod
    def load(cls, env_file: Optional[str] = None) -> 'Config':
        """
        設定を読み込み

        Args:
            env_file: .envファイルパス（オプション）

        Returns:
            Config: 設定オブジェクト

        Raises:
            ConfigError: 設定エラー
        """
        pass

    def validate(self) -> None:
        """
        設定値を検証

        Raises:
            ConfigError: 検証エラー
        """
        pass
```

### 5.2 ConfigLoader クラス

```python
class ConfigLoader:
    """設定読み込みユーティリティ"""

    def __init__(self, env_file: Optional[str] = None):
        """
        Args:
            env_file: .envファイルパス
        """
        self._env_file = env_file
        self._loaded = False

    def load_env(self) -> None:
        """環境変数を読み込み"""
        if self._env_file:
            load_dotenv(self._env_file)
        else:
            load_dotenv()  # デフォルトの.envを探索
        self._loaded = True

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """
        環境変数を取得

        Args:
            key: 環境変数名
            default: デフォルト値

        Returns:
            str: 環境変数の値
        """
        if not self._loaded:
            self.load_env()
        return os.getenv(key, default)

    def get_required(self, key: str) -> str:
        """
        必須の環境変数を取得

        Args:
            key: 環境変数名

        Returns:
            str: 環境変数の値

        Raises:
            ConfigError: 未設定の場合
        """
        value = self.get(key)
        if value is None:
            raise ConfigError(f"Required environment variable '{key}' is not set")
        return value

    def get_int(self, key: str, default: int) -> int:
        """整数値として取得"""
        value = self.get(key)
        if value is None:
            return default
        try:
            return int(value)
        except ValueError:
            raise ConfigError(f"Environment variable '{key}' must be an integer")

    def get_float(self, key: str, default: float) -> float:
        """浮動小数点として取得"""
        value = self.get(key)
        if value is None:
            return default
        try:
            return float(value)
        except ValueError:
            raise ConfigError(f"Environment variable '{key}' must be a float")

    def get_bool(self, key: str, default: bool) -> bool:
        """真偽値として取得"""
        value = self.get(key)
        if value is None:
            return default
        return value.lower() in ('true', '1', 'yes', 'on')

    def get_path(self, key: str, default: Optional[Path] = None) -> Optional[Path]:
        """パスとして取得"""
        value = self.get(key)
        if value is None:
            return default
        return Path(value)
```

## 6. 設定読み込みフロー

```
1. ConfigLoader初期化
   └── .envファイルパス指定（オプション）

2. 環境変数読み込み
   ├── .envファイルから読み込み（python-dotenv）
   └── システム環境変数を上書き

3. API設定の構築
   ├── ANTHROPIC_API_KEY取得（必須）
   ├── CLAUDE_MODEL取得（オプション）
   └── その他API設定取得

4. PDF設定の構築
   ├── ディレクトリパス取得
   └── 制限値取得

5. フォント設定の構築
   ├── フォントパス取得
   └── サイズ制限取得

6. ログ設定の構築
   └── ログレベル、出力先取得

7. 設定検証
   ├── 必須項目の存在確認
   ├── 値の範囲検証
   └── パスの存在確認

8. Configオブジェクト返却
```

## 7. エラーハンドリング

### 7.1 カスタム例外

```python
class ConfigError(Exception):
    """設定エラーの基底クラス"""
    pass

class MissingConfigError(ConfigError):
    """必須設定が未設定"""
    pass

class InvalidConfigError(ConfigError):
    """設定値が不正"""
    pass
```

### 7.2 バリデーション

```python
def validate(self) -> None:
    """設定値の検証"""
    errors = []

    # APIキー検証
    if not self.api.api_key:
        errors.append("ANTHROPIC_API_KEY is required")
    elif not self.api.api_key.startswith("sk-ant-"):
        errors.append("ANTHROPIC_API_KEY format is invalid")

    # トークン数検証
    if self.api.max_tokens < 1 or self.api.max_tokens > 100000:
        errors.append("MAX_TOKENS must be between 1 and 100000")

    # temperature検証
    if self.api.temperature < 0 or self.api.temperature > 1:
        errors.append("TEMPERATURE must be between 0 and 1")

    # ディレクトリ検証
    if not self.pdf.input_dir.exists():
        errors.append(f"Input directory does not exist: {self.pdf.input_dir}")

    if errors:
        raise InvalidConfigError("\n".join(errors))
```

## 8. .envファイル例

### 8.1 .env.example

```bash
# Anthropic API設定
ANTHROPIC_API_KEY=sk-ant-api03-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# モデル設定（オプション）
CLAUDE_MODEL=claude-3-5-sonnet-20241022
MAX_TOKENS=4000
TEMPERATURE=0.3
API_TIMEOUT=60
MAX_RETRIES=3

# PDF設定（オプション）
INPUT_DIR=/app/input
OUTPUT_DIR=/app/output
MAX_FILE_SIZE=104857600
MAX_PAGES=100

# フォント設定（オプション）
FONT_DIR=/app/fonts
JAPANESE_FONT=NotoSansCJK-Regular.ttc
MIN_FONT_SIZE=6.0
MAX_FONT_SIZE=72.0

# ログ設定（オプション）
LOG_LEVEL=INFO
LOG_FILE=
```

## 9. 使用例

```python
from config import Config, ConfigError

# 設定読み込み
try:
    config = Config.load()
except ConfigError as e:
    print(f"Configuration error: {e}")
    sys.exit(1)

# 設定値の使用
print(f"Using model: {config.api.model}")
print(f"Input directory: {config.pdf.input_dir}")

# 個別設定へのアクセス
translator = Translator(
    api_key=config.api.api_key,
    model=config.api.model
)

# カスタム.envファイルから読み込み
config = Config.load(env_file="/path/to/custom.env")
```

## 10. Docker環境での使用

### 10.1 環境変数の注入

```yaml
# docker-compose.yml
services:
  pdf-translator:
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - LOG_LEVEL=DEBUG
```

### 10.2 .envファイルの使用

```yaml
# docker-compose.yml
services:
  pdf-translator:
    env_file:
      - .env
```

## 11. セキュリティ考慮

### 11.1 APIキーの保護

- APIキーは環境変数で管理
- .envファイルは.gitignoreに追加
- ログにAPIキーを出力しない

### 11.2 .dockerignore

```
.env
.env.local
*.key
*.pem
```

### 11.3 APIキーのマスキング

```python
def _mask_api_key(self, api_key: str) -> str:
    """APIキーをログ用にマスキング"""
    if len(api_key) <= 10:
        return "***"
    return f"{api_key[:7]}...{api_key[-4:]}"
```

## 12. テスト項目

- [ ] 正常系：環境変数からの読み込み
- [ ] 正常系：.envファイルからの読み込み
- [ ] 正常系：デフォルト値の適用
- [ ] 正常系：設定値のバリデーション
- [ ] 異常系：APIキー未設定
- [ ] 異常系：無効な設定値
- [ ] 異常系：存在しないディレクトリ
- [ ] 異常系：.envファイル読み込み失敗

---

**作成日**: 2026-01-01
**バージョン**: 1.0
