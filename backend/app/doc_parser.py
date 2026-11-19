"""Document parser: extract text from multiple formats (PDF/Word/Excel/PPT/TXT/MD/HTML/images)."""
import os
import re
from typing import Tuple


def _clean(text: str) -> str:
    """Normalize whitespace: collapse blank lines, trim trailing spaces."""
    lines = [ln.rstrip() for ln in text.splitlines()]
    out, blank = [], 0
    for ln in lines:
        if ln.strip() == "":
            blank += 1
            if blank > 1:
                continue
        else:
            blank = 0
        out.append(ln)
    return "\n".join(out).strip()


def parse_document(file_path: str, filename: str = "") -> Tuple[str, str]:
    """Return (extracted_text, format_label)."""
    name = (filename or os.path.basename(file_path)).lower()
    ext = os.path.splitext(name)[1]

    try:
        if ext == ".pdf":
            return _parse_pdf(file_path), "PDF"
        if ext in (".docx", ".doc"):
            return _parse_docx(file_path), "Word"
        if ext in (".xlsx", ".xls"):
            return _parse_excel(file_path), "Excel"
        if ext in (".pptx", ".ppt"):
            return _parse_pptx(file_path), "PPT"
        if ext in (".txt", ".md", ".markdown", ".csv", ".json", ".log", ".yaml", ".yml", ".xml", ".ini", ".sql"):
            return _parse_text(file_path), ext.lstrip(".").upper()
        if ext in (".html", ".htm"):
            return _parse_html(file_path), "HTML"
        if ext in (".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp", ".tiff"):
            return _parse_image(file_path), "图片(OCR)"
        # fallback: try plain text
        return _parse_text(file_path), ext.lstrip(".").upper() or "文本"
    except Exception as e:
        raise RuntimeError(f"文档解析失败（{ext}）: {e}")


def _parse_pdf(path: str) -> str:
    import fitz  # PyMuPDF
    doc = fitz.open(path)
    parts = []
    for i, page in enumerate(doc):
        text = page.get_text("text")
        if text.strip():
            parts.append(f"【第{i+1}页】\n{text}")
    doc.close()
    if not parts:
        raise RuntimeError("PDF 无可提取文本（可能是扫描件，请转为图片上传使用 OCR）")
    return _clean("\n\n".join(parts))


def _parse_docx(path: str) -> str:
    from docx import Document
    doc = Document(path)
    parts = []
    for p in doc.paragraphs:
        if p.text.strip():
            parts.append(p.text)
    for ti, table in enumerate(doc.tables):
        parts.append(f"\n【表格{ti+1}】")
        for row in table.rows:
            parts.append(" | ".join(cell.text.strip() for cell in row.cells))
    return _clean("\n".join(parts))


def _parse_excel(path: str) -> str:
    import openpyxl
    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    parts = []
    for ws in wb.worksheets:
        parts.append(f"【工作表: {ws.title}】")
        for row in ws.iter_rows(values_only=True):
            cells = [str(c) for c in row if c is not None]
            if cells:
                parts.append(" | ".join(cells))
    wb.close()
    return _clean("\n".join(parts))


def _parse_pptx(path: str) -> str:
    from pptx import Presentation
    prs = Presentation(path)
    parts = []
    for i, slide in enumerate(prs.slides):
        parts.append(f"【第{i+1}页】")
        for shape in slide.shapes:
            if shape.has_text_frame:
                for p in shape.text_frame.paragraphs:
                    if p.text.strip():
                        parts.append(p.text)
            if shape.has_table:
                for row in shape.table.rows:
                    parts.append(" | ".join(c.text.strip() for c in row.cells))
    return _clean("\n".join(parts))


def _parse_text(path: str) -> str:
    for enc in ("utf-8", "gbk", "gb18030", "utf-16", "latin-1"):
        try:
            with open(path, "r", encoding=enc) as f:
                return _clean(f.read())
        except (UnicodeDecodeError, UnicodeError):
            continue
    with open(path, "rb") as f:
        return f.read().decode("utf-8", errors="ignore")


def _parse_html(path: str) -> str:
    from bs4 import BeautifulSoup
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        soup = BeautifulSoup(f.read(), "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()
    return _clean(soup.get_text("\n"))


def _parse_image(path: str) -> str:
    """OCR for images. Uses pytesseract if available, else PIL-based hint."""
    try:
        import pytesseract
        from PIL import Image
        img = Image.open(path)
        text = pytesseract.image_to_string(img, lang="chi_sim+eng")
        if text.strip():
            return _clean(text)
    except Exception:
        pass
    raise RuntimeError("图片 OCR 不可用（未安装 tesseract）。建议安装 tesseract 或改用文本类文档。")


def extract_requirement_points(text: str, max_points: int = 40) -> list:
    """Heuristically extract requirement items from text: headings, numbered lists, feature keywords."""
    lines = text.splitlines()
    points = []
    for ln in lines:
        s = ln.strip()
        if not s or len(s) < 4:
            continue
        # keep lines that look like requirement statements
        if re.match(r"^(\d+[\.、\)）]|第[一二三四五六七八九十]+[章节条]|[-•*]|[（(]\d+[）)])", s) or \
           any(k in s for k in ["需求", "功能", "支持", "应该", "需要", "可以", "系统", "用户", "当", "如果", "则", "必须", "规则", "限制", "校验", "返回", "显示", "提示"]):
            points.append(s[:300])
        if len(points) >= max_points:
            break
    if not points:
        # fallback: first non-empty lines
        points = [ln.strip()[:300] for ln in lines if ln.strip()][:max_points]
    return points
