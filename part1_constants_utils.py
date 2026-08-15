"""
Part 1 — Constants & Basic File Utilities
===========================================
يحتوي هذا الملف على:
- الثوابت العامة (امتدادات، أحجام، تواريخ...)
- الدوال المساعدة الأساسية لجلب معلومات الملفات وتنسيقها.

لا يعتمد هذا الملف على أي جزء آخر من المشروع.
"""

import os
import time
import platform
import hashlib


# =====================================================================
#                         الثوابت (Constants)
# =====================================================================

INVALID_NAME_CHARS = ["\\", "/", ":", ">", "<", "|", '"', "?", "*"]

EXTENSION_CATEGORIES = {
    "All Files (*)": "*",
    "Folders Only (-1)": "-1",
    "Documents & Text": [".pdf", ".docx", ".doc", ".txt", ".xlsx", ".xls", ".pptx", ".ppt", ".csv", ".rtf", ".md"],
    "Images & Graphics": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp", ".ico", ".psd"],
    "Videos": [".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".3gp", ".m4v"],
    "Audio": [".mp3", ".wav", ".aac", ".flac", ".ogg", ".m4a", ".wma"],
    "Code & Programming": [".py", ".js", ".html", ".css", ".cpp", ".c", ".cs", ".java", ".php", ".json", ".sql", ".sh", ".yaml"],
    "Archives & Compressed": [".zip", ".rar", ".7z", ".gz", ".tar", ".bz2"],
    "Custom extension (manual)": "custom"
}

# الملفات التي يمكن قراءة محتواها بأمان أثناء "Search Inside Files"
TEXT_SEARCH_EXTENSIONS = {
    ".txt", ".py", ".json", ".csv", ".md", ".log", ".xml",
    ".html", ".htm", ".css", ".js", ".cpp", ".h", ".c", ".java",
    ".yaml", ".yml", ".ini", ".cfg", ".sh"
}

# حد أقصى لحجم الملف الذي يتم قراءة محتواه (لتفادي تجميد الواجهة / استهلاك الذاكرة)
MAX_CONTENT_SEARCH_SIZE = 15 * 1024 * 1024  # 15 MB

SIZE_PRESETS = {
    "No limit": None,
    "< 1 MB": (0, 1 * 1024 * 1024),
    "1 - 10 MB": (1 * 1024 * 1024, 10 * 1024 * 1024),
    "10 - 100 MB": (10 * 1024 * 1024, 100 * 1024 * 1024),
    "> 100 MB": (100 * 1024 * 1024, None),
}

DATE_PRESETS = ["No filter", "Today", "Yesterday", "This Week", "This Month", "Custom Range"]

HISTORY_FILE = "search_history.json"
FAVORITES_FILE = "saved_searches.json"
INDEX_DB_FILE = "file_index.db"


# =====================================================================
#                    دوال مساعدة عامة (Utilities)
# =====================================================================

def format_size(size_bytes):
    """Converts file size to a human-readable format"""
    if size_bytes == 0:
        return "0 B"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"


def format_duration(seconds):
    if seconds < 1:
        return f"{seconds * 1000:.0f} ms"
    return f"{seconds:.2f} sec"


def parse_extensions(selected_category, custom_input=""):
    if selected_category == "Custom extension (manual)":
        if not custom_input.strip():
            return "*"
        exts = [e.strip() if e.strip().startswith(".") else f".{e.strip()}" for e in custom_input.split(",") if e.strip()]
        return exts if exts else "*"
    return EXTENSION_CATEGORIES.get(selected_category, "*")


def match_extension(file_name, target_exts):
    if target_exts == "*":
        return True
    if isinstance(target_exts, list):
        return any(file_name.lower().endswith(ext.lower()) for ext in target_exts)
    if isinstance(target_exts, str):
        return file_name.lower().endswith(target_exts.lower())
    return False


def get_file_info(path):
    """Retrieves file info (size and modified date)"""
    try:
        stats = os.stat(path)
        is_dir = os.path.isdir(path)
        size_str = "<Folder>" if is_dir else format_size(stats.st_size)
        mod_time = time.strftime("%Y-%m-%d %H:%M", time.localtime(stats.st_mtime))
        return size_str, mod_time
    except Exception:
        return "Unknown", "Unknown"


def get_file_info_full(path):
    """Extended file info (used in the preview panel and properties list)"""
    try:
        stats = os.stat(path)
        is_dir = os.path.isdir(path)
        size_bytes = 0 if is_dir else stats.st_size
        return {
            "name": os.path.basename(path),
            "path": path,
            "type": "Folder" if is_dir else (os.path.splitext(path)[1] or "No extension"),
            "size_bytes": size_bytes,
            "size_str": "<Folder>" if is_dir else format_size(size_bytes),
            "created": time.strftime("%Y-%m-%d %H:%M", time.localtime(stats.st_ctime)),
            "modified": time.strftime("%Y-%m-%d %H:%M", time.localtime(stats.st_mtime)),
            "is_dir": is_dir,
        }
    except Exception:
        return None


def is_hidden_file(path, name):
    """Determines whether the file/folder is hidden (supports Windows and Unix)"""
    if name.startswith("."):
        return True
    if platform.system() == "Windows":
        try:
            import ctypes
            attrs = ctypes.windll.kernel32.GetFileAttributesW(str(path))
            if attrs == -1:
                return False
            FILE_ATTRIBUTE_HIDDEN = 0x2
            return bool(attrs & FILE_ATTRIBUTE_HIDDEN)
        except Exception:
            return False
    return False


def hash_file(path, chunk_size=65536):
    """Safely computes SHA-256 for a file (reads in chunks to avoid memory overload)"""
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return None
