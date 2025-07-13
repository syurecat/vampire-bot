# データベース構成

このディレクトリでは、Discord Bot の音声接続ログやユーザー統計情報を管理するためのデータベースを操作しています。SQLAlchemy を使用して、ORMベースの管理を行っています。

## 依存

- Python 3.10+
- SQLAlchemy
- SQLite(後に他DBも対応予定)

---

## テーブル構成

### `guilds`

サーバー設定などの保存を行うテーブル

| カラム名              | 型       | 説明                             |
|----------------------|----------|----------------------------------|
| `guild_id`           | Integer  | サーバーID (PrimaryKey)         |
| `notification_channel` | Integer | 通知チャンネルのID（nullable） |

---

### `users`

ユーザー固有の情報です。

| カラム名         | 型       | 説明                           |
|------------------|----------|--------------------------------|
| `user_id`        | Integer  | ユーザーID (PrimaryKey)       |
| `speaker_id`     | Integer  | 音声タイプID（拡張用）        |
| `command_count`  | Integer  | コマンド使用回数              |
| `likeability`    | Integer  | 好感度（ゲーム要素などに使用）|

---

### `guild_users`

サーバーごとのユーザー情報を格納する中間テーブルです。

| カラム名   | 型       | 説明                                       |
|------------|----------|--------------------------------------------|
| `id`       | Integer  | 内部ID (PrimaryKey, autoincrement)         |
| `guild_id` | Integer  | サーバーID（外部キー: `guilds.guild_id`） |
| `user_id`  | Integer  | ユーザーID（外部キー: `users.user_id`）   |
| `join_date`| Integer  | サーバーで初めてコマンドを実行したUNIX時間（nullable）    |

---

### `vc_summary`

VCに接続した統計データを月別にまとめて格納します。

| カラム名               | 型       | 説明                           |
|------------------------|----------|--------------------------------|
| `id`                   | Integer  | `guild_users.id`（外部キー）  |
| `channel_id`           | Integer  | VCチャンネルのID               |
| `year`                 | Integer  | 対象年                         |
| `month`                | Integer  | 対象月                         |
| `total_connection_time` | Integer | 接続時間（秒単位）            |
| `total_mic_on_time`    | Integer | ミュートしていた時間（秒）  |

複合主キー: (`id`, `channel_id`, `year`, `month`)

---

### `vc_sessions`

VCの接続/切断イベントを逐次的に保存します（集計処理に利用）。

| カラム名     | 型       | 説明                           |
|--------------|----------|--------------------------------|
| `id`         | Integer  | `guild_users.id`（外部キー）  |
| `channel_id` | Integer  | VCチャンネルのID               |
| `event_time` | Integer  | イベントが起きたUNIX時間       |
| `mic_on`     | Integer  | ミュート状態（0: ON, 1: MUTE）|

複合主キー: (`id`, `channel_id`)
