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
reader = easyocr.Reader(["en"])
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
is_uploaded = uploaded_img is not None
img = Image.open(uploaded_img).convert("RGB") if is_uploaded else None
img_np = np.array(img) if is_uploaded else None
ocr_res = reader.readtext(img_np) if is_uploaded else []
raw_texts = [r[1].strip() for r in ocr_res]
cleaned = [re.sub(r"[^0-9./]", "", t) for t in raw_texts if len(re.sub(r"[^0-9./]", "", t)) > 0]
date_indices = [i for i, t in enumerate(cleaned) if "/" in t and len(t) >= 5]
ocr_rows = [[cleaned[i]] + [float(cleaned[j].replace(",", "")) for j in range(i+1, min(i+5, len(cleaned))) if "/" not in cleaned[j] and cleaned[j].replace(",", "").replace(".", "").isdigit()][:2] for i in date_indices]
valid_ocr = [r for r in ocr_rows if len(r) == 3]
use_ocr = len(valid_ocr) > 0
df_source = pd.DataFrame(valid_ocr, columns=["DateRaw", "SellRaw", "BuyRaw"]).drop_duplicates(subset=["DateRaw"]) if use_ocr else None
ocr_dates = [f"20{d.split('/')[0]}-{d.split('/')[1].zfill(2)}-{d.split('/')[2].zfill(2)}" if len(d.split("/"))==3 else "2026-01-01" for d in df_source["DateRaw"]] if use_ocr else []
fallback_lines = [re.sub(r"[,/]", " ", l).split() for l in sample_text.strip().splitlines() if len(re.sub(r"[,/]", " ", l).split()) >= 5]
fallback_dates = [f"20{l[0]}-{l[1].zfill(2)}-{l[2].zfill(2)}" for l in fallback_lines]
fallback_sells = [float(l[3]) * 1000 for l in fallback_lines]
fallback_buys = [float(l[4]) * 1000 for l in fallback_lines]
df = pd.DataFrame({"Date": pd.to_datetime(ocr_dates), "Sell": df_source["SellRaw"].astype(float) * 1000, "Buy": df_source["BuyRaw"].astype(float) * 1000}).sort_values("Date").reset_index(drop=True) if use_ocr else pd.DataFrame({"Date": pd.to_datetime(fallback_dates), "Sell": fallback_sells, "Buy": fallback_buys}).sort_values("Date").reset_index(drop=True)
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
