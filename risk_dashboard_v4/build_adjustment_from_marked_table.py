import json
import os

import pandas as pd

# ====== 配置区 ======

# 标定表 CSV 路径（你现在这份）
MARKED_CSV = "./data/题目分值风险标定_1200份.csv"

# 输出的 adjustment.json
OUTPUT_JSON = "./adjustment.json"

# item 中文名 -> 前端题目 key
ITEM_TO_KEY = {
    "家庭沟通分": "a3_1",
    "家庭冲突分": "a3_2",
    "冲动易冲动程度": "b1_1",
    "攻击暴力倾向": "b1_2",
    "自我认同问题程度": "b3",
    "受不良同伴影响强度": "c1",
    "受社区影响强度": "c2",
    "逃学旷课频次": "d1",
    "法治教育学习效果": "d2",
    "上网时间问题程度": "e1a",
    "深夜上网问题程度": "e1b",
    "接触有害内容频次": "e2",
    "情感支持": "f1",        # 保护项，后面会特殊处理
    "情绪调节困难程度": "f2",
    "时间管理问题程度": "g1",
    "理财观念行为问题程度": "g2",
}

# 哪些题是“保护性”维度（风险越高，保护越弱）
PROTECTIVE_ITEMS = {"情感支持"}

# ====== 读取标定表 ======

if not os.path.exists(MARKED_CSV):
    raise FileNotFoundError(f"找不到标定表文件: {MARKED_CSV}")

df = pd.read_csv(MARKED_CSV)

required_cols = {"item", "score", "risk_score_0_1"}
missing = required_cols - set(df.columns)
if missing:
    raise ValueError(f"CSV 缺少列: {missing}，当前列有: {list(df.columns)}")

adj = {}

for item_name, key in ITEM_TO_KEY.items():
    sub = df[df["item"] == item_name].copy()
    if sub.empty:
        print(f"[警告] 标定表中没有找到题目: {item_name}，对应 key: {key}，跳过")
        continue

    # 保证有 score 0-5
    sub = sub.sort_values("score")
    score_map = {}
    for _, row in sub.iterrows():
        raw = int(row["score"])
        risk_p = float(row["risk_score_0_1"])

        # 截断到 [0, 1]
        risk_p = max(0.0, min(1.0, risk_p))

        # 对于保护项：我们希望“保护分越高” → “风险越低”
        # 因为前端里 f1 是 map_to="protection"，会把这个值当“保护强度”
        if item_name in PROTECTIVE_ITEMS:
            value = round(1.0 - risk_p, 3)  # 保护 = 1 - 风险
        else:
            value = round(risk_p, 3)        # 风险项直接用风险强度

        score_map[str(raw)] = value

    adj[key] = {
        "ALL": {
            "map": score_map
        }
    }
    print(f"题目 {item_name} (key={key}) 的映射: {score_map}")

# ====== 写出 adjustment.json ======

with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
    json.dump(adj, f, ensure_ascii=False, indent=2)

print(f"\n✅ 已生成校准文件: {OUTPUT_JSON}")
