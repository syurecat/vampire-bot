# Vampire bot
小規模向けの小さなdiscordbotです。身内での遊び用途にお使いください。

以下の主な機能を提供しています：
- VC接続時間の記録と集計
- じゃんけん（通常/対話式）
- ダイスロール・チンチロ・ダイスポーカー
- サーバー通知チャンネル設定
- ユーザーごとの使用統計記録

## 使用方法
### botの準備
[こちら](https://discordpy.readthedocs.io/ja/stable/discord.html) を参考にdiscordbotを用意してください。その際、適切な権限設定を行ってください。
### 環境変数設定
`.env` ファイルをプロジェクトルートに配置して、以下の値を設定してください：
```env
DISCORD_TOKEN=YOUR_DISCORD_BOT_TOKEN
CHANNEL_ID=DEFAULT_CHANNEL_ID
LOG_LEVEL=INFO
ADVANCED_LOG_LEVEL=WARNING
```
### パッケージのインストール
```sh
pip install -r requirements.txt
```
### 実行方法
```sh
py main.py
```
## アプリケーションコマンド一覧
### ゲーム系
`/rps`
ランダムでBotがじゃんけんを出します。

`/rps-me`
Botと直接じゃんけんをプレイ。ボタン式で選択できます。

`/dice roll:int side:int`
指定した面数・回数でサイコロを振ります。

`/chinchiro`
3個のサイコロでチンチロを実行します。

`/dice-poker`
一般的なトランプ風のダイスポーカーを実行します。

`/dice-poker-stgr`
ストグラ風のダイスポーカーを振ります（1〜6の数値で5個）。

### VCログ系
`/vc-time channel:VoiceChannel year:int month:int ephemeral:bool`
過去のVC接続時間とミュート状態の統計を確認できます。

### サーバー設定系（管理者権限）
`/server-settings notification-channel channel:TextChannel`
通知を送信するチャンネルを設定します。

### その他
`/ping`
動作確認用。pong! を返します。

## log設定
ログレベルは `.env` にて設定可能です。（`LOG_LEVEL`, `ADVANCED_LOG_LEVEL`）
コンソールには `RichHandler` によって出力されるようになっています。
慣れていないためミスがあったら教えて下さい。