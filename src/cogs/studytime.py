import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
from pathlib import Path
from datetime import datetime

# --- .env読み込み設定 ---
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
intents.voice_states = True

class TimeTrackerBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)
        # ユーザーの入室時間を記録する辞書 {ユーザーID: 入室時間(datetime)}
        self.study_records = {}

    async def setup_hook(self):
        # 今回はコマンドがないため同期処理は不要ですが、枠だけ残しています
        pass

bot = TimeTrackerBot()

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('時間計測ボットが起動しました。')

# ★ここがメインの計測ロジックです
@bot.event
async def on_voice_state_update(member, before, after):
    # Bot自身の移動は無視
    if member.bot:
        return

    # 1. ユーザーがVCに参加した（または移動してきた）時 -> 【計測開始】
    if before.channel != after.channel and after.channel is not None:
        
        # まだ記録がない場合のみ開始時間をセット
        if member.id not in bot.study_records:
            bot.study_records[member.id] = datetime.now()
            print(f"[開始] {member.name} さんの計測をスタートしました。")

            # BotもVCに入って「計測中」であることを示す（不要なら削除可）
            if member.guild.voice_client is None:
                try:
                    await after.channel.connect(self_deaf=True)
                except:
                    pass
            
            # 開始の合図をDMで送る
            try:
                await member.send(f"⏱️ **{after.channel.name}** での学習時間の計測を開始しました。")
            except discord.Forbidden:
                print(f"{member.name} へのDM送信に失敗しました。")

    # 2. ユーザーがVCから退出した時 -> 【計測終了 & 結果通知】
    if before.channel is not None and after.channel is None:
        
        # 記録があれば計算する
        if member.id in bot.study_records:
            start_time = bot.study_records.pop(member.id) # 記録を取り出して削除
            end_time = datetime.now()
            
            # 経過時間を計算
            duration = end_time - start_time
            total_seconds = int(duration.total_seconds())
            
            # 表示用の整形 (時・分・秒)
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            
            time_str = f"{seconds}秒"
            if minutes > 0:
                time_str = f"{minutes}分 " + time_str
            if hours > 0:
                time_str = f"{hours}時間 " + time_str

            print(f"[終了] {member.name} さんの計測終了: {time_str}")

            # 結果をDMで送信
            try:
                await member.send(f"📊 お疲れ様でした！今回の滞在時間は **{time_str}** でした。")
            except discord.Forbidden:
                pass

    # 3. 誰もいなくなったらBotも退出する処理
    voice_client = member.guild.voice_client
    if voice_client and voice_client.channel:
        if len(voice_client.channel.members) == 1: # メンバーがBot1人だけになったら
            await voice_client.disconnect()
            print("ユーザーがいなくなったため切断しました。")

bot.run(TOKEN)