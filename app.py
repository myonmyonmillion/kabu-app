import streamlit as st
import yfinance as yf
import pandas as pd
import ta
import os
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import urllib.request
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
@st.cache_data(ttl=86400)
def get_nikkei225_tickers():
    """Wikipediaから日経225の銘柄コードを取得する"""
    try:
        url = "https://ja.wikipedia.org/wiki/%E6%97%A5%E7%B5%8C%E5%B9%B3%E5%9D%87%E6%A0%AA%E4%BE%A1"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        with urllib.request.urlopen(req) as response:
            html = response.read()
        tables = pd.read_html(html)
        for t in tables:
            if 'コード' in t.columns and '銘柄名' in t.columns:
                return {str(row['銘柄名']): f"{row['コード']}.T" for _, row in t.iterrows()}
    except Exception:
        pass
    return MAJOR_STOCKS_JP

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
        df['SMA25'] = ta.trend.SMAIndicator(close=df['Close'], window=25).sma_indicator()
        df['SMA200'] = ta.trend.SMAIndicator(close=df['Close'], window=200).sma_indicator()
        
        macd = ta.trend.MACD(close=df['Close'])
        df['MACD'] = macd.macd()
        df['MACD_Signal'] = macd.macd_signal()
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
            "MACDサイン": "🟢 GC発生!" if macd_gc else ("反発中" if latest['MACD_Diff'] > 0 else "下落トレンド"),
            "df": df
        }
    except Exception:
        return None

def fetch_and_analyze(tickers_dict):
    """複数銘柄をマルチスレッドで高速取得し、プログレスバーで進捗表示"""
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
    
    # 決定ボタン
    submitted = st.form_submit_button("🚀 この条件で分析を実行する")

# セッションステートを使って選択状態を保持
if "market_data" not in st.session_state or submitted:
    target_tickers = {}
    if market_choice == "🇯🇵 日本株":
        if mode_choice == "主要銘柄":
            target_tickers = MAJOR_STOCKS_JP.copy()
        else:
            with st.spinner("日経225の銘柄リストを取得中..."):
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
    - **ティッカー**: 銘柄を識別する記号（例：トヨタは 7203.T）。米国株はアルファベットのみ。
    - **RSI (相対力指数)**: 「買われすぎ」「売られすぎ」を0〜100で表す温度計。**30以下**なら売られすぎのバーゲン状態。
    - **MACD (マックディー)**: トレンドの「方向」と「勢い」を見る指標。
    - **ゴールデンクロス (GC)**: MACDなどの短期線が長期線を下から上に突き抜けること。上昇への転換（買いサイン）。
    - **SMA200 (200日移動平均線)**: 過去200日間の平均価格。これが上向きなら「長期的に上昇トレンド（☀️）」と判断。
    - **押し目買い**: 長期的に上昇している株が、一時的にカクッと下がったタイミングを狙って買うローリスクな手法。
    - **指値（さしね）注文**: 「〇〇円まで下がったら買う」と事前に希望価格を指定する注文方法。仕事中の売買に必須。
    """)

# ==========================================
# 🔔 リアルタイム・シグナルアラート
# ==========================================
strong_buys = [d['銘柄名'] for d in market_data if d['RSI(過熱感)'] < 35 and "GC発生" in d['MACDサイン']]
if strong_buys:
    st.toast(f"🚨 現在のリスト内で強い買いシグナル発生: {', '.join(strong_buys)}", icon="📈")

# ==========================================
# UI タブ構成
# ==========================================
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "🏆 買い時ランキング", "🏢 セクター", "💼 ポートフォリオ", 
    "🧪 バックテスト", "📈 マルチタイムフレーム", "🤖 AIパターン・感情分析", "💰 ミニ株・資金配分"
])

# ------------------------------------------
# TAB 1: 買い時ランキング
# ------------------------------------------
with tab1:
    st.header(f"🏆 {st.session_state.get('market_choice_name', '日本株')} 買い時（売られすぎ）ランキング")
    st.markdown("""
    **💡 初心者向けのポイント:** 
    まずは**「RSI(過熱感)」が30に近い銘柄**を探しましょう。売られすぎのバーゲン状態です。
    長期保有を前提とするなら、**「長期トレンド」が上昇中（☀️）**の銘柄の押し目（一時的な下落）を狙うのがローリスクです。
    """)
    if market_data:
        res_df = pd.DataFrame(market_data).sort_values('RSI(過熱感)', ascending=True)
        display_df = res_df.drop(columns=['df']).reset_index(drop=True)
        display_df.index = display_df.index + 1
        st.dataframe(display_df, use_container_width=True)
    else:
        st.warning("表示できるデータがありません。サイドバーの「分析を実行する」ボタンを押してください。")

# ------------------------------------------
# TAB 2: セクター（業種）分析
# ------------------------------------------
with tab2:
    st.header(f"🏢 セクター別 トレンド分析")
    st.markdown("**💡 使い方:** 業界全体が沈んでいるセクターは、優良銘柄も一緒に売られている大チャンスです。")
    if market_data:
        sec_df = pd.DataFrame(market_data)
        sector_group = sec_df.groupby('セクター')['RSI(過熱感)'].mean().reset_index()
        sector_group = sector_group.sort_values('RSI(過熱感)', ascending=True).reset_index(drop=True)
        sector_group.index = sector_group.index + 1
        st.dataframe(sector_group, use_container_width=True)

# ------------------------------------------
# TAB 3: ポートフォリオ・監視
# ------------------------------------------
with tab3:
    st.header("💼 保有銘柄の監視・売り時判定")
    st.markdown("※日米両方の銘柄を一括で管理できます。")
    
    if not os.path.exists(PORTFOLIO_FILE):
        pd.DataFrame(columns=["Ticker", "買値", "株数", "メモ"]).to_csv(PORTFOLIO_FILE, index=False)
    portfolio_df = pd.read_csv(PORTFOLIO_FILE)
    
    with st.expander("➕ 新しい銘柄を追加 (1株から対応)"):
        with st.form("add_portfolio"):
            col1, col2, col3, col4 = st.columns(4)
            p_ticker = col1.text_input("ティッカー (例: 7203.T, TSM)")
            p_price = col2.number_input("平均買値 (1株あたり)", min_value=0.0, format="%.2f")
            p_shares = col3.number_input("保有株数", min_value=1)
            p_memo = col4.text_input("メモ")
            if st.form_submit_button("追加"):
                new_row = pd.DataFrame([{"Ticker": p_ticker, "買値": p_price, "株数": p_shares, "メモ": p_memo}])
                portfolio_df = pd.concat([portfolio_df, new_row], ignore_index=True)
                portfolio_df.to_csv(PORTFOLIO_FILE, index=False)
                st.success("追加しました！画面を更新してください。")
                st.rerun()

    if not portfolio_df.empty:
        status_data = []
        for _, row in portfolio_df.iterrows():
            t = row['Ticker']
            try:
                stock = yf.Ticker(t)
                hist = stock.history(period="1mo")
                if hist.empty: continue
                
                latest_price = hist['Close'].iloc[-1]
                buy_price = row['買値']
                profit_rate = ((latest_price - buy_price) / buy_price) * 100
                total_value = latest_price * row['株数']
                profit_value = (latest_price - buy_price) * row['株数']
                
                rsi = ta.momentum.RSIIndicator(hist['Close'], window=14).rsi().iloc[-1]
                macd = ta.trend.MACD(hist['Close'])
                macd_diff = macd.macd_diff().iloc[-1]
                
                sell_signal = "ホールド 🛡️"
                if rsi >= 70: sell_signal = "⚠️ 利確警戒 (RSI過熱)"
                elif macd_diff < 0 and profit_rate > 0: sell_signal = "📉 利益確定目安 (MACD下落)"
                elif profit_rate < -10: sell_signal = "💀 損切り (-10%)"

                status_data.append({
                    "Ticker": t,
                    "銘柄名": stock.info.get('shortName', t),
                    "株数": row['株数'],
                    "現在値": round(latest_price, 2),
                    "含み損益": round(profit_value, 2),
                    "損益率(%)": round(profit_rate, 2),
                    "現在のアクション": sell_signal
                })
            except Exception:
                continue
        st.dataframe(pd.DataFrame(status_data), use_container_width=True)
        if st.button("ポートフォリオをリセット"):
            pd.DataFrame(columns=["Ticker", "買値", "株数", "メモ"]).to_csv(PORTFOLIO_FILE, index=False)
            st.rerun()

# ------------------------------------------
# TAB 4: バックテストシミュレーション
# ------------------------------------------
with tab4:
    st.header("🧪 買い時ロジックのバックテスト")
    st.info("💡 **Tips:** プルダウン内をクリックし、キーボードで企業名を入力すると絞り込み検索ができます。")
    
    if test_options:
        selected_test = st.selectbox("検証する銘柄を選択", test_options, key="backtest")
        if st.button("シミュレーション実行"):
            t = selected_test.split("(")[-1].replace(")", "")
            target_data = next((r for r in market_data if r['Ticker'] == t), None)
            if target_data is not None:
                df = target_data['df']
                buy_signals = df[df['RSI'] <= 30]
                wins, losses = 0, 0
                for date, row in buy_signals.iterrows():
                    idx = df.index.get_loc(date)
                    if idx + 20 < len(df):
                        return_pct = ((df.iloc[idx + 20]['Close'] - df.iloc[idx]['Close']) / df.iloc[idx]['Close']) * 100
                        if return_pct > 0: wins += 1
                        else: losses += 1
                
                if wins + losses > 0:
                    win_rate = (wins / (wins + losses)) * 100
                    st.subheader(f"シミュレーション結果: 勝率 {win_rate:.1f}% ({wins}勝 {losses}敗)")
                    fig = go.Figure(data=[go.Pie(labels=['勝ち', '負け'], values=[wins, losses], hole=.3, marker_colors=['#00CC96', '#EF553B'])])
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("過去2年間で極端な下落タイミングがありませんでした。（安定している優良株の可能性があります）")

# ------------------------------------------
# TAB 5: マルチタイムフレーム分析
# ------------------------------------------
with tab5:
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
# TAB 6: AIセンチメント & パターンマッチ
# ------------------------------------------
with tab6:
    st.header("🤖 AI分析（パターンマッチング）")
    if test_options:
        ai_ticker = st.selectbox("分析する銘柄を選択", test_options, key="ai")
        t_ai = ai_ticker.split("(")[-1].replace(")", "")
        target_df = next((r['df'] for r in market_data if r['Ticker'] == t_ai), None)
        
        if target_df is not None and len(target_df) > 50:
            recent_pattern = target_df['Close'].tail(14).values
            recent_norm = (recent_pattern - np.mean(recent_pattern)) / (np.std(recent_pattern) + 1e-10)
            
            best_match_score, best_match_idx = -1, 0
            for i in range(len(target_df) - 28): 
                historical_pattern = target_df['Close'].iloc[i:i+14].values
                if np.std(historical_pattern) == 0: continue
                hist_norm = (historical_pattern - np.mean(historical_pattern)) / np.std(historical_pattern)
                
                correlation = np.corrcoef(recent_norm, hist_norm)[0, 1]
                if correlation > best_match_score:
                    best_match_score = correlation
                    best_match_idx = i
                    
            match_date = target_df.index[best_match_idx].strftime('%Y-%m-%d')
            st.info(f"💡 **AI分析結果**: 直近の値動きは、過去 **{match_date}** 頃のチャート形状と **{best_match_score*100:.1f}%** 似ています。")

# ------------------------------------------
# TAB 7: ミニ株・資金配分シミュレーション
# ------------------------------------------
with tab7:
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