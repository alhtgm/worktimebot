import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
from pathlib import Path
from datetime import datetime
import google.generativeai as genai # Gemini用ライブラリ

# --- .env読み込み ---
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parents[2]
env_path = project_root / '.env'
load_dotenv(dotenv_path=env_path)

DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY') # .envの変数名を変更

# APIキーがない場合のチェック
if not GEMINI_API_KEY:
    print("エラー: .envに GEMINI_API_KEY が設定されていません。")
else:
    # Geminiの設定
    genai.configure(api_key=GEMINI_API_KEY)

# モデルの初期化 (高速な gemini-1.5-flash を使用)
model = genai.GenerativeModel('gemini-2.5-flash')

# ---------------------------

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

class StudyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)
        # セッション管理用: {user_id: {'start_time': datetime, 'goal': str, ...}}
        self.sessions = {}

    async def setup_hook(self):
        await self.tree.sync()

bot = StudyBot()

# --- AIフィードバック生成関数 (Gemini版) ---
async def generate_feedback(duration_str, goal, trouble, done, reflection, next_step):
    """Gemini APIを使ってフィードバックを生成する"""
    
    # プロンプトの作成
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
        # 非同期でGeminiを呼び出し
        response = await model.generate_content_async(prompt)
        return response.text
    except Exception as e:
        print(f"Gemini API エラー: {e}")
        return (
            "⚠️ **AIフィードバックの生成に失敗しました**\n"
            "でも、学習お疲れ様でした！記録はしっかり保存されています。\n"
            f"次回も **{next_step}** に向けて頑張りましょう！"
        )

# --- 2. 終了時の報告モーダル ---
class ReportModal(discord.ui.Modal, title="学習報告"):
    done = discord.ui.TextInput(
        label="やったこと", placeholder="例: 行列の掃き出し法を5問解いた", style=discord.TextStyle.paragraph
    )
    reflection = discord.ui.TextInput(
        label="振り返り", placeholder="例: 計算ミスが多かった", style=discord.TextStyle.paragraph, required=False
    )
    next_step = discord.ui.TextInput(
        label="次にやること", placeholder="例: 余因子展開", style=discord.TextStyle.short, required=False
    )

    def __init__(self, user_id, session_data):
        super().__init__()
        self.user_id = user_id
        self.session_data = session_data

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer() # 処理待ち状態にする

        # 時間計算
        end_time = datetime.now()
        start_time = self.session_data['start_time']
        duration = end_time - start_time
        
        # 時間の整形
        total_seconds = int(duration.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        duration_str = f"{hours}時間{minutes}分{seconds}秒"

        # Geminiからフィードバックを取得
        feedback = await generate_feedback(
            duration_str=duration_str,
            goal=self.session_data.get('goal', 'なし'),
            trouble=self.session_data.get('trouble', 'なし'),
            done=self.done.value,
            reflection=self.reflection.value,
            next_step=self.next_step.value
        )

        # 埋め込みメッセージ作成
        embed = discord.Embed(title="🏁 学習終了レポート", color=discord.Color.green())
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
        
        embed.add_field(name="⏱️ 学習時間", value=duration_str, inline=False)
        embed.add_field(name="✅ やったこと", value=self.done.value, inline=False)
        if self.reflection.value:
            embed.add_field(name="💭 振り返り", value=self.reflection.value, inline=False)
        if self.next_step.value:
            embed.add_field(name="➡️ 次にやること", value=self.next_step.value, inline=False)
        
        # AIフィールド
        embed.add_field(name="🤖 AIコーチ (Gemini) からのフィードバック", value=f"```\n{feedback}\n```", inline=False)

        await interaction.followup.send(embed=embed)
        
        # メモリから削除
        if self.user_id in bot.sessions:
            del bot.sessions[self.user_id]


# --- 1. 開始時の目標設定モーダル ---
class GoalModal(discord.ui.Modal, title="目標設定"):
    goal = discord.ui.TextInput(
        label="目標", placeholder="例: 線形代数の内容を理解する", style=discord.TextStyle.short
    )
    trouble = discord.ui.TextInput(
        label="困っていること", placeholder="例: 掃き出し法がまだわからない", style=discord.TextStyle.short, required=False
    )
    comment = discord.ui.TextInput(
        label="コメント/意気込み", placeholder="例: 今日中に理解する！", style=discord.TextStyle.short, required=False
    )

    async def on_submit(self, interaction: discord.Interaction):
        # セッション開始情報を保存
        bot.sessions[interaction.user.id] = {
            'start_time': datetime.now(),
            'goal': self.goal.value,
            'trouble': self.trouble.value,
            'comment': self.comment.value
        }

        # 開始ログのEmbed
        embed = discord.Embed(title="🚀 学習開始", color=discord.Color.blue())
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
        embed.add_field(name="目標", value=self.goal.value, inline=False)
        if self.trouble.value:
            embed.add_field(name="困っていること", value=self.trouble.value, inline=False)
        if self.comment.value:
            embed.add_field(name="コメント", value=self.comment.value, inline=False)
        
        await interaction.response.send_message(embed=embed)


# --- ボタンView (開始用) ---
class StartButtonView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="学習を開始する", style=discord.ButtonStyle.primary, emoji="📝")
    async def start_study(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(GoalModal())

# --- ボタンView (終了用) ---
class EndButtonView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=None)
        self.user_id = user_id

    @discord.ui.button(label="作業報告をする", style=discord.ButtonStyle.success, emoji="✅")
    async def report_study(self, interaction: discord.Interaction, button: discord.ui.Button):
        # 自分の報告ボタンかチェック
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("これはあなたの学習セッションではありません。", ephemeral=True)
            return
        
        if self.user_id not in bot.sessions:
            await interaction.response.send_message("学習データが見つかりません。すでに終了している可能性があります。", ephemeral=True)
            return

        session_data = bot.sessions[self.user_id]
        await interaction.response.send_modal(ReportModal(self.user_id, session_data))


# --- イベント処理 ---
@bot.event
async def on_voice_state_update(member, before, after):
    if member.bot:
        return

    # 1. VC入室 -> 目標設定ボタンを表示
    if before.channel != after.channel and after.channel is not None:
        if member.id not in bot.sessions:
            try:
                await member.send(
                    f"こんにちは {member.display_name} さんが、学習を開始しました。目標を設定してください。",
                    view=StartButtonView()
                )
            except discord.Forbidden:
                pass

    # 2. VC退室 -> 報告ボタンを表示
    if before.channel is not None and after.channel is None:
        if member.id in bot.sessions:
            try:
                await member.send(
                    f"こんにちは {member.display_name} さんが学習を終了しました。作業報告を完了させてください。",
                    view=EndButtonView(member.id)
                )
            except discord.Forbidden:
                pass

bot.run(DISCORD_TOKEN)