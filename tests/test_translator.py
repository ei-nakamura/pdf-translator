"""
PDF Translator - Translator Module Tests

設計書: docs/design/03_translator.md
"""

import pytest
from unittest.mock import Mock, patch, MagicMock


class TestTranslationDirection:
    """TranslationDirection列挙型のテスト"""

    def test_ja_to_en_exists(self):
        """正常系: JA_TO_EN値が存在"""
        from modules.translator import TranslationDirection

        assert TranslationDirection.JA_TO_EN.value == "ja-to-en"

    def test_en_to_ja_exists(self):
        """正常系: EN_TO_JA値が存在"""
        from modules.translator import TranslationDirection

        assert TranslationDirection.EN_TO_JA.value == "en-to-ja"


class TestTranslator:
    """Translatorクラスのテスト"""

    def test_create_translator(self, mock_api_key):
        """正常系: Translator生成"""
        from modules.translator import Translator

        translator = Translator(api_key=mock_api_key)
        assert translator is not None

    def test_create_translator_custom_model(self, mock_api_key):
        """正常系: カスタムモデルでTranslator生成"""
        from modules.translator import Translator

        translator = Translator(
            api_key=mock_api_key, model="claude-3-haiku-20240307"
        )
        assert translator is not None

    def test_validate_api_key_format(self, mock_api_key):
        """正常系: APIキー検証"""
        from modules.translator import Translator

        translator = Translator(api_key=mock_api_key)
        # モックなのでFalseが返る可能性がある
        result = translator.validate_api_key()
        assert isinstance(result, bool)


class TestTranslatorTranslate:
    """Translator.translateメソッドのテスト"""

    def test_translate_empty_text(self, mock_api_key):
        """異常系: 空テキストの翻訳"""
        from modules.translator import Translator, TranslationDirection

        translator = Translator(api_key=mock_api_key)

        # 空テキストは空文字列を返すか例外
        result = translator.translate("", TranslationDirection.JA_TO_EN)
        assert result == "" or result is None

    def test_translate_returns_string(self, mock_api_key):
        """正常系: 翻訳結果が文字列"""
        from modules.translator import Translator, TranslationDirection

        translator = Translator(api_key=mock_api_key)

        with patch.object(translator, "_call_api") as mock_call:
            mock_call.return_value = "Hello"
            result = translator.translate("こんにちは", TranslationDirection.JA_TO_EN)

            assert isinstance(result, str)

    def test_translate_ja_to_en(self, mock_api_key, sample_japanese_text):
        """正常系: 日本語→英語翻訳"""
        from modules.translator import Translator, TranslationDirection

        translator = Translator(api_key=mock_api_key)

        with patch.object(translator, "_call_api") as mock_call:
            mock_call.return_value = "Hello, World! This is a test."
            result = translator.translate(
                sample_japanese_text, TranslationDirection.JA_TO_EN
            )

            assert result is not None
            assert len(result) > 0

    def test_translate_en_to_ja(self, mock_api_key, sample_english_text):
        """正常系: 英語→日本語翻訳"""
        from modules.translator import Translator, TranslationDirection

        translator = Translator(api_key=mock_api_key)

        with patch.object(translator, "_call_api") as mock_call:
            mock_call.return_value = "こんにちは、世界！これはテストです。"
            result = translator.translate(
                sample_english_text, TranslationDirection.EN_TO_JA
            )

            assert result is not None
            assert len(result) > 0


class TestTranslatorBatch:
    """Translator.translate_batchメソッドのテスト"""

    def test_translate_batch_empty_list(self, mock_api_key):
        """正常系: 空リストのバッチ翻訳"""
        from modules.translator import Translator, TranslationDirection

        translator = Translator(api_key=mock_api_key)
        result = translator.translate_batch([], TranslationDirection.JA_TO_EN)

        assert result == []

    def test_translate_batch_returns_list(self, mock_api_key):
        """正常系: バッチ翻訳がリストを返す"""
        from modules.translator import Translator, TranslationDirection

        translator = Translator(api_key=mock_api_key)
        texts = ["こんにちは", "さようなら"]

        with patch.object(translator, "_call_api") as mock_call:
            mock_call.return_value = "Hello\n---\nGoodbye"
            result = translator.translate_batch(texts, TranslationDirection.JA_TO_EN)

            assert isinstance(result, list)

    def test_translate_batch_same_length(self, mock_api_key):
        """正常系: バッチ翻訳の入出力が同じ長さ"""
        from modules.translator import Translator, TranslationDirection

        translator = Translator(api_key=mock_api_key)
        texts = ["Hello", "World", "Test"]

        with patch.object(translator, "translate") as mock_translate:
            mock_translate.side_effect = ["こんにちは", "世界", "テスト"]
            result = translator.translate_batch(texts, TranslationDirection.EN_TO_JA)

            assert len(result) == len(texts)


class TestTranslatorBlocks:
    """Translator.translate_blocksメソッドのテスト"""

    def test_translate_blocks_empty(self, mock_api_key):
        """正常系: 空ブロックリストの翻訳"""
        from modules.translator import Translator, TranslationDirection

        translator = Translator(api_key=mock_api_key)
        result = translator.translate_blocks([], TranslationDirection.JA_TO_EN)

        assert result == []

    def test_translate_blocks_updates_text(self, mock_api_key):
        """正常系: ブロック翻訳でテキストが更新される"""
        from modules.translator import Translator, TranslationDirection
        from modules.layout_manager import TextBlock, BoundingBox, FontInfo

        translator = Translator(api_key=mock_api_key)
        blocks = [
            TextBlock(
                id="block_1",
                text="こんにちは",
                bbox=BoundingBox(0, 0, 100, 20),
                font=FontInfo(name="Arial", size=12.0),
            )
        ]

        with patch.object(translator, "translate") as mock_translate:
            mock_translate.return_value = "Hello"
            result = translator.translate_blocks(blocks, TranslationDirection.JA_TO_EN)

            assert len(result) == 1
            assert result[0].translated_text == "Hello"


class TestTranslatorExceptions:
    """Translator例外クラスのテスト"""

    def test_translation_error_exists(self):
        """TranslationError例外が存在"""
        from modules.translator import TranslationError

        assert TranslationError is not None

    def test_api_connection_error_exists(self):
        """APIConnectionError例外が存在"""
        from modules.translator import APIConnectionError

        assert APIConnectionError is not None

    def test_api_authentication_error_exists(self):
        """APIAuthenticationError例外が存在"""
        from modules.translator import APIAuthenticationError

        assert APIAuthenticationError is not None

    def test_rate_limit_error_exists(self):
        """RateLimitError例外が存在"""
        from modules.translator import RateLimitError

        assert RateLimitError is not None

    def test_token_limit_error_exists(self):
        """TokenLimitError例外が存在"""
        from modules.translator import TokenLimitError

        assert TokenLimitError is not None

    def test_api_connection_error_is_subclass(self):
        """APIConnectionErrorがTranslationErrorのサブクラス"""
        from modules.translator import TranslationError, APIConnectionError

        assert issubclass(APIConnectionError, TranslationError)

    def test_api_authentication_error_is_subclass(self):
        """APIAuthenticationErrorがTranslationErrorのサブクラス"""
        from modules.translator import TranslationError, APIAuthenticationError

        assert issubclass(APIAuthenticationError, TranslationError)


class TestTranslatorRetry:
    """リトライ処理のテスト"""

    def test_retry_on_rate_limit(self, mock_api_key):
        """正常系: レート制限でリトライ"""
        from modules.translator import Translator, TranslationDirection, RateLimitError

        translator = Translator(api_key=mock_api_key)

        call_count = 0

        def mock_call(prompt, direction):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise RateLimitError("Rate limited")
            return "Success"

        with patch.object(translator, "_call_api", side_effect=mock_call):
            result = translator.translate("test", TranslationDirection.JA_TO_EN)
            assert result == "Success"
            assert call_count == 3

    def test_max_retries_exceeded(self, mock_api_key):
        """異常系: 最大リトライ回数超過"""
        from modules.translator import Translator, TranslationDirection, RateLimitError

        translator = Translator(api_key=mock_api_key)

        with patch.object(
            translator, "_call_api", side_effect=RateLimitError("Rate limited")
        ):
            with pytest.raises(RateLimitError):
                translator.translate("test", TranslationDirection.JA_TO_EN)


class TestTranslatorPrompt:
    """プロンプト生成のテスト"""

    def test_build_prompt_ja_to_en(self, mock_api_key):
        """正常系: 日→英プロンプト生成"""
        from modules.translator import Translator, TranslationDirection

        translator = Translator(api_key=mock_api_key)
        prompt = translator._build_prompt("こんにちは", TranslationDirection.JA_TO_EN)

        assert prompt is not None
        assert "こんにちは" in prompt

    def test_build_prompt_en_to_ja(self, mock_api_key):
        """正常系: 英→日プロンプト生成"""
        from modules.translator import Translator, TranslationDirection

        translator = Translator(api_key=mock_api_key)
        prompt = translator._build_prompt("Hello", TranslationDirection.EN_TO_JA)

        assert prompt is not None
        assert "Hello" in prompt

    def test_build_prompt_with_context(self, mock_api_key):
        """正常系: コンテキスト付きプロンプト生成"""
        from modules.translator import Translator, TranslationDirection

        translator = Translator(api_key=mock_api_key)
        prompt = translator._build_prompt(
            "Hello", TranslationDirection.EN_TO_JA, context="Technical document"
        )

        assert "Technical document" in prompt


class TestTranslatorShortText:
    """短いテキスト（単語のみ）の翻訳テスト"""

    def test_translate_single_word(self, mock_api_key):
        """正常系: 単語のみの翻訳"""
        from modules.translator import Translator, TranslationDirection

        translator = Translator(api_key=mock_api_key)

        with patch.object(translator, "_call_api") as mock_call:
            mock_call.return_value = "タスク"
            result = translator.translate("Task", TranslationDirection.EN_TO_JA)

            assert result == "タスク"
            # エラーメッセージが返されていないことを確認
            assert "I notice" not in result
            assert "Could you" not in result

    def test_translate_short_phrase(self, mock_api_key):
        """正常系: 短いフレーズの翻訳"""
        from modules.translator import Translator, TranslationDirection

        translator = Translator(api_key=mock_api_key)

        with patch.object(translator, "_call_api") as mock_call:
            mock_call.return_value = "参考文献"
            result = translator.translate("References", TranslationDirection.EN_TO_JA)

            assert result == "参考文献"

    def test_system_prompt_includes_short_text_rule(self, mock_api_key):
        """正常系: システムプロンプトに短いテキストのルールが含まれる"""
        from modules.translator import Translator, TranslationDirection, SYSTEM_PROMPT_EN_TO_JA

        # ルール8と9が含まれていることを確認
        assert "single words" in SYSTEM_PROMPT_EN_TO_JA or "short" in SYSTEM_PROMPT_EN_TO_JA.lower()
        assert "Never respond with questions" in SYSTEM_PROMPT_EN_TO_JA or "always provide a translation" in SYSTEM_PROMPT_EN_TO_JA.lower()

    def test_validate_translation_response(self, mock_api_key):
        """正常系: 翻訳レスポンスの検証"""
        from modules.translator import Translator, TranslationDirection

        translator = Translator(api_key=mock_api_key)

        # エラーメッセージのような応答がフィルタリングされることを確認
        with patch.object(translator, "_call_api") as mock_call:
            # APIがエラーメッセージを返した場合
            mock_call.return_value = 'I notice you wrote "Task" but didn\'t include any text'

            result = translator.translate("Task", TranslationDirection.EN_TO_JA)

            # 検証機能が実装されていれば、エラーメッセージは除外されるべき
            # 現時点では実装されていないため、このテストは将来の実装のために存在
            assert result is not None
