import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
from pathlib import Path

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

# ▼▼▼ 設定エリア ▼▼▼
# 警告メッセージを送るテキストチャンネルのID
ALERT_CHANNEL_ID = 1468815312664399967 
# ▲▲▲▲▲▲▲▲▲▲▲▲▲

# ゲーム監視に必要な権限設定
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True # VCの状態を見る
intents.presences = True    # ゲームのアクティビティを見る (※PortalでONにする必要あり)
intents.members = True      # メンバー情報を詳しく見る

class GamingPoliceBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # コマンド同期（今回はイベントメインですが念のため）
        await self.tree.sync()

bot = GamingPoliceBot()

# --- 共通処理: ゲーマー検知＆キック ---
async def check_and_kick_gamer(member: discord.Member):
    # 1. そもそもVCに入っていなければ無視
    if member.voice is None or member.voice.channel is None:
        return

    # 2. ユーザーのアクティビティ（状態）をチェック
    # member.activities には「Spotifyを聞いている」「配信中」「ゲーム中」などがリストで入っています
    for activity in member.activities:
        # アクティビティの種類が「Playing (ゲーム中)」の場合
        if activity.type == discord.ActivityType.playing:
            
            game_name = activity.name
            print(f"検知: {member.name} が {game_name} をプレイ中")

            # --- 処罰執行 ---
            
            # A. 全体に晒す
            alert_channel = bot.get_channel(ALERT_CHANNEL_ID)
            if alert_channel:
                await alert_channel.send(
                    f"@everyone  **緊急警報** \n"
                    f"{member.mention} が勉強中にゲーム『**{game_name}**』をプレイしています！\n"
                    f"強制的に通話から退室させます！"
                )

            # B. VCから切断する (move_to(None) で切断になります)
            try:
                await member.move_to(None)
                if alert_channel:
                    await alert_channel.send(f"🔨 {member.display_name} をVCからキックしました。")
            except discord.Forbidden:
                if alert_channel:
                    await alert_channel.send("⚠️ 権限不足のためキックできませんでした。Botの権限を確認してください。")
            except Exception as e:
                print(f"キックエラー: {e}")
            
            # 1つでもゲームが見つかれば処理して終了（重複キックを防ぐ）
            return

# --- イベント1: アクティビティ更新時 (ゲームを始めた瞬間) ---
@bot.event
async def on_presence_update(before, after):
    # Bot自身は無視
    if after.bot:
        return
    # チェック実行
    await check_and_kick_gamer(after)

# --- イベント2: VC状態更新時 (ゲームしながら入室した瞬間) ---
@bot.event
async def on_voice_state_update(member, before, after):
    if member.bot:
        return
    # VCに入った、または移動した場合のみチェック
    if before.channel != after.channel and after.channel is not None:
        await check_and_kick_gamer(member)

bot.run(TOKEN)