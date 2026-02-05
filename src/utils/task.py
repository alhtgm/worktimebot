import discord
from discord.ext import commands, tasks
from discord import app_commands
import os
from dotenv import load_dotenv
from pathlib import Path
from datetime import datetime, timedelta, time

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

class TaskManagerBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)
        # 提出物データのリスト
        # 形式: {'subject': '数学', 'date': date_obj, 'remind_days': 3, 'channel_id': 123}
        self.assignments = []

    async def setup_hook(self):
        # リマインドタスクを開始
        self.daily_reminder_task.start()
        await self.tree.sync()

    # --- 定期チェックタスク ---
    # 毎日 朝8:00 に実行
    @tasks.loop(time=time(hour=8, minute=0))
    async def daily_reminder_task(self):
        print("リマインダーチェックを開始します...")
        await self.check_and_send_reminders()

    async def check_and_send_reminders(self):
        today = datetime.now().date()
        
        # 削除リスト（期限切れの整理用）
        to_remove = []

        for task in self.assignments:
            deadline = task['date']
            remind_days = task['remind_days']
            days_until = (deadline - today).days
            
            channel = self.get_channel(task['channel_id'])
            if not channel:
                continue

            # 1. 設定された「〇日前」のリマインド
            if days_until == remind_days:
                await channel.send(
                    f"🔔 **リマインダー**: 『{task['subject']}』の提出期限まであと **{days_until}日** です！\n"
                    f"📅 期限: {deadline.strftime('%Y/%m/%d')}"
                )
            
            # 2. 当日のリマインド
            elif days_until == 0:
                await channel.send(
                    f"🚨 **提出日当日**: 『{task['subject']}』は今日までです！提出を忘れずに！"
                )
            
            # 3. 期限切れ（自動削除する場合）
            elif days_until < 0:
                to_remove.append(task)

        # 過去のタスクを削除
        for task in to_remove:
            self.assignments.remove(task)

bot = TaskManagerBot()

# --- 日付解析用 ---
def parse_date(date_str: str):
    formats = ["%Y/%m/%d", "%Y-%m-%d", "%m/%d", "%m-%d"]
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            # 年省略時は今年の年を補完
            if dt.year == 1900:
                dt = dt.replace(year=datetime.now().year)
            return dt.date()
        except ValueError:
            continue
    return None

# --- 1. 提出物の登録コマンド ---
@bot.tree.command(name="add_task", description="提出物や課題を登録します")
@app_commands.describe(
    subject="教科やタスク名 (例: 数学レポート)",
    date="提出期限 (例: 2/20)",
    remind_days="何日前に通知しますか？ (例: 3)"
)
async def add_task(interaction: discord.Interaction, subject: str, date: str, remind_days: int):
    deadline = parse_date(date)
    if deadline is None:
        await interaction.response.send_message("⚠️ 日付の形式が正しくありません。`2/20` や `2026-02-20` のように入力してください。", ephemeral=True)
        return

    today = datetime.now().date()
    if deadline < today:
        await interaction.response.send_message("⚠️ 過去の日付は登録できません。", ephemeral=True)
        return

    # データを保存
    new_task = {
        'subject': subject,
        'date': deadline,
        'remind_days': remind_days,
        'channel_id': interaction.channel_id # コマンドを打ったチャンネルに通知します
    }
    bot.assignments.append(new_task)
    
    # 日付順に並び替え
    bot.assignments.sort(key=lambda x: x['date'])

    await interaction.response.send_message(
        f"✅ 登録しました！\n"
        f"📚 **{subject}**\n"
        f"📅 期限: {deadline.strftime('%Y/%m/%d')}\n"
        f"🔔 通知: {remind_days}日前"
    )

# --- 2. 一覧確認コマンド ---
@bot.tree.command(name="list_tasks", description="登録されている提出物の一覧を表示します")
async def list_tasks(interaction: discord.Interaction):
    if not bot.assignments:
        await interaction.response.send_message("現在、登録されている課題はありません。🎉", ephemeral=True)
        return

    embed = discord.Embed(title="📚 提出物・課題リスト", color=discord.Color.blue())
    today = datetime.now().date()
    
    text = ""
    for task in bot.assignments:
        deadline = task['date']
        days_left = (deadline - today).days
        
        # 残り日数に応じたアイコン
        if days_left == 0:
            icon = "🚨 **今日**"
        elif days_left <= 3:
            icon = f"⚠️ あと{days_left}日"
        else:
            icon = f"あと{days_left}日"

        text += f"・**{task['subject']}**: {deadline.strftime('%m/%d')} ({icon})\n"

    embed.description = text
    await interaction.response.send_message(embed=embed)

# --- テスト用: 強制リマインドチェック ---
@bot.command()
async def check_now(ctx):
    await ctx.send("リマインダーを手動チェックします...")
    await bot.check_and_send_reminders()
    await ctx.send("チェック完了。")

bot.run(TOKEN)