## 1. 專案初始化

- [ ] 1.1 建立專案目錄結構（`reports/`、`logs/`）
- [ ] 1.2 建立 `.env` 檔（含 PASSPHRASE、SUBJECT_PREFIX、GMAIL_ADDRESS、GLOBALPING_TOKEN、FABRIC_PATTERN、REPLY_TO_USER）
- [ ] 1.3 建立 `.gitignore`（排除 `.env`、`credentials.json`、`token.json`、`reports/`、`__pycache__/`）
- [ ] 1.4 建立 `requirements.txt`（fastapi、uvicorn、google-auth、google-auth-oauthlib、google-auth-httplib2、google-api-python-client、python-dotenv、requests）

## 2. Gmail OAuth2 設定工具

- [ ] 2.1 建立 `gmail_auth.py`：初次執行 OAuth2 授權流程，產生 `token.json`；支援 `--test` 參數驗證 token 有效性
- [ ] 2.2 建立 `gmail_watch.py`：呼叫 Gmail API `users.watch` 訂閱收信事件，設定 Pub/Sub topic；支援每次執行自動 renew

## 3. Gmail Client 模組

- [ ] 3.1 建立 `gmail_client.py`：`get_message(message_id)` — 呼叫 Gmail API 讀取完整信件，處理 MIME multipart，優先取 text/plain
- [ ] 3.2 `gmail_client.py`：`send_reply(message_id, subject, body)` — 使用 Gmail API 回覆原信（`REPLY_TO_USER=true` 時使用）
- [ ] 3.3 `gmail_client.py`：自動 refresh token 邏輯（access token 過期時以 refresh token 換新）

## 4. 信件驗證模組

- [ ] 4.1 建立 `mail_validator.py`：`validate_subject(subject)` — 驗證主旨格式是否符合 `{SUBJECT_PREFIX} {PASSPHRASE}`
- [ ] 4.2 `mail_validator.py`：`parse_body(body)` — 解析 `IP:` 與 `PASS:` 欄位，回傳 dict 或 None
- [ ] 4.3 `mail_validator.py`：`validate_pass(parsed_pass)` — 比對 PASS 與 .env PASSPHRASE
- [ ] 4.4 `mail_validator.py`：`validate_ip(ip_str)` — 驗證 IPv4 / IPv6 格式

## 5. Globalping Client 模組

- [ ] 5.1 建立 `globalping_client.py`：`run_ping(target_ip)` — POST 到 Globalping API，location=TW，等待結果
- [ ] 5.2 `globalping_client.py`：`run_traceroute(target_ip)` — 同上，type=traceroute
- [ ] 5.3 `globalping_client.py`：`run_dns(target_ip)` — 同上，type=dns
- [ ] 5.4 `globalping_client.py`：`poll_result(measurement_id)` — 每 2 秒輪詢直到 status=finished，最多 120 秒
- [ ] 5.5 `globalping_client.py`：`run_all(target_ip)` — 依序執行三項測試（ping / traceroute / dns），回傳彙整結果

## 6. 報告格式化模組

- [ ] 6.1 建立 `report_formatter.py`：`format_summary(results)` — 將 Globalping 結果整理為純文字（含 PING / TRACEROUTE / DNS 三區塊）
- [ ] 6.2 `report_formatter.py`：`parse_ai_report(fabric_output)` — 解析 `---[用戶版]---` 與 `---[工程師版]---` 分隔標記，回傳兩段內容
- [ ] 6.3 `report_formatter.py`：`save_report(ip, content)` — 儲存 `reports/report_{ip}_{timestamp}.txt`，自動建立目錄

## 7. Fabric Runner 模組

- [ ] 7.1 建立 `fabric_runner.py`：`analyze(summary_text)` — 以 subprocess pipe 呼叫 `fabric --pattern {FABRIC_PATTERN}`，回傳輸出；處理 CLI 不存在 / pattern 不存在的 fallback

## 8. FastAPI 主服務

- [ ] 8.1 建立 `main_server.py`：載入 .env、初始化 FastAPI app、設定 logging
- [ ] 8.2 `main_server.py`：`POST /pubsub/push` — decode base64 message data、提取 Gmail message ID、立即回傳 200、以 `BackgroundTasks` 非同步觸發診斷
- [ ] 8.3 `main_server.py`：`async def process_email(message_id)` — 串接完整診斷流程（讀信 → 驗證 → Globalping → fabric → 儲存報告 → 回信）
- [ ] 8.4 `main_server.py`：重複訊息去重（以 message_id 為 key，60 秒 TTL 的 in-memory set）
- [ ] 8.5 `main_server.py`：`GET /health` — 健康檢查端點

## 9. 手動測試工具

- [ ] 9.1 建立 `test_trigger.py`：模擬 Pub/Sub push，直接呼叫 `POST /pubsub/push`（支援 `--target IP --pass PASSPHRASE` 參數）

## 10. fabric Pattern 安裝

- [ ] 10.1 建立 `setup_fabric_pattern.sh`：自動建立 `~/.config/fabric/patterns/network_analysis/system.md`（含 spec 中定義的完整 prompt）

## 11. 驗證

- [ ] 11.1 確認 `echo "test" | fabric --pattern network_analysis` 可正常輸出
- [ ] 11.2 確認 Globalping API 可連通：`curl -s "https://api.globalping.io/v1/probes" | python3 -m json.tool | head -20`
- [ ] 11.3 啟動服務 `python3 main_server.py`，以 `test_trigger.py --target 8.8.8.8 --pass {PASSPHRASE}` 驗證本地端對端流程
- [ ] 11.4 驗證錯誤 PASS 觸發（log 顯示「通關密碼驗證失敗，忽略」）
- [ ] 11.5 驗證錯誤主旨觸發（log 顯示「主旨不符格式，忽略」）
- [ ] 11.6 確認 `reports/report_8.8.8.8_*.txt` 檔案生成
