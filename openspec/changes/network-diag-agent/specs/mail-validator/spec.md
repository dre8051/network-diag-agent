## ADDED Requirements

### Requirement: 主旨格式驗證
系統 SHALL 驗證信件主旨必須完全符合 `{SUBJECT_PREFIX} {PASSPHRASE}` 格式。

#### Scenario: 主旨符合格式
- **WHEN** 信件主旨為 `[網路障礙回報] dragon2024`（與 .env 設定一致）
- **THEN** 系統 SHALL 通過主旨驗證，繼續後續流程

#### Scenario: 主旨不符格式
- **WHEN** 信件主旨不以 `{SUBJECT_PREFIX}` 開頭，或 passphrase 部分不符
- **THEN** 系統 SHALL 記錄 log `"主旨不符格式，忽略"` 並終止本次處理
- **AND** 不執行任何診斷或回信

### Requirement: Body 欄位解析與雙重驗證
系統 SHALL 從信件 body 解析 `IP:` 與 `PASS:` 欄位，並驗證 PASS 與 .env 一致。

#### Scenario: 成功解析 IP 與 PASS
- **WHEN** body 包含 `IP: 203.69.xxx.xxx` 與 `PASS: dragon2024` 兩行
- **THEN** 系統 SHALL 提取 IP 與 PASS 值（trim 空白）

#### Scenario: PASS 驗證通過
- **WHEN** 解析到的 PASS 值等於 `.env` 的 `PASSPHRASE`
- **THEN** 系統 SHALL 繼續執行 Globalping 測試

#### Scenario: PASS 驗證失敗
- **WHEN** 解析到的 PASS 值不等於 `.env` 的 `PASSPHRASE`
- **THEN** 系統 SHALL 記錄 log `"通關密碼驗證失敗，忽略"` 並終止處理
- **AND** 不執行任何診斷或回信

#### Scenario: IP 格式驗證
- **WHEN** 解析到的 IP 不符合 IPv4 或 IPv6 格式
- **THEN** 系統 SHALL 記錄 log `"IP 格式無效，忽略"` 並終止處理

#### Scenario: 缺少必要欄位
- **WHEN** body 中缺少 `IP:` 或 `PASS:` 任一欄位
- **THEN** 系統 SHALL 記錄 log 並終止處理
