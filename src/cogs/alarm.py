import discord
from discord.ext import commands
import asyncio
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

# ログ用チャンネルID (DM送信に失敗した場合などの予備)
LOG_CHANNEL_ID = 1468815312664399967 

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()

bot = MyBot()

# 共通のタイマー処理関数
async def run_timer(interaction: discord.Interaction, minutes: int):
    # まずDMで受付完了を伝える
    await interaction.response.send_message(f"了解しました。{minutes}分後にこのDMでお知らせします。", ephemeral=False)
    
    await asyncio.sleep(minutes * 60)
    
    # 時間経過後の通知（DM）
    try:
        await interaction.user.send(f"⏰ {minutes}分が経過しました！")
    except Exception as e:
        print(f"通知エラー: {e}")

# 任意の時間を入力するモーダル
class CustomTimeModal(discord.ui.Modal, title="時間を指定"):
    time_input = discord.ui.TextInput(
        label="何分後に通知しますか？",
        placeholder="例: 45",
        style=discord.TextStyle.short,
        required=True,
        min_length=1,
        max_length=4
    )

    async def on_submit(self, interaction: discord.Interaction):
        input_value = self.time_input.value
        if input_value.isdigit():
            minutes = int(input_value)
            if minutes > 0:
                await run_timer(interaction, minutes)
            else:
                await interaction.response.send_message("0より大きい数字を入力してください。", ephemeral=True)
        else:
            await interaction.response.send_message("半角数字のみを入力してください。", ephemeral=True)

# 時間指定用のボタンView
class TimeSelectView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="10分", style=discord.ButtonStyle.primary)
    async def ten_min(self, interaction: discord.Interaction, button: discord.ui.Button):
        await run_timer(interaction, 10)

    @discord.ui.button(label="30分", style=discord.ButtonStyle.success)
    async def thirty_min(self, interaction: discord.Interaction, button: discord.ui.Button):
        await run_timer(interaction, 30)

    @discord.ui.button(label="60分", style=discord.ButtonStyle.danger)
    async def sixty_min(self, interaction: discord.Interaction, button: discord.ui.Button):
        await run_timer(interaction, 60)

    @discord.ui.button(label="時間を指定", style=discord.ButtonStyle.secondary, emoji="⌨️")
    async def custom_time(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(CustomTimeModal())

@bot.event
async def on_voice_state_update(member, before, after):
    if member.bot:
        return

    # --- 自動入室 & DM送信 ---
    # ユーザーが新しいチャンネルに移動し、そこが「なし」ではない場合
    if before.channel != after.channel and after.channel is not None:
        # Botがまだ接続していない場合のみ
        if member.guild.voice_client is None:
            try:
                # 【重要】self_deaf=True を追加（接続が安定します）
                await after.channel.connect(self_deaf=True)
                
                # ユーザーにDMを送る
                try:
                    await member.send(
                        "ボイスチャットへの参加を確認しました。通知する時間を選択してください：", 
                        view=TimeSelectView()
                    )
                except discord.Forbidden:
                    print(f"{member.name} へのDM送信に失敗しました（DM許可設定オフなど）。")

            except discord.ClientException:
                # 既に接続中の場合などのエラーを無視
                pass
            except Exception as e:
                print(f"接続エラー詳細: {e}")

    # --- 自動退出 ---
    voice_client = member.guild.voice_client
    if voice_client and voice_client.channel:
        # Botだけになったら切断
        if len(voice_client.channel.members) == 1:
            await voice_client.disconnect()

bot.run(TOKEN)