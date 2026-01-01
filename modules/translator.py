"""
PDF Translator - Translator Module

Claude APIを使用したテキスト翻訳
"""

from enum import Enum
from typing import List, Optional
import time
import anthropic

from modules.layout_manager import TextBlock


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
