# TalentFlow-AI 业务知识图谱

> AI 蒲公英部落 — 全栈 AI 智能招聘平台
>
> 三大角色：**学生(求职者)** · **导师(HR)** · **管理员**  
> 技术栈：FastAPI + Vue3 + MySQL + Redis + Celery + LangGraph + MCP + FAISS + Docker

---

## 一、三大角色与权限矩阵

```
学生/求职者 (role=1)          导师/HR (role=2)           管理员 (role=3)
─────────────────          ────────────────         ───────────────
• 上传/管理简历               • 发布悬赏任务              • 发布/管理岗位
• 浏览岗位与任务              • 审核学生投递              • 审核简历（绑定技能）
• AI 职位推荐                 • 查看候选人简历            • 管理用户（角色/禁用）
• 一键智能投递 (Agent)        • 工作台统计看板            • 技能词典 CRUD
• 手动单岗位投递                                          • 数据看板
• 查看投递记录                                            • 批量导入岗位
```

---

## 二、全链路闭环总览

```
                         管理员 (role=3)
                            │
              发布岗位 ─────┼───── 审核简历
              (FAISS索引)   │     (绑定标准技能→status=reviewed)
                            │
     ┌──────────────────────┼──────────────────────┐
     ↓                      ↓                      ↓
   岗位池                 简历池 (已审核)         技能词典
   job_positions          resumes                skills_dict
     │                      │
     │     ┌────────────────┤
     │     ↓                ↓
     │   AI推荐引擎       学生投递
     │   (Celery异步)      │
     │     │               ├─ 智能投递 (LangGraph Agent, 7节点)
     │     │               │   LLM优化简历 → LLM生成求职信 → 批量投递
     │     │               │
     │     │               └─ 手动投递 (smart_deliver)
     │     │                   LLM生成求职信 → 单岗位投递
     │     │                       │
     │     └───────────┬───────────┘
     ↓                 ↓
   推荐结果         投递记录 (applications 表)
                      │
                      ↓
                  导师审核 (role=2)
                  ├─ pass   → status=approved + 任务认领
                  └─ reject → status=rejected + 任务恢复
                      │
                      ↓
                  学生看到结果
```

---

## 三、流程一：简历生命周期

```
┌─────────────────────────────────────────────────────────────────────┐
│                        简历从上传到可投递                              │
└─────────────────────────────────────────────────────────────────────┘

学生端                              后端                              管理员端
──────                              ────                              ───────

① 上传简历文件
   POST /user/resumes/parse
   (.pdf/.docx/.doc)
        │
        └──────────────────────────→ file_parser 提取文本
                                      │
                                    LLM parse_resume_fields()
                                    (async ainvoke, 不阻塞)
                                      │
                                    ← 返回结构化字段
                                    name/email/phone/skills
                                    education/summary...

② 用户确认/修改填表
   POST /user/resumes
        │
        └──────────────────────────→ 写入 resumes 表
                                    status = "processed"
                                    第一份自动设为默认

③ 管理简历                                   │
   GET/PUT/DELETE                             │
   /user/resumes                              │
   /user/resumes/{id}/default                 │
                                              │
                                     ┌────────┘
                                     ↓
                              GET /admin/resumes
                              查看所有简历列表
                                     │
                              GET /admin/resumes/{id}
                              查看详情 + AI解析字段
                                     │
                              POST /admin/resumes/{id}/review
                              ├─ pass: 绑定标准技能
                              │        status → "reviewed"
                              └─ reject:
                                       status → "pending"
                                     │
④ 简历可投递 ←────────────────────────┘
   (status = "reviewed")
```

### 涉及文件

| 层 | 文件 | 职责 |
|---|---|---|
| 前端 | `src/views/user/dashboard/ResumeManager.vue` | 上传/填表/列表 |
| 路由(用户) | `app/api/v1/user/resume.py` | 6个端点 |
| 路由(管理) | `app/api/v1/admin/resume_manager.py` | 5个端点 |
| 文件解析 | `app/utils/file_parser.py` | PDF/DOCX/图片文本提取 |
| LLM 解析 | `app/core/llm.py` → `parse_resume_fields()` | async ainvoke |
| 数据模型 | `app/models/resume.py`, `app/models/resume_skill.py`, `app/models/skills.py` | 三表关联 |

---

## 四、流程二：AI 职位推荐（异步）

```
┌─────────────────────────────────────────────────────────────────────┐
│                    异步推荐 — Celery + Redis 三库协作                   │
└─────────────────────────────────────────────────────────────────────┘

前端 JobCockpit.vue
  │
  ├─① POST /user/recommend
  │     compute_recommendations.delay(user_id)
  │     → 序列化任务 → LPUSH Redis DB0
  │     ← 立刻返回 task_id (非阻塞!)
  │
  ├─② 开始轮询
  │     GET /user/recommend/{task_id}
  │     AsyncResult(task_id) → GET Redis DB1
  │     PENDING → 1.5s 后再查
  │     STARTED → 继续等
  │
  │     ┌─── Celery Worker (独立进程, 不阻塞 FastAPI) ──────────┐
  │     │                                                        │
  │     │ ③ BRPOP Redis DB0 → 拿到任务                           │
  │     │                                                        │
  │     │ ④ 查缓存 Redis DB2                                     │
  │     │    key = rec:{user_id}:{resume_id}:{job_max_ts}         │
  │     │    ├─ 命中 → 直接返回 (毫秒)                            │
  │     │    └─ 未命中 ↓                                         │
  │     │                                                        │
  │     │ ⑤ 查 MySQL                                             │
  │     │    - 用户简历 + 技能                                    │
  │     │    - 全量 is_active=True 的岗位                         │
  │     │                                                        │
  │     │ ⑥ HTTP → /internal/embed                               │
  │     │    主进程加载 sentence-transformer                      │
  │     │    (text2vec-base-chinese)                              │
  │     │    → 简历 + 所有岗位 → 向量                             │
  │     │                                                        │
  │     │ ⑦ 混合打分                                             │
  │     │    70% Cosine 相似度 (语义)                              │
  │     │  + 30% Jaccard 相似度 (技能集合)                         │
  │     │  → 粗排 Top-15                                         │
  │     │                                                        │
  │     │ ⑧ HTTP → /internal/rerank                              │
  │     │    BGE-Reranker-v2-m3 精排                              │
  │     │    0.7 × reranker_score + 0.3 × 粗排score              │
  │     │  → 精排 Top-5                                          │
  │     │                                                        │
  │     │ ⑨ 写缓存 Redis DB2                                     │
  │     │    setex(key, 3600, result)  60分钟 TTL                 │
  │     │                                                        │
  │     │ ⑩ return → Celery 自动 SET Redis DB1                   │
  │     │    celery-task-meta-{task_id} = SUCCESS + result        │
  │     └────────────────────────────────────────────────────────┘
  │
  └─③ SUCCESS → 渲染推荐卡片
        岗位标题 | 匹配度 | 公司 | 薪资 | 匹配技能
```

### Redis 四库分工

| DB | 名称 | 写入方 | 读取方 | 生命周期 |
|---|---|---|---|---|
| **0** | Broker | FastAPI `.delay()` LPUSH | Celery Worker BRPOP | 消费即销毁 |
| **1** | Backend | Celery Worker return | FastAPI AsyncResult GET | TTL 3600s |
| **2** | Cache | Celery Worker setex | Celery Worker get | TTL 3600s |
| **3** | Checkpointer | LangGraph ainvoke | LangGraph aget_tuple | 持久保留(规划中) |

### 涉及文件

| 层 | 文件 | 职责 |
|---|---|---|
| 前端 | `JobCockpit.vue` | 推荐卡片 + 轮询动画 |
| 路由 | `app/api/v1/user/recommend.py` | 提交任务 + 查询结果 |
| Worker | `app/rag/recommendation.py` | Celery @task, 完整推荐逻辑 |
| 配置 | `app/celery_app.py` | Celery 实例, DB0/DB1 |
| Internal | `app/api/v1/internal.py` | embed + rerank HTTP 接口 |
| 向量化 | `app/core/embedding.py` | sentence-transformer 加载 |
| 精排 | `app/rag/reranker.py` | BGE-Reranker 加载与调用 |
| 向量库 | `app/rag/vector_store.py` | 技能 FAISS 索引 (语义匹配) |
| 检索器 | `app/rag/retriver.py` | 搜索相似技能 |

---

## 五、流程三：智能投递 Agent（一键海投）

```
┌─────────────────────────────────────────────────────────────────────┐
│            LangGraph Agent — 7节点状态图 + 策略模式                    │
└─────────────────────────────────────────────────────────────────────┘

前端 JobCockpit.vue
  点"一键投递"
  POST /user/agent/apply {mode: "auto", threshold: 60}
    │
    ↓
SmartApplyAgent(user_id=2, mode="auto").run()
    │
    ├── mode == "force_reuse" ?
    │   ├─ 查24h投递历史
    │   ├─ 简历更新时间戳 vs 最后投递时间
    │   └─ 命中 → 直接返回缓存 (跳过整个 Graph)
    │
    └── 正常流程 ↓

agent_graph.ainvoke(state, thread_id=user_id)
    │
    │  MemorySaver Checkpointer (可断点续作)
    │
    ├─ [1] fetch_resume ──────────────────────────────────────────┐
    │   查 MySQL, 三级降级:                                        │
    │   ① 默认 + 已审核 → ② 任意已审核 → ③ 已处理(未审核)         │
    │   → state["resume"]                                         │
    │   → state["skip_generation"] / state["error"]               │
    └──────────────────────────────────────────────────────────────┘
    │
    ↓ 条件边: route_after_fetch
    │  有简历 → [2]    没简历/出错 → [7]直接结束
    │
    ├─ [2] get_recommendations ───────────────────────────────────┐
    │   双路径容错:                                                │
    │   ① MCP Client → call_tool("recommend_jobs")                │
    │      → MCP Server (port 8003) → Celery → 推荐结果           │
    │   ② MCP 失败 → fallback 直调                                │
    │      compute_recommendations(user_id)                       │
    │   → state["matched_jobs"] (score ≥ threshold)               │
    └──────────────────────────────────────────────────────────────┘
    │
    ↓ 条件边: route_after_recommend
    │  有匹配 → [3]    无匹配 → [7]直接结束
    │
    ├─ [3] optimize_resume ───────────────────────────────────────┐
    │   load_skill("optimize_resume")  ← 从 skills/*.md 动态加载   │
    │   Prompt: HR视角, 80字, 量化数据, 行业术语                    │
    │   llm.invoke(prompt) → 全局优化简历亮点 (非按岗位)            │
    │   → state["optimized_summary"]                              │
    └──────────────────────────────────────────────────────────────┘
    │
    ↓ 固定边
    │
    ├─ [4] save_optimized_resume ─────────────────────────────────┐
    │   UPDATE resumes SET summary=optimized WHERE id=resume.id    │
    │   持久化，force_reuse 时可跳过 LLM                            │
    └──────────────────────────────────────────────────────────────┘
    │
    ↓ 固定边
    │
    ├─ [5] generate_letter ───────────────────────────────────────┐
    │   load_skill("generate_letter") ← 招聘顾问视角               │
    │   Prompt: 100-150字, 第一人称, JSON输出                      │
    │   llm.invoke(prompt) → 为所有匹配岗位各自生成求职信           │
    │   → state["cover_letters"] = {岗位标题: 求职信, ...}         │
    └──────────────────────────────────────────────────────────────┘
    │
    ↓ 固定边
    │
    ├─ [6] apply_jobs ───────────────────────────────────────────┐
    │   逐岗位:                                                    │
    │   ① 查重 (同用户+同岗位只投一次)                              │
    │   ② 求职信模糊key匹配 (LLM输出标题可能略有差异)               │
    │   ③ 创建 Application(status="applied")                      │
    │   → state["applied"]                                        │
    └──────────────────────────────────────────────────────────────┘
    │
    ↓ 固定边
    │
    └─ [7] save_record ──────────────────────────────────────────┐
        logger.info(...)  终态日志，Graph 结束                    │
       └──────────────────────────────────────────────────────────┘

← 返回 {applied: [...], cover_letters: {...}} → 前端渲染
```

### Agent 文件协作关系

```
router.py (POST /user/agent/apply)
  │
  └─→ smart_apply_agent.py  (SmartApplyAgent 类)
        │ 拼 state + 策略判断 + ainvoke
        │
        └─→ graph.py  (StateGraph 编译, 全局单例 agent_graph)
              │ 注册7节点 + 2条件边 + 4固定边
              │
              ├─→ state.py   (AgentState TypedDict, 共享黑板)
              ├─→ nodes.py   (7个原子节点函数)
              │     ├─→ mcp_client.py   (MCP协议调用推荐引擎)
              │     └─→ skills/*.md     (外置 Prompt 模板)
              └─→ edges.py   (2个条件路由函数)
```

### 三种策略模式

| 模式 | 行为 | 适用场景 |
|---|---|---|
| `auto` | 正常走 Graph，查重跳过已投递岗位 | 默认 |
| `force_generate` | 跳过查重，强制重新生成求职信 | 想更新求职信 |
| `force_reuse` | 检查 24h 内投递 + 简历没变 → 直接返回历史记录 | 省 LLM 费用 |

### 涉及文件(Agent 目录)

| 文件 | 职责 | 行数 |
|---|---|---|
| `state.py` | 定义 AgentState — 贯穿全图的共享数据类型 | 20 |
| `graph.py` | 编译 StateGraph，注册节点+边，全局单例 | 97 |
| `nodes.py` | 7个原子节点，每个单一职责 | 268 |
| `edges.py` | 2个条件路由函数 (熔断短路) | 38 |
| `smart_apply_agent.py` | 策略模式封装 + 缓存检查 | 44 |
| `smart_deliver.py` | 手动单岗位投递 (不走 Graph) | 98 |
| `router.py` | HTTP 入口 /user/agent/apply | 69 |
| `mcp_client.py` | MCP 协议客户端 | 34 |
| `skills/__init__.py` | 动态加载 .md Prompt 模板 | 15 |
| `skills/optimize_resume.md` | 简历优化 Prompt (HR 视角) | 20 |
| `skills/generate_letter.md` | 求职信生成 Prompt (招聘顾问视角) | 15 |

---

## 六、流程四：手动单岗位投递

```
┌─────────────────────────────────────────────────────────────────────┐
│              轻量直通路 — 不走 LangGraph，REST 直接完成                │
└─────────────────────────────────────────────────────────────────────┘

前端 JobCockpit / TaskBoard
  点某个岗位的"投递"按钮
  POST /user/smart-deliver {job_id: 44, mode: "auto"}
    │
    ↓
  smart_deliver.py
    │
    ├─① 查简历 (默认已审核 → 降级任意可用)
    │     没简历 → return "请先创建简历并等待审核"
    │
    ├─② 防重复检查 (同用户+同岗位)
    │     已有 → return "您已投递过该岗位"
    │
    ├─③ 查岗位信息 (title + description)
    │
    ├─④ LLM 生成求职信
    │     load_skill("generate_letter") + 候选人背景 + 岗位信息
    │     → 纯文本 80-120 字
    │
    └─⑤ 创建 Application(status="applied", cover_letter=...)
         → return {success, message, cover_letter}

  与 Agent 投递的区别:
  ┌──────────────┬──────────────────┬───────────────────┐
  │              │ 智能投递 (Agent)  │ 手动投递 (Deliver) │
  ├──────────────┼──────────────────┼───────────────────┤
  │ 走什么       │ LangGraph 7节点图 │ REST 路由直调      │
  │ 推荐引擎     │ ✅ 先推荐再投     │ ❌ 不调推荐         │
  │ 简历优化     │ ✅ LLM优化亮点    │ ❌ 跳过              │
  │ 求职信       │ ✅ 多岗位批量生成 │ ✅ 单岗位一条        │
  │ 投递数量     │ 所有匹配岗位      │ 1个岗位             │
  │ 适用场景     │ 海投              │ 看到感兴趣的单个投   │
  └──────────────┴──────────────────┴───────────────────┘
```

### 涉及文件

| 文件 | 职责 |
|---|---|
| `app/agent/smart_deliver.py` | 单岗位投递全流程 |

---

## 七、流程五：导师工作台

```
┌─────────────────────────────────────────────────────────────────────┐
│                  导师(role=2) — 发任务 + 审投递                        │
└─────────────────────────────────────────────────────────────────────┘

① 发布悬赏任务
   POST /mentor/tasks
   {title, description, category, price, skills, difficulty, duration}
   → mentor_id 自动绑定 → status=1 (进行中)

② 工作台看板
   GET /mentor/timeline
   → UNION 查询: 任务状态变更 + 新投递记录
   → 按时间倒序, 动态时间轴

   GET /mentor/stats
   → 总任务数 / 进行中 / 悬赏总额 / 待审核数

③ 查看投递列表
   GET /mentor/applications
   → 合并两路数据 (最多50条):
     ├─ 任务投递: Application JOIN Task JOIN User
     └─ 岗位投递: Application JOIN JobPosition JOIN User
   → 统一格式, 按时间倒序

④ 查看候选人简历
   GET /mentor/resumes/{resume_id}
   → 完整简历 (基本信息 + 技能 + 经历 + 项目)

⑤ 审核投递
   POST /mentor/applications/{id}/review
   {action: "pass" | "reject"}

   pass:
     Application.status = "approved"
     Task.taken_by = 候选人ID
     Task.status = 3 (已完成)

   reject:
     Application.status = "rejected"
     Task.taken_by = None
     Task.status = 1 (恢复进行中)
```

### 涉及文件

| 文件 | 职责 |
|---|---|
| 前端 | `src/views/hr/DashBoard.vue`, `Applications.vue`, `Task.vue` |
| 统计 | `app/api/v1/mentor/dashboard.py` (timeline + stats) |
| 任务 | `app/api/v1/mentor/task_manager.py` (CRUD) |
| 审核 | `app/api/v1/mentor/delivery_manager.py` (列表+审核+简历) |

---

## 八、流程六：管理员后台

```
┌─────────────────────────────────────────────────────────────────────┐
│                     管理员(role=3) — 全平台管理                        │
└─────────────────────────────────────────────────────────────────────┘

① 岗位管理
   POST /admin/jobs/parse    → 上传JD → LLM解析 → 预览填表
   POST /admin/jobs          → 确认创建 → FAISS索引
   POST /admin/jobs/batch    → 批量文档 → LLM拆分 → 批量入库
   GET/PUT/DELETE /admin/jobs → CRUD

② 简历审核
   GET  /admin/resumes              → 简历列表 (按状态筛选)
   GET  /admin/resumes/{id}         → 简历详情 + AI解析字段
   POST /admin/resumes/{id}/review  → pass/reject + 绑定标准技能

③ 技能词典
   CRUD /admin/skills
   → 维护标准技能名称 + 分类
   → 简历审核时用于技能标签标准化

④ 用户管理
   GET /admin/users            → 用户列表 + 角色筛选
   PUT /admin/users/{id}       → 修改角色/禁用
   DELETE /admin/users/{id}    → 删除用户

⑤ 数据看板
   GET /admin/stats/overview
   → 总用户数 / 岗位数 / 简历数 / 待审核数
   → 7日简历上传趋势图
   → 技能分类分布图
```

### 涉及文件

| 模块 | 文件 |
|---|---|
| 岗位 | `app/api/v1/admin/job_manager.py` |
| 简历 | `app/api/v1/admin/resume_manager.py` |
| 技能 | `app/api/v1/admin/skill_manager.py` |
| 用户 | `app/api/v1/admin/user_manager.py` |
| 看板 | `app/api/v1/admin/status_manager.py` |

---

## 九、数据库核心表关系

```
users (用户)
  ├── role: 1=学生 2=导师 3=管理员
  │
  ├─→ resumes (简历)
  │     ├── user_id → users.id
  │     ├── is_default: 0/1
  │     ├── status: pending / processed / reviewed
  │     └─→ resume_skills (简历-技能关联)
  │           ├── resume_id → resumes.id
  │           └── skill_id → skills_dict.id
  │
  ├─→ applications (投递记录)
  │     ├── user_id → users.id
  │     ├── job_id → job_positions.id (可为空)
  │     ├── task_id → tasks.id (可为空)
  │     ├── resume_id → resumes.id
  │     ├── cover_letter: TEXT (LLM生成的求职信)
  │     └── status: applied / approved / rejected
  │
  ├─→ tasks (悬赏任务)
  │     ├── mentor_id → users.id (发布导师)
  │     ├── taken_by → users.id (被录用的学生)
  │     └── status: 0=草稿 1=进行中 2=暂停 3=已完成
  │
  └─→ job_positions (招聘岗位)
        ├── job_id: JOB-xxxxxxxx
        ├── required_skills: JSON
        └── is_active: 0/1

skills_dict (标准技能词典)
  └─→ resume_skills (关联)
```

---

## 十、关键技术对应业务

| 技术 | 用于哪个流程 | 核心文件 |
|---|---|---|
| **aiomysql 异步数据库** | 全局 | `database.py` (异步+同步双引擎) |
| **Celery 异步任务** | 流程二: AI推荐 | `celery_app.py` + `recommendation.py` |
| **Redis 四库** | 流程二+三 | DB0(Broker) DB1(Backend) DB2(Cache) DB3(Checkpointer) |
| **LangGraph StateGraph** | 流程三: 智能投递 | `graph.py` (7节点+2条件边) |
| **MCP 协议** | 流程三: Agent调推荐 | `mcp_client.py` + `mcp_server/server.py` |
| **Skills Prompt** | 流程三: LLM优化 | `skills/*.md` (外置模板) |
| **FAISS 向量索引** | 流程六: 岗位入库 | `core/vector_store.py` + `rag/vector_store.py` |
| **RAG 混合检索** | 流程二: 推荐计算 | `recommendation.py` (Jaccard+Cosine+Reranker) |
| **LLM (DeepSeek)** | 流程一/三/四/六 | `llm.py` (ainvoke同步步用) |
| **CI/CD** | 部署 | `.github/workflows/deploy.yml` + 4个Dockerfile |

---

## 十一、API 端点全景

### 认证 (Auth)
| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/v1/auth/register` | 注册 |
| POST | `/api/v1/auth/login` | 登录, 返回 JWT |

### 学生端 (User)
| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/v1/user/resumes/parse` | 上传简历 → AI 解析 |
| POST | `/api/v1/user/resumes` | 保存简历 |
| GET | `/api/v1/user/resumes` | 我的简历列表 |
| PUT | `/api/v1/user/resumes/{id}` | 更新简历 |
| DELETE | `/api/v1/user/resumes/{id}` | 删除简历 |
| POST | `/api/v1/user/resumes/{id}/default` | 设为默认 |
| GET | `/api/v1/user/tasks` | 可接任务列表 |
| GET | `/api/v1/user/tasks/{id}` | 任务详情 |
| POST | `/api/v1/user/tasks/{id}/apply` | 申请任务 |
| GET | `/api/v1/user/jobs` | 岗位列表 |
| POST | `/api/v1/user/jobs/{id}/apply` | 投递岗位 |
| GET | `/api/v1/user/applications` | 我的投递记录 |
| POST | `/api/v1/user/recommend` | 发起AI推荐 |
| GET | `/api/v1/user/recommend/{id}` | 查询推荐结果 |
| POST | `/api/v1/user/agent/apply` | **一键智能投递** |
| GET | `/api/v1/user/agent/status` | 投递历史 |
| POST | `/api/v1/user/smart-deliver` | 手动单岗位投递 |

### 导师端 (Mentor, role=2)
| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/v1/mentor/timeline` | 动态时间轴 |
| GET | `/api/v1/mentor/stats` | 统计看板 |
| POST | `/api/v1/mentor/tasks` | 发布任务 |
| GET | `/api/v1/mentor/tasks` | 我的任务 |
| PUT | `/api/v1/mentor/tasks/{id}` | 编辑任务 |
| DELETE | `/api/v1/mentor/tasks/{id}` | 删除任务 |
| GET | `/api/v1/mentor/applications` | 投递列表 |
| POST | `/api/v1/mentor/applications/{id}/review` | 审核投递 |
| GET | `/api/v1/mentor/resumes/{id}` | 查看简历 |

### 管理端 (Admin, role=3)
| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/v1/admin/jobs/parse` | JD解析 |
| POST | `/api/v1/admin/jobs` | 创建岗位 |
| POST | `/api/v1/admin/jobs/batch` | 批量导入 |
| GET/PUT/DELETE | `/api/v1/admin/jobs/{id}` | 岗位CRUD |
| GET | `/api/v1/admin/resumes` | 简历列表 |
| POST | `/api/v1/admin/resumes/{id}/review` | 审核简历 |
| CRUD | `/api/v1/admin/skills` | 技能词典 |
| GET | `/api/v1/admin/users` | 用户列表 |
| PUT/DELETE | `/api/v1/admin/users/{id}` | 用户管理 |
| GET | `/api/v1/admin/stats/overview` | 数据看板 |

### 内部接口 (Internal)
| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/v1/internal/embed` | 文本向量化 (供Celery Worker调用) |
| POST | `/api/v1/internal/rerank` | Cross-Encoder精排 (供Celery Worker调用) |

---

## 十二、演示操作脚本

### 双浏览器演示闭环 (Chrome + Edge/无痕)

```
Chrome (管理员 admin)                 Edge 无痕 (学生 zhangsan)
─────────────────────                 ─────────────────────────

① POST /admin/jobs
   发布一个岗位 "Python后端开发"

② GET /admin/resumes
   找到 zhangsan 的简历
   → 审核通过, 绑定技能标签
                                      ③ 刷新 JobCockpit
                                         → 看到新岗位

                                      ④ POST /user/recommend
                                         → 等待 AI 推荐结果
                                         → 推荐卡片出现

                                      ⑤ 点 "一键投递"
                                         → Agent 推荐 → 优化简历
                                         → 生成求职信 → 投递成功

⑥ GET /mentor/applications
   看到 zhangsan 的投递
   → 查看求职信内容
   → 点 "通过"

                                      ⑦ 查看 Applications
                                         → 状态: "approved" ✅
```

---

## 十三、部署架构

```
服务器 (140.210.92.250)
  │
  ├── docker compose (6个容器)
  │     ├── talentflow-frontend   :8893  (Nginx + Vue静态文件)
  │     ├── talentflow-backend    :8000  (FastAPI + PyTorch模型)
  │     ├── talentflow-worker     (Celery, 无端口)
  │     ├── talentflow-mcp        :8003  (MCP Server)
  │     ├── talentflow-redis      :6379  (Broker/Backend/Cache)
  │     └── talentflow-mysql      :3306  (主数据库)
  │
  ├── 模型文件: /opt/models/ (Volume挂载, 不进镜像)
  └── CI/CD: git push → GitHub Actions → ghcr.io → SSH部署
```
