[README.md](https://github.com/user-attachments/files/34513635/README.md)
# AI 模拟面试助手

基于需求文档（`AI模拟面试助手-需求文档.md`）、数据库设计（`schema.sql`）与高保真原型（`index.html`）实现的全栈项目。

- **前端**：Vue 3 + JavaScript + Ant Design Vue（PC 端）
- **后端**：Python + FastAPI
- **数据库**：MySQL 8.0（utf8mb4），18 张表与 `schema.sql` 一一对应

## 目录结构

```
├── backend/                 # FastAPI 后端
│   ├── app/
│   │   ├── main.py          # 应用入口（CORS / 路由挂载 / 启动自动建表）
│   │   ├── config.py        # 配置（DB_URL、JWT 密钥、免费配额）
│   │   ├── database.py      # SQLAlchemy 引擎与会话
│   │   ├── models.py        # 18 张表的 ORM 模型
│   │   ├── schemas.py       # Pydantic 请求/响应模型
│   │   ├── security.py      # PBKDF2 密码哈希 + JWT
│   │   ├── deps.py          # 认证 / 会员判定 / 月度配额
│   │   ├── ai_engine.py     # AI 面试官规则引擎（追问 / 判题 / 评分）
│   │   ├── seed.py          # 种子数据（岗位 / 套餐 / 24 道题 / 演示账号）
│   │   ├── init_db.py       # 一键建库建表 + 导入种子数据
│   │   └── routers/         # auth / users / questions / sessions / billing
│   ├── uploads/             # 简历上传目录
│   ├── test_e2e.py          # 端到端接口测试（15 项全通过）
│   └── requirements.txt
└── frontend/                # Vue3 前端
    └── src/
        ├── views/           # 9 个页面（首页/登录/配置/语音/编程/白板/报告/定价/个人中心）
        ├── stores/          # Pinia：user（登录态）+ interview（会话状态机）
        ├── api/             # axios 封装
        └── components/      # RoomHeader（面试房间顶栏 + 倒计时）
```

## 快速启动

### 方式一：一键启动（推荐，重启电脑后依然有效）

双击桌面上的 `start_ai.bat`（或 `D:\start_ai.bat`）即可，脚本会自动：

1. 检查后端虚拟环境 `backend\.venv` 的依赖，缺失时自动补装；
2. 启动后端 FastAPI → http://localhost:8000（接口文档 /docs）；
3. 检查前端 `node_modules`，缺失时自动 `npm install`；
4. 启动前端 Vite → http://localhost:5173；
5. 等待数秒后自动打开浏览器。

> 脚本内全部使用**绝对路径**（venv Python / Node npm 均写死），不依赖 `activate` 和系统 PATH，
> 因此重启电脑后直接双击依然有效。MySQL80 服务已设为开机自启，无需手动启动数据库。

### 方式二：手动启动（开发调试时）

#### 1. 数据库（MySQL 8.0）

后端默认连接 `mysql+pymysql://root:123456@localhost:3306/ai_interview`。  
若本机账号密码不同，请通过环境变量覆盖：

```bash
# Windows (Git Bash)
export DB_URL="mysql+pymysql://root:你的密码@localhost:3306/ai_interview?charset=utf8mb4"
```

#### 2. 后端

```bash
cd backend

# 虚拟环境路径（不要直接用系统 python）
VENV=D:/cp/backend/.venv
"$VENV/Scripts/pip" install -r requirements.txt   # 首次

# 首次运行：建库建表 + 导入种子数据（岗位/套餐/题库/演示账号）
"$VENV/Scripts/python" -B -m app.init_db

# 启动服务（http://localhost:8000，接口文档 http://localhost:8000/docs）
"$VENV/Scripts/python" -B -m uvicorn app.main:app --port 8000 --reload
```

> 注意：如果看到 `ModuleNotFoundError: No module named 'openai'`，说明你用了系统 Python 启动，请用上面 `$VENV/Scripts/python` 路径启动。

演示账号：**<demo@interview.cn> / 123456**（已带 3 场历史面试与成长曲线）

#### 3. 前端

```bash
cd frontend
npm install        # 首次
npm run dev        # http://localhost:5173（/api 已代理到 8000）
```

## 核心功能对照（PRD → 实现）

| PRD 模块 | 实现                                                         |
| ------ | ---------------------------------------------------------- |
| 面试配置   | 岗位/难度/时长/题型滑块/简历上传，右侧实时生成"面试说明书"                           |
| 语音对话   | Web Speech API 语音识别 + speechSynthesis 播报；文字作答降级；AI 按题型追问两轮 |
| 在线编程   | 多语言代码编辑器（行号/模板）、模拟判题、用例通过状态、"提交并讲解思路"                      |
| 白板画图   | 拖拽节点（数据库/缓存/MQ/网关等元素）、连线模式、自动保存快照、AI 观察面板                  |
| 评分反馈   | 免费版总分+评语；会员解锁五维评分与逐题复盘（报告页锁定遮罩）                            |
| 题库     | 内置 24 题（算法/系统设计/八股/行为/项目深挖），按岗位难度出题，题目快照解耦                 |
| 账户     | 免登录游客模式（公开接口出题 + localStorage 记录）+ 邮箱注册登录（JWT）             |
| 订阅会员   | 三档套餐、扫码支付收银台（微信/支付宝个人收款码 + 付款确认）、订阅开通/取消、月度配额（免费 3 场，会员不限） |

## 接入 DeepSeek 大模型（推荐）

项目已内置 DeepSeek 调用模块（`backend/app/llm.py`），配置 API key 后，AI 面试官会根据你的实际回答内容动态追问、点评，而不是按固定模板轮询。

### 配置步骤

1. 在 `backend` 目录复制环境变量示例：

```bash
cd backend
cp .env.example .env
```

2. 编辑 `.env`，填入你的 DeepSeek API key：

```env
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

3. 重启后端服务即可生效。

### 行为说明

- 已配置 `DEEPSEEK_API_KEY`：语音/文字问答走 DeepSeek，`answer="不知道"` 会被识别并引导展开；回答充分时会进入下一题。
- 未配置或 API 调用失败：自动降级到本地规则引擎（`ai_engine.py`），保证服务仍可运行。
- 评分报告同样优先走 DeepSeek，失败时回退到本地规则评分。
- 默认模型为 `deepseek-chat`，默认 base_url 为 `https://api.deepseek.com`。  
  如需使用其他兼容 OpenAI 接口的服务（如 OpenAI、火山、智谱等），修改 `.env` 中的 `DEEPSEEK_BASE_URL` 与 `DEEPSEEK_MODEL` 即可。

## 其他说明

- 代码判题为模拟判定（用例通过展示），生产环境需接入 Docker/WASM 沙箱。
- 支付采用微信/支付宝**个人收款码**扫码付款：用户扫码完成转账后点击「我已完成支付」，系统将订单置为已付并开通会员。收款码图片位于 `frontend/public/pay/`（`wechat.png`、`alipay.jpg`），可直接替换为你自己的收款码；个人收款码无商户支付网关的自动到账回调，生产环境可接入微信/支付宝商户接口实现自动核销。
- TTS/ASR 当前使用浏览器原生 `speechSynthesis` 与 `Web Speech API`，无需后端配置。
