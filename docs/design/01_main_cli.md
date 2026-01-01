# main.py（CLIモジュール）設計書

## 1. 概要

PDF翻訳プログラムのエントリーポイントとなるCLIモジュール。
コマンドライン引数を解析し、各モジュールを連携させて翻訳処理を実行する。

## 2. 責務

- コマンドライン引数の解析と検証
- 各モジュールの初期化と連携
- 翻訳処理フローの制御
- 進捗状況の表示
- エラーハンドリングとログ出力

## 3. 依存関係

```
main.py
├── modules/pdf_reader.py
├── modules/translator.py
├── modules/pdf_writer.py
├── modules/layout_manager.py
└── config.py
```

## 4. コマンドライン引数

| 引数 | 短縮形 | 必須 | デフォルト | 説明 |
| --- | --- | --- | --- | --- |
| `input_file` | - | Yes | - | 入力PDFファイルパス |
| `--output` | `-o` | No | 自動生成 | 出力PDFファイルパス |
| `--direction` | `-d` | No | - | 翻訳方向（ja-to-en / en-to-ja） |
| `--auto-detect` | `-a` | No | False | 言語自動検出モード |
| `--verbose` | `-v` | No | False | 詳細ログ出力 |
| `--log-file` | `-l` | No | None | ログファイルパス |

## 5. クラス設計

### 5.1 PDFTranslatorApp クラス

```python
class PDFTranslatorApp:
    """PDF翻訳アプリケーションのメインクラス"""

    def __init__(self, config: Config):
        """
        Args:
            config: 設定オブジェクト
        """
        pass

    def run(self, input_path: str, output_path: str,
            direction: str, auto_detect: bool) -> bool:
        """
        翻訳処理を実行

        Args:
            input_path: 入力PDFパス
            output_path: 出力PDFパス
            direction: 翻訳方向
            auto_detect: 言語自動検出フラグ

        Returns:
            bool: 処理成功時True
        """
        pass

    def _process_page(self, page_num: int, page_data: PageData) -> PageData:
        """
        1ページの翻訳処理

        Args:
            page_num: ページ番号
            page_data: ページデータ

        Returns:
            PageData: 翻訳済みページデータ
        """
        pass
```

## 6. 処理フロー

```text
1. コマンドライン引数の解析
   ├── argparseによる引数パース
   └── 引数の検証（ファイル存在確認等）

2. 設定の読み込み
   ├── config.pyから設定読み込み
   └── 環境変数からAPIキー取得

3. 各モジュールの初期化
   ├── PDFReader初期化
   ├── Translator初期化（API接続確認）
   └── LayoutManager初期化

4. PDF読み込み
   ├── PDFReaderでテキスト + レイアウト情報抽出
   └── LayoutManagerでレイアウト情報管理

5. 翻訳処理（ページ単位でループ）
   ├── 進捗表示
   ├── テキストブロック単位で翻訳
   └── 翻訳結果をLayoutManagerに反映

6. PDF出力（元PDF複製＋テキスト置換方式）
   ├── PDFWriterで元PDFを開く
   ├── 各ページのテキスト領域を消去
   ├── 翻訳テキストを配置
   └── 変更されたPDFを保存

7. 完了処理
   ├── 処理結果サマリー表示
   └── リソースのクリーンアップ
```

### 6.1 元PDF複製＋テキスト置換方式の詳細

従来の「新規PDFを作成」方式ではなく、元PDFを直接編集する方式を採用：

```text
[入力PDF] ─┬─ テキスト抽出 ───→ [翻訳処理] ───→ [翻訳テキスト]
           │                                          │
           └─ 複製 ────────────────────────────────────┘
                                                       │
                                               [テキスト置換]
                                                       │
                                                       ▼
                                                 [出力PDF]
```

この方式により、背景画像、ベクターグラフィック、図形などがすべて保持される。

## 7. エラーハンドリング

| エラー種別 | 対応 | 終了コード |
| --- | --- | --- |
| 入力ファイル不存在 | エラーメッセージ表示して終了 | 1 |
| 入力ファイル読み込み失敗 | エラーメッセージ表示して終了 | 2 |
| API接続エラー | リトライ後、失敗時は終了 | 3 |
| API認証エラー | APIキー確認を促して終了 | 4 |
| 出力ファイル書き込み失敗 | エラーメッセージ表示して終了 | 5 |
| その他の例外 | スタックトレース出力して終了 | 99 |

## 8. ログ出力

### 8.1 ログレベル

- **DEBUG**: 詳細なデバッグ情報（--verbose時）
- **INFO**: 処理進捗、主要イベント
- **WARNING**: 警告（レイアウト崩れの可能性等）
- **ERROR**: エラー情報

### 8.2 ログフォーマット

```
[2026-01-01 12:00:00] [INFO] Processing page 1/10...
[2026-01-01 12:00:05] [INFO] Page 1 translated successfully
[2026-01-01 12:00:05] [WARNING] Text overflow detected on page 1, block 3
```

## 9. 進捗表示

```
PDF Translation Tool v1.0
=========================
Input:  /app/input/document.pdf (10 pages)
Output: /app/output/document_translated.pdf
Direction: Japanese → English

Processing...
[████████████████████████████████████████] 100% (10/10 pages)

Completed!
- Total pages: 10
- Processing time: 45.2 seconds
- Output file: /app/output/document_translated.pdf
```

## 10. 使用例

```bash
# 基本的な使用
python main.py /app/input/document.pdf --direction ja-to-en

# 出力ファイル指定
python main.py /app/input/document.pdf -d en-to-ja -o /app/output/result.pdf

# 言語自動検出
python main.py /app/input/document.pdf --auto-detect

# 詳細ログ出力
python main.py /app/input/document.pdf -d ja-to-en -v -l /app/output/translate.log
```

## 11. テスト項目

- [ ] 正常系：基本的な翻訳処理
- [ ] 正常系：出力ファイル名指定
- [ ] 正常系：言語自動検出
- [ ] 異常系：入力ファイル不存在
- [ ] 異常系：無効な翻訳方向指定
- [ ] 異常系：APIキー未設定
- [ ] 異常系：出力先ディレクトリ不存在

---

**作成日**: 2026-01-01
**バージョン**: 1.0
