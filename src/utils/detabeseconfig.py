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
                    server_id INTEGER PRIMARY KEY,
                    server_name TEXT NOT NULL
                )
            ''')
            # 3. user_servers
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_servers (
                    user_id INTEGER, server_id INTEGER,
                    PRIMARY KEY (user_id, server_id),
                    FOREIGN KEY (user_id) REFERENCES users (user_id),
                    FOREIGN KEY (server_id) REFERENCES servers (server_id)
                )''')
            # 4. study_sessions
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS study_sessions (
                    session_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER, server_id INTEGER,
                    start_time TEXT NOT NULL, end_time TEXT, duration_minutes INTEGER,
                    FOREIGN KEY (user_id, server_id) REFERENCES user_servers (user_id, server_id)
                )''')
            conn.commit()