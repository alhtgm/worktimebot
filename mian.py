import discord
import os
import sys
from discord.ext import commands
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"ログインしました: {bot.user}")

    bot.session_start_times = {}

# Cogの読み込み
    try:
        #1.学習開始機能の読み込み
        await bot.load_extension("src.cogs.study_start")
        print("study_start extension loaded successfully.")

        #2学習終了機能の読み込み
        await bot.load_extension("src.cogs.study_end")
        print("study_end extension loaded successfully.")
        
        #同期
        synced = await bot.tree.sync()
        print(f"{len(synced)} 個のコマンドを同期しました。")
        
    except Exception as e:
        print(f"拡張機能の読み込みに失敗しました: {e}")

#実行
if TOKEN:
    bot.run(TOKEN)
else:
    print("エラー: .envファイルにTOKENが見つかりません。")