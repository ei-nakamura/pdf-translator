# PDF翻訳プログラム 要件定義書

## 1. 概要

PDFファイルを読み込み、AI（Claude API）を使用してテキストを翻訳し、翻訳結果をPDF形式で出力するプログラム。
日本語⇔英語の双方向翻訳に対応。
**Dockerコンテナ上で動作**し、環境に依存しないポータブルな実行環境を提供。

## 2. 機能要件

### 2.1 PDF読み込み機能
- 入力PDFファイルからテキストを抽出
- 複数ページのPDFに対応
- テキストの構造（段落、見出し等）を可能な限り保持
- テキストの位置情報（座標、フォント情報）を取得

### 2.2 翻訳機能
- 日本語→英語、英語→日本語の双方向翻訳に対応
- Claude APIを使用した高品質な翻訳
- 翻訳元言語の自動検出または手動指定
- 文脈を考慮した自然な翻訳

### 2.3 PDF出力機能
- 翻訳結果をPDF形式で出力
- **元のPDFを複製し、テキスト部分のみを置換する方式**でレイアウトを完全保持
  - 背景画像・描画要素（ベクターグラフィック）の完全保持
  - テキストブロックの位置
  - フォントサイズ（翻訳後の文字数に応じて自動調整）
  - ページサイズ
  - 画像やグラフィックスの配置

## 3. 技術仕様

### 3.1 使用技術スタック

#### コンテナ環境

- **Docker**: コンテナ実行環境
- **Docker Compose**: マルチコンテナ管理（オプション）
- **ベースイメージ**: python:3.11-slim
  - 軽量で高速なビルド
  - 必要なシステム依存関係を追加インストール

#### プログラミング言語

- Python 3.11

#### 使用ライブラリ
- **PDF読み込み**: PyMuPDF (pymupdf)
  - レイアウト情報の詳細な取得が可能
  - 高速で安定した動作
- **PDF出力**: PyMuPDF
  - 元PDFを複製してテキスト置換する方式
  - 描画要素（ベクターグラフィック）の完全保持
- **AI翻訳**: Anthropic Claude API
  - モデル: Claude 3.5 Sonnet または Claude Opus 4.5
  - 高品質な翻訳と文脈理解
  - 長文対応

#### その他
- python-dotenv: 環境変数管理
- anthropic: Claude API公式SDK

### 3.2 プログラム構成

```
pdf-translator/
├── main.py                 # メインプログラム（CLI）
├── modules/
│   ├── __init__.py
│   ├── pdf_reader.py      # PDF読み込み + レイアウト情報抽出
│   ├── translator.py      # Claude API翻訳
│   ├── pdf_writer.py      # レイアウト保持PDF出力
│   └── layout_manager.py  # レイアウト情報管理
├── config.py              # 設定（APIキー等）
├── fonts/                 # 日本語フォントファイル
│   └── NotoSansJP-Regular.ttf
├── input/                 # 入力PDFファイル配置ディレクトリ（ボリュームマウント）
├── output/                # 出力PDFファイル配置ディレクトリ（ボリュームマウント）
├── Dockerfile             # Dockerイメージ定義
├── docker-compose.yml     # Docker Compose設定
├── .env                   # 環境変数（APIキー）
├── .env.example           # 環境変数のサンプル
├── .dockerignore          # Dockerビルド除外設定
├── requirements.txt       # 依存ライブラリ
└── README.md             # 使用方法
```

### 3.3 データフロー

```
入力PDF（ホスト: ./input/）
  ↓ ボリュームマウント
[Dockerコンテナ]
  ├─ [PDF読み込み] → テキスト + レイアウト情報抽出
  ├─ [翻訳処理] → Claude APIで翻訳
  └─ [PDF生成] → 元PDFを複製し、テキスト部分を翻訳テキストで置換
  ↓ ボリュームマウント
出力PDF（ホスト: ./output/）
```

### 3.3.1 レイアウト保持方式の詳細

現在の実装では「元PDFを複製してテキストを置換する」方式を採用：

1. **元PDFの複製**: 入力PDFをそのまま複製（背景、画像、描画要素をすべて保持）
2. **テキスト領域の消去**: 元のテキストブロックの領域を白色で塗りつぶし
3. **翻訳テキストの配置**: 同じ位置に翻訳後のテキストを配置

この方式により：

- ベクターグラフィック（背景、アイコン、図形）が完全に保持される
- 画像が元の位置に保持される
- レイアウト崩れが最小限に抑えられる

### 3.4 Docker構成

#### Dockerfile概要

```dockerfile
FROM python:3.11-slim

# システム依存関係のインストール
RUN apt-get update && apt-get install -y \
    libmupdf-dev \
    fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 依存関係のインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションコードのコピー
COPY . .

# 入出力ディレクトリの作成
RUN mkdir -p /app/input /app/output

ENTRYPOINT ["python", "main.py"]
```

#### docker-compose.yml概要

```yaml
version: '3.8'

services:
  pdf-translator:
    build: .
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
    volumes:
      - ./input:/app/input      # 入力PDFを配置
      - ./output:/app/output    # 翻訳結果を出力
    # コマンドはdocker-compose run時に指定
```

### 3.5 ボリュームマウント設計

| ホスト側     | コンテナ側           | 用途                           |
| ------------ | -------------------- | ------------------------------ |
| `./input/`   | `/app/input/`        | 翻訳対象のPDFファイルを配置    |
| `./output/`  | `/app/output/`       | 翻訳結果のPDFファイルを出力    |
| `./.env`     | 環境変数として注入   | APIキー等の機密情報            |

## 4. 非機能要件

### 4.1 性能
- 1ページあたりの処理時間：数秒～数十秒程度（API応答時間に依存）
- 最大ファイルサイズ：100MB程度
- 最大ページ数：100ページ程度（必要に応じて拡張可能）

### 4.2 使いやすさ

- Dockerコマンド1行で実行可能
- docker-composeによる簡易実行
- 進捗状況の表示（処理中のページ番号等）
- エラー時の適切なメッセージ表示
- ログ出力機能

### 4.3 拡張性
- 将来的に他言語への拡張が容易な設計
- 翻訳APIの切り替えが容易
- モジュール化された設計

### 4.4 セキュリティ

- APIキーは環境変数で管理（.envファイル経由）
- .envファイルは.gitignoreに追加
- .dockerignoreで機密ファイルをイメージから除外
- コンテナは非rootユーザーでの実行を推奨

## 5. 入出力仕様

### 5.1 入力
- **PDFファイルパス**（必須）
  - 形式: .pdf
  - 文字コード: UTF-8対応
- **翻訳方向**（必須）
  - `ja-to-en`: 日本語→英語
  - `en-to-ja`: 英語→日本語
  - または自動検出オプション
- **出力ファイルパス**（オプション）
  - 未指定時は自動生成（例: `input_translated.pdf`）

### 5.2 出力
- **翻訳されたPDFファイル**
  - 元のレイアウトを保持
  - 日英対応フォントを使用
- **ログファイル**（オプション）
  - 処理履歴
  - エラー情報

### 5.3 コマンド例

#### Docker Composeを使用する場合（推奨）

```bash
# ビルド
docker-compose build

# 基本的な使用（inputフォルダにPDFを配置後）
docker-compose run --rm pdf-translator /app/input/document.pdf --direction ja-to-en

# 出力ファイル名を指定
docker-compose run --rm pdf-translator /app/input/document.pdf --direction en-to-ja --output /app/output/translated.pdf
```

#### Dockerコマンドを直接使用する場合

```bash
# ビルド
docker build -t pdf-translator .

# 実行
docker run --rm \
  -v $(pwd)/input:/app/input \
  -v $(pwd)/output:/app/output \
  -e ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY} \
  pdf-translator /app/input/document.pdf --direction ja-to-en
```

#### ローカル実行（開発用）

```bash
# 基本的な使用
python main.py input.pdf --direction ja-to-en

# 自動言語検出
python main.py input.pdf --auto-detect
```

## 6. 制約事項

### 6.1 技術的制約
- **画像化されたテキスト**: OCRが必要なため初期版では非対応
- **複雑なレイアウト**: 表、図表、多段組の完全な再現は困難
- **フォント**: 利用可能な日英対応フォントに限定
- **文字数変化**: 翻訳により文字数が変化するため、完全な位置再現は困難

### 6.2 コスト制約
- Claude API利用には課金が発生
- 大量のページ処理時はコストに注意

### 6.3 言語制約
- 初期版は日本語・英語のみ対応
- 混在言語（1ページ内に日英混在）の処理は要検討

## 7. レイアウト保持の実装方針

### 7.1 実装方式：元PDF複製＋テキスト置換

従来の「新規PDFを作成してレイアウト情報を元に再構築」する方式ではなく、
**「元PDFを複製し、テキスト部分のみを置換」する方式**を採用。

#### 処理フロー

1. **元PDFを開く**: PyMuPDFで入力PDFを読み込み
2. **テキストブロック情報を抽出**: 各ページからテキストとその位置情報を取得
3. **翻訳処理**: Claude APIでテキストを翻訳
4. **テキスト領域を消去**: 元のテキストブロック位置を背景色（通常は白）で塗りつぶし
5. **翻訳テキストを配置**: 同じ位置に翻訳後のテキストを描画
6. **保存**: 変更されたPDFを出力

#### この方式のメリット

- ベクターグラフィック（背景、図形、アイコン）が完全に保持される
- 画像が元の位置・サイズで保持される
- ページレイアウト、余白、回転などがそのまま維持される
- 複雑なレイアウトでも崩れにくい

### 7.2 保持する情報

1. **テキスト位置情報**
   - 各テキストブロックの座標（x, y, width, height）
   - ページ内での相対位置

2. **フォント情報**
   - フォントサイズ
   - フォントスタイル（太字、斜体等）
   - 色情報

3. **ページ情報**
   - ページサイズ（A4, Letter等）
   - 余白
   - 向き（縦/横）

4. **背景・描画要素**（自動保持）
   - ベクターグラフィック
   - 背景色・背景画像
   - 図形・線

### 7.3 テキスト置換の詳細

1. テキストブロック単位で翻訳
2. 元のテキスト領域を消去（redact機能で背景を保持）
3. 同じ位置に翻訳テキストを配置
4. 文字数増減に応じてフォントサイズを自動調整
   - 日本語と英語で文字幅が異なるため、文字種別に応じた係数を使用
   - 日本語（全角）: フォントサイズ × 1.0
   - 英語（半角）: フォントサイズ × 0.55
   - 日英混在テキストは加重平均で幅を推定

### 7.3.1 TranslationGroupのbbox拡張

TranslationGroupで複数のspanがグループ化された場合、翻訳テキストの配置領域を以下のように計算する：

1. **開始位置**: グループ内の最初のspan（`spans[0]`）の左上座標 `(x0, y0)`
2. **終了位置**: グループ内の最後のspan（`spans[-1]`）の右下座標 `(x1, y1)`
3. **拡張bbox**: 上記を組み合わせた `(first.x0, first.y0, last.x1, last.y1)`

この方式により：

- グループ全体をカバーする広い領域に翻訳テキストを配置できる
- フォントサイズの過度な縮小を防止
- 最初のspanのbboxのみを使用する場合と比較して、より大きな配置領域を確保

### 7.4 レイアウト保持の限界

- 翻訳後の文字数が大幅に増えた場合、フォントサイズが小さくなる
- 最小フォントサイズ（6pt）に達した場合、テキストがはみ出す可能性
- 特殊なフォントは代替フォント（日本語: NotoSansCJK、英語: Helvetica）に置き換え
- テキスト背景色が白でない場合、消去処理で背景が見える可能性（将来的に背景色検出で対応予定）

## 8. 実装の優先順位

### Phase 1（MVP: Minimum Viable Product）

1. Docker環境の構築（Dockerfile、docker-compose.yml）
2. PDFからのテキスト抽出（基本機能）
3. Claude API翻訳の実装
4. シンプルなPDF出力（レイアウト保持なし）
5. 基本的なCLI実装

### Phase 2（レイアウト保持）

1. レイアウト情報の抽出
2. レイアウト保持したPDF出力
3. フォント処理の改善（日本語フォント対応）
4. エラーハンドリングの強化

### Phase 3（改善・拡張）

1. 進捗表示の実装
2. ログ機能の充実
3. バッチ処理対応（複数ファイル）
4. Dockerイメージの最適化（マルチステージビルド）

### Phase 4（将来拡張）

1. 他言語対応
2. OCR機能追加
3. Web API化（FastAPI等）
4. Kubernetes対応

## 9. テスト方針

### 9.1 テストケース
- シンプルな1ページPDF
- 複数ページPDF
- 画像を含むPDF
- 表を含むPDF
- 日本語のみ/英語のみ/混在PDF

### 9.2 検証項目
- テキストの正確な抽出
- 翻訳品質
- レイアウトの再現度
- エラーハンドリング
- パフォーマンス

## 10. 開発ステップ

### ステップ1: Docker環境構築

- プロジェクト構造作成
- Dockerfile作成
- docker-compose.yml作成
- .dockerignore作成

### ステップ2: 基本機能実装（Phase 1）

- PDF読み込みモジュール
- 翻訳モジュール
- PDF出力モジュール（シンプル版）
- CLIインターフェース

### ステップ3: Docker動作確認

- イメージビルド
- コンテナ実行テスト
- ボリュームマウント動作確認

### ステップ4: レイアウト保持機能（Phase 2）

- レイアウト情報抽出
- レイアウト保持出力
- 日本語フォント対応

### ステップ5: テスト・改善

- 各種テストケースで動作確認
- バグ修正・改善
- ドキュメント整備

## 11. 参考情報

### 使用予定API・ライブラリのドキュメント

- [Anthropic Claude API](https://docs.anthropic.com/)
- [PyMuPDF Documentation](https://pymupdf.readthedocs.io/)
- [ReportLab Documentation](https://www.reportlab.com/documentation/)
- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)

---

**作成日**: 2026-01-01
**バージョン**: 1.3
**作成者**: Claude Code
**更新履歴**:

- v1.0: 初版作成
- v1.1: Docker使用前提に変更
- v1.2: フォントサイズ自動調整の日本語対応を追記
- v1.3: TranslationGroupのbbox拡張方式を追記
