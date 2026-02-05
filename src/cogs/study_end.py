import discord
from discord.ext import commands
from discord import ui
import datetime

TEXT_CHANNEL_ID = 1468824662199898289
STUDY_VOICE_CHANNEL_ID = 1468824662199898290

#学習報告
class StudyEndModal(ui.Modal, title="学習記録報告"):
    def __init__(self, duration: datetime.timedelta):
        super().__init__()
        self.duration = duration

    todo = ui.TextInput(
        label="やったこと",
        style=discord.TextStyle.short
    )
    progress = ui.TextInput(
        label="分かったこと、わからなかったこと",
        style=discord.TextStyle.short,
        required=False
    )
    next_do = ui.TextInput(
        label="次にやること",
        style=discord.TextStyle.short,
        required=False
    )

    async def on_submit(self, interaction: discord.Interaction):
        channel = interaction.guild.get_channel(TEXT_CHANNEL_ID)
        
        # 時間の計算
        total_seconds = int(self.duration.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        time_str = f"{hours}時間{minutes}分{seconds}秒"

        embed = discord.Embed(title="🏁 学習終了", color=discord.Color.green())
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
        embed.add_field(name="学習時間", value=time_str, inline=False)
        embed.add_field(name="やったこと", value=self.todo.value, inline=False)
        if self.progress.value:
            embed.add_field(name="振り返り", value=self.progress.value, inline=False)
        if self.next_do.value:
            embed.add_field(name="次にやること", value=self.next_do.value, inline=False)

        await channel.send(embed=embed)

        await interaction.response.send_message(
            f"{interaction.user.display_name}さん,お疲れ様でした！",
            ephemeral=True
        )

#学習終了報告ボタン
class EndStudyView(ui.View):
    def __init__(self, duration: datetime.timedelta):
        super().__init__(timeout=None)
        self.duration = duration

    @ui.button(label="作業報告をする", style=discord.ButtonStyle.primary, custom_id="end_study_btn")
    async def end_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(StudyEndModal(duration=self.duration))

#終了処理
class StudyEndCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        if not hasattr(self.bot, "session_start_times"):
            self.bot.session_start_times = {}

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if before.channel == after.channel:
            return

        text_channel = self.bot.get_channel(TEXT_CHANNEL_ID)
        if not text_channel:
            return

        #退出検知
        if before.channel and before.channel.id == STUDY_VOICE_CHANNEL_ID:
            
            # bot本体の変数から開始時間を取得
            if member.id in self.bot.session_start_times:
                start_time = self.bot.session_start_times.pop(member.id) 
                end_time = datetime.datetime.now()
                duration = end_time - start_time
                
                await text_channel.send(
                    content=f"{member.display_name}さんが学習を終了しました。作業報告を完了させてください。",
                    view=EndStudyView(duration=duration) 
                )

async def setup(bot):
    await bot.add_cog(StudyEndCog(bot))