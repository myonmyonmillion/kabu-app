import streamlit as st
import yfinance as yf
import pandas as pd
import ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="株価底打ち検出アプリ", layout="wide")
st.title("📈 ローリスク向け 株価底打ち検出ダッシュボード")

@st.cache_data(ttl=86400)
def get_nikkei225_tickers():
    try:
        url = "https://ja.wikipedia.org/wiki/%E6%97%A5%E7%B5%8C%E5%B9%B3%E5%9D%87%E6%A0%AA%E4%BE%A1"
        tables = pd.read_html(url)
        for df in tables:
            if 'コード' in df.columns:
                return [str(code) + ".T" for code in df['コード']]
    except Exception:
        return []

st.sidebar.header("検索条件パラメータ")
pbr_threshold = st.sidebar.slider("PBRの上限", 0.5, 2.0, 1.2, 0.1)
rsi_threshold = st.sidebar.slider("RSIの下限（売られすぎ基準）", 20, 40, 35, 1)

target_mode = st.sidebar.radio("対象銘柄の指定方法", ["カスタム入力", "日経225全銘柄スキャン"])
if target_mode == "カスタム入力":
    default_tickers = "7203.T, 8306.T, 9432.T, 8058.T, 8001.T, 4502.T, 9104.T"
    ticker_input = st.sidebar.text_area("分析対象ティッカー（カンマ区切り）", default_tickers)
    ticker_list = [t.strip() for t in ticker_input.split(",") if t.strip()]
else:
    ticker_list = get_nikkei225_tickers()

@st.cache_data(ttl=3600)
def fetch_and_analyze(tickers, pbr_limit, rsi_limit):
    data = []
    progress_bar = st.progress(0, text="データ取得中...")
    total = len(tickers)
    
    for i, t in enumerate(tickers):
        progress_bar.progress((i + 1) / total, text=f"データ取得・解析中... {i+1}/{total} ({t})")
        try:
            stock = yf.Ticker(t)
            df = stock.history(period="1y")
            if df.empty or len(df) < 50: continue
            
            # テクニカル指標の計算
            df['RSI'] = ta.momentum.RSIIndicator(close=df['Close'], window=14).rsi()
            df['SMA25'] = ta.trend.SMAIndicator(close=df['Close'], window=25).sma_indicator()
            
            latest = df.iloc[-1]
            
            info = stock.info
            pbr = info.get('priceToBook', None)
            
            if (pbr is not None and pbr <= pbr_limit) and latest['RSI'] <= rsi_limit:
                # 指値の計算
                buy_limit = df['Low'].tail(5).min() # 直近5日の最安値
                sell_limit = latest['SMA25'] # 25日移動平均線
                expected_profit = (sell_limit - buy_limit) / buy_limit * 100 if buy_limit > 0 else 0
                
                # 売り指値が買い指値を上回っている（期待値がプラス）場合のみ追加
                if expected_profit > 1.0:
                    data.append({
                        "Ticker": t,
                        "銘柄名": info.get('shortName', t),
                        "現在値": round(latest['Close'], 1),
                        "買い指値(目安)": round(buy_limit, 1),
                        "売り指値(目安)": round(sell_limit, 1),
                        "見込利益率(%)": round(expected_profit, 1),
                        "RSI": round(latest['RSI'], 1),
                        "PBR": round(pbr, 2),
                        "df": df
                    })
        except Exception:
            continue
            
    progress_bar.empty()
    return data

if st.button("おすすめ5銘柄を抽出"):
    if not ticker_list:
        st.warning("対象銘柄がありません。")
    else:
        results = fetch_and_analyze(ticker_list, pbr_threshold, rsi_threshold)
        
        if results:
            # RSIが低い順にソートして上位5銘柄に絞る
            res_df = pd.DataFrame(results).sort_values('RSI').head(5)
            display_df = res_df.drop(columns=['df']).reset_index(drop=True)
            
            st.subheader(f"🌟 今日の厳選おすすめ {len(display_df)}銘柄")
            st.dataframe(display_df, use_container_width=True)
            
            st.subheader("詳細チャート確認")
            selected_ticker = st.selectbox("銘柄を選択してください", display_df['Ticker'].tolist())
            
            selected_data = next(r for r in results if r['Ticker'] == selected_ticker)
            df_chart = selected_data['df']
            
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
            
            # 株価と25日移動平均線
            fig.add_trace(go.Candlestick(
                x=df_chart.index, open=df_chart['Open'], high=df_chart['High'],
                low=df_chart['Low'], close=df_chart['Close'], name="株価"
            ), row=1, col=1)
            fig.add_trace(go.Scatter(
                x=df_chart.index, y=df_chart['SMA25'], name="25日移動平均(売値目安)", line=dict(color='blue')
            ), row=1, col=1)
            
            # RSI
            fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['RSI'], name="RSI(14)", line=dict(color='orange')), row=2, col=1)
            fig.add_hline(y=30, line_dash="dash", line_color="red", row=2, col=1)
            
            fig.update_layout(height=600, showlegend=True, xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.success("条件に合致する有望な銘柄はありませんでした。")