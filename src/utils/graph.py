import discord
from discord.ext import commands
from discord import app_commands
import os
from dotenv import load_dotenv
from pathlib import Path
import matplotlib.pyplot as plt
import io
import random
from datetime import datetime, timedelta
import matplotlib.dates as mdates

# --- .env読み込み ---
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parents[1]
env_path = project_root / '.env'
load_dotenv(dotenv_path=env_path)

TOKEN = os.getenv('DISCORD_TOKEN')
if TOKEN is None:
    load_dotenv()
    TOKEN = os.getenv('DISCORD_TOKEN')
# ---------------------------

intents = discord.Intents.default()
intents.message_content = True

class GraphBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # 起動時にコマンドを同期
        await self.tree.sync()

bot = GraphBot()

# --- データ生成用（ダミー） ---
# 本来はデータベースから「過去1週間の勉強時間」を取得する部分です。
def get_mock_week_data():
    today = datetime.now().date()
    dates = []
    hours = []
    
    # 過去7日分の日付と、ランダムな勉強時間(0~5時間)を生成
    for i in range(7):
        date = today - timedelta(days=6-i)
        dates.append(date)
        # ランダムな時間 (GitHubの草っぽさを出すため0の日も作る)
        hours.append(random.choice([0, 0.5, 1.0, 2.5, 4.0, 5.5, 8.0]))
        
    return dates, hours

# --- グラフ描画ロジック ---
def create_graph_image(graph_type: str):
    dates, hours = get_mock_week_data()
    
    # プロットの初期化
    plt.figure(figsize=(10, 5))
    
    # 日本語フォント設定がない環境での文字化けを防ぐため英語表記にします
    
    if graph_type == 'bar':
        # --- 1. 棒グラフ (Bar Chart) ---
        # 色: 落ち着いた青
        plt.bar(dates, hours, color='#4c8bf5', alpha=0.8)
        
        plt.title('Study Time (Last 7 Days)', fontsize=16)
        plt.xlabel('Date', fontsize=12)
        plt.ylabel('Hours', fontsize=12)
        plt.grid(axis='y', linestyle='--', alpha=0.7)
        
        # X軸の日付フォーマット
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))

    elif graph_type == 'grass':
        # --- 2. 草/ヒートマップ (Git-style) ---
        # 1行7列の行列としてデータを扱う
        data_matrix = [hours] 
        
        # 色: 白→緑 (GitHub風)
        plt.imshow(data_matrix, cmap='Greens', aspect='auto', vmin=0, vmax=8)
        
        plt.title('Contribution Graph (Intensity)', fontsize=16)
        plt.yticks([]) # Y軸の目盛りは不要
        
        # X軸の設定
        plt.xticks(range(7), [d.strftime('%m/%d') for d in dates])
        
        # 各マスに数字を入れる
        for i in range(7):
            val = hours[i]
            color = 'white' if val > 4 else 'black' # 背景が濃い場合は文字を白く
            plt.text(i, 0, f"{val}h", ha='center', va='center', color=color, fontsize=12, fontweight='bold')

    # メモリバッファに画像を保存
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight')
    buf.seek(0)
    plt.close() # メモリ解放
    
    return buf

# --- コマンド実装 ---
@bot.tree.command(name="graph", description="過去1週間の勉強時間をグラフにします")
@app_commands.describe(type="グラフの種類を選択")
@app_commands.choices(type=[
    app_commands.Choice(name="棒グラフ (推移が見やすい)", value="bar"),
    app_commands.Choice(name="草 (Gitのようなヒートマップ)", value="grass")
])
async def graph(interaction: discord.Interaction, type: str):
    await interaction.response.defer() # 生成に少し時間がかかるため「考え中」にする
    
    try:
        # グラフ生成処理を呼び出し（重い処理は別スレッドが望ましいですが簡易的にここで実行）
        image_buffer = create_graph_image(type)
        
        # Discordに送信
        file = discord.File(image_buffer, filename=f"study_graph_{type}.png")
        await interaction.followup.send(f"📊 過去1週間の学習レポート ({type})", file=file)
        
    except Exception as e:
        await interaction.followup.send(f"グラフ生成中にエラーが発生しました: {e}")

bot.run(TOKEN)