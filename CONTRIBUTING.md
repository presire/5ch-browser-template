# コントリビューションガイド

PRやIssueをお寄せいただきありがとうございます。
スムーズなレビューのために、以下の方針をご確認ください。

## 設計方針: 意図的なモノリス構造

このプロジェクトは日常的なメンテナンスを Claude Code (AIコーディングエージェント) に委ねる前提で設計されています。そのため、人間にとっての可読性よりも **AIにとってのメンテナンスしやすさ** を優先しており、以下のモノリス構造を意図的に採用しています。

| ファイル | ルール |
|---------|--------|
| `apps/desktop/src/App.tsx` | **分割禁止** — 明示的な指示がない限り単一ファイルを維持 |
| `apps/desktop/src/styles.css` | **分割禁止** — CSSモジュール・CSS-in-JS は不使用 |
| 各 Rust crate の `lib.rs` | **2000行超まで分割しない** |

### なぜモノリスなのか

1. **編集の局所性**: 機能追加が1ファイルで完結し、ファイル間の同期作業が発生しない
2. **prop-drilling の回避**: 状態が closure スコープで全関数から直接参照できる
3. **Grep → Edit の1ループ**: 実装・呼び出し元・型定義が同一ファイルにあり、探索コストがゼロ
4. **リファクタの自由度**: 関数シグネチャや state 形状を変えてもファイル境界の型同期が不要

## 歓迎するPR

- バグ修正
- 新機能の追加
- パフォーマンス改善
- Linux/macOS 固有の問題対応
- ドキュメントの改善

## 受け入れられないPR

- `App.tsx` や `lib.rs` のファイル分割・モジュール切り出し
- Redux, Context Provider, CSS-in-JS 等の導入

### npm ランタイム依存について

現在のランタイム依存は react, react-dom, @tauri-apps/api, lucide-react の4つのみに絞っています。バンドルサイズ (Tauriはフロントエンドをバイナリに埋め込む)、サプライチェーンリスク、AIメンテナンスとの相性が理由です。新規依存の追加を検討する場合は、Issue で事前に相談してください。

---

迷った場合も Issue で気軽に相談してください。

## 開発の流れ

1. Issue で提案 (大きな変更の場合)
2. フォーク → ブランチ作成 → 実装
3. PR 作成

### チェックリスト

```bash
cargo check --workspace                   # Rust 型チェック
cargo clippy --workspace -- -D warnings   # Rust lint
cd apps/desktop && npx tsc --noEmit       # TypeScript 型チェック
cd apps/desktop && npm run build && npm run test:smoke-ui  # UIスモークテスト
```

## コード規約

詳細は以下を参照してください:

- [CLAUDE.md](CLAUDE.md) — プロジェクト全体の概要・規約
- [docs/DEVELOPER_GUIDE.md](docs/DEVELOPER_GUIDE.md) — 技術仕様・アーキテクチャ
