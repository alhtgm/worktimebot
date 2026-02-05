import discord
from discord.ext import commands
from discord import app_commands
import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parents[3] / '.env')
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

selected_channel_id = None

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f'Login: {bot.user}')

@bot.tree.command(name="target_channel", description="チャンネル指定")
async def target_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    global selected_channel_id
    selected_channel_id = channel.id
    await interaction.response.send_message(f"設定完了: {channel.mention}", ephemeral=True)

bot.run(TOKEN)