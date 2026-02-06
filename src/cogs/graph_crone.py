import discord
from discord.ext import commands, tasks
from discord import app_commands
import os
from dotenv import load_dotenv
from pathlib import Path
import matplotlib.pyplot as plt
import io
import random
from datetime import datetime, timedelta, time, date
import matplotlib.dates as mdates
import math
import asyncio
from utils.databaseconfig import DatabaseConfig
from utils.databasemethods import DatabaseMethods

class GraphCroneCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_config = DatabaseConfig()
        self.db_methods = DatabaseMethods(self.db_config)

    async def cog_load(self):
        self.weekly_report_task.start()
        self.monthly_report_task.start()

    async def cog_unload(self):
        self.weekly_report_task.cancel()
        self.monthly_report_task.cancel()

    # --- 定期実行タスク (Weekly) ---
    @tasks.loop(time=time(hour=9, minute=0), reconnect=True) 
    async def weekly_report_task(self):
        now = datetime.now()
        if now.weekday() == 0: 
            print("週次レポートの送信を開始します...")
            await self.send_reports_to_all(period_type="weekly")

    # --- 定期実行タスク (Monthly) ---
    @tasks.loop(time=time(hour=9, minute=0), reconnect=True)
    async def monthly_report_task(self):
        now = datetime.now()
        if now.day == 1:
            print("月次レポートの送信を開始します...")
            await self.send_reports_to_all(period_type="monthly")

    # --- 全員にレポートを送る共通関数 ---
    async def send_reports_to_all(self, period_type: str):
        today = datetime.now().date()
        
        if period_type == "weekly":
            end_date = today - timedelta(days=1)
            start_date = end_date - timedelta(days=6)
            graph_type = "bar"
            title_prefix = "📅 週次レポート"
            
        elif period_type == "monthly":
            first_day_this_month = today.replace(day=1)
            end_date = first_day_this_month - timedelta(days=1)
            start_date = end_date.replace(day=1)
            graph_type = "grass"
            title_prefix = "🗓️ 月次レポート"

        for guild in self.bot.guilds:
            for member in guild.members:
                if member.bot:
                    continue
                
                try:
                    # DBからデータを取得してグラフ生成 (データがない場合はNoneが返るなどのハンドリングが必要)
                    # ここではデータが0でもグラフを作る仕様とします
                    img_buf = self.create_graph_image(graph_type, start_date, end_date, member.id)
                    file = discord.File(img_buf, filename="report.png")
                    
                    await member.send(
                        f"{title_prefix} ({start_date} ~ {end_date})\n今週もお疲れ様でした！", 
                        file=file
                    )
                    print(f"{member.name} に送信しました。")
                    await asyncio.sleep(1)
                    
                except discord.Forbidden:
                    print(f"{member.name} はDMをブロックしています。")
                except Exception as e:
                    print(f"{member.name} への送信エラー: {e}")

    # --- グラフ描画 ---
    def create_graph_image(self, graph_type: str, start_date, end_date, user_id=None):
        # データ取得 (user_idが必要)
        dates = []
        hours = []
        delta = (end_date - start_date).days
        
        # 日付リストの作成 (X軸用)
        date_map = {}
        for i in range(delta + 1):
            d = start_date + timedelta(days=i)
            dates.append(d)
            date_map[d] = 0 # 初期値0

        if user_id:
            # DBから直接取得する形に修正 (DatabasMethodsの変更を回避)
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
                data = cursor.fetchall()

            for row in data:
                d_str = row[0] # "YYYY-MM-DD"
                minutes = row[1]
                
                # datetime.date オブジェクトに変換してマッピング
                d_obj = datetime.strptime(d_str, '%Y-%m-%d').date()
                if d_obj in date_map:
                    date_map[d_obj] = round(minutes / 60, 1) # 時間単位に変換

        # マップからリストへ戻す
        hours = [date_map[d] for d in dates]

        num_days = len(dates)
        width = 10 if num_days < 20 else 15
        plt.figure(figsize=(width, 6))
        
        if graph_type == 'bar':
            plt.bar(dates, hours, color='#4c8bf5', alpha=0.8)
            plt.title(f'Study Time ({start_date} - {end_date})', fontsize=16)
            plt.grid(axis='y', linestyle='--', alpha=0.5)
            ax = plt.gca()
            if num_days <= 10: ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
            else: ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
            plt.xticks(rotation=45)

        elif graph_type == 'grass':
            weeks = math.ceil(num_days / 7)
            padded_hours = hours + [None] * (weeks * 7 - len(hours))
            matrix = []
            for i in range(weeks):
                matrix.append(padded_hours[i*7 : (i+1)*7])
            plot_data = [[h if h is not None else -1 for h in row] for row in matrix]
            plt.imshow(plot_data, cmap='Greens', aspect='auto', vmin=0, vmax=9)
            plt.title(f'Contribution ({start_date} ~ {end_date})', fontsize=16)
            plt.axis('off')

        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight')
        buf.seek(0)
        plt.close()
        return buf

    # --- 日付文字列を解析する関数 ---
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

    # --- コマンド実装 ---
    @app_commands.command(name="graph", description="指定した期間の勉強時間をグラフ化します")
    @app_commands.describe(
        type="グラフの種類 (棒グラフ / 草)",
        start="開始日 (例: 2/1, 2026-02-01)",
        end="終了日 (省略すると今日まで。例: 2/20)"
    )
    @app_commands.choices(
        type=[
            app_commands.Choice(name="棒グラフ", value="bar"),
            app_commands.Choice(name="草 (ヒートマップ)", value="grass")
        ]
    )
    async def graph(self, interaction: discord.Interaction, type: str, start: str, end: str = None):
        start_date = self.parse_date(start)
        if start_date is None:
            await interaction.response.send_message(f"⚠️ 開始日 `{start}` の形式がわかりません。\n`2/1` や `2026-02-01` のように入力してください。", ephemeral=True)
            return

        if end:
            end_date = self.parse_date(end)
            if end_date is None:
                await interaction.response.send_message(f"⚠️ 終了日 `{end}` の形式がわかりません。", ephemeral=True)
                return
        else:
            end_date = datetime.now().date()

        if start_date > end_date:
            await interaction.response.send_message("⚠️ 開始日が終了日より未来になっています。", ephemeral=True)
            return

        await interaction.response.defer()
        
        try:
            # 自分のIDを渡す
            image_buffer = self.create_graph_image(type, start_date, end_date, interaction.user.id)
            
            filename = f"graph_{start_date.strftime('%Y%m%d')}-{end_date.strftime('%Y%m%d')}.png"
            file = discord.File(image_buffer, filename=filename)
            
            await interaction.followup.send(
                content=f"📊 **期間レポート**: {start_date.strftime('%Y/%m/%d')} 〜 {end_date.strftime('%Y/%m/%d')}",
                file=file
            )
            
        except Exception as e:
            await interaction.followup.send(f"エラーが発生しました: {e}")

    # ★★★ テスト用コマンド ★★★
    @commands.command()
    async def test_weekly(self, ctx):
        await ctx.send("週次レポートの送信テストを開始します...")
        await self.send_reports_to_all("weekly")
        await ctx.send("完了しました。")

    @commands.command()
    async def test_monthly(self, ctx):
        await ctx.send("月次レポートの送信テストを開始します...")
        await self.send_reports_to_all("monthly")
        await ctx.send("完了しました。")

async def setup(bot):
    await bot.add_cog(GraphCroneCog(bot))
