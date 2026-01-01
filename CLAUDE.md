# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Methodology

This project follows **Test-Driven Development (TDD)**. When adding or modifying features:

1. **Review requirements and design documents first**
   - Check `docs/requirements_definition.md` for requirements
   - Check relevant design docs in `docs/design/` folder
   - Update documents if the change affects specifications

2. **Write or update tests before implementation**
   - Add test cases to the appropriate `tests/test_*.py` file
   - Ensure tests cover both normal and error cases

3. **Implement the code**
   - Write the minimum code to pass the tests
   - Follow existing code patterns and style

4. **Run all tests**
   - Always run `python -m pytest` before committing
   - All tests must pass

## Project Overview

PDF Translator is a CLI tool for bidirectional Japanese-English PDF translation using Claude API. It uses a "source PDF duplication + text replacement" approach that preserves the original layout (backgrounds, vector graphics, images) while replacing text.

## Common Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run translation
python main.py input.pdf --direction ja-to-en
python main.py input.pdf --direction en-to-ja
python main.py input.pdf --auto-detect

# Run all tests
python -m pytest

# Run tests with coverage
python -m pytest --cov=modules --cov-report=html

# Run a single test file
python -m pytest tests/test_pdf_reader.py

# Run a specific test
python -m pytest tests/test_translator.py::test_translate_ja_to_en -v
```

## Architecture

### Data Flow
1. `PDFReader` opens PDF and extracts text blocks with layout info into `DocumentData`
2. `Translator` translates each `TextBlock` via Claude API (with retry logic)
3. `PDFWriter` uses redact-and-replace approach on the original PDF:
   - Adds redact annotations to text areas
   - Applies redactions (removes text)
   - Writes translated text in same positions

### Core Modules

- **main.py**: CLI entry point, `PDFTranslatorApp` orchestrates the pipeline
- **config.py**: Configuration via environment variables (`.env` file), `Config.load()` for initialization
- **modules/layout_manager.py**: Data classes (`BoundingBox`, `TextBlock`, `PageData`, `DocumentData`) shared across modules
- **modules/pdf_reader.py**: PyMuPDF-based text extraction, language detection
- **modules/translator.py**: Claude API integration with exponential backoff retry
- **modules/pdf_writer.py**: PDF output using redact annotations; handles Japanese fonts via system font detection

### Key Design Decisions

- Uses PyMuPDF (`fitz`) for both reading and writing PDFs
- Japanese font handling: auto-detects system fonts (Meiryo on Windows, Noto on Linux, Hiragino on macOS)
- Text replacement via redact annotations preserves underlying PDF structure
- Font size auto-scaling when translated text is longer than original (minimum 6pt)
- All extracted data copied to dataclasses before PDF handle is closed

## Configuration

Required: `ANTHROPIC_API_KEY` environment variable (or in `.env` file)

Optional settings: `CLAUDE_MODEL`, `MAX_TOKENS`, `TEMPERATURE`, `INPUT_DIR`, `OUTPUT_DIR`, `FONT_DIR`

## Testing Notes

- Tests use pytest fixtures defined in `tests/conftest.py`
- Mock API key format: `sk-ant-api03-...`
- `clean_env_and_logging` fixture auto-cleans environment between tests
- **Always run tests before committing**: `python -m pytest`
