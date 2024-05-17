import sqlite3
import json

class Database:
    def __init__(self, db_file):
        self.conn = sqlite3.connect(db_file)
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER,
                group_name TEXT,
                list_name TEXT,
                UNIQUE(group_name, list_name)
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                user_id INTEGER PRIMARY KEY,
                data TEXT
            )
        ''')
        self.conn.commit()

    def add_group(self, group_id, group_name, list_name):
        try:
            self.cursor.execute('INSERT INTO groups (group_id, group_name, list_name) VALUES (?, ?, ?)', (group_id, group_name, list_name))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def get_all_list_names(self):
        self.cursor.execute('SELECT DISTINCT list_name FROM groups')
        return [row[0] for row in self.cursor.fetchall()]

    def get_groups(self, list_name):
        self.cursor.execute('SELECT group_id FROM groups WHERE list_name = ?', (list_name,))
        return [row[0] for row in self.cursor.fetchall()]

    def get_group_names(self, list_name):
        self.cursor.execute('SELECT group_name FROM groups WHERE list_name = ?', (list_name,))
        return [row[0] for row in self.cursor.fetchall()]

    def remove_group_from_list(self, group_name, list_name):
        try:
            self.cursor.execute('DELETE FROM groups WHERE group_name = ? AND list_name = ?', (group_name, list_name))
            self.conn.commit()
            return self.cursor.rowcount > 0
        except sqlite3.Error:
            return False

    def delete_list(self, list_name):
        try:
            self.cursor.execute('DELETE FROM groups WHERE list_name = ?', (list_name,))
            self.conn.commit()
            return self.cursor.rowcount > 0
        except sqlite3.Error:
            return False

    def temp_store(self, user_id, data):
        json_data = json.dumps(data)
        self.cursor.execute('REPLACE INTO sessions (user_id, data) VALUES (?, ?)', (user_id, json_data))
        self.conn.commit()

    def temp_retrieve(self, user_id):
        self.cursor.execute('SELECT data FROM sessions WHERE user_id = ?', (user_id,))
        data = self.cursor.fetchone()
        return json.loads(data[0]) if data else {}

    def clear_session(self, user_id):
        self.cursor.execute('DELETE FROM sessions WHERE user_id = ?', (user_id,))
        self.conn.commit()
