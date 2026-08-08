import streamlit as st
import yfinance as yf
import pandas as pd
import ta
import os
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="総合投資ダッシュボード", layout="wide")
st.title("🦅 グローバル・マルチ投資ダッシュボード")

# --- 定数・初期設定 ---
MAJOR_STOCKS = {
    "トヨタ自動車": "7203.T", "三菱UFJ": "8306.T", "三井住友FG": "8316.T",
    "NTT": "9432.T", "KDDI": "9433.T", "三菱商事": "8058.T",
    "伊藤忠商事": "8001.T", "三井物産": "8031.T", "武田薬品": "4502.T",
    "ソニーG": "6758.T", "日立製作所": "6501.T", "信越化学": "4063.T",
    "オリックス": "8591.T", "ホンダ": "7267.T", "JT": "2914.T",
    "Apple (米)": "AAPL", "Microsoft (米)": "MSFT", "NVIDIA (米)": "NVDA",
    "Tesla (米)": "TSLA", "Amazon (米)": "AMZN", "Alphabet (米)": "GOOGL",
    "Meta (米)": "META", "Coca-Cola (米)": "KO", "P&G (米)": "PG"
}

PORTFOLIO_FILE = "portfolio.csv"

# --- データ取得・解析関数 ---
@st.cache_data(ttl=3600)
def fetch_and_analyze(tickers):
    data = []
    progress_bar = st.progress(0, text="市場データをスキャン中...")
    total = len(tickers)
    
    for i, t in enumerate(tickers):
        progress_bar.progress((i + 1) / total, text=f"スキャン中... {i+1}/{total} ({t})")
        try:
            stock = yf.Ticker(t)
            df = stock.history(period="2y")
            if df.empty or len(df) < 200: continue
            
            info = stock.info
            
            # テクニカル指標の計算
            df['RSI'] = ta.momentum.RSIIndicator(close=df['Close'], window=14).rsi()
            df['SMA25'] = ta.trend.SMAIndicator(close=df['Close'], window=25).sma_indicator()
            df['SMA200'] = ta.trend.SMAIndicator(close=df['Close'], window=200).sma_indicator() # 長期トレンド用
            
            macd = ta.trend.MACD(close=df['Close'])
            df['MACD'] = macd.macd()
            df['MACD_Signal'] = macd.macd_signal()
            df['MACD_Diff'] = macd.macd_diff()
            
            latest = df.iloc[-1]
            prev = df.iloc[-2]
            rsi_val = latest['RSI']
            if pd.isna(rsi_val): continue
            
            # MACDゴールデンクロス判定
            macd_gc = (prev['MACD_Diff'] < 0) and (latest['MACD_Diff'] > 0)
            
            # 長期トレンド判定（200日移動平均線より上か下か）
            long_trend = "上昇中 ☀️" if latest['Close'] > latest['SMA200'] else "下落中 ☔"
            
            # 1株(ミニ株)あたりの価格（日本株は通常100株単位だが、ミニ株なら現在値がそのまま購入額になる）
            currency = info.get('currency', 'JPY')
            min_investment = latest['Close'] if currency == 'JPY' else latest['Close'] # 米国株は元々1株から
            
            data.append({
                "Ticker": t,
                "銘柄名": info.get('shortName', t),
                "セクター": info.get('sector', '不明'),
                "通貨": currency,
                "現在値": round(latest['Close'], 2),
                "ミニ株/1株購入目安": f"{round(min_investment, 2):,} {currency}",
                "長期トレンド": long_trend,
                "RSI(過熱感)": round(rsi_val, 1),
                "MACDサイン": "🟢 GC発生!" if macd_gc else ("反発中" if latest['MACD_Diff'] > 0 else "下落トレンド"),
                "PBR": round(info.get('priceToBook', 0), 2) if info.get('priceToBook') else None,
                "配当利回り(%)": round((info.get('dividendYield', 0) or 0) * 100, 2),
                "df": df
            })
        except Exception:
            continue
            
    progress_bar.empty()
    return data

# データロード
ticker_list = list(MAJOR_STOCKS.values())
if "market_data" not in st.session_state:
    st.session_state.market_data = fetch_and_analyze(ticker_list)
market_data = st.session_state.market_data

# ==========================================
# 🔔 リアルタイム・シグナルアラート機能
# ==========================================
strong_buys = [d['銘柄名'] for d in market_data if d['RSI(過熱感)'] < 35 and "GC発生" in d['MACDサイン']]
if strong_buys:
    st.toast(f"🚨 強い買いシグナル発生: {', '.join(strong_buys)}", icon="📈")

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
    st.header("日米 主要銘柄 買い時ランキング")
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
    st.header("セクター別 トレンド分析")
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
    
    if not os.path.exists(PORTFOLIO_FILE):
        pd.DataFrame(columns=["Ticker", "買値", "株数", "メモ"]).to_csv(PORTFOLIO_FILE, index=False)
    portfolio_df = pd.read_csv(PORTFOLIO_FILE)
    
    with st.expander("➕ 新しい銘柄を追加 (ミニ株対応)"):
        with st.form("add_portfolio"):
            col1, col2, col3, col4 = st.columns(4)
            p_ticker = col1.text_input("ティッカー (例: 7203.T)")
            p_price = col2.number_input("平均買値 (1株あたり)", min_value=0.0, format="%.2f")
            p_shares = col3.number_input("保有株数 (ミニ株は1から)", min_value=1)
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
                    "株数": row['株数'],
                    "現在評価額": round(total_value, 2),
                    "含み損益": round(profit_value, 2),
                    "損益率(%)": round(profit_rate, 2),
                    "現在のアクション": sell_signal
                })
            except:
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
    st.markdown("過去2年間で「RSIが30以下（売られすぎ）」になったタイミングで買い、20営業日後（約1ヶ月後・スイングトレード想定）に売った場合の勝率を検証します。")
    
    test_options = [f"{row['銘柄名']} ({row['Ticker']})" for _, row in pd.DataFrame(market_data).iterrows()]
    selected_test = st.selectbox("検証する銘柄を選択", test_options, key="backtest")
    
    if st.button("シミュレーション実行"):
        t = selected_test.split("(")[1].replace(")", "")
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
    mtf_ticker = st.selectbox("銘柄を選択", test_options, key="mtf")
    
    if st.button("チャートを描画"):
        t_mtf = mtf_ticker.split("(")[1].replace(")", "")
        stock = yf.Ticker(t_mtf)
        df_daily = stock.history(period="6mo", interval="1d")
        df_weekly = stock.history(period="2y", interval="1wk")
        
        fig = make_subplots(rows=1, cols=2, subplot_titles=("日足（短期のエントリーポイント用）", "週足（長期のトレンド確認用）"))
        
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
    
    ai_ticker = st.selectbox("分析する銘柄を選択", test_options, key="ai")
    t_ai = ai_ticker.split("(")[1].replace(")", "")
    target_df = next((r['df'] for r in market_data if r['Ticker'] == t_ai), None)
    
    st.subheader("📰 市場センチメント（感情）分析")
    st.markdown("直近の価格変動（ボラティリティとモメンタム）から、市場が強気か弱気かを推測します。")
    if target_df is not None:
        recent_momentum = target_df['Close'].pct_change().tail(5).sum() * 100
        sentiment = "強気 🐂" if recent_momentum > 0 else "弱気 🐻"
        st.metric(label="直近5日間の市場センチメント", value=sentiment, delta=f"{recent_momentum:.2f}%")

    st.subheader("🔍 AI類似チャートパターン検索")
    st.markdown("直近14日間のチャートの「形」と、過去2年間で最も形が似ている時期をAI（ピアソンの相関係数）で探し出します。")
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
        if best_match_score > 0.8:
            st.success("非常に高い一致率です！過去のこの時期の後に株価がどう動いたかを「マルチタイムフレーム」タブで確認してみてください。")

# ------------------------------------------
# TAB 7: ミニ株・資金配分シミュレーション (NEW)
# ------------------------------------------
with tab7:
    st.header("💰 ミニ株・分散投資シミュレーター")
    st.markdown("全体予算を入力し、各銘柄を「ミニ株（1株単位）」で購入した場合の資金配分を計算します。リスク分散の計画に役立ててください。")
    
    total_budget = st.number_input("投資予算を入力 (円)", min_value=100000, value=2000000, step=100000)
    
    st.write("▼購入したい銘柄の株数（1株から設定可能）を入力すると、予算残高が計算されます。")
    
    selected_for_sim = st.multiselect("分散投資したい銘柄を選択してください", test_options, default=[test_options[0], test_options[1]])
    
    sim_data = []
    used_budget = 0
    for sel in selected_for_sim:
        t_sim = sel.split("(")[1].replace(")", "")
        t_data = next((r for r in market_data if r['Ticker'] == t_sim), None)
        if t_data and t_data['通貨'] == 'JPY': # 日本株のみシミュレーション
            price = t_data['現在値']
            shares = st.number_input(f"{sel} の購入株数", min_value=0, value=10, key=f"sim_{t_sim}")
            cost = price * shares
            used_budget += cost
            sim_data.append({"銘柄": sel, "1株価格": price, "株数": shares, "必要資金(円)": round(cost)})
    
    if sim_data:
        st.dataframe(pd.DataFrame(sim_data), use_container_width=True)
        
        remaining = total_budget - used_budget
        col1, col2 = st.columns(2)
        col1.metric("使用資金", f"¥{used_budget:,.0f}")
        
        if remaining >= 0:
            col2.metric("予算残高", f"¥{remaining:,.0f}")
            st.success(f"予算内に収まっています！残り {remaining:,.0f} 円は別の銘柄への分散や、現金としてプールしておくことができます。")
        else:
            col2.metric("予算オーバー", f"¥{remaining:,.0f}", delta_color="inverse")
            st.error("予算をオーバーしています。株数を減らすか、別の銘柄を検討してください。")