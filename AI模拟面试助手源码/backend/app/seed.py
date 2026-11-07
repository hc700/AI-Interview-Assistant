"""种子数据：岗位、会员套餐、题库、演示账号与其历史面试记录。"""
import json
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from .models import (
    DimensionEvaluation, InterviewSession, Position, Question, QuestionTag,
    SessionEvaluation, SessionSection, SessionQuestion, SubscriptionPlan, User,
)
from .security import hash_password

POSITIONS = [
    ("后端开发工程师", "backend", "服务端 / 中间件 / 分布式"),
    ("前端开发工程师", "frontend", "Web / 跨端 / 工程化"),
    ("算法工程师", "algorithm", "机器学习 / 搜索推荐"),
    ("全栈开发工程师", "fullstack", "前后端全链路"),
    ("测试开发工程师", "test", "自动化测试 / 质量工程"),
    ("大数据开发工程师", "data", "数据仓库 / 实时计算"),
]

PLANS = [
    ("monthly", "月度会员", "monthly", 39, 59,
     "不限次模拟面试 · 五维报告 · 简历定制提问（3 份）", 1),
    ("quarterly", "季度会员", "quarterly", 79, 117,
     "不限次模拟面试 · 五维报告 · 简历定制提问（不限份） · 新题抢先体验", 2),
    ("yearly", "年度会员", "yearly", 199, 468,
     "全部会员权益 · 求职冲刺课程包（价值 ¥99）", 3),
]

# (type, title, content, difficulty, reference, tags, test_cases)
QUESTIONS = [
    # ---- 算法题 ----
    ("algorithm", "206. 反转链表",
     "给你单链表的头节点 head，请你反转链表并返回反转后的链表。要求：先给出迭代解法，再分析能否用递归实现。",
     2, "迭代：三指针 prev/cur/nxt 逐个反转，O(n)/O(1)。递归：reverseList(head.next) 后接回，O(n)/O(n)。",
     ["链表", "双指针"],
     [{"input": "head = [1,2,3,4,5]", "expected": "[5,4,3,2,1]"},
      {"input": "head = [1,2]", "expected": "[2,1]"},
      {"input": "head = []", "expected": "[]"}]),
    ("algorithm", "1. 两数之和",
     "给定整数数组 nums 和目标值 target，找出和为目标值的两个整数下标。要求时间复杂度低于 O(n²)。",
     1, "哈希表一次遍历：value -> index，查找 target - num 是否已存在，O(n)/O(n)。",
     ["哈希表", "数组"],
     [{"input": "nums = [2,7,11,15], target = 9", "expected": "[0,1]"},
      {"input": "nums = [3,2,4], target = 6", "expected": "[1,2]"}]),
    ("algorithm", "3. 无重复字符的最长子串",
     "给定字符串 s，计算不含重复字符的最长子串长度。",
     2, "滑动窗口 + 哈希集合，右指针扩张，遇到重复则收缩左指针，O(n)/O(charset)。",
     ["滑动窗口", "字符串"],
     [{"input": "s = abcabcbb", "expected": "3"},
      {"input": "s = bbbbb", "expected": "1"},
      {"input": "s = pwwkew", "expected": "3"}]),
    ("algorithm", "215. 数组中的第K个最大元素",
     "在未排序数组中找到第 k 个最大的元素。要求平均时间复杂度 O(n)。",
     3, "快速选择（随机 pivot）平均 O(n)；或维护大小为 k 的小顶堆 O(n log k)。",
     ["堆", "快速选择"],
     [{"input": "nums = [3,2,1,5,6,4], k = 2", "expected": "5"},
      {"input": "nums = [3,2,3,1,2,4,5,5,6], k = 4", "expected": "4"}]),
    ("algorithm", "53. 最大子数组和",
     "找出具有最大和的连续子数组（至少一个元素），返回其最大和。",
     2, "动态规划：dp[i] = max(nums[i], dp[i-1]+nums[i])，空间可压缩到 O(1)。",
     ["动态规划", "数组"],
     [{"input": "nums = [-2,1,-3,4,-1,2,1,-5,4]", "expected": "6"},
      {"input": "nums = [-1]", "expected": "-1"}]),
    ("algorithm", "102. 二叉树层序遍历",
     "给定二叉树根节点，返回节点值的层序遍历结果（按层分组）。",
     1, "BFS 队列，每层记录当前队列长度后逐个出队。",
     ["树", "BFS"],
     [{"input": "[3,9,20,null,null,15,7]", "expected": "[[3],[9,20],[15,7]]"}]),
    ("algorithm", "146. LRU 缓存",
     "设计并实现 LRU 缓存：get 与 put 均 O(1)。说明你的数据结构设计。",
     3, "哈希表 + 双向链表；或直接使用语言内置的 LinkedHashMap / OrderedDict。",
     ["设计", "哈希表", "链表"],
     [{"input": "put(1,1) put(2,2) get(1) put(3,3) get(2)", "expected": "1, -1"}]),
    ("algorithm", "121. 买卖股票的最佳时机",
     "给定股票每日价格，只允许一次买卖，求最大利润。",
     1, "一遍扫描维护历史最低价，更新 max(profit)。",
     ["数组", "贪心"],
     [{"input": "prices = [7,1,5,3,6,4]", "expected": "5"},
      {"input": "prices = [7,6,4,3,1]", "expected": "0"}]),

    # ---- 系统设计 ----
    ("system_design", "设计一个短链接服务",
     "请设计一个类似 bit.ly 的短链接服务。在白板上画出架构，并说明存储选型、缓存策略、301/302 的选择与短码生成方案。",
     2, "网关 + Redis 缓存 + MySQL 分片存储；302 便于统计；发号器/哈希取短码；布隆过滤器防穿透。",
     ["系统设计", "缓存", "分布式"], None),
    ("system_design", "设计一个秒杀系统",
     "请设计支撑 10w QPS 的秒杀系统，说明如何防止超卖、如何削峰、库存如何扣减。",
     3, "网关限流 + Redis 预扣库存 + MQ 异步落库 + 前端答题/排队打散流量。",
     ["系统设计", "高并发", "Redis"], None),
    ("system_design", "设计一个即时通讯（IM）系统",
     "设计单机百万在线的 IM 系统：连接层如何组织、消息如何投递与保证不丢、离线消息如何存储。",
     3, "长连接网关集群 + 路由层 + 消息队列 + 写扩散/读扩散按关系规模取舍 + ACK 与重推。",
     ["系统设计", "网络", "消息队列"], None),
    ("system_design", "设计一个排行榜服务",
     "设计实时更新的亿级用户排行榜（如游戏积分榜），支持查询 Top N 与个人排名。",
     2, "Redis ZSet 分桶 + 定期合并，冷热分层，Top N 用本地缓存。",
     ["系统设计", "Redis"], None),

    # ---- 八股 ----
    ("fundamental", "TCP 三次握手",
     "请讲讲 TCP 三次握手的过程，为什么不是两次握手？",
     1, "确认双方收发能力；两次无法让服务端确认客户端可接收。顺带讲 SYN 洪泛与半连接队列。",
     ["网络", "TCP"], None),
    ("fundamental", "HashMap 底层原理与扩容",
     "讲讲 HashMap 的底层结构、put 流程与扩容机制，为什么链表长度超过 8 转红黑树？",
     2, "数组+链表/红黑树；负载因子 0.75 触发 2 倍扩容；树化抵御哈希碰撞攻击。",
     ["Java", "集合"], None),
    ("fundamental", "进程 / 线程 / 协程的区别",
     "请说明进程、线程、协程的区别及适用场景。协程切换为什么比线程切换开销小？",
     1, "资源拥有 vs 调度执行；协程用户态切换不陷入内核，上下文更小。",
     ["操作系统"], None),
    ("fundamental", "MySQL 索引与 B+ 树",
     "为什么 MySQL InnoDB 用 B+ 树而不是 B 树或哈希索引？联合索引的最左前缀原则是什么？",
     2, "矮胖树减少磁盘 IO、叶子链表利于范围查询；最左前缀决定索引命中。",
     ["MySQL", "索引"], None),
    ("fundamental", "Redis 持久化与缓存一致性",
     "讲讲 Redis 的 RDB 与 AOF 的取舍，以及 Cache-Aside 模式下如何保证缓存与数据库一致性。",
     2, "RDB 快照快、AOF 更完整；更新 DB 后删缓存 + 延迟双删 + 兜底过期时间。",
     ["Redis", "缓存"], None),
    ("fundamental", "HTTP/HTTPS 与常见状态码",
     "HTTPS 握手过程是怎样的？301 和 302 的区别是什么？",
     1, "TLS 证书验证 + 协商对称密钥；301 永久重定向会缓存，302 临时重定向。",
     ["网络", "HTTP"], None),
    ("fundamental", "垃圾回收（GC）算法",
     "讲讲常见 GC 算法（标记清除 / 复制 / 标记整理）与分代收集的思路。",
     2, "新生代复制、老年代标记整理/清除；CMS/G1 的取舍。",
     ["JVM", "GC"], None),
    ("fundamental", "一致性哈希",
     "什么是一致性哈希？解决什么问题？虚拟节点的作用是什么？",
     2, "节点增减只影响相邻区间数据；虚拟节点打散热点、提升均衡性。",
     ["分布式", "缓存"], None),

    # ---- 行为面 ----
    ("behavioral", "最有挑战的一个项目",
     "介绍你职业生涯中最有挑战的一个项目：背景、你的角色、难点和最终结果。",
     1, "STAR 结构，突出个人贡献与量化结果。", ["软素质"], None),
    ("behavioral", "与同事产生分歧的经历",
     "讲一次你与同事/上级在技术方案上产生分歧的经历，最后如何解决？",
     1, "对事不对人，用数据与实验推动决策。", ["软素质"], None),
    ("behavioral", "为什么想加入我们公司",
     "你为什么想加入我们？你的职业规划是什么？",
     1, "结合公司业务 + 个人成长路径。", ["软素质"], None),
    ("behavioral", "最大的失败经历",
     "讲一次你印象最深的失败经历，你从中学到了什么？",
     2, "坦诚 + 反思 + 后续改进行动。", ["软素质"], None),

    # ---- 项目深挖 ----
    ("project_dig", "高并发系统的角色与贡献",
     "介绍你最近负责的、并发量最高的一个系统，你在其中承担什么角色？",
     2, "讲清架构、个人贡献与量化指标。", ["项目"], None),
    ("project_dig", "线上故障排查经历",
     "讲一次你亲自处理的线上故障：现象、定位过程、止损与后续改进。",
     2, "监控定位 -> 快速止损 -> 根因分析 -> 复盘改进。", ["项目", "稳定性"], None),
    ("project_dig", "技术选型的取舍",
     "讲一个你主导的技术选型：对比了哪些方案，为什么最终选了现在的方案？",
     2, "多方案对比维度 + 团队适配 + 落地结果。", ["项目", "架构"], None),
    ("project_dig", "性能优化的完整案例",
     "讲一次你做过的性能优化：瓶颈在哪、你怎么定位、优化前后数据对比。",
     2, "先度量再优化，给出前后量化对比。", ["项目", "性能"], None),
]

_HISTORY = [
    # (days_ago, score, comment, mix, dims)
    (18, 68, "首次模拟整体偏紧张，回答偏短，建议放慢语速、先给结论再展开。系统设计环节思路可以但缺乏数据支撑。",
     {"voice": 6, "coding": 1, "whiteboard": 1},
     {"algorithm": 72, "system_design": 55, "expression": 62, "code_quality": 70, "project_depth": 60}),
    (6, 74, "较上一场有明显进步，项目讲述更有结构。算法题完成但复杂度分析不够主动，系统设计仍需专项提升。",
     {"voice": 6, "coding": 2, "whiteboard": 1},
     {"algorithm": 78, "system_design": 60, "expression": 76, "code_quality": 75, "project_depth": 70}),
    (1, 82, "整体表现良好：项目讲述有结构感，优化前后数据对比令人印象深刻；算法题一次通过。短板在系统设计，建议补分布式场景纵深练习。",
     {"voice": 6, "coding": 2, "whiteboard": 1},
     {"algorithm": 88, "system_design": 62, "expression": 90, "code_quality": 85, "project_depth": 78}),
]


def seed_all(db: Session) -> None:
    if db.query(Position).count() == 0:
        for name, code, desc in POSITIONS:
            db.add(Position(name=name, code=code, description=desc))

    if db.query(SubscriptionPlan).count() == 0:
        for code, name, period, price, orig, desc, sort in PLANS:
            db.add(SubscriptionPlan(plan_code=code, name=name, period_type=period,
                                    price=price, original_price=orig, description=desc,
                                    status=1, sort=sort))

    if db.query(Question).count() == 0:
        for qtype, title, content, diff, ref, tags, cases in QUESTIONS:
            q = Question(question_type=qtype, title=title, content=content,
                         difficulty=diff, reference_answer=ref,
                         test_cases=cases, status=1)
            db.add(q)
            db.flush()
            for t in tags:
                db.add(QuestionTag(question_id=q.id, tag_name=t))

    # 演示账号 + 历史记录
    demo = db.query(User).filter(User.email == "demo@interview.cn").first()
    if not demo:
        demo = User(email="demo@interview.cn", phone="13800006688", nickname="张伟",
                    password_hash=hash_password("123456"), register_source="email",
                    status=1, last_login_at=datetime.now())
        db.add(demo)
        db.flush()

        backend = db.query(Position).filter(Position.code == "backend").first()
        for days_ago, score, comment, mix, dims in _HISTORY:
            created = datetime.now() - timedelta(days=days_ago)
            s = InterviewSession(
                user_id=demo.id, position_id=backend.id, difficulty=2,
                duration_min=45, question_mix=mix, status="completed",
                started_at=created, ended_at=created + timedelta(minutes=41),
                overall_score=score, overall_comment=comment, created_at=created)
            db.add(s)
            db.flush()
            for i, stype in enumerate(["voice", "coding", "whiteboard"]):
                db.add(SessionSection(session_id=s.id, section_type=stype,
                                      sequence_no=i + 1, status="completed",
                                      started_at=created, ended_at=created))
            db.add(SessionEvaluation(session_id=s.id, total_score=score,
                                     overall_comment=comment, eval_version="v1"))
            for dim, sc in dims.items():
                db.add(DimensionEvaluation(session_id=s.id, dimension=dim, score=sc))

    db.commit()


def snapshot_of(q: Question, tags: list[str]) -> str:
    return json.dumps({
        "id": q.id, "title": q.title, "content": q.content,
        "type": q.question_type, "difficulty": q.difficulty,
        "test_cases": q.test_cases or [], "tags": tags,
    }, ensure_ascii=False)
