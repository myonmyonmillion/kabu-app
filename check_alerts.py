import os
import pandas as pd
import requests
import yfinance as yf

ALERTS_FILE = "alerts.csv"
LINE_TOKEN = os.environ.get("LINE_TOKEN", "")
LINE_USER_ID = os.environ.get("LINE_USER_ID", "")


def check_alerts():
  if not LINE_TOKEN or not LINE_USER_ID:
    print("エラー: LINE_TOKEN または LINE_USER_ID が設定されていません。")
    return

  if not os.path.exists(ALERTS_FILE):
    print("alerts.csv が存在しません。")
    return

  try:
    df = pd.read_csv(ALERTS_FILE)
  except Exception as e:
    print(f"CSV読み込みエラー: {e}")
    return

  if df.empty:
    print("登録中のアラートはありません。")
    return

  # 「通知済み」列が存在しない場合は追加
  if "通知済み" not in df.columns:
    df["通知済み"] = False

  updated = False

  for idx, row in df.iterrows():
    # すでに通知済みの場合はスキップ（連投防止）
    if row.get("通知済み", False):
      print(f"{row['銘柄名']}: すでに通知済みのためスキップします。")
      continue

    ticker = row["Ticker"]
    target_p = float(row["目標価格"])
    cond = row["通知条件"]
    name = row["銘柄名"]

    try:
      stock = yf.Ticker(ticker)
      hist = stock.history(period="1d")
      if hist.empty:
        continue
      current_p = float(hist["Close"].iloc[-1])

      trigger = False
      if "以下" in cond and current_p <= target_p:
        trigger = True
      elif "以上" in cond and current_p >= target_p:
        trigger = True

      if trigger:
        message_text = (
            f"🚨 【自動監視】株価アラート発動！\n銘柄: {name} ({ticker})\n現在値:"
            f" {current_p:,.2f}\n条件: {target_p:,.2f} {cond.split(' ')[0]}"
        )
        url = "https://api.line.me/v2/bot/message/push"
        headers = {
            "Authorization": f"Bearer {LINE_TOKEN}",
            "Content-Type": "application/json",
        }
        payload = {
            "to": LINE_USER_ID,
            "messages": [{"type": "text", "text": message_text}],
        }
        res = requests.post(url, headers=headers, json=payload)
        print(f"{name}: 通知送信結果 -> {res.status_code}")

        if res.status_code == 200:
          df.at[idx, "通知済み"] = True
          updated = True
      else:
        print(f"{name}: 条件未達 (現在値 {current_p} / 目標 {target_p})")
    except Exception as e:
      print(f"{ticker} 取得エラー: {e}")

  # 通知済みの状態を更新して保存
  if updated:
    df.to_csv(ALERTS_FILE, index=False)
    print("alerts.csv の通知状態を更新しました。")


if __name__ == "__main__":
  check_alerts()