import re
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

st.set_page_config(page_title="信用取引ヴィンテージ＆セリクラ分析", layout="wide")
st.title("📊 信用取引 ヴィンテージ＆セリクラ分析")

sample_text = """26/7/31 447.4 1272.1
26/8/3 371.1 1346.2
26/8/4 344.9 1476.4
26/8/5 326.1 1573.8
26/8/6 334.0 1496.6
26/8/7 343.6 1447.2
26/8/10 363.8 1446.7
26/8/12 341.6 1597.4
26/8/13 359.4 1539.1
26/8/14 353.2 1413.6
26/8/17 333.8 1468.6
26/8/18 325.7 1804.4
26/8/19 344.3 1773.2
26/8/20 310.4 1849.3
26/8/21 299.8 1695.9
26/8/24 284.2 1819.3
26/8/25 320.0 1685.9
26/8/28 272.6 1670.4
26/8/31 286.5 1719.8
26/9/1 328.1 1573.5
26/9/2 365.0 1641.6
26/9/3 361.9 1739.0
26/9/4 216.0 2051.6
26/9/7 232.6 2272.7
26/9/8 223.1 2423.3
26/9/14 177.6 2304.8
26/9/15 180.5 2196.5
26/9/16 184.3 2120.4
26/9/17 230.8 1963.7
26/9/18 179.9 2084.7
26/9/24 185.4 2096.6
26/9/25 193.5 2035.0
26/9/28 190.4 2192.7
26/10/1 228.7 2342.0
26/10/2 185.3 2352.4
26/10/5 220.6 2206.8
26/10/6 220.5 2206.4
26/10/7 266.7 2119.3
26/10/8 262.8 2115.7
26/10/9 394.5 1677.7
26/10/13 481.5 1611.4
26/10/19 487.9 1553.0
26/10/20 490.9 1529.1
26/10/21 501.8 1565.4
26/10/22 492.1 1549.6
26/10/23 471.7 1560.6
26/10/26 478.8 1593.8
26/10/27 489.0 1766.7
26/10/28 474.0 2043.5
26/10/29 500.5 2073.8
26/10/30 284.9 2236.6
26/11/2 288.3 2002.6
26/11/4 291.5 2003.8
26/11/5 450.3 1687.6
26/11/6 1177.0 1701.4"""

st.markdown("### 📝 証券会社データの貼り付け")
input_text = st.text_area("日付 売残 買残 の順（スペース・タブ区切り）", value=sample_text, height=140)
update_btn = st.button("🔄 このデータで分析を更新する", type="primary")

raw_matches = re.findall(r"(\d{2,4}[/-]\d{1,2}[/-]\d{1,2})[\s\t]+(-?[\d,.]+?)[\s\t]+([\d,.]+)", input_text)
parsed_dates = [m[0].replace("/", "-") for m in raw_matches]
parsed_sells = [float(m[1].replace(",", "")) * 1000 for m in raw_matches]
parsed_buys = [float(m[2].replace(",", "")) * 1000 for m in raw_matches]

df = pd.DataFrame({"Date": parsed_dates, "MarginSell": parsed_sells, "MarginBuy": parsed_buys})
df["Date"] = pd.to_datetime(df["Date"], format="mixed")
df = df.drop_duplicates(subset=["Date"]).sort_values("Date").reset_index(drop=True)

slider_max = max(1, len(df) - 1)
target_idx = st.slider("分析基準日（スライダーで過去日へ遡れます）", min_value=0, max_value=slider_max, value=slider_max)

sub_df = df.iloc[:target_idx + 1].copy()
cur_row = sub_df.iloc[-1]
cur_buy = cur_row["MarginBuy"]
cur_sell = cur_row["MarginSell"]
cur_ratio = round(cur_buy / max(1.0, cur_sell), 2)
cur_date_str = cur_row["Date"].strftime("%Y-%m-%d")

# 増減の算出
sub_df["Buy_Diff"] = sub_df["MarginBuy"].diff().fillna(0)
recent_3days_add = sub_df.iloc[-3:]["Buy_Diff"].apply(lambda x: max(0.0, x)).sum()
recent_14days_add = sub_df.iloc[-10:]["Buy_Diff"].apply(lambda x: max(0.0, x)).sum()
recent_30days_add = sub_df.iloc[-22:]["Buy_Diff"].apply(lambda x: max(0.0, x)).sum()

v_recent = min(cur_buy, recent_3days_add)
v_mid = min(cur_buy - v_recent, max(0.0, recent_14days_add - recent_3days_add))
v_old = min(cur_buy - v_recent - v_mid, max(0.0, recent_30days_add - recent_14days_add))
v_stale = max(0.0, cur_buy - (v_recent + v_mid + v_old))

pct_recent = round(v_recent / max(1.0, cur_buy) * 100, 1)
pct_mid = round(v_mid / max(1.0, cur_buy) * 100, 1)
pct_old = round(v_old / max(1.0, cur_buy) * 100, 1)
pct_stale = round(v_stale / max(1.0, cur_buy) * 100, 1)

# セリクラ判定ロジック
peak_buy_idx = sub_df["MarginBuy"].idxmax()
peak_row = sub_df.loc[peak_buy_idx]
peak_date = peak_row["Date"]
peak_buy = peak_row["MarginBuy"]
days_from_peak = (cur_row["Date"] - peak_date).days
due_date = peak_date + pd.DateOffset(months=6)

latest_buy_diff = cur_row["Buy_Diff"]
avg_buy = sub_df["MarginBuy"].mean()
is_panic_drop = latest_buy_diff < -(avg_buy * 0.08)
is_near_due = (140 <= days_from_peak <= 190)

status_title = "🟢 需給正常・推移観察"
status_msg = "急激な投げ売りや期日集中シグナルは現在検知されていません。"
status_type = "info"

status_title = "⚠️ 【セリクラ警戒】6ヶ月期日の集中接近中" if is_near_due else status_title
status_msg = "買残ピーク（" + peak_date.strftime("%Y/%m/%d") + "）から約" + str(days_from_peak) + "日が経過。6ヶ月期日強制決済（" + due_date.strftime("%Y/%m/%d") + " 前後）に伴う処分売りに警戒が必要です。" if is_near_due else status_msg
status_type = "warning" if is_near_due else status_type

status_title = "🔥 【セリクラ発生中】大底・底入れ接近シグナル" if is_panic_drop else status_title
status_msg = "直近で買残の大幅な急減（" + f"{int(latest_buy_diff):,}" + "株）を検知。個人投資家のパニック投げ売り・追証整理が進行しており、需給の大底形成シグナルです。" if is_panic_drop else status_msg
status_type = "error" if is_panic_drop else status_type

st.markdown("---")
st.markdown("## 🎯 セリクラ（大底）シグナル判定")
st.markdown("#### " + status_title)
st.write(status_msg)

st.markdown("---")
c1, c2, c3, c4 = st.columns(4)
c1.metric("分析基準日", cur_date_str)
c2.metric("総信用買残", f"{int(cur_buy):,} 株")
c3.metric("総信用売残", f"{int(cur_sell):,} 株")
c4.metric("信用倍率", f"{cur_ratio} 倍")

st.markdown("### ⏳ 信用期日カレンダー（強制決済ターゲット）")
col_p1, col_p2 = st.columns(2)
col_p1.metric("買残ピーク日", peak_date.strftime("%Y-%m-%d"), f"ピーク株数: {int(peak_buy):,} 株")
col_p2.metric("6ヶ月強制決済期日", due_date.strftime("%Y-%m-%d"), f"ピークから {days_from_peak} 日経過")

st.markdown("### 📊 建玉ヴィンテージ比率（年齢・しこり構成）")
fig = go.Figure(data=[
    go.Bar(name="直近3日以内 (短期・新規)", x=["買残内訳"], y=[v_recent], text=[str(pct_recent) + "%"], textposition="auto", marker_color="#2ecc71"),
    go.Bar(name="4日〜2週間 (中期玉)", x=["買残内訳"], y=[v_mid], text=[str(pct_mid) + "%"], textposition="auto", marker_color="#f1c40f"),
    go.Bar(name="2週間〜1ヶ月 (捕まりかけ玉)", x=["買残内訳"], y=[v_old], text=[str(pct_old) + "%"], textposition="auto", marker_color="#e67e22"),
    go.Bar(name="1ヶ月以上前 (塩漬け・しこり玉)", x=["買残内訳"], y=[v_stale], text=[str(pct_stale) + "%"], textposition="auto", marker_color="#e74c3c")
])
fig.update_layout(barmode="stack", height=420, template="plotly_dark", yaxis_title="株数")
st.plotly_chart(fig, use_container_width=True)

st.markdown("### 📋 入力データ一覧")
st.dataframe(sub_df[["Date", "MarginSell", "MarginBuy", "Buy_Diff"]].tail(15), use_container_width=True)
