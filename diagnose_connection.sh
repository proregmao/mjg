#!/bin/bash
echo "=== 连接诊断脚本 ==="
echo ""
echo "1. 后端服务状态:"
systemctl is-active mjg-backend.service
echo ""
echo "2. 后端端口监听:"
netstat -tlnp 2>/dev/null | grep 8087 || ss -tlnp 2>/dev/null | grep 8087
echo ""
echo "3. 后端健康检查:"
curl -s http://localhost:8087/health
echo ""
echo "4. 后端登录接口:"
curl -s -X POST http://localhost:8087/login -H "Content-Type: application/json" -d '{"username":"test","password":"test"}' | head -1
echo ""
echo "5. OPTIONS预检请求:"
curl -s -X OPTIONS http://localhost:8087/login -H "Origin: http://localhost:88" -H "Access-Control-Request-Method: POST" -w "\nHTTP状态: %{http_code}\n"
echo ""
echo "6. 前端服务状态:"
systemctl is-active mjg-frontend.service
echo ""
echo "7. 前端端口监听:"
netstat -tlnp 2>/dev/null | grep ":88 " || ss -tlnp 2>/dev/null | grep ":88 "
