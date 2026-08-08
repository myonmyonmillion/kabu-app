import streamlit as st
import yfinance as yf
import pandas as pd
import ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os

st.set_page_config(page_title="総合投資ダッシュボード", layout="wide")
st.title("🦅 グローバル・マルチ投資ダッシュボード")

# --- 定数・初期設定 ---
# 日米の主要銘柄をデフォルト設定（選択不要で自動スキャン）
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
            df = stock.history(period="2y") # バックテスト用に長めに取得
            if df.empty or len(df) < 50: continue
            
            info = stock.info
            
            # テクニカル指標の計算
            df['RSI'] = ta.momentum.RSIIndicator(close=df['Close'], window=14).rsi()
            df['SMA25'] = ta.trend.SMAIndicator(close=df['Close'], window=25).sma_indicator()
            
            # MACDの計算
            macd = ta.trend.MACD(close=df['Close'])
            df['MACD'] = macd.macd()
            df['MACD_Signal'] = macd.macd_signal()
            df['MACD_Diff'] = macd.macd_diff() # ヒストグラム（これがプラスになればGC）
            
            latest = df.iloc[-1]
            prev = df.iloc[-2]
            
            rsi_val = latest['RSI']
            if pd.isna(rsi_val): continue
            
            # MACDゴールデンクロス判定（前日マイナス、当日プラス）
            macd_gc = (prev['MACD_Diff'] < 0) and (latest['MACD_Diff'] > 0)
            
            data.append({
                "Ticker": t,
                "銘柄名": info.get('shortName', t),
                "セクター": info.get('sector', '不明'),
                "通貨": info.get('currency', 'JPY'),
                "現在値": round(latest['Close'], 2),
                "RSI": round(rsi_val, 1),
                "MACDサイン": "🟢 GC発生!" if macd_gc else ("反発中" if latest['MACD_Diff'] > 0 else "下落トレンド"),
                "PBR": round(info.get('priceToBook', 0), 2) if info.get('priceToBook') else None,
                "配当利回り(%)": round((info.get('dividendYield', 0) or 0) * 100, 2),
                "df": df
            })
        except Exception:
            continue
            
    progress_bar.empty()
    return data

# データ取得の実行
ticker_list = list(MAJOR_STOCKS.values())
if "market_data" not in st.session_state:
    st.session_state.market_data = fetch_and_analyze(ticker_list)

market_data = st.session_state.market_data

# --- UI タブ構成 ---
tab1, tab2, tab3, tab4 = st.tabs(["🏆 買い時ランキング", "🏢 セクター分析", "💼 ポートフォリオ・監視", "🧪 勝率バックテスト"])

# ==========================================
# TAB 1: ランキング
# ==========================================
with tab1:
    st.header("日米 主要銘柄 売られすぎランキング")
    if market_data:
        res_df = pd.DataFrame(market_data).sort_values('RSI', ascending=True)
        display_df = res_df.drop(columns=['df']).head(15).reset_index(drop=True)
        display_df.index = display_df.index + 1
        st.dataframe(display_df, use_container_width=True)

# ==========================================
# TAB 2: セクター（業種）分析
# ==========================================
with tab2:
    st.header("セクター別 トレンド分析")
    st.write("各セクターの平均RSIです。35に近いセクターは業界全体が不当に売られているチャンスの可能性があります。")
    if market_data:
        sec_df = pd.DataFrame(market_data)
        sector_group = sec_df.groupby('セクター')['RSI'].mean().reset_index()
        sector_group = sector_group.sort_values('RSI', ascending=True).reset_index(drop=True)
        sector_group.index = sector_group.index + 1
        st.dataframe(sector_group.style.background_gradient(cmap='RdYlGn_r'), use_container_width=True)

# ==========================================
# TAB 3: ポートフォリオ・監視（売り時判定）
# ==========================================
with tab3:
    st.header("保有銘柄の監視・売り時判定")
    
    # CSVがなければ空のDataFrameを作成
    if not os.path.exists(PORTFOLIO_FILE):
        pd.DataFrame(columns=["Ticker", "買値", "株数", "メモ"]).to_csv(PORTFOLIO_FILE, index=False)
    
    portfolio_df = pd.read_csv(PORTFOLIO_FILE)
    
    # 登録フォーム
    with st.expander("➕ 新しい銘柄をポートフォリオに追加"):
        with st.form("add_portfolio"):
            col1, col2, col3, col4 = st.columns(4)
            p_ticker = col1.text_input("ティッカー (例: 7203.T, AAPL)")
            p_price = col2.number_input("平均買値", min_value=0.0, format="%.2f")
            p_shares = col3.number_input("保有株数", min_value=1)
            p_memo = col4.text_input("メモ (購入理由など)")
            if st.form_submit_button("追加"):
                new_row = pd.DataFrame([{"Ticker": p_ticker, "買値": p_price, "株数": p_shares, "メモ": p_memo}])
                portfolio_df = pd.concat([portfolio_df, new_row], ignore_index=True)
                portfolio_df.to_csv(PORTFOLIO_FILE, index=False)
                st.success(f"{p_ticker} を追加しました！再読み込みしてください。")
                st.rerun()

    # 保有銘柄の現在状況を判定
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
                
                # 売り時サインの簡易判定
                rsi = ta.momentum.RSIIndicator(hist['Close'], window=14).rsi().iloc[-1]
                macd = ta.trend.MACD(hist['Close'])
                macd_diff = macd.macd_diff().iloc[-1]
                
                sell_signal = "ホールド"
                if rsi >= 70:
                    sell_signal = "⚠️ 利確警戒 (RSI過熱)"
                elif macd_diff < 0 and profit_rate > 0:
                    sell_signal = "📉 利益確定目安 (MACD下落)"
                elif profit_rate < -10:
                    sell_signal = "💀 損切りライン到達 (-10%)"

                status_data.append({
                    "Ticker": t,
                    "メモ": row['メモ'],
                    "買値": buy_price,
                    "現在値": round(latest_price, 2),
                    "損益率(%)": round(profit_rate, 2),
                    "RSI": round(rsi, 1),
                    "現在のアクション": sell_signal
                })
            except:
                continue
        
        st.dataframe(pd.DataFrame(status_data), use_container_width=True)

        if st.button("ポートフォリオをリセット"):
            pd.DataFrame(columns=["Ticker", "買値", "株数", "メモ"]).to_csv(PORTFOLIO_FILE, index=False)
            st.rerun()

# ==========================================
# TAB 4: 勝率バックテスト
# ==========================================
with tab4:
    st.header("RSI 30以下買いのバックテスト (過去2年)")
    st.write("指定した銘柄が過去に「RSIが30以下」になったタイミングで買い、20営業日後（約1ヶ月後）に売った場合の勝率を検証します。")
    
    test_options = [f"{row['銘柄名']} ({row['Ticker']})" for _, row in pd.DataFrame(market_data).iterrows()]
    selected_test = st.selectbox("検証する銘柄を選択", test_options)
    
    if st.button("シミュレーション実行"):
        t = selected_test.split("(")[1].replace(")", "")
        target_data = next((r for r in market_data if r['Ticker'] == t), None)
        
        if target_data is not None:
            df = target_data['df']
            
            # バックテストロジック
            buy_signals = df[df['RSI'] <= 30]
            wins = 0
            trades = []
            
            for date, row in buy_signals.iterrows():
                # 信号が出た日のインデックスを取得
                idx = df.index.get_loc(date)
                # 20営業日後が存在するか確認
                if idx + 20 < len(df):
                    buy_price = df.iloc[idx]['Close']
                    sell_price = df.iloc[idx + 20]['Close']
                    return_pct = ((sell_price - buy_price) / buy_price) * 100
                    
                    is_win = return_pct > 0
                    if is_win: wins += 1
                        
                    trades.append({
                        "買い日": date.strftime("%Y-%m-%d"),
                        "買値": round(buy_price, 2),
                        "売却日(約1ヶ月後)": df.index[idx + 20].strftime("%Y-%m-%d"),
                        "売値": round(sell_price, 2),
                        "損益(%)": round(return_pct, 2),
                        "判定": "勝ち 🟢" if is_win else "負け 🔴"
                    })
            
            if trades:
                win_rate = (wins / len(trades)) * 100
                st.subheader(f"シミュレーション結果: 勝率 {win_rate:.1f}% ({len(trades)}戦 {wins}勝)")
                st.dataframe(pd.DataFrame(trades), use_container_width=True)
            else:
                st.warning("過去2年間で、RSIが30以下になる極端な下落タイミングがありませんでした。")