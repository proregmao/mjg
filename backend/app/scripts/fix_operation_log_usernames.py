"""
修复操作日志中的Base64编码用户名
将Base64编码的用户名解码为实际用户名
"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.db.database import SessionLocal
from app.models.operation_log import OperationLog
import base64
from urllib.parse import unquote


def is_base64_encoded(s):
    """检查字符串是否是Base64编码"""
    if not s or len(s) < 4:
        return False
    # Base64编码的字符串只包含特定字符
    base64_chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/='
    if not all(c in base64_chars for c in s):
        return False
    # 长度应该是4的倍数（或接近）
    if len(s) % 4 != 0 and not s.endswith('='):
        return False
    return True


def decode_username(encoded_username):
    """尝试解码Base64编码的用户名"""
    try:
        # Base64解码
        decoded_bytes = base64.b64decode(encoded_username)
        # 转换为UTF-8字符串
        decoded_str = decoded_bytes.decode("utf-8")
        # URI解码
        decoded_username = unquote(decoded_str)
        # 验证解码后的结果是否有效
        if decoded_username and len(decoded_username) > 0:
            # 检查是否还是Base64编码（双重编码）
            if is_base64_encoded(decoded_username) and decoded_username != encoded_username:
                # 尝试再次解码
                try:
                    double_decoded = base64.b64decode(decoded_username).decode("utf-8")
                    return unquote(double_decoded) if double_decoded else None
                except:
                    return decoded_username
            return decoded_username
    except Exception as e:
        print(f"解码失败: {e}")
        return None
    return None


def fix_usernames():
    """修复操作日志中的Base64编码用户名"""
    db = SessionLocal()
    try:
        # 获取所有操作日志
        logs = db.query(OperationLog).all()
        fixed_count = 0
        
        for log in logs:
            if not log.username:
                continue
            
            # 检查是否是Base64编码的字符串
            if is_base64_encoded(log.username):
                # 尝试解码
                decoded_username = decode_username(log.username)
                if decoded_username and decoded_username != log.username:
                    print(f"修复: {log.username} -> {decoded_username}")
                    log.username = decoded_username
                    fixed_count += 1
                elif not decoded_username:
                    # 解码失败，使用默认值
                    print(f"解码失败，使用默认值: {log.username} -> 未知用户")
                    log.username = "未知用户"
                    fixed_count += 1
        
        if fixed_count > 0:
            db.commit()
            print(f"成功修复 {fixed_count} 条记录")
        else:
            print("没有需要修复的记录")
            
    except Exception as e:
        db.rollback()
        print(f"修复失败: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("开始修复操作日志中的Base64编码用户名...")
    fix_usernames()
    print("修复完成！")









