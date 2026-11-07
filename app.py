import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
st.set_page_config(page_title="信用買残分析ツール", layout="wide")
st.title("信用買残 ヴィンテージ（形成時期）分析")
52週分のダミーデータ
dates = pd.date_range(end=pd.Timestamp.today(), periods=52, freq="W-FRI")
np.random.seed(42)
price_changes = np.random.normal(loc=0.002, scale=0.03, size=52)
price = 1000 * np.cumprod(1 + price_changes)
margin_buy = 500000 + np.cumsum(np.random.normal(loc=5000, scale=30000, size=52))
margin_buy = np.maximum(margin_buy, 100000)
df = pd.DataFrame({
"Date": dates,
"Close": np.round(price, 1),
"MarginBuy": np.round(margin_buy).astype(int)
})
増減の計算
df["MarginDelta"] = df["MarginBuy"].diff().fillna(df["MarginBuy"].iloc[0])
スライダー
target_idx = st.slider("分析する時点を選択", 0, len(df) - 1, len(df) - 1)
target_date = df.loc[target_idx, "Date"].strftime("%Y-%m-%d")
current_margin = int(df.loc[target_idx, "MarginBuy"])
st.subheader(f"基準日: {target_date} (総買残: {current_margin:,} 株)")
ヴィンテージ計算
remaining = current_margin
vintage_buckets = []
for i in range(target_idx, -1, -1):
d = df.loc[i, "Date"]
delta = df.loc[i, "MarginDelta"]
p = df.loc[i, "Close"]
if delta > 0:
allocated = min(remaining, delta)
remaining = remaining - allocated
age = (df.loc[target_idx, "Date"] - d).days
vintage_buckets.append({
"BuildDate": d,
"Price": p,
"Volume": allocated,
"AgeDays": age
})
if remaining <= 0:
break
v_df = pd.DataFrame(vintage_buckets)
if len(v_df) > 0:
periods = []
for days in v_df["AgeDays"]:
if days <= 30:
periods.append("1ヶ月以内 (短期)")
elif days <= 90:
periods.append("1〜3ヶ月前")
elif days <= 150:
periods.append("3〜5ヶ月前")
else:
periods.append("5ヶ月以上 (期日接近)")
v_df["Period"] = periods
weighted_cost = (v_df["Price"] * v_df["Volume"]).sum() / v_df["Volume"].sum()
current_close = df.loc[target_idx, "Close"]
pnl = ((current_close - weighted_cost) / weighted_cost) * 100
col1, col2, col3 = st.columns(3)
col1.metric("推定・平均建玉コスト", f"{weighted_cost:,.1f} 円")
col2.metric("現在株価", f"{current_close:,.1f} 円")
col3.metric("推定損益率", f"{pnl:+.2f} %")
fig = make_subplots(
rows=2, cols=1,
shared_xaxes=True,
vertical_spacing=0.1,
subplot_titles=("株価と信用買残の推移", "信用買残の時期別構成（いつ作られたか）"),
row_heights=[0.6, 0.4]
)
fig.add_trace(go.Scatter(x=df["Date"], y=df["Close"], name="株価", line=dict(color="#1f77b4", width=2)), row=1, col=1)
fig.add_trace(go.Scatter(x=df["Date"], y=df["MarginBuy"], name="買残", line=dict(color="#ff7f0e", dash="dot"), yaxis="y3"), row=1, col=1)
fig.add_vline(x=df.loc[target_idx, "Date"], line_color="red", line_dash="dash", row=1, col=1)
summary = v_df.groupby("Period", observed=True)["Volume"].sum().reset_index()
fig.add_trace(go.Bar(
x=summary["Period"],
y=summary["Volume"],
marker_color=["#2ca02c", "#bcbd22", "#e377c2", "#d62728"],
text=summary["Volume"].apply(lambda x: f"{x:,} 株"),
textposition="auto"
), row=2, col=1)
fig.update_layout(
height=650,
showlegend=True,
yaxis=dict(title="株価 (円)"),
yaxis3=dict(title="買残 (株)", overlaying="y", side="right"),
margin=dict(l=30, r=30, t=40, b=30)
)
st.plotly_chart(fig, use_container_width=True)
st.write("▼ 時期別の残存内訳")
st.dataframe(v_df[["BuildDate", "AgeDays", "Period", "Price", "Volume"]].rename(columns={
"BuildDate": "形成日",
"AgeDays": "経過日数",
"Period": "期間区分",
"Price": "当時の株価",
"Volume": "推定残存株数"
}))
