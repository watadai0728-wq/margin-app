import re
import cv2
import easyocr
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from PIL import Image
st.set_page_config(page_title="Margin OCR Analyzer", layout="wide")
st.title("📊 信用買残 スクショ画像分析")
@st.cache_resource
def load_ocr():
return easyocr.Reader(["en"])
reader = load_ocr()
uploaded_img = st.file_uploader("証券画面のスクショ画像をアップロード", type=["png", "jpg", "jpeg"])
sample_text = """26/10/26 1146.1 48258.1
26/10/27 883.6 49160.2
26/10/28 1110.2 47255.2
26/10/29 378.3 46751.8
26/10/30 1452.7 47992.4
26/11/2 1056.1 51873.6
26/11/4 1243.7 53575.5
26/11/5 1415.6 54163.1
26/11/6 1272.1 50146.4"""
extracted_rows = []
if uploaded_img is not None:
img = Image.open(uploaded_img).convert("RGB")
st.image(img, caption="アップロードされた画像", use_container_width=True)
img_np = np.array(img)
ocr_results = reader.readtext(img_np)
all_texts = [r[1].strip() for r in ocr_results]
cleaned = []
for t in all_texts:
t_clean = re.sub(r"[^0-9./]", "", t)
if len(t_clean) > 0:
cleaned.append(t_clean)
for i in range(len(cleaned)):
token = cleaned[i]
if "/" in token and len(token) >= 5:
date_val = token
nums = []
for j in range(i + 1, min(i + 5, len(cleaned))):
candidate = cleaned[j].replace(",", "")
if "/" not in candidate:
try:
nums.append(float(candidate))
except:
pass
if len(nums) >= 2:
extracted_rows.append([date_val, nums[0], nums[1]])
if len(extracted_rows) > 0:
st.success(f"画像から {len(extracted_rows)} 件のデータを検出しました！")
df_raw = pd.DataFrame(extracted_rows, columns=["DateRaw", "SellRaw", "BuyRaw"]).drop_duplicates(subset=["DateRaw"])
dates_list = []
for d in df_raw["DateRaw"]:
parts = d.split("/")
if len(parts) == 3:
y = "20" + parts[0] if len(parts[0]) == 2 else parts[0]
dates_list.append(f"{y}-{parts[1].zfill(2)}-{parts[2].zfill(2)}")
else:
dates_list.append("2026-01-01")
df = pd.DataFrame({
"Date": pd.to_datetime(dates_list),
"Sell": df_raw["SellRaw"].astype(float) * 1000,
"Buy": df_raw["BuyRaw"].astype(float) * 1000
}).sort_values("Date").reset_index(drop=True)
else:
if uploaded_img is not None:
st.warning("画像から数値を認識できませんでした。下のサンプルデータで表示します。")
lines = [re.sub(r"[,/]", " ", l).split() for l in sample_text.strip().splitlines() if len(re.sub(r"[,/]", " ", l).split()) >= 5]
dates = ["20" + l[0] + "-" + l[1].zfill(2) + "-" + l[2].zfill(2) for l in lines]
sells = [float(l[3]) * 1000 for l in lines]
buys = [float(l[4]) * 1000 for l in lines]
df = pd.DataFrame({"Date": pd.to_datetime(dates), "Sell": sells, "Buy": buys}).sort_values("Date").reset_index(drop=True)
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
st.write("▼ 認識・計算データ推移")
st.dataframe(df.assign(
Date=df["Date"].dt.strftime("%Y-%m-%d"),
Buy=df["Buy"].apply(lambda x: f"{int(x):,}"),
Sell=df["Sell"].apply(lambda x: f"{int(x):,}")
)[["Date", "Sell", "Buy"]], use_container_width=True)
