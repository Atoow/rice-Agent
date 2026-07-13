"""知识图谱 Schema 定义 —— 实体标签、关系类型、约束。"""

# 节点标签
LABELS = {
    "Disease": "病害",
    "Symptom": "症状",
    "Control": "防治措施",
    "Variety": "品种",
    "EnvCondition": "环境条件",
    "GrowthStage": "生育期",
}

# 关系类型
RELATIONSHIPS = {
    "HAS_SYMPTOM": ("Disease", "Symptom"),
    "INDICATES": ("Symptom", "Disease"),
    "CONTROLLED_BY": ("Disease", "Control"),
    "EFFECTIVE_AGAINST": ("Control", "Disease"),
    "TRIGGERS": ("EnvCondition", "Disease"),
    "RESISTANT_TO": ("Variety", "Disease"),
    "SUSCEPTIBLE_TO": ("Variety", "Disease"),
    "OCCURS_AT": ("Disease", "GrowthStage"),
}

# 节点属性定义
PROPERTIES = {
    "Disease": {
        "name": "str (必需)",
        "scientific_name": "str (可选)",
        "pathogen_type": "str — 真菌/细菌/病毒/虫害",
        "risk_level": "str — 高/中/低",
    },
    "Symptom": {
        "name": "str (必需)",
        "type": "str — 叶片/穗/茎/根/全株",
        "severity": "str — 轻/中/重",
    },
    "Control": {
        "name": "str (必需)",
        "type": "str — 生物/化学/农艺",
        "active_ingredient": "str (可选)",
        "safety_interval": "int (天)",
    },
    "Variety": {
        "name": "str (必需)",
        "resistance": "list[str]",
        "suitable_regions": "str",
    },
    "EnvCondition": {
        "type": "str — 温度/湿度/水分/光照",
        "threshold_min": "float",
        "threshold_max": "float",
    },
    "GrowthStage": {
        "name": "str (必需)",
        "duration_days": "int",
        "order": "int",
    },
}

# 创建约束的 Cypher 语句
CONSTRAINTS = [
    "CREATE CONSTRAINT disease_name IF NOT EXISTS FOR (d:Disease) REQUIRE d.name IS UNIQUE",
    "CREATE CONSTRAINT symptom_name IF NOT EXISTS FOR (s:Symptom) REQUIRE s.name IS UNIQUE",
    "CREATE CONSTRAINT control_name IF NOT EXISTS FOR (c:Control) REQUIRE c.name IS UNIQUE",
    "CREATE CONSTRAINT variety_name IF NOT EXISTS FOR (v:Variety) REQUIRE v.name IS UNIQUE",
    "CREATE CONSTRAINT stage_name IF NOT EXISTS FOR (g:GrowthStage) REQUIRE g.name IS UNIQUE",
]

# 索引
INDEXES = [
    "CREATE INDEX disease_pathogen IF NOT EXISTS FOR (d:Disease) ON (d.pathogen_type)",
    "CREATE INDEX symptom_type IF NOT EXISTS FOR (s:Symptom) ON (s.type)",
    "CREATE INDEX env_type IF NOT EXISTS FOR (e:EnvCondition) ON (e.type)",
]
