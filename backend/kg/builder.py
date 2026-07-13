"""图谱构建器 —— 初始化 Schema、导入数据、构建关系。"""
from neo4j import GraphDatabase
from backend.config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
from backend.kg.schema import CONSTRAINTS, INDEXES


class GraphBuilder:
    """水稻知识图谱的构建和管理。"""

    def __init__(self):
        self.driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    def init_schema(self):
        """创建约束和索引。"""
        with self.driver.session() as session:
            for cypher in CONSTRAINTS:
                try:
                    session.run(cypher)
                    print(f"[Schema] 约束已创建: {cypher[:60]}...")
                except Exception as e:
                    print(f"[Schema] 约束跳过（可能已存在）: {e}")

            for cypher in INDEXES:
                try:
                    session.run(cypher)
                    print(f"[Schema] 索引已创建: {cypher[:60]}...")
                except Exception as e:
                    print(f"[Schema] 索引跳过（可能已存在）: {e}")

    def upsert_disease(self, name: str, scientific_name: str = "",
                       pathogen_type: str = "", risk_level: str = "中"):
        """插入或更新病害节点。"""
        with self.driver.session() as session:
            result = session.run(
                """MERGE (d:Disease {name: $name})
                   SET d.scientific_name = $scientific_name,
                       d.pathogen_type = $pathogen_type,
                       d.risk_level = $risk_level
                   RETURN d.name""",
                name=name, scientific_name=scientific_name,
                pathogen_type=pathogen_type, risk_level=risk_level
            )
            return result.single()["d.name"]

    def upsert_symptom(self, name: str, symptom_type: str = "", severity: str = "中"):
        """插入或更新症状节点。"""
        with self.driver.session() as session:
            session.run(
                """MERGE (s:Symptom {name: $name})
                   SET s.type = $type, s.severity = $severity""",
                name=name, type=symptom_type, severity=severity
            )

    def link_symptom_to_disease(self, symptom_name: str, disease_name: str, weight: float = 0.5):
        """创建症状→病害的 INDICATES 关系。"""
        with self.driver.session() as session:
            session.run(
                """MATCH (s:Symptom {name: $symptom}), (d:Disease {name: $disease})
                   MERGE (s)-[r:INDICATES]->(d)
                   SET r.weight = $weight""",
                symptom=symptom_name, disease=disease_name, weight=weight
            )

    def upsert_control(self, name: str, control_type: str = "",
                       active_ingredient: str = "", safety_interval: int = 0):
        """插入或更新防治措施节点。"""
        with self.driver.session() as session:
            session.run(
                """MERGE (c:Control {name: $name})
                   SET c.type = $type, c.active_ingredient = $active_ingredient,
                       c.safety_interval = $safety_interval""",
                name=name, type=control_type, active_ingredient=active_ingredient,
                safety_interval=safety_interval
            )

    def link_control_to_disease(self, control_name: str, disease_name: str):
        """创建防治措施→病害的 EFFECTIVE_AGAINST 关系。"""
        with self.driver.session() as session:
            session.run(
                """MATCH (c:Control {name: $control}), (d:Disease {name: $disease})
                   MERGE (c)-[:EFFECTIVE_AGAINST]->(d)""",
                control=control_name, disease=disease_name
            )

    def upsert_variety(self, name: str, resistance: list[str] = None,
                       suitable_regions: str = ""):
        """插入品种并批量建立抗性关系。"""
        with self.driver.session() as session:
            session.run(
                """MERGE (v:Variety {name: $name})
                   SET v.suitable_regions = $regions""",
                name=name, regions=suitable_regions
            )
            if resistance:
                for disease in resistance:
                    session.run(
                        """MATCH (v:Variety {name: $variety}), (d:Disease {name: $disease})
                           MERGE (v)-[:RESISTANT_TO]->(d)""",
                        variety=name, disease=disease
                    )

    def upsert_env_condition(self, condition_type: str, threshold_min: float,
                             threshold_max: float):
        """插入环境条件节点。"""
        with self.driver.session() as session:
            session.run(
                """MERGE (e:EnvCondition {type: $type})
                   SET e.threshold_min = $min, e.threshold_max = $max""",
                type=condition_type, min=threshold_min, max=threshold_max
            )

    def link_env_to_disease(self, condition_type: str, disease_name: str, threshold: str = ""):
        """创建环境条件→病害的 TRIGGERS 关系。"""
        with self.driver.session() as session:
            session.run(
                """MATCH (e:EnvCondition {type: $type}), (d:Disease {name: $disease})
                   MERGE (e)-[r:TRIGGERS]->(d)
                   SET r.threshold = $threshold""",
                type=condition_type, disease=disease_name, threshold=threshold
            )

    def upsert_growth_stage(self, name: str, duration_days: int = 0, order: int = 0):
        """插入生育期节点。"""
        with self.driver.session() as session:
            session.run(
                """MERGE (g:GrowthStage {name: $name})
                   SET g.duration_days = $duration, g.order = $order""",
                name=name, duration=duration_days, order=order
            )

    def link_disease_to_stage(self, disease_name: str, stage_name: str, probability: float = 0.5):
        """创建病害→生育期的 OCCURS_AT 关系。"""
        with self.driver.session() as session:
            session.run(
                """MATCH (d:Disease {name: $disease}), (g:GrowthStage {name: $stage})
                   MERGE (d)-[r:OCCURS_AT]->(g)
                   SET r.probability = $prob""",
                disease=disease_name, stage=stage_name, prob=probability
            )

    def get_stats(self) -> dict:
        """获取图谱统计信息。"""
        with self.driver.session() as session:
            result = session.run(
                "MATCH (n) RETURN labels(n) as label, count(n) as cnt"
            )
            stats = {}
            for record in result:
                label = record["label"][0]
                stats[label] = record["cnt"]
            return stats

    def close(self):
        self.driver.close()
