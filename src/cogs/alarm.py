import discord
from discord.ext import commands
from discord import app_commands # スラッシュコマンド用
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

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)
        # ★機能のON/OFFを管理する変数（デフォルトはTrue=有効）
        self.is_timer_enabled = True

    async def setup_hook(self):
        await self.tree.sync()

bot = MyBot()

# --- タイマー処理関数 ---
async def run_timer(interaction: discord.Interaction, minutes: int):
    await interaction.response.send_message(f"了解しました。{minutes}分後にこのDMでお知らせします。", ephemeral=False)
    await asyncio.sleep(minutes * 60)
    try:
        await interaction.user.send(f"⏰ {minutes}分が経過しました！")
    except Exception as e:
        print(f"通知エラー: {e}")

# --- 時間指定モーダル ---
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

# --- 時間選択ボタン ---
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

# ★★★ 新機能: ON/OFF切り替えコマンド ★★★
@bot.tree.command(name="toggle_timer", description="VC参加時の自動タイマー機能をON/OFFします")
async def toggle_timer(interaction: discord.Interaction):
    # 状態を反転させる (True -> False / False -> True)
    bot.is_timer_enabled = not bot.is_timer_enabled
    
    status_text = "オン" if bot.is_timer_enabled else "オフ"
    color = discord.Color.green() if bot.is_timer_enabled else discord.Color.red()
    
    embed = discord.Embed(
        title="設定変更",
        description=f"自動タイマー機能を **{status_text}** にしました。",
        color=color
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

# --- イベント処理 ---
@bot.event
async def on_voice_state_update(member, before, after):
    if member.bot:
        return

    # --- 自動入室 & DM送信 ---
    if before.channel != after.channel and after.channel is not None:
        
        # ★ここで機能をチェック！ OFFなら何もしないで終了
        if not bot.is_timer_enabled:
            return

        if member.guild.voice_client is None:
            try:
                # 接続処理
                await after.channel.connect(self_deaf=True)
                
                # DM送信処理
                try:
                    await member.send(
                        "ボイスチャットへの参加を確認しました。通知する時間を選択してください：", 
                        view=TimeSelectView()
                    )
                except discord.Forbidden:
                    print(f"{member.name} へのDM送信に失敗しました。")

            except discord.ClientException:
                pass
            except Exception as e:
                print(f"接続エラー詳細: {e}")

    # --- 自動退出 ---
    voice_client = member.guild.voice_client
    if voice_client and voice_client.channel:
        if len(voice_client.channel.members) == 1:
            await voice_client.disconnect()

bot.run(TOKEN)