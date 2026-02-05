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
import math

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
        await self.tree.sync()

bot = GraphBot()

# --- 日付文字列を解析する関数 ---
def parse_date(date_str: str):
    """
    "2/1", "2025-02-01", "2026/2/20" などの文字列を datetime オブジェクトに変換
    """
    formats = [
        "%Y/%m/%d", "%Y-%m-%d", # 年あり
        "%m/%d", "%m-%d"        # 年なし
    ]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            # 年が省略された場合 (1900年になる) は、現在の年に補正
            if dt.year == 1900:
                dt = dt.replace(year=datetime.now().year)
            return dt.date()
        except ValueError:
            continue
            
    return None # 解析失敗

# --- 指定範囲の模擬データ生成 ---
def get_mock_data_range(start_date, end_date):
    dates = []
    hours = []
    
    # 日数差を計算
    delta = (end_date - start_date).days
    
    # 開始日が終了日より後の場合などは空などを返す対策
    if delta < 0:
        return [], []

    for i in range(delta + 1):
        current_date = start_date + timedelta(days=i)
        dates.append(current_date)
        
        # ランダムな勉強時間 (0〜10h)
        if random.random() < 0.2:
            hours.append(0)
        else:
            hours.append(round(random.uniform(0.5, 9.0), 1))
            
    return dates, hours

# --- グラフ描画ロジック ---
def create_graph_image(graph_type: str, start_date, end_date):
    dates, hours = get_mock_data_range(start_date, end_date)
    num_days = len(dates)
    
    # 画像サイズ調整
    width = 10 if num_days < 20 else 15
    plt.figure(figsize=(width, 6))
    
    if graph_type == 'bar':
        # === 棒グラフ ===
        plt.bar(dates, hours, color='#4c8bf5', alpha=0.8)
        
        plt.title(f'Study Time ({start_date.strftime("%Y/%m/%d")} - {end_date.strftime("%m/%d")})', fontsize=16)
        plt.ylabel('Hours', fontsize=12)
        plt.grid(axis='y', linestyle='--', alpha=0.5)
        
        # X軸フォーマット
        ax = plt.gca()
        if num_days <= 15:
            ax.xaxis.set_major_locator(mdates.DayLocator(interval=1))
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
        elif num_days <= 40:
            ax.xaxis.set_major_locator(mdates.DayLocator(interval=5))
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
        else:
            ax.xaxis.set_major_locator(mdates.MonthLocator())
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y/%m'))
            
        plt.xticks(rotation=45)

    elif graph_type == 'grass':
        # === 草 (ヒートマップ) ===
        weeks = math.ceil(num_days / 7)
        padded_hours = hours + [None] * (weeks * 7 - len(hours))
        
        matrix = []
        for i in range(weeks):
            matrix.append(padded_hours[i*7 : (i+1)*7])
            
        plot_data = [[h if h is not None else -1 for h in row] for row in matrix]

        plt.imshow(plot_data, cmap='Greens', aspect='auto', vmin=0, vmax=9)
        plt.title(f'Contribution ({start_date.strftime("%m/%d")} ~ {end_date.strftime("%m/%d")})', fontsize=16)
        
        plt.xlabel('Day', fontsize=12)
        plt.ylabel('Week', fontsize=12)
        plt.xticks(range(7), ['Day1', '2', '3', '4', '5', '6', '7'])
        plt.yticks(range(weeks), [f"W{i+1}" for i in range(weeks)])

        # データ数が多い場合は数字を表示しない
        if num_days <= 35:
            for y in range(weeks):
                for x in range(7):
                    val = matrix[y][x]
                    if val is not None:
                        color = 'white' if val > 4.5 else 'black'
                        plt.text(x, y, f"{val}", ha='center', va='center', 
                                 color=color, fontsize=10, fontweight='bold')

    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight')
    buf.seek(0)
    plt.close()
    
    return buf

# --- コマンド実装 ---
@bot.tree.command(name="graph", description="指定した期間の勉強時間をグラフ化します")
@app_commands.describe(
    type="グラフの種類 (棒グラフ / 草)",
    start="開始日 (例: 2/1, 2026-02-01)",
    end="終了日 (省略すると今日まで。例: 2/20)"
)
@app_commands.choices(
    type=[
        app_commands.Choice(name="棒グラフ", value="bar"),
        app_commands.Choice(name="草 (ヒートマップ)", value="grass")
    ]
)
async def graph(interaction: discord.Interaction, type: str, start: str, end: str = None):
    # 1. 開始日の解析
    start_date = parse_date(start)
    if start_date is None:
        await interaction.response.send_message(f"⚠️ 開始日 `{start}` の形式がわかりません。\n`2/1` や `2026-02-01` のように入力してください。", ephemeral=True)
        return

    # 2. 終了日の解析
    if end:
        end_date = parse_date(end)
        if end_date is None:
            await interaction.response.send_message(f"⚠️ 終了日 `{end}` の形式がわかりません。", ephemeral=True)
            return
    else:
        # 省略されたら今日にする
        end_date = datetime.now().date()

    # 3. 日付の前後チェック
    if start_date > end_date:
        await interaction.response.send_message("⚠️ 開始日が終了日より未来になっています。", ephemeral=True)
        return

    await interaction.response.defer()
    
    try:
        image_buffer = create_graph_image(type, start_date, end_date)
        
        # ファイル名をわかりやすく (例: graph_20260201-20260220.png)
        filename = f"graph_{start_date.strftime('%Y%m%d')}-{end_date.strftime('%Y%m%d')}.png"
        file = discord.File(image_buffer, filename=filename)
        
        await interaction.followup.send(
            content=f"📊 **期間レポート**: {start_date.strftime('%Y/%m/%d')} 〜 {end_date.strftime('%Y/%m/%d')}",
            file=file
        )
        
    except Exception as e:
        await interaction.followup.send(f"エラーが発生しました: {e}")

bot.run(TOKEN)