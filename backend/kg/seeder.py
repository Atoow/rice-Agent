"""种子数据导入 —— 水稻病虫害核心知识导入 Neo4j 图谱。

数据来源：CABI 病虫害库 + 现有文档提取。
通过 LLM 辅助抽取，人工校对后录入。
"""
from backend.kg.builder import GraphBuilder
from backend.llm.factory import create_llm_provider
import json


# === 手工标注的核心水稻病虫害数据（CABI 来源） ===

SEED_DATA = [
    # ---- 稻瘟病 ----
    {
        "disease": {"name": "稻瘟病", "scientific_name": "Pyricularia oryzae",
                     "pathogen_type": "真菌", "risk_level": "高"},
        "symptoms": [
            {"name": "叶片梭形病斑", "type": "叶片", "severity": "中"},
            {"name": "病斑中央灰白色边缘褐色", "type": "叶片", "severity": "中"},
            {"name": "穗颈瘟", "type": "穗", "severity": "重"},
            {"name": "谷粒变黑", "type": "穗", "severity": "重"},
        ],
        "controls": [
            {"name": "三环唑", "type": "化学", "active_ingredient": "三环唑", "safety_interval": 21},
            {"name": "稻瘟灵", "type": "化学", "active_ingredient": "稻瘟灵", "safety_interval": 21},
            {"name": "春雷霉素", "type": "生物", "active_ingredient": "春雷霉素", "safety_interval": 14},
            {"name": "合理施肥控氮", "type": "农艺", "active_ingredient": "", "safety_interval": 0},
        ],
        "varieties": {
            "susceptible": ["宜香优2115"],
            "resistant": ["五优308"],
        },
        "env_triggers": [
            {"type": "温度", "threshold": "25-28°C"},
            {"type": "湿度", "threshold": ">90%"},
        ],
        "stages": [{"name": "分蘖期", "probability": 0.3}, {"name": "抽穗期", "probability": 0.8}],
    },
    # ---- 纹枯病 ----
    {
        "disease": {"name": "纹枯病", "scientific_name": "Rhizoctonia solani",
                     "pathogen_type": "真菌", "risk_level": "高"},
        "symptoms": [
            {"name": "叶鞘云纹状病斑", "type": "茎", "severity": "中"},
            {"name": "茎秆腐烂", "type": "茎", "severity": "重"},
            {"name": "叶片枯黄", "type": "叶片", "severity": "中"},
        ],
        "controls": [
            {"name": "井冈霉素", "type": "生物", "active_ingredient": "井冈霉素", "safety_interval": 14},
            {"name": "苯醚甲环唑", "type": "化学", "active_ingredient": "苯醚甲环唑", "safety_interval": 28},
            {"name": "合理密植通风", "type": "农艺", "active_ingredient": "", "safety_interval": 0},
        ],
        "varieties": {
            "susceptible": [],
            "resistant": ["五优308"],
        },
        "env_triggers": [
            {"type": "温度", "threshold": "28-32°C"},
            {"type": "湿度", "threshold": ">95%"},
        ],
        "stages": [{"name": "分蘖期", "probability": 0.7}, {"name": "抽穗期", "probability": 0.5}],
    },
    # ---- 稻飞虱 ----
    {
        "disease": {"name": "稻飞虱", "scientific_name": "Nilaparvata lugens",
                     "pathogen_type": "虫害", "risk_level": "高"},
        "symptoms": [
            {"name": "植株基部褐色", "type": "茎", "severity": "中"},
            {"name": "叶片发黄枯萎", "type": "叶片", "severity": "重"},
            {"name": "植株倒伏", "type": "全株", "severity": "重"},
        ],
        "controls": [
            {"name": "吡虫啉", "type": "化学", "active_ingredient": "吡虫啉", "safety_interval": 14},
            {"name": "噻虫嗪", "type": "化学", "active_ingredient": "噻虫嗪", "safety_interval": 21},
            {"name": "赤眼蜂", "type": "生物", "active_ingredient": "", "safety_interval": 0},
            {"name": "合理灌溉控水", "type": "农艺", "active_ingredient": "", "safety_interval": 0},
        ],
        "varieties": {
            "susceptible": ["宜香优2115"],
            "resistant": [],
        },
        "env_triggers": [
            {"type": "温度", "threshold": "25-30°C"},
            {"type": "湿度", "threshold": ">80%"},
        ],
        "stages": [{"name": "分蘖期", "probability": 0.6}, {"name": "抽穗期", "probability": 0.6}],
    },
    # ---- 稻纵卷叶螟 ----
    {
        "disease": {"name": "稻纵卷叶螟", "scientific_name": "Cnaphalocrocis medinalis",
                     "pathogen_type": "虫害", "risk_level": "中"},
        "symptoms": [
            {"name": "叶片卷曲", "type": "叶片", "severity": "中"},
            {"name": "叶片白斑", "type": "叶片", "severity": "轻"},
            {"name": "叶片枯死", "type": "叶片", "severity": "重"},
        ],
        "controls": [
            {"name": "氯虫苯甲酰胺", "type": "化学", "active_ingredient": "氯虫苯甲酰胺", "safety_interval": 21},
            {"name": "苏云金杆菌", "type": "生物", "active_ingredient": "Bt", "safety_interval": 7},
            {"name": "及时排水晒田", "type": "农艺", "active_ingredient": "", "safety_interval": 0},
        ],
        "varieties": {
            "susceptible": [],
            "resistant": [],
        },
        "env_triggers": [
            {"type": "湿度", "threshold": ">85%"},
        ],
        "stages": [{"name": "分蘖期", "probability": 0.5}, {"name": "抽穗期", "probability": 0.4}],
    },
    # ---- 水稻白叶枯病 ----
    {
        "disease": {"name": "白叶枯病", "scientific_name": "Xanthomonas oryzae pv. oryzae",
                     "pathogen_type": "细菌", "risk_level": "高"},
        "symptoms": [
            {"name": "叶缘黄白色条纹", "type": "叶片", "severity": "中"},
            {"name": "叶片干枯卷曲", "type": "叶片", "severity": "重"},
            {"name": "叶脉变黄", "type": "叶片", "severity": "轻"},
        ],
        "controls": [
            {"name": "噻菌铜", "type": "化学", "active_ingredient": "噻菌铜", "safety_interval": 21},
            {"name": "中生菌素", "type": "生物", "active_ingredient": "中生菌素", "safety_interval": 14},
            {"name": "选用抗病品种", "type": "农艺", "active_ingredient": "", "safety_interval": 0},
        ],
        "varieties": {
            "susceptible": [],
            "resistant": ["五优308"],
        },
        "env_triggers": [
            {"type": "温度", "threshold": "25-30°C"},
            {"type": "湿度", "threshold": ">90%"},
        ],
        "stages": [{"name": "分蘖期", "probability": 0.4}, {"name": "抽穗期", "probability": 0.6}],
    },
]

# 生育期数据
GROWTH_STAGES = [
    {"name": "苗期", "duration_days": 25, "order": 1},
    {"name": "分蘖期", "duration_days": 30, "order": 2},
    {"name": "拔节期", "duration_days": 15, "order": 3},
    {"name": "抽穗期", "duration_days": 15, "order": 4},
    {"name": "灌浆期", "duration_days": 25, "order": 5},
    {"name": "成熟期", "duration_days": 30, "order": 6},
]

# 品种数据
VARIETIES = [
    {"name": "宜香优2115", "regions": "四川、重庆", "resistant": []},
    {"name": "五优308", "regions": "长江流域", "resistant": ["稻瘟病", "纹枯病", "白叶枯病"]},
]


def seed_all():
    """导入所有种子数据到 Neo4j。"""
    builder = GraphBuilder()

    # 初始化 Schema
    builder.init_schema()

    # 导入生育期
    for stage in GROWTH_STAGES:
        builder.upsert_growth_stage(stage["name"], stage["duration_days"], stage["order"])

    # 导入品种
    for variety in VARIETIES:
        builder.upsert_variety(variety["name"], variety["resistant"], variety["regions"])

    # 导入病虫害数据
    for item in SEED_DATA:
        d = item["disease"]
        builder.upsert_disease(d["name"], d.get("scientific_name", ""),
                               d.get("pathogen_type", ""), d.get("risk_level", "中"))
        disease_name = d["name"]

        # 症状
        for sym in item["symptoms"]:
            builder.upsert_symptom(sym["name"], sym["type"], sym["severity"])
            builder.link_symptom_to_disease(sym["name"], disease_name, 0.7)

        # 防治措施
        for ctrl in item["controls"]:
            builder.upsert_control(ctrl["name"], ctrl["type"],
                                   ctrl.get("active_ingredient", ""),
                                   ctrl.get("safety_interval", 0))
            builder.link_control_to_disease(ctrl["name"], disease_name)

        # 环境触发
        for env in item["env_triggers"]:
            builder.upsert_env_condition(env["type"], 0, 100)
            builder.link_env_to_disease(env["type"], disease_name, env["threshold"])

        # 生育期关联
        for stage in item["stages"]:
            builder.link_disease_to_stage(disease_name, stage["name"], stage["probability"])

    # 统计
    stats = builder.get_stats()
    print(f"图谱导入完成: {stats}")

    builder.close()
    return stats


def extract_from_documents(doc_text: str) -> list[dict]:
    """从文档文本中用 LLM 辅助提取病虫害实体。

    Args:
        doc_text: 文档文本

    Returns:
        提取的病虫害数据结构列表
    """
    llm = create_llm_provider()
    prompt = f"""从以下水稻种植文档中提取病虫害信息，以 JSON 格式返回。

文档内容：
{doc_text[:3000]}

请提取其中提到的：
1. 病害/虫害名称及学名（如有）
2. 症状描述
3. 防治措施（生物/化学/农艺）
4. 相关的环境条件

返回格式：
[{{"disease": {{...}}, "symptoms": [{{...}}], "controls": [{{...}}], "env_triggers": [{{...}}]}}]
"""

    response = llm.generate([{"role": "user", "content": prompt}])
    # 简单解析（实际可用 json.loads 提取）
    try:
        start = response.find("[")
        end = response.rfind("]") + 1
        if start >= 0 and end > start:
            return json.loads(response[start:end])
    except (json.JSONDecodeError, ValueError):
        pass
    return []


if __name__ == "__main__":
    seed_all()
