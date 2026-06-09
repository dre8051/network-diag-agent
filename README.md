# network-diag-agent

國際連線障礙自動診斷系統。用戶寄特定格式 Gmail，自動觸發 Globalping 測試 + fabric AI 分析，產出診斷報告並回信。

## 架構

```
用戶寄信 → Gmail Pub/Sub → FastAPI Webhook → Globalping API → fabric AI → 報告 + 回信
```

## 環境需求

- Python 3.12+（透過 `uv` 管理）
- [fabric CLI](https://github.com/danielmiessler/fabric)（AI 分析）
- [ngrok](https://ngrok.com/)（或固定 IP）— 讓 Pub/Sub 能打到 localhost
- Google Cloud 帳號（Gmail API + Pub/Sub）

## 安裝

```bash
# 1. clone
git clone https://github.com/dre8051/network-diag-agent
cd network-diag-agent

# 2. 建立 venv（使用 uv）
uv venv
source .venv/bin/activate

# 3. 安裝依賴
uv pip install -r requirements.txt

# 4. 複製並填寫 .env
cp .env.example .env
# 編輯 .env，填入 PASSPHRASE、GMAIL_ADDRESS 等

# 5. 安裝 fabric pattern
bash setup_fabric_pattern.sh

# 6. Gmail OAuth2 授權（需 credentials.json）
python gmail_auth.py

# 7. 設定 Gmail Watch
python gmail_watch.py
```

## 啟動

```bash
# 先啟動 ngrok
ngrok http 8000

# 再啟動服務
source .venv/bin/activate
python main_server.py
```

## 本地測試（不需 Gmail）

```bash
# 啟動服務後，用 test_trigger.py 直接觸發診斷
source .venv/bin/activate
python test_trigger.py --target 8.8.8.8 --pass dragon2024
```

## 檔案說明

| 檔案 | 說明 |
|---|---|
| `main_server.py` | FastAPI 主服務（Pub/Sub webhook） |
| `gmail_auth.py` | 初次 OAuth2 授權，產生 token.json |
| `gmail_watch.py` | 訂閱 Gmail 收信事件（7 天更新一次） |
| `gmail_client.py` | 讀信 / 回信工具 |
| `mail_validator.py` | 主旨格式 + 通關密碼驗證 |
| `globalping_client.py` | 呼叫 Globalping API（ping/traceroute/dns） |
| `fabric_runner.py` | 呼叫 fabric CLI 進行 AI 分析 |
| `report_formatter.py` | 格式化報告、儲存檔案 |
| `test_trigger.py` | 本地測試工具 |
| `setup_fabric_pattern.sh` | 安裝 fabric network_analysis pattern |

## 設定 cron（Gmail Watch 每 6 天更新）

```bash
# crontab -e
0 9 */6 * * cd /home/dre8051/network-diag-agent && source .venv/bin/activate && python gmail_watch.py >> logs/watch.log 2>&1
```

## 測試

```bash
source .venv/bin/activate
python -m pytest tests/ -v
```
