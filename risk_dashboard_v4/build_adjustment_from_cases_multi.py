# -*- coding: utf-8 -*-
"""
基于多份问卷个案数据，自动校准 0-5 分值到 [0,1] 区间的风险/保护强度，
生成 adjustment.json，供 app.py 前端进行量表校准使用。

使用说明：
    1. 将所有用于训练的问卷 CSV 放在 ./data 目录下。
    2. 每行需要有一列“身份定位”或“身份定位_clean”，用于区分风险等级。
    3. 每份问卷中的打分题需要包含 ITEM_TO_KEY 里列出的中文列名，值为 0~5。
    4. 在项目根目录运行：
           python build_adjustment_from_cases_multi.py
       会在根目录生成 ./adjustment.json。
"""

import os
import glob
import json
from typing import Dict, List

import pandas as pd

# ===== 基本配置 =====

DATA_DIR = "./data"
FILE_PATTERNS = ["*.csv"]
OUTPUT_JSON = "./adjustment.json"

# 统一的“身份 → 风险基线”映射（0 ~ 1）
IDENTITY_TO_RISK = {
    "普通学生（表现稳定）": 0.15,
    "普通学生（表现稳定)": 0.15,  # 半角括号兼容
    "普通学生（略需关注）": 0.40,
    "普通学生（略需关注)": 0.40,
    "重点关注对象": 0.75,
    "高风险需干预": 1.00,
    "监护良好但有违法行为": 0.95,
}

# 题目映射：问卷里的中文列名 -> 前端 key
ITEM_TO_KEY: Dict[str, str] = {
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
    "时间管理问题程度": "g1",
    "理财观念行为问题程度": "g2",
    # 保护因子
    "情感支持": "f1",
    "情绪调节困难程度": "f2",
}

# 哪些 key 在 JSON 里存的是“保护强度”(0=弱保护,1=强保护)
PROTECTIVE_KEYS = {"f1"}

# 每个原始分值最少样本数，低于此则退回线性映射
MIN_COUNT_PER_SCORE = 30


def find_all_files() -> List[str]:
    files: List[str] = []
    for pat in FILE_PATTERNS:
        files.extend(glob.glob(os.path.join(DATA_DIR, pat)))
    files = sorted(set(files))
    return files


def load_all_cases() -> pd.DataFrame:
    files = find_all_files()
    if not files:
        raise FileNotFoundError(f"在 {DATA_DIR} 下未找到任何 CSV 文件，请确认路径和文件名。")

    dfs = []
    print("将用于校准的问卷文件：")
    for path in files:
        try:
            try:
                df = pd.read_csv(path, encoding="utf-8-sig")
            except UnicodeDecodeError:
                df = pd.read_csv(path, encoding="gbk")
        except Exception as e:
            print(f"  ⚠️ 读取 {path} 失败：{e}")
            continue

        df.columns = df.columns.str.strip()
        print(f"  - {path} (样本数: {len(df)})")
        dfs.append(df)

    if not dfs:
        raise RuntimeError("未成功读取到任何有效 CSV，请检查文件编码/格式。")

    df_all = pd.concat(dfs, ignore_index=True)

    # 身份列可能叫“身份定位”或“身份定位_clean”
    id_col = None
    for cand in ["身份定位", "身份定位_clean"]:
        if cand in df_all.columns:
            id_col = cand
            break
    if id_col is None:
        raise ValueError("合并后的数据中缺少 '身份定位' 或 '身份定位_clean' 列。")

    df_all = df_all[df_all[id_col].notna()].copy()
    df_all["身份定位_clean"] = df_all[id_col].astype(str).str.strip()

    # 根据身份映射 risk_y
    def _id_to_y(v: str) -> float:
        return float(IDENTITY_TO_RISK.get(str(v).strip(), 0.40))

    df_all["risk_y"] = df_all["身份定位_clean"].map(_id_to_y)
    print(f"合并后总样本数: {len(df_all)}")
    print(df_all[["身份定位_clean", "risk_y"]].head())
    print(f"全体样本 risk_y 均值: {df_all['risk_y'].mean():.4f}")

    # 确保题目列为 0~5 数字
    for col_name in ITEM_TO_KEY.keys():
        if col_name not in df_all.columns:
            print(f"  ⚠️ 数据中缺少列：{col_name}，该题目将不会参与校准。")
            continue
        s = pd.to_numeric(df_all[col_name], errors="coerce")
        s = s.clip(0, 5)
        df_all[col_name] = s

    return df_all


def build_adjustment(df: pd.DataFrame) -> dict:
    adj: Dict[str, dict] = {}
    global_mean = float(df["risk_y"].mean())

    for col_name, key in ITEM_TO_KEY.items():
        if col_name not in df.columns:
            continue

        is_protective = key in PROTECTIVE_KEYS
        print(f"\n=== 标定题目：{col_name} (key={key}) protective={is_protective} ===")
        score_vals = []
        score_map: Dict[str, float] = {}

        for raw in range(6):
            mask = df[col_name] == raw
            subset = df.loc[mask]

            if len(subset) >= MIN_COUNT_PER_SCORE:
                mean_risk = float(subset["risk_y"].mean())
                if is_protective:
                    # 保护因子：样本越低风险，保护越高
                    val = 1.0 - mean_risk
                else:
                    val = mean_risk
            else:
                # 样本不足：回退到“全局平均 + 线性倾斜”
                if is_protective:
                    lin_prot = raw / 5.0  # 分越高保护越强
                    val = 0.7 * lin_prot + 0.3 * (1.0 - global_mean)
                else:
                    lin_risk = raw / 5.0  # 分越高风险越高
                    val = 0.7 * lin_risk + 0.3 * global_mean

            # 限制到 (0.02, 0.98)，避免过于极端
            val = max(0.02, min(0.98, float(val)))
            score_vals.append(val)

        # 单调性修正：风险题目单调递增；保护题目单调递增(保护强度随分数升高)
        if is_protective:
            for i in range(1, 6):
                if score_vals[i] < score_vals[i - 1]:
                    score_vals[i] = score_vals[i - 1]
        else:
            for i in range(1, 6):
                if score_vals[i] < score_vals[i - 1]:
                    score_vals[i] = score_vals[i - 1]

        for raw, val in enumerate(score_vals):
            score_map[str(raw)] = round(val, 4)

        adj[key] = {
            "ALL": {
                "map": score_map
            }
        }
        print(f"  映射表：{score_map}")

    return adj


def main():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR, exist_ok=True)
        print(f"已创建数据目录 {DATA_DIR}，请先将问卷 CSV 放入该目录后再运行本脚本。")
        return

    df = load_all_cases()
    adj = build_adjustment(df)

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(adj, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 已生成校准结果 JSON：{OUTPUT_JSON}")


if __name__ == "__main__":
    main()
