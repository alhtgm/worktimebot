import discord
from discord.ext import commands
from discord import ui
import datetime

TEXT_CHANNEL_ID = 1468824662199898289
STUDY_VOICE_CHANNEL_ID = 1468824662199898290

#目標設定
class StudyStartModal(ui.Modal, title="学習目標設定"):
    goal = ui.TextInput(
        label="今の目標",
        style=discord.TextStyle.short,
        placeholder=""
    )
    problem = ui.TextInput(
        label="困っていること、解決したいこと",
        style=discord.TextStyle.short,
        required=False
    )
    comment = ui.TextInput(
        label="コメント",
        style=discord.TextStyle.paragraph,
        required=False
    )

    async def on_submit(self, interaction: discord.Interaction):
        channel = interaction.guild.get_channel(TEXT_CHANNEL_ID)
        
        embed = discord.Embed(title="🚀 学習開始", color=discord.Color.blue())
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
        embed.add_field(name="目標", value=self.goal.value, inline=False)
        if self.problem.value:
            embed.add_field(name="困っていること", value=self.problem.value, inline=False)
        if self.comment.value:
            embed.add_field(name="コメント", value=self.comment.value, inline=False)

        await channel.send(embed=embed)
        
        await interaction.response.send_message(
            f"{interaction.user.display_name}さん、入力ありがとうございます。学習を頑張ってください！",
            ephemeral=True
        )

#開始ボタン
class StartStudyView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="学習を開始する", style=discord.ButtonStyle.primary, custom_id="start_study_btn")
    async def start_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(StudyStartModal())

#Cogクラス
class StudyStartCog(commands.Cog):
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

        # 入室検知
        if after.channel and after.channel.id == STUDY_VOICE_CHANNEL_ID:
            # bot本体の変数に開始時間を保存
            self.bot.session_start_times[member.id] = datetime.datetime.now()
            
            await text_channel.send(
                content=f"{member.display_name}さんが、学習を開始しました。目標を設定してください。",
                view=StartStudyView()
            )

async def setup(bot):
    await bot.add_cog(StudyStartCog(bot))