import sqlite3
import datetime
import os

DATABASE_PATH = "data/users.db"

class Database:
    def __init__(self):
        os.makedirs("data", exist_ok=True)
        self.conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        self.create_tables()
    
    def create_tables(self):
        cursor = self.conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                joined_date TEXT,
                is_banned BOOLEAN DEFAULT FALSE,
                is_admin BOOLEAN DEFAULT FALSE,
                total_checks INTEGER DEFAULT 0,
                total_hits INTEGER DEFAULT 0,
                checks_today INTEGER DEFAULT 0,
                last_check_date TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS check_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                filename TEXT,
                total_accounts INTEGER,
                hits_found INTEGER,
                check_date TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS proxies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                proxy_string TEXT UNIQUE,
                is_working BOOLEAN DEFAULT TRUE
            )
        ''')
        
        self.conn.commit()
    
    def add_user(self, user_id, username, first_name):
        cursor = self.conn.cursor()
        today = datetime.datetime.now().isoformat()
        
        cursor.execute('''
            INSERT OR IGNORE INTO users (user_id, username, first_name, joined_date)
            VALUES (?, ?, ?, ?)
        ''', (user_id, username, first_name, today))
        
        self.conn.commit()
    
    def is_banned(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute("SELECT is_banned FROM users WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        return result[0] if result else False
    
    def ban_user(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute("UPDATE users SET is_banned = TRUE WHERE user_id = ?", (user_id,))
        self.conn.commit()
    
    def unban_user(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute("UPDATE users SET is_banned = FALSE WHERE user_id = ?", (user_id,))
        self.conn.commit()
    
    def is_admin(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute("SELECT is_admin FROM users WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        return result[0] if result else False
    
    def make_admin(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute("UPDATE users SET is_admin = TRUE WHERE user_id = ?", (user_id,))
        self.conn.commit()
    
    def update_stats(self, user_id, total_checked, hits_found):
        cursor = self.conn.cursor()
        today = datetime.datetime.now().date().isoformat()
        
        cursor.execute('''
            UPDATE users 
            SET total_checks = total_checks + ?,
                total_hits = total_hits + ?,
                checks_today = CASE 
                    WHEN last_check_date = ? THEN checks_today + ?
                    ELSE ?
                END,
                last_check_date = ?
            WHERE user_id = ?
        ''', (total_checked, hits_found, today, total_checked, total_checked, today, user_id))
        
        self.conn.commit()
    
    def add_log(self, user_id, filename, total_accounts, hits_found):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO check_logs (user_id, filename, total_accounts, hits_found, check_date)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, filename, total_accounts, hits_found, datetime.datetime.now().isoformat()))
        self.conn.commit()
    
    def get_user_logs(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT filename, total_accounts, hits_found, check_date 
            FROM check_logs 
            WHERE user_id = ? 
            ORDER BY id DESC 
            LIMIT 10
        ''', (user_id,))
        return cursor.fetchall()
    
    def get_user(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        return cursor.fetchone()
    
    def get_all_users(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT user_id, username, first_name, total_checks, total_hits, is_banned FROM users")
        return cursor.fetchall()
    
    def get_stats(self):
        cursor = self.conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]
        
        cursor.execute("SELECT SUM(total_checks) FROM users")
        total_checks = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT SUM(total_hits) FROM users")
        total_hits = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT COUNT(*) FROM users WHERE checks_today > 0 AND last_check_date = ?", 
                      (datetime.datetime.now().date().isoformat(),))
        active_today = cursor.fetchone()[0]
        
        return {
            "total_users": total_users,
            "total_checks": total_checks,
            "total_hits": total_hits,
            "active_today": active_today,
            "hit_rate": (total_hits / total_checks * 100) if total_checks > 0 else 0
        }
    
    def add_proxy(self, proxy_string):
        cursor = self.conn.cursor()
        try:
            cursor.execute("INSERT INTO proxies (proxy_string) VALUES (?)", (proxy_string,))
            self.conn.commit()
            return True
        except:
            return False
    
    def get_proxies(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT proxy_string FROM proxies WHERE is_working = TRUE")
        return [row[0] for row in cursor.fetchall()]
    
    def delete_proxy(self, proxy_string):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM proxies WHERE proxy_string = ?", (proxy_string,))
        self.conn.commit()
    
    def close(self):
        self.conn.close()