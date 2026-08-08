import yfinance as yf
import pandas as pd
import ta

def check_bottom_signal(ticker_symbol):
    try:
        stock = yf.Ticker(ticker_symbol)
        df = stock.history(period="1y")
        
        if df.empty or len(df) < 50:
            return None

        # テクニカル指標の計算
        df['RSI'] = ta.momentum.RSIIndicator(close=df['Close'], window=14).rsi()
        df['SMA25'] = ta.trend.SMAIndicator(close=df['Close'], window=25).sma_indicator()

        latest = df.iloc[-1]
        prev = df.iloc[-2]

        info = stock.info
        pbr = info.get('priceToBook', None)
        div_yield = info.get('dividendYield', 0) or 0

        # 条件判定（少し条件を緩めて検出しやすく調整）
        # 1. RSIが35以下（売られすぎ圏内）
        is_rsi_low = latest['RSI'] < 35
        # 2. 前日からRSIが上昇（下げ止まり・反発の兆候）
        is_rsi_turning = latest['RSI'] > prev['RSI']
        # 3. PBR 1.5倍以下（割安圏）
        is_cheap = (pbr is not None and pbr < 1.5)

        status = "通常"
        if is_rsi_low and is_cheap:
            if is_rsi_turning:
                status = "★底打ち反発の兆候"
            else:
                status = "売られすぎ（監視対象）"

        return {
            "コード": ticker_symbol,
            "銘柄名": info.get('shortName', ticker_symbol),
            "現在値": round(latest['Close'], 1),
            "RSI": round(latest['RSI'], 1),
            "PBR": round(pbr, 2) if pbr else "N/A",
            "配当利回り(%)": round(div_yield * 100, 2),
            "判定": status
        }
    except Exception as e:
        return None

# 日経平均の主要銘柄・高配当株リスト例
tickers = [
    "7203.T", # トヨタ自動車
    "8306.T", # 三菱UFJ
    "9432.T", # NTT
    "8058.T", # 三菱商事
    "8001.T", # 伊藤忠
    "6758.T", # ソニーグループ
    "4502.T", # 武田薬品
    "9104.T", # 商船三井
]

print("データ取得・解析中...")
results = []
for t in tickers:
    res = check_bottom_signal(t)
    if res:
        results.append(res)

df_res = pd.DataFrame(results)
print("\n=== 解析結果 ===")
print(df_res.to_string(index=False))