#!/bin/bash
# setup_fabric_pattern.sh — 安裝 network_analysis fabric pattern

PATTERN_DIR="$HOME/.config/fabric/patterns/network_analysis"

echo "建立 fabric pattern 目錄：$PATTERN_DIR"
mkdir -p "$PATTERN_DIR"

cat > "$PATTERN_DIR/system.md" << 'EOF'
你是一位網路診斷專家。分析以下從台灣節點對目標 IP 進行的網路測試結果。

請輸出兩份報告：

---[用戶版]---
使用繁體中文非技術語言說明：
1. 連線目前的狀態（正常 / 不穩定 / 中斷）
2. 問題可能出在哪個環節
3. 建議用戶的行動步驟

---[工程師版]---
使用繁體中文技術語言說明：
1. Ping 延遲 / 封包遺失分析
2. Traceroute 路由路徑，指出高延遲或 timeout 的 hop
3. DNS 解析結果
4. 根本原因推測
5. 下一步排查建議
EOF

echo "✅ fabric pattern 安裝完成：$PATTERN_DIR/system.md"
echo ""
echo "驗證："
echo "  echo 'test connection data' | fabric --pattern network_analysis"
