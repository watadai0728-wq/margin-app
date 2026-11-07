import re
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
st.set_page_config(page_title="Margin Analyzer", layout="wide")
st.title("📊 信用買残 ヴィンテージ分析")
sample_text = """26/10/26 1146.1 48258.1
26/10/27 883.6 49160.2
26/10/28 1110.2 47255.2
26/10/29 378.3 46751.8
26/10/30 1452.7 47992.4
26/11/2 1056.1 51873.6
26/11/4 1243.7 53575.5
26/11/5 1415.6 54163.1
26/11/6 1272.1 50146.4"""
raw_text = st.text_area("証券会社のデータ（日付 売残 買残）", value=sample_text, height=160)
lines = [re.sub(r"[,/]", " ", l).split() for l in raw_text.strip().splitlines() if len(re.sub(r"[,/]", " ", l).split()) >= 5]
dates = ["20" + l[0] + "-" + l[1].zfill(2) + "-" + l[2].zfill(2) for l in lines]
sells = [float(l[3]) * 1000 for l in lines]
buys = [float(l[4]) * 1000 for l in lines]
df = pd.DataFrame({"Date": dates, "Sell": sells, "Buy": buys})
df["Date"] = pd.to_datetime(df["Date"])
df["Delta"] = df["Buy"].diff().fillna(0)
target_idx = st.slider("分析基準日", 0, len(df)-1, len(df)-1)
curr_date = df.loc[target_idx, "Date"].strftime("%Y-%m-%d")
curr_buy = int(df.loc[target_idx, "Buy"])
curr_sell = int(df.loc[target_idx, "Sell"])
st.subheader(f"基準日: {curr_date} (総買残: {curr_buy:,} 株)")
col1, col2 = st.columns(2)
col1.metric("総信用買残", f"{curr_buy:,} 株")
col2.metric("総信用売残", f"{curr_sell:,} 株", f"倍率 {(curr_buy/curr_sell):.1f}倍" if curr_sell>0 else "")
recent_gain = int(df.loc[:target_idx, "Delta"].clip(lower=0).tail(3).sum())
salt_buy = max(0, curr_buy - recent_gain)
periods = ["直近3日以内 (新規)", "それ以前 (高値塩漬け・しこり玉)"]
volumes = [min(recent_gain, curr_buy), salt_buy]
colors = ["#2ecc71", "#e74c3c"]
fig = go.Figure(go.Bar(
x=periods,
y=volumes,
marker_color=colors,
text=[f"{v:,} 株 ({v/curr_buy*100:.1f}%)" for v in volumes],
textposition="auto"
))
fig.update_layout(height=400, margin=dict(l=20, r=20, t=30, b=20), yaxis_title="株数")
st.plotly_chart(fig, use_container_width=True)
st.write("▼ 入力データの推移")
st.dataframe(df.assign(
Date=df["Date"].dt.strftime("%Y-%m-%d"),
Buy=df["Buy"].apply(lambda x: f"{int(x):,}"),
Sell=df["Sell"].apply(lambda x: f"{int(x):,}")
)[["Date", "Sell", "Buy"]], use_container_width=True)
