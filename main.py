import os
import discord
from discord import app_commands
from discord.ext import tasks
import requests
from flask import Flask
import threading
from datetime import datetime
import asyncio
import pytz
from dotenv import load_dotenv

# 環境変数の読み込み
load_dotenv()

# --- 1. Flask ダミーサーバー設定 (Renderの起動エラー対策) ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is alive!"

def run_flask():
    # Renderが指定するポート（デフォルト10000）で起動
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- 2. 天気予報・服装アドバイスロジック (GASより移植) ---
def get_fashion_advice(temp):
    try:
        temp = float(temp)
    except (ValueError, TypeError):
        return "適切な服装をお選びください"

    if temp >= 28:
        return "ノースリーブ＋薄手スカート。UV対策もおすすめ"
    elif temp >= 24:
        return "半袖ブラウスやワンピースが快適"
    elif temp >= 20:
        return "薄手シャツやカーディガンがちょうど良い"
    elif temp >= 16:
        return "ライトジャケットがあると安心"
    elif temp >= 10:
        return "ニット＋コート系がおすすめ"
    else:
        return "厚手コート・防寒重視がおすすめ"

def get_tokyo_weather():
    url = "https://www.jma.go.jp/bosai/forecast/data/forecast/130000.json"
    try:
        response = requests.get(url)
        data = response.json()
        weather = data[0]["timeSeries"][0]["areas"][0]["weathers"][0]
        
        temp_min = "不明"
        temp_max = "不明"
        temp_areas = data[0]["timeSeries"][2]["areas"]
        for area in temp_areas:
            if area["area"]["name"] == "東京":
                temp_min = area["temps"][0]
                temp_max = area["temps"][1]
                break
        
        advice = get_fashion_advice(temp_max)
        
        return (
            f"🌤️ **東京都 本日の天気**\n\n"
            f"天気：{weather}\n"
            f"最低気温：{temp_min}℃\n"
            f"最高気温：{temp_max}℃\n\n"
            f"👗 **今日のおすすめ服装**\n{advice}"
        )
    except Exception as e:
        return f"天気情報の取得に失敗しました: {e}"

# --- 3. Discord Bot 設定 ---
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GUILD_ID = os.getenv("DISCORD_GUILD_ID")
CHANNEL_ID = os.getenv("DISCORD_CHANNEL_ID")

class MyBot(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.default())
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        # 定期実行タスクを開始
        self.daily_weather_task.start()
        # スラッシュコマンドを同期
        if GUILD_ID:
            guild = discord.Object(id=int(GUILD_ID))
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            print(f"Synced to guild: {GUILD_ID}")

    # 1分ごとにチェックを行うループ
    @tasks.loop(seconds=60)
    async def daily_weather_task(self):
        jst = pytz.timezone('Asia/Tokyo')
        now = datetime.now(jst)
        
        # 毎日 朝6時00分 にメッセージを送信
        if now.hour == 6 and now.minute == 0:
            if CHANNEL_ID:
                channel = self.get_channel(int(CHANNEL_ID))
                if channel:
                    message = get_tokyo_weather()
                    await channel.send(message)
                    print(f"Daily message sent at {now}")
                    # 二重送信防止のために1分以上待機
                    await asyncio.sleep(61)

    @daily_weather_task.before_loop
    async def before_daily_weather_task(self):
        await self.wait_until_ready()

client = MyBot()

# --- 4. スラッシュコマンド (/weather) ---
@client.tree.command(name="weather", description="東京の天気と服装アドバイスを即座に表示します")
async def weather(interaction: discord.Interaction):
    message = get_tokyo_weather()
    await interaction.response.send_message(message)

# --- 5. メイン実行 ---
if __name__ == "__main__":
    # RenderのPort Scan対策としてFlaskを別スレッドで起動
    threading.Thread(target=run_flask, daemon=True).start()
    
    if TOKEN:
        client.run(TOKEN)
    else:
        print("Error: DISCORD_BOT_TOKEN not found.")
