import discord
from discord.ext import commands
from discord import ui
import datetime

# --- 設定 ---
# 実際のIDに書き換えてください
TEXT_CHANNEL_ID = 1468824662199898287
STUDY_VOICE_CHANNEL_ID = 1468824662199898290

# --- 1. 目標設定用モーダル ---
class StudyStartModal(ui.Modal, title="学習目標設定"):
    goal = ui.TextInput(
        label="今の目標",
        style=discord.TextStyle.short,
        placeholder="例: 英単語を50個覚える"
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
        # テキストチャンネルを取得して送信
        channel = interaction.guild.get_channel(TEXT_CHANNEL_ID)
        
        embed = discord.Embed(title="🚀 学習開始", color=discord.Color.blue())
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
        embed.add_field(name="目標", value=self.goal.value, inline=False)
        if self.problem.value:
            embed.add_field(name="困っていること", value=self.problem.value, inline=False)
        if self.comment.value:
            embed.add_field(name="コメント", value=self.comment.value, inline=False)

        await channel.send(embed=embed)
        
        # モーダルを送信したユーザーには、自分だけにその場で見えるメッセージを返す
        await interaction.response.send_message(
            f"{interaction.user.display_name}さん、入力ありがとうございます。学習を頑張ってください！",
            ephemeral=True
        )

# --- 2. 目標設定開始ボタン（View） ---
class StartStudyView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="学習を開始する", style=discord.ButtonStyle.primary, custom_id="start_study_btn")
    async def start_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(StudyStartModal())

# --- 3. 学習報告用モーダル ---
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
        
        # 時間の計算（秒、分、時間）
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
            f"{interaction.user.display_name}さん、入力ありがとうございます。お疲れ様でした！",
            ephemeral=True
        )

# --- 4. 学習終了報告ボタン（View） ---
class EndStudyView(ui.View):
    def __init__(self, duration: datetime.timedelta):
        super().__init__(timeout=None)
        self.duration = duration

    @ui.button(label="作業報告をする", style=discord.ButtonStyle.primary, custom_id="end_study_btn")
    async def end_button(self, interaction: discord.Interaction, button: ui.Button):
        # モーダルを開く際に、計算済みの時間を渡す
        await interaction.response.send_modal(StudyEndModal(duration=self.duration))

# --- 5. メインのCogクラス ---
class StudyCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.session_start_times = {} # ユーザーIDごとの開始時間を保持

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        # ボイスチャンネルへの参加・退出がない場合は無視
        if before.channel == after.channel:
            return

        text_channel = self.bot.get_channel(TEXT_CHANNEL_ID)
        if not text_channel:
            # チャンネルが見つからない場合は処理しない（エラー回避）
            return


        if after.channel and after.channel.id == STUDY_VOICE_CHANNEL_ID:
            self.session_start_times[member.id] = datetime.datetime.now()
            
            await text_channel.send(
                content=f"{member.display_name}さんが、学習を開始しました。目標を設定してください。",
                view=StartStudyView()
            )


        elif before.channel and before.channel.id == STUDY_VOICE_CHANNEL_ID:

            if member.id in self.session_start_times:
                start_time = self.session_start_times.pop(member.id) 
                end_time = datetime.datetime.now()
                duration = end_time - start_time
                
                await text_channel.send(
                    content=f"{member.display_name}さんが学習を終了しました。作業報告を完了させてください。",
                    view=EndStudyView(duration=duration) 
                )

async def setup(bot):
    await bot.add_cog(StudyCog(bot))