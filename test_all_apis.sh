#!/bin/bash

# 全面测试所有API接口

BASE_URL="http://localhost:8001"
TOKEN=""

echo "=========================================="
echo "开始测试所有API接口"
echo "=========================================="
echo ""

# 1. 测试登录
echo "1. 测试登录接口..."
LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"123456"}')
echo "响应: $LOGIN_RESPONSE"

TOKEN=$(echo $LOGIN_RESPONSE | grep -o '"accessToken":"[^"]*' | cut -d'"' -f4)
if [ -z "$TOKEN" ]; then
  echo "❌ 登录失败，无法获取token"
  exit 1
fi
echo "✅ 登录成功，Token: ${TOKEN:0:20}..."
echo ""

# 2. 测试获取用户信息
echo "2. 测试获取用户信息接口..."
USERINFO_RESPONSE=$(curl -s -X POST "$BASE_URL/userInfo" \
  -H "Content-Type: application/json" \
  -d "{\"accessToken\":\"$TOKEN\"}")
echo "响应: $USERINFO_RESPONSE"
echo ""

# 3. 测试客户管理API
echo "3. 测试客户管理API..."
echo "  3.1 获取客户列表..."
curl -s "$BASE_URL/api/customers?skip=0&limit=10" | head -c 200
echo ""
echo "  3.2 创建客户..."
CUSTOMER_RESPONSE=$(curl -s -X POST "$BASE_URL/api/customers" \
  -H "Content-Type: application/json" \
  -d '{"name":"测试客户","phone":"13800138000"}')
echo "响应: $CUSTOMER_RESPONSE"
CUSTOMER_ID=$(echo $CUSTOMER_RESPONSE | grep -o '"id":[0-9]*' | head -1 | cut -d':' -f2)
echo ""

# 4. 测试商品管理API
echo "4. 测试商品管理API..."
echo "  4.1 获取商品列表..."
curl -s "$BASE_URL/api/products?skip=0&limit=10" | head -c 200
echo ""
echo "  4.2 创建商品..."
PRODUCT_RESPONSE=$(curl -s -X POST "$BASE_URL/api/products" \
  -H "Content-Type: application/json" \
  -d '{"name":"测试商品","unit":"瓶","price":10.00,"cost_price":5.00,"stock":100,"product_type":"normal","is_active":true}')
echo "响应: $PRODUCT_RESPONSE"
PRODUCT_ID=$(echo $PRODUCT_RESPONSE | grep -o '"id":[0-9]*' | head -1 | cut -d':' -f2)
echo ""

# 5. 测试房间管理API
echo "5. 测试房间管理API..."
echo "  5.1 获取房间列表..."
curl -s "$BASE_URL/api/rooms" | head -c 200
echo ""
echo "  5.2 创建房间..."
ROOM_RESPONSE=$(curl -s -X POST "$BASE_URL/api/rooms" \
  -H "Content-Type: application/json" \
  -d '{"name":"测试房间"}')
echo "响应: $ROOM_RESPONSE"
ROOM_ID=$(echo $ROOM_RESPONSE | grep -o '"id":[0-9]*' | head -1 | cut -d':' -f2)
echo ""

# 6. 测试统计API
echo "6. 测试统计API..."
echo "  6.1 每日统计..."
curl -s "$BASE_URL/api/statistics/daily?date=2025-12-06" | head -c 200
echo ""
echo "  6.2 客户排行..."
curl -s "$BASE_URL/api/statistics/customer-ranking?limit=10" | head -c 200
echo ""
echo "  6.3 房间使用率..."
curl -s "$BASE_URL/api/statistics/room-usage" | head -c 200
echo ""

# 7. 测试导出API
echo "7. 测试导出API..."
echo "  7.1 导出客户数据..."
curl -s "$BASE_URL/api/export/customers" | head -c 100
echo ""

echo "=========================================="
echo "API测试完成"
echo "=========================================="

















