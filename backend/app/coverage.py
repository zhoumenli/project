"""Requirement coverage analysis: map requirement points to existing test cases.

Approach (no external NLP deps):
1. Split requirement text into points (reuse doc_parser.extract_requirement_points).
2. For each point, tokenize into terms (Chinese bigrams + ASCII words), drop generic words.
3. Score every case by term overlap + API-path bonus; a case "covers" a point when
   similarity passes threshold or the point declares the case's API path.
4. Report per-point matrix + summary (coverage %, uncovered points, orphan cases).
"""
import re
from typing import List, Dict

from .doc_parser import extract_requirement_points

# 泛化词：出现在几乎所有需求/用例里，参与匹配只会稀释相似度
GENERIC = {"系统", "功能", "测试", "用例", "支持", "需要", "应该", "必须",
           "用户", "相关", "模块", "信息", "数据", "情况", "操作", "界面", "页面"}

# 相似度阈值：术语重合率(相对需求点词数)达到该值即视为覆盖
COVER_THRESHOLD = 0.28
# 接口路径命中加成
URL_BONUS = 0.45


def _terms(text: str) -> set:
    """Tokenize mixed CN/EN text: Chinese bigrams (+short segs) + ASCII tokens."""
    zh_segs = re.findall(r"[\u4e00-\u9fff]+", text or "")
    grams = set()
    for seg in zh_segs:
        if len(seg) <= 2:
            grams.add(seg)
        else:
            for i in range(len(seg) - 1):
                grams.add(seg[i:i + 2])
    grams |= set(re.findall(r"[a-z_][a-z0-9_./-]{2,}", (text or "").lower()))
    return {g for g in grams if g not in GENERIC}


def _point_urls(point: str) -> List[str]:
    """API paths declared inside a requirement point (e.g. POST /api/login)."""
    urls = re.findall(r"/[A-Za-z0-9_\-/]+", point or "")
    return [u.rstrip("/").lower() for u in urls if len(u) > 3]


def _case_terms(c: dict) -> set:
    parts = [c.get("title", ""), c.get("precondition", ""), c.get("steps", ""),
             c.get("expected", ""), c.get("url", "")]
    for t in (c.get("tags") or []):
        parts.append(str(t))
    return _terms(" ".join(str(p) for p in parts if p))


def analyze(text: str, cases: List[dict]) -> dict:
    """Analyze requirement text against case dicts (case-center fields)."""
    points = extract_requirement_points(text)
    if not points:
        points = [ln.strip()[:300] for ln in (text or "").splitlines() if ln.strip()][:20]
    if not points:
        return {"requirement_points": [], "summary": {
            "points": 0, "covered": 0, "coverage": 0,
            "cases_total": len(cases), "matched_cases": 0, "orphan_cases": []}}

    prepared = []
    for c in cases:
        cu = (c.get("url") or "").split("?")[0].rstrip("/").lower()
        prepared.append({
            "id": c.get("id"), "title": c.get("title", ""), "priority": c.get("priority", ""),
            "case_type": c.get("case_type", ""), "url": c.get("url", ""), "cu": cu,
            "terms": _case_terms(c),
        })

    matrix = []
    matched_case_ids = set()
    for i, pt in enumerate(points, 1):
        pt_terms = _terms(pt)
        pt_urls = _point_urls(pt)
        matches = []
        for c in prepared:
            overlap = pt_terms & c["terms"]
            score = (len(overlap) / max(1, len(pt_terms))) + (
                URL_BONUS if pt_urls and c["cu"] and any(c["cu"].endswith(u) or u.endswith(c["cu"]) for u in pt_urls) else 0.0)
            if score >= COVER_THRESHOLD:
                matches.append({"id": c["id"], "title": c["title"], "priority": c["priority"],
                                "case_type": c["case_type"], "score": round(min(score, 1.5), 2)})
        matches.sort(key=lambda m: -m["score"])
        top = matches[:6]
        for m in top:
            matched_case_ids.add(m["id"])
        matrix.append({
            "index": i, "text": pt, "covered": bool(matches),
            "best_score": top[0]["score"] if top else 0,
            "case_count": len(matches), "matched": top,
        })

    covered_n = sum(1 for m in matrix if m["covered"])
    orphans = [{"id": c["id"], "title": c["title"], "case_type": c["case_type"]}
               for c in prepared if c["id"] not in matched_case_ids]
    return {
        "requirement_points": matrix,
        "summary": {
            "points": len(matrix),
            "covered": covered_n,
            "coverage": round(covered_n / len(matrix) * 100, 1) if matrix else 0,
            "cases_total": len(prepared),
            "matched_cases": len(matched_case_ids),
            "orphan_cases": orphans,
        },
    }
