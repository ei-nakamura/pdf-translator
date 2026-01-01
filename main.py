"""
PDF Translator - Main CLI Module

PDF翻訳アプリケーションのエントリーポイント
"""

import argparse
import logging
import sys
import time
from pathlib import Path
from typing import Optional, Callable, List

from config import Config, ConfigError, MissingConfigError
from modules.pdf_reader import PDFReader, PDFReadError
from modules.translator import Translator, TranslationDirection, TranslationError
from modules.pdf_writer import PDFWriter, PDFWriteError
from modules.layout_manager import LayoutManager, PageData


VERSION = "1.0.0"

EXIT_SUCCESS = 0
EXIT_INPUT_NOT_FOUND = 1
EXIT_INPUT_READ_ERROR = 2
EXIT_API_CONNECTION_ERROR = 3
EXIT_API_AUTH_ERROR = 4
EXIT_OUTPUT_WRITE_ERROR = 5
EXIT_UNKNOWN_ERROR = 99

# Aliases for backward compatibility
EXIT_FILE_NOT_FOUND = EXIT_INPUT_NOT_FOUND
EXIT_FILE_READ_ERROR = EXIT_INPUT_READ_ERROR
EXIT_FILE_WRITE_ERROR = EXIT_OUTPUT_WRITE_ERROR


def setup_logging(verbose: bool = False, log_file: Optional[str] = None) -> logging.Logger:
    logger = logging.getLogger("pdf_translator")
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)

    # Remove existing handlers to avoid duplication
    logger.handlers.clear()

    formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s")

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG if verbose else logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    if log_file:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def parse_arguments(args: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse command line arguments.

    Args:
        args: List of arguments to parse. If None, uses sys.argv.

    Returns:
        Parsed arguments namespace.
    """
    parser = argparse.ArgumentParser(
        description="PDF Translation Tool - Translate PDF documents using Claude API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("input_file", help="Input PDF file path")
    parser.add_argument("-o", "--output", help="Output PDF file path")
    parser.add_argument(
        "-d", "--direction",
        choices=["ja-to-en", "en-to-ja"],
        help="Translation direction",
    )
    parser.add_argument(
        "-a", "--auto-detect",
        action="store_true",
        help="Auto-detect source language",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument("-l", "--log-file", help="Log file path")
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")

    return parser.parse_args(args)


def generate_output_path(
    input_path: str,
    suffix: str = "_translated",
    output_dir: Optional[str] = None
) -> str:
    """Generate output file path from input path.

    Args:
        input_path: Input PDF file path.
        suffix: Suffix to add to the filename.
        output_dir: Optional output directory. Defaults to /app/output.

    Returns:
        Generated output file path.
    """
    path = Path(input_path)

    if output_dir:
        out_dir = Path(output_dir)
    else:
        out_dir = Path("/app/output")

    return str(out_dir / f"{path.stem}{suffix}.pdf")


class PDFTranslatorApp:
    """PDF翻訳アプリケーション"""

    def __init__(self, config: Config, logger: Optional[logging.Logger] = None):
        self._config = config
        self._logger = logger or logging.getLogger("pdf_translator")
        self._reader: Optional[PDFReader] = None
        self._translator: Optional[Translator] = None
        self._writer: Optional[PDFWriter] = None
        self._layout_manager: Optional[LayoutManager] = None
        self._progress_callback: Optional[Callable[[int, int, str], None]] = None

    def set_progress_callback(self, callback: Callable[[int, int, str], None]) -> None:
        """Set a callback for progress updates.

        Args:
            callback: A function that takes (current, total, message) parameters.
        """
        self._progress_callback = callback

    def _report_progress(self, current: int, total: int, message: str) -> None:
        """Report progress to the callback if set.

        Args:
            current: Current progress value.
            total: Total progress value.
            message: Progress message.
        """
        if self._progress_callback:
            self._progress_callback(current, total, message)

    def run(self, input_path: str, output_path: str, direction: str, auto_detect: bool) -> bool:
        self._logger.info(f"PDF Translation Tool v{VERSION}")
        self._logger.info("=" * 50)

        try:
            # PDF読み込み + テキスト抽出
            self._reader = PDFReader()
            doc_data = self._reader.open(input_path)
            self._logger.info(f"Input: {input_path} ({doc_data.page_count} pages)")
            self._logger.info(f"Output: {output_path}")

            self._layout_manager = LayoutManager()
            self._layout_manager.set_document(doc_data)

            # 言語検出
            if auto_detect:
                all_text = " ".join(
                    block.text for page in doc_data.pages for block in page.text_blocks
                )
                detected_lang = self._reader.detect_language(all_text)
                direction = "ja-to-en" if detected_lang == "ja" else "en-to-ja"
                self._logger.info(f"Detected language: {detected_lang}")

            trans_direction = (
                TranslationDirection.JA_TO_EN
                if direction == "ja-to-en"
                else TranslationDirection.EN_TO_JA
            )
            target_lang = "en" if direction == "ja-to-en" else "ja"
            direction_str = "Japanese → English" if direction == "ja-to-en" else "English → Japanese"
            self._logger.info(f"Direction: {direction_str}")

            # 翻訳モジュール初期化
            self._translator = Translator(
                api_key=self._config.api.api_key,
                model=self._config.api.model,
            )

            # PDFReader を閉じる（doc_dataにはすでにデータがコピーされている）
            self._reader.close()
            self._reader = None

            # PDFWriter初期化 - 元PDFを複製する新方式
            self._writer = PDFWriter()
            self._writer.open_source(input_path)

            self._logger.info("")
            self._logger.info("Processing...")
            start_time = time.time()

            # 各ページを処理
            for i, page_data in enumerate(doc_data.pages):
                self._logger.info(f"Processing page {i + 1}/{doc_data.page_count}...")
                self._report_progress(i + 1, doc_data.page_count, f"Processing page {i + 1}")

                # テキストブロックを翻訳
                translated_page = self._process_page(i, page_data, trans_direction)

                # 元PDFのテキストを置換
                self._writer.replace_text_on_page(i, translated_page.text_blocks, target_lang)

            self._writer.save(output_path)
            elapsed = time.time() - start_time

            self._logger.info("")
            self._logger.info("Completed!")
            self._logger.info(f"- Total pages: {doc_data.page_count}")
            self._logger.info(f"- Processing time: {elapsed:.1f} seconds")
            self._logger.info(f"- Output file: {output_path}")

            return True

        except FileNotFoundError as e:
            self._logger.error(f"File not found: {e}")
            return False
        except PDFReadError as e:
            self._logger.error(f"PDF read error: {e}")
            return False
        except TranslationError as e:
            self._logger.error(f"Translation error: {e}")
            return False
        except PDFWriteError as e:
            self._logger.error(f"PDF write error: {e}")
            return False
        finally:
            self._cleanup()

    def _process_page(self, page_num: int, page_data: PageData, direction: TranslationDirection) -> PageData:
        if not page_data.text_blocks:
            return page_data

        self._translator.translate_blocks(page_data.text_blocks, direction)
        return page_data

    def _cleanup(self) -> None:
        if self._reader:
            self._reader.close()
        if self._writer:
            self._writer.close()


def main() -> int:
    args = parse_arguments()

    logger = setup_logging(verbose=args.verbose, log_file=args.log_file)

    input_path = args.input_file
    if not Path(input_path).exists():
        logger.error(f"Input file not found: {input_path}")
        return EXIT_INPUT_NOT_FOUND

    try:
        config = Config.load()
    except MissingConfigError as e:
        logger.error(f"Configuration error: {e}")
        return EXIT_API_AUTH_ERROR
    except ConfigError as e:
        logger.error(f"Configuration error: {e}")
        return EXIT_UNKNOWN_ERROR

    if not args.direction and not args.auto_detect:
        logger.error("Please specify --direction or --auto-detect")
        return EXIT_UNKNOWN_ERROR

    if args.output:
        output_path = args.output
    else:
        suffix = "_translated"
        if args.direction:
            lang = args.direction.split("-")[-1]
            suffix = f"_{lang}"
        output_path = generate_output_path(input_path, suffix=suffix, output_dir=str(config.pdf.output_dir))

    app = PDFTranslatorApp(config, logger)
    success = app.run(input_path, output_path, args.direction or "", args.auto_detect)

    return EXIT_SUCCESS if success else EXIT_UNKNOWN_ERROR


if __name__ == "__main__":
    sys.exit(main())
