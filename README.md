# PDF Translator

PDF文書を日英双方向で翻訳するCLIツール。Claude APIを使用した高品質な翻訳と、元PDFのレイアウト（背景画像、ベクターグラフィック）を完全保持します。

## 特徴

- **双方向翻訳**: 日本語→英語、英語→日本語に対応
- **レイアウト完全保持**: 元PDF複製＋テキスト置換方式により、背景・図形・画像をそのまま保持
- **高品質翻訳**: Claude API（Sonnet/Opus）による文脈を考慮した自然な翻訳
- **言語自動検出**: ソース言語を自動判定するオプション
- **日本語フォント対応**: システムフォント（メイリオ等）を自動検出して使用

## インストール

### 前提条件

- Python 3.11以上
- Anthropic APIキー

### セットアップ

```bash
# リポジトリをクローン
git clone https://github.com/ei-nakamura/pdf-translator.git
cd pdf-translator

# 仮想環境を作成（推奨）
python -m venv venv
source venv/bin/activate  # Linux/macOS
# または
venv\Scripts\activate  # Windows

# 依存関係をインストール
pip install -r requirements.txt

# 環境変数を設定
cp .env.example .env
# .envファイルを編集してANTHROPIC_API_KEYを設定
```

## 使い方

### 基本的な使用

```bash
# 日本語→英語
python main.py input.pdf --direction ja-to-en

# 英語→日本語
python main.py input.pdf --direction en-to-ja

# 言語自動検出
python main.py input.pdf --auto-detect
```

### オプション

| オプション | 短縮形 | 説明 |
|-----------|-------|------|
| `--output` | `-o` | 出力ファイルパス（デフォルト: 自動生成） |
| `--direction` | `-d` | 翻訳方向（`ja-to-en` または `en-to-ja`） |
| `--auto-detect` | `-a` | 言語自動検出モード |
| `--verbose` | `-v` | 詳細ログ出力 |
| `--log-file` | `-l` | ログファイルパス |
| `--version` | | バージョン表示 |

### 使用例

```bash
# 出力ファイル名を指定
python main.py document.pdf -d ja-to-en -o translated.pdf

# 詳細ログを表示
python main.py document.pdf -d en-to-ja -v

# ログをファイルに出力
python main.py document.pdf -a -l translation.log
```

## Docker での実行

```bash
# イメージをビルド
docker-compose build

# 翻訳を実行（inputフォルダにPDFを配置）
docker-compose run --rm pdf-translator /app/input/document.pdf --direction ja-to-en
```

## プロジェクト構成

```
pdf-translator/
├── main.py                 # CLIエントリーポイント
├── config.py               # 設定管理
├── modules/
│   ├── pdf_reader.py       # PDF読み込み・テキスト抽出
│   ├── translator.py       # Claude API翻訳
│   ├── pdf_writer.py       # PDF出力（テキスト置換）
│   └── layout_manager.py   # レイアウト情報管理
├── tests/                  # ユニットテスト
├── docs/                   # 設計書・ドキュメント
├── input/                  # 入力PDFディレクトリ
├── output/                 # 出力PDFディレクトリ
└── fonts/                  # カスタムフォント（オプション）
```

## 設定

`.env`ファイルで以下の設定が可能です：

```env
# 必須
ANTHROPIC_API_KEY=your-api-key

# オプション
CLAUDE_MODEL=claude-sonnet-4-20250514
MAX_TOKENS=4000
TEMPERATURE=0.3
```

## レイアウト保持の仕組み

従来の「新規PDF作成」方式ではなく、**元PDF複製＋テキスト置換**方式を採用：

1. 元PDFを開く（背景・画像・図形をすべて保持）
2. テキスト領域にredact注釈を追加
3. redactionを適用してテキストを削除
4. 同じ位置に翻訳テキストを配置
5. 変更されたPDFを保存

これにより：
- ベクターグラフィック（背景、アイコン、図形）が完全保持
- 画像が元の位置に保持
- 複雑なレイアウトでも崩れにくい

## テスト

```bash
# 全テストを実行
python -m pytest

# カバレッジ付きで実行
python -m pytest --cov=modules --cov-report=html
```

## 制限事項

- 画像化されたテキスト（スキャンPDF）は非対応
- 翻訳後の文字数増加により、フォントサイズが自動縮小される場合あり
- 最小フォントサイズ（6pt）に達した場合、テキストがはみ出す可能性
- 特殊フォントは代替フォントに置換

## ライセンス

MIT License

## 作成者

Claude Code

---

**バージョン**: 1.0.0
