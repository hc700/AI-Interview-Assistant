# -*- coding: utf-8 -*-
"""端到端验证：/api/interview/evaluate 是否按题对齐、按内容评分（场景A优 vs 场景B差）"""
import json, urllib.request, sys

BASE = "http://127.0.0.1:8000/api/interview/evaluate"
Q = json.load(open("D:/cp/backend/sample_questions.json", encoding="utf-8"))
V = Q["voice"][0]; C = Q["coding"][0]; W = Q["whiteboard"][0]

def post(payload):
    req = urllib.request.Request(BASE, data=json.dumps(payload).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode("utf-8"))

def mk(voice_turns, coding_obj, wb_obj, pass_rate, wb_elems):
    questions = [V, C, W]
    qa_groups = [
        {"no": 1, "section_type": "voice", "turns": voice_turns},
        {"no": 2, "section_type": "coding", "turns": coding_obj["turns"], "coding": coding_obj["coding"]},
        {"no": 3, "section_type": "whiteboard", "turns": wb_obj["turns"], "whiteboard": wb_obj["whiteboard"]},
    ]
    return {"questions": questions, "qa_groups": qa_groups,
            "coding_pass_rate": pass_rate, "whiteboard_elements": wb_elems}

# ============ 场景 A：高质量、多轮流 + 完整代码 + 白板讲解 ============
A = mk(
    voice_turns=[
        {"speaker": "candidate", "content": "HashMap 底层是数组+链表结构，JDK8 之后链表长度超过 8 且数组长度超过 64 会转红黑树。put 流程：先算 key 的 hash，再 (n-1)&hash 定位桶下标，冲突就尾插挂链表。默认负载因子 0.75，size 超过 capacity*0.75 就扩容为 2 倍并重新 hash。"},
        {"speaker": "interviewer", "content": "追问：为什么负载因子取 0.75？扩容为什么是 2 倍？"},
        {"speaker": "candidate", "content": "0.75 是空间与时间的折中：泊松分布下桶内元素分布均匀，冲突概率低。容量取 2 的幂，(n-1)&hash 等价取模；扩容 2 倍后元素只可能留在原位或移到 原位置+oldCap，只需看高位新增的 bit 是 0 还是 1，无需重新计算全部 hash，rehash 高效。"},
    ],
    coding_obj={"turns": [{"speaker": "candidate", "content": "迭代法三指针 prev/cur/nxt 逐个反转，O(n) 时间 O(1) 空间；递归版 reverseList(head.next) 也能做，最后返回新头。"}],
                "coding": {"language": "python",
                           "code": "def reverseList(head):\n    prev, cur = None, head\n    while cur:\n        nxt = cur.next\n        cur.next = prev\n        prev = cur\n        cur = nxt\n    return prev",
                           "passed": 3, "total": 3, "output": "3/3 测试用例通过", "run_status": "success"}},
    wb_obj={"turns": [{"speaker": "candidate", "content": "网关先查 Redis 缓存，未命中走发号器生成短码，映射落 MySQL 分片；访问返回 302 便于统计；布隆过滤器挡穿透。"}],
            "whiteboard": {"nodes": ["客户端", "网关", "发号器", "Redis缓存", "MySQL分片", "302跳转"], "edges": 5,
                           "explanation": "客户端请求网关 -> 查 Redis 缓存，命中直接 302；未命中由发号器生成唯一短码并写 MySQL 分片；回源时用布隆过滤器拦截不存在 key，防止穿透数据库。"}},
    pass_rate=1.0, wb_elems=6,
)

# ============ 场景 B：不会 / 不知道 / 跳过（含空代码、无白板） ============
B = mk(
    voice_turns=[
        {"speaker": "candidate", "content": "这个 HashMap 底层原理我没深入研究过，不太清楚。"},
        {"speaker": "interviewer", "content": "那扩容机制了解吗？"},
        {"speaker": "candidate", "content": "不知道，没看过源码。"},
    ],
    coding_obj={"turns": [{"speaker": "candidate", "content": "反转链表我没写过，不会。"}],
                "coding": {"language": "python", "code": "", "passed": 0, "total": 3,
                           "output": "", "run_status": ""}},
    wb_obj={"turns": [{"speaker": "candidate", "content": "短链接系统没设计过，不会。"}],
            "whiteboard": {"nodes": [], "edges": 0, "explanation": ""}},
    pass_rate=0.0, wb_elems=0,
)

for name, payload in (("场景A-优质回答", A), ("场景B-不会/未作答", B)):
    print("=" * 70)
    print(f"[{name}] POST /api/interview/evaluate ...")
    try:
        r = post(payload)
        total = r.get("total_score")
        print("  total_score =", total)
        print("  overall_comment =", (r.get("overall_comment") or "")[:200])
        print("  dimensions:")
        for d in r.get("dimensions") or []:
            print(f"    - {d.get('name')}: {d.get('score')}  ({d.get('feedback') or ''})")
        print("  per-question:")
        for qs in r.get("question_scores") or []:
            fb = (qs.get("feedback") or "").replace("\n", " ")
            sg = (qs.get("suggestion") or "").replace("\n", " ")
            print(f"    Q{qs.get('no')} [{qs.get('score')}分] feedback: {fb[:120]}")
            if sg:
                print(f"         suggestion: {sg[:120]}")
    except Exception as e:
        print("  ERROR:", e)
    print()
