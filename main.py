import os
import discord
from discord import app_commands
import requests
from flask import Flask
import threading
from dotenv import load_dotenv

load_dotenv()

# --- 1. Flask ダミーサーバー設定 (Renderのタイムアウト対策) ---
app = Flask(__name__)

@app.route('/')
def hello():
    return "Bot is running!"

def run_flask():
    # Renderは環境変数 PORT を指定してくるので、それに合わせる
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- 2. Discord Bot 設定 ---
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
guild_id_env = os.getenv("DISCORD_GUILD_ID")

class MyBot(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.default())
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        if guild_id_env:
            guild = discord.Object(id=int(guild_id_env))
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            print(f"Synced to guild: {guild_id_env}")

client = MyBot()

# --- 3. 天気予報ロジック (以前のものを移植) ---
def get_weather_info():
    url = "https://www.jma.go.jp/bosai/forecast/data/forecast/130000.json"
    res = requests.get(url).json()
    weather = res[0]["timeSeries"][0]["areas"][0]["weathers"][0]
    temp_max = res[0]["timeSeries"][2]["areas"][0]["temps"][1] # 東京の最高気温
    return weather, temp_max

@client.tree.command(name="tenki", description="東京の天気を表示")
async def tenki(interaction: discord.Interaction):
    weather, t_max = get_weather_info()
    await interaction.response.send_message(f"今日の天気は {weather}、最高気温は {t_max}℃ です！")

# --- 4. 実行 ---
if __name__ == "__main__":
    # Flaskを別スレッドで開始
    threading.Thread(target=run_flask).start()
    
    # Discord Botを開始
    if TOKEN:
        client.run(TOKEN)
    else:
        print("Error: DISCORD_BOT_TOKEN not found.")
