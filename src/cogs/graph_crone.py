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
import calendar # 月末の計算用

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

intents = discord.Intents.default()
intents.message_content = True
intents.members = True # メンバー一覧を取得するために必要

class ReportBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # 定期実行タスクを開始
        self.weekly_report_task.start()
        self.monthly_report_task.start()
        await self.tree.sync()

    # --- 定期実行タスク (Weekly) ---
    # 毎週 月曜日 の 9:00 (JST) に実行する設定の例
    # utc_offset=9 で日本時間を指定
    @tasks.loop(time=time(hour=9, minute=0), reconnect=True) 
    async def weekly_report_task(self):
        # 今日が月曜日(0)の場合のみ実行
        now = datetime.now()
        if now.weekday() == 0: 
            print("週次レポートの送信を開始します...")
            await self.send_reports_to_all(period_type="weekly")

    # --- 定期実行タスク (Monthly) ---
    # 毎月 9:00 にチェックし、1日の場合のみ実行
    @tasks.loop(time=time(hour=9, minute=0), reconnect=True)
    async def monthly_report_task(self):
        now = datetime.now()
        # 今日が1日の場合のみ実行
        if now.day == 1:
            print("月次レポートの送信を開始します...")
            await self.send_reports_to_all(period_type="monthly")

    # --- 全員にレポートを送る共通関数 ---
    async def send_reports_to_all(self, period_type: str):
        # 日付範囲の計算
        today = datetime.now().date()
        
        if period_type == "weekly":
            # 先週の月曜〜日曜
            end_date = today - timedelta(days=1) # 昨日（日曜）
            start_date = end_date - timedelta(days=6) # 先週の月曜
            graph_type = "bar" # 週次は棒グラフが見やすい
            title_prefix = "📅 週次レポート"
            
        elif period_type == "monthly":
            # 先月の1日〜末日
            first_day_this_month = today.replace(day=1)
            end_date = first_day_this_month - timedelta(days=1) # 先月の末日
            start_date = end_date.replace(day=1) # 先月の1日
            graph_type = "grass" # 月次は草（ヒートマップ）が見やすい
            title_prefix = "🗓️ 月次レポート"

        # 所属している全サーバーの全メンバーに対して実行
        # ※実際にはデータベースにあるユーザーIDリストを使うのが一般的です
        for guild in self.guilds:
            for member in guild.members:
                if member.bot:
                    continue
                
                try:
                    # グラフ生成 (mockデータ)
                    # ★ここで本来は member.id を渡して、その人のデータをDBから引きます
                    img_buf = create_graph_image(graph_type, start_date, end_date)
                    file = discord.File(img_buf, filename="report.png")
                    
                    await member.send(
                        f"{title_prefix} ({start_date} ~ {end_date})\n今週もお疲れ様でした！", 
                        file=file
                    )
                    print(f"{member.name} に送信しました。")
                    await asyncio.sleep(1) # API制限回避のためのウェイト
                    
                except discord.Forbidden:
                    print(f"{member.name} はDMをブロックしています。")
                except Exception as e:
                    print(f"{member.name} への送信エラー: {e}")

bot = ReportBot()
import asyncio # sleep用にインポート

# --- (前回のコードと同じ) 模擬データ生成 ---
def get_mock_data_range(start_date, end_date):
    dates = []
    hours = []
    delta = (end_date - start_date).days
    if delta < 0: return [], []
    for i in range(delta + 1):
        current_date = start_date + timedelta(days=i)
        dates.append(current_date)
        if random.random() < 0.2: hours.append(0)
        else: hours.append(round(random.uniform(0.5, 9.0), 1))
    return dates, hours

# --- (前回のコードと同じ) グラフ描画 ---
def create_graph_image(graph_type: str, start_date, end_date):
    dates, hours = get_mock_data_range(start_date, end_date)
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
        plt.axis('off') # 軸を消してシンプルに

    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight')
    buf.seek(0)
    plt.close()
    return buf

# ★★★ テスト用コマンド ★★★
# 実際に月曜や1日まで待てないので、強制的にレポート処理を走らせるコマンド
@bot.command()
async def test_weekly(ctx):
    await ctx.send("週次レポートの送信テストを開始します...")
    await bot.send_reports_to_all("weekly")
    await ctx.send("完了しました。")

@bot.command()
async def test_monthly(ctx):
    await ctx.send("月次レポートの送信テストを開始します...")
    await bot.send_reports_to_all("monthly")
    await ctx.send("完了しました。")

bot.run(TOKEN)