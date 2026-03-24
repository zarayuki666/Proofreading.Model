# -*- coding: utf-8 -*-
"""
基于多份问卷“0-5 分值表”，训练一个 GBDT 黑盒模型，
学习题目之间的非线性组合关系（例如：家庭冲突 × 情绪失调）。

使用说明：
  1. 将所有用于训练的 CSV 放到 ./data 目录下（列名需包含 ITEM_TO_KEY 中的中文列）。
  2. 每行需要有一列 “身份定位” 或 “身份定位_clean”，用于区分 普通学生 / 重点关注对象 / 高风险 等。
  3. 在容器中执行：
         python build_ml_model_v4.py
  4. 脚本会生成：ml_risk_model.pkl
     app.py 会自动尝试加载并使用该模型（若不存在则只用规则引擎）。
"""

import os
import glob
from typing import Dict, List

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from joblib import dump

DATA_DIR = "./data"
FILE_PATTERNS = ["*.csv"]
OUTPUT_MODEL = "./ml_risk_model.pkl"

# ---- 统一的“身份 → 目标风险值”(0~1) ----
IDENTITY_TO_RISK: Dict[str, float] = {
    "普通学生（表现稳定）": 0.15,
    "普通学生（表现稳定)": 0.15,
    "普通学生（略需关注）": 0.40,
    "普通学生（略需关注)": 0.40,
    "重点关注对象": 0.75,
    "高风险需干预": 1.00,
    "监护良好但有违法行为": 0.95,
}

# ---- 身份样本权重：让模型更重视高风险个案 ----
IDENTITY_WEIGHT: Dict[str, float] = {
    "普通学生（表现稳定）": 1.0,
    "普通学生（表现稳定)": 1.0,
    "普通学生（略需关注）": 2.5,
    "普通学生（略需关注)": 2.5,
    "重点关注对象": 8.0,
    "高风险需干预": 12.0,
    "监护良好但有违法行为": 12.0,
}

# 与 adjustment 构建脚本保持一致的列名映射
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
    "情感支持": "f1",
    "情绪调节困难程度": "f2",
}


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
    print("将用于 ML 训练的问卷文件：")
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

    return df_all


def build_feature_matrix(df: pd.DataFrame):
    # 1) 目标变量 y
    def _id_to_y(v: str) -> float:
        return float(IDENTITY_TO_RISK.get(str(v).strip(), 0.40))

    df["risk_y"] = df["身份定位_clean"].map(_id_to_y)

    # 2) 样本权重
    def _id_to_w(v: str) -> float:
        return float(IDENTITY_WEIGHT.get(str(v).strip(), 1.0))

    df["sample_w"] = df["身份定位_clean"].map(_id_to_w)

    print(f"合并后总样本数: {len(df)}")
    print(df[["身份定位_clean", "risk_y"]].head())

    # 3) 选择题目列（0-5 分值）
    feature_cols: List[str] = []
    feature_keys: List[str] = []

    for col_zh, key in ITEM_TO_KEY.items():
        if col_zh in df.columns:
            feature_cols.append(col_zh)
            feature_keys.append(key)
        else:
            print(f"  ⚠️ 训练数据中缺少列：{col_zh} ，该题目将不会用于 ML。")

    if not feature_cols:
        raise RuntimeError("没有任何题目列可用于训练（ITEM_TO_KEY 对应的列均不存在）。")

    # 将题目列安全转换为数值 0~5
    X_base = df[feature_cols].copy()
    for c in feature_cols:
        X_base[c] = pd.to_numeric(X_base[c], errors="coerce")
        X_base[c] = X_base[c].fillna(0.0)
        X_base[c] = X_base[c].clip(0.0, 5.0)

    X_base = X_base.values

    # 4) 手工交互特征（与 app 前端保持一致）
    def _col_idx_by_key(key: str):
        zh_col = None
        for zh, k in ITEM_TO_KEY.items():
            if k == key:
                zh_col = zh
                break
        if zh_col is None:
            return None
        try:
            return feature_cols.index(zh_col)
        except ValueError:
            return None

    idx_a3_2 = _col_idx_by_key("a3_2")
    idx_f2   = _col_idx_by_key("f2")
    idx_b1_2 = _col_idx_by_key("b1_2")
    idx_c1   = _col_idx_by_key("c1")
    idx_e1a  = _col_idx_by_key("e1a")
    idx_d1   = _col_idx_by_key("d1")

    def _safe_inter(i, j):
        if i is None or j is None:
            return np.zeros((X_base.shape[0], 1), dtype=float)
        return (X_base[:, i] * X_base[:, j]).reshape(-1, 1)

    inter_fam_emo = _safe_inter(idx_a3_2, idx_f2)   # 家庭冲突 × 情绪调节困难
    inter_vio_peer = _safe_inter(idx_b1_2, idx_c1)  # 暴力攻击 × 不良同伴
    inter_net_drop = _safe_inter(idx_e1a, idx_d1)   # 上网时间问题 × 逃学/在校表现

    extra_list = [inter_fam_emo, inter_vio_peer, inter_net_drop]
    extra_features = ["a3_2*f2", "b1_2*c1", "e1a*d1"]

    X = np.concatenate([X_base] + extra_list, axis=1)

    y = df["risk_y"].astype(float).values
    w = df["sample_w"].astype(float).values

    return X, y, w, feature_keys, extra_features, feature_cols


def train_model(X, y, w):
    # 简单的 GBDT 回归模型
    gbdt = GradientBoostingRegressor(
        loss="squared_error",
        n_estimators=300,
        learning_rate=0.05,
        max_depth=3,
        subsample=0.8,
        random_state=42,
    )
    gbdt.fit(X, y, sample_weight=w)

    y_hat = gbdt.predict(X)
    mse = float(((y_hat - y) ** 2).mean())
    print(f"✅ 训练完成，训练集 MSE = {mse:.4f}")
    return gbdt


def main():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR, exist_ok=True)
        print(f"已创建数据目录 {DATA_DIR}，请先将问卷 CSV 放入该目录后再运行本脚本。")
        return

    print("🚀 开始训练 ML 黑盒模型 (GBDT)...")
    df = load_all_cases()
    X, y, w, feature_keys, extra_features, feature_cols = build_feature_matrix(df)
    gbdt = train_model(X, y, w)

    bundle = {
        "model": gbdt,
        "base_keys": feature_keys,
        "extra_features": extra_features,
        "feature_cols_zh": feature_cols,
        "identity_mapping": IDENTITY_TO_RISK,
        "identity_weight": IDENTITY_WEIGHT,
        "version": "v4_gbdt_interactions",
    }

    dump(bundle, OUTPUT_MODEL)
    print(f"💾 已保存 ML 模型到 {OUTPUT_MODEL}")
    print("   前端 app.py 将自动尝试加载该文件，成功则会在右侧显示“规则 + AI 双引擎”结果。")


if __name__ == "__main__":
    main()
