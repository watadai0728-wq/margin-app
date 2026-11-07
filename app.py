import io
import re
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
st.set_page_config(page_title="Margin Vintage Analyzer", layout="wide")
st.title("📊 信用買残 ヴィンテージ分析")
st.markdown("""
証券会社のサイト（SBI証券、楽天証券、株探など）の「過去情報」や「時系列テーブル」をコピーして下の枠に貼り付けるだけで、正確な数値をもとに分析できます。
""")
sample_text = """日付\t売残\t買残\t信用倍率
26/10/26\t1,146.1\t48,258.1\t42.10
26/10/27\t883.6\t49,160.2\t55.63
26/10/28\t1,110.2\t47,255.2\t42.56
26/10/29\t378.3\t46,751.8\t123.58
26/10/30\t1,452.7\t47,992.4\t33.03
26/11/2\t1,056.1\t51,873.6\t49.11
26/11/4\t1,243.7\t53,575.5\t43.07
26/11/5\t1,415.6\t54,163.1\t38.26
26/11/6\t1,272.1\t50,146.4\t39.42"""
raw_text = st.text_area(
"証券会社の表データを貼り付け（タブ/カンマ/スペース区切り自動対応）",
value=sample_text,
height=180
)
multiplier = st.selectbox(
"買残・売残の単位",
[1000, 1, 100],
format_func=lambda x: "千株（画像の表示単位：×1,000）" if x == 1000 else ("株（実数）" if x == 1 else "単元（×100）")
)
df = None
if raw_text.strip():
try:
lines = [line.strip() for line in raw_text.strip().splitlines() if line.strip()]
rows = []
for line in lines:
parts = re.split(r"[\t, ]+", line.replace(",", ""))
parts = [p.strip() for p in parts if p.strip()]
if len(parts) >= 3 and any(char.isdigit() for char in parts[0]):
date_str = parts[0]
try:
sell_val = float(parts[1])
buy_val = float(parts[2])
close_val = float(parts[3]) if len(parts) >= 4 and not "/" in parts[3] else np.nan
rows.append({"Date": date_str, "MarginSell": sell_val, "MarginBuy": buy_val, "Close": close_val})
except ValueError:
continue
if rows:
df = pd.DataFrame(rows)
# 日付パース
df["Date"] = pd.to_datetime(df["Date"], format="%y/%m/%d", errors="coerce")
df["Date"] = df["Date"].fillna(pd.to_datetime(df["Date"], errors="coerce"))
df["MarginBuy"] = df["MarginBuy"] * multiplier
df["MarginSell"] = df["MarginSell"] * multiplier
df = df.sort_values("Date").reset_index(drop=True)
df["MarginDelta"] = df["MarginBuy"].diff().fillna(0)
except Exception as e:
st.error(f"データ解析エラー: {e}")
if df is not None and len(df) > 0:
st.success(f"データ読込完了：{len(df)} 件の時系列レコード")
target_idx = st.slider("分析基準日の選択", 0, len(df) - 1, len(df) - 1)
target_date = df.loc[target_idx, "Date"].strftime("%Y-%m-%d")
current_margin = int(df.loc[target_idx, "MarginBuy"])
st.subheader(f"基準日: {target_date} (総買残: {current_margin:,} 株)")
# FIFOによるヴィンテージ逆算
remaining = current_margin
vintage_buckets = []
for i in range(target_idx, -1, -1):
d = df.loc[i, "Date"]
delta = df.loc[i, "MarginDelta"]
close_p = df.loc[i, "Close"]
if delta > 0:
allocated = min(remaining, delta)
remaining -= allocated
vintage_buckets.append({
"Date": d,
"Close": close_p,
"Volume": allocated,
"AgeDays": (df.loc[target_idx, "Date"] - d).days
})
if remaining <= 0:
break
# 残余分（データ期間より前に建てられた玉）
if remaining > 0:
vintage_buckets.append({
"Date": df.loc[0, "Date"],
"Close": df.loc[0, "Close"],
"Volume": remaining,
"AgeDays": 180
})
v_df = pd.DataFrame(vintage_buckets)
def classify_period(days):
if days <= 7:
return "直近1週間以内"
elif days <= 30:
return "1ヶ月以内"
elif days <= 90:
return "1〜3ヶ月前"
elif days <= 150:
return "3〜5ヶ月前"
else:
return "5ヶ月以上前（期日接近・塩漬け）"
v_df["Period"] = v_df["AgeDays"].apply(classify_period)
# 集計と指標表示
col1, col2 = st.columns(2)
col1.metric("総信用買残", f"{current_margin:,} 株")
current_sell = int(df.loc[target_idx, "MarginSell"])
col2.metric("総信用売残", f"{current_sell:,} 株", delta=f"倍率 {(current_margin / current_sell):.2f}倍" if current_sell > 0 else None)
# ヴィンテージグラフ描画
period_order = ["直近1週間以内", "1ヶ月以内", "1〜3ヶ月前", "3〜5ヶ月前", "5ヶ月以上前（期日接近・塩漬け）"]
v_summary = v_df.groupby("Period")["Volume"].sum().reindex(period_order).fillna(0).reset_index()
v_summary["Share"] = (v_summary["Volume"] / current_margin) * 100
fig = go.Figure()
fig.add_trace(go.Bar(
x=v_summary["Period"],
y=v_summary["Volume"],
text=[f"{int(v):,}株
({s:.1f}%)" if v > 0 else "" for v, s in zip(v_summary["Volume"], v_summary["Share"])],
textposition="auto",
marker_color=["#2ecc71", "#3498db", "#f39c12", "#e67e22", "#e74c3c"]
))
fig.update_layout(
title=f"買残の時期別構成（建玉ヴィンテージ比率）",
xaxis_title="形成時期区分",
yaxis_title="株数",
height=450,
margin=dict(l=20, r=20, t=50, b=30)
)
st.plotly_chart(fig, use_container_width=True)
# 詳細テーブル
st.write("▼ 内訳詳細")
disp_df = v_df[["Date", "Period", "AgeDays", "Volume"]].copy()
disp_df["Date"] = disp_df["Date"].dt.strftime("%Y-%m-%d")
disp_df["Volume"] = disp_df["Volume"].apply(lambda x: f"{int(x):,} 株")
disp_df = disp_df.rename(columns={"Date": "形成日", "Period": "区分", "AgeDays": "経過日数", "Volume": "推定株数"})
st.dataframe(disp_df, use_container_width=True)
else:
st.warning("有効なデータがありません。テキストエリアにデータを貼り付けてください。")
