#!/bin/bash

# 全面测试所有页面功能

BASE_URL="http://localhost:8001"
FRONTEND_URL="http://localhost:8091"

echo "=========================================="
echo "全面测试所有页面功能"
echo "=========================================="
echo ""

# 1. 测试后端API
echo "1. 测试后端API..."
echo "  1.1 健康检查..."
HEALTH=$(curl -s "$BASE_URL/health")
if echo "$HEALTH" | grep -q "ok"; then
  echo "      ✅ 后端服务正常"
else
  echo "      ❌ 后端服务异常"
  exit 1
fi

echo "  1.2 登录接口..."
LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"123456"}')
if echo "$LOGIN_RESPONSE" | grep -q "accessToken"; then
  echo "      ✅ 登录接口正常"
else
  echo "      ❌ 登录接口异常: $LOGIN_RESPONSE"
  exit 1
fi

TOKEN=$(echo $LOGIN_RESPONSE | grep -o '"accessToken":"[^"]*' | cut -d'"' -f4)

echo "  1.3 客户管理API..."
CUSTOMERS=$(curl -s "$BASE_URL/api/customers?skip=0&limit=5")
if echo "$CUSTOMERS" | grep -q "\["; then
  echo "      ✅ 客户列表API正常"
else
  echo "      ❌ 客户列表API异常"
fi

echo "  1.4 商品管理API..."
PRODUCTS=$(curl -s "$BASE_URL/api/products?skip=0&limit=5")
if echo "$PRODUCTS" | grep -q "\["; then
  echo "      ✅ 商品列表API正常"
else
  echo "      ❌ 商品列表API异常"
fi

echo "  1.5 房间管理API..."
ROOMS=$(curl -s "$BASE_URL/api/rooms")
if echo "$ROOMS" | grep -q "\["; then
  echo "      ✅ 房间列表API正常"
else
  echo "      ❌ 房间列表API异常"
fi

echo "  1.6 统计API..."
STATS=$(curl -s "$BASE_URL/api/statistics/daily?date=2025-12-06")
if echo "$STATS" | grep -q "total_revenue"; then
  echo "      ✅ 统计API正常"
else
  echo "      ❌ 统计API异常"
fi

echo ""

# 2. 测试前端页面（检查路由配置）
echo "2. 检查前端路由配置..."
if [ -f "/data/mjg/vue3-admin-better/src/router/index.js" ]; then
  ROUTE_COUNT=$(grep -c "path:" /data/mjg/vue3-admin-better/src/router/index.js || echo "0")
  echo "      ✅ 路由配置文件存在，包含 $ROUTE_COUNT 个路由"
else
  echo "      ❌ 路由配置文件不存在"
fi

echo ""

# 3. 检查页面组件
echo "3. 检查页面组件..."
PAGES=(
  "customer/list.vue"
  "customer/detail.vue"
  "product/list.vue"
  "room/list.vue"
  "room/session.vue"
  "room/history.vue"
  "statistics/daily.vue"
  "statistics/monthly.vue"
  "statistics/customer-ranking.vue"
  "statistics/room-usage.vue"
  "statistics/product-sales.vue"
  "settings/export.vue"
  "settings/backup.vue"
)

MISSING=0
for page in "${PAGES[@]}"; do
  if [ -f "/data/mjg/vue3-admin-better/src/views/$page" ]; then
    echo "      ✅ $page"
  else
    echo "      ❌ $page 缺失"
    MISSING=$((MISSING + 1))
  fi
done

if [ $MISSING -eq 0 ]; then
  echo "      ✅ 所有页面组件都存在"
else
  echo "      ⚠️  有 $MISSING 个页面组件缺失"
fi

echo ""

# 4. 检查API文件
echo "4. 检查API文件..."
API_FILES=(
  "customer.js"
  "product.js"
  "room.js"
  "statistics.js"
  "export.js"
)

MISSING_API=0
for api in "${API_FILES[@]}"; do
  if [ -f "/data/mjg/vue3-admin-better/src/api/$api" ]; then
    echo "      ✅ $api"
  else
    echo "      ❌ $api 缺失"
    MISSING_API=$((MISSING_API + 1))
  fi
done

if [ $MISSING_API -eq 0 ]; then
  echo "      ✅ 所有API文件都存在"
else
  echo "      ⚠️  有 $MISSING_API 个API文件缺失"
fi

echo ""

# 5. 测试前端服务
echo "5. 测试前端服务..."
if curl -s "$FRONTEND_URL" > /dev/null 2>&1; then
  echo "      ✅ 前端服务运行中"
else
  echo "      ⚠️  前端服务未运行或无法访问"
fi

echo ""
echo "=========================================="
echo "测试完成"
echo "=========================================="

















