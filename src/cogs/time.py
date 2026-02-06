import discord
from discord.ext import commands
from discord import app_commands
import os
from dotenv import load_dotenv
from pathlib import Path
from datetime import datetime, timedelta
import random
# ★データベース関連のインポート
from utils.databaseconfig import DatabaseConfig
from utils.databasemethods import DatabaseMethods

class TimeCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_config = DatabaseConfig()
        self.db_methods = DatabaseMethods(self.db_config)

    # --- 日付解析用 ---
    def parse_date(self, date_str: str):
        formats = ["%Y/%m/%d", "%Y-%m-%d", "%m/%d", "%m-%d"]
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                if dt.year == 1900:
                    dt = dt.replace(year=datetime.now().year)
                return dt.date()
            except ValueError:
                continue
        return None

    # --- データ取得 (DBから) ---
    def get_data_list(self, user_id, start_date, end_date):
        data_list = []
        
        # 1. 範囲内の全日付を0で初期化
        date_map = {}
        delta = (end_date - start_date).days
        if delta < 0: return []
        
        for i in range(delta + 1):
            d = start_date + timedelta(days=i)
            # datetime.dateオブジェクトのまま扱います
            date_map[d] = 0.0

        # 2. DBからデータを取得
        # db_data = self.db_methods.get_daily_study_time(user_id, start_date, end_date) # 廃止
        
        query = '''
            SELECT date(start_time), SUM(duration_minutes)
            FROM study_sessions
            WHERE user_id = ? 
              AND date(start_time) BETWEEN ? AND ?
              AND duration_minutes IS NOT NULL
            GROUP BY date(start_time)
            ORDER BY date(start_time)
        '''
        
        with self.db_config.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (user_id, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')))
            db_data = cursor.fetchall()
        
        for row in db_data:
            d_str = row[0] # "YYYY-MM-DD"
            minutes = row[1]
            
            d_obj = datetime.strptime(d_str, '%Y-%m-%d').date()
            if d_obj in date_map:
                date_map[d_obj] = round(minutes / 60, 1) # 分 -> 時間

        # 3. リストに戻す
        for d in sorted(date_map.keys()):
            data_list.append({"date": d, "hours": date_map[d]})
                
        return data_list

    # --- 統計コマンド ---
    @app_commands.command(name="stats", description="勉強時間の詳細データを数値リストで表示します")
    @app_commands.describe(
        period="期間を選択 (週間 / 月間 / カスタム)",
        start="開始日 (カスタムの場合のみ必須。例: 2/1)",
        end="終了日 (省略可)"
    )
    @app_commands.choices(period=[
        app_commands.Choice(name="1週間 (Weekly)", value="weekly"),
        app_commands.Choice(name="1ヶ月 (Monthly)", value="monthly"),
        app_commands.Choice(name="カスタム指定", value="custom")
    ])
    async def stats(self, interaction: discord.Interaction, period: str, start: str = None, end: str = None):
        # 期間の決定ロジック
        today = datetime.now().date()
        
        if period == "weekly":
            end_date = today
            start_date = today - timedelta(days=6) # 過去7日間
            title = "📅 週次データレポート"
            
        elif period == "monthly":
            end_date = today
            start_date = today - timedelta(days=29) # 過去30日間
            title = "🗓️ 月次データレポート"
            
        elif period == "custom":
            if start is None:
                await interaction.response.send_message("⚠️ カスタムを選択した場合は `start` (開始日) を入力してください。", ephemeral=True)
                return
            
            start_date = self.parse_date(start)
            if start_date is None:
                await interaction.response.send_message("⚠️ 日付形式エラー。 `2/1` のように入力してください。", ephemeral=True)
                return

            if end:
                end_date = self.parse_date(end)
                if end_date is None:
                    await interaction.response.send_message("⚠️ 終了日の形式が正しくありません。", ephemeral=True)
                    return
            else:
                end_date = today
                
            title = f"📊 指定期間レポート ({start_date.strftime('%m/%d')} ~ {end_date.strftime('%m/%d')})"

        # 日付順序チェック
        if start_date > end_date:
            await interaction.response.send_message("⚠️ 開始日が終了日より未来になっています。", ephemeral=True)
            return

        # データ取得 (DBから)
        data = self.get_data_list(interaction.user.id, start_date, end_date)
        
        if not data:
            await interaction.response.send_message("データがありません。", ephemeral=True)
            return

        # === 集計処理 ===
        total_hours = sum(d["hours"] for d in data)
        avg_hours = total_hours / len(data) if data else 0
        max_hours = max(data, key=lambda x: x["hours"])
        
        # === テキスト整形 (表組みのような見た目にする) ===
        # Discordのコードブロック ``` を使って等幅フォントで表示します
        text_table = " 日付       | 時間 \n"
        text_table += "------------+------\n"
        
        for entry in data:
            d_str = entry["date"].strftime("%Y/%m/%d")
            h_str = f"{entry['hours']}h".rjust(5) # 右寄せで桁を揃える
            text_table += f" {d_str} | {h_str}\n"

        # 文字数制限対策 (長すぎる場合はカット)
        if len(text_table) > 1800:
            text_table = text_table[:1800] + "\n... (データが長すぎるため省略)"

        # Embed作成
        embed = discord.Embed(title=title, color=discord.Color.green())
        
        # 概要フィールド
        summary_text = (
            f"**合計時間**: `{total_hours:.1f} 時間`\n"
            f"**1日平均**: `{avg_hours:.1f} 時間`\n"
            f"**最高記録**: `{max_hours['hours']} 時間` ({max_hours['date'].strftime('%m/%d')})"
        )
        embed.add_field(name="📈 集計サマリー", value=summary_text, inline=False)
        
        # 詳細データフィールド
        embed.add_field(name="📝 詳細ログ", value=f"```\n{text_table}\n```", inline=False)

        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(TimeCog(bot))