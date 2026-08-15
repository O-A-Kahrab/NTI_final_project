"""
Part 3 — Core Search Engine
===========================================
يحتوي هذا الملف على محرك البحث الرئيسي:
- search_files            : البحث الأساسي عن ملفات/مجلدات
- find_similar_files      : البحث عن ملفات مشابهة لملف معين
- find_duplicate_files    : البحث عن الملفات المكررة (بالحجم ثم SHA-256)

يعتمد على:
    part1_constants_utils.py
    part2_predicates_filters.py
"""

import os
import re

from part1_constants_utils import get_file_info_full, hash_file
from part2_predicates_filters import (
    build_name_predicate,
    content_search_match,
    passes_size_filter,
    passes_date_filter,
)


def search_files(file_name, target_exts, directory, exact_match, stop_event,
                  subfolders=True, include_hidden=False, case_sensitive=False,
                  use_wildcard=False, use_regex=False, search_content=False,
                  min_size=None, max_size=None, date_filter=None,
                  custom_date_start=None, custom_date_end=None,
                  item_kind=None, progress_callback=None):
    """
    محرك البحث الأساسي (تم تطويره تدريجيًا من النسخة الأصلية).
    يحافظ على نفس التوقيع الأساسي القديم مع إضافة معاملات اختيارية جديدة
    حتى لا ينكسر أي استدعاء قديم للدالة.
    """
    # تحديد نوع العنصر المطلوب: ملف / مجلد / كلاهما
    if item_kind is None:
        is_folder_only = (target_exts == "-1")
        item_kind = "folder" if is_folder_only else "file"

    def match_extension(file_name_, target_exts_):
        if target_exts_ == "*":
            return True
        if isinstance(target_exts_, list):
            return any(file_name_.lower().endswith(ext.lower()) for ext in target_exts_)
        if isinstance(target_exts_, str):
            return file_name_.lower().endswith(target_exts_.lower())
        return False

    def is_hidden_file(path, name):
        if name.startswith("."):
            return True
        import platform
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

    matches = []
    scanned = 0

    regex_pattern = None
    if use_regex:
        try:
            regex_pattern = re.compile(file_name, 0 if case_sensitive else re.IGNORECASE)
        except re.error:
            regex_pattern = None

    name_predicate, error = build_name_predicate(file_name, exact_match, use_wildcard, use_regex, case_sensitive)
    if error:
        # يُعاد استخدامه من الواجهة لعرض رسالة خطأ واضحة بدلاً من الانهيار
        raise ValueError(error)

    for root, dirs, files in os.walk(directory, topdown=True):
        if stop_event.is_set():
            break

        # استبعاد المجلدات المخفية إن لم يُطلب البحث فيها
        if not include_hidden:
            dirs[:] = [d for d in dirs if not is_hidden_file(os.path.join(root, d), d)]

        # التحكم في البحث داخل المجلدات الفرعية
        if not subfolders:
            dirs[:] = []

        candidate_items = []
        if item_kind in ("file", "both"):
            candidate_items.extend([(f, False) for f in files])
        if item_kind in ("folder", "both"):
            candidate_items.extend([(d, True) for d in dirs])

        for item, is_dir in candidate_items:
            if stop_event.is_set():
                break

            scanned += 1
            if progress_callback and scanned % 100 == 0:
                progress_callback(scanned, len(matches), root)

            if not include_hidden and is_hidden_file(os.path.join(root, item), item):
                continue

            full_path = os.path.join(root, item)
            name_matched = name_predicate(item)
            content_matched = False

            if not is_dir and search_content and not name_matched:
                content_matched = content_search_match(full_path, file_name, case_sensitive, use_regex, regex_pattern)

            matched = name_matched or content_matched
            if not matched:
                continue

            if not is_dir and not match_extension(item, target_exts):
                continue

            if not is_dir:
                try:
                    size_bytes = os.path.getsize(full_path)
                    mtime = os.path.getmtime(full_path)
                except OSError:
                    continue

                if not passes_size_filter(size_bytes, min_size, max_size):
                    continue
                if not passes_date_filter(mtime, date_filter, custom_date_start, custom_date_end):
                    continue

            matches.append(full_path)

    if progress_callback:
        progress_callback(scanned, len(matches), directory)

    return matches


def find_similar_files(reference_path, search_root, stop_event, by_name=True, by_extension=True, by_size=True, size_tolerance=0.2):
    """Searches for files similar to a given file based on name / extension / approximate size"""
    ref_info = get_file_info_full(reference_path)
    if not ref_info or ref_info["is_dir"]:
        return []

    ref_name_no_ext = os.path.splitext(ref_info["name"])[0].lower()
    ref_ext = os.path.splitext(ref_info["name"])[1].lower()
    ref_size = ref_info["size_bytes"]

    results = []
    for root, dirs, files in os.walk(search_root):
        if stop_event.is_set():
            break
        for f in files:
            full_path = os.path.join(root, f)
            if full_path == reference_path:
                continue

            score = 0
            name_no_ext, ext = os.path.splitext(f)
            if by_extension and ext.lower() == ref_ext:
                score += 1
            if by_name and ref_name_no_ext in name_no_ext.lower():
                score += 1
            if by_size:
                try:
                    size = os.path.getsize(full_path)
                    if ref_size > 0 and abs(size - ref_size) / max(ref_size, 1) <= size_tolerance:
                        score += 1
                except OSError:
                    pass

            if score >= 1:
                results.append(full_path)

    return results


def find_duplicate_files(directories, stop_event, progress_callback=None):
    """
    يبحث عن الملفات المكررة:
    1) تجميع أولي حسب الحجم (سريع)
    2) مقارنة نهائية باستخدام SHA-256 لكل مجموعة محتملة
    يرجع dict: { hash: [path1, path2, ...] } للمجموعات التي تحتوي على أكثر من ملف فعلاً
    """
    size_groups = {}
    scanned = 0

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
                    size = os.path.getsize(full_path)
                except OSError:
                    continue
                scanned += 1
                if progress_callback and scanned % 100 == 0:
                    progress_callback(scanned, root)
                size_groups.setdefault(size, []).append(full_path)

    hash_groups = {}
    for size, paths in size_groups.items():
        if len(paths) < 2 or size == 0:
            continue
        for p in paths:
            if stop_event.is_set():
                break
            file_hash = hash_file(p)
            if file_hash:
                hash_groups.setdefault(file_hash, []).append(p)

    return {h: paths for h, paths in hash_groups.items() if len(paths) > 1}
