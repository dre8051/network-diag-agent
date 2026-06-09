## ADDED Requirements

### Requirement: 解析並儲存雙軌報告
系統 SHALL 從 fabric 輸出解析用戶版與工程師版報告，並儲存為本地檔案。

#### Scenario: 成功解析雙軌報告
- **WHEN** fabric 輸出包含 `---[用戶版]---` 與 `---[工程師版]---` 分隔標記
- **THEN** 系統 SHALL 分別提取兩段報告內容

#### Scenario: 儲存報告檔案
- **WHEN** 報告解析完成
- **THEN** 系統 SHALL 將完整報告（含兩段）儲存為 `reports/report_{ip}_{timestamp}.txt`
- **AND** timestamp 格式為 `%Y%m%d_%H%M%S`
- **AND** 若 `reports/` 目錄不存在則自動建立

#### Scenario: 解析失敗 fallback
- **WHEN** fabric 輸出不包含預期的分隔標記
- **THEN** 系統 SHALL 將整個輸出視為工程師版儲存
- **AND** 用戶版標注為「AI 報告格式解析失敗，請查看原始輸出」
