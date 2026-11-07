"""AI 面试官引擎。

优先调用 DeepSeek 大模型（配置 DEEPSEEK_API_KEY 后启用）。
当未配置 key 或 DeepSeek 调用失败时，自动降级到本地规则引擎，保证可用性。
"""
import hashlib
import re
from collections import defaultdict

from . import llm

# ---------------------- 追问语料（本地 fallback） ----------------------
_FOLLOWUP_BANK = {
    "algorithm": [
        "你的解法时间复杂度和空间复杂度分别是多少？有没有更优的做法？",
        "如果输入规模扩大到千万级，你的方案会遇到什么瓶颈？如何优化？",
        "边界情况你是怎么考虑的？比如空输入、只有 1 个元素时程序会怎样？",
    ],
    "system_design": [
        "这个链路里如果缓存未命中，你会如何处理？如何保证缓存与数据库的一致性？",
        "如果某个核心组件宕机，系统的降级与容灾方案是什么？",
        "流量再增长 10 倍，你的架构要怎么演进？瓶颈最先出现在哪里？",
    ],
    "fundamental": [
        "能结合一个实际场景讲讲这个知识点是怎么落地的吗？",
        "它和同类方案相比，优缺点分别是什么？你会在什么场景下做取舍？",
        "如果让你从零实现一个简化版本，你会怎么设计？",
    ],
    "behavioral": [
        "这个过程中你和团队最大的分歧是什么？最后是怎么解决的？",
        "回头看这段经历，如果重来一次你会在哪些地方做得不一样？",
    ],
    "project_dig": [
        "这个项目里你个人贡献最大的难点是什么？说说你的解决过程和数据结果。",
        "项目上线后遇到过线上故障吗？当时是怎么定位和止损的？",
        "你提到的这个技术选型，当时有没有对比过其他方案？为什么最终选它？",
    ],
}

_SHORT_ANSWER_REPLIES = [
    "你的回答有点简短，能再具体展开一下吗？最好结合实际项目或数据来说明。",
    "我了解到的大概是这样，但我想听更深的细节——具体是怎么实现的？",
    "嗯，方向对了，不过面试中这样回答深度不够，可以补充一下原理或踩过的坑吗？",
]

_ACK_REPLIES = [
    "好的，回答得很清晰，这部分我就不继续追问了。",
    "嗯，逻辑是通的，这个点你掌握得不错。",
    "可以，看得出你对这块有实际经验。",
]


def _stable_score(seed: str, low: int, high: int) -> int:
    h = int(hashlib.md5(seed.encode("utf-8")).hexdigest(), 16)
    return low + h % (high - low + 1)


def _local_reply(question: dict, answer: str, followup_no: int = 0) -> dict:
    """本地规则引擎生成追问/点评。"""
    qtype = question.get("type") or question.get("question_type") or "fundamental"
    title = question.get("title", "")
    answer = (answer or "").strip()

    if len(answer) < 20:
        return {"reply": _SHORT_ANSWER_REPLIES[followup_no % len(_SHORT_ANSWER_REPLIES)],
                "is_followup": True}

    if followup_no == 0:
        bank = _FOLLOWUP_BANK.get(qtype, _FOLLOWUP_BANK["fundamental"])
        return {"reply": f"你刚才提到了「{title}」相关的内容。{bank[0]}", "is_followup": True}

    if followup_no == 1:
        bank = _FOLLOWUP_BANK.get(qtype, _FOLLOWUP_BANK["fundamental"])
        return {"reply": bank[1 % len(bank)], "is_followup": True}

    ack = _ACK_REPLIES[_stable_score(title, 0, len(_ACK_REPLIES) - 1)]
    return {"reply": f"{ack}我们来看下一个问题。", "is_followup": False}


def mock_reply(question: dict, answer: str, followup_no: int = 0,
               history: list[dict] | None = None) -> dict:
    """返回 {reply, is_followup}。

    优先走 DeepSeek；失败或未配置 key 时回退到本地规则引擎。
    """
    result = llm.interviewer_reply(question, answer, followup_no, history)
    if result and result.get("reply"):
        return result
    return _local_reply(question, answer, followup_no)


# ---------------------- 判题（本地模拟） ----------------------
def judge_code(question: dict, code: str) -> dict:
    """模拟判题：代码非空、长度达标、包含 return 视为通过。"""
    cases = question.get("test_cases") or []
    total = max(len(cases), 1)
    code = (code or "").strip()
    result_cases = []
    passed = 0

    if not code:
        for c in cases or [{"input": "-", "expected": "-"}]:
            result_cases.append({"input": c.get("input"), "expected": c.get("expected"),
                                 "actual": "无输出", "ok": False})
        return {"passed": 0, "total": total, "run_status": "error",
                "output": "编译错误：提交了空代码", "cases": result_cases}

    looks_valid = len(code) >= 30 and ("return" in code or "def " in code or "func" in code
                                       or "public" in code or "fn " in code)
    for i, c in enumerate(cases or [{"input": "-", "expected": "-"}]):
        ok = looks_valid and i < (total if looks_valid else max(1, total - 1))
        if looks_valid:
            ok = True
        result_cases.append({
            "input": c.get("input"), "expected": c.get("expected"),
            "actual": c.get("expected") if ok else "运行超时",
            "ok": ok,
        })
        if ok:
            passed += 1

    run_status = "success" if passed == total else ("error" if passed == 0 else "partial")
    output = f"运行完成：{passed}/{total} 个用例通过。"
    if passed == total:
        output += "代码正确，请口头讲解一下你的思路与复杂度分析。"
    elif passed == 0:
        output += "代码没有通过任何用例，请检查逻辑后重新提交。"
    return {"passed": passed, "total": total, "run_status": run_status,
            "output": output, "cases": result_cases}


# ---------------------- 整场评分 ----------------------
_DIM_NAMES = {
    "algorithm": "算法能力",
    "system_design": "系统设计",
    "expression": "表达能力",
    "code_quality": "代码质量",
    "project_depth": "项目深度",
}
_DIM_ORDER = ["algorithm", "system_design", "expression", "code_quality", "project_depth"]

# 题型 -> 对能力维度的影响权重（由后端确定性聚合，避免大模型乱打维度分）
_TYPE_DIM_WEIGHT = {
    "algorithm": {"algorithm": 0.55, "code_quality": 0.45},
    "coding": {"algorithm": 0.55, "code_quality": 0.45},
    "system_design": {"system_design": 0.6, "expression": 0.2, "project_depth": 0.2},
    "whiteboard": {"system_design": 0.6, "expression": 0.2, "project_depth": 0.2},
    "project_dig": {"project_depth": 0.6, "expression": 0.4},
    "behavioral": {"expression": 0.6, "project_depth": 0.4},
    "fundamental": {"expression": 0.5, "project_depth": 0.5},
}

# 常见无信息量字符（用于关键词命中判定时过滤 2 字 n-gram）
_STOP_CHARS = set("的了与和及在用时会把能被要是这也那还有其并对从为于而或所中")


def _dimension_feedback(name: str, score: int) -> str:
    if score >= 85:
        return f"{name}表现优秀，是本场面试的加分项，继续保持。"
    if score >= 70:
        return f"{name}处于中上水平，细节和深度还有提升空间。"
    return f"{name}相对薄弱，建议近期做专项练习补强。"


def _keyword_hit_count(reference: str, texts: list[str]) -> int:
    """参考答案要点命中数。

    将参考要点按标点切成若干要点短句，对每个短句提取 2/3 字 n-gram，
    候选回答中出现任一 n-gram 即认为谈到该要点。用于本地兜底评分。
    """
    if not reference or not texts:
        return 0
    joined = "".join(texts).replace(" ", "").replace("\n", "").replace("\u3000", "")
    if not joined:
        return 0
    segs = [s.strip().replace(" ", "").replace("\u3000", "")
            for s in re.split(r"[，。；、,.;:：!?！？()（）【】\[\]/\\\n]+", reference)]
    hit = 0
    for seg in segs:
        if len(seg) < 3:
            continue
        found = False
        # 先看 3-gram
        tri = {seg[i:i + 3] for i in range(len(seg) - 2)}
        if any(t in joined for t in tri):
            found = True
        if not found:
            bi = {seg[i:i + 2] for i in range(len(seg) - 1)
                  if not (any(ch in _STOP_CHARS for ch in seg[i:i + 2]))}
            if any(b in joined for b in bi):
                found = True
        if found:
            hit += 1
    return hit


def _candidate_texts(item: dict) -> list[str]:
    return [(t.get("content") or "").strip()
            for t in (item.get("turns") or []) if t.get("speaker") == "candidate"]


def _local_score_question(item: dict) -> int:
    """本地规则：按“作答情况 + 参考答案要点命中 + 追问补充 + 代码/白板证据”给每题打分。"""
    texts = [t for t in _candidate_texts(item) if t]
    joined = "".join(texts)

    # 编程题
    coding = item.get("coding")
    if coding:
        code = (coding.get("code") or "").strip()
        total = int(coding.get("total") or 0)
        passed = int(coding.get("passed") or 0)
        pr = passed / total if total else 0.0
        if not code:
            return 30  # 空代码
        has_logic = any(k in code for k in
                        ("def ", "class ", "return", "func ", "public",
                         "function", "=>", "for ", "while ", "if ", "int ", "var "))
        base = 40 + (int(pr * 40) if has_logic else int(pr * 20))
        if has_logic and pr >= 1:
            base += 8  # 一次通过
        if texts:  # 有口头讲解思路
            best = max(len(t) for t in texts)
            base += min(12, 3 + best // 60)
            base += _keyword_hit_count("复杂度 时间 空间 边界 优化 遍历 哈希 递归 指针", texts) * 2
        return min(100, max(30, base))

    # 系统设计/白板题
    wb = item.get("whiteboard")
    if wb:
        nodes = [str(n).strip() for n in (wb.get("nodes") or []) if str(n).strip()]
        edges = int(wb.get("edges") or 0)
        if not nodes:
            base = 30  # 白板空白
        else:
            key_kw = {"缓存", "数据库", "消息队列", "网关", "负载均衡", "微服务", "队列",
                      "分片", "主从", "降级", "限流", "监控", "CDN", "存储", "用户", "服务"}
            hit = len({n for n in nodes} & key_kw)
            base = 42 + min(24, hit * 4) + min(14, max(0, len(nodes) - 3) * 2) + min(10, edges * 2)
        if texts:
            best = max(len(t) for t in texts)
            base += min(20, 8 + best // 50)
            base += _keyword_hit_count("链路 瓶颈 缓存一致性 容量估算 降级 监控 容灾 高可用 演进", texts) * 2
        return min(100, max(30, base))

    # 语音/主观题
    if not texts:
        return 35  # 完全未作答
    longest = max(len(t) for t in texts)
    if longest < 4:
        return 35
    if longest < 15:
        return 45  # 只有一两句，无实质内容
    base = 50 + min(18, longest // 30)
    ref = item.get("reference_answer") or ""
    if ref:
        base += min(22, _keyword_hit_count(ref, texts) * 4)
    if len(texts) >= 2 and len(texts[-1]) >= 40:
        base += 6  # 追问后能有效补充
    if any(k in joined for k in ("首先", "其次", "最后", "第一", "第二", "一是", "整体是",
                                 "总体", "方案是", "可以分为", "我的做法")):
        base += 5  # 有结构感
    if ("不知道" in joined or "不会" in joined or "没学过" in joined) and longest < 60:
        base -= 15
    return min(100, max(35, base))


def _local_feedback_suggestion(item: dict, score: int) -> tuple[str, str]:
    """本地引擎为每题生成评价与建议（仅在无大模型时使用）。"""
    texts = [t for t in _candidate_texts(item) if t]
    coding = item.get("coding")
    wb = item.get("whiteboard")
    if score < 45:
        if coding and not (coding.get("code") or "").strip():
            return "未提交有效代码。", "先写出可运行的解题框架，再逐步完善逻辑。"
        if wb and not (wb.get("nodes") or []):
            return "白板为空，未展示设计思路。", "建议先画出核心组件（用户/网关/服务/存储）再讲链路。"
        return "未作答或回答过于简短，无法判断真实水平。", "即使不确定也请说出思路或相关概念，避免直接放弃。"
    if score >= 90:
        return "回答准确完整，覆盖关键要点，有深度与细节，表现优秀。", "继续保持，可进一步主动补充复杂度与权衡分析。"
    if score >= 78:
        return "回答要点基本到位、结构较清晰，但个别细节或深度还可加强。", "对照参考答案检查遗漏点，练习先给结论再展开。"
    if score >= 60:
        return "方向正确但偏浅，关键要点覆盖不全。", "用 STAR/要点分点的方式重组回答，补充原理与量化数据。"
    if not texts:
        return "作答极少，疑似卡壳。", "先答框架再补细节，训练面对未知问题时的兜底表达。"
    return "回答较薄弱，与题目核心要点有偏差。", "建议针对该考点做专项梳理并反复演练。"


def _aggregate_dimensions(items: list[dict], per_q: list[dict]) -> list[dict]:
    """把逐题得分按题型权重确定性聚合为能力维度分（只输出有题目证据的维度）。"""
    no2type = {it["no"]: it.get("type") or "fundamental" for it in items}
    acc: dict[str, float] = defaultdict(float)
    wsum: dict[str, float] = defaultdict(float)
    for ev in per_q:
        weights = _TYPE_DIM_WEIGHT.get(no2type.get(ev["no"], "fundamental"),
                                       _TYPE_DIM_WEIGHT["fundamental"])
        for dim, wt in weights.items():
            acc[dim] += float(ev["score"]) * wt
            wsum[dim] += wt
    dims = []
    for dim in _DIM_ORDER:
        if wsum.get(dim, 0) <= 0:
            continue  # 本场没有该维度的题目证据，不硬编分数
        score = max(0, min(100, round(acc[dim] / wsum[dim])))
        dims.append({"dimension": dim, "name": _DIM_NAMES[dim], "score": score,
                     "feedback": _dimension_feedback(_DIM_NAMES[dim], score)})
    return dims


def _local_overall_comment(items: list[dict], dims: list[dict]) -> str:
    """本地引擎生成总评。"""
    scores = [d["score"] for d in dims]
    total = round(sum(scores) / len(scores)) if scores else 0
    unanswered = 0
    for it in items:
        if it.get("coding") and not (it.get("coding") or {}).get("code"):
            unanswered += 1
        elif it.get("whiteboard") is not None and not (it.get("whiteboard") or {}).get("nodes"):
            unanswered += 1
        elif not _candidate_texts(it):
            unanswered += 1
    grade = "优秀" if total >= 88 else ("进阶" if total >= 75 else "扎实")
    parts = [f"综合 {total} 分，评级「{grade}」。"]
    strong = [d["name"] for d in dims if d["score"] >= 85]
    weak = [d["name"] for d in dims if d["score"] < 70]
    if strong:
        parts.append(f"优势在{'、'.join(strong)}，回答有内容有结构。")
    if weak:
        parts.append(f"短板在{'、'.join(weak)}，建议对照参考答案逐题复盘。")
    if unanswered:
        parts.append(f"本场有 {unanswered} 道题未作答或几乎未作答，是拉低总分的主要原因，务必重视。")
    if not strong and not weak and not unanswered:
        parts.append("整体发挥稳定，仍有提升空间。")
    parts.append("建议把每道题练到能脱离提示、按要点完整讲清的程度。")
    return "".join(parts)[:480]


def _normalize_items(items: list[dict]) -> list[dict]:
    """规整评分输入，保证字段齐全。"""
    out = []
    for i, it in enumerate(items or []):
        if not isinstance(it, dict):
            continue
        out.append({
            "no": int(it.get("no", i + 1)),
            "type": it.get("type") or it.get("section_type") or "fundamental",
            "title": it.get("title") or f"题目{it.get('no', i + 1)}",
            "content": it.get("content") or "",
            "difficulty": it.get("difficulty", 1),
            "tags": it.get("tags") or [],
            "reference_answer": it.get("reference_answer") or "",
            "turns": it.get("turns") or [],
            "coding": it.get("coding"),
            "whiteboard": it.get("whiteboard"),
        })
    return out


def evaluate(items: list[dict], coding_pass_rate: float | None = None,
             whiteboard_elements: int | None = None) -> dict:
    """整场评分（新入口）。

    items: 每题一个 dict，见 llm.evaluate_groups 说明。优先调用 DeepSeek 逐题评分，
    失败或无 key 时回退到本地内容评分；维度分由后端按题型权重确定性聚合。
    """
    items = _normalize_items(items)
    llm_result = llm.evaluate_groups(items, coding_pass_rate, whiteboard_elements)
    llm_map = {q["no"]: q for q in (llm_result or {}).get("question_scores", [])}

    per_q = []
    for it in items:
        ev = llm_map.get(it["no"])
        if ev:
            per_q.append({"no": it["no"], "title": it["title"], "type": it["type"],
                          "score": ev["score"], "feedback": ev["feedback"],
                          "suggestion": ev.get("suggestion", "")})
        else:
            score = _local_score_question(it)
            fb, sug = _local_feedback_suggestion(it, score)
            per_q.append({"no": it["no"], "title": it["title"], "type": it["type"],
                          "score": score, "feedback": fb, "suggestion": sug})

    dims = _aggregate_dimensions(items, per_q)
    total = round(sum(d["score"] for d in dims) / len(dims)) if dims else \
        round(sum(ev["score"] for ev in per_q) / max(len(per_q), 1))
    comment = ((llm_result or {}).get("overall_comment") or "").strip() or \
        _local_overall_comment(items, dims)

    question_evaluations = [
        {"title": ev["title"], "type": ev["type"], "score": ev["score"],
         "feedback": ev["feedback"], "suggestion": ev["suggestion"]}
        for ev in per_q
    ]
    return {"total_score": total, "overall_comment": comment[:490],
            "dimensions": dims, "question_evaluations": question_evaluations}


def evaluate_legacy(questions: list[dict], answers: list[str],
                    coding_pass_rate: float = 0.0,
                    whiteboard_elements: int = 0) -> dict:
    """旧入口兼容：把平铺 answers 按题目下标包装成 items 再评分（仅用于旧调用方兜底）。"""
    items = []
    for i, q in enumerate(questions):
        ans = answers[i] if i < len(answers) else ""
        items.append({
            "no": i + 1,
            "type": q.get("type") or q.get("question_type") or "fundamental",
            "title": q.get("title", ""),
            "content": q.get("content", ""),
            "difficulty": q.get("difficulty", 1),
            "tags": q.get("tags") or [],
            "reference_answer": q.get("reference_answer") or "",
            "turns": [{"speaker": "candidate", "content": ans}] if ans else [],
        })
    return evaluate(items, coding_pass_rate, whiteboard_elements)
