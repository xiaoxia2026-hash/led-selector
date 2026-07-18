import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
import os

st.set_page_config(page_title="多参数LED选型系统", layout="wide")
st.title("💡 多维度二极管智能检索系统")

# ========== 数据加载 ==========
@st.cache_data
def load_data():
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(current_dir, "LED_database.xlsx")
        
        if not os.path.exists(file_path):
            st.error("❌ 文件不存在")
            return None
        
        # 限制读取行数（防止内存溢出）
        df = pd.read_excel(file_path, nrows=1000)
        
        if df.empty:
            st.warning("⚠️ 数据为空")
            return None
        
        # 强制转换数值列为数字类型
        numeric_cols = ['Dominant_wt', '光通量 (lm)', '光效 (lm/W)', 'CCT', 'x', 'y', 'u', 'v']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # 删除关键列为空的行
        df = df.dropna(subset=['CCT', 'x', 'y'])
        
        return df
        
    except Exception as e:
        st.error(f"❌ 错误：{str(e)}")
        return None

# 加载数据
df = load_data()

if df is None or df.empty:
    st.error("❌ 数据加载失败")
    st.stop()

# ========== 显示数据预览 ==========
st.subheader("📊 数据预览（前5行）")
st.dataframe(df.head(5), use_container_width=True)
st.caption(f"总记录数：{len(df)} 条（已限制1000行）")

# ========== 参数列表 ==========
params = [
    ("CCT", "色温 (K)", 3000.0, 100.0, 300.0),
    ("Dominant_wt", "主波长 (nm)", 580.0, 1.0, 5.0),
    ("x", "CIE-x", 0.3000, 0.001, 0.01),
    ("y", "CIE-y", 0.3100, 0.001, 0.01),
    ("u", "CIE-u", 0.2000, 0.001, 0.01),
    ("v", "CIE-v", 0.4500, 0.001, 0.01),
]

st.sidebar.header("🔍 输入目标参数与容差")

targets = {}
tolerances = {}
cols = st.sidebar.columns(2)

for i, (col, label, default, step, tol_default) in enumerate(params):
    if col not in df.columns:
        st.sidebar.warning(f"⚠️ 列 '{col}' 不存在")
        continue
    with cols[i % 2]:
        targets[col] = st.number_input(f"{label}", value=default, step=step, format="%.4f")
        tolerances[col] = st.number_input(f"容差±", value=tol_default, step=step/2, format="%.4f", key=f"tol_{col}")

st.sidebar.markdown("---")
top_n = st.sidebar.slider("显示最优匹配数量", 1, 20, 5)

# ========== 筛选算法 ==========
def multi_param_filter(df, targets, tolerances):
    mask = pd.Series([True] * len(df))
    for col in targets:
        if col in df.columns:
            mask &= (df[col] >= targets[col] - tolerances[col]) & (df[col] <= targets[col] + tolerances[col])
    candidates = df[mask].copy()
    
    if candidates.empty:
        return candidates
    
    scores = []
    for idx, row in candidates.iterrows():
        score = 0
        for col in targets:
            if col in df.columns and tolerances[col] != 0:
                dev = abs(row[col] - targets[col]) / tolerances[col]
                score += dev
        scores.append(score)
    candidates['综合得分'] = scores
    candidates = candidates.sort_values('综合得分')
    return candidates

# ========== 检索 ==========
if st.button("🚀 开始检索", type="primary"):
    results = multi_param_filter(df, targets, tolerances)
    
    if results.empty:
        st.error("❌ 未找到符合容差范围的型号，请放宽容差。")
    else:
        st.success(f"✅ 找到 {len(results)} 个符合条件的型号")
        
        display_df = results.head(top_n).copy()
        for col in targets:
            if col in display_df.columns:
                display_df[col] = display_df[col].map(lambda x: f"{x:.4f}" if pd.notna(x) else "")
        
        cols_to_show = ['Model', 'Vendor'] + list(targets.keys()) + ['综合得分']
        available_cols = [c for c in cols_to_show if c in display_df.columns]
        st.dataframe(display_df[available_cols], use_container_width=True)
        
        col1, col2 = st.columns(2)
        with col1:
            if 'x' in results.columns and 'y' in results.columns:
                fig = px.scatter(
                    results.head(top_n), 
                    x='x', 
                    y='y', 
                    text='Model',
                    title="色度坐标分布",
                    labels={'x': 'CIE-x', 'y': 'CIE-y'}
                )
                fig.add_scatter(
                    x=[targets['x']], 
                    y=[targets['y']], 
                    mode='markers', 
                    marker=dict(size=15, symbol='star', color='red'),
                    name='目标坐标'
                )
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            if 'Vendor' in results.columns:
                vendor_count = results.head(top_n)['Vendor'].value_counts()
                st.bar_chart(vendor_count)
                st.caption("最优匹配结果中的厂家占比")

# ========== 完整数据库 ==========
with st.expander("📂 查看完整数据库一览"):
    st.dataframe(df, use_container_width=True)
    st.caption(f"共 {len(df)} 条记录")
