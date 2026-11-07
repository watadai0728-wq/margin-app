import re
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="Margin Vintage Analyzer", layout="wide")
st.title("信用買残 ヴィンテージ分析")

builtin_data = """26/07/08 266.3 13232.6
26/07/09 395.5 12241.3
26/07/10 536.7 13129.0
26/07/13 218.1 14356.4
26/07/14 333.1 13490.9
26/07/15 359.8 12513.1
26/07/16 112.8 14233.7
26/07/17 377.9 13887.9
26/07/21 571.8 11149.9
26/07/22 685.6 10180.8
26/07/23 383.4 10406.8
26/07/24 542.8 11385.7
26/07/27 483.1 11638.6
26/07/28 146.7 13253.4
26/07/29 140.2 13519.4
26/07/30 485.8 12979.9
26/07/31 544.6 12321.6
26/08/03 252.1 11324.1
26/08/05 627.3 11759.6
26/08/06 979.0 12431.7
26/08/07 556.2 13231.0
26/08/10 233.3 12521.2
26/08/12 2.8 11531.4
26/08/13 406.3 10977.1
26/08/14 769.5 12103.5
26/08/17 943.7 10943.2
26/08/19 573.6 14703.5
26/08/20 737.7 14060.8
26/08/21 768.2 13289.5
26/08/24 335.5 14221.1
26/08/25 171.3 14293.7
26/08/26 282.9 14660.7
26/08/27 146.9 14107.3
26/08/28 457.1 16165.8
26/08/31 496.8 15190.6
26/09/03 124.2 13618.4
26/09/04 1014.4 13506.7
26/09/07 903.5 12783.6
26/09/08 403.9 12489.9
26/09/09 25.2 13087.1
26/09/10 47.0 12787.0
26/09/11 698.1 13943.0
26/09/14 435.6 14197.2
26/09/15 439.3 13839.8
26/09/16 76.1 14492.7
26/09/17 150.2 15367.4
26/09/18 767.8 13486.5
26/09/24 441.3 14414.4
26/09/25 836.4 13929.9
26/09/28 445.1 14836.7
26/09/29 515.7 15224.8
26/09/30 996.6 14533.0
26/10/01 427.8 11247.8
26/10/02 2575.9 41467.7
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

st.write("▼ データを追加・変更する場合は貼り付けて下のボタンを押してください：")
raw_input = st.text_area("テキスト入力", value="", height=100, placeholder="証券アプリやWebからコピーした表をそのまま貼り付け")
btn_apply = st.button("このデータで分析を更新する", type="primary")

clean_input = raw_input.strip()
is_custom = len(clean_input) > 0
chosen_text = clean_input if is_custom else builtin_data

norm_lines = [l.replace("　", " ").replace("\t", " ").strip() for l in chosen_text.splitlines() if len(l.strip()) > 0]
raw_matches = [re.search(r"(\d{2,4})[/.-](\d{1,2})[/.-](\d{1,2})\s+([0-9,.\-]+)\s+([0-9,.]+)", l) for l in norm_lines]
valid_matches = [m for m in raw_matches if m is not None]

match_count = len(valid_matches)
st.success("認識されたデータ件数: " + str(match_count) + " 件" + ("（ユーザー入力）" if is_custom else "（内蔵4ヶ月データ）"))

years = [m.group(1) if len(m.group(1)) == 4 else "20" + m.group(1) for m in valid_matches]
dates = [years[i] + "-" + valid_matches[i].group(2).zfill(2) + "-" + valid_matches[i].group(3).zfill(2) for i in range(match_count)]
sells = [abs(float(valid_matches[i].group(4).replace(",", ""))) * 1000 for i in range(match_count)]
buys = [float(valid_matches[i].group(5).replace(",", "")) * 1000 for i in range(match_count)]

parsed_df = pd.DataFrame({"Date": pd.to_datetime(dates), "Sell": sells, "Buy": buys})
df = parsed_df.drop_duplicates(subset=["Date"]).sort_values("Date").reset_index(drop=True)
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

v_recent = int(pos_deltas[sub_df["DaysAgo"] <= 14].sum())
v_1m = int(pos_deltas[(sub_df["DaysAgo"] > 14) & (sub_df["DaysAgo"] <= 45)].sum())
v_3m = int(pos_deltas[(sub_df["DaysAgo"] > 45) & (sub_df["DaysAgo"] <= 90)].sum())
v_accounted = v_recent + v_1m + v_3m
v_old = max(0, curr_buy - v_accounted)

periods = ["直近2週以内", "2週〜1.5ヶ月前", "1.5〜3ヶ月前", "それ以前 (長期塩漬け)"]
volumes = [min(v_recent, curr_buy), min(v_1m, max(0, curr_buy - v_recent)), min(v_3m, max(0, curr_buy - v_recent - v_1m)), v_old]
colors = ["#2ecc71", "#3498db", "#f39c12", "#e74c3c"]
labels = [f"{v:,}株 (" + str(round(v/curr_buy*100, 1) if curr_buy > 0 else 0) + "%)" for v in volumes]

fig = go.Figure(go.Bar(x=periods, y=volumes, marker_color=colors, text=labels, textposition="auto"))
fig.update_layout(height=420, margin=dict(l=20, r=20, t=30, b=20), yaxis_title="株数")
st.plotly_chart(fig, use_container_width=True)

st.write("▼ 読み込み済みデータ一覧（全 " + str(len(df)) + " 営業日分）")
df_display = df.copy()
df_display["Date"] = df_display["Date"].dt.strftime("%Y-%m-%d")
df_display["Buy"] = df_display["Buy"].apply(lambda x: f"{int(x):,}")
df_display["Sell"] = df_display["Sell"].apply(lambda x: f"{int(x):,}")
st.dataframe(df_display[["Date", "Sell", "Buy"]], use_container_width=True)
