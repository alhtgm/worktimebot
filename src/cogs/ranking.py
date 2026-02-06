import discord
from discord.ext import commands
from discord import app_commands
import os
from dotenv import load_dotenv
from pathlib import Path
import random
from datetime import datetime, timedelta
# ★データベース関連のインポート
from utils.databaseconfig import DatabaseConfig
from utils.databasemethods import DatabaseMethods

class RankingCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_config = DatabaseConfig()
        self.db_methods = DatabaseMethods(self.db_config)

    # --- 時間表示のフォーマット関数 (例: 1.5時間 -> 1時間30分) ---
    def format_hours(self, hours_float):
        total_minutes = int(hours_float * 60)
        h = total_minutes // 60
        m = total_minutes % 60
        return f"{h}時間{m}分"

    # --- データを生成する関数 (DBから取得) ---
    def get_ranking_data(self, guild, period_type):
        ranking_data = []
        today = datetime.now().date()
        
        # 期間の設定
        if period_type == 'weekly':
            # 今週: 先週の月曜〜日曜じゃないと変かもしれないが、今回は「過去7日間」 vs 「その前の7日間」で比較
            end_date = today
            start_date = today - timedelta(days=6)
            
            prev_end_date = start_date - timedelta(days=1)
            prev_start_date = prev_end_date - timedelta(days=6)
            
        elif period_type == 'monthly':
            # 今月: 過去30日間
            end_date = today
            start_date = today - timedelta(days=29)
            
            prev_end_date = start_date - timedelta(days=1)
            prev_start_date = prev_end_date - timedelta(days=29)

        # 1. 期間内のランキングデータを取得 (List of (user_id, total_minutes))
        current_data = self.db_methods.get_aggregated_ranking(guild.id, start_date, end_date)
        
        # 2. 比較用に前の期間のデータを取得 (辞書化して引きやすくする)
        prev_data_raw = self.db_methods.get_aggregated_ranking(guild.id, prev_start_date, prev_end_date)
        prev_data_map = {row[0]: row[1] for row in prev_data_raw} # {user_id: minutes}

        # 3. 整形
        for row in current_data:
            user_id = row[0]
            total_minutes = row[1]
            
            # メンバー情報の取得 (サーバーにいない人は除外 or "Unknown")
            member = guild.get_member(user_id)
            if not member:
                continue
                
            current_hours = round(total_minutes / 60, 1)
            
            # 前回の時間
            prev_minutes = prev_data_map.get(user_id, 0)
            prev_hours = round(prev_minutes / 60, 1)
            
            diff = current_hours - prev_hours
            
            ranking_data.append({
                "name": member.display_name,
                "current": current_hours,
                "previous": prev_hours,
                "diff": diff
            })
            
        return ranking_data

    # --- ランキングコマンド ---
    @app_commands.command(name="ranking", description="メンバーの勉強時間ランキングを表示します")
    @app_commands.describe(period="期間を選択してください")
    @app_commands.choices(period=[
        app_commands.Choice(name="週間ランキング (Weekly)", value="weekly"),
        app_commands.Choice(name="月間ランキング (Monthly)", value="monthly")
    ])
    async def ranking(self, interaction: discord.Interaction, period: str):
        await interaction.response.defer()
        
        # データの取得
        data = self.get_ranking_data(interaction.guild, period)
        
        # タイトルや色の設定
        if period == "weekly":
            title = "🏆 今週の勉強時間ランキング (Top 10)"
            desc = "過去7日間と、その前の7日間を比較しています"
            color = discord.Color.gold()
        else:
            title = "👑 今月の勉強時間ランキング (Top 10)"
            desc = "過去30日間と、その前の30日間を比較しています"
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
                diff_str = f"📈 (+{self.format_hours(abs(diff_val))})"
            elif diff_val < -0.1:
                diff_str = f"📉 (-{self.format_hours(abs(diff_val))})"
            else:
                diff_str = "➡️ (±0分)"
                
            # 行を作成: 1. 名前: 10時間30分 📈 (+2時間)
            current_time_str = self.format_hours(user["current"])
            text_list += f"{rank_icon} **{user['name']}**: {current_time_str} \u3000{diff_str}\n"

        if not text_list:
            text_list = "データがありません。"

        embed.add_field(name="Ranking", value=text_list, inline=False)
        
        # 自分の順位を探す
        my_rank_info = "圏外"
        for i, user in enumerate(data, 1):
            if user["name"] == interaction.user.display_name:
                my_rank_info = f"{i}位 ({self.format_hours(user['current'])})"
                break
                
        embed.set_footer(text=f"あなたの順位: {my_rank_info}")
        
        await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(RankingCog(bot))