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
from email.utils import parsedate_to_datetime
import requests

# ------------------------------------------
# ページ設定
# ------------------------------------------
st.set_page_config(page_title="総合投資ダッシュボード", layout="wide", initial_sidebar_state="expanded")
st.title("🦅 グローバル・マルチ投資ダッシュボード")

# ------------------------------------------
# 定数・設定ファイル
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
ALERTS_FILE = "alerts.csv"

# LINE認証情報の初期値設定
DEFAULT_LINE_TOKEN = "5tixnuTNtGg4kcYchf0EHxZdgdSfG7VwrxRRw3XsrDAwvYVmAJoUzhxEMo9SknD/T4vcPHrA1OTUHO3xy4kiAchUSB+MzgqNrmi5ue5gIl4jAtkL12M26oLflVAmvrOIfio6TUI3R4oR10KpIfV/ywdB04t89/1O/w1cDnyilFU="
DEFAULT_LINE_USER_ID = "U13ae39891172d8f144b303ec5b404b62"

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

def analyze_single_stock(name, ticker, strategy):
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
            
        target_price = latest['BB_Low'] if not pd.isna(latest['BB_Low']) else latest['SMA25']
        currency = info.get('currency', 'JPY' if ticker.endswith('.T') else 'USD')
        
        per = info.get('trailingPE', None)
        pbr = info.get('priceToBook', None)
        
        div_yield = info.get('dividendYield', None)
        if div_yield is not None:
            if div_yield > 0.2:
                div_yield_disp = round(div_yield, 2)
            else:
                div_yield_disp = round(div_yield * 100, 2)
        else:
            div_yield_disp = "-"
        
        # 1. テクニカルスコア計算
        score = 0
        if is_uptrend: score += 30
        if macd_gc: score += 20
        elif latest['MACD_Diff'] > 0: score += 10
        
        if 30 <= rsi_val <= 45: score += 30
        elif rsi_val < 30: score += 10 
        elif 45 < rsi_val <= 60: score += 10

        # 2. ファンダメンタルズ補正
        overvalued_flag = False
        is_fundamental_good = False
        
        if strategy == "中長期割安 (総合判断)":
            if per and isinstance(per, (int, float)):
                if per > 50:
                    score -= 30
                    overvalued_flag = True
                elif per > 30:
                    score -= 15
                    overvalued_flag = True
                elif 0 < per <= 15:
                    score += 15
                    is_fundamental_good = True

            if pbr and isinstance(pbr, (int, float)):
                if pbr > 4.0:
                    score -= 15
                    overvalued_flag = True
                elif 0 < pbr <= 1.0:
                    score += 10
                    is_fundamental_good = True

        # 3. アクション判定
        if rsi_val > 70:
            action = "高値警戒（見送り） 🛑"
            target_str = f"過熱。{round(float(target_price), 1)} まで調整待ち"
            score = -50  
        elif (rsi_val <= 40 or macd_gc) and not overvalued_flag:
            action = "今すぐ買い候補 🚀"
            target_str = "現在値付近が買い時"
        elif (rsi_val <= 40 or macd_gc) and overvalued_flag:
            action = "テクニカル良好（割高警戒） ⚠️"
            target_str = f"高PER/PBR注意（押し目: {round(float(target_price), 1)}）"
        else:
            action = "様子見 ⏳"
            target_str = f"押し目目安: {round(float(target_price), 1)}"
            
        # 4. 初心者向けコメントの生成
        comment = ""
        if "様子見" in action:
            if is_fundamental_good:
                comment = "💡 【解説】 企業の基礎体力や割安度は文句なしのトップクラスですが、今この瞬間の買いタイミングとしては、あと少し引きつけた方が安全な銘柄です。"
            else:
                comment = "💡 【解説】 現在は明確な買いサインが出ていません。設定された押し目目安まで下落するのを待つのが無難です。"
        elif "今すぐ買い候補" in action:
            if is_fundamental_good:
                comment = "💡 【解説】 割安かつチャートも底値圏！非常に条件が揃った文句なしの買い候補です。"
            else:
                comment = "💡 【解説】 テクニカル指標が明確な買いサインを出しています！短期的な上昇トレンドの波に乗れる可能性があります。"
        elif "割高警戒" in action:
            comment = "💡 【解説】 チャートの形は良いですが、株価が企業価値に対して割高水準にあります。急な下落（高値掴み）に注意してください。"
        elif "高値警戒" in action:
            comment = "💡 【解説】 相場が過熱しており、いつ利益確定の売りが出てもおかしくない状態です。今は手を出さないのが吉です。"
        
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
            "配当利回り(%)": div_yield_disp,
            "初心者向けコメント": comment
        }
    except Exception:
        return None

def fetch_and_analyze(tickers_dict, strategy):
    data = []
    total = len(tickers_dict)
    if total == 0: return data
    
    progress_text = st.empty()
    progress_bar = st.progress(0)
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_to_stock = {executor.submit(analyze_single_stock, name, t, strategy): name for name, t in tickers_dict.items()}
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
            
            try:
                dt = parsedate_to_datetime(pubDate)
                formatted_date = dt.strftime("%y/%m/%d %H:%M")
            except:
                formatted_date = pubDate

            news_list.append({'title': title, 'link': link, 'date': formatted_date})
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

if "alerts_df" not in st.session_state:
    if os.path.exists(ALERTS_FILE):
        try:
            st.session_state.alerts_df = pd.read_csv(ALERTS_FILE)
        except:
            st.session_state.alerts_df = pd.DataFrame(columns=["Ticker", "銘柄名", "通知条件", "目標価格"])
    else:
        st.session_state.alerts_df = pd.DataFrame(columns=["Ticker", "銘柄名", "通知条件", "目標価格"])
        
if "selected_ticker" not in st.session_state:
    st.session_state.selected_ticker = None

if "active_tab" not in st.session_state:
    st.session_state.active_tab = "🏆 ランキング"

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
    
    strategy_choice = st.radio(
        "🧠 投資スタイル (判定ロジック)", 
        ["中長期割安 (総合判断)", "短期スイング (テクニカル重視)"],
        help="【総合判断】はPER/PBRも加味して割高株を排除します。【テクニカル重視】は業績を無視し、チャートの勢いのみで判定します。"
    )
    
    mode_choice = "主要銘柄"
    if market_choice == "🇯🇵 日本株":
        mode_choice = st.radio("📊 銘柄モード (日本株)", ["日経225全銘柄", "主要銘柄"])
    else:
        st.write("📊 銘柄モード: 主要米国株 (TSM等含む)")
    
    custom_tickers_input = st.text_input("➕ 追加ティッカー (例: 8267.T, PLTR)")
    submitted = st.form_submit_button("🚀 この条件で分析を実行する")

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
        st.session_state.market_data = fetch_and_analyze(target_tickers, strategy_choice)
        st.session_state.market_choice_name = market_choice
        st.session_state.strategy_name = strategy_choice

market_data = st.session_state.market_data
test_options = sorted([f"{row['銘柄名']} ({row['Ticker']})" for row in market_data]) if market_data else []
usd_jpy_rate = macro_data.get("JPY=X", {}).get("price", 150.0) if macro_data else 150.0

all_master_tickers = {}
all_master_tickers.update(MAJOR_STOCKS_JP)
all_master_tickers.update(MAJOR_STOCKS_US)
all_master_tickers.update(get_nikkei225_tickers())
full_ticker_options = [f"{name} ({code})" for name, code in all_master_tickers.items()]

# ==========================================
# カスタムUI タブ構成
# ==========================================
tabs = ["🏆 ランキング", "📈 チャート", "💼 ポートフォリオ", "💰 資金配分", "🔔 LINE通知"]
selected_tab = st.radio("メニュー", tabs, index=tabs.index(st.session_state.active_tab), horizontal=True, label_visibility="collapsed")

if selected_tab != st.session_state.active_tab:
    st.session_state.active_tab = selected_tab
    st.rerun()

# ------------------------------------------
# TAB 1: 買い時ランキング
# ------------------------------------------
if st.session_state.active_tab == "🏆 ランキング":
    st.header(f"🏆 {st.session_state.get('market_choice_name', '日本株')} トップ10")
    st.caption(f"現在の判定ロジック: **{st.session_state.get('strategy_name', '中長期割安 (総合判断)')}**")
    
    show_only_buy_now = st.toggle("🚀 『今すぐ買い』銘柄のみ表示", value=False)
    
    if market_data:
        res_df = pd.DataFrame(market_data).sort_values('総合スコア', ascending=False)
        
        if show_only_buy_now:
            res_df = res_df[res_df['推奨アクション'].str.contains('今すぐ買い')]
            
        display_df = res_df.reset_index(drop=True)
        display_df.index = display_df.index + 1
        
        if display_df.empty:
            st.info("現在「今すぐ買い」の条件を満たす銘柄はありません。")
        else:
            for idx, row in display_df.head(10).iterrows():
                with st.container(border=True):
                    col_left, col_right = st.columns([3, 1])
                    with col_left:
                        st.markdown(f"#### **{idx}位 : {row['銘柄名']}** (`{row['Ticker']}`)")
                        st.write(f"**判定:** {row['推奨アクション']} | **スコア:** {row['総合スコア']}点")
                        st.write(f"**現在値:** {row['現在値']} {row['通貨']} | **目標:** {row['目標買値']}")
                        st.caption(f"PER: {row['PER']}倍 | PBR: {row['PBR']}倍 | RSI: {row['RSI(過熱感)']}%")
                    with col_right:
                        st.write("") 
                        if st.button("チャート 📈", key=f"btn_{row['Ticker']}"):
                            st.session_state.selected_ticker = row['Ticker']
                            st.session_state.active_tab = "📈 チャート"
                            st.rerun()
                    if row['初心者向けコメント']:
                        st.info(row['初心者向けコメント'])
                    
            st.markdown("---")
            with st.expander("📊 全データの表を見る"):
                st.dataframe(display_df, use_container_width=True)
    else:
        st.warning("表示できるデータがありません。サイドバーから分析を実行してください。")

# ------------------------------------------
# TAB 2: マルチタイムフレーム分析
# ------------------------------------------
elif st.session_state.active_tab == "📈 チャート":
    st.header("📈 マルチタイムフレーム ＆ 出来高分析")
    if test_options:
        default_idx = 0
        if st.session_state.selected_ticker:
            for i, opt in enumerate(test_options):
                if st.session_state.selected_ticker in opt:
                    default_idx = i
                    break

        mtf_ticker = st.selectbox(
            "銘柄を検索・選択", 
            test_options, 
            key="mtf", 
            index=default_idx
        )
        
        if mtf_ticker:
            t_mtf = mtf_ticker.split("(")[-1].replace(")", "")
            t_data = next((r for r in market_data if r['Ticker'] == t_mtf), None)
            
            if t_data:
                st.markdown(f"## {t_data['銘柄名']} | 現在の株価: **{t_data['現在値']} {t_data['通貨']}**")
                with st.container():
                    m_col1, m_col2, m_col3, m_col4 = st.columns(4)
                    m_col1.metric("総合スコア", f"{t_data['総合スコア']}点")
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
                    subplot_titles=(f"日足（短期用） - {mtf_ticker}", f"週足（長期用） - {mtf_ticker}"),
                    specs=[[{"secondary_y": True}], [{"secondary_y": True}]]
                )
                
                fig.add_trace(go.Candlestick(x=df_daily.index, open=df_daily['Open'], high=df_daily['High'], low=df_daily['Low'], close=df_daily['Close'], name="日足"), row=1, col=1, secondary_y=False)
                fig.add_trace(go.Bar(x=df_daily.index, y=df_daily['Volume'], name="出来高", marker_color='rgba(150, 150, 150, 0.4)'), row=1, col=1, secondary_y=True)
                
                if not df_weekly.empty:
                    fig.add_trace(go.Candlestick(x=df_weekly.index, open=df_weekly['Open'], high=df_weekly['High'], low=df_weekly['Low'], close=df_weekly['Close'], name="週足"), row=2, col=1, secondary_y=False)
                    fig.add_trace(go.Bar(x=df_weekly.index, y=df_weekly['Volume'], name="週出来高", marker_color='rgba(150, 150, 150, 0.4)'), row=2, col=1, secondary_y=True)
                
                fig.update_layout(height=800, xaxis_rangeslider_visible=False, xaxis2_rangeslider_visible=False)
                
                fig.update_xaxes(tickformat="%y/%m/%d", row=1, col=1)
                fig.update_xaxes(tickformat="%y/%m", row=2, col=1)
                
                st.plotly_chart(fig, use_container_width=True)

                col_f1, col_f2, col_f3 = st.columns(3)
                col_f1.metric("PER (株価収益率)", f"{t_data['PER']}倍" if t_data else "-")
                col_f2.metric("PBR (株価純資産倍率)", f"{t_data['PBR']}倍" if t_data else "-")
                col_f3.metric("配当利回り", f"{t_data['配当利回り(%)']}%" if t_data else "-")
                
                st.markdown("### 📰 関連ニュース")
                news_data = get_google_news(t_data['銘柄名'] if t_data else t_mtf)
                if news_data:
                    for n in news_data:
                        st.write(f"- 🔗 [{n['title']}]({n['link']}) \n  *(配信日時: {n['date']})*")
                else:
                    st.write("関連ニュースが見つかりませんでした。")

# ------------------------------------------
# TAB 3: ポートフォリオ・売り時判定
# ------------------------------------------
elif st.session_state.active_tab == "💼 ポートフォリオ":
    st.header("💼 保有銘柄の監視")
    
    with st.expander("➕ 新しい保有銘柄を追加", expanded=True):
        with st.form("add_portfolio_form", clear_on_submit=True):
            p_sel = st.selectbox("銘柄を検索・選択", full_ticker_options, index=None)
            col1, col2, col3 = st.columns(3)
            p_price = col1.number_input("平均買値", min_value=0.0, format="%.2f", step=10.0)
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
        for idx, row in st.session_state.portfolio_df.iterrows():
            t = row['Ticker']
            try:
                stock = yf.Ticker(t)
                hist = stock.history(period="1d")
                if hist.empty: continue
                latest_price = float(hist['Close'].iloc[-1])
                buy_price = float(row['買値'])
                profit_rate = ((latest_price - buy_price) / buy_price) * 100 if buy_price > 0 else 0
                
                jp_name_found = t
                for name, code in all_master_tickers.items():
                    if code == t: jp_name_found = name; break

                status_data.append({
                    "Ticker": t, "銘柄名": jp_name_found, 
                    "現在値": f"{latest_price:,.1f}", "買値": f"{buy_price:,.1f}",
                    "損益率(%)": round(profit_rate, 2)
                })
            except Exception:
                continue
                
        if status_data:
            st.dataframe(pd.DataFrame(status_data), use_container_width=True)

# ------------------------------------------
# TAB 4: 資金配分
# ------------------------------------------
elif st.session_state.active_tab == "💰 資金配分":
    st.header("💰 分散投資シミュレーター")
    st.info("予算を入力し、買いたい銘柄を選ぶとシミュレーションができます。")

# ------------------------------------------
# TAB 5: LINE Messaging API通知
# ------------------------------------------
elif st.session_state.active_tab == "🔔 LINE通知":
    st.header("🔔 LINE Messaging API 株価アラート設定")
    st.markdown("""
    **💡 あらかじめ設定されたトークンとユーザーIDが初期入力されています。**
    """)
    
    col_t1, col_t2 = st.columns(2)
    line_access_token = col_t1.text_input("🔑 チャネルアクセストークン", value=DEFAULT_LINE_TOKEN, type="password")
    line_user_id = col_t2.text_input("👤 Your user ID (ユーザーID)", value=DEFAULT_LINE_USER_ID, type="password")
    
    with st.expander("➕ 新しい通知アラートを登録", expanded=True):
        with st.form("add_alert_form", clear_on_submit=True):
            a_sel = st.selectbox("監視する銘柄を選択", full_ticker_options, index=None)
            col1, col2 = st.columns(2)
            a_condition = col1.radio("通知条件", ["指定価格以下になったら (買い時)", "指定価格以上になったら (売り時)"])
            a_price = col2.number_input("目標価格", min_value=0.0, format="%.2f", step=10.0)
            
            if st.form_submit_button("アラート登録"):
                if a_sel and a_price > 0:
                    t_code = a_sel.split("(")[-1].replace(")", "")
                    t_name = a_sel.split(" (")[0]
                    new_alert = pd.DataFrame([{"Ticker": t_code, "銘柄名": t_name, "通知条件": a_condition, "目標価格": a_price}])
                    st.session_state.alerts_df = pd.concat([st.session_state.alerts_df, new_alert], ignore_index=True)
                    st.session_state.alerts_df.to_csv(ALERTS_FILE, index=False)
                    st.success(f"{t_name} のアラートを登録しました！")
                    st.rerun()

    if not st.session_state.alerts_df.empty:
        st.subheader("📋 登録中のアラート一覧")
        st.dataframe(st.session_state.alerts_df, use_container_width=True)
        
        if st.button("🔄 監視を実行（条件合致でLINE送信）", type="primary"):
            if not line_access_token or not line_user_id:
                st.error("上の入力欄に『アクセストークン』と『ユーザーID』を入力してください。")
            else:
                with st.spinner("現在の株価を取得し、アラートをチェック中..."):
                    notified_count = 0
                    for idx, row in st.session_state.alerts_df.iterrows():
                        t = row['Ticker']
                        target_p = float(row['目標価格'])
                        cond = row['通知条件']
                        name = row['銘柄名']
                        
                        try:
                            stock = yf.Ticker(t)
                            hist = stock.history(period="1d")
                            if hist.empty: continue
                            current_p = float(hist['Close'].iloc[-1])
                            
                            trigger = False
                            if "以下" in cond and current_p <= target_p:
                                trigger = True
                            elif "以上" in cond and current_p >= target_p:
                                trigger = True
                                
                            if trigger:
                                message_text = f"🚨 株価アラート発動！\n銘柄: {name} ({t})\n現在値: {current_p:,.2f}\n条件: {target_p:,.2f} {cond.split(' ')[0]}"
                                
                                url = "https://api.line.me/v2/bot/message/push"
                                headers = {
                                    "Authorization": f"Bearer {line_access_token}",
                                    "Content-Type": "application/json"
                                }
                                payload = {
                                    "to": line_user_id,
                                    "messages": [{"type": "text", "text": message_text}]
                                }
                                
                                res = requests.post(url, headers=headers, json=payload)
                                if res.status_code == 200:
                                    st.success(f"📱 {name} のアラートをLINEに送信しました！")
                                    notified_count += 1
                                else:
                                    st.error(f"送信失敗 ({res.status_code}): トークンやIDを確認してください。\nエラー内容: {res.text}")
                        except Exception as e:
                            st.write(f"エラー: {e}")
                            continue
                            
                    if notified_count == 0:
                        st.info("現在、条件を満たしている銘柄はありませんでした。")
                        
        if st.button("アラートを全件リセット"):
            st.session_state.alerts_df = pd.DataFrame(columns=["Ticker", "銘柄名", "通知条件", "目標価格"])
            if os.path.exists(ALERTS_FILE): os.remove(ALERTS_FILE)
            st.rerun()