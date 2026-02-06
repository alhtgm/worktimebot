import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
from pathlib import Path
from datetime import datetime
import uuid
# ★データベース関連のインポート
from utils.databaseconfig import DatabaseConfig
from utils.databasemethods import DatabaseMethods

class StudyTimeCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # データベース設定の初期化
        self.db_config = DatabaseConfig()
        self.db_methods = DatabaseMethods(self.db_config)
        
        # セッションIDをメモリ上で一時的に保持する辞書 {user_id: session_id}
        # ※DBには保存されますが、退室時にどのセッションを終了させるか知るために必要
        self.active_sessions = {}

    @commands.Cog.listener()
    async def on_ready(self):
        print('時間計測ボットが起動しました。')

    # ★ここがメインの計測ロジックです
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        # Bot自身の移動は無視
        if member.bot:
            return

        # 1. ユーザーがVCに参加した（または移動してきた）時 -> 【計測開始】
        if before.channel != after.channel and after.channel is not None:
            
            # まだアクティブなセッションがない場合のみ開始
            if member.id not in self.active_sessions:
                # セッションIDの生成
                session_id = str(uuid.uuid4())
                self.active_sessions[member.id] = session_id
                
                # ユーザー情報とサーバー情報の同期
                self.db_methods.sync_user_and_server(member.id, member.display_name, member.guild.id)
                # セッション開始をDBに記録
                self.db_methods.start_session(session_id, member.id, member.guild.id)
                
                print(f"[開始] {member.name} さんの計測をスタートしました。(Session: {session_id})")

                # BotもVCに入って「計測中」であることを示す（不要なら削除可）
                if member.guild.voice_client is None:
                    try:
                        await after.channel.connect(self_deaf=True)
                    except:
                        pass
                
                # 開始の合図をDMで送る
                try:
                    await member.send(f"⏱️ **{after.channel.name}** での学習時間の計測を開始しました。")
                except discord.Forbidden:
                    print(f"{member.name} へのDM送信に失敗しました。")

        # 2. ユーザーがVCから退出した時 -> 【計測終了 & 結果通知】
        if before.channel is not None and after.channel is None:
            
            # アクティブなセッションがあれば終了処理
            if member.id in self.active_sessions:
                session_id = self.active_sessions.pop(member.id) # IDを取り出して削除
                
                # DB上でセッション終了処理（時間の計算と保存）
                self.db_methods.end_session(session_id)

                print(f"[終了] {member.name} さんの計測終了 (Session: {session_id})")

                # 結果をDMで送信
                # ※ここでの具体的な時間はDBから再取得するか計算する必要がありますが、
                # 簡易的にメッセージだけ送るか、必要ならDBから取得するロジックを追加できます。
                try:
                    await member.send(f"📊 お疲れ様でした！学習時間を記録しました。")
                except discord.Forbidden:
                    pass

        # 3. 誰もいなくなったらBotも退出する処理
        voice_client = member.guild.voice_client
        if voice_client and voice_client.channel:
            if len(voice_client.channel.members) == 1: # メンバーがBot1人だけになったら
                await voice_client.disconnect()
                print("ユーザーがいなくなったため切断しました。")

async def setup(bot):
    await bot.add_cog(StudyTimeCog(bot))