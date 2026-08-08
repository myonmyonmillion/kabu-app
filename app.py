import streamlit as st
import yfinance as yf
import pandas as pd
import ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="株価底打ち検出アプリ", layout="wide")
st.title("📈 ローリスク向け 株価底打ち検出ダッシュボード")

# 日経225取得関数
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

# 主要銘柄の辞書（ここに追加したい銘柄を書いておくと選択肢が増えます）
major_stocks = {
    "トヨタ自動車": "7203.T", "三菱UFJ": "8306.T", "三井住友FG": "8316.T",
    "NTT": "9432.T", "KDDI": "9433.T", "ソフトバンク": "9434.T",
    "三菱商事": "8058.T", "伊藤忠商事": "8001.T", "三井物産": "8031.T",
    "武田薬品": "4502.T", "アステラス製薬": "4503.T",
    "商船三井": "9104.T", "日本郵船": "9101.T",
    "ソニーG": "6758.T", "日立製作所": "6501.T", "信越化学": "4063.T"
}

# --- サイドバー設定 ---
st.sidebar.header("検索条件パラメータ")
pbr_threshold = st.sidebar.slider("PBRの上限（割安さ）", 0.5, 3.0, 1.5, 0.1)
div_threshold = st.sidebar.slider("配当利回りの下限(%)", 0.0, 6.0, 3.0, 0.5)

st.sidebar.header("分析対象の選択")
target_mode = st.sidebar.radio("対象銘柄の指定方法", ["選択式 (主要優良銘柄)", "日経225全銘柄スキャン"])

if target_mode == "選択式 (主要優良銘柄)":
    # 選択式（マルチセレクト）に変更
    default_selections = ["トヨタ自動車", "三菱UFJ", "NTT", "三菱商事", "武田薬品"]
    selected_names = st.sidebar.multiselect("対象銘柄を選択してください", list(major_stocks.keys()), default=default_selections)
    ticker_list = [major_stocks[name] for name in selected_names]
else:
    st.sidebar.info("日経225構成銘柄を自動取得してスキャンします。")
    ticker_list = get_nikkei225_tickers()

# --- データ取得・解析関数 ---
@st.cache_data(ttl=3600)
def fetch_and_analyze(tickers, pbr_limit, div_limit):
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
            # ボリンジャーバンド追加
            indicator_bb = ta.volatility.BollingerBands(close=df["Close"], window=20, window_dev=2)
            df['BB_High'] = indicator_bb.bollinger_hband()
            df['BB_Low'] = indicator_bb.bollinger_lband()
            
            latest = df.iloc[-1]
            info = stock.info
            pbr = info.get('priceToBook', None)
            div = (info.get('dividendYield', 0) or 0) * 100
            
            # ファンダメンタルズ条件（PBRと配当利回りで足切り）
            if (pbr is not None and pbr <= pbr_limit) and (div >= div_limit):
                buy_limit = df['Low'].tail(5).min()
                sell_limit = latest['SMA25']
                
                # 状態のテキスト判定
                rsi_val = latest['RSI']
                if rsi_val <= 35:
                    status = "🔥 底値圏 (要注目)"
                elif rsi_val <= 45:
                    status = "📉 下落・様子見"
                elif rsi_val >= 70:
                    status = "⚠️ 高値圏 (過熱)"
                else:
                    status = "平熱"

                data.append({
                    "Ticker": t,
                    "銘柄名": info.get('shortName', t),
                    "現在値": round(latest['Close'], 1),
                    "状態": status,
                    "RSI": round(rsi_val, 1),
                    "PBR": round(pbr, 2),
                    "配当利回り(%)": round(div, 2),
                    "買い指値(目安)": round(buy_limit, 1),
                    "売り指値(目安)": round(sell_limit, 1),
                    "df": df
                })
        except Exception:
            continue
            
    progress_bar.empty()
    return data

# --- メイン画面 ---
if st.button("現在の条件でランキングを抽出"):
    if not ticker_list:
        st.warning("対象銘柄が選択されていません。")
    else:
        results = fetch_and_analyze(ticker_list, pbr_threshold, div_threshold)
        
        if results:
            # 「RSIが低い順（より売られすぎている順）」に並び替えて最大5件表示
            res_df = pd.DataFrame(results).sort_values('RSI', ascending=True).head(5)
            display_df = res_df.drop(columns=['df']).reset_index(drop=True)
            
            st.subheader(f"🌟 指定条件をクリアした「RSIが低い（底値に近い）」トップ {len(display_df)}銘柄")
            st.dataframe(display_df, use_container_width=True)
            
            st.subheader("詳細チャート確認")
            selected_ticker = st.selectbox("チャートを見る銘柄を選択してください", display_df['Ticker'].tolist())
            
            selected_data = next(r for r in results if r['Ticker'] == selected_ticker)
            df_chart = selected_data['df']
            
            # Plotlyでチャート描画（ボリンジャーバンド追加）
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
            
            # 株価ローソク足
            fig.add_trace(go.Candlestick(
                x=df_chart.index, open=df_chart['Open'], high=df_chart['High'],
                low=df_chart['Low'], close=df_chart['Close'], name="株価"
            ), row=1, col=1)
            
            # 移動平均とボリンジャーバンド
            fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['SMA25'], name="25日移動平均", line=dict(color='blue', width=1)), row=1, col=1)
            fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['BB_High'], name="+2σ", line=dict(color='lightgray', dash='dash')), row=1, col=1)
            fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['BB_Low'], name="-2σ (底値目安)", line=dict(color='lightgray', dash='dash')), row=1, col=1)
            
            # RSI
            fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['RSI'], name="RSI(14)", line=dict(color='orange')), row=2, col=1)
            fig.add_hline(y=35, line_dash="dash", line_color="red", annotation_text="売られすぎライン(35)", row=2, col=1)
            
            fig.update_layout(height=650, showlegend=True, xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.success("指定した条件（PBR・配当利回り）を満たす銘柄はありませんでした。左のパラメーターを少し緩めてみてください。")