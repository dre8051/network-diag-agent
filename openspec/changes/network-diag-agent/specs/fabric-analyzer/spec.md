## ADDED Requirements

### Requirement: 整理測試結果並呼叫 fabric 分析
系統 SHALL 將 Globalping 測試結果整理為純文字 summary，透過 subprocess pipe 傳入 fabric CLI 取得 AI 分析報告。

#### Scenario: 測試結果整理為純文字
- **WHEN** 取得 ping / traceroute / DNS 三項測試結果
- **THEN** 系統 SHALL 將其格式化為包含以下區塊的純文字：
  - `=== PING 結果 ===`（延遲、封包遺失率、各節點統計）
  - `=== TRACEROUTE 結果 ===`（各 hop IP、延遲、是否 timeout）
  - `=== DNS 解析結果 ===`（解析到的 IP、TTL）

#### Scenario: 呼叫 fabric CLI
- **WHEN** 純文字 summary 準備完成
- **THEN** 系統 SHALL 執行 `fabric --pattern {FABRIC_PATTERN}` 並以 stdin pipe 傳入 summary
- **AND** 等待 fabric 輸出完整報告文字（最多 120 秒）

#### Scenario: fabric 執行失敗
- **WHEN** fabric CLI 不存在、pattern 不存在，或 subprocess 執行失敗
- **THEN** 系統 SHALL 記錄完整錯誤訊息
- **AND** 將原始測試結果（未經 AI 分析）作為報告內容繼續後續流程
