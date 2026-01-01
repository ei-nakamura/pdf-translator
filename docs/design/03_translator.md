# translator.py（翻訳モジュール）設計書

## 1. 概要

Claude APIを使用してテキストを翻訳するモジュール。
日本語⇔英語の双方向翻訳に対応し、文脈を考慮した高品質な翻訳を提供する。

## 2. 責務

- Claude APIとの通信管理
- テキストの翻訳処理
- 翻訳方向（日→英、英→日）の制御
- 翻訳品質の最適化（プロンプトエンジニアリング）
- APIレート制限の管理
- エラーハンドリングとリトライ処理

## 3. 依存関係

```
translator.py
├── anthropic (Claude API SDK)
├── config.py (API設定)
└── modules/layout_manager.py (TextBlock, SpanInfo, TranslationGroupデータクラス)
```

## 4. 定数定義

```python
# 翻訳方向
class TranslationDirection(Enum):
    JA_TO_EN = "ja-to-en"  # 日本語 → 英語
    EN_TO_JA = "en-to-ja"  # 英語 → 日本語

# APIモデル
DEFAULT_MODEL = "claude-3-5-sonnet-20241022"
FALLBACK_MODEL = "claude-3-haiku-20240307"

# リトライ設定
MAX_RETRIES = 3
RETRY_DELAY_BASE = 1.0  # 秒
RETRY_DELAY_MULTIPLIER = 2.0

# トークン制限
MAX_INPUT_TOKENS = 4000
MAX_OUTPUT_TOKENS = 4000
```

## 5. クラス設計

### 5.1 Translator クラス

```python
class Translator:
    """Claude APIを使用した翻訳クラス"""

    def __init__(self, api_key: str, model: str = DEFAULT_MODEL):
        """
        Args:
            api_key: Anthropic APIキー
            model: 使用するモデル名
        """
        self._client: anthropic.Anthropic = None
        self._model = model

    def translate(self, text: str, direction: TranslationDirection,
                  context: Optional[str] = None) -> str:
        """
        テキストを翻訳

        Args:
            text: 翻訳対象テキスト
            direction: 翻訳方向
            context: 文脈情報（オプション）

        Returns:
            str: 翻訳結果

        Raises:
            TranslationError: 翻訳エラー
        """
        pass

    def translate_blocks(self, blocks: List[TextBlock],
                         direction: TranslationDirection) -> List[TextBlock]:
        """
        複数のテキストブロックを翻訳

        Args:
            blocks: テキストブロックリスト
            direction: 翻訳方向

        Returns:
            List[TextBlock]: 翻訳済みテキストブロックリスト
        """
        pass

    def translate_batch(self, texts: List[str],
                        direction: TranslationDirection) -> List[str]:
        """
        複数テキストをバッチ翻訳（効率化）

        Args:
            texts: テキストリスト
            direction: 翻訳方向

        Returns:
            List[str]: 翻訳結果リスト
        """
        pass

    def validate_api_key(self) -> bool:
        """
        APIキーの有効性を確認

        Returns:
            bool: 有効な場合True
        """
        pass

    def _build_prompt(self, text: str, direction: TranslationDirection,
                      context: Optional[str] = None) -> str:
        """翻訳用プロンプトを構築"""
        pass

    def _call_api(self, prompt: str) -> str:
        """APIを呼び出し"""
        pass

    def _handle_rate_limit(self, retry_count: int) -> None:
        """レート制限対応の待機処理"""
        pass

    def translate_spans(self, spans: List[SpanInfo],
                        direction: TranslationDirection) -> List[TranslationGroup]:
        """
        span配列を翻訳し、グループ情報を返す

        全spanを1回のAPI呼び出しで翻訳し、AIがどのspanを
        グループ化して翻訳すべきかを判断する。

        Args:
            spans: 位置順にソートされたSpanInfoのリスト
            direction: 翻訳方向

        Returns:
            List[TranslationGroup]: 翻訳グループのリスト
        """
        pass

    def _parse_translation_groups(self, response: str,
                                   spans: List[SpanInfo]) -> List[TranslationGroup]:
        """
        APIレスポンスをパースしてTranslationGroupのリストを生成

        Args:
            response: APIからのJSON文字列
            spans: 元のSpanInfoリスト

        Returns:
            List[TranslationGroup]: パースされた翻訳グループ
        """
        pass

    def _fallback_groups(self, spans: List[SpanInfo]) -> List[TranslationGroup]:
        """
        フォールバック: 各spanを個別グループとして扱う

        JSONパースに失敗した場合に使用

        Args:
            spans: SpanInfoリスト

        Returns:
            List[TranslationGroup]: 各spanを個別グループとした結果
        """
        pass
```

## 6. プロンプト設計

### 6.1 システムプロンプト

```python
SYSTEM_PROMPT_JA_TO_EN = """You are a professional translator specializing in Japanese to English translation.

Rules:
1. Translate the given Japanese text into natural, fluent English
2. Preserve the original meaning and nuance as much as possible
3. Maintain the tone and style of the original text
4. Keep proper nouns, technical terms, and brand names unchanged unless there is a commonly used English equivalent
5. Output ONLY the translated text without any explanations or notes
6. Preserve paragraph structure and line breaks
"""

SYSTEM_PROMPT_EN_TO_JA = """You are a professional translator specializing in English to Japanese translation.

Rules:
1. Translate the given English text into natural, fluent Japanese
2. Preserve the original meaning and nuance as much as possible
3. Maintain the tone and style of the original text
4. Keep proper nouns, technical terms, and brand names unchanged unless there is a commonly used Japanese equivalent
5. Output ONLY the translated text without any explanations or notes
6. Preserve paragraph structure and line breaks
7. Use appropriate Japanese writing style (です/ます調 or だ/である調) based on the context
8. For single words or short phrases (like "Task", "Context", "References"), translate them directly without asking for more context
9. Never respond with questions or requests for clarification - always provide a translation
"""
```

### 6.2 スパンベース翻訳用システムプロンプト

```python
SYSTEM_PROMPT_SPANS_EN_TO_JA = """You are a professional translator for PDF documents.
You will receive a JSON array of text spans extracted from a PDF, sorted by position (top-left to bottom-right).

Your task:
1. Analyze which spans should be translated together as meaningful groups
2. Translate each group from English to Japanese
3. Return the result as a JSON array

Input format:
[{"index": 0, "text": "Hello"}, {"index": 1, "text": "World"}, ...]

Output format (MUST be valid JSON):
[
  {"start": 0, "end": 1, "translation": "翻訳結果"},
  {"start": 2, "end": 5, "translation": "別の翻訳"},
  ...
]

Rules:
- "start" and "end" are inclusive span indices
- Group spans that form a logical unit (sentence, phrase, heading)
- Single words can be their own group
- Translate naturally, not word-by-word
- Keep proper nouns and technical terms as appropriate
- Output ONLY the JSON array, no explanations
"""

SYSTEM_PROMPT_SPANS_JA_TO_EN = """You are a professional translator for PDF documents.
You will receive a JSON array of text spans extracted from a PDF, sorted by position (top-left to bottom-right).

Your task:
1. Analyze which spans should be translated together as meaningful groups
2. Translate each group from Japanese to English
3. Return the result as a JSON array

Input format:
[{"index": 0, "text": "こんにちは"}, {"index": 1, "text": "世界"}, ...]

Output format (MUST be valid JSON):
[
  {"start": 0, "end": 1, "translation": "Hello World"},
  {"start": 2, "end": 5, "translation": "Another translation"},
  ...
]

Rules:
- "start" and "end" are inclusive span indices
- Group spans that form a logical unit (sentence, phrase, heading)
- Single words can be their own group
- Translate naturally, not word-by-word
- Keep proper nouns and technical terms as appropriate
- Output ONLY the JSON array, no explanations
"""
```

### 6.3 ユーザープロンプト

```python
def _build_user_prompt(self, text: str, context: Optional[str] = None) -> str:
    prompt = f"Translate the following text:\n\n{text}"

    if context:
        prompt = f"Context: {context}\n\n{prompt}"

    return prompt
```

## 7. 処理フロー

### 7.1 単一テキスト翻訳

```
1. 入力テキストの検証
   ├── 空テキストチェック
   └── 文字数制限チェック

2. プロンプト構築
   ├── システムプロンプト選択
   └── ユーザープロンプト生成

3. API呼び出し（リトライ付き）
   ├── リクエスト送信
   ├── レスポンス受信
   └── エラー時リトライ

4. 結果処理
   ├── レスポンス解析
   └── 翻訳テキスト抽出

5. 翻訳結果返却
```

### 7.2 バッチ翻訳（効率化）

```
1. テキストリストを適切なサイズに分割
   └── トークン制限を考慮

2. 複数テキストを1つのプロンプトにまとめる
   ├── 区切り記号で連結
   └── インデックス付与

3. API呼び出し
   └── 1回のリクエストで複数翻訳

4. レスポンス分割
   ├── 区切り記号で分離
   └── 元のインデックスに対応付け

5. 翻訳結果リスト返却
```

### 7.3 スパンベース翻訳（推奨）

```
1. SpanInfoリストをJSON形式に変換
   ├── 各spanのindex, textを抽出
   └── JSON配列として送信

2. API呼び出し（1回のみ）
   ├── スパンベース用システムプロンプト使用
   └── JSON配列を入力として送信

3. レスポンスをパース
   ├── JSON配列を解析
   ├── start/end/translationを抽出
   └── TranslationGroupを生成

4. グループに対応するspanを紐付け
   ├── 範囲内のspanを収集
   └── original_textを結合

5. TranslationGroupリスト返却
```

**メリット**:

- API呼び出し回数が1回に削減（ブロック単位では53回 → 1回）
- 処理時間が大幅に短縮（150秒 → 40秒程度）
- AIがコンテキストを考慮してグループ化を判断

## 8. エラーハンドリング

### 8.1 カスタム例外

```python
class TranslationError(Exception):
    """翻訳エラーの基底クラス"""
    pass

class APIConnectionError(TranslationError):
    """API接続エラー"""
    pass

class APIAuthenticationError(TranslationError):
    """API認証エラー"""
    pass

class RateLimitError(TranslationError):
    """レート制限エラー"""
    pass

class TokenLimitError(TranslationError):
    """トークン制限超過エラー"""
    pass
```

### 8.2 エラー対応マトリクス

| エラー種別 | HTTPコード | 対応 |
| --- | --- | --- |
| 認証エラー | 401 | APIAuthenticationError発生、リトライなし |
| レート制限 | 429 | 指数バックオフでリトライ |
| サーバーエラー | 500-599 | 指数バックオフでリトライ |
| トークン超過 | 400 | テキスト分割して再試行 |
| ネットワークエラー | - | リトライ後、失敗時APIConnectionError |

### 8.3 リトライロジック

```python
def _call_api_with_retry(self, prompt: str) -> str:
    """
    リトライ付きAPI呼び出し

    指数バックオフ:
    - 1回目リトライ: 1秒待機
    - 2回目リトライ: 2秒待機
    - 3回目リトライ: 4秒待機
    """
    for attempt in range(MAX_RETRIES):
        try:
            return self._call_api(prompt)
        except RateLimitError:
            if attempt < MAX_RETRIES - 1:
                delay = RETRY_DELAY_BASE * (RETRY_DELAY_MULTIPLIER ** attempt)
                time.sleep(delay)
            else:
                raise
```

## 9. パフォーマンス最適化

### 9.1 バッチ処理

- 短いテキストブロックは複数まとめて1回のAPI呼び出しで処理
- トークン使用量を削減し、レイテンシを改善

### 9.2 キャッシュ（将来実装）

```python
# 同一テキストの再翻訳を防ぐキャッシュ機構
@lru_cache(maxsize=1000)
def _cached_translate(self, text: str, direction: str) -> str:
    return self._translate_impl(text, direction)
```

## 10. 使用例

```python
from modules.translator import Translator, TranslationDirection

# 初期化
translator = Translator(api_key="sk-ant-...")

# APIキー検証
if not translator.validate_api_key():
    raise ValueError("Invalid API key")

# 単一テキスト翻訳
result = translator.translate(
    text="こんにちは、世界！",
    direction=TranslationDirection.JA_TO_EN
)
print(result)  # "Hello, world!"

# バッチ翻訳
texts = ["おはよう", "こんにちは", "こんばんは"]
results = translator.translate_batch(texts, TranslationDirection.JA_TO_EN)
print(results)  # ["Good morning", "Hello", "Good evening"]

# テキストブロック翻訳
translated_blocks = translator.translate_blocks(
    blocks=text_blocks,
    direction=TranslationDirection.EN_TO_JA
)
```

## 11. 設定パラメータ

| パラメータ | デフォルト値 | 説明 |
| --- | --- | --- |
| model | claude-3-5-sonnet-20241022 | 使用モデル |
| max_retries | 3 | 最大リトライ回数 |
| timeout | 60 | API呼び出しタイムアウト（秒） |
| max_tokens | 4000 | 最大出力トークン数 |
| temperature | 0.3 | 生成の多様性（低め推奨） |

## 12. テスト項目

- [x] 正常系：日本語→英語翻訳
- [x] 正常系：英語→日本語翻訳
- [x] 正常系：長文テキスト翻訳
- [x] 正常系：バッチ翻訳
- [x] 正常系：特殊文字を含むテキスト
- [ ] 正常系：スパンベース翻訳（translate_spans）
- [ ] 正常系：翻訳グループのパース
- [x] 異常系：空テキスト
- [x] 異常系：無効なAPIキー
- [x] 異常系：レート制限（リトライ確認）
- [x] 異常系：ネットワークエラー
- [ ] 異常系：トークン制限超過

---

**作成日**: 2026-01-01
**バージョン**: 2.0
**更新履歴**:

- v1.0: 初版作成
- v2.0: スパンベース翻訳機能（translate_spans）を追加
