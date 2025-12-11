#!/bin/bash
# API测试脚本

# 从.env文件读取后端端口
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$SCRIPT_DIR/.env" ]; then
    export $(cat "$SCRIPT_DIR/.env" | grep -v '^#' | xargs)
fi
BACKEND_PORT=${BACKEND_PORT:-8087}
BASE_URL="http://localhost:${BACKEND_PORT}"

echo "=========================================="
echo "开始测试麻将馆记账系统API"
echo "=========================================="
echo ""

# 1. 测试健康检查
echo "1. 测试健康检查..."
curl -s "$BASE_URL/health" | python3 -m json.tool
echo ""

# 2. 测试创建客户
echo "2. 测试创建客户..."
CUSTOMER_RESPONSE=$(curl -s -X POST "$BASE_URL/api/customers" \
  -H "Content-Type: application/json" \
  -d '{"name": "张三", "phone": "13800138000"}')
echo "$CUSTOMER_RESPONSE" | python3 -m json.tool
CUSTOMER_ID=$(echo "$CUSTOMER_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")
echo "创建的客户ID: $CUSTOMER_ID"
echo ""

# 3. 测试获取客户列表
echo "3. 测试获取客户列表..."
curl -s "$BASE_URL/api/customers" | python3 -m json.tool
echo ""

# 4. 测试获取客户详情
echo "4. 测试获取客户详情..."
curl -s "$BASE_URL/api/customers/$CUSTOMER_ID" | python3 -m json.tool
echo ""

# 5. 测试创建商品
echo "5. 测试创建商品..."
PRODUCT_RESPONSE=$(curl -s -X POST "$BASE_URL/api/products" \
  -H "Content-Type: application/json" \
  -d '{"name": "矿泉水", "unit": "瓶", "price": 5.0, "cost_price": 2.0, "stock": 100}')
echo "$PRODUCT_RESPONSE" | python3 -m json.tool
PRODUCT_ID=$(echo "$PRODUCT_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")
echo "创建的商品ID: $PRODUCT_ID"
echo ""

# 6. 测试创建餐费商品
echo "6. 测试创建餐费商品..."
MEAL_PRODUCT_RESPONSE=$(curl -s -X POST "$BASE_URL/api/products" \
  -H "Content-Type: application/json" \
  -d '{"name": "午餐", "unit": "份", "price": 20.0, "cost_price": 10.0, "stock": 0, "product_type": "meal"}')
echo "$MEAL_PRODUCT_RESPONSE" | python3 -m json.tool
MEAL_PRODUCT_ID=$(echo "$MEAL_PRODUCT_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")
echo "创建的餐费商品ID: $MEAL_PRODUCT_ID"
echo ""

# 7. 测试创建房间
echo "7. 测试创建房间..."
ROOM_RESPONSE=$(curl -s -X POST "$BASE_URL/api/rooms" \
  -H "Content-Type: application/json" \
  -d '{"name": "101号房间"}')
echo "$ROOM_RESPONSE" | python3 -m json.tool
ROOM_ID=$(echo "$ROOM_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")
echo "创建的房间ID: $ROOM_ID"
echo ""

# 8. 测试开始使用房间
echo "8. 测试开始使用房间..."
SESSION_RESPONSE=$(curl -s -X POST "$BASE_URL/api/rooms/$ROOM_ID/start-session")
echo "$SESSION_RESPONSE" | python3 -m json.tool
SESSION_ID=$(echo "$SESSION_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")
echo "创建的房间使用记录ID: $SESSION_ID"
echo ""

# 9. 测试添加客户到房间
echo "9. 测试添加客户到房间..."
curl -s -X POST "$BASE_URL/api/rooms/sessions/$SESSION_ID/add-customer" \
  -H "Content-Type: application/json" \
  -d "{\"customer_id\": $CUSTOMER_ID}" | python3 -m json.tool
echo ""

# 10. 测试记录借款
echo "10. 测试记录借款..."
curl -s -X POST "$BASE_URL/api/rooms/sessions/$SESSION_ID/loan" \
  -H "Content-Type: application/json" \
  -d "{\"customer_id\": $CUSTOMER_ID, \"amount\": 100.0}" | python3 -m json.tool
echo ""

# 11. 测试记录商品消费
echo "11. 测试记录商品消费..."
curl -s -X POST "$BASE_URL/api/rooms/sessions/$SESSION_ID/product" \
  -H "Content-Type: application/json" \
  -d "{\"product_id\": $PRODUCT_ID, \"customer_id\": $CUSTOMER_ID, \"quantity\": 2}" | python3 -m json.tool
echo ""

# 12. 测试记录餐费
echo "12. 测试记录餐费..."
curl -s -X POST "$BASE_URL/api/rooms/sessions/$SESSION_ID/meal" \
  -H "Content-Type: application/json" \
  -d "{\"product_id\": $MEAL_PRODUCT_ID, \"customer_id\": $CUSTOMER_ID, \"amount\": 20.0, \"description\": \"午餐\"}" | python3 -m json.tool
echo ""

# 13. 测试设置台子费
echo "13. 测试设置台子费..."
curl -s -X PUT "$BASE_URL/api/rooms/sessions/$SESSION_ID/table-fee" \
  -H "Content-Type: application/json" \
  -d '{"table_fee": 50.0}' | python3 -m json.tool
echo ""

# 14. 测试结算房间
echo "14. 测试结算房间..."
curl -s -X POST "$BASE_URL/api/rooms/sessions/$SESSION_ID/settle" | python3 -m json.tool
echo ""

# 15. 测试获取客户借款记录
echo "15. 测试获取客户借款记录..."
curl -s "$BASE_URL/api/customers/$CUSTOMER_ID/loans" | python3 -m json.tool
echo ""

# 16. 测试获取房间使用记录
echo "16. 测试获取房间使用记录..."
curl -s "$BASE_URL/api/rooms/sessions" | python3 -m json.tool
echo ""

echo "=========================================="
echo "API测试完成！"
echo "=========================================="

