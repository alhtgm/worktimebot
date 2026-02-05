from datetime import datetime
from .databaseconfig import DatabaseConfig 

class DatabaseMethod: 
    def __init__(self):
        self.config = DatabaseConfig()

    #ユーザーとサーバーの登録
    def register_user_and_server(self, user_id, user_name, server_id, server_name):
        with self.config.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('INSERT OR REPLACE INTO users (user_id, name) VALUES (?, ?)', (user_id, user_name))
            cursor.execute('INSERT OR REPLACE INTO servers (server_id, server_name) VALUES (?, ?)', (server_id, server_name))
            try:
                cursor.execute('INSERT INTO user_servers (user_id, server_id) VALUES (?, ?)', (user_id, server_id))
            except:
                pass
            conn.commit()

    #学習開始時刻を記録
    def start_session(self, user_id, server_id):
        start_time = datetime.now().isoformat()
        with self.config.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('INSERT INTO study_sessions (user_id, server_id, start_time) VALUES (?, ?, ?)', (user_id, server_id, start_time))
            conn.commit()
            return cursor.lastrowid

    #学習終了時刻と学習時間を記録
    def end_session(self, session_id):
        end_time_dt = datetime.now()
        with self.config.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT start_time FROM study_sessions WHERE session_id = ?', (session_id,))
            row = cursor.fetchone()
            if not row: return None
            
            start_time_dt = datetime.fromisoformat(row[0])
            duration = end_time_dt - start_time_dt
            minutes = int(duration.total_seconds() / 60)
            
            cursor.execute('UPDATE study_sessions SET end_time = ?, duration_minutes = ? WHERE session_id = ?', 
                           (end_time_dt.isoformat(), minutes, session_id))
            conn.commit()
            return minutes