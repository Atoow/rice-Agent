"""知识图谱初始化脚本 —— 导入水稻病虫害种子数据到 Neo4j。"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.kg.seeder import seed_all

if __name__ == "__main__":
    print("=== 开始导入知识图谱种子数据 ===")
    stats = seed_all()
    print(f"=== 完成！图谱统计: {stats} ===")
