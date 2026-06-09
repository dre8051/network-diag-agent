## ADDED Requirements

### Requirement: 回覆用戶診斷報告
系統 SHALL 在 `REPLY_TO_USER=true` 時，使用 Gmail API 回覆原信並附上用戶版報告。

#### Scenario: 成功回覆
- **WHEN** `REPLY_TO_USER` 為 `true` 且報告已產出
- **THEN** 系統 SHALL 使用 Gmail API `users.messages.send` 回覆原信
- **AND** 回信主旨為 `Re: {原主旨}`
- **AND** 回信 body 包含用戶版報告全文

#### Scenario: REPLY_TO_USER 關閉
- **WHEN** `REPLY_TO_USER` 為 `false` 或未設定
- **THEN** 系統 SHALL 跳過回信步驟
- **AND** 僅記錄 log `"回信功能已關閉，僅儲存報告"`

#### Scenario: 回信失敗處理
- **WHEN** Gmail API 回傳錯誤
- **THEN** 系統 SHALL 記錄錯誤 log
- **AND** 不重試（報告已儲存為本地檔案，不因回信失敗影響整體流程）
