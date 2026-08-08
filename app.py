import streamlit as st
import yfinance as yf
import pandas as pd
import ta
import os
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ------------------------------------------
# ページ設定
# ------------------------------------------
st.set_page_config(page_title="総合投資ダッシュボード", layout="wide", initial_sidebar_state="expanded")
st.title("🦅 グローバル・マルチ投資ダッシュボード")

# ------------------------------------------
# 定数・銘柄リスト
# ------------------------------------------
# 日本の主要銘柄
MAJOR_STOCKS_JP = {
    "トヨタ自動車": "7203.T", "三菱UFJ FG": "8306.T", "三井住友FG": "8316.T",
    "NTT": "9432.T", "KDDI": "9433.T", "三菱商事": "8058.T",
    "伊藤忠商事": "8001.T", "三井物産": "8031.T", "武田薬品工業": "4502.T",
    "ソニーグループ": "6758.T", "日立製作所": "6501.T", "信越化学工業": "4063.T",
    "オリックス": "8591.T", "ホンダ": "7267.T", "JT (日本たばこ産業)": "2914.T",
    "ファーストリテイリング": "9983.T", "ソフトバンクグループ": "9984.T", "東京エレクトロン": "8035.T"
}

# 米国の主要銘柄（TSMなど追加）
MAJOR_STOCKS_US = {
    "Apple": "AAPL", "Microsoft": "MSFT", "NVIDIA": "NVDA",
    "Tesla": "TSLA", "Amazon": "AMZN", "Alphabet (Google)": "GOOGL",
    "Meta (Facebook)": "META", "Coca-Cola": "KO", "Procter & Gamble": "PG",
    "TSMC (台湾セミコンダクター)": "TSM", "Netflix": "NFLX", "AMD": "AMD",
    "Intel": "INTC", "Johnson & Johnson": "JNJ", "Visa": "V"
}

PORTFOLIO_FILE = "portfolio.csv"

# ------------------------------------------
# 関数: 日経225リストの取得（Wikipediaから動的取得）
# ------------------------------------------
@st.cache_data(ttl=86400) # 1日キャッシュ
def get_nikkei225_tickers():
    try:
        # Wikipediaの英語ページから日経225の構成銘柄テーブルを取得
        tables = pd.read_html('https://en.wikipedia.org/wiki/Nikkei_225')
        for t in tables:
            if 'Company' in t.columns and 'Code' in t.columns:
                # { "Company Name": "XXXX.T" } の辞書を作成
                return {row['Company']: f"{row['Code']}.T" for _, row in t.iterrows()}
    except Exception:
        pass
    # 失敗した場合は主要銘柄を返す
    return MAJOR_STOCKS_JP

# ------------------------------------------
# 関数: データ取得・解析
# ------------------------------------------
@st.cache_data(ttl=3600) # 1時間キャッシュ
def fetch_and_analyze(tickers_dict):
    data = []
    total = len(tickers_dict)
    if total == 0: return data
    
    # 読み込みの進捗バー
    progress_bar = st.progress(0, text="市場データをスキャン中...")
    
    for i, (name, t) in enumerate(tickers_dict.items()):
        progress_bar.progress((i + 1) / total, text=f"スキャン中... {i+1}/{total} ({name})")
        try:
            stock = yf.Ticker(t)
            df = stock.history(period="2y")
            if df.empty or len(df) < 200: continue
            
            info = stock.info
            # 日本語名がyfinanceから取れれば上書き、なければ辞書の名前を使う
            display_name = info.get('shortName', name)
            
            # テクニカル指標の計算
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
            if pd.isna(rsi_val): continue
            
            # 買い時判定ロジック
            macd_gc = (prev['MACD_Diff'] < 0) and (latest['MACD_Diff'] > 0)
            long_trend = "上昇中 ☀️" if latest['Close'] > latest['SMA200'] else "下落中 ☔"
            
            currency = info.get('currency', 'JPY')
            min_investment = latest['Close']
            
            data.append({
                "Ticker": t,
                "銘柄名": display_name,
                "セクター": info.get('sector', '不明'),
                "通貨": currency,
                "現在値": round(latest['Close'], 2),
                "1株購入目安": f"{round(min_investment, 2):,} {currency}",
                "長期トレンド": long_trend,
                "RSI(過熱感)": round(rsi_val, 1),
                "MACDサイン": "🟢 GC発生!" if macd_gc else ("反発中" if latest['MACD_Diff'] > 0 else "下落トレンド"),
                "df": df
            })
        except Exception:
            continue
            
    progress_bar.empty()
    return data

# ==========================================
# ⚙️ サイドバー (メニュー)
# ==========================================
st.sidebar.header("⚙️ 検索・フィルター設定")

market_choice = st.sidebar.radio("🌐 対象市場を選択", ["🇯🇵 日本株", "🇺🇸 米国株"])

target_tickers = {}

if market_choice == "🇯🇵 日本株":
    mode_choice = st.sidebar.radio("📊 銘柄モード (日本株)", ["主要銘柄", "日経225全銘柄"])
    if mode_choice == "主要銘柄":
        target_tickers = MAJOR_STOCKS_JP.copy()
    else:
        st.sidebar.info("※日経225全銘柄は初回読み込みに1〜2分かかります（以降は高速化されます）")
        target_tickers = get_nikkei225_tickers().copy()
else:
    st.sidebar.write("📊 銘柄モード: 主要米国株 (TSM等含む)")
    target_tickers = MAJOR_STOCKS_US.copy()

st.sidebar.markdown("---")
st.sidebar.write("➕ **個別銘柄の追加検索**")
st.sidebar.write("※リストにない銘柄を調べたい場合、ティッカーをカンマ区切りで入力してください。（例: `8267.T`, `PLTR`）")
custom_tickers_input = st.sidebar.text_input("追加ティッカー名:")

if custom_tickers_input:
    for t_raw in custom_tickers_input.split(","):
        t = t_raw.strip().upper()
        if t:
            # 英語/日本語名が不明な場合はティッカー名をキーにする
            target_tickers[f"追加銘柄({t})"] = t

# データロード実行
market_data = fetch_and_analyze(target_tickers)

# セレクトボックス用の日本語リスト作成 (例: "トヨタ自動車 (7203.T)")
test_options = [f"{row['銘柄名']} ({row['Ticker']})" for row in market_data]

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
    st.header(f"{market_choice} 買い時（売られすぎ）ランキング")
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

# ------------------------------------------
# TAB 2: セクター（業種）分析
# ------------------------------------------
with tab2:
    st.header(f"{market_choice} セクター別 トレンド分析")
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
    st.header("保有銘柄の監視・売り時判定")
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
                elif profit_rate < -10: sell_signal = "💀 損切りライン到達 (-10%)"

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
    st.markdown("過去2年間で「RSIが30以下（売られすぎ）」になったタイミングで買い、約1ヶ月後に売った場合の勝率を検証します。")
    st.info("💡 **Tips:** セレクトボックス内をクリックし、キーボードで企業名を入力するとリアルタイムで検索（絞り込み）ができます。")
    
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
    st.markdown("""
    **💡 初心者向けのポイント:**
    長期（週足チャート）が右肩上がりであることを確認してから、短期（日足チャート）で一時的に下がったところを買うのが安全な投資の王道です。
    """)
    st.info("💡 **Tips:** 枠内をクリックして企業名をタイピング入力することで絞り込み検索ができます。")
    
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
    st.header("🤖 AI分析（完全無料版）")
    st.markdown("外部の有料AIに頼らず、株価の統計データから市場の心理と過去のパターンを導き出します。")
    
    if test_options:
        ai_ticker = st.selectbox("分析する銘柄を選択", test_options, key="ai")
        t_ai = ai_ticker.split("(")[-1].replace(")", "")
        target_df = next((r['df'] for r in market_data if r['Ticker'] == t_ai), None)
        
        st.subheader("📰 市場センチメント（感情）分析")
        st.markdown("直近の価格変動（ボラティリティとモメンタム）から、市場が強気か弱気かを推測します。")
        if target_df is not None:
            recent_momentum = target_df['Close'].pct_change().tail(5).sum() * 100
            sentiment = "強気 🐂" if recent_momentum > 0 else "弱気 🐻"
            st.metric(label="直近5日間の市場センチメント", value=sentiment, delta=f"{recent_momentum:.2f}%")

        st.subheader("🔍 AI類似チャートパターン検索")
        st.markdown("直近14日間のチャートの「形」と、過去2年間で最も形が似ている時期をAIで探し出します。")
        if target_df is not None and len(target_df) > 50:
            recent_pattern = target_df['Close'].tail(14).values
            recent_norm = (recent_pattern - np.mean(recent_pattern)) / (np.std(recent_pattern) + 1e-10)
            
            best_match_score = -1
            best_match_idx = 0
            
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
    st.header("💰 ミニ株・分散投資シミュレーター")
    st.markdown("全体予算を入力し、各銘柄を購入した場合の資金配分を計算します。")
    
    total_budget = st.number_input("投資予算を入力 (円・ドル)", min_value=10000, value=2000000, step=100000)
    
    if test_options:
        selected_for_sim = st.multiselect("分散投資したい銘柄を選択してください", test_options, default=test_options[:2] if len(test_options)>1 else test_options)
        
        sim_data = []
        used_budget = 0
        for sel in selected_for_sim:
            t_sim = sel.split("(")[-1].replace(")", "")
            t_data = next((r for r in market_data if r['Ticker'] == t_sim), None)
            if t_data:
                price = t_data['現在値']
                shares = st.number_input(f"{sel} の購入株数", min_value=0, value=10, key=f"sim_{t_sim}")
                cost = price * shares
                used_budget += cost
                sim_data.append({"銘柄": sel, "通貨": t_data['通貨'], "1株価格": price, "株数": shares, "必要資金": round(cost, 2)})
        
        if sim_data:
            st.dataframe(pd.DataFrame(sim_data), use_container_width=True)
            
            remaining = total_budget - used_budget
            col1, col2 = st.columns(2)
            col1.metric("使用資金", f"{used_budget:,.2f}")
            
            if remaining >= 0:
                col2.metric("予算残高", f"{remaining:,.2f}")
                st.success("予算内に収まっています！")
            else:
                col2.metric("予算オーバー", f"{remaining:,.2f}", delta_color="inverse")
                st.error("予算をオーバーしています。株数を調整してください。")