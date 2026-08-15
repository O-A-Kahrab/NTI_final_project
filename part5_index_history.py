"""
Part 5 — Indexing (SQLite) & History / Favorites Persistence
===============================================================
يحتوي هذا الملف على:
- FileIndexDB: فهرسة اختيارية للملفات باستخدام SQLite لتسريع البحث المتكرر.
- دوال سجل البحث (History) والمفضلة (Favorites) المحفوظة على شكل JSON.

يعتمد على:
    part1_constants_utils.py  (لجلب أسماء الملفات الافتراضية)
"""

import os
import time
import json
import sqlite3
import datetime as dt

from part1_constants_utils import HISTORY_FILE, FAVORITES_FILE, INDEX_DB_FILE


# =====================================================================
#            الفهرسة باستخدام SQLite (Advanced - Optional)
# =====================================================================

class FileIndexDB:
    """
    فهرسة اختيارية للملفات باستخدام SQLite لتسريع عمليات البحث المتكررة.
    لا تُستخدم إلزاميًا؛ محرك البحث المباشر (search_files) يبقى يعمل بشكل مستقل تمامًا.
    """

    def __init__(self, db_path=INDEX_DB_FILE):
        self.db_path = db_path

    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS files (
                path TEXT PRIMARY KEY,
                name TEXT,
                extension TEXT,
                size INTEGER,
                created TEXT,
                modified TEXT,
                directory TEXT
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_name ON files(name)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ext ON files(extension)")
        return conn

    def rebuild_index(self, directories, stop_event, progress_callback=None):
        conn = self._connect()
        cur = conn.cursor()
        cur.execute("DELETE FROM files")
        conn.commit()

        count = 0
        for directory in directories:
            if stop_event.is_set():
                break
            for root, dirs, files in os.walk(directory):
                if stop_event.is_set():
                    break
                for f in files:
                    if stop_event.is_set():
                        break
                    full_path = os.path.join(root, f)
                    try:
                        stats = os.stat(full_path)
                    except OSError:
                        continue
                    cur.execute(
                        "INSERT OR REPLACE INTO files VALUES (?,?,?,?,?,?,?)",
                        (full_path, f, os.path.splitext(f)[1].lower(), stats.st_size,
                         time.strftime("%Y-%m-%d %H:%M", time.localtime(stats.st_ctime)),
                         time.strftime("%Y-%m-%d %H:%M", time.localtime(stats.st_mtime)),
                         root)
                    )
                    count += 1
                    if count % 500 == 0:
                        conn.commit()
                        if progress_callback:
                            progress_callback(count, root)
        conn.commit()
        conn.close()
        return count

    def search(self, name_query, limit=2000):
        conn = self._connect()
        cur = conn.cursor()
        cur.execute("SELECT path, name, extension, size, created, modified FROM files WHERE name LIKE ? LIMIT ?",
                     (f"%{name_query}%", limit))
        rows = cur.fetchall()
        conn.close()
        return rows

    def count(self):
        try:
            conn = self._connect()
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM files")
            n = cur.fetchone()[0]
            conn.close()
            return n
        except Exception:
            return 0


# =====================================================================
#                       سجل البحث (History) والمفضلة
# =====================================================================

def save_to_history(search_query, results, history_file=HISTORY_FILE):
    """Kept as the original function to maintain compatibility with old calls"""
    history_data = {}
    if os.path.exists(history_file):
        try:
            with open(history_file, "r", encoding="utf-8") as f:
                history_data = json.load(f)
        except Exception:
            history_data = {}

    history_data[search_query] = results

    with open(history_file, "w", encoding="utf-8") as f:
        json.dump(history_data, f, ensure_ascii=False, indent=4)


def load_history_entries(history_file="search_history_entries.json"):
    if not os.path.exists(history_file):
        return []
    try:
        with open(history_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def append_history_entry(entry, history_file="search_history_entries.json", max_entries=50):
    entries = load_history_entries(history_file)
    entries.insert(0, entry)
    entries = entries[:max_entries]
    try:
        with open(history_file, "w", encoding="utf-8") as f:
            json.dump(entries, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
    return entries


def clear_history_entries(history_file="search_history_entries.json"):
    try:
        if os.path.exists(history_file):
            os.remove(history_file)
    except Exception:
        pass


def load_favorites(favorites_file=FAVORITES_FILE):
    if not os.path.exists(favorites_file):
        return []
    try:
        with open(favorites_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_favorites(favorites, favorites_file=FAVORITES_FILE):
    try:
        with open(favorites_file, "w", encoding="utf-8") as f:
            json.dump(favorites, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
