## Context

目前無現有系統；本系統為全新建置。設計目標是在本地機器上運行，透過 Google Cloud Pub/Sub 接收 Gmail push notification，自動執行國際連線診斷並產出 AI 分析報告。

核心限制：
- 服務執行於本地（非雲端），需 ngrok 或固定 IP 提供公開 HTTPS endpoint
- Gmail Watch 有效期 7 天，需 cron 自動更新
- Pub/Sub 要求 webhook 在 60 秒內回傳 200，長時間診斷必須非同步

## Goals / Non-Goals

**Goals:**
- 全自動化：從收信到產出報告零人工介入
- 安全性：雙重通關密碼驗證，防止未授權觸發
- 可讀性：雙軌報告（用戶版 + 工程師版）
- 可擴充：模組化設計，各元件可獨立替換

**Non-Goals:**
- 高可用性 / 雲端部署（本版本為本地運行）
- 多用戶 / 多通關密碼管理
- Web UI 或 Dashboard
- 歷史報告查詢介面

## Decisions

### Decision 1: FastAPI + uvicorn 作為 webhook server

**選擇**：FastAPI + uvicorn 非同步架構  
**原因**：Pub/Sub 要求 60 秒內回傳 200；診斷（ping/traceroute）耗時約 30-90 秒。FastAPI 的 `BackgroundTasks` 可立即回傳 200，再非同步執行診斷，避免 Pub/Sub 重複推送。  
**替代方案**：Flask（同步，會超時）、aiohttp（更底層，開發複雜度高）

### Decision 2: Globalping REST API（非 CLI）

**選擇**：直接呼叫 `https://api.globalping.io/v1/measurements` REST API  
**原因**：避免子 process 依賴，錯誤處理更精確，可取得結構化 JSON 結果  
**替代方案**：globalping CLI（需安裝額外 binary，輸出為純文字需 parse）

### Decision 3: fabric CLI 透過 subprocess pipe

**選擇**：`subprocess.run(["fabric", "--pattern", FABRIC_PATTERN], input=summary_text, ...)`  
**原因**：fabric 的設計本就是 CLI pipe 工具；Python SDK 不存在，subprocess 是唯一合理方式  
**替代方案**：直接呼叫 AI API（需自己管理 prompt，失去 fabric pattern 管理優勢）

### Decision 4: 通關密碼雙重驗證

**選擇**：主旨 + body PASS 欄位都必須符合 `.env` 的 `PASSPHRASE`  
**原因**：防止主旨被猜中後直接觸發；body 的 PASS 是第二道確認，同時也確保 IP 欄位格式正確  
**替代方案**：僅驗證主旨（安全性不足）

### Decision 5: 報告儲存格式

**選擇**：`report_{ip}_{timestamp}.txt` 純文字檔，儲存於 `reports/` 目錄  
**原因**：簡單、無額外依賴、易於人工檢視；timestamp 用 `%Y%m%d_%H%M%S` 格式確保唯一性  
**替代方案**：SQLite 資料庫（過度設計）、JSON 格式（可讀性較低）

## Risks / Trade-offs

- **ngrok URL 不固定** → 每次重啟需更新 Pub/Sub subscription；長期建議改用 ngrok 固定網域或自備固定 IP
- **Gmail Watch 7 天過期** → 設 cron job 每 6 天自動 renew；watch 失效期間不會收到通知
- **Globalping 速率限制** → 未認證 250 次/小時；超限後診斷失敗，需申請免費 token
- **fabric pattern 需手動安裝** → `~/.config/fabric/patterns/network_analysis/system.md` 需在部署時建立
- **Pub/Sub 重複推送** → 若處理失敗或網路中斷，Pub/Sub 會重試；需 idempotency 檢查（以 message ID 去重）
