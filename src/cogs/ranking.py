import discord
from discord.ext import commands
from discord import app_commands
import os
from dotenv import load_dotenv
from pathlib import Path
import random

# --- .env読み込み ---
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parents[1]
env_path = project_root / '.env'
load_dotenv(dotenv_path=env_path)

TOKEN = os.getenv('DISCORD_TOKEN')
if TOKEN is None:
    load_dotenv()
    TOKEN = os.getenv('DISCORD_TOKEN')
# ---------------------------

# メンバー情報を取得するために必要
intents = discord.Intents.default()
intents.message_content = True
intents.members = True 

class RankingBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()

bot = RankingBot()

# --- 時間表示のフォーマット関数 (例: 1.5時間 -> 1時間30分) ---
def format_hours(hours_float):
    total_minutes = int(hours_float * 60)
    h = total_minutes // 60
    m = total_minutes % 60
    return f"{h}時間{m}分"

# --- 模擬ランキングデータの生成 ---
def generate_mock_ranking(guild, period_type):
    ranking_data = []
    
    # サーバーの全メンバーに対してダミーデータを生成
    for member in guild.members:
        if member.bot:
            continue
            
        # 今週/今月の時間 (0〜50時間)
        current_hours = round(random.uniform(0, 50.0), 1)
        
        # 先週/先月の時間 (比較用: 0〜50時間)
        previous_hours = round(random.uniform(0, 50.0), 1)
        
        # 差分を計算
        diff = current_hours - previous_hours
        
        ranking_data.append({
            "name": member.display_name,
            "current": current_hours,
            "previous": previous_hours,
            "diff": diff
        })
    
    # 時間が多い順(降順)に並び替え
    ranking_data.sort(key=lambda x: x["current"], reverse=True)
    
    return ranking_data

# --- ランキングコマンド ---
@bot.tree.command(name="ranking", description="メンバーの勉強時間ランキングを表示します")
@app_commands.describe(period="期間を選択してください")
@app_commands.choices(period=[
    app_commands.Choice(name="週間ランキング (Weekly)", value="weekly"),
    app_commands.Choice(name="月間ランキング (Monthly)", value="monthly")
])
async def ranking(interaction: discord.Interaction, period: str):
    await interaction.response.defer()
    
    # データの取得（モック）
    data = generate_mock_ranking(interaction.guild, period)
    
    # タイトルや色の設定
    if period == "weekly":
        title = "🏆 今週の勉強時間ランキング (Top 10)"
        desc = "先週との比較を表示しています"
        color = discord.Color.gold()
    else:
        title = "👑 今月の勉強時間ランキング (Top 10)"
        desc = "先月との比較を表示しています"
        color = discord.Color.purple()
        
    embed = discord.Embed(title=title, description=desc, color=color)
    
    # 上位10名を表示
    top_10 = data[:10]
    
    text_list = ""
    for i, user in enumerate(top_10, 1):
        # 順位による装飾
        if i == 1:
            rank_icon = "🥇"
        elif i == 2:
            rank_icon = "🥈"
        elif i == 3:
            rank_icon = "🥉"
        else:
            rank_icon = f"**{i}.**"
            
        # 差分の表示装飾
        diff_val = user["diff"]
        if diff_val > 0.1:
            diff_str = f"📈 (+{format_hours(abs(diff_val))})"
        elif diff_val < -0.1:
            diff_str = f"📉 (-{format_hours(abs(diff_val))})"
        else:
            diff_str = "➡️ (±0分)"
            
        # 行を作成: 1. 名前: 10時間30分 📈 (+2時間)
        current_time_str = format_hours(user["current"])
        text_list += f"{rank_icon} **{user['name']}**: {current_time_str} \u3000{diff_str}\n"

    if not text_list:
        text_list = "データがありません。"

    embed.add_field(name="Ranking", value=text_list, inline=False)
    
    # 自分の順位を探す
    my_rank_info = "圏外"
    for i, user in enumerate(data, 1):
        if user["name"] == interaction.user.display_name:
            my_rank_info = f"{i}位 ({format_hours(user['current'])})"
            break
            
    embed.set_footer(text=f"あなたの順位: {my_rank_info}")
    
    await interaction.followup.send(embed=embed)

bot.run(TOKEN)