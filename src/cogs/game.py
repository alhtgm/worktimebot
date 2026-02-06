import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
from pathlib import Path

class GameCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # --- 共通処理: ゲーマー検知＆キック ---
    async def check_and_kick_gamer(self, member: discord.Member):
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
                
                alert_channel = member.guild.system_channel
                if not alert_channel:
                    for channel in member.guild.text_channels:
                        if channel.permissions_for(member.guild.me).send_messages:
                            alert_channel = channel
                            break
                
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
    @commands.Cog.listener()
    async def on_presence_update(self, before, after):
        # Bot自身は無視
        if after.bot:
            return
        # チェック実行
        await self.check_and_kick_gamer(after)

    # --- イベント2: VC状態更新時 (ゲームしながら入室した瞬間) ---
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.bot:
            return
        # VCに入った、または移動した場合のみチェック
        if before.channel != after.channel and after.channel is not None:
            await self.check_and_kick_gamer(member)

async def setup(bot):
    await bot.add_cog(GameCog(bot))