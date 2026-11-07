import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
st.set_page_config(page_title="信用買残ヴィンテージ分析ツール", layout="wide")
st.title("📊 信用買残 ヴィンテージ（形成時期）分析ツール")
st.markdown("""
公表される信用買残の推移から、「現在の買残がいつ建てられたものか」をFIFO（先入先出）モデルで逆算・推定します。
""")
--- サイドバー：データ入力・設定 ---
st.sidebar.header("設定 & データ")
data_source = st.sidebar.radio("データソース", ["デモ用サンプルデータを生成", "CSVをアップロード"])
df = None
if data_source == "デモ用サンプルデータを生成":
dates = pd.date_range(end=pd.Timestamp.today(), periods=52, freq="W-FRI")
np.random.seed(42)
price_changes = np.random.normal(loc=0.002, scale=0.03, size=len(dates))
price = 1000 * np.cumprod(1 + price_changes)
margin_buy = 500000 + np.cumsum(np.random.normal(loc=5000, scale=30000, size=len(dates)))
margin_buy = np.maximum(margin_buy, 100000)
df = pd.DataFrame({
"Date": dates,
"Close": np.round(price, 1),
"MarginBuy": np.round(margin_buy).astype(int)
})
st.sidebar.success("サンプルデータを読み込みました")
else:
uploaded_file = st.sidebar.file_uploader("CSVファイルをアップロード", type=["csv"])
st.sidebar.caption("※ 必須カラム: Date（日付）, Close（終値）, MarginBuy（信用買残）")
if uploaded_file is not None:
df = pd.read_csv(uploaded_file)
df["Date"] = pd.to_datetime(df["Date"])
df = df.sort_values("Date").reset_index(drop=True)
if df is not None:
df["MarginDelta"] = df["MarginBuy"].diff().fillna(df["MarginBuy"].iloc[0])
target_idx = st.slider(
"分析対象の日付を選択",
min_value=0,
max_value=len(df) - 1,
value=len(df) - 1,
format="%d"
)
target_date = df.loc[target_idx, "Date"].strftime("%Y-%m-%d")
current_margin = df.loc[target_idx, "MarginBuy"]
st.subheader(f"基準日: {target_date} (総買残: {current_margin:,} 株)")
remaining = current_margin
vintage_buckets = []
for i in range(target_idx, -1, -1):
d = df.loc[i, "Date"]
delta = df.loc[i, "MarginDelta"]
p = df.loc[i, "Close"]
if delta > 0:
allocated = min(remaining, delta)
remaining -= allocated
age_days = (df.loc[target_idx, "Date"] - d).days
vintage_buckets.append({
"BuildDate": d,
"Price": p,
"Volume": allocated,
"AgeDays": age_days
})
if remaining <= 0:
break
v_df = pd.DataFrame(vintage_buckets)
def get_period_label(days):
if days <= 30:
return "1ヶ月以内 (短期)"
elif days <= 90:
return "1〜3ヶ月前"
elif days <= 150:
return "3〜5ヶ月前"
else:
return "5ヶ月以上 (期日接近/超)"
if not v_df.empty:
v_df["Period"] = v_df["AgeDays"].apply(get_period_label)
col1, col2, col3 = st.columns(3)
weighted_cost = (v_df["Price"] * v_df["Volume"]).sum() / v_df["Volume"].sum()
current_close = df.loc[target_idx, "Close"]
pnl_pct = ((current_close - weighted_cost) / weighted_cost) * 100
col1.metric("推定・平均建玉コスト", f"{weighted_cost:,.1f} 円")
col2.metric("現在株価", f"{current_close:,.1f} 円")
col3.metric("推定損益率", f"{pnl_pct:+.2f} %", delta=f"{pnl_pct:+.2f}%")
fig = make_subplots(
rows=2, cols=1,
shared_xaxes=True,
vertical_spacing=0.08,
subplot_titles=("株価推移と信用買残推移", "基準日における買残の時期別構成（ヴィンテージ）"),
row_heights=[0.6, 0.4]
)
fig.add_trace(go.Scatter(x=df["Date"], y=df["Close"], name="株価", line=dict(color="#1f77b4", width=2)), row=1, col=1)
fig.add_trace(go.Scatter(x=df["Date"], y=df["MarginBuy"], name="信用買残", line=dict(color="#ff7f0e", dash="dot"), yaxis="y3"), row=1, col=1)
fig.add_vline(x=df.loc[target_idx, "Date"], line_width=1.5, line_dash="dash", line_color="red", row=1, col=1)
period_summary = v_df.groupby("Period", observed=True)["Volume"].sum().reset_index()
fig.add_trace(go.Bar(
x=period_summary["Period"],
y=period_summary["Volume"],
marker_color=["#2ca02c", "#bcbd22", "#e377c2", "#d62728"],
text=period_summary["Volume"].apply(lambda x: f"{x:,} 株"),
textposition="auto"
), row=2, col=1)
fig.update_layout(
height=700,
showlegend=True,
yaxis=dict(title="株価 (円)"),
yaxis3=dict(title="信用買残 (株)", overlaying="y", side="right"),
margin=dict(l=40, r=40, t=40, b=40)
)
st.plotly_chart(fig, use_container_width=True)
st.write("▼ 建て時期ごとの詳細内訳")
st.dataframe(v_df[["BuildDate", "AgeDays", "Period", "Price", "Volume"]].rename(columns={
"BuildDate": "形成日",
"AgeDays": "経過日数",
"Period": "期間区分",
"Price": "当時の株価",
"Volume": "推定残存株数"
}))
else:
st.info("左側のサイドバーからデータを読み込んでください。")
