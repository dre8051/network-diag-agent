## ADDED Requirements

### Requirement: 讀取完整信件內容
系統 SHALL 透過 Gmail API (OAuth2) 以 message ID 讀取完整信件，提取主旨與純文字 body。

#### Scenario: 成功讀取信件
- **WHEN** 提供有效的 Gmail message ID
- **THEN** 系統 SHALL 呼叫 Gmail API `users.messages.get`（format=full）
- **AND** 回傳包含 subject 與純文字 body 的物件

#### Scenario: 解析 MIME multipart body
- **WHEN** 信件為 multipart 格式（text/plain + text/html）
- **THEN** 系統 SHALL 優先提取 `text/plain` 部分
- **AND** 若無 text/plain 則 fallback 到 text/html 去除 HTML tags

#### Scenario: token 過期自動更新
- **WHEN** `token.json` 的 access token 已過期
- **THEN** 系統 SHALL 使用 refresh token 自動換新 access token
- **AND** 將更新後的 token 寫回 `token.json`

#### Scenario: 讀取失敗處理
- **WHEN** Gmail API 回傳錯誤（404 / 403 / 網路錯誤）
- **THEN** 系統 SHALL 記錄錯誤 log 並終止本次診斷流程
- **AND** 不重試（避免重複副作用）
