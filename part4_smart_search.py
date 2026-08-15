"""
Part 4 — Smart Search Parser
===========================================
تحليل استعلامات شبه طبيعية (بدون أي API خارجي) واستخراج:
- الامتدادات المطلوبة
- فلتر التاريخ
- حدود الحجم (أكبر من / أصغر من)
- كلمة البحث المتبقية

يعتمد على:
    part1_constants_utils.py  (لجلب EXTENSION_CATEGORIES)
"""

import re

from part1_constants_utils import EXTENSION_CATEGORIES


SMART_EXTENSION_KEYWORDS = {
    "pdf": [".pdf"], "python": [".py"], "word": [".docx", ".doc"],
    "excel": [".xlsx", ".xls"], "image": EXTENSION_CATEGORIES["Images & Graphics"],
    "images": EXTENSION_CATEGORIES["Images & Graphics"], "صور": EXTENSION_CATEGORIES["Images & Graphics"],
    "video": EXTENSION_CATEGORIES["Videos"], "videos": EXTENSION_CATEGORIES["Videos"],
    "فيديو": EXTENSION_CATEGORIES["Videos"], "audio": EXTENSION_CATEGORIES["Audio"],
    "mp3": [".mp3"], "zip": [".zip"], "text": [".txt"], "نصوص": [".txt"],
}

SMART_DATE_KEYWORDS = {
    "today": "Today", "Today": "Today",
    "yesterday": "Yesterday", "Yesterday": "Yesterday",
    "this week": "This Week", "This Week": "This Week",
    "this month": "This Month", "This Month": "This Month",
}


def parse_smart_query(text):
    """
    محلل بسيط لاستعلامات شبه طبيعية (لا يعتمد على أي API خارجي).
    أمثلة:
      "pdf files larger than 50mb"  -> extension=.pdf, min_size=50MB
      "python files modified this week" -> extension=.py, date=هذا الأسبوع
    """
    lowered = text.lower()
    result = {"extensions": None, "min_size": None, "max_size": None, "date_filter": None, "keyword": None}

    for key, exts in SMART_EXTENSION_KEYWORDS.items():
        if key in lowered:
            result["extensions"] = exts
            break

    for key, val in SMART_DATE_KEYWORDS.items():
        if key in lowered:
            result["date_filter"] = val
            break

    size_match = re.search(r"(larger than|bigger than|أكبر من|>)\s*(\d+(?:\.\d+)?)\s*(mb|kb|gb)", lowered)
    if size_match:
        value, unit = float(size_match.group(2)), size_match.group(3)
        multiplier = {"kb": 1024, "mb": 1024 ** 2, "gb": 1024 ** 3}[unit]
        result["min_size"] = int(value * multiplier)

    size_match2 = re.search(r"(smaller than|less than|أصغر من|<)\s*(\d+(?:\.\d+)?)\s*(mb|kb|gb)", lowered)
    if size_match2:
        value, unit = float(size_match2.group(2)), size_match2.group(3)
        multiplier = {"kb": 1024, "mb": 1024 ** 2, "gb": 1024 ** 3}[unit]
        result["max_size"] = int(value * multiplier)

    # الكلمة المتبقية (بعد إزالة الكلمات المفتاحية) تُستخدم كاسم بحث اختياري
    cleaned = lowered
    for key in list(SMART_EXTENSION_KEYWORDS) + list(SMART_DATE_KEYWORDS) + ["files", "file", "Files", "modified"]:
        cleaned = cleaned.replace(key, " ")
    if size_match:
        cleaned = cleaned.replace(size_match.group(0), " ")
    if size_match2:
        cleaned = cleaned.replace(size_match2.group(0), " ")
    cleaned = cleaned.strip()
    result["keyword"] = cleaned if cleaned else "*"

    return result
