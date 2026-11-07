import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
st.set_page_config(page_title="Margin Analysis", layout="wide")
st.title("信用買残 ヴィンテージ分析")
uploaded = st.file_uploader("株データCSVをアップロード", type=["csv"])
dates_mock = pd.date_range(end=pd.Timestamp.today(), periods=52, freq="W-FRI")
np.random.seed(42)
price_changes = np.random.normal(0.002, 0.03, 52)
price_mock = 1000 * np.cumprod(1 + price_changes)
margin_mock = np.maximum(500000 + np.cumsum(np.random.normal(5000, 30000, 52)), 100000)
df_mock = pd.DataFrame({"Date": dates_mock, "Close": np.round(price_mock, 1), "MarginBuy": np.round(margin_mock).astype(int)})
df = pd.read_csv(uploaded) if uploaded is not None else df_mock
df["Date"] = pd.to_datetime(df["Date"])
df = df.sort_values("Date").reset_index(drop=True)
df["MarginDelta"] = df["MarginBuy"].diff().fillna(df["MarginBuy"].iloc[0])
st.caption("※ CSVを使う場合は「Date（日付）」「Close（終値）」「MarginBuy（信用買残）」の列を含めてください。現在は未アップロードのためサンプル表示中です。" if uploaded is None else "※ アップロードされたデータを表示中")
target_idx = st.slider("分析週の選択", 0, len(df) - 1, len(df) - 1)
target_date = df.loc[target_idx, "Date"].strftime("%Y-%m-%d")
current_margin = int(df.loc[target_idx, "MarginBuy"])
st.subheader(f"基準日: {target_date} (総買残: {current_margin:,} 株)")
sub_df = df.iloc[:target_idx+1].iloc[::-1].copy()
sub_df = sub_df[sub_df["MarginDelta"] > 0].copy()
sub_df["CumAlloc"] = sub_df["MarginDelta"].cumsum()
sub_df["Allocated"] = np.where(sub_df["CumAlloc"] <= current_margin, sub_df["MarginDelta"], np.maximum(0, current_margin - (sub_df["CumAlloc"] - sub_df["MarginDelta"])))
v_df = sub_df[sub_df["Allocated"] > 0].copy()
v_df["AgeDays"] = (df.loc[target_idx, "Date"] - v_df["Date"]).dt.days
v_df["Period"] = np.where(v_df["AgeDays"] <= 30, "1ヶ月以内", np.where(v_df["AgeDays"] <= 90, "1〜3ヶ月前", np.where(v_df["AgeDays"] <= 150, "3〜5ヶ月前", "5ヶ月以上(期日接近)")))
weighted_cost = (v_df["Close"] * v_df["Allocated"]).sum() / v_df["Allocated"].sum() if not v_df.empty and v_df["Allocated"].sum() > 0 else df.loc[target_idx, "Close"]
current_close = df.loc[target_idx, "Close"]
pnl = ((current_close - weighted_cost) / weighted_cost) * 100 if weighted_cost > 0 else 0
col1, col2, col3 = st.columns(3)
col1.metric("推定・平均コスト", f"{weighted_cost:,.1f} 円")
col2.metric("現在株価", f"{current_close:,.1f} 円")
col3.metric("推定損益率", f"{pnl:+.2f} %")
fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.1, subplot_titles=("株価推移と買残", "買残の時期別構成"), row_heights=[0.6, 0.4])
fig.add_trace(go.Scatter(x=df["Date"], y=df["Close"], name="株価", line=dict(color="#1f77b4", width=2)), row=1, col=1)
fig.add_trace(go.Scatter(x=df["Date"], y=df["MarginBuy"], name="信用買残", line=dict(color="#ff7f0e", dash="dot"), yaxis="y3"), row=1, col=1)
fig.add_vline(x=df.loc[target_idx, "Date"], line_color="red", line_dash="dash", row=1, col=1)
summary = v_df.groupby("Period", observed=True)["Allocated"].sum().reset_index() if not v_df.empty else pd.DataFrame({"Period": [], "Allocated": []})
fig.add_trace(go.Bar(x=summary["Period"], y=summary["Allocated"], text=summary["Allocated"].apply(lambda x: f"{int(x):,} 株") if not summary.empty else [], textposition="auto"), row=2, col=1)
fig.update_layout(height=650, showlegend=True, yaxis=dict(title="株価(円)"), yaxis3=dict(title="買残(株)", overlaying="y", side="right"), margin=dict(l=30, r=30, t=40, b=30))
st.plotly_chart(fig, use_container_width=True)
st.dataframe(v_df[["Date", "AgeDays", "Period", "Close", "Allocated"]].rename(columns={"Date": "形成日", "AgeDays": "経過日数", "Period": "区分", "Close": "当時の株価", "Allocated": "推定株数"}))
