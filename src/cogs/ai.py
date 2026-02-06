import discord
from discord.ext import commands
from discord import app_commands
import os
from dotenv import load_dotenv
from pathlib import Path
from datetime import datetime
import google.generativeai as genai

# --- .env読み込み ---
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parents[1] # 階層に合わせて調整してください
env_path = project_root / '.env'
load_dotenv(dotenv_path=env_path)

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

# APIキーがない場合のチェック
if not GEMINI_API_KEY:
    print("エラー: .envに GEMINI_API_KEY が設定されていません。")
else:
    genai.configure(api_key=GEMINI_API_KEY)

# モデルの初期化 (安定版の 1.5-flash を使用します)
model = genai.GenerativeModel('gemini-2.5-flash')

# --- AIフィードバック生成関数 ---
async def generate_feedback(duration_str, goal, trouble, done, reflection, next_step):
    prompt = f"""
    あなたは親切で優秀な学習コーチです。
    以下のユーザーの学習報告をもとに、以下の2点を行ってください。
    1. 頑張りを認める温かい褒め言葉をかける。
    2. 次の学習に向けた、簡潔で具体的なアドバイスを1つ提供する。
    
    【学習データ】
    ・勉強時間: {duration_str}
    ・当初の目標: {goal}
    ・困っていたこと: {trouble}
    ・実際にやったこと: {done}
    ・ユーザーの振り返り: {reflection}
    ・次にやること: {next_step}

    レスポンスは「肯定的」かつ「励ます」トーンでお願いします。
    """

    try:
        response = await model.generate_content_async(prompt)
        return response.text
    except Exception as e:
        print(f"Gemini API エラー: {e}")
        return (
            "⚠️ **AIフィードバックの生成に失敗しました**\n"
            "でも、学習お疲れ様でした！記録はしっかり保存されています。\n"
            f"次回も **{next_step}** に向けて頑張りましょう！"
        )

# --- 報告モーダル ---
class ReportModal(discord.ui.Modal, title="学習報告"):
    done = discord.ui.TextInput(label="やったこと", placeholder="例: 行列の掃き出し法を5問解いた", style=discord.TextStyle.paragraph)
    reflection = discord.ui.TextInput(label="振り返り", placeholder="例: 計算ミスが多かった", style=discord.TextStyle.paragraph, required=False)
    next_step = discord.ui.TextInput(label="次にやること", placeholder="例: 余因子展開", style=discord.TextStyle.short, required=False)

    def __init__(self, user_id, session_data, cog_instance):
        super().__init__()
        self.user_id = user_id
        self.session_data = session_data
        self.cog_instance = cog_instance

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()

        end_time = datetime.now()
        start_time = self.session_data['start_time']
        duration = end_time - start_time
        total_seconds = int(duration.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        duration_str = f"{hours}時間{minutes}分{seconds}秒"

        feedback = await generate_feedback(
            duration_str,
            self.session_data.get('goal', 'なし'),
            self.session_data.get('trouble', 'なし'),
            self.done.value,
            self.reflection.value,
            self.next_step.value
        )

        embed = discord.Embed(title="🏁 学習終了レポート", color=discord.Color.green())
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
        embed.add_field(name="⏱️ 学習時間", value=duration_str, inline=False)
        embed.add_field(name="✅ やったこと", value=self.done.value, inline=False)
        if self.reflection.value: embed.add_field(name="💭 振り返り", value=self.reflection.value, inline=False)
        if self.next_step.value: embed.add_field(name="➡️ 次にやること", value=self.next_step.value, inline=False)
        embed.add_field(name="🤖 AIコーチ (Gemini)", value=f"```\n{feedback}\n```", inline=False)

        await interaction.followup.send(embed=embed)
        if self.user_id in self.cog_instance.sessions:
            del self.cog_instance.sessions[self.user_id]

# --- 目標設定モーダル ---
class GoalModal(discord.ui.Modal, title="目標設定"):
    goal = discord.ui.TextInput(label="目標", placeholder="例: 線形代数を理解する", style=discord.TextStyle.short)
    trouble = discord.ui.TextInput(label="困っていること", placeholder="例: 掃き出し法がわからない", style=discord.TextStyle.short, required=False)
    comment = discord.ui.TextInput(label="コメント", placeholder="例: 今日中にやる！", style=discord.TextStyle.short, required=False)
    
    def __init__(self, cog_instance):
        super().__init__()
        self.cog_instance = cog_instance

    async def on_submit(self, interaction: discord.Interaction):
        self.cog_instance.sessions[interaction.user.id] = {
            'start_time': datetime.now(),
            'goal': self.goal.value,
            'trouble': self.trouble.value,
            'comment': self.comment.value
        }
        embed = discord.Embed(title="🚀 学習開始", color=discord.Color.blue())
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
        embed.add_field(name="目標", value=self.goal.value, inline=False)
        if self.trouble.value: embed.add_field(name="困っていること", value=self.trouble.value, inline=False)
        await interaction.response.send_message(embed=embed)

# --- ボタンViews ---
class StartButtonView(discord.ui.View):
    def __init__(self, cog_instance):
        super().__init__(timeout=None)
        self.cog_instance = cog_instance
        
    @discord.ui.button(label="学習を開始する", style=discord.ButtonStyle.primary, emoji="📝")
    async def start(self, interaction, button):
        await interaction.response.send_modal(GoalModal(self.cog_instance))

class EndButtonView(discord.ui.View):
    def __init__(self, user_id, cog_instance):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.cog_instance = cog_instance
        
    @discord.ui.button(label="作業報告をする", style=discord.ButtonStyle.success, emoji="✅")
    async def report(self, interaction, button):
        if interaction.user.id != self.user_id: return
        if self.user_id not in self.cog_instance.sessions: return
        await interaction.response.send_modal(ReportModal(self.user_id, self.cog_instance.sessions[self.user_id], self.cog_instance))


class AICog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.sessions = {}
        # ★デフォルトは False (OFF) に設定
        self.is_auto_study_enabled = False

    # --- 機能のON/OFF切り替えコマンド ---
    @app_commands.command(name="toggle_study", description="学習記録・AIフィードバック機能のON/OFFを切り替えます")
    async def toggle_study(self, interaction: discord.Interaction):
        # 状態を反転
        self.is_auto_study_enabled = not self.is_auto_study_enabled
        
        status = "オン (有効)" if self.is_auto_study_enabled else "オフ (無効)"
        color = discord.Color.green() if self.is_auto_study_enabled else discord.Color.red()
        
        embed = discord.Embed(
            title="設定変更",
            description=f"学習記録機能を **{status}** にしました。",
            color=color
        )
        if not self.is_auto_study_enabled:
            embed.set_footer(text="VCに入っても通知は送られません。")
        else:
            embed.set_footer(text="VCに入ると目標設定ボタンが送信されます。")

        await interaction.response.send_message(embed=embed, ephemeral=True)

    # --- イベント処理 ---
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.bot: return

        # ★機能がOFFならここで終了（何もしない）
        if not self.is_auto_study_enabled:
            return

        # 1. VC入室
        if before.channel != after.channel and after.channel is not None:
            if member.id not in self.sessions:
                try:
                    await member.send(
                        f"こんにちは {member.display_name} さん。学習を開始しますか？",
                        view=StartButtonView(self)
                    )
                except: pass

        # 2. VC退室
        if before.channel is not None and after.channel is None:
            if member.id in self.sessions:
                try:
                    await member.send(
                        f"{member.display_name} さん、お疲れ様でした。報告を作成しますか？",
                        view=EndButtonView(member.id, self)
                    )
                except: pass

async def setup(bot):
    await bot.add_cog(AICog(bot))