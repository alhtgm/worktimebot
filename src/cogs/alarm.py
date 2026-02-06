import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import os
from dotenv import load_dotenv
from pathlib import Path

class AlarmCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # 実行中のアラームタスクを管理する辞書 {user_id: task}
        self.active_alarms = {}

    # --- アラームのセットアップ ---
    async def run_alarm(self, interaction: discord.Interaction, minutes: int):
        # 既存のアラームがあればキャンセル
        if interaction.user.id in self.active_alarms:
            self.active_alarms[interaction.user.id].cancel()
        
        # メッセージを更新して待機開始
        await interaction.response.edit_message(content=f"了解しました。{minutes}分後にこのDMでお知らせします。", view=None)
        
        # タスクを作成して登録
        task = self.bot.loop.create_task(self.alarm_task(interaction.user, minutes))
        self.active_alarms[interaction.user.id] = task

    # --- 実際の待機ロジック ---
    async def alarm_task(self, user: discord.User, minutes: int):
        try:
            await asyncio.sleep(minutes * 60)
            
            # 時間経過後の通知
            await user.send(f"⏰ {minutes}分が経過しました！")
            
        except asyncio.CancelledError:
            # キャンセルされた場合
            pass
        except Exception as e:
            print(f"アラームエラー: {e}")
        finally:
            # タスク完了後に辞書から削除
            if user.id in self.active_alarms:
                self.active_alarms.pop(user.id, None)

    # --- イベント処理 ---
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.bot:
            return

        # 1. VCに参加した時
        if before.channel != after.channel and after.channel is not None:
            
            # BotもVCに接続（ミュート状態）
            if member.guild.voice_client is None:
                try:
                    await after.channel.connect(self_deaf=True)
                except:
                    pass
            
            # DMで質問を送る
            try:
                await member.send(
                    f"**{after.channel.name}** への参加を確認しました。\nアラーム（タイマー）機能を使用しますか？", 
                    view=InitialAskView(self)
                )
            except discord.Forbidden:
                print(f"{member.name} へのDM送信に失敗しました。")

        # 2. VCから退出した時 -> アラーム解除
        if before.channel is not None and after.channel is None:
            if member.id in self.active_alarms:
                task = self.active_alarms[member.id]
                task.cancel() # タスクをキャンセル
                self.active_alarms.pop(member.id, None)
                
                try:
                    await member.send("🚪 VCから退出したため、アラームを解除しました。")
                except:
                    pass

        # 3. VCからBot以外がいなくなった時（自動切断）
        voice_client = member.guild.voice_client
        if voice_client and voice_client.channel:
            if len(voice_client.channel.members) == 1:
                await voice_client.disconnect()


# --- モーダル（手動入力） ---
class CustomTimeModal(discord.ui.Modal, title="時間を指定"):
    time_input = discord.ui.TextInput(
        label="何分後に通知しますか？",
        placeholder="例: 45",
        style=discord.TextStyle.short,
        required=True,
        min_length=1,
        max_length=4
    )
    
    def __init__(self, cog_instance):
        super().__init__()
        self.cog_instance = cog_instance

    async def on_submit(self, interaction: discord.Interaction):
        if self.time_input.value.isdigit():
            minutes = int(self.time_input.value)
            if minutes > 0:
                await self.cog_instance.run_alarm(interaction, minutes)
            else:
                await interaction.response.send_message("0より大きい数字を入力してください。", ephemeral=True)
        else:
            await interaction.response.send_message("半角数字のみを入力してください。", ephemeral=True)

# --- 時間選択パネル (Step 2) ---
class TimeSelectView(discord.ui.View):
    def __init__(self, cog_instance):
        super().__init__(timeout=None)
        self.cog_instance = cog_instance

    @discord.ui.button(label="10分", style=discord.ButtonStyle.primary)
    async def ten_min(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog_instance.run_alarm(interaction, 10)

    @discord.ui.button(label="30分", style=discord.ButtonStyle.success)
    async def thirty_min(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog_instance.run_alarm(interaction, 30)

    @discord.ui.button(label="60分", style=discord.ButtonStyle.danger)
    async def sixty_min(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog_instance.run_alarm(interaction, 60)

    @discord.ui.button(label="時間を指定", style=discord.ButtonStyle.secondary, emoji="⌨️")
    async def custom_time(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(CustomTimeModal(self.cog_instance))

# --- 最初の質問パネル (Step 1) ---
class InitialAskView(discord.ui.View):
    def __init__(self, cog_instance):
        super().__init__(timeout=None)
        self.cog_instance = cog_instance

    # 「使う」→ 時間選択パネルへ
    @discord.ui.button(label="アラームを使う", style=discord.ButtonStyle.green, emoji="⏰")
    async def use_timer(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            content="通知する時間を選択してください：", 
            view=TimeSelectView(self.cog_instance)
        )

    # 「使わない」→ 終了
    @discord.ui.button(label="使わない", style=discord.ButtonStyle.grey, emoji="✖️")
    async def no_timer(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            content="了解しました。アラームは使用しません。", 
            view=None
        )

async def setup(bot):
    await bot.add_cog(AlarmCog(bot))