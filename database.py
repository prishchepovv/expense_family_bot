import sqlite3
from datetime import datetime, date
import logging

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_name='expenses.db'):
        self.db_name = db_name
        self.init_db()

    def init_db(self):
        """Инициализация базы данных"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        # Таблица пользователей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                registered_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица категорий
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                emoji TEXT
            )
        ''')
        
        # Таблица расходов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                description TEXT,
                date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        # Добавляем основные категории
        default_categories = [
            ('🍔 Еда', '🍔'),
            ('⛽️ Бензин', '⛽️'),
            ('🏠 Дом', '🏠'),
            ('👗 Одежда', '👗'),
            ('💊 Здоровье', '💊'),
            ('🍺 Посиделки', '🍺'),
            ('📱 Связь', '📱'),
            ('💡 Коммуналка', '💡'),
            ('🎁 Подарки', '🎁'),
            ('💸 Кредиты', '💸'),
            ('🚬 Курение', '🚬'),
            ('🐈 Животные', '🐈'),
        ]
        
        cursor.executemany('''
            INSERT OR IGNORE INTO categories (name, emoji) VALUES (?, ?)
        ''', default_categories)
        
        conn.commit()
        conn.close()
        logger.info("База данных инициализирована")

    def add_user(self, user_id, username, first_name):
        """Добавление пользователя"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO users (user_id, username, first_name) 
            VALUES (?, ?, ?)
        ''', (user_id, username, first_name))
        
        conn.commit()
        conn.close()

    def add_expense(self, user_id, amount, category, description=""):
        """Добавление расхода"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO expenses (user_id, amount, category, description, date)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, amount, category, description, datetime.now()))
        
        conn.commit()
        conn.close()

    def get_categories(self):
        """Получение списка категорий"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute('SELECT name, emoji FROM categories')
        categories = cursor.fetchall()
        conn.close()
        
        return [f"{emoji} {name}" for name, emoji in categories]

    def get_today_expenses(self, user_id):
        """Получение расходов за сегодня"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT category, SUM(amount) 
            FROM expenses 
            WHERE user_id = ? AND date(date) = date('now')
            GROUP BY category
        ''', (user_id,))
        
        expenses = cursor.fetchall()
        conn.close()
        return expenses

    def get_month_expenses(self, user_id):
        """Получение расходов за текущий месяц"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT category, SUM(amount) 
            FROM expenses 
            WHERE user_id = ? AND strftime('%Y-%m', date) = strftime('%Y-%m', 'now')
            GROUP BY category
        ''', (user_id,))
        
        expenses = cursor.fetchall()
        conn.close()
        return expenses

    def get_total_today(self, user_id):
        """Общая сумма расходов за сегодня"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT SUM(amount) 
            FROM expenses 
            WHERE user_id = ? AND date(date) = date('now')
        ''', (user_id,))
        
        total = cursor.fetchone()[0] or 0
        conn.close()
        return total

    def get_total_month(self, user_id):
        """Общая сумма расходов за месяц"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT SUM(amount) 
            FROM expenses 
            WHERE user_id = ? AND strftime('%Y-%m', date) = strftime('%Y-%m', 'now')
        ''', (user_id,))
        
        total = cursor.fetchone()[0] or 0
        conn.close()
        return total