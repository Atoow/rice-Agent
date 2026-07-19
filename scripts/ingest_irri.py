"""
IRRI 数据导入脚本

将抓取的 IRRI 文章：
1. 用 LLM 提取结构化实体 → 导入 Neo4j 知识图谱
2. 全文切分 → 导入 Numpy 向量知识库

用法:
  python scripts/ingest_irri.py
"""

import json
import os
import sys
from pathlib import Path

# 确保 backend 可导入
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.kg.builder import GraphBuilder
from backend.rag.retriever import Retriever
from backend.rag.embedding import OllamaEmbedding
from backend.config import CHUNK_SIZE, CHUNK_OVERLAP

# 新增：用 LLM 逐篇提取图谱实体 (IRRI 文章结构不同于种子数据)
from backend.llm.factory import create_llm_provider

# ═══════════════════════════════════════════════════════════
# Phase 1: 导入 Neo4j 知识图谱
# ═══════════════════════════════════════════════════════════


def _extract_kg_entities(article: dict) -> dict | None:
    """用 LLM 从单篇 IRRI 文章提取图谱实体。"""
    import asyncio
    llm = create_llm_provider()
    title = article.get("title", "")
    content = article.get("content", "")[:2500]
    category = article.get("category", "")

    prompt = f"""从以下水稻文章提取病虫害知识图谱实体。

文章标题: {title}
分类: {category}
文章内容:
{content}

请提取出:
1. 病害/虫害名称 (disease)，及其学名 (scientific_name)、病原类型 (pathogen_type: 真菌/细菌/病毒/虫害)、风险等级 (risk_level: 高/中/低)
2. 症状列表 (symptoms): 描述 (name)、部位 (type: 叶片/茎/穗/根/全株)、严重程度 (severity: 重/中/轻)
3. 防治措施 (controls): 名称 (name)、类型 (type: 化学/生物/农艺)、有效成分 (active_ingredient)、安全间隔期 (safety_interval)
4. 环境触发条件 (env_triggers): 类型 (type)、阈值 (threshold)
5. 易感品种 (susceptible_varieties) 和抗病品种 (resistant_varieties)
6. 发生生育期 (growth_stages) 及概率 (probability)

以 JSON 返回，格式:
{{
  "disease": {{"name": "...", "scientific_name": "...", "pathogen_type": "...", "risk_level": "..."}},
  "symptoms": [{{"name": "...", "type": "...", "severity": "..."}}],
  "controls": [{{"name": "...", "type": "...", "active_ingredient": "...", "safety_interval": 0}}],
  "env_triggers": [{{"type": "...", "threshold": "..."}}],
  "susceptible_varieties": [],
  "resistant_varieties": [],
  "growth_stages": [{{"name": "...", "probability": 0.5}}]
}}

如果文章本质是营养缺乏/非生物性问题（如 Alkalinity, Nitrogen deficiency），不要返回 disease 而是返回 {{"skip": true, "reason": "说明"}}。
如果文章是管理措施类（如 Direct seeding, Field level），也返回 skip。
只提取明确的病害/虫害实体。"""

    try:
        response = asyncio.run(llm.generate([{"role": "user", "content": prompt}]))
        # 解析 JSON
        start = response.find("{")
        end = response.rfind("}") + 1
        if start >= 0 and end > start:
            data = json.loads(response[start:end])
            if data.get("skip"):
                return None
            return data
    except Exception as e:
        print(f"    LLM 解析失败: {e}")
    return None


def import_to_neo4j(articles: list[dict], dry_run: bool = False):
    """将提取的实体导入 Neo4j 知识图谱。

    Args:
        articles: IRRI 文章列表
        dry_run: True 则只打印不导入
    """
    print("\n🔗 Phase 1: 导入 Neo4j 知识图谱")
    print("=" * 50)

    if dry_run:
        print("  [DRY RUN 模式，不实际操作 Neo4j]")
        builder = None
    else:
        builder = GraphBuilder()
        builder.init_schema()

    imported = 0
    skipped = 0

    for i, article in enumerate(articles):
        title = article.get("title", f"Article #{i}")
        cat = article.get("category", "?")

        # 跳过明显非病害的文章 (营养缺乏类)
        skip_keywords = [
            "deficiency", "toxicity", "excess", "alkalinity",
            "direct seeding", "field level", "crop too dense",
            "drought", "dry wind", "flooding", "genetic",
            "heavy rainfall", "mixed variety", "muddy water",
            "poor seed", "poor transplant", "replanted",
            "salinity", "seed rate", "seed too deep", "seeder clogged",
            "soil crusting", "soil too soft", "cloddy soil",
        ]
        title_lower = title.lower()
        if any(kw in title_lower for kw in skip_keywords):
            skipped += 1
            continue

        print(f"  [{i+1}/{len(articles)}] {title} ({cat})", end="")

        if dry_run:
            print("  → 跳过 (dry run)")
            continue

        # LLM 提取
        entity = _extract_kg_entities(article)
        if not entity or not entity.get("disease"):
            print("  → 无有效实体")
            skipped += 1
            continue

        d = entity["disease"]
        disease_name = d.get("name", title)

        try:
            # 创建病害节点
            builder.upsert_disease(
                disease_name,
                d.get("scientific_name", ""),
                d.get("pathogen_type", ""),
                d.get("risk_level", "中"),
            )

            # 症状
            for sym in entity.get("symptoms", []):
                if sym.get("name"):
                    builder.upsert_symptom(sym["name"], sym.get("type", ""), sym.get("severity", ""))
                    builder.link_symptom_to_disease(sym["name"], disease_name, 0.7)

            # 防治措施
            for ctrl in entity.get("controls", []):
                if ctrl.get("name"):
                    builder.upsert_control(
                        ctrl["name"], ctrl.get("type", ""),
                        ctrl.get("active_ingredient", ""),
                        ctrl.get("safety_interval", 0),
                    )
                    builder.link_control_to_disease(ctrl["name"], disease_name)

            # 环境条件
            for env in entity.get("env_triggers", []):
                if env.get("type"):
                    builder.upsert_env_condition(env["type"], 0, 100)
                    builder.link_env_to_disease(env["type"], disease_name, env.get("threshold", ""))

            # 品种抗性
            for v in entity.get("susceptible_varieties", []):
                if v:
                    builder.upsert_variety(v, [], "")
                    # SUSCEPTIBLE_TO 关系未在 builder 中实现，跳过
            for v in entity.get("resistant_varieties", []):
                if v:
                    builder.upsert_variety(v, [disease_name], "")

            # 生育期
            for stage in entity.get("growth_stages", []):
                if stage.get("name"):
                    builder.link_disease_to_stage(disease_name, stage["name"], stage.get("probability", 0.5))

            imported += 1
            print(f"  ✅ ({len(entity.get('symptoms',[]))} 症状, {len(entity.get('controls',[]))} 防治)")

        except Exception as e:
            print(f"  ❌ {e}")
            skipped += 1

    if not dry_run:
        stats = builder.get_stats()
        print(f"\n  📊 图谱统计: {stats}")
        builder.close()

    print(f"\n  导入: {imported} | 跳过: {skipped}")


# ═══════════════════════════════════════════════════════════
# Phase 2: 导入向量知识库
# ═══════════════════════════════════════════════════════════


def _chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """简单中文切分：优先按句号、换行切，其次按长度切。"""
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        if end < len(text):
            # 尝试在句号或换行处断开
            for sep in ["。", "\n", ".", "；"]:
                pos = text.rfind(sep, start, end)
                if pos > start + chunk_size // 2:
                    end = pos + 1
                    break
        chunks.append(text[start:end])
        start = end - overlap if end - overlap > start else end
    return chunks


def import_to_vectorstore(articles: list[dict]):
    """将 IRRI 文章导入 Numpy 向量知识库。

    每条文章的每个 section 单独做一个 chunk。
    """
    print("\n📚 Phase 2: 导入向量知识库")
    print("=" * 50)

    embedding = OllamaEmbedding()
    retriever = Retriever(embedding=embedding)

    chunks = []
    for article in articles:
        title = article.get("title", "")
        cat = article.get("category", "")

        # 每个 section 独立入库
        for heading, text in article.get("sections", {}).items():
            source = f"IRRI: {title} - {heading}"
            sub_chunks = _chunk_text(text)
            for idx, chunk_text in enumerate(sub_chunks):
                chunks.append({
                    "content": chunk_text,
                    "source": source,
                    "index": idx,
                })

        # 如果没有 section，整篇内容入库
        if not article.get("sections"):
            content = article.get("content", "")
            if content and len(content) > 50:
                sub_chunks = _chunk_text(content)
                for idx, chunk_text in enumerate(sub_chunks):
                    chunks.append({
                        "content": chunk_text,
                        "source": f"IRRI: {title}",
                        "index": idx,
                    })

    print(f"  切分完成: {len(chunks)} 个文本块")

    if chunks:
        added = retriever.add_documents(chunks)
        print(f"  ✅ 已入库 {added} 个块")
        stats = retriever.get_collection_stats()
        print(f"  📊 向量库总计: {stats['total_chunks']} 个块, {stats['vector_dim']} 维向量")
    else:
        print("  ⚠️  没有可入库的文本")


# ═══════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════


def main():
    import argparse

    parser = argparse.ArgumentParser(description="导入 IRRI 数据到知识图谱和向量库")
    parser.add_argument("--input", default="data/irri/irri_all.json", help="IRRI JSON 文件路径")
    parser.add_argument("--kg-only", action="store_true", help="只导入图谱")
    parser.add_argument("--vec-only", action="store_true", help="只导入向量库")
    parser.add_argument("--dry-run", action="store_true", help="不实际操作，只预览")
    args = parser.parse_args()

    # 加载
    input_path = Path(__file__).parent.parent / args.input
    if not input_path.exists():
        print(f"❌ 文件不存在: {input_path}")
        print(f"   请先运行 scripts/scrape_irri.py")
        sys.exit(1)

    with open(input_path, encoding="utf-8") as f:
        articles = json.load(f)

    print(f"📄 加载 {len(articles)} 篇 IRRI 文章")

    if not args.vec_only:
        import_to_neo4j(articles, dry_run=args.dry_run)

    if not args.kg_only:
        import_to_vectorstore(articles)

    print("\n🎉 导入完成!")


if __name__ == "__main__":
    main()
