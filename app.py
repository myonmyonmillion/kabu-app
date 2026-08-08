import streamlit as st
import yfinance as yf
import pandas as pd
import ta
import os
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import concurrent.futures

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
    "ファーストリテイリング": "9983.T", "ソフトバンクグループ": "9984.T", "東京エレクトロン": "8035.T"
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
    """外部アクセスに依存しない完全内蔵型の日経225銘柄リスト"""
    raw_data = (
        "1332.T ニッスイ,1333.T マルハニチロ,2002.T 日清製粉G,2269.T 明治HD,2282.T 日本ハム,"
        "2413.T エムスリー,2432.T ディー・エヌ・エー,2501.T サッポロHD,2502.T アサヒGHD,2503.T キリンHD,2531.T 宝HD,2768.T 双日,2801.T キッコーマン,2802.T 味の素,2871.T ニチレイ,2914.T JT,3086.T Jフロント,3099.T 三越伊勢丹,3289.T 東急不動産,3382.T セブン&アイ,"
        "3401.T 帝人,3402.T 東レ,3405.T クラレ,3407.T 旭化成,3436.T SUMCO,3659.T ネクソン,3861.T 王子HD,3863.T 日本製紙,4004.T レゾナック,4005.T 住友化学,4021.T 日産化学,4041.T 日本曹達,4042.T 東ソー,4043.T トクヤマ,4061.T デンカ,4063.T 信越化学,4151.T 協和キリン,4183.T 三井化学,4188.T 三菱ケミカル,4208.T UBE,4324.T 電通G,4452.T 花王,"
        "4502.T 武田薬品,4503.T アステラス製薬,4506.T 住友ファーマ,4507.T 塩野義製薬,4519.T 中外製薬,4523.T エーザイ,4568.T 第一三共,4578.T 大塚HD,4689.T LINEヤフー,4704.T トレンドマイクロ,4751.T サイバーエージェント,4755.T 楽天G,4901.T 富士フイルム,4911.T 資生堂,5019.T 出光興産,5020.T ENEOS,5101.T 横浜ゴム,5108.T ブリヂストン,5201.T AGC,5202.T 日本板硝子,5214.T 日本電気硝子,5232.T 住友大阪セメント,5233.T 太平洋セメント,5301.T 東海カーボン,5332.T TOTO,5333.T 日本ガイシ,"
        "5401.T 日本製鉄,5406.T 神戸製鋼所,5411.T JFEHD,5541.T 大平洋金属,5631.T 日本製鋼所,5703.T 日本軽金属,5706.T 三井金属,5711.T 三菱マテリアル,5713.T 住友金属鉱山,5714.T DOWA,5801.T 古河電工,5802.T 住友電工,5803.T フジクラ,5831.T しずおかFG,6098.T リクルートHD,6103.T オークマ,6118.T アイダ,6273.T SMC,6301.T コマツ,6302.T 住友重機械,6305.T 日立建機,6326.T クボタ,6361.T 荏原製作所,6367.T ダイキン,6471.T 日本精工,6472.T NTN,6473.T ジェイテクト,6501.T 日立製作所,6503.T 三菱電機,6504.T 富士電機,6506.T 安川電機,6526.T ソシオネクスト,6594.T ニデック,"
        "6645.T オムロン,6701.T NEC,6702.T 富士通,6723.T ルネサス,6724.T エプソン,6752.T パナソニック,6758.T ソニーG,6762.T TDK,6770.T アルプスアルパイン,6841.T 横河電機,6857.T アドバンテスト,6861.T キーエンス,6902.T デンソー,6952.T カシオ,6954.T ファナック,6971.T 京セラ,6976.T 太陽誘電,6981.T 村田製作所,6988.T 日東電工,"
        "7011.T 三菱重工,7012.T 川崎重工,7013.T IHI,7186.T コンコルディア,7201.T 日産自動車,7202.T いすゞ自動車,7203.T トヨタ自動車,7205.T 日野自動車,7211.T 三菱自動車,7261.T マツダ,7267.T ホンダ,7269.T スズキ,7270.T SUBARU,7272.T ヤマハ発動機,7731.T ニコン,7733.T オリンパス,7735.T SCREEN,7741.T HOYA,7751.T キヤノン,7752.T リコー,7762.T シチズン時計,7832.T バンダイナムコ,7911.T TOPPAN,7912.T 大日本印刷,7951.T ヤマハ,7974.T 任天堂,"
        "8001.T 伊藤忠商事,8002.T 丸紅,8015.T 豊田通商,8031.T 三井物産,8035.T 東京エレクトロン,8053.T 住友商事,8058.T 三菱商事,8233.T 高島屋,8252.T 丸井G,8267.T イオン,8304.T あおぞら銀行,8306.T 三菱UFJ,8308.T りそなHD,8309.T 三井住友トラスト,8316.T 三井住友FG,8331.T 千葉銀行,8354.T ふくおかFG,8411.T みずほFG,8591.T オリックス,8601.T 大和証券G,8604.T 野村HD,8628.T 松井証券,8630.T SOMPOHD,8725.T MS&AD,8750.T 第一生命HD,8766.T 東京海上HD,8795.T T&DHD,8801.T 三井不動産,8802.T 三菱地所,8804.T 東京建物,8830.T 住友不動産,"
        "9001.T 東武鉄道,9005.T 東急,9007.T 小田急電鉄,9008.T 京王電鉄,9009.T 京成電鉄,9020.T JR東日本,9021.T JR西日本,9022.T JR東海,9064.T ヤマトHD,9101.T 日本郵船,9104.T 商船三井,9107.T 川崎汽船,9147.T NIPPON EXPRESS,9201.T 日本航空,9202.T ANAHD,9301.T 三菱倉庫,9432.T NTT,9433.T KDDI,9434.T ソフトバンク,9501.T 東京電力HD,9502.T 中部電力,9503.T 関西電力,9531.T 東京ガス,9532.T 大阪ガス,9602.T 東宝,9613.T NTTデータG,9735.T セコム,9766.T コナミG,9843.T ニトリHD,9983.T ファーストリテイリング,9984.T ソフトバンクG"
    )
    tickers = {}
    for item in raw_data.split(","):
        if item.strip():
            code, name = item.strip().split(" ", 1)
            tickers[name] = code
    return tickers

@st.cache_data(ttl=3600)
def get_exchange_rate():
    """最新のドル円レートを取得"""
    try:
        return yf.Ticker("JPY=X").history(period="1d")['Close'].iloc[-1]
    except Exception:
        return 150.0

def analyze_single_stock(name, ticker):
    """単一銘柄のデータ取得と分析ロジック"""
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period="2y")
        if df.empty or len(df) < 200: return None
        
        info = stock.info
        display_name = info.get('shortName', name)
        
        df['RSI'] = ta.momentum.RSIIndicator(close=df['Close'], window=14).rsi()
        df['SMA200'] = ta.trend.SMAIndicator(close=df['Close'], window=200).sma_indicator()
        
        macd = ta.trend.MACD(close=df['Close'])
        df['MACD_Diff'] = macd.macd_diff()
        
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        rsi_val = latest['RSI']
        if pd.isna(rsi_val): return None
        
        macd_gc = (prev['MACD_Diff'] < 0) and (latest['MACD_Diff'] > 0)
        long_trend = "上昇中 ☀️" if latest['Close'] > latest['SMA200'] else "下落中 ☔"
        
        currency = info.get('currency', 'JPY')
        min_investment = latest['Close']
        
        return {
            "Ticker": ticker,
            "銘柄名": display_name,
            "セクター": info.get('sector', '不明'),
            "通貨": currency,
            "現在値": round(latest['Close'], 2),
            "1株購入目安": f"{round(min_investment, 2):,} {currency}",
            "長期トレンド": long_trend,
            "RSI(過熱感)": round(rsi_val, 1),
            "MACDサイン": "🟢 GC発生!" if macd_gc else ("反発中" if latest['MACD_Diff'] > 0 else "下落トレンド")
        }
    except Exception:
        return None

def fetch_and_analyze(tickers_dict):
    data = []
    total = len(tickers_dict)
    if total == 0: return data
    
    progress_text = st.empty()
    progress_bar = st.progress(0)
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
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

# ==========================================
# セッションステート（状態保持）の初期化
# ==========================================
# ポートフォリオの初期読み込み（ページジャンプ防止用）
if "portfolio_df" not in st.session_state:
    if os.path.exists(PORTFOLIO_FILE):
        st.session_state.portfolio_df = pd.read_csv(PORTFOLIO_FILE)
    else:
        st.session_state.portfolio_df = pd.DataFrame(columns=["Ticker", "買値", "株数", "メモ"])

# ==========================================
# ⚙️ サイドバー (メニュー & 決定ボタン)
# ==========================================
st.sidebar.header("⚙️ 検索・フィルター設定")

with st.sidebar.form("search_form"):
    market_choice = st.radio("🌐 対象市場を選択", ["🇯🇵 日本株", "🇺🇸 米国株"])
    
    mode_choice = "主要銘柄"
    if market_choice == "🇯🇵 日本株":
        mode_choice = st.radio("📊 銘柄モード (日本株)", ["主要銘柄", "日経225全銘柄"])
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
        st.session_state.market_data = fetch_and_analyze(target_tickers)
        st.session_state.market_choice_name = market_choice

market_data = st.session_state.market_data
test_options = sorted([f"{row['銘柄名']} ({row['Ticker']})" for row in market_data])
usd_jpy_rate = get_exchange_rate()

st.sidebar.markdown("---")
with st.sidebar.expander("📖 投資用語集 (初心者向け)", expanded=False):
    st.markdown("""
    - **ティッカー**: 銘柄を識別する記号。
    - **RSI (相対力指数)**: 「買われすぎ」「売られすぎ」を0〜100で表す温度計。**30以下**なら売られすぎ。
    - **MACD (マックディー)**: トレンドの「方向」と「勢い」を見る指標。
    - **ゴールデンクロス (GC)**: MACDなどの短期線が長期線を下から上に突き抜けること。買いサイン。
    - **SMA200 (200日移動平均線)**: これが上向きなら「長期的に上昇トレンド（☀️）」と判断。
    - **押し目買い**: 長期的に上昇している株が、一時的にカクッと下がったタイミングを狙うローリスクな手法。
    - **指値（さしね）注文**: 「〇〇円まで下がったら買う/売る」と事前に希望価格を指定する注文方法。仕事中の売買に必須。
    """)

# ==========================================
# UI タブ構成 (不要タブを削除してスッキリ化)
# ==========================================
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🏆 買い時ランキング", "🏢 セクター", "💼 ポートフォリオ", 
    "📈 マルチタイムフレーム", "💰 ミニ株・資金配分"
])

# ------------------------------------------
# TAB 1: 買い時ランキング
# ------------------------------------------
with tab1:
    st.header(f"🏆 {st.session_state.get('market_choice_name', '日本株')} 買い時（売られすぎ）ランキング")
    st.markdown("**💡 初心者向けのポイント:** まずは**「RSI(過熱感)」が30に近い銘柄**を探しましょう。長期保有を前提とするなら、**「長期トレンド」が上昇中（☀️）**の銘柄の押し目を狙うのがローリスクです。")
    if market_data:
        res_df = pd.DataFrame(market_data).sort_values('RSI(過熱感)', ascending=True)
        display_df = res_df.reset_index(drop=True)
        display_df.index = display_df.index + 1
        st.dataframe(display_df, use_container_width=True)
    else:
        st.warning("表示できるデータがありません。サイドバーの「分析を実行する」ボタンを押してください。")

# ------------------------------------------
# TAB 2: セクター（業種）分析
# ------------------------------------------
with tab2:
    st.header(f"🏢 セクター別 トレンド分析")
    if market_data:
        sec_df = pd.DataFrame(market_data)
        sector_group = sec_df.groupby('セクター')['RSI(過熱感)'].mean().reset_index()
        sector_group = sector_group.sort_values('RSI(過熱感)', ascending=True).reset_index(drop=True)
        sector_group.index = sector_group.index + 1
        st.dataframe(sector_group, use_container_width=True)

# ------------------------------------------
# TAB 3: ポートフォリオ・売り時判定 (大幅アップデート)
# ------------------------------------------
with tab3:
    st.header("💼 保有銘柄の監視・売り時判定")
    st.markdown("現在の株価と指定した買値を比較し、**目標達成（+10%）**や**損切りライン（-10%）**を自動で判定します。")
    
    # 銘柄選択用のマスターリスト作成（日米＋日経225全て）
    all_master_tickers = {}
    all_master_tickers.update(MAJOR_STOCKS_JP)
    all_master_tickers.update(MAJOR_STOCKS_US)
    all_master_tickers.update(get_nikkei225_tickers())
    portfolio_ticker_options = [f"{name} ({code})" for name, code in all_master_tickers.items()]
    
    with st.expander("➕ 新しい保有銘柄を追加 (検索対応)", expanded=False):
        # selectbox は Streamlit の仕様で文字入力による絞り込み検索（サジェスト）が可能です。
        p_sel = st.selectbox("銘柄を検索・選択してください（直接入力で絞り込み可）", portfolio_ticker_options)
        
        col1, col2, col3 = st.columns(3)
        p_price = col1.number_input("平均買値 (1株あたり)", min_value=0.0, format="%.2f", step=10.0)
        p_shares = col2.number_input("保有株数", min_value=1)
        p_memo = col3.text_input("メモ")
        
        if st.button("ポートフォリオに追加"):
            t_code = p_sel.split("(")[-1].replace(")", "")
            new_row = pd.DataFrame([{"Ticker": t_code, "買値": p_price, "株数": p_shares, "メモ": p_memo}])
            # セッションステートに直接追加することで、リロード時のページジャンプを防止
            st.session_state.portfolio_df = pd.concat([st.session_state.portfolio_df, new_row], ignore_index=True)
            st.session_state.portfolio_df.to_csv(PORTFOLIO_FILE, index=False)
            st.success(f"{p_sel} を追加しました！")

    if not st.session_state.portfolio_df.empty:
        status_data = []
        for idx, row in st.session_state.portfolio_df.iterrows():
            t = row['Ticker']
            try:
                stock = yf.Ticker(t)
                hist = stock.history(period="1mo")
                if hist.empty: continue
                
                latest_price = hist['Close'].iloc[-1]
                buy_price = row['買値']
                
                # 自動計算：利確と損切りの目安ライン
                target_sell = buy_price * 1.10  # +10%
                stop_loss = buy_price * 0.90    # -10%
                
                profit_rate = ((latest_price - buy_price) / buy_price) * 100 if buy_price > 0 else 0
                profit_value = (latest_price - buy_price) * row['株数']
                
                rsi = ta.momentum.RSIIndicator(hist['Close'], window=14).rsi().iloc[-1]
                macd = ta.trend.MACD(hist['Close'])
                macd_diff = macd.macd_diff().iloc[-1]
                
                # 売り時・現状分析のロジック
                sell_signal = "ホールド 🛡️"
                if buy_price > 0:
                    if latest_price >= target_sell:
                        sell_signal = "🎯 目標達成 (+10%超・利確推奨)"
                    elif latest_price <= stop_loss:
                        sell_signal = "💀 損切りライン到達 (-10%)"
                    elif rsi >= 70:
                        sell_signal = "⚠️ RSI過熱 (そろそろ利確警戒)"
                    elif macd_diff < 0 and profit_rate > 0:
                        sell_signal = "📉 トレンド下落 (利益確保の目安)"

                status_data.append({
                    "Ticker": t,
                    "銘柄名": stock.info.get('shortName', t),
                    "現在のアクション": sell_signal,
                    "現在値": f"{latest_price:,.1f}",
                    "買値": f"{buy_price:,.1f}",
                    "目標利確価格(+10%)": f"{target_sell:,.1f}",
                    "損切りライン(-10%)": f"{stop_loss:,.1f}",
                    "含み損益": f"{profit_value:,.1f}",
                    "損益率(%)": round(profit_rate, 2),
                    "メモ": row['メモ']
                })
            except Exception:
                continue
                
        st.dataframe(pd.DataFrame(status_data), use_container_width=True)
        
        if st.button("ポートフォリオを全件リセット", type="primary"):
            st.session_state.portfolio_df = pd.DataFrame(columns=["Ticker", "買値", "株数", "メモ"])
            st.session_state.portfolio_df.to_csv(PORTFOLIO_FILE, index=False)
            st.success("リセットしました。")

# ------------------------------------------
# TAB 4: マルチタイムフレーム分析
# ------------------------------------------
with tab4:
    st.header("📈 マルチタイムフレーム（複数時間軸）分析")
    if test_options:
        mtf_ticker = st.selectbox("チャートを表示する銘柄を選択", test_options, key="mtf")
        if st.button("チャートを描画"):
            t_mtf = mtf_ticker.split("(")[-1].replace(")", "")
            stock = yf.Ticker(t_mtf)
            df_daily = stock.history(period="6mo", interval="1d")
            df_weekly = stock.history(period="2y", interval="1wk")
            
            fig = make_subplots(rows=1, cols=2, subplot_titles=(f"日足（短期のエントリー用） - {t_mtf}", f"週足（長期のトレンド確認用） - {t_mtf}"))
            fig.add_trace(go.Candlestick(x=df_daily.index, open=df_daily['Open'], high=df_daily['High'], low=df_daily['Low'], close=df_daily['Close'], name="日足"), row=1, col=1)
            fig.add_trace(go.Candlestick(x=df_weekly.index, open=df_weekly['Open'], high=df_weekly['High'], low=df_weekly['Low'], close=df_weekly['Close'], name="週足"), row=1, col=2)
            fig.update_layout(height=500, xaxis_rangeslider_visible=False, xaxis2_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)

# ------------------------------------------
# TAB 5: ミニ株・資金配分シミュレーション
# ------------------------------------------
with tab5:
    st.header("💰 ミニ株・分散投資シミュレーター (日本円計算)")
    st.markdown("全体予算(円)を入力してください。**※米国株を選択した場合は、自動で最新の為替レートで日本円に換算して予算から引かれます。**")
    st.caption(f"現在の適用為替レート: 1ドル = 約 {usd_jpy_rate:.2f} 円")
    
    total_budget = st.number_input("投資予算を入力 (日本円)", min_value=10000, value=2000000, step=100000)
    
    if test_options:
        selected_for_sim = st.multiselect("分散投資したい銘柄を選択", test_options, default=test_options[:2] if len(test_options)>1 else test_options)
        
        sim_data = []
        used_budget_jpy = 0
        for sel in selected_for_sim:
            t_sim = sel.split("(")[-1].replace(")", "")
            t_data = next((r for r in market_data if r['Ticker'] == t_sim), None)
            if t_data:
                price = t_data['現在値']
                currency = t_data['通貨']
                shares = st.number_input(f"{sel} の購入株数", min_value=0, value=10, key=f"sim_{t_sim}")
                
                cost_local = price * shares
                cost_jpy = cost_local * usd_jpy_rate if currency == "USD" else cost_local
                used_budget_jpy += cost_jpy
                
                sim_data.append({
                    "銘柄": sel, 
                    "1株価格": f"{price:,.2f} {currency}", 
                    "株数": shares, 
                    "必要資金(円換算)": f"¥{round(cost_jpy):,}"
                })
        
        if sim_data:
            st.dataframe(pd.DataFrame(sim_data), use_container_width=True)
            
            remaining = total_budget - used_budget_jpy
            col1, col2 = st.columns(2)
            col1.metric("使用資金(円)", f"¥{used_budget_jpy:,.0f}")
            
            if remaining >= 0:
                col2.metric("予算残高(円)", f"¥{remaining:,.0f}")
                st.success(f"予算内に収まっています！残り {remaining:,.0f} 円は現金余力として待機できます。")
            else:
                col2.metric("予算オーバー(円)", f"¥{remaining:,.0f}", delta_color="inverse")
                st.error("予算をオーバーしています。購入株数を調整してください。")