import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from datetime import datetime

# ── 頁面設定 ──────────────────────────────────────────────────
st.set_page_config(
    page_title="Kitty 投資組合 | CFA 儀表板",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── 深色主題 CSS ──────────────────────────────────────────────
st.markdown("""
<style>
  .stApp { background-color: #0D1117; color: #E6EDF3; }
  section[data-testid="stSidebar"] { background-color: #161B22; }
  .metric-card {
    background: #161B22;
    border: 1px solid #30363D;
    border-radius: 10px;
    padding: 16px 20px;
    text-align: center;
  }
  .metric-label { color: #8B949E; font-size: 12px; margin-bottom: 4px; }
  .metric-value { font-size: 22px; font-weight: bold; }
  .alert-red   { border-color: #F85149; background: #F8514910; }
  .alert-yellow { border-color: #E3B341; background: #E3B34110; }
  .alert-green  { border-color: #3FB950; background: #3FB95010; }
  .alert-teal   { border-color: #56D364; background: #56D36410; }
  .section-header {
    background: #161B22;
    border-left: 4px solid #58A6FF;
    padding: 8px 16px;
    margin: 20px 0 12px 0;
    border-radius: 0 8px 8px 0;
    font-size: 15px;
    font-weight: bold;
    color: #58A6FF;
  }
  .insight-box {
    background: #161B22;
    border: 1px solid #30363D;
    border-radius: 8px;
    padding: 14px;
    margin: 6px 0;
  }
  div[data-testid="stMetric"] { background: #161B22; border-radius: 8px; padding: 10px; }
  div[data-testid="stMetric"] label { color: #8B949E !important; }
  .stDataFrame { background: #161B22; }
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# 設定
# ══════════════════════════════════════════════════════════════
SHEET_URL = (
    "https://docs.google.com/spreadsheets/d/"
    "1-GHglq7SWRqtxFeF8EpUkFBVqK5dxhGvUxXS14A2TVw"
    "/export?format=csv&gid=763823790"
)

GOAL = 2_000_000

SECTOR_MAP = {
    "ARM":    ("半導體",    "美股"),
    "GLD":    ("黃金/避險", "美股"),
    "IWM":    ("廣市場ETF", "美股"),
    "NVDA":   ("半導體",    "美股"),
    "QQQ":    ("科技ETF",   "美股"),
    "TSLA":   ("消費科技",  "美股"),
    "TSM":    ("半導體",    "美股"),
    "VNQ":    ("REITs",    "美股"),
    "VTI":    ("廣市場ETF", "美股"),
    "0050":   ("廣市場ETF", "台股"),
    "006208": ("廣市場ETF", "台股"),
    "2330":   ("半導體",    "台股"),
    "2454":   ("半導體",    "台股"),
}

# ══════════════════════════════════════════════════════════════
# 從 Google Sheets 載入資料（1 小時快取）
# ══════════════════════════════════════════════════════════════
@st.cache_data(ttl=3600, show_spinner="載入最新持倉資料...")
def load_data():
    try:
        df_raw = pd.read_csv(SHEET_URL, header=None, dtype=str)

        # 現金
        cash_mask = df_raw.iloc[:, 0].astype(str).str.strip() == "現金"
        cash = float(str(df_raw.loc[cash_mask].iloc[0, 1]).replace(",", "").strip())

        # 總資產（找 100.00% 那行）
        pct_mask = df_raw.iloc[:, 2].astype(str).str.strip() == "100.00%"
        total = float(str(df_raw.loc[pct_mask].iloc[0, 1]).replace(",", "").strip())

        # 持倉
        valid = set(SECTOR_MAP.keys())
        rows = df_raw[df_raw.iloc[:, 4].isin(valid)]

        holdings = []
        for _, row in rows.iterrows():
            ticker = str(row.iloc[4]).strip()
            value  = float(str(row.iloc[5]).replace(",", "").strip())
            cost   = float(str(row.iloc[6]).replace(",", "").strip())
            shares = float(str(row.iloc[12]).replace(",", "").strip())
            sector, region = SECTOR_MAP[ticker]
            holdings.append({
                "ticker": ticker, "value": value, "cost": cost,
                "shares": shares, "sector": sector, "region": region,
            })

        return pd.DataFrame(holdings), cash, total

    except Exception as e:
        st.error(f"❌ 無法載入 Google Sheets：{e}")
        st.caption("請確認試算表為公開可讀取狀態")
        st.stop()


df, CASH, TOTAL = load_data()
df["weight"] = df["value"] / TOTAL * 100
df["return"] = (df["value"] - df["cost"]) / df["cost"] * 100

STOCK_TOTAL = df["value"].sum()
TOTAL_COST  = df["cost"].sum()
STOCK_RET   = (STOCK_TOTAL - TOTAL_COST) / TOTAL_COST * 100

pos_w  = list(df["value"] / TOTAL) + [CASH / TOTAL]
HHI    = sum(w**2 for w in pos_w)
EFF_N  = 1 / HHI
TSMC   = df[df.ticker.isin(["TSM", "2330"])]["value"].sum()
NVDA_V = df[df.ticker == "NVDA"]["value"].sum()
SEMI   = df[df.ticker.isin(["ARM", "NVDA", "TSM", "2330", "2454"])]["value"].sum()

TODAY      = datetime.now()
YEAR_END   = datetime(2026, 12, 31)
MONTHS_LEFT = max(1, int((YEAR_END - TODAY).days / 30))

# ══════════════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════════════
col_t1, col_t2, col_t3 = st.columns([3, 1, 1])
with col_t1:
    st.markdown("# 📊 Kitty 投資組合  ·  CFA 儀表板")
    st.caption(f"資料更新：{TODAY.strftime('%Y/%m/%d %H:%M')}（每小時自動重整）　｜　目標：2026年底達到 NT$200萬")
with col_t2:
    progress = TOTAL / GOAL
    st.markdown(f"""
    <div class="metric-card alert-yellow">
      <div class="metric-label">目標進度</div>
      <div class="metric-value" style="color:#E3B341">{progress*100:.1f}%</div>
      <div class="metric-label">NT${TOTAL:,.0f} / NT${GOAL:,.0f}</div>
    </div>
    """, unsafe_allow_html=True)
with col_t3:
    if st.button("🔄 重新整理資料", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

st.progress(progress, text="")
st.divider()

# ══════════════════════════════════════════════════════════════
# ① KPI 卡片
# ══════════════════════════════════════════════════════════════
st.markdown('<div class="section-header">① 資產快照</div>', unsafe_allow_html=True)

k1, k2, k3, k4, k5, k6, k7, k8 = st.columns(8)

def kpi(col, label, value, alert=""):
    cls = f"metric-card alert-{alert}" if alert else "metric-card"
    col_map = {"red":"#F85149","yellow":"#E3B341","green":"#3FB950","teal":"#56D364","":"#E6EDF3"}
    vc = col_map.get(alert, "#E6EDF3")
    col.markdown(f"""
    <div class="{cls}">
      <div class="metric-label">{label}</div>
      <div class="metric-value" style="color:{vc}">{value}</div>
    </div>
    """, unsafe_allow_html=True)

kpi(k1, "總資產",       f"NT${TOTAL/10000:.1f}萬",         "teal")
kpi(k2, "目標缺口",     f"NT${(GOAL-TOTAL)/10000:.1f}萬",  "yellow")
kpi(k3, "股票報酬率",   f"+{STOCK_RET:.1f}%",               "green")
kpi(k4, "現金比例",     f"{CASH/TOTAL*100:.1f}%",           "red" if CASH/TOTAL > 0.15 else "yellow")
kpi(k5, "HHI集中度",    f"{HHI:.3f}",                       "red" if HHI > 0.10 else "green")
kpi(k6, "有效部位數",   f"{EFF_N:.1f} 個",                  "yellow" if EFF_N < 10 else "green")
kpi(k7, "半導體暴露",   f"{SEMI/TOTAL*100:.1f}%",            "red")
kpi(k8, "TSMC實際暴露", f"{TSMC/TOTAL*100:.1f}%",           "red")

st.markdown("<br>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# ② 資產配置 + ③ 集中度
# ══════════════════════════════════════════════════════════════
st.markdown('<div class="section-header">② 資產配置 & ③ 個股集中度</div>', unsafe_allow_html=True)

col_pie, col_bar = st.columns([1, 1.4])

with col_pie:
    sector_df = df.groupby("sector")["value"].sum().reset_index()
    sector_df = pd.concat(
        [sector_df, pd.DataFrame([{"sector": "現金", "value": CASH}])],
        ignore_index=True,
    ).sort_values("value", ascending=False)
    sector_df["pct"] = sector_df["value"] / TOTAL * 100

    color_map = {
        "半導體":    "#F85149",
        "廣市場ETF": "#58A6FF",
        "科技ETF":   "#BC8CFF",
        "黃金/避險": "#E3B341",
        "REITs":     "#FFA657",
        "消費科技":  "#FF7B72",
        "現金":      "#8B949E",
    }
    colors = [color_map.get(s, "#56D364") for s in sector_df["sector"]]

    fig_pie = go.Figure(go.Pie(
        labels=sector_df["sector"],
        values=sector_df["pct"],
        hole=0.45,
        marker=dict(colors=colors, line=dict(color="#0D1117", width=2)),
        textinfo="label+percent",
        textfont=dict(size=11, color="#E6EDF3"),
        hovertemplate="<b>%{label}</b><br>%{percent}<br>NT$%{value:,.0f}萬<extra></extra>",
    ))
    fig_pie.update_layout(
        title=dict(text="板塊配置", font=dict(color="#E6EDF3", size=13)),
        paper_bgcolor="#161B22", plot_bgcolor="#161B22",
        font=dict(color="#8B949E"),
        legend=dict(font=dict(color="#8B949E", size=10), bgcolor="#161B22"),
        margin=dict(t=40, b=10, l=10, r=10),
        height=320,
        annotations=[dict(
            text=f"<b>半導體<br>{SEMI/TOTAL*100:.0f}%</b>",
            x=0.5, y=0.5, font=dict(size=13, color="#F85149"), showarrow=False,
        )],
    )
    st.plotly_chart(fig_pie, width="stretch")

with col_bar:
    conc_df = df[~df.ticker.isin(["TSM", "2330"])].copy()
    tsmc_row = pd.DataFrame([{
        "ticker": "TSMC合計\n(TSM+2330)",
        "value": TSMC,
        "cost": df[df.ticker.isin(["TSM", "2330"])]["cost"].sum(),
        "sector": "半導體", "region": "合計",
        "weight": TSMC / TOTAL * 100,
        "return": (TSMC - df[df.ticker.isin(["TSM","2330"])]["cost"].sum()) /
                   df[df.ticker.isin(["TSM","2330"])]["cost"].sum() * 100,
        "shares": 0,
    }])
    conc_df = pd.concat([tsmc_row, conc_df]).sort_values("value", ascending=True)
    conc_df["weight"] = conc_df["value"] / TOTAL * 100

    bar_colors = []
    for _, row in conc_df.iterrows():
        if "TSMC合計" in str(row["ticker"]):
            bar_colors.append("#FF7B72")
        elif row["weight"] > 10:
            bar_colors.append("#F85149")
        elif row["weight"] > 5:
            bar_colors.append("#E3B341")
        else:
            bar_colors.append("#3FB950")

    fig_bar = go.Figure(go.Bar(
        x=conc_df["weight"],
        y=conc_df["ticker"],
        orientation="h",
        marker=dict(color=bar_colors, line=dict(color="#0D1117", width=0.5)),
        text=[f"{w:.1f}%" for w in conc_df["weight"]],
        textposition="outside",
        textfont=dict(color="#E6EDF3", size=10),
        hovertemplate="<b>%{y}</b><br>%{x:.1f}%<extra></extra>",
    ))
    fig_bar.add_vline(x=10, line=dict(color="#F85149", width=1.5, dash="dash"),
                      annotation=dict(text="10% 警戒", font=dict(color="#F85149", size=9)))
    fig_bar.add_vline(x=5,  line=dict(color="#E3B341", width=1, dash="dot"),
                      annotation=dict(text="5% 注意", font=dict(color="#E3B341", size=9), y=0.05))
    fig_bar.update_layout(
        title=dict(text="個股集中度（% 總資產）", font=dict(color="#E6EDF3", size=13)),
        paper_bgcolor="#161B22", plot_bgcolor="#161B22",
        xaxis=dict(color="#8B949E", gridcolor="#30363D", title="佔比%"),
        yaxis=dict(color="#E6EDF3", tickfont=dict(size=10)),
        margin=dict(t=40, b=10, l=10, r=60),
        height=320,
        showlegend=False,
    )
    st.plotly_chart(fig_bar, width="stretch")

# ══════════════════════════════════════════════════════════════
# ④ 持倉明細表格
# ══════════════════════════════════════════════════════════════
st.markdown('<div class="section-header">④ 持倉明細</div>', unsafe_allow_html=True)

display_df = df.copy().sort_values("value", ascending=False)
display_df["市值(TWD)"] = display_df["value"].apply(lambda x: f"NT${x:,.0f}")
display_df["成本(TWD)"] = display_df["cost"].apply(lambda x: f"NT${x:,.0f}")
display_df["佔比%"]     = display_df["weight"].apply(lambda x: f"{x:.1f}%")
display_df["報酬率"]    = display_df["return"].apply(lambda x: f"+{x:.1f}%" if x >= 0 else f"{x:.1f}%")
display_df["風險燈號"]  = display_df["weight"].apply(
    lambda w: "🔴 高度集中" if w > 10 else ("🟡 注意" if w > 5 else "🟢 安全"))

st.dataframe(
    display_df[["ticker","region","sector","市值(TWD)","佔比%","成本(TWD)","報酬率","風險燈號"]]
    .rename(columns={"ticker":"標的","region":"地區","sector":"板塊"}),
    width="stretch",
    hide_index=True,
    height=420,
)

# ══════════════════════════════════════════════════════════════
# ⑤ CFA 風險洞察
# ══════════════════════════════════════════════════════════════
st.markdown('<div class="section-header">⑤ CFA 風險洞察</div>', unsafe_allow_html=True)

col_r1, col_r2 = st.columns(2)

gld_val = df[df.ticker == "GLD"]["value"].sum()
qqq_val = df[df.ticker == "QQQ"]["value"].sum()

insights = [
    ("🔴 TSMC 雙重持股",   f"TSM(ADR) + 2330 = {TSMC/TOTAL*100:.1f}% 同一家公司\n建議保留 2330，賣出 TSM ADR",       "red"),
    ("🔴 半導體集中度",     f"ARM+NVDA+TSM+2330+2454 合計 {SEMI/TOTAL*100:.1f}%\nCFA 建議單一產業上限 25%",           "red"),
    ("🟡 QQQ vs VTI 重疊", "QQQ 前 20 大持股與 VTI 重疊 ~73%\n停止 QQQ 定投，改為 VTI",                             "yellow"),
    ("🟡 現金拖累",         f"現金 {CASH/TOTAL*100:.1f}% 閒置，建議降至 10%\n可逢低加碼或提前定投",                   "yellow"),
    ("🟡 0050 vs 006208",  "兩檔都追蹤台灣 50，建議合併至 0050",                                                     "yellow"),
    ("🟢 GLD 配置合理",     f"黃金 {gld_val/TOTAL*100:.1f}%，與股市相關性低\n維持，市場波動時可加碼",                 "green"),
]

for i, (title, detail, color) in enumerate(insights):
    col = col_r1 if i % 2 == 0 else col_r2
    border = {"red": "#F85149", "yellow": "#E3B341", "green": "#3FB950"}[color]
    col.markdown(f"""
    <div class="insight-box" style="border-left: 3px solid {border};">
      <b style="color:{border}">{title}</b><br>
      <span style="color:#8B949E; font-size:13px; white-space:pre-line">{detail}</span>
    </div>
    """, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# ⑥ 再平衡建議
# ══════════════════════════════════════════════════════════════
st.markdown('<div class="section-header">⑥ CFA 再平衡建議</div>', unsafe_allow_html=True)

vti_val    = df[df.ticker == "VTI"]["value"].sum()
tw50_val   = df[df.ticker.isin(["0050", "006208"])]["value"].sum()
vnq_val    = df[df.ticker == "VNQ"]["value"].sum()
rebal = [
    ("VTI（廣市場）",       35.0, vti_val/TOTAL*100,   "↑ 停QQQ定投，轉換所有QQQ為VTI"),
    ("0050（台股）",         15.0, tw50_val/TOTAL*100,  "↑ 停006208，合併至0050"),
    ("NVDA",                10.0, NVDA_V/TOTAL*100,    "↓ 逢高分批減持至10%"),
    ("TSMC（保留2330）",    10.0, TSMC/TOTAL*100,      "↓ 賣TSM ADR，同公司不需雙持"),
    ("GLD（黃金）",           8.0, gld_val/TOTAL*100,  "= 維持，逢跌加碼"),
    ("VNQ（REITs）",          7.0, vnq_val/TOTAL*100,  "= 維持"),
    ("現金",                10.0, CASH/TOTAL*100,       "↓ 從高水位降至10%，逢低部署"),
    ("QQQ",                  0.0, qqq_val/TOTAL*100,   "✗ 全部轉換VTI，消除重疊"),
    ("006208",               0.0, df[df.ticker=="006208"]["value"].sum()/TOTAL*100, "✗ 合併至0050"),
]
rebal_df = pd.DataFrame(rebal, columns=["標的", "目標%", "現況%", "行動"])
rebal_df["差距(ppt)"] = rebal_df["現況%"] - rebal_df["目標%"]
rebal_df["目標%"]     = rebal_df["目標%"].apply(lambda x: f"{x:.0f}%")
rebal_df["現況%"]     = rebal_df["現況%"].apply(lambda x: f"{x:.1f}%")
rebal_df["差距(ppt)"] = rebal_df["差距(ppt)"].apply(lambda x: f"+{x:.1f}" if x > 0 else f"{x:.1f}")

st.dataframe(rebal_df, width="stretch", hide_index=True, height=350)

# ══════════════════════════════════════════════════════════════
# ⑦ 目標追蹤（互動式 Slider）
# ══════════════════════════════════════════════════════════════
st.markdown('<div class="section-header">⑦ 200萬目標追蹤（互動模擬器）</div>', unsafe_allow_html=True)

col_s1, col_s2 = st.columns([1, 3])
with col_s1:
    monthly_contrib = st.slider("每月定投金額 (NT$)", 0, 50000, 15000, step=1000)
    target_return   = st.slider("預期年化報酬率 (%)", 0, 25, 9, step=1)
    months_sim      = st.slider("模擬月數", 6, 24, MONTHS_LEFT)
    st.divider()
    r_m = (1 + target_return / 100) ** (1 / 12) - 1
    path_custom = [TOTAL]
    for m in range(1, months_sim + 1):
        path_custom.append(path_custom[-1] * (1 + r_m) + monthly_contrib)
    final_custom = path_custom[-1]
    gap = GOAL - final_custom
    color_result = "#3FB950" if final_custom >= GOAL else "#F85149"
    st.markdown(f"""
    <div class="metric-card" style="border-color:{color_result}; background:{color_result}15">
      <div class="metric-label">模擬結果（{months_sim}個月後）</div>
      <div class="metric-value" style="color:{color_result}">NT${final_custom/10000:.1f}萬</div>
      <div class="metric-label">{'✓ 達標！' if final_custom >= GOAL else f'差 NT${abs(gap):,.0f}'}</div>
    </div>
    """, unsafe_allow_html=True)

with col_s2:
    months = list(range(months_sim + 1))
    scenarios = {"保守 6%": 0.06, "基準 9%": 0.09, "樂觀 12%": 0.12, "目標 15%": 0.15}
    colors_line = ["#8B949E", "#58A6FF", "#56D364", "#3FB950"]

    fig_goal = go.Figure()
    for (label, rate), color in zip(scenarios.items(), colors_line):
        rM = (1 + rate) ** (1 / 12) - 1
        path = [TOTAL]
        for m in range(1, months_sim + 1):
            path.append(path[-1] * (1 + rM) + monthly_contrib)
        fig_goal.add_trace(go.Scatter(
            x=months, y=[v / 10000 for v in path],
            mode="lines", name=label,
            line=dict(color=color, width=2, dash="dash" if label == "保守 6%" else "solid"),
            hovertemplate=f"<b>{label}</b><br>%{{x}}個月後：NT$%{{y:.1f}}萬<extra></extra>",
        ))

    fig_goal.add_trace(go.Scatter(
        x=months, y=[v / 10000 for v in path_custom],
        mode="lines", name=f"自訂 {target_return}% / NT${monthly_contrib:,}",
        line=dict(color="#FFA657", width=3),
        hovertemplate="<b>自訂</b><br>%{x}個月後：NT$%{y:.1f}萬<extra></extra>",
    ))
    fig_goal.add_hline(y=GOAL / 10000,  line=dict(color="#E3B341", width=1.5, dash="dash"),
                       annotation=dict(text="目標 200萬", font=dict(color="#E3B341")))
    fig_goal.add_hline(y=TOTAL / 10000, line=dict(color="#8B949E", width=1, dash="dot"),
                       annotation=dict(text=f"現在 {TOTAL/10000:.0f}萬", font=dict(color="#8B949E", size=9)))
    fig_goal.update_layout(
        paper_bgcolor="#161B22", plot_bgcolor="#161B22",
        xaxis=dict(title="月數", color="#8B949E", gridcolor="#30363D"),
        yaxis=dict(title="資產（萬TWD）", color="#8B949E", gridcolor="#30363D"),
        legend=dict(font=dict(color="#8B949E"), bgcolor="#161B22"),
        margin=dict(t=20, b=40, l=60, r=20),
        height=320,
        font=dict(color="#8B949E"),
    )
    st.plotly_chart(fig_goal, width="stretch")

# ══════════════════════════════════════════════════════════════
# ⑧ 相關性熱力圖
# ══════════════════════════════════════════════════════════════
st.markdown('<div class="section-header">⑧ 持倉重疊與相關性分析</div>', unsafe_allow_html=True)

col_heat, col_note = st.columns([1.5, 1])
with col_heat:
    tickers_corr = ["VTI", "QQQ", "NVDA", "TSM", "2330", "0050", "GLD", "VNQ", "IWM"]
    corr_matrix = np.array([
        [ 1.00, 0.92, 0.72, 0.65, 0.60, 0.45, 0.05, 0.72, 0.88],
        [ 0.92, 1.00, 0.80, 0.72, 0.65, 0.50, 0.02, 0.60, 0.78],
        [ 0.72, 0.80, 1.00, 0.78, 0.72, 0.45, 0.00, 0.40, 0.60],
        [ 0.65, 0.72, 0.78, 1.00, 0.92, 0.55, 0.05, 0.42, 0.55],
        [ 0.60, 0.65, 0.72, 0.92, 1.00, 0.60, 0.05, 0.40, 0.50],
        [ 0.45, 0.50, 0.45, 0.55, 0.60, 1.00, 0.08, 0.38, 0.42],
        [ 0.05, 0.02, 0.00, 0.05, 0.05, 0.08, 1.00, 0.15, 0.05],
        [ 0.72, 0.60, 0.40, 0.42, 0.40, 0.38, 0.15, 1.00, 0.68],
        [ 0.88, 0.78, 0.60, 0.55, 0.50, 0.42, 0.05, 0.68, 1.00],
    ])
    fig_heat = go.Figure(go.Heatmap(
        z=corr_matrix, x=tickers_corr, y=tickers_corr,
        colorscale=[[0, "#161B22"], [0.5, "#58A6FF"], [1, "#F85149"]],
        zmin=-0.2, zmax=1.0,
        text=[[f"{v:.2f}" for v in row] for row in corr_matrix],
        texttemplate="%{text}",
        textfont=dict(size=9, color="#E6EDF3"),
        hovertemplate="%{y} vs %{x}: %{z:.2f}<extra></extra>",
    ))
    fig_heat.update_layout(
        title=dict(text="持倉相關係數（估算）", font=dict(color="#E6EDF3", size=12)),
        paper_bgcolor="#161B22", plot_bgcolor="#161B22",
        xaxis=dict(color="#8B949E"), yaxis=dict(color="#8B949E"),
        margin=dict(t=40, b=10, l=10, r=10),
        height=330,
    )
    st.plotly_chart(fig_heat, width="stretch")

with col_note:
    st.markdown("""
    <div class="insight-box" style="margin-top:40px">
      <b style="color:#58A6FF">讀圖重點</b><br><br>
      <span style="color:#F85149">🔴 深紅 > 0.85：高度重疊</span><br>
      <span style="color:#8B949E; font-size:13px">VTI ↔ QQQ（0.92）→ 重疊嚴重</span><br>
      <span style="color:#8B949E; font-size:13px">TSM ↔ 2330（0.92）→ 同家公司</span><br><br>
      <span style="color:#E3B341">🟡 中藍 0.5~0.85：有相關</span><br>
      <span style="color:#8B949E; font-size:13px">整體美股持倉高度同向</span><br><br>
      <span style="color:#3FB950">🟢 接近 0：獨立分散</span><br>
      <span style="color:#8B949E; font-size:13px">GLD 幾乎與所有股票無關</span><br>
      <span style="color:#8B949E; font-size:13px">→ 黃金配置的核心價值</span>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("""
    <div class="insight-box" style="margin-top:12px; border-left:3px solid #F85149">
      <b style="color:#F85149">主要問題</b><br>
      <span style="color:#8B949E; font-size:13px">
      你的投資組合中大部分持倉<br>
      都高度正相關，代表下跌時<br>
      幾乎會一起跌，分散效果差。<br><br>
      真正分散的只有 GLD（黃金）
      </span>
    </div>
    """, unsafe_allow_html=True)

# Footer
st.divider()
st.caption("⚠️ 本儀表板為個人財務分析工具，非投資建議。資料來源：Google Sheets（每小時自動更新）。")
