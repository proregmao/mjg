#!/bin/bash

# 麻将馆记账系统启动脚本
# 功能：启动后端和前端，检查端口占用，自动修复常见错误

# 不设置 set -e，以便更好地处理错误和自动修复

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置
BACKEND_PORT=8001
FRONTEND_PORT=8091
BACKEND_DIR="/data/mjg/backend"
FRONTEND_DIR="/data/mjg/vue3-admin-better"
BACKEND_LOG="/tmp/mjg_backend.log"
FRONTEND_LOG="/tmp/mjg_frontend.log"
MAX_WAIT_TIME=30  # 最大等待启动时间（秒）

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查端口是否被占用
check_port() {
    local port=$1
    
    # 方法1: 使用 lsof
    if command -v lsof &> /dev/null; then
        if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
            return 0  # 端口被占用
        fi
    fi
    
    # 方法2: 使用 netstat
    if command -v netstat &> /dev/null; then
        if netstat -tlnp 2>/dev/null | grep -q ":$port "; then
            return 0  # 端口被占用
        fi
    fi
    
    # 方法3: 使用 ss
    if command -v ss &> /dev/null; then
        if ss -tlnp 2>/dev/null | grep -q ":$port "; then
            return 0  # 端口被占用
        fi
    fi
    
    # 方法4: 尝试连接
    if timeout 1 bash -c "echo > /dev/tcp/localhost/$port" 2>/dev/null; then
        return 0  # 端口被占用
    fi
    
    return 1  # 端口空闲
}

# 杀掉占用端口的进程
kill_port() {
    local port=$1
    log_warning "端口 $port 被占用，正在清理..."
    
    local pids=""
    
    # 方法1: 使用 lsof
    if command -v lsof &> /dev/null; then
        pids=$(lsof -ti :$port 2>/dev/null)
    fi
    
    # 方法2: 使用 netstat
    if [ -z "$pids" ] && command -v netstat &> /dev/null; then
        pids=$(netstat -tlnp 2>/dev/null | grep ":$port " | awk '{print $7}' | cut -d'/' -f1 | grep -E '^[0-9]+$' | sort -u)
    fi
    
    # 方法3: 使用 ss
    if [ -z "$pids" ] && command -v ss &> /dev/null; then
        pids=$(ss -tlnp 2>/dev/null | grep ":$port " | grep -oP 'pid=\K[0-9]+' | sort -u)
    fi
    
    # 方法4: 使用 fuser
    if [ -z "$pids" ] && command -v fuser &> /dev/null; then
        pids=$(fuser $port/tcp 2>/dev/null | grep -oE '[0-9]+' | sort -u)
    fi
    
    if [ -z "$pids" ]; then
        log_warning "无法找到占用端口 $port 的进程"
        # 使用 fuser 强制杀掉（更安全，只杀占用特定端口的进程）
        if command -v fuser &> /dev/null; then
            fuser -k $port/tcp 2>/dev/null || true
        fi
        sleep 2
        if check_port $port; then
            log_error "无法清理端口 $port，请手动处理: lsof -i :$port"
            return 1
        else
            log_success "端口 $port 已清理"
            return 0
        fi
    fi
    
    for pid in $pids; do
        if [ ! -z "$pid" ] && [ "$pid" != "-" ] && [ "$pid" -gt 0 ] 2>/dev/null; then
            log_info "正在杀掉进程 $pid (端口 $port)"
            kill -9 $pid 2>/dev/null || true
            sleep 1
        fi
    done
    
    # 再次检查
    sleep 2
    if check_port $port; then
        log_error "无法清理端口 $port，请手动处理"
        return 1
    else
        log_success "端口 $port 已清理"
        return 0
    fi
}

# 检查并安装后端依赖
check_backend_deps() {
    log_info "检查后端依赖..."
    
    if [ ! -d "$BACKEND_DIR/venv" ]; then
        log_warning "虚拟环境不存在，正在创建..."
        cd "$BACKEND_DIR"
        python3 -m venv venv
        log_success "虚拟环境创建完成"
    fi
    
    # 激活虚拟环境并检查依赖
    source "$BACKEND_DIR/venv/bin/activate"
    
    if [ ! -f "$BACKEND_DIR/venv/bin/uvicorn" ]; then
        log_warning "后端依赖未安装，正在安装..."
        pip install -q --upgrade pip
        pip install -q -r "$BACKEND_DIR/requirements.txt"
        log_success "后端依赖安装完成"
    fi
}

# 检查并安装前端依赖
check_frontend_deps() {
    log_info "检查前端依赖..."
    
    cd "$FRONTEND_DIR"
    
    # 检查 @rspack/binding 是否存在
    local rspack_binding_exists=false
    if [ -d "node_modules/@rspack/binding" ] || [ -L "node_modules/@rspack/binding" ]; then
        rspack_binding_exists=true
    fi
    
    # 检查版本匹配（@rspack/core 和 @rspack/binding 应该版本一致）
    local version_match=true
    if [ "$rspack_binding_exists" = true ] && [ -f "package.json" ]; then
        local core_version=$(grep -oP '"@rspack/core":\s*"\^?\K[0-9.]+' package.json 2>/dev/null || echo "")
        local binding_version=$(grep -oP '"@rspack/binding":\s*"\^?\K[0-9.]+' package.json 2>/dev/null || echo "")
        if [ ! -z "$core_version" ] && [ ! -z "$binding_version" ] && [ "$core_version" != "$binding_version" ]; then
            log_warning "检测到 @rspack 版本不匹配 (core: $core_version, binding: $binding_version)"
            version_match=false
        fi
    fi
    
    if [ ! -d "node_modules" ] || [ "$rspack_binding_exists" = false ] || [ "$version_match" = false ]; then
        if [ "$version_match" = false ]; then
            log_warning "修复 @rspack 版本不匹配问题..."
            if command -v pnpm &> /dev/null; then
                local core_version=$(grep -oP '"@rspack/core":\s*"\^?\K[0-9.]+' package.json 2>/dev/null || echo "1.5.8")
                pnpm add -D "@rspack/binding@$core_version" 2>&1 | tail -5
            fi
        fi
        
        log_warning "前端依赖未安装或 @rspack/binding 缺失，正在安装..."
        if command -v pnpm &> /dev/null; then
            pnpm install
            # 允许构建脚本（可能需要）
            echo "" | pnpm approve-builds 2>/dev/null || true
        elif command -v npm &> /dev/null; then
            npm install
        else
            log_error "未找到 npm 或 pnpm，请先安装 Node.js"
            exit 1
        fi
        
        # 再次检查 @rspack/binding
        if [ ! -d "node_modules/@rspack/binding" ] && [ ! -L "node_modules/@rspack/binding" ]; then
            log_warning "@rspack/binding 仍未安装，尝试单独安装..."
            if command -v pnpm &> /dev/null; then
                local core_version=$(grep -oP '"@rspack/core":\s*"\^?\K[0-9.]+' package.json 2>/dev/null || echo "1.5.8")
                pnpm add -D "@rspack/binding@$core_version" || true
            else
                npm install --save-dev @rspack/binding || true
            fi
        fi
        
        log_success "前端依赖安装完成"
    fi
}

# 检查数据库
check_database() {
    log_info "检查数据库..."
    
    if [ ! -f "$BACKEND_DIR/database.db" ]; then
        log_warning "数据库不存在，正在初始化..."
        cd "$BACKEND_DIR"
        source venv/bin/activate
        python -c "from app.db.init_db import init_db; init_db()" 2>/dev/null || {
            log_warning "数据库初始化失败，将在首次启动时自动创建"
        }
    fi
}

# 启动后端
start_backend() {
    log_info "启动后端服务 (端口 $BACKEND_PORT)..."
    
    # 检查端口
    if check_port $BACKEND_PORT; then
        kill_port $BACKEND_PORT || exit 1
    fi
    
    cd "$BACKEND_DIR"
    source venv/bin/activate
    
    # 启动后端（后台运行）
    nohup uvicorn app.main:app --host 0.0.0.0 --port $BACKEND_PORT --reload > "$BACKEND_LOG" 2>&1 &
    BACKEND_PID=$!
    echo $BACKEND_PID > /tmp/mjg_backend.pid
    
    log_info "后端进程 ID: $BACKEND_PID"
    
    # 等待后端启动
    local wait_time=0
    while [ $wait_time -lt $MAX_WAIT_TIME ]; do
        sleep 1
        wait_time=$((wait_time + 1))
        
        if check_port $BACKEND_PORT; then
            # 检查是否真的启动成功（能访问API）
            if curl -s http://localhost:$BACKEND_PORT/docs > /dev/null 2>&1; then
                log_success "后端启动成功！"
                return 0
            fi
        fi
        
        # 检查进程是否还在运行
        if ! kill -0 $BACKEND_PID 2>/dev/null; then
            log_error "后端进程异常退出"
            log_error "错误日志："
            tail -20 "$BACKEND_LOG"
            
            # 尝试自动修复常见错误
            fix_backend_errors
            return 1
        fi
    done
    
    log_error "后端启动超时"
    log_error "日志："
    tail -20 "$BACKEND_LOG"
    return 1
}

# 修复后端常见错误
fix_backend_errors() {
    log_info "尝试自动修复后端错误..."
    
    cd "$BACKEND_DIR"
    source venv/bin/activate
    
    # 检查是否是依赖问题
    if grep -q "ModuleNotFoundError\|ImportError" "$BACKEND_LOG" 2>/dev/null; then
        log_warning "检测到依赖问题，重新安装依赖..."
        pip install -q --upgrade pip
        pip install -q -r requirements.txt
        log_success "依赖重新安装完成，请重新运行启动脚本"
    fi
    
    # 检查是否是数据库问题
    if grep -q "database\|sqlite" "$BACKEND_LOG" 2>/dev/null; then
        log_warning "检测到数据库问题，尝试初始化数据库..."
        python -c "from app.db.init_db import init_db; init_db()" 2>/dev/null || true
    fi
    
    # 检查是否是端口问题
    if grep -q "address already in use\|port.*in use" "$BACKEND_LOG" 2>/dev/null; then
        log_warning "检测到端口占用问题，尝试清理端口..."
        kill_port $BACKEND_PORT || true
    fi
}

# 启动前端
start_frontend() {
    log_info "启动前端服务 (端口 $FRONTEND_PORT)..."
    
    # 检查端口
    if check_port $FRONTEND_PORT; then
        kill_port $FRONTEND_PORT || exit 1
    fi
    
    cd "$FRONTEND_DIR"
    
    # 检查是否有 rspack 命令
    local serve_cmd=""
    if command -v pnpm &> /dev/null; then
        serve_cmd="pnpm run serve:rspack"
    elif command -v npm &> /dev/null; then
        serve_cmd="npm run serve:rspack"
    else
        log_error "未找到 npm 或 pnpm"
        exit 1
    fi
    
    # 启动前端（后台运行）
    nohup $serve_cmd > "$FRONTEND_LOG" 2>&1 &
    FRONTEND_PID=$!
    echo $FRONTEND_PID > /tmp/mjg_frontend.pid
    
    log_info "前端进程 ID: $FRONTEND_PID"
    
    # 等待前端启动
    local wait_time=0
    while [ $wait_time -lt $MAX_WAIT_TIME ]; do
        sleep 2
        wait_time=$((wait_time + 2))
        
        if check_port $FRONTEND_PORT; then
            # 检查是否真的启动成功
            if curl -s http://localhost:$FRONTEND_PORT > /dev/null 2>&1; then
                log_success "前端启动成功！"
                return 0
            fi
        fi
        
        # 检查进程是否还在运行
        if ! kill -0 $FRONTEND_PID 2>/dev/null; then
            log_error "前端进程异常退出"
            log_error "错误日志："
            tail -30 "$FRONTEND_LOG"
            
            # 尝试自动修复常见错误
            if fix_frontend_errors; then
                log_info "错误已修复，正在重新启动前端..."
                sleep 2
                # 重新启动前端
                start_frontend
                return $?
            else
                return 1
            fi
        fi
    done
    
    log_error "前端启动超时"
    log_error "日志："
    tail -30 "$FRONTEND_LOG"
    return 1
}

# 修复前端常见错误
fix_frontend_errors() {
    log_info "尝试自动修复前端错误..."
    
    cd "$FRONTEND_DIR"
    
    # 检查是否是 @rspack/binding 缺失问题
    if grep -q "@rspack/binding\|Cannot find module.*@rspack" "$FRONTEND_LOG" 2>/dev/null; then
        log_warning "检测到 @rspack/binding 缺失，正在修复..."
        
        # 方法1: 允许构建脚本（pnpm 可能需要）
        if command -v pnpm &> /dev/null; then
            log_info "允许构建脚本..."
            pnpm approve-builds 2>/dev/null || true
        fi
        
        # 方法2: 确保 @rspack/binding 在 package.json 中
        if ! grep -q "@rspack/binding" "$FRONTEND_DIR/package.json" 2>/dev/null; then
            log_info "添加 @rspack/binding 到 package.json..."
            if command -v pnpm &> /dev/null; then
                pnpm add -D @rspack/binding@1.5.8 2>&1 | tail -5
            else
                npm install --save-dev @rspack/binding@1.5.8 2>&1 | tail -5
            fi
        fi
        
        # 方法3: 重新安装所有依赖
        log_info "重新安装所有依赖..."
        if command -v pnpm &> /dev/null; then
            # 不删除 node_modules，只重新安装
            pnpm install
            pnpm approve-builds 2>/dev/null || true
        else
            npm install
        fi
        
        # 方法4: 如果还是不行，完全重新安装
        if [ ! -d "$FRONTEND_DIR/node_modules/@rspack/binding" ]; then
            log_warning "完全重新安装依赖..."
            if command -v pnpm &> /dev/null; then
                rm -rf node_modules .pnpm-store
                pnpm install
                pnpm approve-builds 2>/dev/null || true
            else
                rm -rf node_modules
                npm install
            fi
        fi
        
        log_success "依赖修复完成"
        return 0
    fi
    
    # 检查是否是依赖问题
    if grep -q "Cannot find module\|Module not found" "$FRONTEND_LOG" 2>/dev/null; then
        log_warning "检测到依赖问题，重新安装依赖..."
        if command -v pnpm &> /dev/null; then
            rm -rf node_modules
            pnpm install
            pnpm approve-builds 2>/dev/null || true
        else
            rm -rf node_modules
            npm install
        fi
        log_success "依赖重新安装完成"
        return 0
    fi
    
    # 检查是否是端口问题
    if grep -q "port.*already in use\|EADDRINUSE" "$FRONTEND_LOG" 2>/dev/null; then
        log_warning "检测到端口占用问题，尝试清理端口..."
        kill_port $FRONTEND_PORT || true
        return 0
    fi
    
    # 检查是否是构建工具问题
    if grep -q "rspack\|webpack" "$FRONTEND_LOG" 2>/dev/null; then
        log_warning "检测到构建工具问题，重新安装依赖..."
        if command -v pnpm &> /dev/null; then
            rm -rf node_modules
            pnpm install
            pnpm approve-builds 2>/dev/null || true
        else
            rm -rf node_modules
            npm install
        fi
        return 0
    fi
    
    return 1
}

# 安全地停止特定进程（通过进程名和端口）
safe_kill_process() {
    local port=$1
    local process_name=$2
    
    # 只杀掉匹配进程名且占用指定端口的进程
    if command -v lsof &> /dev/null; then
        local pids=$(lsof -ti :$port 2>/dev/null)
        for pid in $pids; do
            local cmdline=$(ps -p $pid -o comm= 2>/dev/null)
            if [[ "$cmdline" == *"$process_name"* ]] || [[ "$cmdline" == *"node"* ]] || [[ "$cmdline" == *"uvicorn"* ]] || [[ "$cmdline" == *"python"* ]]; then
                log_info "停止进程 $pid ($cmdline) 端口 $port"
                kill $pid 2>/dev/null || true
                sleep 1
            fi
        done
    fi
}

# 停止服务
stop_services() {
    log_info "停止服务..."
    
    # 停止后端 - 仅通过PID文件
    if [ -f /tmp/mjg_backend.pid ]; then
        BACKEND_PID=$(cat /tmp/mjg_backend.pid)
        if kill -0 $BACKEND_PID 2>/dev/null; then
            log_info "停止后端进程 $BACKEND_PID"
            kill $BACKEND_PID 2>/dev/null || true
            sleep 2
        fi
        rm -f /tmp/mjg_backend.pid
    fi
    
    # 停止前端 - 仅通过PID文件
    if [ -f /tmp/mjg_frontend.pid ]; then
        FRONTEND_PID=$(cat /tmp/mjg_frontend.pid)
        if kill -0 $FRONTEND_PID 2>/dev/null; then
            log_info "停止前端进程 $FRONTEND_PID"
            kill $FRONTEND_PID 2>/dev/null || true
            sleep 2
        fi
        rm -f /tmp/mjg_frontend.pid
    fi
    
    # 安全清理端口 - 只杀掉 uvicorn/python 和 node 进程
    safe_kill_process $BACKEND_PORT "uvicorn"
    safe_kill_process $FRONTEND_PORT "node"
    
    log_success "服务已停止"
}

# 显示服务状态
show_status() {
    echo ""
    log_info "========== 服务状态 =========="
    
    # 后端状态
    if check_port $BACKEND_PORT; then
        log_success "后端服务运行中 (端口 $BACKEND_PORT)"
        echo "  API文档: http://localhost:$BACKEND_PORT/docs"
        echo "  API地址: http://localhost:$BACKEND_PORT"
    else
        log_error "后端服务未运行"
    fi
    
    # 前端状态
    if check_port $FRONTEND_PORT; then
        log_success "前端服务运行中 (端口 $FRONTEND_PORT)"
        echo "  访问地址: http://localhost:$FRONTEND_PORT"
    else
        log_error "前端服务未运行"
    fi
    
    echo ""
}

# 主函数
main() {
    echo ""
    log_info "=========================================="
    log_info "  麻将馆记账系统启动脚本"
    log_info "=========================================="
    echo ""
    
    # 检查参数
    case "${1:-start}" in
        start)
            # 检查依赖
            check_backend_deps
            check_frontend_deps
            check_database
            
            # 启动服务
            start_backend && start_frontend
            
            if [ $? -eq 0 ]; then
                show_status
                log_success "所有服务启动成功！"
                echo ""
                log_info "查看日志："
                echo "  后端日志: tail -f $BACKEND_LOG"
                echo "  前端日志: tail -f $FRONTEND_LOG"
                echo ""
                log_info "停止服务: $0 stop"
            else
                log_error "服务启动失败，请检查日志"
                exit 1
            fi
            ;;
        stop)
            stop_services
            ;;
        restart)
            stop_services
            sleep 3
            
            # 直接在当前进程中启动，不递归调用脚本
            # 检查依赖
            check_backend_deps
            check_frontend_deps
            check_database
            
            # 启动服务
            start_backend && start_frontend
            
            if [ $? -eq 0 ]; then
                show_status
                log_success "所有服务重启成功！"
                echo ""
                log_info "查看日志："
                echo "  后端日志: tail -f $BACKEND_LOG"
                echo "  前端日志: tail -f $FRONTEND_LOG"
            else
                log_error "服务重启失败，请检查日志"
                exit 1
            fi
            ;;
        status)
            show_status
            ;;
        *)
            echo "用法: $0 {start|stop|restart|status}"
            exit 1
            ;;
    esac
}

# 运行主函数
main "$@"

