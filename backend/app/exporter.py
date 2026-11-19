"""Export generated test cases to multiple file formats."""
import io
import csv
import json
from typing import List, Dict, Tuple

FORMATS = {
    "xlsx": ("Excel (.xlsx)", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
    "docx": ("Word (.docx)", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
    "md": ("Markdown (.md)", "text/markdown"),
    "csv": ("CSV (.csv)", "text/csv"),
    "json": ("JSON (.json)", "application/json"),
    "txt": ("纯文本 (.txt)", "text/plain"),
    "html": ("HTML (.html)", "text/html"),
}

COLUMNS_ZH = ["编号", "标题", "维度", "优先级", "类型", "前置条件", "步骤", "预期结果", "标签", "风险"]
COLUMNS_EN = ["No", "Title", "Dimension", "Priority", "Type", "Precondition", "Steps", "Expected", "Tags", "Risk"]
KEYS = ["no", "title", "dimension_disp", "priority", "case_type_disp",
        "precondition", "steps", "expected", "tags_disp", "risk"]


def _rows(cases: List[dict], lang: str):
    sep = "、" if lang == "zh" else ", "
    rows = []
    for c in cases:
        row = []
        for k in KEYS:
            v = c.get(k, "")
            if isinstance(v, list):
                v = sep.join(str(x) for x in v)
            row.append(v if v is not None else "")
        rows.append(row)
    return rows


def _columns(lang: str):
    return COLUMNS_ZH if lang == "zh" else COLUMNS_EN


def export_cases(cases: List[dict], fmt: str, doc_name: str, lang: str = "zh") -> Tuple[bytes, str, str]:
    """Return (bytes, filename, content_type) for the requested format."""
    fmt = (fmt or "xlsx").lower()
    if fmt not in FORMATS:
        raise ValueError(f"不支持的导出格式: {fmt}")
    label, content_type = FORMATS[fmt]
    safe_name = "".join(ch for ch in (doc_name or "cases") if ch not in '\\/:*?"<>|').strip() or "cases"
    rows = _rows(cases, lang)
    cols = _columns(lang)

    if fmt == "xlsx":
        from openpyxl import Workbook
        from openpyxl.styles import Font, Alignment, PatternFill
        wb = Workbook()
        ws = wb.active
        ws.title = "测试用例"
        ws.append(cols)
        for cell in ws[1]:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor="4472C4")
            cell.alignment = Alignment(vertical="center")
        for r in rows:
            ws.append(r)
        widths = [8, 36, 20, 10, 10, 28, 48, 44, 20, 30]
        for i, w in enumerate(widths, 1):
            ws.column_dimensions[chr(64 + i)].width = w
        for row in ws.iter_rows(min_row=2):
            for cell in row:
                cell.alignment = Alignment(wrap_text=True, vertical="top")
        ws.freeze_panes = "A2"
        buf = io.BytesIO()
        wb.save(buf)
        return buf.getvalue(), f"{safe_name}.xlsx", content_type

    if fmt == "docx":
        from docx import Document
        from docx.shared import Pt
        doc = Document()
        doc.add_heading((doc_name or "测试用例") + (" - Test Cases" if lang == "en" else " - 测试用例"), level=0)
        for c in cases:
            doc.add_heading(f"{c.get('no', '')}. {c.get('title', '')}", level=2)
            for col, key in zip(cols[1:], KEYS[1:]):
                v = c.get(key, "")
                if isinstance(v, list):
                    v = ", ".join(str(x) for x in v)
                p = doc.add_paragraph()
                run = p.add_run(f"{col}: ")
                run.bold = True
                p.add_run(str(v if v is not None else ""))
            if c.get("formatted"):
                p = doc.add_paragraph()
                run = p.add_run(("模板输出:" if lang == "zh" else "Formatted:"))
                run.bold = True
                doc.add_paragraph(c["formatted"])
            doc.add_paragraph()
        buf = io.BytesIO()
        doc.save(buf)
        return buf.getvalue(), f"{safe_name}.docx", content_type

    if fmt == "csv":
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(cols)
        w.writerows(rows)
        return ("\ufeff" + buf.getvalue()).encode("utf-8"), f"{safe_name}.csv", content_type

    if fmt == "json":
        return json.dumps(cases, ensure_ascii=False, indent=2).encode("utf-8"), f"{safe_name}.json", content_type

    if fmt == "md":
        lines = [f"# {doc_name or '测试用例'}", ""]
        header = "| " + " | ".join(cols) + " |"
        lines.append(header)
        lines.append("| " + " | ".join(["---"] * len(cols)) + " |")
        for r in rows:
            cells = [str(x).replace("|", "\\|").replace("\n", "<br>") for x in r]
            lines.append("| " + " | ".join(cells) + " |")
        lines.append("")
        lines.append(("## 模板输出详情" if lang == "zh" else "## Formatted Details"))
        lines.append("")
        for c in cases:
            lines.append(f"### {c.get('no','')}. {c.get('title','')}")
            lines.append("")
            lines.append("```text")
            lines.append(c.get("formatted", ""))
            lines.append("```")
            lines.append("")
        return "\n".join(lines).encode("utf-8"), f"{safe_name}.md", content_type

    if fmt == "txt":
        blocks = []
        for c in cases:
            blocks.append(c.get("formatted", "") or "")
        return ("\n" + "=" * 60 + "\n").join(blocks).encode("utf-8"), f"{safe_name}.txt", content_type

    if fmt == "html":
        import html as html_mod
        thead = "".join(f"<th>{html_mod.escape(c)}</th>" for c in cols)
        body_rows = ""
        for r in rows:
            cells = "".join(f"<td>{html_mod.escape(str(x)).replace(chr(10), '<br>')}</td>" for x in r)
            body_rows += f"<tr>{cells}</tr>"
        doc = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>{html_mod.escape(doc_name or '测试用例')}</title>
<style>body{{font-family:Arial,'Microsoft YaHei',sans-serif;margin:24px;color:#222}}table{{border-collapse:collapse;width:100%;font-size:13px}}th,td{{border:1px solid #d0d5dd;padding:8px;vertical-align:top}}th{{background:#4472C4;color:#fff}}tr:nth-child(even){{background:#fafbfc}}h1{{font-size:20px}}</style></head>
<body><h1>{html_mod.escape(doc_name or '测试用例')}</h1><table><thead><tr>{thead}</tr></thead><tbody>{body_rows}</tbody></table></body></html>"""
        return doc.encode("utf-8"), f"{safe_name}.html", content_type

    raise ValueError(f"不支持的导出格式: {fmt}")
