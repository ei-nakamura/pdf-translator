"""
PDF Translator - Main CLI Module Tests

設計書: docs/design/01_main_cli.md
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock


class TestCLIArguments:
    """コマンドライン引数のテスト"""

    def test_parse_input_file(self):
        """正常系: 入力ファイル引数"""
        from main import parse_arguments

        args = parse_arguments(["/app/input/test.pdf", "--direction", "ja-to-en"])

        assert args.input_file == "/app/input/test.pdf"

    def test_parse_direction_ja_to_en(self):
        """正常系: 翻訳方向 ja-to-en"""
        from main import parse_arguments

        args = parse_arguments(["/app/input/test.pdf", "--direction", "ja-to-en"])

        assert args.direction == "ja-to-en"

    def test_parse_direction_en_to_ja(self):
        """正常系: 翻訳方向 en-to-ja"""
        from main import parse_arguments

        args = parse_arguments(["/app/input/test.pdf", "--direction", "en-to-ja"])

        assert args.direction == "en-to-ja"

    def test_parse_direction_short(self):
        """正常系: 翻訳方向（短縮形）"""
        from main import parse_arguments

        args = parse_arguments(["/app/input/test.pdf", "-d", "ja-to-en"])

        assert args.direction == "ja-to-en"

    def test_parse_output_file(self):
        """正常系: 出力ファイル引数"""
        from main import parse_arguments

        args = parse_arguments(
            [
                "/app/input/test.pdf",
                "--direction",
                "ja-to-en",
                "--output",
                "/app/output/result.pdf",
            ]
        )

        assert args.output == "/app/output/result.pdf"

    def test_parse_output_short(self):
        """正常系: 出力ファイル（短縮形）"""
        from main import parse_arguments

        args = parse_arguments(
            ["/app/input/test.pdf", "-d", "ja-to-en", "-o", "/app/output/result.pdf"]
        )

        assert args.output == "/app/output/result.pdf"

    def test_parse_auto_detect(self):
        """正常系: 自動言語検出"""
        from main import parse_arguments

        args = parse_arguments(["/app/input/test.pdf", "--auto-detect"])

        assert args.auto_detect is True

    def test_parse_auto_detect_short(self):
        """正常系: 自動言語検出（短縮形）"""
        from main import parse_arguments

        args = parse_arguments(["/app/input/test.pdf", "-a"])

        assert args.auto_detect is True

    def test_parse_verbose(self):
        """正常系: 詳細ログ"""
        from main import parse_arguments

        args = parse_arguments(["/app/input/test.pdf", "-d", "ja-to-en", "--verbose"])

        assert args.verbose is True

    def test_parse_log_file(self):
        """正常系: ログファイル指定"""
        from main import parse_arguments

        args = parse_arguments(
            [
                "/app/input/test.pdf",
                "-d",
                "ja-to-en",
                "--log-file",
                "/app/output/translate.log",
            ]
        )

        assert args.log_file == "/app/output/translate.log"

    def test_parse_missing_input_file(self):
        """異常系: 入力ファイル未指定"""
        from main import parse_arguments

        with pytest.raises(SystemExit):
            parse_arguments([])

    def test_parse_invalid_direction(self):
        """異常系: 無効な翻訳方向"""
        from main import parse_arguments

        with pytest.raises(SystemExit):
            parse_arguments(["/app/input/test.pdf", "--direction", "invalid"])


class TestPDFTranslatorApp:
    """PDFTranslatorAppクラスのテスト"""

    def test_create_app(self):
        """正常系: アプリケーション生成"""
        from main import PDFTranslatorApp
        from config import Config

        with patch("config.Config.load") as mock_load:
            mock_config = Mock()
            mock_config.api.api_key = "test-key"
            mock_load.return_value = mock_config

            app = PDFTranslatorApp(mock_config)
            assert app is not None

    def test_run_file_not_found(self, temp_dir):
        """異常系: 入力ファイル不存在"""
        from main import PDFTranslatorApp
        from config import Config

        mock_config = Mock()
        mock_config.api.api_key = "test-key"

        app = PDFTranslatorApp(mock_config)

        non_existent = str(temp_dir / "nonexistent.pdf")
        result = app.run(
            input_path=non_existent,
            output_path=str(temp_dir / "output.pdf"),
            direction="ja-to-en",
            auto_detect=False,
        )

        assert result is False


class TestMainFunction:
    """main関数のテスト"""

    def test_main_returns_exit_code(self):
        """正常系: main関数が終了コードを返す"""
        from main import main

        # 引数なしで実行すると終了コード1（エラー）
        with patch("sys.argv", ["main.py"]):
            with pytest.raises(SystemExit):
                main()

    def test_main_with_help(self):
        """正常系: ヘルプ表示"""
        from main import main

        with patch("sys.argv", ["main.py", "--help"]):
            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 0


class TestExitCodes:
    """終了コードのテスト"""

    def test_exit_code_constants(self):
        """正常系: 終了コード定数が存在"""
        from main import (
            EXIT_SUCCESS,
            EXIT_INPUT_NOT_FOUND,
            EXIT_INPUT_READ_ERROR,
            EXIT_API_CONNECTION_ERROR,
            EXIT_API_AUTH_ERROR,
            EXIT_OUTPUT_WRITE_ERROR,
            EXIT_UNKNOWN_ERROR,
        )

        assert EXIT_SUCCESS == 0
        assert EXIT_INPUT_NOT_FOUND == 1
        assert EXIT_INPUT_READ_ERROR == 2
        assert EXIT_API_CONNECTION_ERROR == 3
        assert EXIT_API_AUTH_ERROR == 4
        assert EXIT_OUTPUT_WRITE_ERROR == 5
        assert EXIT_UNKNOWN_ERROR == 99


class TestProgressDisplay:
    """進捗表示のテスト"""

    def test_progress_callback(self):
        """正常系: 進捗コールバック"""
        from main import PDFTranslatorApp

        mock_config = Mock()
        mock_config.api.api_key = "test-key"

        app = PDFTranslatorApp(mock_config)

        # 進捗コールバックが設定できること
        progress_values = []

        def on_progress(current, total, message):
            progress_values.append((current, total, message))

        app.set_progress_callback(on_progress)

        # 内部でコールバックが呼ばれることを確認
        app._report_progress(1, 10, "Processing page 1")

        assert len(progress_values) == 1
        assert progress_values[0] == (1, 10, "Processing page 1")


class TestOutputPath:
    """出力パス生成のテスト"""

    def test_generate_output_path_default(self):
        """正常系: デフォルト出力パス生成"""
        from main import generate_output_path
        from pathlib import PurePosixPath

        input_path = "/app/input/document.pdf"
        output_path = generate_output_path(input_path)

        # Use PurePosixPath for cross-platform comparison
        expected = PurePosixPath("/app/output/document_translated.pdf")
        actual = PurePosixPath(output_path.replace("\\", "/"))

        assert actual == expected

    def test_generate_output_path_custom_suffix(self):
        """正常系: カスタムサフィックス"""
        from main import generate_output_path
        from pathlib import PurePosixPath

        input_path = "/app/input/document.pdf"
        output_path = generate_output_path(input_path, suffix="_en")

        expected = PurePosixPath("/app/output/document_en.pdf")
        actual = PurePosixPath(output_path.replace("\\", "/"))

        assert actual == expected

    def test_generate_output_path_custom_dir(self):
        """正常系: カスタム出力ディレクトリ"""
        from main import generate_output_path
        from pathlib import PurePosixPath

        input_path = "/app/input/document.pdf"
        output_path = generate_output_path(input_path, output_dir="/custom/output")

        expected = PurePosixPath("/custom/output/document_translated.pdf")
        actual = PurePosixPath(output_path.replace("\\", "/"))

        assert actual == expected


class TestLogging:
    """ログ設定のテスト"""

    def test_setup_logging_default(self):
        """正常系: デフォルトログ設定"""
        from main import setup_logging

        logger = setup_logging(verbose=False)

        assert logger is not None

    def test_setup_logging_verbose(self):
        """正常系: 詳細ログ設定"""
        from main import setup_logging

        logger = setup_logging(verbose=True)

        assert logger is not None

    def test_setup_logging_with_file(self, temp_dir):
        """正常系: ファイル出力ログ設定"""
        from main import setup_logging

        log_file = str(temp_dir / "test.log")
        logger = setup_logging(verbose=False, log_file=log_file)

        assert logger is not None

        # Close handlers to release file lock on Windows
        for handler in logger.handlers[:]:
            handler.close()
            logger.removeHandler(handler)
