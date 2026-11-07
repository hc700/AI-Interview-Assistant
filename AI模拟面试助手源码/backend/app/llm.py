"""DeepSeek / OpenAI-compatible LLM 封装。

通过环境变量配置：
- DEEPSEEK_API_KEY：必填
- DEEPSEEK_BASE_URL：默认 https://api.deepseek.com
- DEEPSEEK_MODEL：默认 deepseek-chat

当未配置 API key 或调用失败时，调用方应回退到本地规则引擎。
"""
from __future__ import annotations

import json
import os
import re
from typing import Any

from . import config

try:
    from openai import OpenAI  # type: ignore
    _OPENAI_AVAILABLE = True
except Exception:  # 未安装 openai 时降级，不阻断整个服务
    OpenAI = None  # type: ignore
    _OPENAI_AVAILABLE = False

DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-chat"


def _get_client() -> OpenAI | None:
    """如果未配置 key 或未安装 openai 包，返回 None。"""
    key = config.DEEPSEEK_API_KEY
    if not key or not _OPENAI_AVAILABLE:
        return None
    return OpenAI(api_key=key, base_url=config.DEEPSEEK_BASE_URL or DEFAULT_BASE_URL)


def _extract_json(text: str) -> dict:
    """从可能包含 markdown 代码块或前后说明文字的文本中鲁棒地提取 JSON 对象。"""
    if not text:
        raise ValueError("empty response")
    text = text.strip()
    # 1) 去掉 ```json ... ``` / ``` 围栏
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if fence:
        text = fence.group(1).strip()
    # 2) 直接解析
    try:
        return json.loads(text)
    except Exception:
        pass
    # 3) 截取第一个 { 到最后一个 } 之间的内容再解析（容忍前后多余说明文字）
    start, end = text.find("{"), text.rfind("}")
    if 0 <= start < end:
        try:
            return json.loads(text[start:end + 1])
        except Exception:
            pass
    raise ValueError("no valid JSON found in response")


def _safe_chat(messages: list[dict], temperature: float = 0.7, max_tokens: int = 1024) -> str | None:
    client = _get_client()
    if not client:
        return None
    try:
        resp = client.chat.completions.create(
            model=config.DEEPSEEK_MODEL or DEFAULT_MODEL,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return resp.choices[0].message.content
    except Exception:
        # 调用失败时不抛异常，由调用方 fallback
        return None


def interviewer_reply(question: dict, answer: str, followup_no: int = 0,
                      history: list[dict] | None = None) -> dict | None:
    """让 DeepSeek 扮演面试官，根据考生回答生成追问或点评。

    返回 {"reply": str, "is_followup": bool}，失败返回 None。
    """
    title = question.get("title", "")
    content = question.get("content", "")
    qtype = question.get("type") or question.get("question_type") or "fundamental"
    answer = (answer or "").strip()
    history = history or []

    system_prompt = (
        "你是一名资深技术面试官，正在对候选人进行在线模拟面试。"
        "你的任务是针对当前问题听完候选人回答后，给出自然、专业、像真人面试官一样的回应。"
        "若候选人回答敷衍、过短（例如'不知道'、'不会'、'不太清楚'等），请温和地引导他尝试回答或展开思路；"
        "若候选人回答得不错，请基于回答内容继续深入追问一个相关细节。"
        "注意：追问必须紧扣候选人的回答内容，不要脱离上下文。"
    )

    messages = [{"role": "system", "content": system_prompt}]
    messages.append({
        "role": "user",
        "content": (
            f"当前题目类型：{qtype}\n题目：{title}\n题干：{content}\n\n"
            f"这是该题第 {followup_no + 1} 轮互动。"
        ),
    })
    for h in history:
        messages.append({"role": "assistant", "content": h.get("ai", "")})
        messages.append({"role": "user", "content": f"考生回答：{h.get('user', '')}"})
    messages.append({"role": "user", "content": f"考生最新回答：{answer}\n\n请按 JSON 格式返回：{{\"reply\": \"你要说的话\", \"is_followup\": true/false}}。is_followup=true 表示继续追问，false 表示结束本题。"})

    raw = _safe_chat(messages, temperature=0.7, max_tokens=512)
    if not raw:
        return None
    try:
        data = _extract_json(raw)
        return {
            "reply": data.get("reply", "").strip() or "能再详细说说吗？",
            "is_followup": bool(data.get("is_followup", False)),
        }
    except Exception:
        return None


_TYPE_LABELS = {
    "algorithm": "算法编程",
    "system_design": "系统设计",
    "fundamental": "技术基础",
    "behavioral": "行为面试",
    "project_dig": "项目深挖",
    "coding": "在线编程",
    "whiteboard": "白板系统设计",
}

_SCORE_RUBRIC = """评分必须严格基于「候选人实际说/写了什么」，并对照参考答案要点判断，禁止只看字数、禁止用模板分。
每题评分标准（0-100）：
- 90~100：内容准确，覆盖参考答案的大部分要点，条理清晰，有自己的深度思考或量化细节；
- 75~89：核心要点基本答出，方向正确，但深度、结构或个别细节不足；
- 60~74：方向大体正确但明显偏浅，遗漏关键点，或有部分错误表述；
- 40~59：严重偏题、关键点几乎未涉及、多处错误，或回答极其简短没有实质内容；
- 0~39：未作答、直接说“不知道/不会”且无任何展开、或完全跑题。
加分考虑：面试官追问后候选人能有效补充加深 → 在原基础上适当上调；反之，第一次回答尚可但追问后无法深入 → 适当下调。
对编程题：结合代码是否解决问题、逻辑/边界/复杂度与“思路讲解”质量综合评分（无需真实运行）。
对系统设计题：结合白板元素与结构、以及讲解是否覆盖链路/瓶颈/容错来评分。"""


def evaluate_groups(items: list[dict], coding_pass_rate: float | None = None,
                    whiteboard_elements: int | None = None) -> dict | None:
    """让 DeepSeek 对一场面试逐题打分（每道题附带完整题干、参考答案要点与多轮问答上下文）。

    items: 每题一个 dict：
        {no, type, title, content, difficulty, tags[], reference_answer, turns[], coding?, whiteboard?}
    返回 {"question_scores": [{"no","score","feedback","suggestion"}...], "overall_comment": str}
    失败返回 None（调用方回退本地引擎）。
    """
    # ---- 构造给模型的场景文本（控制体积，防止超长截断）----
    parts = []
    for it in items:
        qtype = it.get("type") or "fundamental"
        head = (f"第 {it.get('no')} 题 [{_TYPE_LABELS.get(qtype, qtype)}"
                f"/难度{it.get('difficulty', 1)}]：{it.get('title', '')}")
        parts.append(head)
        content = (it.get("content") or "").strip()
        if content:
            parts.append(f"题干：{content[:600]}")
        ref = (it.get("reference_answer") or "").strip()
        if ref:
            parts.append(f"参考答案要点：{ref[:400]}")
        # 对话轮次（candidate 与 interviewer 交替）
        turns = it.get("turns") or []
        if turns:
            parts.append("答题过程：")
            for t in turns[:10]:
                who = "考生回答" if t.get("speaker") == "candidate" else "面试官追问"
                parts.append(f"- {who}：{(t.get('content') or '')[:500]}")
        else:
            parts.append("答题过程：考生未作答。")
        # 编程信息
        coding = it.get("coding")
        if coding:
            code = (coding.get("code") or "")[:1500]
            parts.append(f"提交代码（{coding.get('language', '')}）：\n```\n{code}\n```")
            pr = coding.get("passed", 0) / max(coding.get("total", 1), 1)
            parts.append(f"用例判定：通过 {coding.get('passed', 0)}/{coding.get('total', 1)}")
        # 白板信息
        wb = it.get("whiteboard")
        if wb:
            nodes = wb.get("nodes") or []
            parts.append("白板结构：" + (" → ".join(str(n) for n in nodes[:14]) or "（空白）")
                         + f"（共 {len(nodes)} 个元素，{wb.get('edges', 0)} 条连线）")

    scene = "\n".join(parts)

    system_prompt = (
        "你是一名资深技术面试评分官。请根据以下面试场景中每一道题的「题干、参考答案要点、"
        "考生与面试官的完整问答过程」对每一题独立打分并给出评语。\n"
        + _SCORE_RUBRIC
    )

    json_schema = (
        "请只输出一个 JSON 对象，不要输出任何其他文字或 markdown：\n"
        "{\n"
        '  "question_scores": [\n'
        '    {"no": 题目序号, "score": 0-100整数, '
        '"feedback": "对这一题回答的针对性评价(40字内)", "suggestion": "具体可执行的改进建议(30字内)"}\n'
        "  ],\n"
        '  "overall_comment": "整场面试总体评语，指出最突出的优点与最需要改进的1-2点(80字内)"\n'
        "}"
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"{scene}\n\n{json_schema}"},
    ]

    max_tokens = 1400 + len(items) * 220
    raw = _safe_chat(messages, temperature=0.3, max_tokens=min(max_tokens, 6000))
    # 解析失败时重试一次（追加“只输出纯 JSON”的纠正指令）
    if raw:
        try:
            return _normalize_eval(_extract_json(raw), items)
        except Exception:
            messages.append({"role": "user", "content": "上次输出不是合法的纯 JSON。请只输出一个 JSON 对象本身，不要包含 ``` 或任何说明。"})
            raw2 = _safe_chat(messages, temperature=0.2, max_tokens=min(max_tokens, 6000))
            if raw2:
                try:
                    return _normalize_eval(_extract_json(raw2), items)
                except Exception:
                    return None
    return None


def _normalize_eval(data: dict, items: list[dict]) -> dict | None:
    """把模型输出规整为标准结构；缺题/非法分数字段剔除，由调用方补本地分。"""
    qs = []
    for ev in data.get("question_scores") or []:
        try:
            no = int(ev.get("no", 0))
            score = int(round(float(ev.get("score", 50))))
        except Exception:
            continue
        if no <= 0 or not any(it.get("no") == no for it in items):
            continue
        score = max(0, min(100, score))
        qs.append({
            "no": no,
            "score": score,
            "feedback": (ev.get("feedback") or "").strip()[:120] or "继续加油。",
            "suggestion": (ev.get("suggestion") or "").strip()[:100],
        })
    if not qs:
        return None
    return {
        "question_scores": qs,
        "overall_comment": (data.get("overall_comment") or "").strip()[:500],
    }


# ----- 兼容旧接口：questions + answers 平铺（尽量按序对应），新代码不再使用 -----
def evaluate_interview(questions: list[dict], answers: list[str],
                       coding_pass_rate: float = 0.0,
                       whiteboard_elements: int = 0) -> dict | None:
    items = []
    for i, q in enumerate(questions):
        items.append({
            "no": i + 1,
            "type": q.get("type") or q.get("question_type") or "fundamental",
            "title": q.get("title", ""),
            "content": q.get("content", ""),
            "difficulty": q.get("difficulty", 1),
            "tags": q.get("tags") or [],
            "reference_answer": q.get("reference_answer") or "",
            "turns": [{"speaker": "candidate",
                       "content": answers[i]}] if i < len(answers) and answers[i] else [],
        })
    return evaluate_groups(items, coding_pass_rate, whiteboard_elements)
