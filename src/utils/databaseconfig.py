import sqlite3
import os

class DatabaseConfig:
    #sqlite3の接続と初期化
    def __init__(self, db_path="data/study_bot.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.init_db()

    #データベース接続を取得
    def get_connection(self):
        return sqlite3.connect(self.db_path)

    #データベースの初期化
    def init_db(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # 1. users
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL
                )
            ''')
            # 2. servers
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS servers (
                    server_id INTEGER PRIMARY KEY
                )
            ''')
            # 3. study_sessions
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS study_sessions (
                    session_id TEXT PRIMARY KEY, 
                    user_id INTEGER NOT NULL,
                    server_id INTEGER NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    duration_minutes INTEGER,
                    FOREIGN KEY (user_id) REFERENCES users(user_id),
                    FOREIGN KEY (server_id) REFERENCES servers(server_id)
                )
            ''')
            conn.commit()

if __name__ == "__main__":
    # 1. クラスを実体化する（この瞬間に __init__ が呼ばれる）
    config = DatabaseConfig("data/study_bot.db")
    
    # 2. 接続テスト
    try:
        conn = config.get_connection()
        print("データベースに正常に接続できました！")
        
        # テーブルの一覧を取得して確認
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        print(f"作成されたテーブル: {[t[0] for t in tables]}")
        
        conn.close()
        print("テスト完了。")
        
    except Exception as e:
        print(f"エラーが発生しました: {e}")