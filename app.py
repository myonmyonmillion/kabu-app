import streamlit as st
import yfinance as yf
import pandas as pd
import ta
import os
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import concurrent.futures
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET

# ------------------------------------------
# ページ設定
# ------------------------------------------
st.set_page_config(page_title="総合投資ダッシュボード", layout="wide", initial_sidebar_state="expanded")
st.title("🦅 グローバル・マルチ投資ダッシュボード")

# ------------------------------------------
# 定数・銘柄リスト
# ------------------------------------------
MAJOR_STOCKS_JP = {
    "トヨタ自動車": "7203.T", "三菱UFJ FG": "8306.T", "三井住友FG": "8316.T",
    "NTT": "9432.T", "KDDI": "9433.T", "三菱商事": "8058.T",
    "伊藤忠商事": "8001.T", "三井物産": "8031.T", "武田薬品工業": "4502.T",
    "ソニーグループ": "6758.T", "日立製作所": "6501.T", "信越化学工業": "4063.T",
    "オリックス": "8591.T", "ホンダ": "7267.T", "JT (日本たばこ産業)": "2914.T",
    "ファーストリテイリング": "9983.T", "ソフトバンクグループ": "9984.T", 
    "東京エレクトロン": "8035.T", "LIXIL": "5938.T", "ダイキン": "6367.T",
    "村田製作所": "6981.T"
}

MAJOR_STOCKS_US = {
    "Apple": "AAPL", "Microsoft": "MSFT", "NVIDIA": "NVDA",
    "Tesla": "TSLA", "Amazon": "AMZN", "Alphabet (Google)": "GOOGL",
    "Meta (Facebook)": "META", "Coca-Cola": "KO", "Procter & Gamble": "PG",
    "TSMC (台湾セミコンダクター)": "TSM", "Netflix": "NFLX", "AMD": "AMD",
    "Intel": "INTC", "Johnson & Johnson": "JNJ", "Visa": "V"
}

PORTFOLIO_FILE = "portfolio.csv"

# ------------------------------------------
# 関数群
# ------------------------------------------
@st.cache_data
def get_nikkei225_tickers():
    raw_data = (
        "1332.T ニッスイ,1333.T マルハニチロ,2002.T 日清製粉G,2269.T 明治HD,2282.T 日本ハム,"
        "2413.T エムスリー,2432.T ディー・エヌ・エー,2501.T サッポロHD,2502.T アサヒGHD,2503.T キリンHD,2531.T 宝HD,2768.T 双日,2801.T キッコーマン,2802.T 味の素,2871.T ニチレイ,2914.T JT,3086.T Jフロント,3099.T 三越伊勢丹,3289.T 東急不動産,3382.T セブン&アイ,"
        "3401.T 帝人,3402.T 東レ,3405.T クラレ,3407.T 旭化成,3436.T SUMCO,3659.T ネクソン,3861.T 王子HD,3863.T 日本製紙,4004.T レゾナック,4005.T 住友化学,4021.T 日産化学,4041.T 日本曹達,4042.T 東ソー,4043.T トクヤマ,4061.T デンカ,4063.T 信越化学,4151.T 協和キリン,4183.T 三井化学,4188.T 三菱ケミカル,4208.T UBE,4324.T 電通G,4452.T 花王,"
        "4502.T 武田薬品,4503.T アステラス製薬,4506.T 住友ファーマ,4507.T 塩野義製薬,4519.T 中外製薬,4523.T エーザイ,4568.T 第一三共,4578.T 大塚HD,4689.T LINEヤフー,4704.T トレンドマイクロ,4751.T サイバーエージェント,4755.T 楽天G,4901.T 富士フイルム,4911.T 資生堂,5019.T 出光興産,5020.T ENEOS,5101.T 横浜ゴム,5108.T ブリヂストン,5201.T AGC,5202.T 日本板硝子,5214.T 日本電気硝子,5232.T 住友大阪セメント,5233.T 太平洋セメント,5301.T 東海カーボン,5332.T TOTO,5333.T 日本ガイシ,"
        "5401.T 日本製鉄,5406.T 神戸製鋼所,5411.T JFEHD,5541.T 大平洋金属,5631.T 日本製鋼所,5703.T 日本軽金属,5706.T 三井金属,5711.T 三菱マテリアル,5713.T 住友金属鉱山,5714.T DOWA,5801.T 古河電工,5802.T 住友電工,5803.T フジクラ,5831.T しずおかFG,5938.T LIXIL,6098.T リクルートHD,6103.T オークマ,6118.T アイダ,6273.T SMC,6301.T コマツ,6302.T 住友重機械,6305.T 日立建機,6326.T クボタ,6361.T 荏原製作所,6367.T ダイキン,6471.T 日本精工,6472.T NTN,6473.T ジェイテクト,6501.T 日立製作所,6503.T 三菱電機,6504.T 富士電機,6506.T 安川電機,6526.T ソシオネクスト,6594.T ニデック,"
        "6645.T オムロン,6701.T NEC,6702.T 富士通,6723.T ルネサス,6724.T エプソン,6752.T パナソニック,6758.T ソニーG,6762.T TDK,6770.T アルプスアルパイン,6841.T 横河電機,6857.T アドバンテスト,6861.T キーエンス,6902.T デンソー,6952.T カシオ,6954.T ファナック,6971.T 京セラ,6976.T 太陽誘電,6981.T 村田製作所,6988.T 日東電工,"
        "7011.T 三菱重工,7012.T 川崎重工,7013.T IHI,7186.T コンコルディア,7201.T 日産自動車,7202.T いすゞ自動車,7203.T トヨタ自動車,7205.T 日野自動車,7211.T 三菱自動車,7261.T マツダ,7267.T ホンダ,7269.T スズキ,7270.T SUBARU,7272.T ヤマハ発動機,7731.T ニコン,7733.T オリンパス,7735.T SCREEN,7741.T HOYA,7751.T キヤノン,7752.T リコー,7762.T シチズン時計,7832.T バンダイナムコ,7911.T TOPPAN,7912.T 大日本印刷,7951.T ヤマハ,7974.T 任天堂,"
        "8001.T 伊藤商事,8002.T 丸紅,8015.T 豊田通商,8031.T 三井物産,8035.T 東京エレクトロン,8053.T 住友商事,8058.T 三菱商事,8233.T 高島屋,8252.T 丸井G,8267.T イオン,8304.T あおぞら銀行,8306.T 三菱UFJ,8308.T りそなHD,8309.T 三井住友トラスト,8316.T 三井住友FG,8331.T 千葉銀行,8354.T ふくおかFG,8411.T みずほFG,8591.T オリックス,8601.T 大和証券G,8604.T 野村HD,8628.T 松井証券,8630.T SOMPOHD,8725.T MS&AD,8750.T 第一生命HD,8766.T 東京海上HD,8795.T T&DHD,8801.T 三井不動産,8802.T 三菱地所,8804.T 東京建物,8830.T 住友不動産,"
        "9001.T 東武鉄道,9005.T 東急,9007.T 小田急電鉄,9008.T 京王電鉄,9009.T 京成電鉄,9020.T JR東日本,9021.T JR西日本,9022.T JR東海,9064.T ヤマトHD,9101.T 日本郵船,9104.T 商船三井,9107.T 川崎汽船,9147.T NIPPON EXPRESS,9201.T 日本航空,9202.T ANAHD,9301.T 三菱倉庫,9432.T NTT,9433.T KDDI,9434.T ソフトバンク,9501.T 東京電力HD,9502.T 中部電力,9503.T 関西電力,9531.T 東京ガス,9532.T 大阪ガス,9602.T 東宝,9613.T NTTデータG,9735.T セコム,9766.T コナミG,9843.T ニトリHD,9983.T ファーストリテイリング,9984.T ソフトバンクG"
    )
    tickers = {}
    for item in raw_data.split(","):
        if item.strip():
            parts = item.strip().split(" ", 1)
            if len(parts) == 2:
                code, name = parts
                tickers[name] = code
    return tickers

@st.cache_data(ttl=3600)
def get_macro_data():
    try:
        data = yf.download("^N225 ^GSPC JPY=X", period="2d", group_by="ticker", progress=False)
        res = {}
        for t in ["^N225", "^GSPC", "JPY=X"]:
            if t in data and not data[t].empty:
                close_prices = data[t]['Close'].dropna()
                if len(close_prices) >= 2:
                    current = float(close_prices.iloc[-1])
                    prev = float(close_prices.iloc[-2])
                    res[t] = {"price": current, "diff": current - prev, "diff_pct": (current - prev) / prev * 100}
        return res
    except Exception:
        return {}

def analyze_single_stock(name, ticker):
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period="2y")
        if df.empty or len(df) < 25: 
            return None
        
        try:
            info = stock.info
        except Exception:
            info = {}
            
        display_name = name
        
        df['RSI'] = ta.momentum.RSIIndicator(close=df['Close'], window=14).rsi()
        macd = ta.trend.MACD(close=df['Close'])
        df['MACD_Diff'] = macd.macd_diff()
        
        bb = ta.volatility.BollingerBands(close=df['Close'], window=20, window_dev=2)
        df['BB_Low'] = bb.bollinger_lband()
        df['SMA25'] = ta.trend.SMAIndicator(close=df['Close'], window=25).sma_indicator()
        
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        rsi_val = latest['RSI']
        if pd.isna(rsi_val) or pd.isna(latest['MACD_Diff']): 
            return None
        
        macd_gc = (prev['MACD_Diff'] < 0) and (latest['MACD_Diff'] > 0)
        
        if len(df) >= 200:
            df['SMA200'] = ta.trend.SMAIndicator(close=df['Close'], window=200).sma_indicator()
            sma_val = df['SMA200'].iloc[-1]
            is_uptrend = not pd.isna(sma_val) and (latest['Close'] > sma_val)
        else:
            is_uptrend = False
            
        # --- 目安金額と買い時アクションのロジック ---
        target_price = latest['BB_Low'] if not pd.isna(latest['BB_Low']) else latest['SMA25']
        currency = info.get('currency', 'JPY' if ticker.endswith('.T') else 'USD')
        
        # ファンダメンタル指標の取得
        per = info.get('trailingPE', None)
        pbr = info.get('priceToBook', None)
        
        # 【修正】配当利回りの異常値（Yahoo Financeのバグ対応）
        div_yield = info.get('dividendYield', None)
        if div_yield is not None:
            # もし利回りが20% (0.2) を超えている場合は、すでに%化された数値が返ってきていると判定
            if div_yield > 0.2:
                div_yield_disp = round(div_yield, 2)
            else:
                div_yield_disp = round(div_yield * 100, 2)
        else:
            div_yield_disp = "-"
        
        # スコア計算
        score = 0
        if is_uptrend: score += 30
        if macd_gc: score += 20
        elif latest['MACD_Diff'] > 0: score += 10
        
        if 30 <= rsi_val <= 45: score += 30
        elif rsi_val < 30: score += 10 
        elif 45 < rsi_val <= 60: score += 10
        
        if rsi_val > 70:
            action = "高値警戒（見送り） 🛑"
            target_str = f"過熱。{round(float(target_price), 1)} まで調整待ち"
            score = -50  
        elif rsi_val <= 40 or macd_gc:
            action = "今すぐ買い候補 🚀"
            target_str = "現在値付近が買い時"
        else:
            action = "様子見 ⏳"
            target_str = f"押し目目安: {round(float(target_price), 1)}"
        
        return {
            "Ticker": ticker,
            "銘柄名": display_name,
            "総合スコア": score,
            "セクター": info.get('sector', '不明'),
            "通貨": currency,
            "現在値": round(float(latest['Close']), 2),
            "推奨アクション": action,
            "目標買値": target_str,
            "RSI(過熱感)": round(float(rsi_val), 1),
            "PER": round(per, 2) if per else "-",
            "PBR": round(pbr, 2) if pbr else "-",
            "配当利回り(%)": div_yield_disp
        }
    except Exception:
        return None

def fetch_and_analyze(tickers_dict):
    data = []
    total = len(tickers_dict)
    if total == 0: return data
    
    progress_text = st.empty()
    progress_bar = st.progress(0)
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_to_stock = {executor.submit(analyze_single_stock, name, t): name for name, t in tickers_dict.items()}
        completed = 0
        for future in concurrent.futures.as_completed(future_to_stock):
            completed += 1
            name = future_to_stock[future]
            progress_text.text(f"📊 市場データをスキャン中... ({completed}/{total}) : {name}")
            progress_bar.progress(completed / total)
            res = future.result()
            if res:
                data.append(res)
                
    progress_text.empty()
    progress_bar.empty()
    return data

@st.cache_data(ttl=1800)
def get_google_news(query):
    news_list = []
    try:
        encoded_query = urllib.parse.quote(query + " 株")
        url = f"https://news.google.com/rss/search?q={encoded_query}&hl=ja&gl=JP&ceid=JP:ja"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            xml_data = response.read()
        root = ET.fromstring(xml_data)
        for item in root.findall('.//item')[:5]:
            title = item.find('title').text
            link = item.find('link').text
            pubDate = item.find('pubDate').text
            news_list.append({'title': title, 'link': link, 'date': pubDate})
    except Exception:
        pass
    return news_list

# ==========================================
# 初期化
# ==========================================
if "portfolio_df" not in st.session_state:
    if os.path.exists(PORTFOLIO_FILE):
        try:
            st.session_state.portfolio_df = pd.read_csv(PORTFOLIO_FILE)
        except:
            st.session_state.portfolio_df = pd.DataFrame(columns=["Ticker", "買値", "株数", "メモ"])
    else:
        st.session_state.portfolio_df = pd.DataFrame(columns=["Ticker", "買値", "株数", "メモ"])
        
if "selected_ticker" not in st.session_state:
    st.session_state.selected_ticker = None

if "active_tab" not in st.session_state:
    st.session_state.active_tab = "🏆 買い時ランキング"

# ==========================================
# マクロサマリー
# ==========================================
macro_data = get_macro_data()
if macro_data:
    col_m1, col_m2, col_m3 = st.columns(3)
    if "^N225" in macro_data:
        col_m1.metric("日経平均", f"¥{macro_data['^N225']['price']:,.2f}", f"{macro_data['^N225']['diff']:,.2f} ({macro_data['^N225']['diff_pct']:.2f}%)")
    if "^GSPC" in macro_data:
        col_m2.metric("S&P 500", f"${macro_data['^GSPC']['price']:,.2f}", f"{macro_data['^GSPC']['diff']:,.2f} ({macro_data['^GSPC']['diff_pct']:.2f}%)")
    if "JPY=X" in macro_data:
        col_m3.metric("ドル円 (USD/JPY)", f"¥{macro_data['JPY=X']['price']:,.2f}", f"{macro_data['JPY=X']['diff']:,.2f} ({macro_data['JPY=X']['diff_pct']:.2f}%)", delta_color="inverse")
st.markdown("---")

# ==========================================
# サイドバー
# ==========================================
st.sidebar.header("⚙️ 検索・フィルター設定")

with st.sidebar.form("search_form"):
    market_choice = st.radio("🌐 対象市場を選択", ["🇯🇵 日本株", "🇺🇸 米国株"])
    
    mode_choice = "主要銘柄"
    if market_choice == "🇯🇵 日本株":
        mode_choice = st.radio("📊 銘柄モード (日本株)", ["日経225全銘柄", "主要銘柄"])
    else:
        st.write("📊 銘柄モード: 主要米国株 (TSM等含む)")
    
    custom_tickers_input = st.text_input("➕ 追加ティッカー (例: 8267.T, PLTR)")
    submitted = st.form_submit_button("🚀 この条件で分析を実行する")

st.sidebar.markdown("---")
st.sidebar.header("📖 投資の教科書 (用語集)")
with st.sidebar.expander("📝 株式用語と指標の解説を開く", expanded=False):
    st.markdown("""
    **✅ ファンダメンタルズ分析（企業価値）**
    - **PER (株価収益率)**
      企業の利益に対して株価が割安かを示します。一般的に15倍以下で割安。
    - **PBR (株価純資産倍率)**
      企業の純資産（解散価値）に対する株価の割合。1倍割れはお買い得。
    - **配当利回り**
      投資額に対して年間でもらえる配当金の割合。3〜4%以上が高配当。
    
    **✅ テクニカル分析（チャート・心理）**
    - **RSI (相対力指数)**
      買われすぎ・売られすぎの過熱感を示します。**70以上で買われすぎ、30以下で売られすぎ**。
    - **MACD (マックディー)**
      トレンドの方向を見る指標。シグナル線を下から上に抜ける「ゴールデンクロス」は買いサイン。
    - **ボリンジャーバンド**
      株価が動く範囲を予測する帯（バンド）。
      ・**-2σ（下の線）**に触れると「売られすぎ」で反発（買い）シグナル
      ・**+2σ（上の線）**に触れると「買われすぎ」で下落（売り）シグナル
    """)

if "market_data" not in st.session_state or submitted:
    target_tickers = {}
    if market_choice == "🇯🇵 日本株":
        if mode_choice == "主要銘柄":
            target_tickers = MAJOR_STOCKS_JP.copy()
        else:
            with st.spinner("日経225の銘柄リストを展開中..."):
                target_tickers = get_nikkei225_tickers().copy()
    else:
        target_tickers = MAJOR_STOCKS_US.copy()
        
    if custom_tickers_input:
        for t_raw in custom_tickers_input.split(","):
            t = t_raw.strip().upper()
            if t: target_tickers[f"追加銘柄({t})"] = t
            
    with st.spinner("データをスキャン・解析しています..."):
        st.session_state.market_data = fetch_and_analyze(target_tickers)
        st.session_state.market_choice_name = market_choice

market_data = st.session_state.market_data
test_options = sorted([f"{row['銘柄名']} ({row['Ticker']})" for row in market_data]) if market_data else []
usd_jpy_rate = macro_data.get("JPY=X", {}).get("price", 150.0) if macro_data else 150.0

# ==========================================
# カスタムUI タブ構成
# ==========================================
tabs = ["🏆 買い時ランキング", "📈 マルチタイムフレーム", "💼 ポートフォリオ判定", "💰 資金配分"]
selected_tab = st.radio("メニュー", tabs, index=tabs.index(st.session_state.active_tab), horizontal=True, label_visibility="collapsed")

if selected_tab != st.session_state.active_tab:
    st.session_state.active_tab = selected_tab
    st.rerun()

# ------------------------------------------
# TAB 1: 買い時ランキング
# ------------------------------------------
if st.session_state.active_tab == "🏆 買い時ランキング":
    st.header(f"🏆 {st.session_state.get('market_choice_name', '日本株')} トップ10銘柄")
    st.info("💡 右端のボタンをクリックすると、「マルチタイムフレーム」タブで詳細なチャート分析を確認できます。")
    
    if market_data:
        res_df = pd.DataFrame(market_data).sort_values('総合スコア', ascending=False)
        display_df = res_df.reset_index(drop=True)
        display_df.index = display_df.index + 1
        
        hc = st.columns([0.5, 2, 1, 2, 2.5, 1.5])
        hc[0].markdown("**順位**")
        hc[1].markdown("**銘柄名**")
        hc[2].markdown("**現在値**")
        hc[3].markdown("**推奨アクション**")
        hc[4].markdown("**目標買値**")
        hc[5].markdown("**分析**")
        st.divider()
        
        for idx, row in display_df.head(10).iterrows():
            c = st.columns([0.5, 2, 1, 2, 2.5, 1.5])
            c[0].write(f"{idx}位")
            c[1].write(f"**{row['銘柄名']}**\n\n`{row['Ticker']}`")
            c[2].write(f"{row['現在値']} {row['通貨']}")
            c[3].write(row['推奨アクション'])
            c[4].write(row['目標買値'])
            
            if c[5].button("チャート確認 📈", key=f"btn_{row['Ticker']}"):
                st.session_state.selected_ticker = row['Ticker']
                st.session_state.active_tab = "📈 マルチタイムフレーム"
                st.rerun()
                
        st.markdown("---")
        with st.expander("📊 全データの表を見る"):
            st.dataframe(display_df, use_container_width=True)
    else:
        st.warning("表示できるデータがありません。サイドバーから分析を実行してください。")

# ------------------------------------------
# TAB 2: マルチタイムフレーム分析
# ------------------------------------------
elif st.session_state.active_tab == "📈 マルチタイムフレーム":
    st.header("📈 マルチタイムフレーム ＆ 出来高分析")
    if test_options:
        default_idx = 0
        if st.session_state.selected_ticker:
            for i, opt in enumerate(test_options):
                if st.session_state.selected_ticker in opt:
                    default_idx = i
                    break

        mtf_ticker = st.selectbox(
            "チャートを表示・分析する銘柄を検索・選択", 
            test_options, 
            key="mtf", 
            index=default_idx,
            placeholder="銘柄名（日本語）を入力して検索"
        )
        
        if mtf_ticker:
            t_mtf = mtf_ticker.split("(")[-1].replace(")", "")
            t_data = next((r for r in market_data if r['Ticker'] == t_mtf), None)
            
            if t_data:
                st.markdown(f"## {t_data['銘柄名']} | 現在の株価: **{t_data['現在値']} {t_data['通貨']}**")
                with st.container():
                    st.markdown("#### 💡 基本評価指標（ランキング連動）")
                    # 【修正】文字が見切れないように st.metric と st.markdown を併用
                    m_col1, m_col2, m_col3, m_col4 = st.columns(4)
                    m_col1.metric("総合買い時スコア", f"{t_data['総合スコア']}点")
                    with m_col2:
                        st.caption("推奨アクション")
                        st.markdown(f"**{t_data['推奨アクション']}**")
                    with m_col3:
                        st.caption("目標買値")
                        st.markdown(f"**{t_data['目標買値']}**")
                    m_col4.metric("RSI (過熱感)", f"{t_data['RSI(過熱感)']}%")
            
            st.markdown("---")
            
            stock = yf.Ticker(t_mtf)
            df_daily = stock.history(period="6mo", interval="1d")
            df_weekly = stock.history(period="2y", interval="1wk")
            
            if not df_daily.empty and len(df_daily) >= 15:
                df_daily['RSI'] = ta.momentum.RSIIndicator(close=df_daily['Close'], window=14).rsi()
                macd = ta.trend.MACD(close=df_daily['Close'])
                df_daily['MACD_Diff'] = macd.macd_diff()
                
                latest = df_daily.iloc[-1]
                prev = df_daily.iloc[-2]
                
                fig = make_subplots(
                    rows=2, cols=1, 
                    shared_xaxes=False, vertical_spacing=0.15,
                    subplot_titles=(f"日足（短期のエントリー用） - {mtf_ticker}", f"週足（長期のトレンド確認用） - {mtf_ticker}"),
                    specs=[[{"secondary_y": True}], [{"secondary_y": True}]]
                )
                
                fig.add_trace(go.Candlestick(x=df_daily.index, open=df_daily['Open'], high=df_daily['High'], low=df_daily['Low'], close=df_daily['Close'], name="日足"), row=1, col=1, secondary_y=False)
                fig.add_trace(go.Bar(x=df_daily.index, y=df_daily['Volume'], name="出来高", marker_color='rgba(150, 150, 150, 0.4)'), row=1, col=1, secondary_y=True)
                
                if not df_weekly.empty:
                    fig.add_trace(go.Candlestick(x=df_weekly.index, open=df_weekly['Open'], high=df_weekly['High'], low=df_weekly['Low'], close=df_weekly['Close'], name="週足"), row=2, col=1, secondary_y=False)
                    fig.add_trace(go.Bar(x=df_weekly.index, y=df_weekly['Volume'], name="週出来高", marker_color='rgba(150, 150, 150, 0.4)'), row=2, col=1, secondary_y=True)
                
                fig.update_layout(height=800, xaxis_rangeslider_visible=False, xaxis2_rangeslider_visible=False)
                
                # 【修正】X軸の日付フォーマットをスッキリ表示
                fig.update_xaxes(tickformat="%y/%m/%d", row=1, col=1)
                fig.update_xaxes(tickformat="%y/%m", row=2, col=1)
                
                fig.update_yaxes(title_text="株価", secondary_y=False)
                fig.update_yaxes(title_text="出来高", secondary_y=True, showgrid=False)
                st.plotly_chart(fig, use_container_width=True)

                st.markdown("### 🤖 銘柄テクニカル ＆ ファンダメンタル診断")
                rsi_val = latest['RSI']
                is_gc = (prev['MACD_Diff'] < 0) and (latest['MACD_Diff'] > 0)
                
                if len(df_daily) >= 200:
                    df_daily['SMA200'] = ta.trend.SMAIndicator(close=df_daily['Close'], window=200).sma_indicator()
                    sma_val = df_daily['SMA200'].iloc[-1]
                    is_uptrend = not pd.isna(sma_val) and (latest['Close'] > sma_val)
                else:
                    is_uptrend = None
                
                per_str = f"{t_data['PER']}倍" if t_data and t_data['PER'] != "-" else "データなし"
                pbr_str = f"{t_data['PBR']}倍" if t_data and t_data['PBR'] != "-" else "データなし"
                div_str = f"{t_data['配当利回り(%)']}%" if t_data and t_data['配当利回り(%)'] != "-" else "データなし"

                col_f1, col_f2, col_f3 = st.columns(3)
                col_f1.metric("PER (株価収益率)", per_str)
                col_f2.metric("PBR (株価純資産倍率)", pbr_str)
                col_f3.metric("配当利回り", div_str)
                
                analysis_text = f"**【{mtf_ticker} の現状分析】**\n\n"
                
                if is_uptrend is True:
                    analysis_text += "☀️ **長期トレンド:** 200日移動平均線を上回っており、長期的な上昇トレンドに乗っています。\n"
                elif is_uptrend is False:
                    analysis_text += "☔ **長期トレンド:** 200日移動平均線を下回っており、長期的には下落傾向（または調整中）です。\n"
                
                if not pd.isna(rsi_val):
                    if rsi_val <= 35:
                        analysis_text += f"📉 **過熱感 (RSI: {rsi_val:.1f}):** 30に近く「売られすぎ」の水準です。反発を狙うチャンスです。\n"
                    elif rsi_val >= 70:
                        analysis_text += f"🔥 **過熱感 (RSI: {rsi_val:.1f}):** 70を超え「買われすぎ」です。高値掴みのリスクがあるため見送りを推奨します。\n"
                    else:
                        analysis_text += f"⚖️ **過熱感 (RSI: {rsi_val:.1f}):** 中立な状態です。\n"
                    
                if is_gc:
                    analysis_text += "🟢 **MACD:** **ゴールデンクロス発生！** 短期的な下落が終わり、上昇トレンドに転換する初動のサインです。\n"
                elif latest['MACD_Diff'] > 0:
                    analysis_text += "📈 **MACD:** 短期的には上昇の勢いが強い状態です。\n"
                else:
                    analysis_text += "📉 **MACD:** 短期的には下落圧力がかかっています。底を打つまで様子見が無難です。\n"

                st.info(analysis_text)
                
                st.markdown("### 📰 関連ニュース（最新ヘッドライン）")
                news_data = get_google_news(t_data['銘柄名'] if t_data else t_mtf)
                if news_data:
                    for n in news_data:
                        st.write(f"- 🔗 [{n['title']}]({n['link']}) \n  *(配信日時: {n['date']})*")
                else:
                    st.write("関連ニュースが見つかりませんでした。")
                    
            else:
                st.warning("選択された銘柄のチャートデータを十分に取得できませんでした。")

# ------------------------------------------
# TAB 3: ポートフォリオ・売り時判定
# ------------------------------------------
elif st.session_state.active_tab == "💼 ポートフォリオ判定":
    st.header("💼 保有銘柄の監視・高度な売り時判定")
    all_master_tickers = {}
    all_master_tickers.update(MAJOR_STOCKS_JP)
    all_master_tickers.update(MAJOR_STOCKS_US)
    all_master_tickers.update(get_nikkei225_tickers())
    portfolio_ticker_options = [f"{name} ({code})" for name, code in all_master_tickers.items()]
    
    with st.expander("➕ 新しい保有銘柄を追加 (検索対応)", expanded=True):
        with st.form("add_portfolio_form", clear_on_submit=True):
            p_sel = st.selectbox(
                "銘柄を検索・選択してください", 
                portfolio_ticker_options, 
                index=None, 
                placeholder="ここをクリックして文字入力で検索"
            )
            col1, col2, col3 = st.columns(3)
            p_price = col1.number_input("平均買値 (1株あたり)", min_value=0.0, format="%.2f", step=10.0)
            p_shares = col2.number_input("保有株数", min_value=1)
            p_memo = col3.text_input("メモ")
            
            if st.form_submit_button("ポートフォリオに追加"):
                if p_sel:
                    t_code = p_sel.split("(")[-1].replace(")", "")
                    new_row = pd.DataFrame([{"Ticker": t_code, "買値": p_price, "株数": p_shares, "メモ": p_memo}])
                    st.session_state.portfolio_df = pd.concat([st.session_state.portfolio_df, new_row], ignore_index=True)
                    st.session_state.portfolio_df.to_csv(PORTFOLIO_FILE, index=False)
                    st.success(f"{p_sel} を追加しました！")
                    st.rerun()

    if not st.session_state.portfolio_df.empty:
        status_data = []
        total_profit = 0
        win_count = 0
        warning_count = 0
        detailed_evaluations = []

        for idx, row in st.session_state.portfolio_df.iterrows():
            t = row['Ticker']
            try:
                stock = yf.Ticker(t)
                hist = stock.history(period="3mo")
                if hist.empty: continue
                
                latest_price = float(hist['Close'].iloc[-1])
                buy_price = float(row['買値'])
                
                profit_rate = ((latest_price - buy_price) / buy_price) * 100 if buy_price > 0 else 0
                profit_value = (latest_price - buy_price) * float(row['株数'])
                total_profit += profit_value
                if profit_rate > 0: win_count += 1
                
                recent_high = float(hist['High'].max())
                trailing_stop = recent_high * 0.90 
                hard_stop_loss = buy_price * 0.85 
                
                bb = ta.volatility.BollingerBands(close=hist['Close'], window=20, window_dev=2)
                bb_high = bb.bollinger_hband().iloc[-1]
                sma25 = ta.trend.SMAIndicator(close=hist['Close'], window=25).sma_indicator().iloc[-1]
                
                sell_signal = "ホールド 🛡️"
                if buy_price > 0:
                    if latest_price <= hard_stop_loss:
                        sell_signal = "💀 損切りライン到達"
                        warning_count += 1
                    elif latest_price <= trailing_stop and profit_rate > 0:
                        sell_signal = "📉 トレール割れ (利益確保)"
                        warning_count += 1
                    elif not pd.isna(bb_high) and latest_price > bb_high:
                        sell_signal = "🔥 BB+2σ超え (短期利確警戒)"
                    elif not pd.isna(sma25) and latest_price < sma25 and profit_rate > 0:
                        sell_signal = "⚠️ 短期トレンド崩れ (利確検討)"
                
                jp_name_found = t
                for name, code in all_master_tickers.items():
                    if code == t:
                        jp_name_found = name
                        break

                status_data.append({
                    "Ticker": t,
                    "銘柄名": jp_name_found,
                    "現在のアクション": sell_signal,
                    "現在値": f"{latest_price:,.1f}",
                    "買値": f"{buy_price:,.1f}",
                    "含み損益": f"{profit_value:,.1f}",
                    "損益率(%)": round(profit_rate, 2)
                })

                eval_text = ""
                target_price_20 = buy_price * 1.20
                stop_loss_10 = buy_price * 0.90

                if latest_price >= target_price_20:
                    eval_text += f"- **🎯 利確目線**: すでに+20%以上の利益（目安: {target_price_20:,.1f}）が出ています。一部利益確定や逆指値の引き上げを推奨します。\n"
                elif latest_price > buy_price:
                    eval_text += "- **🎯 利確目線**: 順調に含み益が出ています。このままトレンドに乗ってホールドし、利益を伸ばす方針が有効です。\n"
                
                if latest_price <= stop_loss_10:
                    eval_text += f"- **🚨 損切り目線**: 買値から10%以上下落（防衛ライン: {stop_loss_10:,.1f}）しています。致命傷を防ぐため早めの損切り（撤退）を強く検討してください。\n"
                elif latest_price < buy_price:
                    eval_text += f"- **⚠️ 損切り目線**: 含み損です。あらかじめ決めた損切りライン（例: 買値の-8%）を割ったら迷わず売る準備をしてください。\n"
                
                if sell_signal == "ホールド 🛡️":
                    eval_text += "- **💎 ホールド推奨**: テクニカル指標に大きな崩れはありません。中長期での保有継続をおすすめします。\n"
                
                detailed_evaluations.append({
                    "name": jp_name_found,
                    "ticker": t,
                    "buy_price": buy_price,
                    "current": latest_price,
                    "eval": eval_text
                })

            except Exception:
                continue
                
        if status_data:
            st.dataframe(pd.DataFrame(status_data), use_container_width=True)
            col_a, col_b, col_c = st.columns(3)
            pf_len = len(status_data)
            win_rate = (win_count / pf_len) * 100 if pf_len > 0 else 0
            
            col_a.metric("トータル含み損益", f"¥{total_profit:,.0f}")
            col_b.metric("ポートフォリオ勝率", f"{win_rate:.1f}%", f"{win_count}勝 / {pf_len - win_count}敗")
            
            if warning_count > 0:
                col_c.error(f"⚠️ {warning_count}銘柄に利確・損切りのサインが出ています。")
            else:
                col_c.success("🌟 トレンドに乗れています。ホールド継続推奨。")

            st.markdown("---")
            st.markdown("### 🤖 多角的な判定・アドバイス詳細")
            for item in detailed_evaluations:
                with st.expander(f"📌 {item['name']} ({item['ticker']}) - 買値: {item['buy_price']:,.1f} → 現在値: {item['current']:,.1f}", expanded=False):
                    st.markdown(item['eval'])

        if st.button("ポートフォリオを全件リセット", type="primary"):
            st.session_state.portfolio_df = pd.DataFrame(columns=["Ticker", "買値", "株数", "メモ"])
            if os.path.exists(PORTFOLIO_FILE): os.remove(PORTFOLIO_FILE)
            st.rerun()

# ------------------------------------------
# TAB 4: 資金配分
# ------------------------------------------
elif st.session_state.active_tab == "💰 資金配分":
    st.header("💰 ミニ株・分散投資シミュレーター (日本円計算)")
    total_budget = st.number_input("投資予算を入力 (日本円)", min_value=10000, value=2000000, step=100000)
    
    if test_options:
        selected_for_sim = st.multiselect(
            "分散投資したい銘柄を選択", test_options, default=test_options[:2] if len(test_options)>1 else test_options
        )
        sim_data, used_budget_jpy = [], 0
        for sel in selected_for_sim:
            t_sim = sel.split("(")[-1].replace(")", "")
            t_data = next((r for r in market_data if r['Ticker'] == t_sim), None)
            if t_data:
                price, currency = t_data['現在値'], t_data['通貨']
                shares = st.number_input(f"{sel} の購入株数", min_value=0, value=10, key=f"sim_{t_sim}")
                cost_local = price * shares
                cost_jpy = cost_local * usd_jpy_rate if currency == "USD" else cost_local
                used_budget_jpy += cost_jpy
                sim_data.append({"銘柄": sel, "1株価格": f"{price:,.2f} {currency}", "株数": shares, "必要資金(円換算)": f"¥{round(cost_jpy):,}"})
        
        if sim_data:
            st.dataframe(pd.DataFrame(sim_data), use_container_width=True)
            remaining = total_budget - used_budget_jpy
            col1, col2 = st.columns(2)
            col1.metric("使用資金(円)", f"¥{used_budget_jpy:,.0f}")
            if remaining >= 0:
                col2.metric("予算残高(円)", f"¥{remaining:,.0f}")
                st.success(f"予算内です！残り {remaining:,.0f} 円は現金余力として待機できます。")
            else:
                col2.metric("予算オーバー(円)", f"¥{remaining:,.0f}", delta_color="inverse")
                st.error("予算をオーバーしています。")