"""
PDF Translator - Translator Module

Claude APIを使用したテキスト翻訳
"""

from enum import Enum
from typing import List, Optional, Tuple
import time
import json
import re
import anthropic

from modules.layout_manager import TextBlock, SpanInfo, TranslationGroup


class TranslationDirection(Enum):
    JA_TO_EN = "ja-to-en"
    EN_TO_JA = "en-to-ja"


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


DEFAULT_MODEL = "claude-3-5-sonnet-20241022"
MAX_RETRIES = 3
RETRY_DELAY_BASE = 1.0
RETRY_DELAY_MULTIPLIER = 2.0


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
7. Use appropriate Japanese writing style based on the context
8. For single words or short phrases (like "Task", "Context", "References", "Evaluate", "Iterate"), translate them directly without asking for more context
9. Never respond with questions, requests for clarification, or any meta-commentary - always provide a translation immediately
"""

SYSTEM_PROMPT_SPANS_EN_TO_JA = """You are a professional translator for PDF documents. You will receive a JSON array of text spans extracted from a PDF, sorted by position (top-left to bottom-right).

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

SYSTEM_PROMPT_SPANS_JA_TO_EN = """You are a professional translator for PDF documents. You will receive a JSON array of text spans extracted from a PDF, sorted by position (top-left to bottom-right).

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


class Translator:
    """翻訳クラス"""

    def __init__(self, api_key: str, model: str = DEFAULT_MODEL):
        self._api_key = api_key
        self._model = model
        self._client: Optional[anthropic.Anthropic] = None

    def _get_client(self) -> anthropic.Anthropic:
        if self._client is None:
            self._client = anthropic.Anthropic(api_key=self._api_key)
        return self._client

    def validate_api_key(self) -> bool:
        try:
            client = self._get_client()
            client.messages.create(
                model=self._model,
                max_tokens=10,
                messages=[{"role": "user", "content": "Hi"}],
            )
            return True
        except anthropic.AuthenticationError:
            return False
        except Exception:
            return False

    def translate(self, text: str, direction: TranslationDirection, context: Optional[str] = None) -> str:
        if not text or not text.strip():
            return ""

        prompt = self._build_prompt(text, direction, context)
        return self._call_api_with_retry(prompt, direction)

    def translate_batch(self, texts: List[str], direction: TranslationDirection) -> List[str]:
        if not texts:
            return []
        return [self.translate(t, direction) for t in texts]

    def translate_blocks(self, blocks: List[TextBlock], direction: TranslationDirection) -> List[TextBlock]:
        if not blocks:
            return []

        for block in blocks:
            translated = self.translate(block.text, direction)
            block.translated_text = translated

        return blocks

    def translate_spans(
        self,
        spans: List[SpanInfo],
        direction: TranslationDirection
    ) -> List[TranslationGroup]:
        """
        span配列を翻訳し、グループ情報を返す

        Args:
            spans: 位置順にソートされたSpanInfoのリスト
            direction: 翻訳方向

        Returns:
            TranslationGroupのリスト（どのspan範囲がどう翻訳されたか）
        """
        if not spans:
            return []

        # spanをJSON形式に変換
        span_data = [{"index": s.index, "text": s.text} for s in spans]
        prompt = json.dumps(span_data, ensure_ascii=False)

        # API呼び出し
        system_prompt = (
            SYSTEM_PROMPT_SPANS_JA_TO_EN
            if direction == TranslationDirection.JA_TO_EN
            else SYSTEM_PROMPT_SPANS_EN_TO_JA
        )

        response = self._call_api_with_system(prompt, system_prompt)

        # レスポンスをパース
        groups = self._parse_translation_groups(response, spans)

        return groups

    def _call_api_with_system(self, prompt: str, system_prompt: str) -> str:
        """指定したシステムプロンプトでAPI呼び出し"""
        last_error = None

        for attempt in range(MAX_RETRIES):
            try:
                client = self._get_client()
                response = client.messages.create(
                    model=self._model,
                    max_tokens=8000,
                    system=system_prompt,
                    messages=[{"role": "user", "content": prompt}],
                )
                return response.content[0].text
            except anthropic.RateLimitError as e:
                last_error = RateLimitError(str(e))
                if attempt < MAX_RETRIES - 1:
                    delay = RETRY_DELAY_BASE * (RETRY_DELAY_MULTIPLIER ** attempt)
                    time.sleep(delay)
            except anthropic.AuthenticationError as e:
                raise APIAuthenticationError(str(e))
            except anthropic.APIConnectionError as e:
                last_error = APIConnectionError(str(e))
                if attempt < MAX_RETRIES - 1:
                    delay = RETRY_DELAY_BASE * (RETRY_DELAY_MULTIPLIER ** attempt)
                    time.sleep(delay)
            except Exception as e:
                raise TranslationError(str(e))

        if last_error:
            raise last_error
        raise TranslationError("Translation failed after retries")

    def _parse_translation_groups(
        self,
        response: str,
        spans: List[SpanInfo]
    ) -> List[TranslationGroup]:
        """
        APIレスポンスをパースしてTranslationGroupのリストを生成

        Args:
            response: APIからのJSON文字列
            spans: 元のSpanInfoリスト

        Returns:
            TranslationGroupのリスト
        """
        # JSONを抽出（余分なテキストがある場合に対応）
        json_match = re.search(r'\[.*\]', response, re.DOTALL)
        if not json_match:
            # フォールバック: 各spanを個別に翻訳されたものとして扱う
            return self._fallback_groups(spans)

        try:
            data = json.loads(json_match.group())
        except json.JSONDecodeError:
            return self._fallback_groups(spans)

        groups: List[TranslationGroup] = []
        span_dict = {s.index: s for s in spans}

        for item in data:
            start = item.get("start", 0)
            end = item.get("end", start)
            translation = item.get("translation", "")

            # 対象spanを収集
            group_spans = [span_dict[i] for i in range(start, end + 1) if i in span_dict]
            if not group_spans:
                continue

            # 元テキストを結合
            original_text = "".join(s.text for s in group_spans)

            groups.append(TranslationGroup(
                start_index=start,
                end_index=end,
                original_text=original_text,
                translated_text=translation,
                spans=group_spans,
            ))

        return groups

    def _fallback_groups(self, spans: List[SpanInfo]) -> List[TranslationGroup]:
        """フォールバック: 各spanを個別グループとして扱う"""
        groups = []
        for span in spans:
            groups.append(TranslationGroup(
                start_index=span.index,
                end_index=span.index,
                original_text=span.text,
                translated_text=span.text,  # 翻訳なし
                spans=[span],
            ))
        return groups

    def _build_prompt(self, text: str, direction: TranslationDirection, context: Optional[str] = None) -> str:
        prompt = f"Translate the following text:\n\n{text}"
        if context:
            prompt = f"Context: {context}\n\n{prompt}"
        return prompt

    def _get_system_prompt(self, direction: TranslationDirection) -> str:
        if direction == TranslationDirection.JA_TO_EN:
            return SYSTEM_PROMPT_JA_TO_EN
        else:
            return SYSTEM_PROMPT_EN_TO_JA

    def _call_api(self, prompt: str, direction: TranslationDirection) -> str:
        client = self._get_client()
        system_prompt = self._get_system_prompt(direction)

        response = client.messages.create(
            model=self._model,
            max_tokens=4000,
            system=system_prompt,
            messages=[{"role": "user", "content": prompt}],
        )

        return response.content[0].text

    def _call_api_with_retry(self, prompt: str, direction: TranslationDirection) -> str:
        last_error = None

        for attempt in range(MAX_RETRIES):
            try:
                return self._call_api(prompt, direction)
            except RateLimitError as e:
                # Already our custom exception (from mocks or previous processing)
                last_error = e
                if attempt < MAX_RETRIES - 1:
                    delay = RETRY_DELAY_BASE * (RETRY_DELAY_MULTIPLIER ** attempt)
                    time.sleep(delay)
            except anthropic.RateLimitError as e:
                last_error = RateLimitError(str(e))
                if attempt < MAX_RETRIES - 1:
                    delay = RETRY_DELAY_BASE * (RETRY_DELAY_MULTIPLIER ** attempt)
                    time.sleep(delay)
            except anthropic.AuthenticationError as e:
                raise APIAuthenticationError(str(e))
            except anthropic.APIConnectionError as e:
                last_error = APIConnectionError(str(e))
                if attempt < MAX_RETRIES - 1:
                    delay = RETRY_DELAY_BASE * (RETRY_DELAY_MULTIPLIER ** attempt)
                    time.sleep(delay)
            except TranslationError:
                raise
            except Exception as e:
                raise TranslationError(str(e))

        if last_error:
            raise last_error
        raise TranslationError("Translation failed after retries")
