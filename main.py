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

load_dotenv()

app = Flask(__name__)
@app.route('/')
def home(): return "Bot is alive!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- 改良版：天気予報・服装アドバイスロジック ---
def get_fashion_advice(temp):
    try:
        temp = float(temp)
    except (ValueError, TypeError):
        return "適切な服装をお選びください"

    if temp >= 28: return "ノースリーブ＋薄手スカート。UV対策もおすすめ"
    elif temp >= 24: return "半袖ブラウスやワンピースが快適"
    elif temp >= 20: return "薄手シャツやカーディガンがちょうど良い"
    elif temp >= 16: return "ライトジャケットがあると安心"
    elif temp >= 10: return "ニット＋コート系がおすすめ"
    else: return "厚手コート・防寒重視がおすすめ"

def get_tokyo_weather():
    url = "https://www.jma.go.jp/bosai/forecast/data/forecast/130000.json"
    try:
        response = requests.get(url)
        data = response.json()
        
        # 天気
        weather = data[0]["timeSeries"][0]["areas"][0]["weathers"][0]
        
        # 気温取得の改良
        temp_min = "不明"
        temp_max = "不明"
        temp_series = data[0]["timeSeries"][2]["areas"]
        
        for area in temp_series:
            if area["area"]["name"] == "東京":
                # 数値だけを抽出してリスト化
                temps = []
                for t in area["temps"]:
                    try:
                        temps.append(float(t))
                    except ValueError:
                        continue
                
                if len(temps) >= 2:
                    # 2つ以上ある場合は、小さい方を最低、大きい方を最高とする
                    # ※気象庁のデータ順序（今日最高/明日最低など）に左右されないための処理
                    temp_min = int(min(temps))
                    temp_max = int(max(temps))
                elif len(temps) == 1:
                    # 1つしかない場合は、それを最高気温として扱う
                    temp_max = int(temps[0])
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

# --- Discord Bot 本体 ---
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GUILD_ID = os.getenv("DISCORD_GUILD_ID")
CHANNEL_ID = os.getenv("DISCORD_CHANNEL_ID")

class MyBot(discord.Client):
    def __init__(self):
        # インテントの設定を変更
        intents = discord.Intents.default()
        intents.message_content = True  # これを追加
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        self.daily_weather_task.start()
        if GUILD_ID:
            guild = discord.Object(id=int(GUILD_ID))
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)

    @tasks.loop(seconds=60)
    async def daily_weather_task(self):
        jst = pytz.timezone('Asia/Tokyo')
        now = datetime.now(jst)
        if now.hour == 6 and now.minute == 30:
            if CHANNEL_ID:
                channel = self.get_channel(int(CHANNEL_ID))
                if channel:
                    await channel.send(get_tokyo_weather())
                    await asyncio.sleep(61)

    @daily_weather_task.before_loop
    async def before_daily_weather_task(self):
        await self.wait_until_ready()

client = MyBot()

# --- メンションに反応する処理 ---
@client.event
async def on_message(message):
    # Bot自身のメッセージには反応しない
    if message.author == client.user:
        return

    # Botへのメンションが含まれているかチェック
    if client.user in message.mentions:
        content = message.content.lower()
        
        # 褒め言葉のリスト
        compliments = ["かわいい", "可愛い", "すごい", "天才", "えらい", "偉い", "助かる", "好き", "大好き", "すき", "がんばって", "頑張って", "有能"]
        
        # 褒め言葉が含まれているか確認
        if any(word in content for word in compliments):
            replies = [
                "えっ…そ、そんなこと言われても何も出ないよ！ (/// \/\/\/)",
                "あ、ありがとう…。急に言われると照れるな…。",
                "ふん、当たり前でしょ！…でも、そんなに褒められるのは悪くないかも…。",
                "（照れて顔をそらしている）",
                "も、もう！お世辞はやめてよ！嬉しいけど！",
                "かもねさんに褒められるととっても嬉しい！"
            ]
            import random
            await message.reply(random.choice(replies))
        else:
            # 褒め言葉以外のメンションへの反応（必要なら）
            await message.reply("呼んだ？何か手伝えることがあったら言ってね！")

@client.tree.command(name="weather", description="東京の天気を表示")
async def weather(interaction: discord.Interaction):
    await interaction.response.send_message(get_tokyo_weather())

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    if TOKEN:
        client.run(TOKEN)
