## Why

用戶回報國際連線問題時，工程師需手動執行 ping/traceroute/DNS 等測試、彙整結果、再撰寫分析報告，流程耗時且容易遺漏關鍵資訊。本系統透過 Gmail 觸發、Globalping 分散式測試節點與 fabric AI 分析，將整個診斷流程自動化，縮短從回報到取得報告的時間至 2 分鐘以內。

## What Changes

- **新增** Gmail Pub/Sub webhook 接收器：接收 Gmail push notification，解碼並讀取信件
- **新增** 信件格式驗證：主旨須符合 `[網路障礙回報] {PASSPHRASE}`，body 須含 `IP:` / `PASS:` 欄位
- **新增** 雙重通關密碼驗證：主旨與 body 中的 PASS 必須同時符合 `.env` 設定
- **新增** Globalping API 整合：從台灣節點對目標 IP 執行 ping / traceroute / DNS 測試
- **新增** fabric CLI 整合：將測試結果 pipe 進 `network_analysis` pattern，產出雙語報告
- **新增** 報告雙軌輸出：用戶版（非技術語言）+ 工程師版（技術語言），分別儲存並可選擇回信

## Capabilities

### New Capabilities

- `pubsub-webhook`: 接收 Google Cloud Pub/Sub push 通知，decode base64 message，提取 Gmail message ID
- `gmail-reader`: 透過 Gmail API (OAuth2) 讀取完整信件，解析主旨與 body 內容
- `mail-validator`: 驗證信件主旨格式與雙重通關密碼（主旨 + body PASS 欄位）
- `globalping-runner`: 呼叫 Globalping REST API，從台灣節點執行 ping / traceroute / DNS，回傳結構化結果
- `fabric-analyzer`: 將測試結果整理為純文字，pipe 進 fabric CLI `network_analysis` pattern，取得 AI 分析報告
- `report-writer`: 解析 AI 報告中的 `---[用戶版]---` 與 `---[工程師版]---` 區塊，儲存為 `report_{ip}_{timestamp}.txt`
- `gmail-reply`: 用 Gmail API 回覆原信，附上用戶版報告（由 `REPLY_TO_USER` 環境變數控制）

### Modified Capabilities

<!-- 無 -->

## Impact

- 新增 Python 專案，主要相依：`fastapi`, `uvicorn`, `google-auth`, `google-auth-oauthlib`, `google-api-python-client`, `python-dotenv`, `requests`
- 需要 Google Cloud 專案（啟用 Gmail API + Pub/Sub），及本地安裝 fabric CLI
- 需要 ngrok（或固定 IP + nginx）將本地 8000 port 暴露為公開 HTTPS endpoint
- 敏感資料（OAuth token、PASSPHRASE、API keys）全部存於 `.env`，不進版控
