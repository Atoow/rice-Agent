"""
IRRI Rice Knowledge Bank 完整抓取脚本

执照: CC BY-NC-SA 3.0 (Creative Commons)

数据源:
1. Pest management fact sheets (65篇病虫害)
2. Rice Doctor fact sheets (~100篇营养/毒性)
3. PDF 公开文档

输出: data/irri/*.json
"""

import json
import os
import re
import time
import urllib.request
import urllib.error
from pathlib import Path
from urllib.parse import urljoin
from html import unescape

# ── Config ───────────────────────────────────────────

OUTPUT_DIR = Path(__file__).parent.parent / "data" / "irri"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
DELAY = 1.5
UA = "Mozilla/5.0 (Rice-Agent Academic Research)"

# ── HTTP Helpers ──────────────────────────────────────

def _get(url: str, max_retries: int = 3) -> str | None:
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=20) as r:
                return r.read().decode("utf-8", errors="replace")
        except Exception as e:
            print(f"  [retry {attempt + 1}] {e}")
            time.sleep(DELAY * 2)
    return None

def _download_file(url: str, path: Path) -> bool:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=60) as r:
            path.write_bytes(r.read())
        return True
    except Exception as e:
        print(f"  ✗ 下载失败: {e}")
        return False

# ── HTML Parsers ──────────────────────────────────────

def _strip_tags(html: str) -> str:
    text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
    text = re.sub(r'<[^>]+>', '\n', text)
    text = unescape(text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

def _extract_category_items(html: str, base_url: str) -> list[dict]:
    """从分类页提取所有 item 链接 (class='pos-title' 中的 a 标签)."""
    items = []
    pattern = re.compile(
        r'class="pos-title">\s*<a\s+(?:title="[^"]*"\s+)?href="([^"]+)"[^>]*>(.*?)</a>',
        re.DOTALL | re.IGNORECASE,
    )
    for m in pattern.finditer(html):
        href = m.group(1).strip()
        title = re.sub(r'<[^>]+>', '', m.group(2)).strip()
        items.append({"title": title, "url": urljoin(base_url, href)})
    return items

def _extract_pagination(html: str, base_url: str) -> list[str]:
    """从分页栏提取其他页码 URL."""
    pages = []
    m = re.search(r'<div\s+class="zoo-pagination">(.*?)</div>', html, re.DOTALL)
    if m:
        for a in re.finditer(r'<a\s+href="([^"]+)"[^>]*>\s*\d+\s*</a>', m.group(1)):
            pages.append(urljoin(base_url, a.group(1)))
    # 去重并排序
    return sorted(set(pages))

def _parse_fact_sheet(html: str, url: str) -> dict:
    """解析单篇 fact sheet 内容."""
    data = {"url": url, "title": "", "content": "", "sections": {}}

    # ─ 标题
    m = re.search(r'<h1\s+class="title">(.*?)</h1>', html, re.DOTALL)
    if m:
        data["title"] = unescape(re.sub(r'<[^>]+>', '', m.group(1)).strip())

    # ─ 提取 h2 及其后的文本段落
    h2s = list(re.finditer(r'<h2[^>]*>(.*?)</h2>', html, re.DOTALL))

    content_parts = []

    # 第一个 h2 之前的引言文本
    if h2s:
        intro_text = html[: h2s[0].start()]
        intro_text = _strip_tags(intro_text)
        if len(intro_text) > 30:
            content_parts.append(intro_text)

    for i, h2 in enumerate(h2s):
        heading = _strip_tags(h2.group(1))
        start = h2.end()
        end = h2s[i + 1].start() if i + 1 < len(h2s) else len(html)
        body = html[start:end]
        text = _strip_tags(body)

        # 过滤尾部杂物
        cut = text.find("IRRI Technologies")
        if cut > 0:
            text = text[:cut]
        cut = text.find("Popular Items")
        if cut > 0:
            text = text[:cut]
        text = text.strip()

        if len(text) > 15:
            content_parts.append(f"## {heading}\n{text}")
            data["sections"][heading] = text

    data["content"] = "\n\n".join(content_parts)
    return data

# ── Scraper ───────────────────────────────────────────

def scrape_with_subcategories(
    label: str,
    start_url: str,
    output_name: str,
    suburls: list[str] | None = None,
):
    """抓取一个分类下的所有 fact sheet (含子分类页面)."""
    print(f"\n{'='*60}")
    print(f"📋 {label}")
    print(f"{'='*60}")

    all_items = []

    # 收集子分类列表页 URL
    list_urls = [start_url]
    if suburls:
        for sub in suburls:
            list_urls.append(urljoin(start_url, sub))

    for list_url in list_urls:
        print(f"\n  列表页: {list_url}")
        html = _get(list_url)
        if not html:
            continue

        items = _extract_category_items(html, list_url)
        print(f"  → {len(items)} 篇")

        # 分页
        more = _extract_pagination(html, list_url)
        for p in more:
            if p not in list_urls:
                list_urls.append(p)
                print(f"  → 发现分页: {p}")

        all_items.extend(items)
        time.sleep(DELAY)

    # 去重
    seen = set()
    unique = []
    for it in all_items:
        if it["url"] not in seen:
            seen.add(it["url"])
            unique.append(it)

    print(f"\n  去重后共 {len(unique)} 篇，开始逐篇抓取...")

    results = []
    for i, item in enumerate(unique):
        print(f"  [{i+1}/{len(unique)}] {item['title']}", end="")
        html = _get(item["url"])
        if not html:
            print("  ✗")
            item["error"] = "fetch_failed"
            results.append(item)
            time.sleep(DELAY)
            continue

        parsed = _parse_fact_sheet(html, item["url"])
        parsed["category"] = label
        results.append(parsed)
        print(f"  ({len(parsed['content'])} chars)")
        time.sleep(DELAY)

    # 保存
    out_path = OUTPUT_DIR / f"{output_name}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"  ✅ {out_path} ({len(results)} 篇)\n")
    return results

def scrape_pdfs():
    """下载 IRRI 公开 PDF 文档."""
    print(f"\n{'='*60}")
    print("📄 PDF 文档")
    print(f"{'='*60}")
    pdf_dir = OUTPUT_DIR / "pdfs"
    pdf_dir.mkdir(exist_ok=True)

    pdfs = {
        "Control_of_Rice_Diseases.pdf":
            "http://www.knowledgebank.irri.org/ericeproduction/PDF_&_Docs/Control_of_Rice_Diseases.pdf",
        "Control_of_rice_insect_pests.pdf":
            "http://www.knowledgebank.irri.org/ericeproduction/PDF_&_Docs/Control_of_rice_insect_pests.pdf",
    }
    for name, url in pdfs.items():
        path = pdf_dir / name
        if path.exists():
            print(f"  ✓ 已存在: {name}")
            continue
        print(f"  下载: {name}")
        _download_file(url, path)
        print(f"  {path.stat().st_size:,} bytes")
        time.sleep(DELAY)

# ── Main ──────────────────────────────────────────────

def main():
    print("🌾 IRRI Rice Knowledge Bank 数据抓取")
    print(f"   授权: CC BY-NC-SA 3.0")
    print(f"   输出: {OUTPUT_DIR}")

    # 1. 病虫害管理 (按子分类)
    scrape_with_subcategories(
        "Pest Management",
        "http://www.knowledgebank.irri.org/training/fact-sheets/pest-management",
        "pest_management",
        suburls=[],  # 同一页
    )

    # 2. Rice Doctor (多页)
    scrape_with_subcategories(
        "Rice Doctor Fact Sheets",
        "http://knowledgebank.irri.org/decision-tools/rice-doctor/rice-doctor-fact-sheets",
        "rice_doctor",
        suburls=[
            "http://knowledgebank.irri.org/decision-tools/rice-doctor/rice-doctor-fact-sheets/2",
            "http://knowledgebank.irri.org/decision-tools/rice-doctor/rice-doctor-fact-sheets/3",
            "http://knowledgebank.irri.org/decision-tools/rice-doctor/rice-doctor-fact-sheets/4",
            "http://knowledgebank.irri.org/decision-tools/rice-doctor/rice-doctor-fact-sheets/5",
        ],
    )

    # 3. PDFs
    scrape_pdfs()

    print(f"\n{'='*60}")
    print("🎉 抓取完成!")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
