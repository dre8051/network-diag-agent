## ADDED Requirements

### Requirement: 執行 Globalping 網路測試
系統 SHALL 透過 Globalping REST API 從台灣節點對目標 IP 執行 ping、traceroute、DNS 三項測試，並等待結果完成。

#### Scenario: 發起測試請求
- **WHEN** 提供有效的目標 IP
- **THEN** 系統 SHALL 向 `POST https://api.globalping.io/v1/measurements` 發送請求
- **AND** 設定 `locations: [{country: "TW"}]`，每項測試 `limit: 3`（3 個台灣節點）

#### Scenario: 輪詢等待結果
- **WHEN** 測試請求被接受（回傳 measurement ID）
- **THEN** 系統 SHALL 每 2 秒輪詢 `GET /v1/measurements/{id}` 直到 status 為 `finished`
- **AND** 最多等待 120 秒，超時則記錄錯誤

#### Scenario: 三項測試並行發起
- **WHEN** 開始執行診斷
- **THEN** 系統 SHALL 依序或並行發起 ping / traceroute / DNS 三項測試
- **AND** 等待全部完成後再彙整結果

#### Scenario: 帶 token 請求
- **WHEN** `.env` 的 `GLOBALPING_TOKEN` 非空
- **THEN** 系統 SHALL 在 Authorization header 加入 `Bearer {token}`

#### Scenario: API 錯誤處理
- **WHEN** Globalping API 回傳 4xx/5xx 或網路錯誤
- **THEN** 系統 SHALL 記錄錯誤並在測試結果中標注該項測試失敗
- **AND** 繼續執行其他測試項目（不因單項失敗中止）
