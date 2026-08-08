import streamlit as st
import yfinance as yf
import pandas as pd
import ta
import os
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import concurrent.futures
import time
import random
import requests

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
    "東京エレクトロン": "8035.T", "LIXIL": "5938.T" 
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
@st.cache_data(ttl=86400) # 1日1回だけ再取得
def get_nikkei225_tickers():
    """Wikipediaから確実な225銘柄リストを動的に取得する"""
    try:
        url = "https://ja.wikipedia.org/wiki/%E6%97%A5%E7%B5%8C%E5%B9%B3%E5%9D%87%E6%A0%AA%E4%BE%A1"
        tables = pd.read_html(url)
        for df in tables:
            if 'コード' in df.columns and '銘柄名' in df.columns:
                tickers = {}
                for _, row in df.iterrows():
                    code = str(int(row['コード'])) + ".T"
                    name = str(row['銘柄名'])
                    tickers[name] = code
                if len(tickers) >= 200: # 正常に取得できた場合
                    return tickers
    except Exception:
        pass
    
    # 万が一Wikipediaの構造が変わって取得失敗した場合のフォールバック（緊急用リスト）
    return MAJOR_STOCKS_JP

@st.cache_data(ttl=3600)
def get_exchange_rate():
    try:
        return yf.Ticker("JPY=X").history(period="1d")['Close'].iloc[-1]
    except Exception:
        return 150.0

def analyze_single_stock(name, ticker):
    """1銘柄のデータを安全に取得・解析する"""
    # 💡 Streamlit Cloudでのアクセス遮断を防ぐため、ランダムなウェイトを挟む
    time.sleep(random.uniform(0.2, 0.6))
    
    try:
        # 💡 ボット検知を回避するためブラウザからのアクセスを装う
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })
        
        stock = yf.Ticker(ticker, session=session)
        df = stock.history(period="2y")
        
        if df.empty or len(df) < 15:
            return None
            
        df['RSI'] = ta.momentum.RSIIndicator(close=df['Close'], window=14).rsi()
        macd = ta.trend.MACD(close=df['Close'])
        df['MACD_Diff'] = macd.macd_diff()
        
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        rsi_val = latest['RSI']
        
        if pd.isna(rsi_val):
            return None
        
        macd_gc = (prev['MACD_Diff'] < 0) and (latest['MACD_Diff'] > 0)
        
        if len(df) >= 200:
            df['SMA200'] = ta.trend.SMAIndicator(close=df['Close'], window=200).sma_indicator()
            long_trend = "上昇中 ☀️" if latest['Close'] > latest['SMA200'].iloc[-1] else "下落中 ☔"
        else:
            long_trend = "データ蓄積中 ➖"
            
        currency = "JPY" if ticker.endswith(".T") else "USD"
        
        sector = "不明"
        try:
            sector = stock.info.get('sector', '不明')
        except Exception:
            pass
        
        return {
            "Ticker": ticker,
            "銘柄名": name,
            "セクター": sector,
            "通貨": currency,
            "現在値": round(float(latest['Close']), 2),
            "1株購入目安": f"{round(float(latest['Close']), 2):,} {currency}",
            "長期トレンド": long_trend,
            "RSI(過熱感)": round(float(rsi_val), 1),
            "MACDサイン": "🟢 GC発生!" if macd_gc else ("反発中" if latest['MACD_Diff'] > 0 else "下落トレンド")
        }
    except Exception:
        return None

def fetch_and_analyze(tickers_dict):
    data = []
    total = len(tickers_dict)
    if total == 0:
        return data
    
    progress_text = st.empty()
    progress_bar = st.progress(0)
    
    # 💡 並列数を10→3に減らし、サーバー負荷を抑えて確実な取得を目指す
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
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
# セッションステートの初期化
# ==========================================
if "portfolio_df" not in st.session_state:
    if os.path.exists(PORTFOLIO_FILE):
        st.session_state.portfolio_df = pd.read_csv(PORTFOLIO_FILE)
    else:
        st.session_state.portfolio_df = pd.DataFrame(columns=["Ticker", "買値", "株数", "メモ"])

# ==========================================
# ⚙️ サイドバー
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

need_fetch = ("market_data" not in st.session_state) or (not st.session_state.market_data) or submitted

if need_fetch:
    target_tickers = {}
    if market_choice == "🇯🇵 日本株":
        if mode_choice == "主要銘柄":
            target_tickers = MAJOR_STOCKS_JP.copy()
        else:
            with st.spinner("Wikipediaから日経225の最新銘柄リストを取得中..."):
                target_tickers = get_nikkei225_tickers().copy()
    else:
        target_tickers = MAJOR_STOCKS_US.copy()
        
    if custom_tickers_input:
        for t_raw in custom_tickers_input.split(","):
            t = t_raw.strip().upper()
            if t:
                target_tickers[f"追加銘柄({t})"] = t
            
    with st.spinner("データをスキャン・解析しています...（API制限回避のため少し時間がかかります）"):
        st.session_state.market_data = fetch_and_analyze(target_tickers)
        st.session_state.market_choice_name = market_choice

market_data = st.session_state.get("market_data", [])
test_options = sorted([f"{row['銘柄名']} ({row['Ticker']})" for row in market_data]) if market_data else []
usd_jpy_rate = get_exchange_rate()

st.sidebar.markdown("---")
with st.sidebar.expander("📖 投資用語集 (初心者向け)", expanded=False):
    st.markdown("""
    - **RSI**: 「買われすぎ」「売られすぎ」を0〜100で表す温度計。**30以下**なら売られすぎ。
    - **MACD**: トレンドの「方向」と「勢い」を見る指標。
    - **ゴールデンクロス (GC)**: 短期線が長期線を下から上に突き抜けること。下落トレンドが終わり、上昇トレンドに入る初動の強力な買いサイン。
    - **SMA200**: 200日移動平均線。これが上向きなら「長期的に上昇トレンド（☀️）」と判断。
    """)

# ==========================================
# UI タブ構成
# ==========================================
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🏆 買い時ランキング", "💼 ポートフォリオ", 
    "📈 マルチタイムフレーム", "💰 資金配分", "🏢 セクター"
])

# ------------------------------------------
# TAB 1: 買い時ランキング
# ------------------------------------------
with tab1:
    st.header(f"🏆 {st.session_state.get('market_choice_name', '日本株')} 買い時ランキング")
    if market_data:
        res_df = pd.DataFrame(market_data).sort_values('RSI(過熱感)', ascending=True)
        display_df = res_df.reset_index(drop=True)
        display_df.index = display_df.index + 1
        
        search_term = st.text_input("🔍 ランキング内を絞り込み検索 (銘柄名やTickerを入力)", placeholder="例: トヨタ", value="")
        if search_term:
            display_df = display_df[
                display_df['銘柄名'].str.contains(search_term, case=False, na=False) | 
                display_df['Ticker'].str.contains(search_term, case=False, na=False)
            ]
            
        st.dataframe(display_df, use_container_width=True)
    else:
        st.warning("表示できるデータがありません。サイドバーから分析を実行してください。")

# ------------------------------------------
# TAB 2: ポートフォリオ・売り時判定
# ------------------------------------------
with tab2:
    st.header("💼 保有銘柄の監視・売り時判定")
    
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
                placeholder="ここをクリックして文字入力で検索（例: LIXIL, 5938, TSM）"
            )
            col1, col2, col3 = st.columns(3)
            p_price = col1.number_input("平均買値 (1株あたり)", min_value=0.0, format="%.2f", step=10.0)
            p_shares = col2.number_input("保有株数", min_value=1)
            p_memo = col3.text_input("メモ", value="")
            
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

        for idx, row in st.session_state.portfolio_df.iterrows():
            t = row['Ticker']
            try:
                stock = yf.Ticker(t)
                hist = stock.history(period="1mo")
                if hist.empty or len(hist) < 15: 
                    continue
                
                latest_price = hist['Close'].iloc[-1]
                buy_price = row['買値']
                
                target_sell = buy_price * 1.10
                stop_loss = buy_price * 0.90
                
                profit_rate = ((latest_price - buy_price) / buy_price) * 100 if buy_price > 0 else 0
                profit_value = (latest_price - buy_price) * row['株数']
                total_profit += profit_value
                if profit_rate > 0:
                    win_count += 1
                
                rsi = ta.momentum.RSIIndicator(hist['Close'], window=14).rsi().iloc[-1]
                macd = ta.trend.MACD(hist['Close'])
                macd_diff = macd.macd_diff().iloc[-1]
                
                sell_signal = "ホールド 🛡️"
                if buy_price > 0:
                    if latest_price >= target_sell:
                        sell_signal = "🎯 目標達成 (+10%超・利確推奨)"
                    elif latest_price <= stop_loss:
                        sell_signal = "💀 損切りライン到達 (-10%)"
                        warning_count += 1
                    elif rsi >= 70:
                        sell_signal = "⚠️ RSI過熱 (そろそろ利確警戒)"
                        warning_count += 1
                    elif macd_diff < 0 and profit_rate > 0:
                        sell_signal = "📉 トレンド下落 (利益確保の目安)"

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
                    "目標利確価格(+10%)": f"{target_sell:,.1f}",
                    "損切りライン(-10%)": f"{stop_loss:,.1f}",
                    "含み損益": f"{profit_value:,.1f}",
                    "損益率(%)": round(profit_rate, 2),
                    "メモ": row['メモ']
                })
            except Exception:
                continue
                
        if status_data:
            st.dataframe(pd.DataFrame(status_data), use_container_width=True)

            st.markdown("### 🧠 ポートフォリオ総合診断")
            col_a, col_b, col_c = st.columns(3)
            pf_len = len(status_data)
            win_rate = (win_count / pf_len) * 100 if pf_len > 0 else 0
            
            col_a.metric("トータル含み損益", f"¥{total_profit:,.0f}")
            col_b.metric("ポートフォリオ勝率", f"{win_rate:.1f}%", f"{win_count}勝 / {pf_len - win_count}敗")
            
            if warning_count > 0:
                col_c.error(f"⚠️ {warning_count}銘柄に警戒サインが出ています。損切りや利確を検討しましょう。")
            elif pf_len > 0 and total_profit > 0:
                col_c.success("🌟 非常に健全な状態です！このままトレンドに乗りましょう。")
            else:
                col_c.info("📊 経過観察中です。")

        if st.button("ポートフォリオを全件リセット", type="primary"):
            st.session_state.portfolio_df = pd.DataFrame(columns=["Ticker", "買値", "株数", "メモ"])
            st.session_state.portfolio_df.to_csv(PORTFOLIO_FILE, index=False)
            st.rerun()

# ------------------------------------------
# TAB 3: マルチタイムフレーム分析
# ------------------------------------------
with tab3:
    st.header("📈 マルチタイムフレーム（複数時間軸）分析")
    if test_options:
        mtf_ticker = st.selectbox(
            "チャートを表示・分析する銘柄を検索・選択", 
            test_options, 
            key="mtf", 
            index=0,
            placeholder="銘柄名（日本語）を入力して検索"
        )
        
        if mtf_ticker:
            t_mtf = mtf_ticker.split("(")[-1].replace(")", "")
            stock = yf.Ticker(t_mtf)
            df_daily = stock.history(period="6mo", interval="1d")
            df_weekly = stock.history(period="2y", interval="1wk")
            
            if not df_daily.empty and len(df_daily) >= 15:
                df_daily['RSI'] = ta.momentum.RSIIndicator(close=df_daily['Close'], window=14).rsi()
                macd = ta.trend.MACD(close=df_daily['Close'])
                df_daily['MACD_Diff'] = macd.macd_diff()
                
                latest = df_daily.iloc[-1]
                prev = df_daily.iloc[-2]
                
                fig = make_subplots(rows=2, cols=1, subplot_titles=(f"日足（短期のエントリー用） - {mtf_ticker}", f"週足（長期のトレンド確認用） - {mtf_ticker}"))
                fig.add_trace(go.Candlestick(x=df_daily.index, open=df_daily['Open'], high=df_daily['High'], low=df_daily['Low'], close=df_daily['Close'], name="日足"), row=1, col=1)
                fig.add_trace(go.Candlestick(x=df_weekly.index, open=df_weekly['Open'], high=df_weekly['High'], low=df_weekly['Low'], close=df_weekly['Close'], name="週足"), row=2, col=1)
                fig.update_layout(height=800, xaxis_rangeslider_visible=False, xaxis2_rangeslider_visible=False)
                st.plotly_chart(fig, use_container_width=True)

                st.markdown("### 🤖 銘柄テクニカル診断（今買い時か？）")
                
                rsi_val = latest['RSI']
                is_gc = (prev['MACD_Diff'] < 0) and (latest['MACD_Diff'] > 0)
                
                analysis_text = f"**【{mtf_ticker} の現状分析】**\n\n"
                
                if len(df_daily) >= 200:
                    df_daily['SMA200'] = ta.trend.SMAIndicator(close=df_daily['Close'], window=200).sma_indicator()
                    is_uptrend = latest['Close'] > df_daily['SMA200'].iloc[-1]
                    if is_uptrend:
                        analysis_text += "☀️ **長期トレンド:** 200日移動平均線を上回っており、長期的な上昇トレンドに乗っています。\n"
                    else:
                        analysis_text += "☔ **長期トレンド:** 200日移動平均線を下回っており、長期的には下落傾向（または調整中）です。\n"
                    
                if not pd.isna(rsi_val):
                    if rsi_val <= 35:
                        analysis_text += f"📉 **過熱感 (RSI: {rsi_val:.1f}):** 30に近く「売られすぎ」の水準です。反発を狙う絶好のチャンス（買い時）の可能性があります。\n"
                    elif rsi_val >= 70:
                        analysis_text += f"🔥 **過熱感 (RSI: {rsi_val:.1f}):** 70を超えており「買われすぎ」です。今からの新規購入は高値掴みのリスクがあるため見送りを推奨します。\n"
                    else:
                        analysis_text += f"⚖️ **過熱感 (RSI: {rsi_val:.1f}):** 中立な状態です。極端な割安感はありません。\n"
                    
                if is_gc:
                    analysis_text += "🟢 **MACD:** **ゴールデンクロスが発生しています！** 短期的な下落が終わり、上昇トレンドに転換する初動のサインが出ています。強気の買いシグナルです。\n"
                elif latest['MACD_Diff'] > 0:
                    analysis_text += "📈 **MACD:** 短期的には上昇の勢い（モメンタム）が強い状態を維持しています。\n"
                else:
                    analysis_text += "📉 **MACD:** 短期的には下落方向への圧力がかかっています。底を打つまで様子見が無難です。\n"

                st.info(analysis_text)
            else:
                st.warning("十分な価格データが取得できませんでした。")
    else:
        st.info("データが読み込まれていません。")

# ------------------------------------------
# TAB 4: ミニ株・資金配分シミュレーション
# ------------------------------------------
with tab4:
    st.header("💰 ミニ株・分散投資シミュレーター (日本円計算)")
    st.markdown("全体予算(円)を入力してください。")
    
    total_budget = st.number_input("投資予算を入力 (日本円)", min_value=10000, value=2000000, step=100000)
    
    if test_options:
        selected_for_sim = st.multiselect(
            "分散投資したい銘柄を検索・選択", 
            test_options, 
            default=test_options[:2] if len(test_options)>1 else test_options,
            placeholder="銘柄名（日本語）を入力して検索"
        )
        
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

# ------------------------------------------
# TAB 5: セクター（業種）分析
# ------------------------------------------
with tab5:
    st.header("🏢 セクター別 トレンド分析")
    if market_data:
        sec_df = pd.DataFrame(market_data)
        if 'セクター' in sec_df.columns:
            sector_group = sec_df.groupby('セクター')['RSI(過熱感)'].mean().reset_index()
            sector_group = sector_group.sort_values('RSI(過熱感)', ascending=True).reset_index(drop=True)
            sector_group.index = sector_group.index + 1
            st.dataframe(sector_group, use_container_width=True)
        else:
            st.warning("セクター情報が取得できませんでした。")