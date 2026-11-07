import re
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

st.set_page_config(page_title="信用取引ヴィンテージ＆セリクラ分析", layout="wide")
st.title("📊 信用取引 ヴィンテージ＆セリクラ分析")

sample_text = """26/7/23 1199.0 10923.3
26/7/24 1168.0 10964.8
26/7/27 1103.8 11528.1
26/7/28 1080.7 11869.6
26/7/29 1077.5 11934.2
26/7/30 975.6 11935.7
26/7/31 1312.9 12349.5
26/8/3 1211.3 13582.6
26/8/6 1252.3 13241.7
26/8/7 131.4 11372.7
26/8/10 122.2 11563.3
26/8/12 331.9 10960.5
26/8/13 364.6 10616.6
26/8/14 418.4 10424.8
26/8/17 747.7 10538.5
26/8/18 696.1 10929.8
26/8/19 622.4 11625.2
26/8/20 602.1 12225.6
26/8/21 270.6 11862.7
26/8/24 250.0 11914.8
26/8/25 218.3 11848.6
26/8/26 260.8 11748.5
26/8/27 240.2 11682.9
26/8/28 299.5 12426.4
26/8/31 434.6 11795.3
26/9/1 367.3 11681.8
26/9/2 357.9 12004.8
26/9/3 331.2 12320.6
26/9/4 254.4 11890.4
26/9/7 261.5 11450.0
26/9/8 226.0 12763.1
26/9/9 391.0 11673.8
26/9/10 324.5 12715.4
26/9/11 286.0 12536.1
26/9/14 241.7 12979.0
26/9/15 282.1 13121.2
26/9/16 355.5 12973.1
26/9/17 351.5 13059.6
26/9/18 298.7 12197.1
26/9/24 595.8 11012.5
26/9/25 347.7 11355.3
26/9/28 508.2 11337.7
26/9/29 540.7 11521.2
26/9/30 1076.1 11033.6
26/10/1 1138.5 11102.0
26/10/2 360.0 10394.4
26/10/5 353.0 10470.2
26/10/6 496.5 10119.4
26/10/7 598.2 10140.9
26/10/8 508.9 10169.6
26/10/9 275.1 10085.2
26/10/13 352.2 9993.8
26/10/14 444.3 9900.0
26/10/15 378.7 10308.8
26/10/16 230.1 10086.9
26/10/19 282.3 10772.0
26/10/20 298.8 11902.2
26/10/21 502.1 11801.6
26/10/22 672.4 12725.4
26/10/23 309.7 12027.4
26/10/26 278.2 12568.1
26/10/27 440.9 12143.0
26/10/28 583.4 12288.9
26/10/29 649.1 12226.8
26/10/30 359.4 13082.2
26/11/2 395.7 13980.1
26/11/4 569.3 15184.9
26/11/5 561.2 16320.9
26/11/6 546.9 15142.1"""

st.markdown("### 📝 証券会社データの貼り付け")
input_text = st.text_area("日付 売残 買残 の順（スペース・タブ区切り）", value=sample_text, height=140)
update_btn = st.button("🔄 このデータで分析を更新する", type="primary")

raw_matches = re.findall(r"(\d{2,4})[/-](\d{1,2})[/-](\d{1,2})[\s\t]+(-?[\d,.]+?)[\s\t]+([\d,.]+)", input_text)
parsed_dates = [("20" + m[0] if len(m[0]) == 2 else m[0]) + "-" + m[1].zfill(2) + "-" + m[2].zfill(2) for m in raw_matches]
parsed_sells = [float(m[3].replace(",", "")) * 1000 for m in raw_matches]
parsed_buys = [float(m[4].replace(",", "")) * 1000 for m in raw_matches]

df = pd.DataFrame({"Date": parsed_dates, "MarginSell": parsed_sells, "MarginBuy": parsed_buys})
df["Date"] = pd.to_datetime(df["Date"], format="%Y-%m-%d")
df = df.drop_duplicates(subset=["Date"]).sort_values("Date").reset_index(drop=True)
df["Buy_Diff"] = df["MarginBuy"].diff().fillna(0)

# 全日程のヴィンテージ数値を一括事前計算
all_recent = [min(df.loc[i, "MarginBuy"], df.loc[max(0, i-2):i, "Buy_Diff"].apply(lambda x: max(0.0, x)).sum()) for i in range(len(df))]
all_mid_add = [df.loc[max(0, i-9):i, "Buy_Diff"].apply(lambda x: max(0.0, x)).sum() for i in range(len(df))]
all_mid = [min(df.loc[i, "MarginBuy"] - all_recent[i], max(0.0, all_mid_add[i] - df.loc[max(0, i-2):i, "Buy_Diff"].apply(lambda x: max(0.0, x)).sum())) for i in range(len(df))]
all_old_add = [df.loc[max(0, i-21):i, "Buy_Diff"].apply(lambda x: max(0.0, x)).sum() for i in range(len(df))]
all_old = [min(df.loc[i, "MarginBuy"] - all_recent[i] - all_mid[i], max(0.0, all_old_add[i] - all_mid_add[i])) for i in range(len(df))]
all_stale = [max(0.0, df.loc[i, "MarginBuy"] - (all_recent[i] + all_mid[i] + all_old[i])) for i in range(len(df))]

last_idx = len(df) - 1
cur_row = df.iloc[-1]
cur_buy = cur_row["MarginBuy"]
cur_sell = cur_row["MarginSell"]
cur_ratio = round(cur_buy / max(1.0, cur_sell), 2)
cur_date_str = cur_row["Date"].strftime("%Y-%m-%d")
latest_buy_diff = cur_row["Buy_Diff"]

peak_buy_idx = df["MarginBuy"].idxmax()
peak_row = df.loc[peak_buy_idx]
peak_date = peak_row["Date"]
peak_buy = peak_row["MarginBuy"]
days_from_peak = (cur_row["Date"] - peak_date).days
due_date = peak_date + pd.DateOffset(months=6)

avg_buy = df["MarginBuy"].mean()
is_panic_drop = latest_buy_diff < -(avg_buy * 0.08)
is_near_due = (140 <= days_from_peak <= 190)

status_title = "🟢 需給正常・推移観察"
status_msg = "急激な投げ売りや期日集中シグナルは現在検知されていません。"
status_title = "⚠️ 【セリクラ警戒】6ヶ月期日の集中接近中" if is_near_due else status_title
status_msg = "買残ピーク（" + peak_date.strftime("%Y/%m/%d") + "）から約" + str(days_from_peak) + "日が経過。6ヶ月期日強制決済（" + due_date.strftime("%Y/%m/%d") + " 前後）に伴う処分売りに警戒が必要です。" if is_near_due else status_msg
status_title = "🔥 【セリクラ発生中】大底・底入れ接近シグナル" if is_panic_drop else status_title
status_msg = "直近で買残の大幅な急減（" + f"{int(latest_buy_diff):,}" + "株）を検知。個人投資家のパニック投げ売り・追証整理が進行しており、需給の大底形成シグナルです。" if is_panic_drop else status_msg

st.markdown("---")
st.markdown("## 🎯 セリクラ（大底）シグナル判定（最新基準）")
st.markdown("#### " + status_title)
st.write(status_msg)

st.markdown("---")
c1, c2, c3, c4 = st.columns(4)
c1.metric("最新基準日", cur_date_str)
c2.metric("総信用買残", f"{int(cur_buy):,} 株")
c3.metric("総信用売残", f"{int(cur_sell):,} 株")
c4.metric("信用倍率", f"{cur_ratio} 倍")

st.markdown("### ⏳ 信用期日カレンダー（強制決済ターゲット）")
col_p1, col_p2 = st.columns(2)
col_p1.metric("買残ピーク日", peak_date.strftime("%Y-%m-%d"), f"ピーク株数: {int(peak_buy):,} 株")
col_p2.metric("6ヶ月強制決済期日", due_date.strftime("%Y-%m-%d"), f"ピークから {days_from_peak} 日経過")

st.markdown("### 📊 建玉ヴィンテージ比率（ぬるぬるシークバー内蔵）")

date_labels = [d.strftime("%m/%d") for d in df["Date"]]

# Plotlyのクライアントサイド・アニメーションフレーム（ブラウザ側で即座に動く）
frames = [go.Frame(data=[
    go.Bar(y=[all_recent[k]], text=[f"{round(all_recent[k]/max(1.0, df.loc[k, 'MarginBuy'])*100, 1)}%"]),
    go.Bar(y=[all_mid[k]], text=[f"{round(all_mid[k]/max(1.0, df.loc[k, 'MarginBuy'])*100, 1)}%"]),
    go.Bar(y=[all_old[k]], text=[f"{round(all_old[k]/max(1.0, df.loc[k, 'MarginBuy'])*100, 1)}%"]),
    go.Bar(y=[all_stale[k]], text=[f"{round(all_stale[k]/max(1.0, df.loc[k, 'MarginBuy'])*100, 1)}%"])
], name=str(k), layout=go.Layout(title=f"基準日: {df.loc[k, 'Date'].strftime('%Y-%m-%d')} (総買残: {int(df.loc[k, 'MarginBuy']):,}株)")) for k in range(len(df))]

slider_steps = [{"args": [[str(k)], {"frame": {"duration": 0, "redraw": True}, "mode": "immediate", "transition": {"duration": 0}}], "label": date_labels[k], "method": "animate"} for k in range(len(df))]

fig = go.Figure(
    data=[
        go.Bar(name="直近3日以内 (短期・新規)", x=["買残内訳"], y=[all_recent[-1]], text=[f"{round(all_recent[-1]/max(1.0, cur_buy)*100, 1)}%"], textposition="auto", marker_color="#2ecc71"),
        go.Bar(name="4日〜2週間 (中期玉)", x=["買残内訳"], y=[all_mid[-1]], text=[f"{round(all_mid[-1]/max(1.0, cur_buy)*100, 1)}%"], textposition="auto", marker_color="#f1c40f"),
        go.Bar(name="2週間〜1ヶ月 (捕まりかけ玉)", x=["買残内訳"], y=[all_old[-1]], text=[f"{round(all_old[-1]/max(1.0, cur_buy)*100, 1)}%"], textposition="auto", marker_color="#e67e22"),
        go.Bar(name="1ヶ月以上前 (塩漬け・しこり玉)", x=["買残内訳"], y=[all_stale[-1]], text=[f"{round(all_stale[-1]/max(1.0, cur_buy)*100, 1)}%"], textposition="auto", marker_color="#e74c3c")
    ],
    frames=frames
)

max_y = df["MarginBuy"].max() * 1.15
fig.update_layout(
    barmode="stack",
    height=480,
    template="plotly_dark",
    yaxis_title="株数",
    yaxis_range=[0, max_y],
    title=f"基準日: {cur_date_str} (総買残: {int(cur_buy):,}株)",
    sliders=[{
        "active": last_idx,
        "yanchor": "top",
        "xanchor": "left",
        "currentvalue": {"font": {"size": 13, "color": "#00e676"}, "prefix": "📅 選択日付: ", "visible": True, "xanchor": "right"},
        "transition": {"duration": 0},
        "pad": {"b": 10, "t": 30},
        "len": 1.0,
        "x": 0.0,
        "y": 0,
        "steps": slider_steps
    }]
)

st.plotly_chart(fig, use_container_width=True)

st.markdown("---")
st.markdown("### 📋 入力データ一覧")
st.dataframe(df[["Date", "MarginSell", "MarginBuy", "Buy_Diff"]].tail(15), use_container_width=True)
