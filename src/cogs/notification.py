
import discord
from discord.ext import commands

class Notification(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.target_voice_id = 1468824662199898290
        self.target_text_id = 1468824662199898289

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):

        text_channel = self.bot.get_channel(self.target_text_id)
        if text_channel is None:
            return

        #入室
        if after.channel is not None and after.channel.id == self.target_voice_id:
            if before.channel is None or before.channel.id != self.target_voice_id:
                await text_channel.send(f"📢 **{member.display_name}** さんが通話に参加しました！")

        #退出の検知
        if before.channel is not None and before.channel.id == self.target_voice_id:
            if after.channel is None or after.channel.id != self.target_voice_id:
                await text_channel.send(f"👋 **{member.display_name}** さんが通話から退出しました。")

async def setup(bot):
    await bot.add_cog(Notification(bot))