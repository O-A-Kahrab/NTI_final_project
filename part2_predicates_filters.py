"""
Part 2 — Matching Predicates & Filters
===========================================
يحتوي هذا الملف على منطق مطابقة الاسم/المحتوى، وفلاتر الحجم والتاريخ.

يعتمد على:
    part1_constants_utils.py  (لجلب TEXT_SEARCH_EXTENSIONS و MAX_CONTENT_SEARCH_SIZE)
"""

import os
import re
import fnmatch
import datetime as dt

from part1_constants_utils import TEXT_SEARCH_EXTENSIONS, MAX_CONTENT_SEARCH_SIZE


def build_name_predicate(query, exact_match, use_wildcard, use_regex, case_sensitive):
    """
    يبني دالة (predicate) تقارن اسم الملف بمعيار البحث حسب الخيارات المحددة:
    - Regex
    - Wildcards (*.py)
    - بحث دقيق / بحث جزئي
    ترجع (predicate, error) حيث error نص خطأ في حال فشل تجميع Regex
    """
    # اسم بحث فارغ = عرض كل الملفات (يُطبَّق فلتر الامتداد لاحقًا بشكل منفصل)
    if not query.strip():
        return (lambda name: True), None

    if use_regex:
        try:
            flags = 0 if case_sensitive else re.IGNORECASE
            pattern = re.compile(query, flags)
        except re.error as e:
            return None, f"Invalid regex pattern: {e}"

        def predicate(name):
            return bool(pattern.search(name))
        return predicate, None

    if use_wildcard or "*" in query or "?" in query:
        pattern = re.compile(fnmatch.translate(query), 0 if case_sensitive else re.IGNORECASE)

        def predicate(name):
            return bool(pattern.match(name))
        return predicate, None

    q = query if case_sensitive else query.lower()

    def predicate(name):
        target = name if case_sensitive else name.lower()
        name_no_ext, _ = os.path.splitext(target)
        if exact_match:
            return target == q or name_no_ext == q
        return q in target

    return predicate, None


def content_search_match(path, query, case_sensitive, use_regex, regex_pattern=None):
    """
    بحث آمن داخل محتوى الملف. لا يحاول قراءة الملفات الثنائية أو الضخمة.
    يرجع True/False فقط، ولا يوقف البرنامج عند حدوث أخطاء.
    """
    try:
        ext = os.path.splitext(path)[1].lower()
        if ext not in TEXT_SEARCH_EXTENSIONS:
            return False
        if os.path.getsize(path) > MAX_CONTENT_SEARCH_SIZE:
            return False

        # فحص سريع لتفادي قراءة ملفات ثنائية بالخطأ (تحقق من وجود بايتات null)
        with open(path, "rb") as fb:
            chunk = fb.read(2048)
            if b"\x00" in chunk:
                return False

        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        if use_regex and regex_pattern is not None:
            return bool(regex_pattern.search(content))

        if not case_sensitive:
            content = content.lower()
            query = query.lower()
        return query in content
    except Exception:
        return False


def passes_size_filter(size_bytes, min_size, max_size):
    if min_size is not None and size_bytes < min_size:
        return False
    if max_size is not None and size_bytes > max_size:
        return False
    return True


def passes_date_filter(mtime_ts, date_filter, custom_start=None, custom_end=None):
    if not date_filter or date_filter == "No filter":
        return True

    file_date = dt.date.fromtimestamp(mtime_ts)
    today = dt.date.today()

    if date_filter == "Today":
        return file_date == today
    if date_filter == "Yesterday":
        return file_date == today - dt.timedelta(days=1)
    if date_filter == "This Week":
        start_of_week = today - dt.timedelta(days=today.weekday())
        return start_of_week <= file_date <= today
    if date_filter == "This Month":
        return file_date.year == today.year and file_date.month == today.month
    if date_filter == "Custom Range":
        if custom_start and file_date < custom_start:
            return False
        if custom_end and file_date > custom_end:
            return False
        return True
    return True
