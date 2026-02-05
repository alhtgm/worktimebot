import sqlite3
from datetime import datetime

class DatabaseMethods:
    def __init__(self, db_config):
        self.config = db_config

    def _execute_query(self, query, params=()):
        with self.config.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor

    def sync_user_and_server(self, user_id, user_name, server_id):
        """
        通話開始前に、ユーザーとサーバーが各マスターテーブルに存在することを確認します。
        外部キー制約があるため、この処理が重要です。
        """
        with self.config.get_connection() as conn:
            cursor = conn.cursor()
            # ユーザーを登録（すでにいれば無視）
            cursor.execute('INSERT OR IGNORE INTO users (user_id, name) VALUES (?, ?)', (user_id, user_name))
            # 名前が変わっている可能性があるので更新
            cursor.execute('UPDATE users SET name = ? WHERE user_id = ?', (user_name, user_id))
            # サーバーを登録（すでにいれば無視）
            cursor.execute('INSERT OR IGNORE INTO servers (server_id) VALUES (?)', (server_id,))
            conn.commit()

    def start_session(self, session_id, user_id, server_id):
        """通話開始（入室）を記録します"""
        start_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        query = '''
            INSERT INTO study_sessions (session_id, user_id, server_id, start_time)
            VALUES (?, ?, ?, ?)
        '''
        self._execute_query(query, (session_id, user_id, server_id, start_time))

    def end_session(self, session_id):
        """通話終了（退室）を記録し、時間を計算します"""
        end_time_dt = datetime.now()
        end_time_str = end_time_dt.strftime('%Y-%m-%d %H:%M:%S')

        with self.config.get_connection() as conn:
            cursor = conn.cursor()
            
            # 開始時間を取得して経過時間を計算
            cursor.execute('SELECT start_time FROM study_sessions WHERE session_id = ?', (session_id,))
            result = cursor.fetchone()
            
            if result:
                start_time_dt = datetime.strptime(result[0], '%Y-%m-%d %H:%M:%S')
                # 差分を分単位で計算（秒なら .total_seconds()）
                duration_minutes = int((end_time_dt - start_time_dt).total_seconds())

                query = '''
                    UPDATE study_sessions 
                    SET end_time = ?, duration_minutes = ? 
                    WHERE session_id = ?
                '''
                cursor.execute(query, (end_time_str, duration_minutes, session_id))
                conn.commit()