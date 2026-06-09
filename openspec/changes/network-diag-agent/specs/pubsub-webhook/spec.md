## ADDED Requirements

### Requirement: 接收 Pub/Sub push 通知
系統 SHALL 在 `POST /pubsub/push` 端點接收來自 Google Cloud Pub/Sub 的 HTTP push 通知，立即回傳 HTTP 200，並以非同步方式處理診斷流程。

#### Scenario: 正常接收並非同步處理
- **WHEN** Pub/Sub 推送一個合法的 push 通知到 `/pubsub/push`
- **THEN** 系統立即回傳 HTTP 200
- **AND** 系統在背景執行後續診斷流程

#### Scenario: message data 解碼
- **WHEN** 收到的 Pub/Sub message 包含 base64 編碼的 `data` 欄位
- **THEN** 系統 SHALL 將其 decode 為 UTF-8 字串
- **AND** 從中提取 Gmail message ID（`emailAddress` + `historyId` 或直接 `messageId`）

#### Scenario: 無效 payload 不重試
- **WHEN** 收到的 payload 格式不符（缺少 `message` 欄位或無法解碼）
- **THEN** 系統 SHALL 回傳 HTTP 200（避免 Pub/Sub 重複推送）
- **AND** 記錄警告 log

#### Scenario: 重複訊息去重
- **WHEN** 同一個 Pub/Sub message ID 在 60 秒內被推送超過一次
- **THEN** 系統 SHALL 忽略重複訊息
- **AND** 仍回傳 HTTP 200
