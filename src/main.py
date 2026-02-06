import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
from pathlib import Path

# .envファイルの読み込み
load_dotenv(Path(__file__).parents[1] / '.env')
TOKEN = os.getenv('DISCORD_TOKEN')

class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        # ゲーム検知(status/activity)とメンバー情報のために必要
        intents.presences = True
        intents.members = True
        super().__init__(command_prefix='!', intents=intents)

    async def setup_hook(self):
        # cogsディレクトリ内の拡張機能を読み込む
        cogs_dir = Path(__file__).parent / 'cogs'
        if cogs_dir.exists():
            for filename in os.listdir(cogs_dir):
                if filename.endswith('.py') and not filename.startswith('__'):
                    extension_name = f'cogs.{filename[:-3]}'
                    try:
                        await self.load_extension(extension_name)
                        print(f'Loaded extension: {extension_name}')
                    except Exception as e:
                        print(f'Failed to load extension {extension_name}: {e}')
        else:
            print(f"Warning: cogs directory not found at {cogs_dir}")
        
        # コマンドツリーの同期
        await self.tree.sync()

bot = MyBot()

selected_channel_id = None

@bot.event
async def on_ready():
    print(f'Login: {bot.user}')

@bot.tree.command(name="target_channel", description="チャンネル指定")
async def target_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    global selected_channel_id
    selected_channel_id = channel.id
    await interaction.response.send_message(f"設定完了: {channel.mention}", ephemeral=True)

if __name__ == "__main__":
    bot.run(TOKEN)
