# -*- coding: utf-8 -*-
"""简历解析：从 PDF / DOCX / PPT(X) / TXT 中提取文本、摘要与技术栈关键词。"""
from __future__ import annotations

import io
import os
import re
from typing import Any


def _to_text(raw: bytes) -> str:
    """尽量按 utf-8 解码，失败则使用 latin-1 兜底（不会抛异常）。"""
    for enc in ("utf-8", "gbk", "gb18030", "utf-16", "latin-1"):
        try:
            return raw.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return raw.decode("utf-8", errors="ignore")


def extract_pdf_text(data: bytes) -> str:
    try:
        from pypdf import PdfReader
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("缺少 PDF 解析依赖，请执行：pip install pypdf") from exc
    try:
        reader = PdfReader(io.BytesIO(data))
    except Exception:
        # 文件损坏或不是合法 PDF（可能是后缀伪装）
        return ""
    parts = []
    for page in reader.pages:
        try:
            txt = page.extract_text() or ""
        except Exception:
            txt = ""
        parts.append(txt)
    return "\n".join(parts)


def extract_docx_text(data: bytes) -> str:
    try:
        from docx import Document
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("缺少 Word 解析依赖，请执行：pip install python-docx") from exc
    try:
        doc = Document(io.BytesIO(data))
    except Exception:
        return ""
    parts = [p.text for p in doc.paragraphs if p.text]
    # 也读表格中的文字
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                if cell.text:
                    parts.append(cell.text)
    return "\n".join(parts)


def _pptx_shape_texts(shape) -> list[str]:
    """递归收集一个 shape（含组合形状）内的全部文本。"""
    texts: list[str] = []
    try:
        if shape.shape_type == 6:  # GROUP
            for sub in shape.shapes:
                texts.extend(_pptx_shape_texts(sub))
            return texts
    except Exception:
        pass
    if getattr(shape, "has_text_frame", False):
        for para in shape.text_frame.paragraphs:
            line = "".join(run.text for run in para.runs).strip()
            if line:
                texts.append(line)
    if getattr(shape, "has_table", False):
        for row in shape.table.rows:
            for cell in row.cells:
                txt = (cell.text or "").strip()
                if txt:
                    texts.append(txt)
    return texts


def extract_pptx_text(data: bytes) -> str:
    """解析 .pptx（Office Open XML 格式，python-pptx 支持）。"""
    try:
        from pptx import Presentation
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("缺少 PPT 解析依赖，请执行：pip install python-pptx") from exc
    try:
        prs = Presentation(io.BytesIO(data))
    except Exception:
        # 文件损坏或后缀伪装（如 .ppt 改名成 .pptx）
        return ""
    parts: list[str] = []
    for slide in prs.slides:
        for shape in slide.shapes:
            parts.extend(_pptx_shape_texts(shape))
        # 备注页文字也纳入（简历 PPT 常把说明写进备注）
        try:
            if slide.has_notes_slide and slide.notes_slide.notes_text_frame:
                note = (slide.notes_slide.notes_text_frame.text or "").strip()
                if note:
                    parts.append(note)
        except Exception:
            pass
    return "\n".join(parts)


def _extract_ppt_binary_text(data: bytes) -> str:
    """.ppt（PowerPoint 97-2003 二进制格式）兜底提取：扫描 UTF-16LE / ASCII 文本流。"""
    texts: list[str] = []
    # 1) UTF-16LE 连续可打印段（中文与常见符号在二进制 ppt 中按 UTF-16 存储）
    run_chars: list[str] = []
    i = 0
    n = len(data)
    while i + 1 < n:
        code = data[i] | (data[i + 1] << 8)
        ch = chr(code)
        ok = (0x4e00 <= code <= 0x9fff) or (0x20 <= code < 0x7f and ch.isprintable()) or code in (0x2018, 0x2019, 0x201c, 0x201d, 0x3001, 0x3002, 0xff08, 0xff09, 0x2014, 0x2026)
        if ok:
            run_chars.append(ch)
            i += 2
        else:
            if len(run_chars) >= 4:  # 过滤太短的噪声段
                texts.append("".join(run_chars))
            run_chars = []
            i += 2
    if len(run_chars) >= 4:
        texts.append("".join(run_chars))
    # 2) ASCII 连续段兜底（有些老文件用单字节存储）
    for m in re.finditer(rb"[\x20-\x7e]{8,}", data):
        seg = m.group().decode("ascii", errors="ignore")
        # 过滤明显的二进制/路径噪声
        if not re.search(r"[a-zA-Z]{3}", seg):
            continue
        if any(x in seg.lower() for x in ("microsoft", "powerpoint", "root entry", "\\office", "current user")):
            continue
        texts.append(seg)
    combined = "\n".join(texts)
    # 若提取量太少，视为失败（避免拿噪声当简历内容）
    return combined if len(re.sub(r"\s", "", combined)) >= 20 else ""


def extract_text(data: bytes, filename: str | None = None) -> str:
    """根据文件名后缀选择解析器，统一返回纯文本。"""
    ext = os.path.splitext(filename or "")[1].lower()
    if ext == ".pdf":
        return extract_pdf_text(data)
    if ext in (".docx", ".doc"):
        return extract_docx_text(data)
    if ext == ".pptx":
        return extract_pptx_text(data)
    if ext == ".ppt":
        # 老二进制格式：python-pptx 不支持，走 UTF-16 扫描兜底
        return _extract_ppt_binary_text(data)
    # 其余按纯文本处理
    return _to_text(data)


# 技术栈关键词库：语言 / 框架 / 数据库 / 中间件 / 云原生 / AI / 工具 / 软技能方向
_TECH_KEYWORDS: list[tuple[str, list[str]]] = [
    ("Python", ["python", "django", "flask", "fastapi", "tornado", "celery"]),
    ("Java", ["java", "spring", "springboot", "spring boot", "springcloud", "spring cloud", "mybatis", "hibernate", "maven", "gradle"]),
    ("Go", ["golang", "go 语言", "gin", "beego"]),
    ("C++", ["c++", "cpp", "c/c++", "qt"]),
    ("C", [" c 语言", "嵌入式 c", " c 开发", " c 程序"]),
    ("JavaScript", ["javascript", "js", "es6", "typescript", "ts", "nodejs", "node.js", "vue", "vue.js", "react", "react.js", "angular", "webpack", "vite", "next.js", "nuxt"]),
    ("前端", ["前端", "html", "css", "h5", "小程序", "uni-app", "flutter"]),
    ("PHP", ["php", "laravel", "thinkphp"]),
    ("Rust", ["rust"]),
    ("算法", ["算法", "数据结构", "leetcode", "机器学习", "深度学习", "tensorflow", "pytorch", "sklearn", "推荐算法", "nlp", "cv", "计算机视觉"]),
    ("MySQL", ["mysql", "sql", "innodb"]),
    ("PostgreSQL", ["postgresql", "postgres"]),
    ("Redis", ["redis", "缓存"]),
    ("MongoDB", ["mongodb", "mongo"]),
    ("Elasticsearch", ["elasticsearch", "es", "elastic search", "搜索引擎"]),
    ("Kafka", ["kafka"]),
    ("RabbitMQ", ["rabbitmq"]),
    ("RocketMQ", ["rocketmq"]),
    ("消息队列", ["消息队列", "mq"]),
    ("Docker", ["docker", "容器化"]),
    ("Kubernetes", ["kubernetes", "k8s"]),
    ("微服务", ["微服务", "服务治理", "dubbo", "grpc", "rpc"]),
    ("高并发", ["高并发", "并发编程", "多线程", "异步", "性能优化", "qps", "tps", "负载均衡"]),
    ("Linux", ["linux", "unix", "shell", "bash"]),
    ("Git", ["git", "github", "gitlab"]),
    ("DevOps", ["devops", "ci/cd", "jenkins", "github actions", "gitlab ci"]),
    ("大数据", ["hadoop", "spark", "flink", "hive", "hbase", "kafka", "etl", "数仓", "数据仓库", "大数据"]),
    ("测试", ["测试", "单元测试", "自动化测试", "selenium", "pytest", "junit", "postman", "接口测试"]),
    ("AI", ["大模型", "llm", "prompt", "chatgpt", "openai", "langchain", "rag", "agent", "多模态"]),
]

# 扁平化：alias -> canonical
_ALIAS_MAP: dict[str, str] = {}
for canonical, aliases in _TECH_KEYWORDS:
    for alias in aliases:
        _ALIAS_MAP[alias.lower()] = canonical


def extract_tech_tags(text: str, top_k: int = 8) -> list[str]:
    """按命中频率与词长排序，返回技术栈标签列表。"""
    text_lower = text.lower()
    # 先统计每个 alias 命中次数
    counter: dict[str, int] = {}
    for alias, canonical in _ALIAS_MAP.items():
        # 使用单词边界，避免把 "c" 当成 c 语言；同时支持中文无需边界
        escaped = re.escape(alias)
        # 若 alias 含中文，用固定字符串查找；否则加前后非词字符边界
        if any("\u4e00" <= ch <= "\u9fff" for ch in alias):
            count = text_lower.count(alias)
        else:
            count = len(re.findall(rf"(?<![a-z0-9_.]){escaped}(?![a-z0-9_.])", text_lower))
        if count:
            counter[canonical] = counter.get(canonical, 0) + count

    if not counter:
        return []

    # 按命中次数降序；次数相同按标签长度升序（更具体的词优先）
    sorted_tags = sorted(counter.items(), key=lambda x: (-x[1], -len(x[0])))
    # 最多 top_k 个；过滤掉过于宽泛且次数少的？这里不过滤，保持真实
    return [tag for tag, _ in sorted_tags[:top_k]]


def make_summary(text: str, max_len: int = 300) -> str:
    """清理文本并取前 max_len 字符作为摘要。"""
    # 去除多余空白、换行、制表符
    cleaned = re.sub(r"[\s]+", " ", text).strip()
    if len(cleaned) <= max_len:
        return cleaned
    return cleaned[:max_len].rstrip() + "…"


def parse_resume(data: bytes, filename: str | None = None) -> dict[str, Any]:
    """
    统一入口。返回 dict:
    {
        "file_name": str,
        "summary": str,
        "tech_tags": list[str],
        "word_count": int,
    }
    """
    text = extract_text(data, filename) if data else ""
    summary = make_summary(text)
    tags = extract_tech_tags(text)
    # 若一个词都没命中，可能是文本为空或非常规简历
    if not tags:
        if summary.strip():
            tags = ["通用"]
        else:
            tags = ["未识别到有效文本"]
    return {
        "file_name": os.path.basename(filename or "简历"),
        "summary": summary,
        "tech_tags": tags,
        "word_count": len(re.findall(r"\b\w+\b", text)) + len(re.findall(r"[\u4e00-\u9fff]", text)),
    }
