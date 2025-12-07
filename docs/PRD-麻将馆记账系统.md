# 麻将馆记账系统 - 产品需求文档（PRD）

**文档版本**: v1.0  
**创建时间**: 2025-12-06 13:49:56  
**项目类型**: Web应用（B/S架构）

---

## 📋 目录

1. [项目概述](#项目概述)
2. [功能需求](#功能需求)
3. [数据库设计](#数据库设计)
4. [业务流程](#业务流程)
5. [技术架构](#技术架构)
6. [界面设计](#界面设计)
7. [非功能需求](#非功能需求)

---

## 1. 项目概述

### 1.1 项目背景
为麻将馆开发一套记账管理系统，用于管理客户信息、商品信息、房间使用记录，自动计算房间利润，提高管理效率。

### 1.2 项目目标
- 实现客户信息的增删改查
- 实现商品信息的增删改查和库存管理
- 实现房间使用记录和消费记录
- 自动计算房间利润
- 提供统计报表和数据导出功能

### 1.3 技术栈
- **前端**: Vue3 + Element Plus + Rspack（基于vue3-admin-better）
- **后端**: Python FastAPI
- **数据库**: SQLite

---

## 2. 功能需求

### 2.1 客户管理模块

#### 2.1.1 客户信息管理
- **功能描述**: 管理客户基本信息
- **字段要求**:
  - 姓名（必填）
  - 电话（可选）
  - 欠款余额（自动计算，不允许负数）
  - 存款余额（自动计算）
- **操作功能**:
  - 添加客户
  - 编辑客户（姓名、电话）
  - 查看客户详情
  - **不允许删除客户**（即使没有欠款和记录）

#### 2.1.2 客户借款管理
- **功能描述**: 记录客户向麻将馆的借款
- **业务规则**:
  - 每笔借款必须记录明细
  - 自动更新客户欠款余额
  - 支持关联房间使用记录
- **显示内容**:
  - 借款时间
  - 借款金额
  - 剩余未还金额
  - 状态（正常/已转移/已还清）
  - 关联房间（如有）

#### 2.1.3 客户还款管理
- **功能描述**: 记录客户还款
- **业务规则**:
  - 每笔还款必须记录明细
  - 自动更新客户欠款余额
  - 支持指定还款到具体借款记录，或还总欠款
- **显示内容**:
  - 还款时间
  - 还款金额
  - 关联借款记录（如有）
  - 关联房间（如有）

#### 2.1.4 客户转账（转移款）
- **功能描述**: 实现客户之间的债务转移
- **业务场景**: 甲找麻将馆借3000元，然后甲把3000元借给乙，相当于甲不欠麻将馆，乙欠麻将馆3000元
- **业务规则**:
  - 转出方必须有足够的欠款余额
  - 转移金额不能超过转出方欠款
  - 不能自己转给自己
  - 自动创建转入方的新借款记录
  - 标记转出方的原始借款为"已转移"
  - 自动更新双方余额
- **显示内容**:
  - 转出方、转入方
  - 转移金额
  - 转移时间
  - 转账前后余额变化

#### 2.1.5 客户详情页
- **功能描述**: 查看客户完整信息
- **显示内容**:
  - 基本信息
  - 借款明细列表（支持筛选）
  - 还款明细列表（支持筛选）
  - 转账记录列表
  - 余额变化趋势图（可选）

---

### 2.2 商品管理模块

#### 2.2.1 商品信息管理
- **功能描述**: 管理商品基本信息
- **字段要求**:
  - 名称（必填）
  - 单位（如：瓶、包、份等）
  - 单价（销售价）
  - 成本价（用于利润计算）
  - 库存（整数）
  - 商品类型（普通商品/餐费类型）
  - 是否启用
- **操作功能**:
  - 添加商品
  - 编辑商品
  - 删除商品（软删除）
  - 启用/禁用商品

#### 2.2.2 库存管理
- **功能描述**: 管理商品库存
- **功能要求**:
  - 商品消费时自动减少库存
  - 支持手动调整库存（增加/减少）
  - 库存不足时提示

#### 2.2.3 餐费管理
- **功能描述**: 餐费作为特殊商品类型管理
- **业务规则**:
  - 餐费在商品表中设置，`product_type='meal'`
  - 餐费有成本价，用于利润计算
  - 记录餐费时选择餐费商品并输入金额

---

### 2.3 房间管理模块

#### 2.3.1 房间信息管理
- **功能描述**: 管理房间基本信息
- **字段要求**:
  - 名称（必填）
  - 状态（空闲/使用中/已结算）
- **操作功能**:
  - 添加房间
  - 编辑房间
  - 查看房间使用记录

#### 2.3.2 房间使用（核心功能）
- **功能描述**: 记录房间使用过程中的所有消费
- **使用流程**:
  1. 选择房间（必须是空闲状态）
  2. 添加客户（可多个，支持中途添加/移除）
  3. 记录消费（可多次操作）:
     - 记录借款
     - 记录商品消费
     - 记录餐费
  4. 设置台子费（用户手动输入）
  5. 房间转移（可选，从A房间换到B房间）
  6. 结算房间（一次性结算所有消费）

#### 2.3.3 房间消费记录
- **借款记录**:
  - 选择客户
  - 输入金额
  - 自动更新客户欠款余额
  - 关联房间使用记录
- **商品消费记录**:
  - 选择商品
  - 选择客户（可选）
  - 输入数量
  - 自动检查库存
  - 自动减少库存
  - 记录成本价用于利润计算
- **餐费记录**:
  - 选择餐费商品（product_type='meal'）
  - 选择客户（可选）
  - 输入金额
  - 使用商品表中的成本价计算成本

#### 2.3.4 房间转移
- **功能描述**: 支持房间之间的转移
- **业务规则**:
  - 转移时保留所有人员信息和消费记录
  - 只更新房间ID
  - 原房间自动变为空闲
  - 新房间自动变为使用中
  - 记录转移历史

#### 2.3.5 房间结算
- **功能描述**: 结算房间使用，计算利润
- **业务规则**:
  - 必须一次性结算所有消费（不支持部分结算）
  - 计算利润 = 台子费 - 商品总成本 - 餐费总成本
  - 借款不参与利润计算
  - 更新房间状态为"空闲"
  - 记录结束时间

#### 2.3.6 利润计算
- **计算公式**: 
  ```
  利润 = 台子费 - 商品总成本 - 餐费总成本
  ```
- **说明**:
  - 台子费：用户手动输入
  - 商品总成本 = Σ(商品数量 × 商品成本价)
  - 餐费总成本 = Σ(餐费成本价)
  - 借款不参与利润计算

#### 2.3.7 房间历史记录
- **功能描述**: 查看房间使用历史
- **筛选条件**:
  - 按房间筛选
  - 按时间范围筛选
- **显示内容**:
  - 房间名称
  - 使用时间（开始-结束）
  - 参与客户
  - 台子费
  - 总利润
  - 详细消费记录

---

### 2.4 统计报表模块

#### 2.4.1 每日统计
- **功能描述**: 查看每日收入、支出、利润统计
- **显示内容**:
  - 日期选择器
  - 收入统计（台子费、商品收入、餐费收入）
  - 成本统计（商品成本、餐费成本）
  - 利润统计
  - 房间使用情况

#### 2.4.2 每月统计
- **功能描述**: 查看每月汇总数据
- **显示内容**:
  - 月份选择器
  - 汇总数据（同上）
  - 趋势图
  - 导出Excel功能

#### 2.4.3 客户消费排行
- **功能描述**: 统计客户消费情况
- **排行方式**:
  - 按消费金额排行
  - 按欠款金额排行
- **显示内容**:
  - 客户姓名
  - 消费金额/欠款金额
  - 客户详情链接

#### 2.4.4 房间使用率
- **功能描述**: 统计房间使用情况
- **显示内容**:
  - 房间使用时长统计
  - 房间收入排行
  - 房间利润排行

#### 2.4.5 商品销售统计
- **功能描述**: 统计商品销售情况
- **显示内容**:
  - 商品销售排行
  - 商品利润分析
  - 库存预警

---

### 2.5 系统设置模块

#### 2.5.1 数据导出
- **功能描述**: 导出数据到Excel
- **导出内容**:
  - 客户数据
  - 房间记录
  - 月结清单

#### 2.5.2 数据备份
- **功能描述**: 备份和恢复数据库
- **功能要求**:
  - 手动备份数据库
  - 查看备份列表
  - 恢复数据库

---

## 3. 数据库设计

### 3.1 表结构

#### 3.1.1 客户表（customers）
| 字段名 | 类型 | 说明 | 约束 |
|--------|------|------|------|
| id | INTEGER | 主键 | PRIMARY KEY |
| name | VARCHAR(100) | 姓名 | NOT NULL |
| phone | VARCHAR(20) | 电话 | |
| balance | DECIMAL(10,2) | 当前欠款余额 | DEFAULT 0, NOT NULL |
| deposit | DECIMAL(10,2) | 存款余额 | DEFAULT 0 |
| created_at | DATETIME | 创建时间 | NOT NULL |
| updated_at | DATETIME | 更新时间 | NOT NULL |

#### 3.1.2 商品表（products）
| 字段名 | 类型 | 说明 | 约束 |
|--------|------|------|------|
| id | INTEGER | 主键 | PRIMARY KEY |
| name | VARCHAR(100) | 名称 | NOT NULL |
| unit | VARCHAR(20) | 单位 | |
| price | DECIMAL(10,2) | 单价（销售价） | NOT NULL |
| cost_price | DECIMAL(10,2) | 成本价 | NOT NULL |
| stock | INTEGER | 库存 | DEFAULT 0 |
| is_active | BOOLEAN | 是否启用 | DEFAULT TRUE |
| product_type | VARCHAR(20) | 商品类型 | DEFAULT 'normal' |
| created_at | DATETIME | 创建时间 | NOT NULL |
| updated_at | DATETIME | 更新时间 | NOT NULL |

**商品类型说明**:
- `normal`: 普通商品
- `meal`: 餐费类型

#### 3.1.3 房间表（rooms）
| 字段名 | 类型 | 说明 | 约束 |
|--------|------|------|------|
| id | INTEGER | 主键 | PRIMARY KEY |
| name | VARCHAR(100) | 名称 | NOT NULL |
| status | VARCHAR(20) | 状态 | DEFAULT 'idle' |
| created_at | DATETIME | 创建时间 | NOT NULL |
| updated_at | DATETIME | 更新时间 | NOT NULL |

**状态说明**:
- `idle`: 空闲
- `in_use`: 使用中
- `settled`: 已结算

#### 3.1.4 房间使用记录表（room_sessions）
| 字段名 | 类型 | 说明 | 约束 |
|--------|------|------|------|
| id | INTEGER | 主键 | PRIMARY KEY |
| room_id | INTEGER | 房间ID | FOREIGN KEY |
| start_time | DATETIME | 开始时间 | NOT NULL |
| end_time | DATETIME | 结束时间 | |
| status | VARCHAR(20) | 状态 | DEFAULT 'in_progress' |
| table_fee | DECIMAL(10,2) | 台子费 | DEFAULT 0 |
| total_revenue | DECIMAL(10,2) | 总收入 | DEFAULT 0 |
| total_cost | DECIMAL(10,2) | 总成本 | DEFAULT 0 |
| total_profit | DECIMAL(10,2) | 总利润 | DEFAULT 0 |
| created_at | DATETIME | 创建时间 | NOT NULL |
| updated_at | DATETIME | 更新时间 | NOT NULL |

**状态说明**:
- `in_progress`: 进行中
- `settled`: 已结算

#### 3.1.5 房间客户关联表（room_customers）
| 字段名 | 类型 | 说明 | 约束 |
|--------|------|------|------|
| id | INTEGER | 主键 | PRIMARY KEY |
| session_id | INTEGER | 房间使用记录ID | FOREIGN KEY |
| customer_id | INTEGER | 客户ID | FOREIGN KEY |
| joined_at | DATETIME | 加入时间 | NOT NULL |
| left_at | DATETIME | 离开时间 | |
| created_at | DATETIME | 创建时间 | NOT NULL |

#### 3.1.6 客户借款记录表（customer_loans）
| 字段名 | 类型 | 说明 | 约束 |
|--------|------|------|------|
| id | INTEGER | 主键 | PRIMARY KEY |
| customer_id | INTEGER | 客户ID | FOREIGN KEY |
| amount | DECIMAL(10,2) | 借款金额 | NOT NULL |
| loan_type | VARCHAR(20) | 借款类型 | NOT NULL |
| from_customer_id | INTEGER | 出借方客户ID | FOREIGN KEY, NULL |
| to_customer_id | INTEGER | 借入方客户ID | FOREIGN KEY, NULL |
| transfer_from_id | INTEGER | 转移款关联ID | FOREIGN KEY, NULL |
| status | VARCHAR(20) | 状态 | DEFAULT 'active' |
| remaining_amount | DECIMAL(10,2) | 剩余未还金额 | NOT NULL |
| session_id | INTEGER | 房间使用记录ID | FOREIGN KEY, NULL |
| created_at | DATETIME | 创建时间 | NOT NULL |
| updated_at | DATETIME | 更新时间 | NOT NULL |

**借款类型说明**:
- `from_shop`: 向麻将馆借款
- `between_customers`: 客户间借款

**状态说明**:
- `active`: 正常
- `transferred`: 已转移
- `repaid`: 已还清

#### 3.1.7 客户还款记录表（customer_repayments）
| 字段名 | 类型 | 说明 | 约束 |
|--------|------|------|------|
| id | INTEGER | 主键 | PRIMARY KEY |
| customer_id | INTEGER | 客户ID | FOREIGN KEY |
| loan_id | INTEGER | 借款记录ID | FOREIGN KEY, NULL |
| amount | DECIMAL(10,2) | 还款金额 | NOT NULL |
| session_id | INTEGER | 房间使用记录ID | FOREIGN KEY, NULL |
| created_at | DATETIME | 创建时间 | NOT NULL |

#### 3.1.8 转账记录表（transfers）
| 字段名 | 类型 | 说明 | 约束 |
|--------|------|------|------|
| id | INTEGER | 主键 | PRIMARY KEY |
| from_customer_id | INTEGER | 转出方客户ID | FOREIGN KEY |
| to_customer_id | INTEGER | 转入方客户ID | FOREIGN KEY |
| amount | DECIMAL(10,2) | 转移金额 | NOT NULL |
| original_loan_id | INTEGER | 原始借款记录ID | FOREIGN KEY |
| new_loan_id | INTEGER | 新创建的借款记录ID | FOREIGN KEY |
| created_at | DATETIME | 创建时间 | NOT NULL |

#### 3.1.9 商品消费记录表（product_consumptions）
| 字段名 | 类型 | 说明 | 约束 |
|--------|------|------|------|
| id | INTEGER | 主键 | PRIMARY KEY |
| session_id | INTEGER | 房间使用记录ID | FOREIGN KEY |
| customer_id | INTEGER | 客户ID | FOREIGN KEY, NULL |
| product_id | INTEGER | 商品ID | FOREIGN KEY |
| quantity | INTEGER | 数量 | NOT NULL |
| unit_price | DECIMAL(10,2) | 单价 | NOT NULL |
| total_price | DECIMAL(10,2) | 总价 | NOT NULL |
| cost_price | DECIMAL(10,2) | 成本价 | NOT NULL |
| total_cost | DECIMAL(10,2) | 总成本 | NOT NULL |
| created_at | DATETIME | 创建时间 | NOT NULL |

#### 3.1.10 餐费记录表（meal_records）
| 字段名 | 类型 | 说明 | 约束 |
|--------|------|------|------|
| id | INTEGER | 主键 | PRIMARY KEY |
| session_id | INTEGER | 房间使用记录ID | FOREIGN KEY |
| customer_id | INTEGER | 客户ID | FOREIGN KEY, NULL |
| product_id | INTEGER | 餐费商品ID | FOREIGN KEY |
| amount | DECIMAL(10,2) | 餐费金额 | NOT NULL |
| cost_price | DECIMAL(10,2) | 成本价 | NOT NULL |
| description | VARCHAR(255) | 餐费说明 | |
| created_at | DATETIME | 创建时间 | NOT NULL |

#### 3.1.11 房间转移记录表（room_transfers）
| 字段名 | 类型 | 说明 | 约束 |
|--------|------|------|------|
| id | INTEGER | 主键 | PRIMARY KEY |
| session_id | INTEGER | 房间使用记录ID | FOREIGN KEY |
| from_room_id | INTEGER | 原房间ID | FOREIGN KEY |
| to_room_id | INTEGER | 目标房间ID | FOREIGN KEY |
| transferred_at | DATETIME | 转移时间 | NOT NULL |
| transferred_by | VARCHAR(100) | 操作人 | |
| created_at | DATETIME | 创建时间 | NOT NULL |

### 3.2 索引设计
- `customers.name`: 客户姓名索引
- `customers.phone`: 客户电话索引
- `products.name`: 商品名称索引
- `rooms.name`: 房间名称索引
- `room_sessions.room_id`: 房间ID索引
- `room_sessions.status`: 状态索引
- `customer_loans.customer_id`: 客户ID索引
- `customer_loans.status`: 状态索引
- `product_consumptions.session_id`: 房间使用记录ID索引
- `product_consumptions.product_id`: 商品ID索引

---

## 4. 业务流程

### 4.1 房间使用流程

```
1. 选择房间
   ↓
2. 检查房间状态（必须是空闲）
   ↓
3. 创建room_sessions记录（status='in_progress'）
   ↓
4. 更新房间状态为'in_use'
   ↓
5. 添加客户（可多个，支持中途添加/移除）
   ↓
6. 记录消费（可多次操作）
   ├── 记录借款
   ├── 记录商品消费
   └── 记录餐费
   ↓
7. 设置台子费（用户手动输入）
   ↓
8. 房间转移（可选）
   ↓
9. 结算房间
   ├── 计算总利润
   ├── 更新room_sessions状态为'settled'
   ├── 记录结束时间
   └── 更新房间状态为'idle'
```

### 4.2 转移款流程

```
1. 选择转出方（甲）
   ↓
2. 检查转出方欠款余额 >= 转移金额
   ↓
3. 选择转入方（乙，不能是自己）
   ↓
4. 输入转移金额
   ↓
5. 查找转出方的未还清借款记录（按时间排序）
   ↓
6. 创建transfer记录
   ↓
7. 更新转出方的借款记录（status='transferred'）
   ↓
8. 创建转入方的新借款记录（status='active'）
   ↓
9. 更新双方余额
   ├── 转出方 balance -= 转移金额
   └── 转入方 balance += 转移金额
```

### 4.3 利润计算流程

```
1. 获取房间使用记录的所有消费
   ↓
2. 计算商品总成本 = Σ(商品数量 × 商品成本价)
   ↓
3. 计算餐费总成本 = Σ(餐费成本价)
   ↓
4. 计算总利润 = 台子费 - 商品总成本 - 餐费总成本
   ↓
5. 更新room_sessions的利润字段
```

---

## 5. 技术架构

### 5.1 前端架构
- **框架**: Vue 3.x
- **UI组件库**: Element Plus
- **构建工具**: Rspack
- **状态管理**: Vuex
- **路由管理**: Vue Router
- **HTTP请求**: Axios
- **数据可视化**: ECharts
- **Excel导出**: xlsx

### 5.2 后端架构
- **框架**: Python FastAPI
- **ORM**: SQLAlchemy
- **数据验证**: Pydantic
- **数据库**: SQLite
- **API文档**: 自动生成（Swagger）

### 5.3 项目结构

#### 前端结构
```
vue3-admin-better/
├── src/
│   ├── api/              # API接口
│   ├── views/            # 页面组件
│   │   ├── customer/     # 客户管理
│   │   ├── product/      # 商品管理
│   │   ├── room/         # 房间管理
│   │   └── statistics/   # 统计报表
│   ├── components/       # 公共组件
│   ├── store/            # 状态管理
│   └── utils/            # 工具函数
```

#### 后端结构
```
backend/
├── app/
│   ├── models/           # 数据库模型
│   ├── schemas/          # Pydantic模型
│   ├── api/              # API路由
│   ├── services/         # 业务逻辑
│   ├── db/               # 数据库配置
│   └── main.py           # 入口文件
├── database.db           # SQLite数据库
└── requirements.txt      # 依赖文件
```

---

## 6. 界面设计

### 6.1 整体布局
- 采用vue3-admin-better的布局样式
- 左侧导航菜单
- 顶部工具栏
- 主内容区域

### 6.2 主要页面

#### 6.2.1 客户管理页面
- 客户列表（表格形式）
- 搜索和筛选功能
- 添加/编辑客户对话框
- 客户详情页（标签页：基本信息、借款记录、还款记录、转账记录）

#### 6.2.2 商品管理页面
- 商品列表（表格形式）
- 搜索和筛选功能
- 添加/编辑商品对话框
- 库存调整对话框

#### 6.2.3 房间管理页面
- 房间列表（卡片或表格形式，显示状态）
- 房间使用页面（核心功能）:
  - 顶部：房间信息、使用时间、当前状态
  - 客户列表区域
  - 消费记录区域（标签页：借款、商品、餐费）
  - 房间操作区域（转移、设置台子费、结算）
  - 利润预览区域（实时计算）

#### 6.2.4 统计报表页面
- 每日统计（图表+表格）
- 每月统计（图表+表格+导出）
- 客户消费排行（表格）
- 房间使用率（图表）
- 商品销售统计（表格）

---

## 7. 非功能需求

### 7.1 性能要求
- 页面加载时间 < 2秒
- API响应时间 < 500ms
- 支持100+客户数据
- 支持50+房间使用记录

### 7.2 安全要求
- 数据校验（防止负数余额、库存不足等）
- 事务处理（关键操作使用数据库事务）
- 数据备份（支持手动备份）

### 7.3 可用性要求
- 界面友好，操作简单
- 实时反馈（余额、利润实时显示）
- 操作确认（关键操作需要确认）
- 错误提示（友好的错误信息）

### 7.4 兼容性要求
- 支持Chrome、Firefox、Edge等主流浏览器
- 响应式设计，支持PC、平板、手机

---

## 8. 特殊业务规则

1. **客户删除**: 不允许删除客户，即使没有欠款和记录也不允许
2. **房间转移**: 转移后原房间自动变为空闲，新房间自动变为使用中
3. **部分结算**: 不支持部分结算，房间必须一次性结算所有消费
4. **餐费成本**: 餐费作为特殊商品类型，成本价在商品管理中设置
5. **台子费**: 用户手动输入，不自动计算
6. **利润计算**: 利润 = 台子费 - 商品总成本 - 餐费总成本（借款不参与利润计算）
7. **余额计算**: 每次借款/还款/转移后自动更新客户余额
8. **库存管理**: 商品消费时自动减少库存，库存不足时提示

---

## 9. 开发优先级

### 第一阶段（核心功能）
1. 客户管理（增删改查、转账）
2. 商品管理（增删改查、库存）
3. 房间管理（基础功能）
4. 房间使用（记录消费、结算）

### 第二阶段（完善功能）
1. 房间转移
2. 统计报表
3. 数据导出

### 第三阶段（优化功能）
1. 数据备份
2. 操作日志
3. 性能优化

---

**文档结束**

