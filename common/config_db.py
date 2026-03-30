import sqlite3
import os

DB_PATH = "local_config.db"

def init_config_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Create a table to store excluded items
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS exclusions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL, -- 'Category', 'Index', or 'Stock'
            value TEXT NOT NULL,
            UNIQUE(type, value)
        )
    """)
    conn.commit()
    conn.close()

def add_exclusion(item_type, value):
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("INSERT INTO exclusions (type, value) VALUES (?, ?)", (item_type, value))
        conn.commit()
    except sqlite3.IntegrityError:
        pass # Already excluded
    finally:
        conn.close()

def remove_exclusion(item_id):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM exclusions WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()

def get_all_exclusions():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM exclusions")
    data = cursor.fetchall()
    conn.close()
    return data