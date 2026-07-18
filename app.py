import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
import os

st.set_page_config(page_title="多参数LED选型系统", layout="wide")
st.title("💡 多维度二极管智能检索系统")

# ========== 数据加载函数（带错误处理） ==========
@st.cache_data
def load_data():
    try:
        # 获取当前文件所在目录
        current_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(current_dir, "LED_database.xlsx")
        
        # 检查文件是否存在
        if not os.path.exists(file_path):
            st.error(f"❌ 文件不存在：{file_path}")
            return pd.DataFrame()
        
        # 读取Excel
        df = pd.read_excel(file_path)
        
        # 检查是否为空
        if df.empty:
            st.warning("⚠️ Excel文件为空")
            return df
        
        # 显示列名（调试用）
        st.sidebar.write("📋 Excel列名：", list(df.columns))
        
        return df
        
    except Exception as e:
        st.error(f"❌ 读取Excel失败：{str(e)}")
        return pd.DataFrame()

# ========== 加载数据 ==========
df = load_data()

# 检查数据是否加载成功
if df.empty:
    st.stop()  # 停止执行，避免后续错误

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
    with cols[i % 2]:
        # 检查列是否存在
        if col not in df.columns:
            st.sidebar.warning(f"⚠️ 列 '{col}' 不存在")
            continue
        targets[col] = st.number_input(f"{label}", value=default, step=step, format="%.4f")
        tolerances[col] = st.number_input(f"容差±", value=tol_default, step=step/2, format="%.4f", key=f"tol_{col}")

st.sidebar.markdown("---")
top_n = st.sidebar.slider("显示最优匹配数量", 1, 20, 5)

# ========== 核心筛选算法 ==========
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

# ========== 检索按钮 ==========
if st.button("🚀 开始检索", type="primary"):
    results = multi_param_filter(df, targets, tolerances)
    
    if results.empty:
        st.error("❌ 未找到完全符合容差范围的型号，请适当放宽容差。")
    else:
        st.success(f"✅ 找到 {len(results)} 个符合条件的型号，展示最优的 {top_n} 个")
        
        display_df = results.head(top_n).copy()
        for col in targets:
            if col in display_df.columns:
                display_df[col] = display_df[col].map(lambda x: f"{x:.4f}")
        
        # 显示表格
        cols_to_show = ['Model', 'Vendor'] + list(targets.keys()) + ['综合得分']
        available_cols = [c for c in cols_to_show if c in display_df.columns]
        st.dataframe(display_df[available_cols], use_container_width=True)
        
        # 绘图
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

# ========== 查看完整数据库 ==========
with st.expander("📂 查看完整数据库一览"):
    st.dataframe(df, use_container_width=True)
    st.caption(f"共 {len(df)} 条记录")
