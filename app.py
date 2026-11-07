import re
import pytesseract
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from PIL import Image
st.set_page_config(page_title="Margin Vintage Analyzer", layout="wide")
st.title("信用買残 ヴィンテージ分析")
uploaded_files = st.file_uploader("証券画面のスクショ画像（複数可）", type=["png", "jpg", "jpeg"], accept_multiple_files=True)
sample_text = """26/10/02 2575.9 41467.7
26/10/05 2056.6 42876.9
26/10/06 1565.1 42086.1
26/10/07 781.0 44973.7
26/10/08 759.7 43426.2
26/10/09 1503.4 44798.3
26/10/13 737.0 49885.8
26/10/14 1036.4 49852.5
26/10/15 758.9 48809.9
26/10/16 1536.3 47831.1
26/10/19 1469.7 46782.6
26/10/20 1018.9 46816.3
26/10/21 929.6 46590.9
26/10/22 332.6 47705.2
26/10/23 1614.8 48234.5
26/10/26 1146.1 48258.1
26/10/27 883.6 49160.2
26/10/28 1110.2 47255.2
26/10/29 378.3 46751.8
26/10/30 1452.7 47992.4
26/11/02 1056.1 51873.6
26/11/04 1243.7 53575.5
26/11/05 1415.6 54163.1
26/11/06 1272.1 50146.4"""
st.write("またはテキストを直接貼り付け（iPhoneの写真から長押しコピーした文字など）：")
raw_input = st.text_area("テキスト入力", value="", height=120, placeholder="26/11/06 1272.1 50146.4 のように貼り付け")
ocr_lines = []
ocr_debug = ""
if uploaded_files:
for f in uploaded_files:
try:
img = Image.open(f).convert("L")
txt = pytesseract.image_to_string(img, config="--psm 6")
ocr_debug += "\n" + txt
for l in txt.splitlines():
ocr_lines.append(l)
except Exception as e:
pass
target_text = raw_input if len(raw_input.strip()) > 0 else ("\n".join(ocr_lines) if len(ocr_lines) > 0 else sample_text)
parsed_records = []
for line in target_text.splitlines():
m = re.search(r"(\d{2})/.-/.-\s+([0-9,.]+)\s+([0-9,.]+)", line)
if m:
try:
d_str = "20" + m.group(1) + "-" + m.group(2).zfill(2) + "-" + m.group(3).zfill(2)
s_val = float(m.group(4).replace(",", "")) * 1000
b_val = float(m.group(5).replace(",", "")) * 1000
parsed_records.append({"Date": pd.to_datetime(d_str), "Sell": s_val, "Buy": b_val})
except:
pass
if len(parsed_records) > 0:
df = pd.DataFrame(parsed_records).drop_duplicates(subset=["Date"]).sort_values("Date").reset_index(drop=True)
else:
fallback_lines = sample_text.splitlines()
fb_records = []
for l in fallback_lines:
pts = l.split()
fb_records.append({"Date": pd.to_datetime("20" + pts[0].replace("/", "-")), "Sell": float(pts[1])*1000, "Buy": float(pts[2])*1000})
df = pd.DataFrame(fb_records).sort_values("Date").reset_index(drop=True)
if uploaded_files and len(raw_input.strip()) == 0:
st.warning("画像からの数字認識が正確に行えなかったため、サンプルデータを表示しています。下のテキスト枠にコピーした文字を貼り付けてみてください。")
df["Delta"] = df["Buy"].diff().fillna(0)
slider_max = max(1, len(df) - 1)
target_idx = st.slider("分析基準日", 0, slider_max, slider_max)
curr_date = df.loc[target_idx, "Date"].strftime("%Y-%m-%d")
curr_buy = int(df.loc[target_idx, "Buy"])
curr_sell = int(df.loc[target_idx, "Sell"])
st.subheader("基準日: " + curr_date + " (総買残: " + f"{curr_buy:,}" + " 株)")
col1, col2 = st.columns(2)
col1.metric("総信用買残", f"{curr_buy:,}" + " 株")
ratio_val = round(curr_buy / curr_sell, 1) if curr_sell > 0 else 0
col2.metric("総信用売残", f"{curr_sell:,}" + " 株", str(ratio_val) + "倍")
sub_df = df.loc[:target_idx].copy()
sub_df["DaysAgo"] = (df.loc[target_idx, "Date"] - sub_df["Date"]).dt.days
pos_deltas = sub_df["Delta"].clip(lower=0)
v_recent = int(pos_deltas[sub_df["DaysAgo"] <= 7].sum())
v_1m = int(pos_deltas[(sub_df["DaysAgo"] > 7) & (sub_df["DaysAgo"] <= 30)].sum())
v_3m = int(pos_deltas[(sub_df["DaysAgo"] > 30) & (sub_df["DaysAgo"] <= 90)].sum())
v_accounted = v_recent + v_1m + v_3m
v_old = max(0, curr_buy - v_accounted)
periods = ["直近1週以内", "1週〜1ヶ月前", "1〜3ヶ月前", "それ以前 (塩漬け・期日接近)"]
volumes = [min(v_recent, curr_buy), min(v_1m, max(0, curr_buy - v_recent)), min(v_3m, max(0, curr_buy - v_recent - v_1m)), v_old]
colors = ["#2ecc71", "#3498db", "#f39c12", "#e74c3c"]
labels = [f"{v:,}株 (" + str(round(v/curr_buy*100, 1) if curr_buy > 0 else 0) + "%)" for v in volumes]
fig = go.Figure(go.Bar(
x=periods,
y=volumes,
marker_color=colors,
text=labels,
textposition="auto"
))
fig.update_layout(height=420, margin=dict(l=20, r=20, t=30, b=20), yaxis_title="株数")
st.plotly_chart(fig, use_container_width=True)
st.write("▼ 読み込み済みデータ（全 " + str(len(df)) + " 営業日分）")
df_display = df.copy()
df_display["Date"] = df_display["Date"].dt.strftime("%Y-%m-%d")
df_display["Buy"] = df_display["Buy"].apply(lambda x: f"{int(x):,}")
df_display["Sell"] = df_display["Sell"].apply(lambda x: f"{int(x):,}")
st.dataframe(df_display[["Date", "Sell", "Buy"]], use_container_width=True)
