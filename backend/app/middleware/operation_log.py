"""
操作日志中间件
用于记录所有API操作
"""
import json
import time
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.models.operation_log import OperationLog
from datetime import datetime


class OperationLogMiddleware(BaseHTTPMiddleware):
    """操作日志中间件"""
    
    # 不需要记录日志的路径
    EXCLUDED_PATHS = [
        "/",
        "/health",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/api/operation-logs",  # 操作日志查询本身不记录
    ]
    
    # 模块映射：根据路径判断操作模块
    MODULE_MAP = {
        "/api/customers": "客户管理",
        "/api/products": "商品管理",
        "/api/rooms": "房间管理",
        "/api/statistics": "统计报表",
        "/api/export": "数据导出",
        "/api/backup": "数据备份",
        "/api/users": "用户管理",
        "/api/suppliers": "供货商管理",
        "/api/purchases": "进货管理",
        "/api/other-expenses": "其它支出管理",
        "/api/other-incomes": "其它收入管理",
        "/api/system-configs": "系统配置",
        "/api/payment-statistics": "支付方式统计",
        "/api/category-statistics": "分类统计",
    }
    
    # 操作类型映射：根据HTTP方法和路径判断操作类型
    ACTION_MAP = {
        "GET": "查询",
        "POST": "创建",
        "PUT": "更新",
        "DELETE": "删除",
        "PATCH": "修改",
    }
    
    async def dispatch(self, request: Request, call_next):
        """处理请求并记录日志"""
        start_time = time.time()
        
        # 跳过OPTIONS预检请求（CORS预检请求）
        if request.method == "OPTIONS":
            return await call_next(request)
        
        # 检查是否需要记录日志
        if request.url.path in self.EXCLUDED_PATHS:
            return await call_next(request)
        
        # 获取请求信息
        method = request.method
        path = request.url.path
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent", "")
        
        # 获取用户名（从token或header中）
        username = "未知用户"
        user_id = None
        auth_header = request.headers.get("authorization", "")
        # 尝试从header中获取用户名（前端可能在header中传递）
        username_header = request.headers.get("x-username", "")
        username_encoded = request.headers.get("x-username-encoded", "")
        if username_header:
            # 如果用户名是Base64编码的，需要解码
            if username_encoded == "base64":
                try:
                    import base64
                    from urllib.parse import unquote
                    # Base64解码
                    decoded_bytes = base64.b64decode(username_header)
                    # 转换为UTF-8字符串（因为前端使用TextEncoder编码）
                    decoded_str = decoded_bytes.decode("utf-8")
                    # URI解码
                    decoded_username = unquote(decoded_str)
                    # 验证解码后的用户名是否有效（不是Base64编码的字符串）
                    # 如果解码后的字符串看起来像Base64编码（只包含Base64字符且长度合理），可能是双重编码
                    if decoded_username and len(decoded_username) > 0:
                        # 检查是否看起来像Base64编码的字符串（只包含Base64字符且以=结尾）
                        if not (decoded_username.endswith('=') and len(decoded_username) % 4 == 0 and 
                                all(c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=' for c in decoded_username)):
                            username = decoded_username
                        else:
                            # 可能是双重编码，尝试再次解码
                            try:
                                double_decoded = base64.b64decode(decoded_username).decode("utf-8")
                                username = unquote(double_decoded) if double_decoded else "未知用户"
                            except:
                                username = "未知用户"
                    else:
                        username = "未知用户"
                except Exception as e:
                    # 解码失败，使用默认值而不是原始编码值
                    print(f"解码用户名失败: {e}, 原始值: {username_header}")
                    username = "未知用户"
            else:
                # 检查是否是Base64编码的字符串（可能是历史数据或错误数据）
                # 如果看起来像Base64编码，尝试解码
                if username_header and len(username_header) > 4:
                    # 检查是否看起来像Base64编码
                    is_likely_base64 = (
                        (username_header.endswith('=') and len(username_header) % 4 == 0) or
                        (len(username_header) >= 8 and all(c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=' for c in username_header))
                    )
                    
                    if is_likely_base64:
                        try:
                            import base64
                            from urllib.parse import unquote
                            decoded_bytes = base64.b64decode(username_header)
                            decoded_str = decoded_bytes.decode("utf-8")
                            decoded_username = unquote(decoded_str)
                            # 验证解码后的结果是否有效且不是Base64编码
                            if decoded_username and len(decoded_username) > 0:
                                # 检查解码后的结果是否还是Base64编码
                                if not (decoded_username.endswith('=') and len(decoded_username) % 4 == 0 and
                                        all(c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=' for c in decoded_username)):
                                    username = decoded_username
                                else:
                                    # 双重编码，尝试再次解码
                                    try:
                                        double_decoded = base64.b64decode(decoded_username).decode("utf-8")
                                        username = unquote(double_decoded) if double_decoded else "未知用户"
                                    except:
                                        username = "未知用户"
                            else:
                                username = "未知用户"
                        except Exception as e:
                            # 解码失败，使用默认值而不是原始编码值
                            print(f"自动解码Base64用户名失败: {e}, 原始值: {username_header}")
                            username = "未知用户"
                    else:
                        # 不是Base64编码，直接使用
                        username = username_header
                else:
                    username = username_header
        elif auth_header:
            # 简化处理：从token中提取用户名（实际应该从token解析）
            # 这里可以根据实际认证方式调整
            # 暂时使用token的前几位作为标识
            username = f"用户({auth_header[:10]}...)"
        
        # 获取请求体
        request_data = None
        if method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.body()
                if body:
                    request_data = body.decode("utf-8")[:2000]  # 限制长度
            except:
                pass
        
        # 执行请求
        response = await call_next(request)
        
        # 计算执行时间
        execution_time = int((time.time() - start_time) * 1000)
        
        # 获取响应状态码
        status_code = response.status_code
        
        # 获取响应数据（仅记录关键信息，仅记录错误响应）
        response_data = None
        error_message = None
        if status_code >= 400:
            # 对于错误响应，尝试记录错误信息
            # 注意：由于响应体可能已经被读取，这里只记录状态码
            error_message = f"HTTP {status_code} 错误"
        
        # 判断操作模块
        module = "未知模块"
        for path_prefix, module_name in self.MODULE_MAP.items():
            if path.startswith(path_prefix):
                module = module_name
                break
        
        # 判断操作类型
        action = self.ACTION_MAP.get(method, method)
        # 如果是创建操作，尝试从路径中提取更具体的操作
        if method == "POST":
            if "/start-session" in path:
                action = "开始使用房间"
            elif "/add-customer" in path:
                action = "添加客户到房间"
            elif "/remove-customer" in path:
                action = "移除房间客户"
            elif "/loan" in path:
                action = "记录借款"
            elif "/product" in path:
                action = "记录商品消费"
            elif "/meal" in path:
                action = "记录餐费"
            elif "/settle" in path:
                action = "结算房间"
            elif "/transfer" in path:
                action = "客户转账"
        elif method == "PUT":
            if "/stock" in path:
                action = "调整库存"
            elif "/table-fee" in path:
                action = "设置台子费"
        
        # 记录操作日志
        try:
            db: Session = SessionLocal()
            try:
                log = OperationLog(
                    user_id=user_id,
                    username=username,
                    action=action,
                    module=module,
                    method=method,
                    path=path,
                    ip_address=ip_address,
                    user_agent=user_agent[:500] if user_agent else None,
                    request_data=request_data,
                    response_data=response_data,
                    status_code=status_code,
                    error_message=error_message,
                    execution_time=execution_time
                )
                db.add(log)
                db.commit()
            except Exception as e:
                db.rollback()
                print(f"记录操作日志失败: {e}")
            finally:
                db.close()
        except Exception as e:
            print(f"创建数据库会话失败: {e}")
        
        return response

