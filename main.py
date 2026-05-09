import os
import discord
from discord import app_commands
import requests

# --- 設定 ---
# 環境変数の取得
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
# サーバーIDは数値(int)である必要があるので変換
guild_raw = os.getenv("DISCORD_GUILD_ID")
GUILD_ID = discord.Object(id=int(guild_raw)) if guild_raw else None

# 念のため、読み込めているかチェック（エラーを防ぐ）
if TOKEN is None:
    print("エラー: 環境変数 'DISCORD_BOT_TOKEN' が設定されていません。")
    exit()

class MyBot(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.default())
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        # スラッシュコマンドをサーバーに同期
        self.tree.copy_global_to(guild=GUILD_ID)
        await self.tree.sync(guild=GUILD_ID)

client = MyBot()

def get_weather_info():
    url = "https://www.jma.go.jp/bosai/forecast/data/forecast/130000.json"
    res = requests.get(url).json()
    
    weather = res[0]["timeSeries"][0]["areas"][0]["weathers"][0]
    temp_areas = res[0]["timeSeries"][2]["areas"]
    
    temp_min = "不明"
    temp_max = "不明"
    
    for area in temp_areas:
        if area["area"]["name"] == "東京":
            temp_min = area["temps"][0]
            temp_max = area["temps"][1]
            break
            
    return weather, temp_min, temp_max

def get_fashion_advice(temp):
    temp = int(temp) if temp != "不明" else 0
    if temp >= 28: return "ノースリーブ＋薄手スカート。UV対策もおすすめ"
    if temp >= 24: return "半袖ブラウスやワンピースが快適"
    if temp >= 20: return "薄手シャツやカーディガンがちょうど良い"
    if temp >= 16: return "ライトジャケットがあると安心"
    if temp >= 10: return "ニット＋コート系がおすすめ"
    return "厚手コート・防寒重視がおすすめ"

@client.tree.command(name="tenki", description="東京の天気と服装アドバイスを表示します")
async def tenki(interaction: discord.Interaction):
    weather, t_min, t_max = get_weather_info()
    advice = get_fashion_advice(t_max)
    
    message = (
        f"🌤️ **東京都 本日の天気**\n\n"
        f"天気：{weather}\n"
        f"最低気温：{t_min}℃\n"
        f"最高気温：{t_max}℃\n\n"
        f"👗 **今日のおすすめ服装**\n{advice}"
    )
    await interaction.response.send_message(message)

client.run(TOKEN)
