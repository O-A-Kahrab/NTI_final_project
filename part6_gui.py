"""
Part 6 — GUI (Tkinter)
===========================================
هذا الملف يحتوي على الواجهة الرسومية فقط (AdvancedSearchApp) ونقطة
تشغيل البرنامج. يعتمد على كل الأجزاء الخمسة السابقة لتوفير منطق
البحث والفهرسة والسجل/المفضلة.
"""

import os
import time
import platform
import subprocess
import threading
import datetime as dt
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog

try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except Exception:
    PIL_AVAILABLE = False

try:
    from send2trash import send2trash
    SEND2TRASH_AVAILABLE = True
except Exception:
    SEND2TRASH_AVAILABLE = False

from part1_constants_utils import (
    INVALID_NAME_CHARS, EXTENSION_CATEGORIES, TEXT_SEARCH_EXTENSIONS,
    MAX_CONTENT_SEARCH_SIZE, SIZE_PRESETS, DATE_PRESETS,
    format_size, format_duration, parse_extensions, get_file_info, get_file_info_full,
)
from part3_search_engine import search_files, find_similar_files, find_duplicate_files
from part4_smart_search import parse_smart_query
from part5_index_history import (
    FileIndexDB, save_to_history, load_history_entries, append_history_entry,
    clear_history_entries, load_favorites, save_favorites,
)


# =====================================================================
#                         تطبيق الواجهة الرسومية
#                          (GUI - Tkinter)
# =====================================================================

class AdvancedSearchApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Advanced File and Folder Search Engine - Professional Edition")
        self.root.geometry("1200x760")
        self.root.minsize(1000, 650)

        self.style = ttk.Style()
        self.style.theme_use('clam')

        self.last_results = []
        self.last_query = ""
        self.stop_event = threading.Event()
        self.index_stop_event = threading.Event()

        self.sort_state = {}  # column -> reverse(bool)
        self.search_start_time = None
        self.index_db = FileIndexDB()

        self.filters_visible = False
        self.preview_visible = True

        self.create_widgets()
        self.create_context_menu()

    # ---------------------------------------------------------------
    #                       بناء الواجهة
    # ---------------------------------------------------------------
    def create_widgets(self):
        input_frame = ttk.LabelFrame(self.root, text=" Search Criteria ", padding=15)
        input_frame.pack(fill="x", padx=15, pady=(10, 5))

        ttk.Label(input_frame, text="File / Folder Name:").grid(row=0, column=0, sticky="w", pady=5)
        self.entry_filename = ttk.Entry(input_frame, width=40)
        self.entry_filename.grid(row=0, column=1, columnspan=2, sticky="ew", pady=5, padx=5)
        self.entry_filename.bind("<Return>", lambda e: self.start_search_thread())

        ttk.Label(input_frame, text="Search Type:").grid(row=1, column=0, sticky="w", pady=5)
        self.search_mode_var = tk.StringVar(value="0")

        radio_frame = ttk.Frame(input_frame)
        radio_frame.grid(row=1, column=1, sticky="w", pady=5)
        ttk.Radiobutton(radio_frame, text="Exact Search", variable=self.search_mode_var, value="1").pack(side="left", padx=5)
        ttk.Radiobutton(radio_frame, text="Advanced Search", variable=self.search_mode_var, value="0").pack(side="left", padx=10)

        ttk.Label(input_frame, text="Category / Filter:").grid(row=2, column=0, sticky="w", pady=5)
        self.combo_category = ttk.Combobox(input_frame, values=list(EXTENSION_CATEGORIES.keys()), state="readonly", width=22)
        self.combo_category.set("All Files (*)")
        self.combo_category.grid(row=2, column=1, sticky="w", pady=5, padx=5)
        self.combo_category.bind("<<ComboboxSelected>>", self.on_category_change)

        self.entry_custom_ext = ttk.Entry(input_frame, width=15, state="disabled")
        self.entry_custom_ext.grid(row=2, column=2, sticky="w", pady=5, padx=5)

        ttk.Label(input_frame, text="Folders (separate with | or ,):").grid(row=3, column=0, sticky="w", pady=5)
        self.entry_dirs = ttk.Entry(input_frame, width=40)
        self.entry_dirs.grid(row=3, column=1, sticky="ew", pady=5, padx=5)

        btn_browse = ttk.Button(input_frame, text="Browse...", command=self.browse_directory)
        btn_browse.grid(row=3, column=2, pady=5, padx=5)

        # ---- صف البحث الذكي ----
        ttk.Label(input_frame, text="Smart Search (optional):").grid(row=4, column=0, sticky="w", pady=5)
        self.entry_smart = ttk.Entry(input_frame, width=40)
        self.entry_smart.grid(row=4, column=1, sticky="ew", pady=5, padx=5)
        ttk.Button(input_frame, text="Analyze & Apply", command=self.apply_smart_search).grid(row=4, column=2, pady=5, padx=5)

        btn_frame = ttk.Frame(input_frame)
        btn_frame.grid(row=5, column=0, columnspan=3, pady=10)

        self.btn_search = ttk.Button(btn_frame, text="Start Search 🔍", command=self.start_search_thread)
        self.btn_search.pack(side="left", padx=5)

        self.btn_stop = ttk.Button(btn_frame, text="Stop 🛑", command=self.stop_search, state="disabled")
        self.btn_stop.pack(side="left", padx=5)

        self.btn_toggle_filters = ttk.Button(btn_frame, text="Advanced Filters ▾", command=self.toggle_filters)
        self.btn_toggle_filters.pack(side="left", padx=5)

        self.btn_save_history = ttk.Button(btn_frame, text="Save Results (JSON)", command=self.save_search_history)
        self.btn_save_history.pack(side="left", padx=5)

        ttk.Button(btn_frame, text="History 🕓", command=self.open_history_window).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Favorites ⭐", command=self.open_favorites_window).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Save as Favorite Search", command=self.save_current_as_favorite).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Duplicate Files 🧬", command=self.open_duplicates_window).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Indexing 🗂", command=self.open_index_window).pack(side="left", padx=5)

        input_frame.columnconfigure(1, weight=1)

        # ---- لوحة الفلاتر المتقدمة (قابلة للطي) ----
        self.filters_frame = ttk.LabelFrame(self.root, text=" Advanced Filters ", padding=12)
        self._build_filters_panel(self.filters_frame)
        # لا يتم عرضها إلا عند الضغط على الزر (pack عند الحاجة فقط)

        # ---- شريط الحالة والتقدم ----
        status_bar = ttk.Frame(self.root)
        status_bar.pack(fill="x", padx=15, pady=(5, 0))

        self.status_var = tk.StringVar(value="Ready to search...")
        self.status_label = ttk.Label(status_bar, textvariable=self.status_var, font=("Arial", 10, "italic"))
        self.status_label.pack(side="left")

        self.stats_var = tk.StringVar(value="")
        ttk.Label(status_bar, textvariable=self.stats_var, font=("Arial", 9)).pack(side="right")

        progress_frame = ttk.Frame(self.root)
        progress_frame.pack(fill="x", padx=15, pady=(2, 8))

        self.progress = ttk.Progressbar(progress_frame, mode="indeterminate")
        self.progress.pack(fill="x", side="top")

        scan_info_frame = ttk.Frame(progress_frame)
        scan_info_frame.pack(fill="x", pady=(3, 0))
        self.scanned_var = tk.StringVar(value="")
        ttk.Label(scan_info_frame, textvariable=self.scanned_var, font=("Arial", 8)).pack(side="left")
        self.current_path_var = tk.StringVar(value="")
        ttk.Label(scan_info_frame, textvariable=self.current_path_var, font=("Arial", 8)).pack(side="right")

        # ---- منطقة المحتوى: النتائج + المعاينة ----
        content_frame = ttk.Frame(self.root)
        content_frame.pack(fill="both", expand=True, padx=15, pady=5)

        results_frame = ttk.LabelFrame(content_frame, text=" Search Results ", padding=10)
        results_frame.pack(side="left", fill="both", expand=True)

        columns = ("type", "name", "size", "mtime", "path")
        self.tree = ttk.Treeview(results_frame, columns=columns, show="headings", selectmode="extended")

        headers = {"type": "Type", "name": "Name", "size": "Size", "mtime": "Last Modified", "path": "Full Path"}
        widths = {"type": 70, "name": 180, "size": 90, "mtime": 130, "path": 340}
        for col in columns:
            self.tree.heading(col, text=headers[col], command=lambda c=col: self.sort_by_column(c))
            self.tree.column(col, width=widths[col], anchor="center" if col != "name" and col != "path" else "w")

        scrollbar_y = ttk.Scrollbar(results_frame, orient="vertical", command=self.tree.yview)
        scrollbar_x = ttk.Scrollbar(results_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscroll=scrollbar_y.set, xscroll=scrollbar_x.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar_y.grid(row=0, column=1, sticky="ns")
        scrollbar_x.grid(row=1, column=0, sticky="ew")

        results_frame.rowconfigure(0, weight=1)
        results_frame.columnconfigure(0, weight=1)

        self.tree.bind("<Double-1>", self.open_selected_item)
        self.tree.bind("<Button-3>", self.show_context_menu)   # Windows/Linux
        self.tree.bind("<Button-2>", self.show_context_menu)   # macOS
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)

        # ---- لوحة المعاينة ----
        self.preview_frame = ttk.LabelFrame(content_frame, text=" Preview ", padding=10, width=320)
        self.preview_frame.pack(side="right", fill="y", padx=(10, 0))
        self.preview_frame.pack_propagate(False)
        self._build_preview_panel(self.preview_frame)

    def _build_filters_panel(self, parent):
        # صف: نوع العنصر + خيارات عامة
        options_frame = ttk.Frame(parent)
        options_frame.pack(fill="x", pady=(0, 8))

        self.var_subfolders = tk.BooleanVar(value=True)
        self.var_hidden = tk.BooleanVar(value=False)
        self.var_case_sensitive = tk.BooleanVar(value=False)
        self.var_search_content = tk.BooleanVar(value=False)
        self.var_use_regex = tk.BooleanVar(value=False)
        self.var_use_wildcard = tk.BooleanVar(value=False)

        ttk.Checkbutton(options_frame, text="Search in subfolders", variable=self.var_subfolders).pack(side="left", padx=6)
        ttk.Checkbutton(options_frame, text="Include hidden files", variable=self.var_hidden).pack(side="left", padx=6)
        ttk.Checkbutton(options_frame, text="Case sensitive", variable=self.var_case_sensitive).pack(side="left", padx=6)
        ttk.Checkbutton(options_frame, text="Search inside file contents", variable=self.var_search_content).pack(side="left", padx=6)
        ttk.Checkbutton(options_frame, text="Use Regex", variable=self.var_use_regex).pack(side="left", padx=6)
        ttk.Checkbutton(options_frame, text="Use Wildcards (*.py)", variable=self.var_use_wildcard).pack(side="left", padx=6)

        item_kind_frame = ttk.Frame(parent)
        item_kind_frame.pack(fill="x", pady=(0, 8))
        ttk.Label(item_kind_frame, text="Search for:").pack(side="left", padx=(0, 6))
        self.var_item_kind = tk.StringVar(value="file")
        ttk.Radiobutton(item_kind_frame, text="Files Only", variable=self.var_item_kind, value="file").pack(side="left", padx=5)
        ttk.Radiobutton(item_kind_frame, text="Folders Only", variable=self.var_item_kind, value="folder").pack(side="left", padx=5)
        ttk.Radiobutton(item_kind_frame, text="Both", variable=self.var_item_kind, value="both").pack(side="left", padx=5)

        # صف الحجم
        size_frame = ttk.Frame(parent)
        size_frame.pack(fill="x", pady=(0, 8))
        ttk.Label(size_frame, text="Size:").pack(side="left", padx=(0, 6))
        ttk.Label(size_frame, text="Min (MB):").pack(side="left")
        self.entry_min_size = ttk.Entry(size_frame, width=8)
        self.entry_min_size.pack(side="left", padx=(2, 10))
        ttk.Label(size_frame, text="Max (MB):").pack(side="left")
        self.entry_max_size = ttk.Entry(size_frame, width=8)
        self.entry_max_size.pack(side="left", padx=(2, 10))
        ttk.Label(size_frame, text="Presets:").pack(side="left", padx=(10, 4))
        self.combo_size_preset = ttk.Combobox(size_frame, values=list(SIZE_PRESETS.keys()), state="readonly", width=14)
        self.combo_size_preset.set("No limit")
        self.combo_size_preset.pack(side="left")
        self.combo_size_preset.bind("<<ComboboxSelected>>", self.apply_size_preset)

        # صف التاريخ
        date_frame = ttk.Frame(parent)
        date_frame.pack(fill="x")
        ttk.Label(date_frame, text="Date:").pack(side="left", padx=(0, 6))
        self.combo_date_filter = ttk.Combobox(date_frame, values=DATE_PRESETS, state="readonly", width=15)
        self.combo_date_filter.set("No filter")
        self.combo_date_filter.pack(side="left", padx=(0, 10))
        self.combo_date_filter.bind("<<ComboboxSelected>>", self.on_date_filter_change)

        ttk.Label(date_frame, text="From (YYYY-MM-DD):").pack(side="left")
        self.entry_date_start = ttk.Entry(date_frame, width=12, state="disabled")
        self.entry_date_start.pack(side="left", padx=(2, 10))
        ttk.Label(date_frame, text="To (YYYY-MM-DD):").pack(side="left")
        self.entry_date_end = ttk.Entry(date_frame, width=12, state="disabled")
        self.entry_date_end.pack(side="left", padx=(2, 0))

    def _build_preview_panel(self, parent):
        self.preview_info_var = tk.StringVar(value="Select a file to preview it here.")
        info_label = ttk.Label(parent, textvariable=self.preview_info_var, justify="right", wraplength=290, font=("Arial", 9))
        info_label.pack(fill="x", pady=(0, 8))

        self.preview_container = ttk.Frame(parent)
        self.preview_container.pack(fill="both", expand=True)

        self.preview_image_label = ttk.Label(self.preview_container)
        self.preview_text = tk.Text(self.preview_container, wrap="none", font=("Consolas", 9), state="disabled")
        preview_scroll = ttk.Scrollbar(self.preview_container, orient="vertical", command=self.preview_text.yview)
        self.preview_text.configure(yscrollcommand=preview_scroll.set)
        self._preview_scroll = preview_scroll

    # ---------------------------------------------------------------
    #                     تفعيل / إخفاء الفلاتر
    # ---------------------------------------------------------------
    def toggle_filters(self):
        if self.filters_visible:
            self.filters_frame.pack_forget()
            self.btn_toggle_filters.config(text="Advanced Filters ▾")
        else:
            self.filters_frame.pack(fill="x", padx=15, pady=(0, 5), after=self.root.pack_slaves()[0])
            self.btn_toggle_filters.config(text="Advanced Filters ▴")
        self.filters_visible = not self.filters_visible

    def apply_size_preset(self, event=None):
        preset = SIZE_PRESETS.get(self.combo_size_preset.get())
        self.entry_min_size.delete(0, tk.END)
        self.entry_max_size.delete(0, tk.END)
        if preset:
            min_b, max_b = preset
            if min_b is not None:
                self.entry_min_size.insert(0, str(min_b / (1024 * 1024)))
            if max_b is not None:
                self.entry_max_size.insert(0, str(max_b / (1024 * 1024)))

    def on_date_filter_change(self, event=None):
        if self.combo_date_filter.get() == "Custom Range":
            self.entry_date_start.config(state="normal")
            self.entry_date_end.config(state="normal")
        else:
            self.entry_date_start.config(state="disabled")
            self.entry_date_end.config(state="disabled")

    def on_category_change(self, event):
        if self.combo_category.get() == "Custom extension (manual)":
            self.entry_custom_ext.config(state="normal")
            self.entry_custom_ext.focus()
        else:
            self.entry_custom_ext.delete(0, tk.END)
            self.entry_custom_ext.config(state="disabled")

    def browse_directory(self):
        folder = filedialog.askdirectory()
        if folder:
            folder = os.path.normpath(folder)
            current = self.entry_dirs.get().strip()
            if current:
                self.entry_dirs.delete(0, tk.END)
                self.entry_dirs.insert(0, f"{current} | {folder}")
            else:
                self.entry_dirs.insert(0, folder)

    # ---------------------------------------------------------------
    #                       البحث الذكي
    # ---------------------------------------------------------------
    def apply_smart_search(self):
        text = self.entry_smart.get().strip()
        if not text:
            messagebox.showwarning("Notice", "Please enter a smart search query first.")
            return

        parsed = parse_smart_query(text)

        self.entry_filename.delete(0, tk.END)
        self.entry_filename.insert(0, parsed["keyword"] if parsed["keyword"] not in ("", "*") else "")

        if parsed["extensions"]:
            self.combo_category.set("Custom extension (manual)")
            self.entry_custom_ext.config(state="normal")
            self.entry_custom_ext.delete(0, tk.END)
            self.entry_custom_ext.insert(0, ",".join(parsed["extensions"]))

        if not self.filters_visible:
            self.toggle_filters()

        if parsed["min_size"] is not None:
            self.entry_min_size.delete(0, tk.END)
            self.entry_min_size.insert(0, str(parsed["min_size"] / (1024 * 1024)))
        if parsed["max_size"] is not None:
            self.entry_max_size.delete(0, tk.END)
            self.entry_max_size.insert(0, str(parsed["max_size"] / (1024 * 1024)))
        if parsed["date_filter"]:
            self.combo_date_filter.set(parsed["date_filter"])
            self.on_date_filter_change()

        messagebox.showinfo("Smart Search", "The extracted filters have been applied. Click 'Start Search' to continue.")

    # ---------------------------------------------------------------
    #                       التحقق من المدخلات
    # ---------------------------------------------------------------
    def validate_inputs(self):
        file_name = self.entry_filename.get().strip()
        selected_cat = self.combo_category.get()
        custom_ext = self.entry_custom_ext.get()
        directories_str = self.entry_dirs.get().strip()

        use_regex = self.var_use_regex.get() if hasattr(self, "var_use_regex") else False
        use_wildcard = self.var_use_wildcard.get() if hasattr(self, "var_use_wildcard") else False

        # اسم البحث أصبح اختياريًا: تركه فارغًا يعرض كل الملفات (مع تطبيق الفلاتر المحددة مثل الامتداد)
        if not file_name and not use_regex and not use_wildcard:
            for char in file_name:
                if char in INVALID_NAME_CHARS:
                    messagebox.showerror("Invalid Name", f"The following characters cannot be used in the name:\n{INVALID_NAME_CHARS}")
                    return None

        if not directories_str:
            messagebox.showwarning("Notice", "Please select at least one folder.")
            return None

        raw_dirs = directories_str.replace("|", ",").split(",")
        dirs_list = [os.path.normpath(d.strip()) for d in raw_dirs if d.strip()]
        invalid_dirs = [d for d in dirs_list if not os.path.isdir(d)]

        if invalid_dirs:
            messagebox.showerror("Invalid Folder", f"The following folders are invalid:\n{invalid_dirs}")
            return None

        target_exts = parse_extensions(selected_cat, custom_ext)
        return file_name, target_exts, dirs_list

    def _collect_filter_options(self):
        """Collects all current advanced filter options from the UI (with safe defaults)"""
        min_size = None
        max_size = None
        try:
            if hasattr(self, "entry_min_size") and self.entry_min_size.get().strip():
                min_size = int(float(self.entry_min_size.get().strip()) * 1024 * 1024)
        except ValueError:
            pass
        try:
            if hasattr(self, "entry_max_size") and self.entry_max_size.get().strip():
                max_size = int(float(self.entry_max_size.get().strip()) * 1024 * 1024)
        except ValueError:
            pass

        date_filter = self.combo_date_filter.get() if hasattr(self, "combo_date_filter") else "No filter"
        custom_start = custom_end = None
        if date_filter == "Custom Range":
            try:
                if self.entry_date_start.get().strip():
                    custom_start = dt.datetime.strptime(self.entry_date_start.get().strip(), "%Y-%m-%d").date()
                if self.entry_date_end.get().strip():
                    custom_end = dt.datetime.strptime(self.entry_date_end.get().strip(), "%Y-%m-%d").date()
            except ValueError:
                messagebox.showwarning("Notice", "Invalid custom date format; the date range will be ignored.")

        return {
            "subfolders": self.var_subfolders.get() if hasattr(self, "var_subfolders") else True,
            "include_hidden": self.var_hidden.get() if hasattr(self, "var_hidden") else False,
            "case_sensitive": self.var_case_sensitive.get() if hasattr(self, "var_case_sensitive") else False,
            "search_content": self.var_search_content.get() if hasattr(self, "var_search_content") else False,
            "use_regex": self.var_use_regex.get() if hasattr(self, "var_use_regex") else False,
            "use_wildcard": self.var_use_wildcard.get() if hasattr(self, "var_use_wildcard") else False,
            "item_kind": self.var_item_kind.get() if hasattr(self, "var_item_kind") else "file",
            "min_size": min_size,
            "max_size": max_size,
            "date_filter": date_filter,
            "custom_date_start": custom_start,
            "custom_date_end": custom_end,
        }

    # ---------------------------------------------------------------
    #                       تنفيذ البحث (Threaded)
    # ---------------------------------------------------------------
    def start_search_thread(self):
        valid_data = self.validate_inputs()
        if not valid_data:
            return

        file_name, target_exts, dirs_list = valid_data
        exact_match = (self.search_mode_var.get() == "1")
        options = self._collect_filter_options()

        for item in self.tree.get_children():
            self.tree.delete(item)
        self._clear_preview()

        self.stop_event.clear()
        self.btn_search.config(state="disabled")
        self.btn_stop.config(state="normal")
        self.progress.config(mode="indeterminate")
        self.progress.start(10)
        self.status_var.set("Searching selected folders...")
        self.stats_var.set("")
        self.search_start_time = time.time()

        thread = threading.Thread(
            target=self.run_search,
            args=(file_name, target_exts, dirs_list, exact_match, options),
            daemon=True
        )
        thread.start()

    def stop_search(self):
        self.stop_event.set()
        self.status_var.set("Stopping the operation...")

    def _on_search_progress(self, scanned, found, current_path):
        # يُستدعى من خيط البحث؛ يجب تمرير التحديث لخيط الواجهة عبر after()
        def update():
            self.scanned_var.set(f"Scanned: {scanned:,} item(s)")
            self.current_path_var.set(current_path if len(current_path) < 60 else "..." + current_path[-57:])
        self.root.after(0, update)

    def run_search(self, file_name, target_exts, dirs_list, exact_match, options):
        found_directories = []
        error_message = None

        try:
            for directory in dirs_list:
                if self.stop_event.is_set():
                    break
                res = search_files(
                    file_name, target_exts, directory, exact_match, self.stop_event,
                    progress_callback=self._on_search_progress,
                    **options
                )
                found_directories.extend(res)
        except ValueError as e:
            error_message = str(e)

        self.root.after(0, self.finish_search, found_directories, file_name, error_message)

    def finish_search(self, found_directories, query, error_message=None):
        self.progress.stop()
        self.btn_search.config(state="normal")
        self.btn_stop.config(state="disabled")
        self.last_results = found_directories
        self.last_query = query

        if error_message:
            self.status_var.set("An error occurred in the search pattern.")
            messagebox.showerror("Search Error", error_message)
            return

        duration = time.time() - self.search_start_time if self.search_start_time else 0

        if self.stop_event.is_set():
            self.status_var.set(f"Search stopped! Found {len(found_directories)} result(s) before stopping.")
        elif not found_directories:
            self.status_var.set("No results found.")
        else:
            self.status_var.set(f"Search complete: found {len(found_directories)} result(s).")

        total_size = 0
        for path in found_directories:
            item_type = "Folder" if os.path.isdir(path) else "File"
            name = os.path.basename(path)
            size_str, mod_time = get_file_info(path)
            if item_type == "File":
                try:
                    total_size += os.path.getsize(path)
                except OSError:
                    pass
            self.tree.insert("", "end", values=(item_type, name, size_str, mod_time, path))

        self.stats_var.set(
            f"{len(found_directories)} results  •  {format_duration(duration)}  •  {format_size(total_size)}"
        )

        if found_directories:
            save_to_history(query, found_directories)

        append_history_entry({
            "query": query,
            "timestamp": dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "results_count": len(found_directories),
            "directories": self.entry_dirs.get(),
            "category": self.combo_category.get(),
            "custom_ext": self.entry_custom_ext.get(),
            "exact_match": self.search_mode_var.get(),
        })

    # ---------------------------------------------------------------
    #                     ترتيب النتائج (Sorting)
    # ---------------------------------------------------------------
    def sort_by_column(self, col):
        items = [(self.tree.set(k, col), k) for k in self.tree.get_children("")]
        reverse = self.sort_state.get(col, False)

        if col == "size":
            def size_key(v):
                text = v[0]
                if text == "<Folder>" or text == "Unknown":
                    return -1
                try:
                    num, unit = text.split()
                    mult = {"B": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3, "TB": 1024**4, "PB": 1024**5}
                    return float(num) * mult.get(unit, 1)
                except Exception:
                    return 0
            items.sort(key=size_key, reverse=reverse)
        else:
            items.sort(key=lambda v: v[0].lower() if isinstance(v[0], str) else v[0], reverse=reverse)

        for index, (_, k) in enumerate(items):
            self.tree.move(k, "", index)

        self.sort_state[col] = not reverse

    # ---------------------------------------------------------------
    #                     المعاينة (Preview Panel)
    # ---------------------------------------------------------------
    def on_tree_select(self, event):
        selected = self.tree.selection()
        if len(selected) != 1:
            self._clear_preview()
            return
        item_data = self.tree.item(selected[0])
        full_path = item_data['values'][4]
        self.show_preview(full_path)

    def _clear_preview(self):
        self.preview_info_var.set("Select a file to preview it here.")
        self.preview_image_label.pack_forget()
        self.preview_text.pack_forget()
        self._preview_scroll.pack_forget()

    def show_preview(self, path):
        info = get_file_info_full(path)
        if not info:
            self._clear_preview()
            return

        self.preview_info_var.set(
            f"Name: {info['name']}\n"
            f"Type: {info['type']}\n"
            f"Size: {info['size_str']}\n"
            f"Created: {info['created']}\n"
            f"Modified: {info['modified']}\n"
            f"Path: {info['path']}"
        )

        self.preview_image_label.pack_forget()
        self.preview_text.pack_forget()
        self._preview_scroll.pack_forget()

        if info["is_dir"]:
            return

        ext = os.path.splitext(path)[1].lower()
        image_exts = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}

        if ext in image_exts and PIL_AVAILABLE:
            try:
                img = Image.open(path)
                img.thumbnail((280, 280))
                photo = ImageTk.PhotoImage(img)
                self.preview_image_label.configure(image=photo, text="")
                self.preview_image_label.image = photo  # الاحتفاظ بمرجع لتفادي الحذف من الذاكرة
                self.preview_image_label.pack(pady=5)
            except Exception:
                self.preview_info_var.set(self.preview_info_var.get() + "\n\n(Failed to load image preview)")
        elif ext in image_exts and not PIL_AVAILABLE:
            self.preview_info_var.set(self.preview_info_var.get() + "\n\n(To preview images, install the Pillow library: pip install pillow)")
        elif ext in TEXT_SEARCH_EXTENSIONS:
            self.preview_text.pack(side="left", fill="both", expand=True)
            self._preview_scroll.pack(side="right", fill="y")
            self.preview_text.configure(yscrollcommand=self._preview_scroll.set, state="normal")
            self.preview_text.delete("1.0", tk.END)
            try:
                if os.path.getsize(path) <= MAX_CONTENT_SEARCH_SIZE:
                    with open(path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read(200000)  # حد أقصى للعرض حتى لا تتجمد الواجهة
                    self.preview_text.insert("1.0", content)
                else:
                    self.preview_text.insert("1.0", "File is too large to preview.")
            except Exception as e:
                self.preview_text.insert("1.0", f"Could not read file: {e}")
            self.preview_text.configure(state="disabled")

    # ---------------------------------------------------------------
    #                     القائمة المنبثقة (Context Menu)
    # ---------------------------------------------------------------
    def create_context_menu(self):
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="Open", command=self.ctx_open)
        self.context_menu.add_command(label="Open With...", command=self.ctx_open_with)
        self.context_menu.add_command(label="Open File Location", command=lambda: self.open_selected_item(None))
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Copy Path", command=self.ctx_copy_path)
        self.context_menu.add_command(label="Copy", command=self.ctx_copy)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Rename", command=self.ctx_rename)
        self.context_menu.add_command(label="Delete", command=self.ctx_delete)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Properties", command=self.ctx_properties)
        self.context_menu.add_command(label="Add to Favorites", command=self.ctx_add_favorite)
        self.context_menu.add_command(label="Search for Similar Files", command=self.ctx_search_similar)

    def show_context_menu(self, event):
        row_id = self.tree.identify_row(event.y)
        if row_id and row_id not in self.tree.selection():
            self.tree.selection_set(row_id)
        if self.tree.selection():
            self.context_menu.tk_popup(event.x_root, event.y_root)

    def _get_selected_paths(self):
        return [self.tree.item(i)["values"][4] for i in self.tree.selection()]

    def ctx_open(self):
        for path in self._get_selected_paths():
            try:
                if platform.system() == "Windows":
                    os.startfile(path)
                elif platform.system() == "Darwin":
                    subprocess.run(["open", path])
                else:
                    subprocess.run(["xdg-open", path])
            except Exception as e:
                messagebox.showerror("Error", f"Could not open the file:\n{e}")

    def ctx_open_with(self):
        paths = self._get_selected_paths()
        if not paths:
            return
        path = paths[0]
        try:
            if platform.system() == "Windows":
                subprocess.run(["rundll32.exe", "shell32.dll,OpenAs_RunDLL", path])
            elif platform.system() == "Darwin":
                subprocess.run(["open", "-a", "Finder", path])
            else:
                subprocess.run(["xdg-open", path])
        except Exception as e:
            messagebox.showerror("Error", f"Could not open the 'Open With' menu:\n{e}")

    def ctx_copy_path(self):
        paths = self._get_selected_paths()
        if not paths:
            return
        self.root.clipboard_clear()
        self.root.clipboard_append("\n".join(paths))
        self.status_var.set(f"Copied {len(paths)} path(s) to the clipboard.")

    def ctx_copy(self):
        """Copies the selected file(s) to the same folder with a (copy) suffix"""
        import shutil
        paths = self._get_selected_paths()
        copied = 0
        for path in paths:
            try:
                if os.path.isdir(path):
                    continue
                base, ext = os.path.splitext(path)
                new_path = f"{base} - copy{ext}"
                counter = 1
                while os.path.exists(new_path):
                    new_path = f"{base} - copy ({counter}){ext}"
                    counter += 1
                shutil.copy2(path, new_path)
                copied += 1
            except Exception as e:
                messagebox.showerror("Error", f"Could not copy file {path}:\n{e}")
        if copied:
            messagebox.showinfo("Done", f"Copied {copied} file(s) successfully.")

    def ctx_rename(self):
        paths = self._get_selected_paths()
        if len(paths) != 1:
            messagebox.showwarning("Notice", "Please select exactly one item to rename.")
            return
        old_path = paths[0]
        old_name = os.path.basename(old_path)

        dialog = tk.Toplevel(self.root)
        dialog.title("Rename")
        dialog.geometry("400x120")
        ttk.Label(dialog, text="New name:").pack(pady=(15, 5))
        entry = ttk.Entry(dialog, width=40)
        entry.insert(0, old_name)
        entry.pack(pady=5)
        entry.focus()
        entry.select_range(0, len(os.path.splitext(old_name)[0]))

        def do_rename():
            new_name = entry.get().strip()
            if not new_name:
                return
            for char in INVALID_NAME_CHARS:
                if char in new_name:
                    messagebox.showerror("Invalid Name", f"Cannot use the character: {char}")
                    return
            new_path = os.path.join(os.path.dirname(old_path), new_name)
            if os.path.exists(new_path):
                messagebox.showerror("Error", "An item with the same name already exists.")
                return
            try:
                os.rename(old_path, new_path)
                self.tree.set(self.tree.selection()[0], "name", new_name)
                self.tree.set(self.tree.selection()[0], "path", new_path)
                dialog.destroy()
                self.status_var.set("Renamed successfully.")
            except Exception as e:
                messagebox.showerror("Error", f"Rename failed:\n{e}")

        ttk.Button(dialog, text="Confirm", command=do_rename).pack(pady=10)

    def ctx_delete(self):
        import shutil
        paths = self._get_selected_paths()
        if not paths:
            return
        confirm = messagebox.askyesno(
            "Confirm Delete",
            f"Are you sure you want to delete {len(paths)} item(s)?\n"
            + ("The item(s) will be moved to the Recycle Bin." if SEND2TRASH_AVAILABLE else "Warning: this will permanently delete!")
        )
        if not confirm:
            return

        deleted_ids = []
        for item_id in list(self.tree.selection()):
            path = self.tree.item(item_id)["values"][4]
            try:
                if SEND2TRASH_AVAILABLE:
                    send2trash(path)
                elif os.path.isdir(path):
                    shutil.rmtree(path)
                else:
                    os.remove(path)
                deleted_ids.append(item_id)
            except Exception as e:
                messagebox.showerror("Error", f"Could not delete {path}:\n{e}")

        for item_id in deleted_ids:
            self.tree.delete(item_id)
        self.status_var.set(f"Deleted {len(deleted_ids)} item(s).")

    def ctx_properties(self):
        paths = self._get_selected_paths()
        if len(paths) != 1:
            messagebox.showinfo("Properties", f"{len(paths)} item(s) selected.")
            return
        info = get_file_info_full(paths[0])
        if not info:
            messagebox.showerror("Error", "Could not retrieve information for this item.")
            return
        messagebox.showinfo(
            "Properties",
            f"Name: {info['name']}\n"
            f"Type: {info['type']}\n"
            f"Size: {info['size_str']}\n"
            f"Created: {info['created']}\n"
            f"Modified: {info['modified']}\n"
            f"Path: {info['path']}"
        )

    def ctx_add_favorite(self):
        paths = self._get_selected_paths()
        if not paths:
            return
        favorites = load_favorites()
        for path in paths:
            favorites.append({"type": "file_shortcut", "name": os.path.basename(path), "path": path})
        save_favorites(favorites)
        messagebox.showinfo("Done", f"Added {len(paths)} item(s) to favorites.")

    def ctx_search_similar(self):
        paths = self._get_selected_paths()
        if len(paths) != 1:
            messagebox.showwarning("Notice", "Please select a single file to search for similar files.")
            return
        reference = paths[0]
        search_root = os.path.dirname(reference)

        self.status_var.set("Searching for similar files...")
        stop_event = threading.Event()

        def worker():
            results = find_similar_files(reference, search_root, stop_event)
            self.root.after(0, lambda: self._show_similar_results(reference, results))

        threading.Thread(target=worker, daemon=True).start()

    def _show_similar_results(self, reference, results):
        win = tk.Toplevel(self.root)
        win.title(f"Files similar to: {os.path.basename(reference)}")
        win.geometry("650x400")

        listbox = tk.Listbox(win, font=("Arial", 10))
        listbox.pack(fill="both", expand=True, padx=10, pady=10)
        if not results:
            listbox.insert("end", "No similar files found.")
        for r in results:
            listbox.insert("end", r)
        self.status_var.set(f"Found {len(results)} similar file(s).")

    # ---------------------------------------------------------------
    #                       فتح موقع الملف (الأصلية)
    # ---------------------------------------------------------------
    def open_selected_item(self, event):
        selected_item = self.tree.selection()
        if not selected_item:
            return

        item_data = self.tree.item(selected_item[0])
        full_path = item_data['values'][4]  # index 4 هو المسار الكامل

        if not os.path.exists(full_path):
            messagebox.showerror("Error", "The file or path no longer exists.")
            return

        system = platform.system()

        if system == "Windows":
            subprocess.run(f'explorer /select,"{os.path.normpath(full_path)}"')
        elif system == "Darwin":
            subprocess.run(["open", "-R", full_path])
        else:
            folder = full_path if os.path.isdir(full_path) else os.path.dirname(full_path)
            subprocess.run(["xdg-open", folder])

    def save_search_history(self):
        if not self.last_results and not self.last_query:
            messagebox.showwarning("Notice", "No previous results to export.")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")]
        )

        if not file_path:
            return

        try:
            save_to_history(self.last_query, self.last_results, file_path)
            messagebox.showinfo("Success", "Search results saved to JSON file successfully.")
        except Exception as e:
            messagebox.showerror("Error", f"Save failed: {e}")

    # ---------------------------------------------------------------
    #                       نافذة السجل (History)
    # ---------------------------------------------------------------
    def open_history_window(self):
        entries = load_history_entries()

        win = tk.Toplevel(self.root)
        win.title("Search History")
        win.geometry("600x400")

        listbox = tk.Listbox(win, font=("Arial", 10))
        listbox.pack(fill="both", expand=True, padx=10, pady=10)

        for e in entries:
            listbox.insert("end", f"{e.get('timestamp','')} | {e.get('query','')} | {e.get('results_count',0)} results")

        def rerun_selected():
            sel = listbox.curselection()
            if not sel:
                return
            entry = entries[sel[0]]
            self.entry_filename.delete(0, tk.END)
            self.entry_filename.insert(0, entry.get("query", ""))
            self.entry_dirs.delete(0, tk.END)
            self.entry_dirs.insert(0, entry.get("directories", ""))
            if entry.get("category"):
                self.combo_category.set(entry["category"])
            if entry.get("custom_ext"):
                self.entry_custom_ext.config(state="normal")
                self.entry_custom_ext.delete(0, tk.END)
                self.entry_custom_ext.insert(0, entry["custom_ext"])
            self.search_mode_var.set(entry.get("exact_match", "0"))
            win.destroy()
            self.start_search_thread()

        def clear_all():
            if messagebox.askyesno("Confirm", "Clear the entire search history?"):
                clear_history_entries()
                listbox.delete(0, "end")

        btns = ttk.Frame(win)
        btns.pack(fill="x", pady=(0, 10))
        ttk.Button(btns, text="Re-run Selected Search", command=rerun_selected).pack(side="left", padx=10)
        ttk.Button(btns, text="Clear History", command=clear_all).pack(side="left", padx=10)

    # ---------------------------------------------------------------
    #                 عمليات البحث المفضلة (Saved Searches)
    # ---------------------------------------------------------------
    def save_current_as_favorite(self):
        valid_data = self.validate_inputs()
        if not valid_data:
            return
        file_name, target_exts, dirs_list = valid_data

        name = simpledialog.askstring("Save Search", "Favorite search name:")
        if not name:
            return

        options = self._collect_filter_options()
        options["custom_date_start"] = str(options["custom_date_start"]) if options["custom_date_start"] else None
        options["custom_date_end"] = str(options["custom_date_end"]) if options["custom_date_end"] else None

        favorites = load_favorites()
        favorites.append({
            "type": "saved_search",
            "name": name,
            "query": file_name,
            "category": self.combo_category.get(),
            "custom_ext": self.entry_custom_ext.get(),
            "directories": self.entry_dirs.get(),
            "exact_match": self.search_mode_var.get(),
            "options": options,
        })
        save_favorites(favorites)
        messagebox.showinfo("Done", f"Search '{name}' saved to favorites.")

    def open_favorites_window(self):
        favorites = load_favorites()
        saved_searches = [f for f in favorites if f.get("type") == "saved_search"]

        win = tk.Toplevel(self.root)
        win.title("Favorite Searches")
        win.geometry("600x400")

        listbox = tk.Listbox(win, font=("Arial", 10))
        listbox.pack(fill="both", expand=True, padx=10, pady=10)

        for s in saved_searches:
            listbox.insert("end", f"{s.get('name')}  —  {s.get('query')}")

        def run_selected():
            sel = listbox.curselection()
            if not sel:
                return
            s = saved_searches[sel[0]]
            self.entry_filename.delete(0, tk.END)
            self.entry_filename.insert(0, s.get("query", ""))
            self.entry_dirs.delete(0, tk.END)
            self.entry_dirs.insert(0, s.get("directories", ""))
            self.combo_category.set(s.get("category", "All Files (*)"))
            if s.get("custom_ext"):
                self.entry_custom_ext.config(state="normal")
                self.entry_custom_ext.delete(0, tk.END)
                self.entry_custom_ext.insert(0, s["custom_ext"])
            self.search_mode_var.set(s.get("exact_match", "0"))

            opts = s.get("options", {})
            if opts:
                if not self.filters_visible:
                    self.toggle_filters()
                self.var_subfolders.set(opts.get("subfolders", True))
                self.var_hidden.set(opts.get("include_hidden", False))
                self.var_case_sensitive.set(opts.get("case_sensitive", False))
                self.var_search_content.set(opts.get("search_content", False))
                self.var_use_regex.set(opts.get("use_regex", False))
                self.var_use_wildcard.set(opts.get("use_wildcard", False))
                self.var_item_kind.set(opts.get("item_kind", "file"))

            win.destroy()
            self.start_search_thread()

        def rename_selected():
            sel = listbox.curselection()
            if not sel:
                return
            new_name = simpledialog.askstring("Rename", "New name:")
            if new_name:
                saved_searches[sel[0]]["name"] = new_name
                others = [f for f in favorites if f.get("type") != "saved_search"]
                save_favorites(others + saved_searches)
                listbox.delete(sel[0])
                listbox.insert(sel[0], f"{new_name}  —  {saved_searches[sel[0]].get('query')}")

        def delete_selected():
            sel = listbox.curselection()
            if not sel:
                return
            removed = saved_searches.pop(sel[0])
            others = [f for f in favorites if f is not removed]
            save_favorites(others)
            listbox.delete(sel[0])

        btns = ttk.Frame(win)
        btns.pack(fill="x", pady=(0, 10))
        ttk.Button(btns, text="Run", command=run_selected).pack(side="left", padx=10)
        ttk.Button(btns, text="Rename", command=rename_selected).pack(side="left", padx=10)
        ttk.Button(btns, text="Delete", command=delete_selected).pack(side="left", padx=10)

    # ---------------------------------------------------------------
    #                     نافذة الملفات المكررة
    # ---------------------------------------------------------------
    def open_duplicates_window(self):
        directories_str = self.entry_dirs.get().strip()
        if not directories_str:
            messagebox.showwarning("Notice", "Please select at least one folder in the Directories field first.")
            return
        raw_dirs = directories_str.replace("|", ",").split(",")
        dirs_list = [os.path.normpath(d.strip()) for d in raw_dirs if d.strip() and os.path.isdir(d.strip())]
        if not dirs_list:
            messagebox.showerror("Error", "No valid folders to search for duplicates.")
            return

        win = tk.Toplevel(self.root)
        win.title("Duplicate Files")
        win.geometry("800x500")

        status_var = tk.StringVar(value="Click 'Start Scan' to begin searching for duplicate files.")
        ttk.Label(win, textvariable=status_var).pack(anchor="w", padx=10, pady=(10, 0))

        tree = ttk.Treeview(win, columns=("group", "path", "size"), show="headings")
        tree.heading("group", text="Group")
        tree.heading("path", text="Path")
        tree.heading("size", text="Size")
        tree.column("group", width=100, anchor="center")
        tree.column("path", width=500, anchor="w")
        tree.column("size", width=100, anchor="center")
        tree.pack(fill="both", expand=True, padx=10, pady=10)

        stop_event = threading.Event()

        def start_scan():
            for i in tree.get_children():
                tree.delete(i)
            status_var.set("Scanning...")
            stop_event.clear()

            def worker():
                groups = find_duplicate_files(
                    dirs_list, stop_event,
                    progress_callback=lambda scanned, path: self.root.after(
                        0, lambda: status_var.set(f"Scanning... {scanned:,} file(s) scanned")
                    )
                )
                self.root.after(0, lambda: populate_results(groups))

            threading.Thread(target=worker, daemon=True).start()

        def populate_results(groups):
            if not groups:
                status_var.set("No duplicate files found.")
                return
            group_num = 0
            for file_hash, paths in groups.items():
                group_num += 1
                for p in paths:
                    size_str, _ = get_file_info(p)
                    tree.insert("", "end", values=(f"#{group_num}", p, size_str))
            status_var.set(f"Found {group_num} group(s) of duplicate files.")

        def delete_selected():
            selected = tree.selection()
            if not selected:
                return
            if not messagebox.askyesno("Confirm", f"Delete {len(selected)} selected file(s)?"):
                return
            for item_id in selected:
                path = tree.item(item_id)["values"][1]
                try:
                    if SEND2TRASH_AVAILABLE:
                        send2trash(path)
                    else:
                        os.remove(path)
                    tree.delete(item_id)
                except Exception as e:
                    messagebox.showerror("Error", f"Could not delete {path}:\n{e}")

        def open_location():
            selected = tree.selection()
            if not selected:
                return
            path = tree.item(selected[0])["values"][1]
            self._open_path_location(path)

        btns = ttk.Frame(win)
        btns.pack(fill="x", pady=(0, 10))
        ttk.Button(btns, text="Start Scan", command=start_scan).pack(side="left", padx=10)
        ttk.Button(btns, text="Open Location", command=open_location).pack(side="left", padx=10)
        ttk.Button(btns, text="Delete Selected", command=delete_selected).pack(side="left", padx=10)

    def _open_path_location(self, full_path):
        if not os.path.exists(full_path):
            messagebox.showerror("Error", "The file or path no longer exists.")
            return
        system = platform.system()
        if system == "Windows":
            subprocess.run(f'explorer /select,"{os.path.normpath(full_path)}"')
        elif system == "Darwin":
            subprocess.run(["open", "-R", full_path])
        else:
            folder = full_path if os.path.isdir(full_path) else os.path.dirname(full_path)
            subprocess.run(["xdg-open", folder])

    # ---------------------------------------------------------------
    #                     نافذة الفهرسة (SQLite Index)
    # ---------------------------------------------------------------
    def open_index_window(self):
        win = tk.Toplevel(self.root)
        win.title("File Indexing (SQLite)")
        win.geometry("500x260")

        count = self.index_db.count()
        status_var = tk.StringVar(value=f"Currently indexed files: {count:,}")
        ttk.Label(win, textvariable=status_var, font=("Arial", 10)).pack(pady=15)

        progress = ttk.Progressbar(win, mode="indeterminate")
        progress.pack(fill="x", padx=20)

        stop_event = threading.Event()

        def rebuild():
            directories_str = self.entry_dirs.get().strip()
            if not directories_str:
                messagebox.showwarning("Notice", "Please select at least one folder in the main interface.")
                return
            raw_dirs = directories_str.replace("|", ",").split(",")
            dirs_list = [os.path.normpath(d.strip()) for d in raw_dirs if d.strip() and os.path.isdir(d.strip())]
            if not dirs_list:
                messagebox.showerror("Error", "No valid folders to index.")
                return

            progress.start(10)
            status_var.set("Building index...")
            stop_event.clear()

            def worker():
                total = self.index_db.rebuild_index(
                    dirs_list, stop_event,
                    progress_callback=lambda count_, path: self.root.after(
                        0, lambda: status_var.set(f"Indexing... {count_:,} file(s)")
                    )
                )
                self.root.after(0, lambda: finish(total))

            def finish(total):
                progress.stop()
                status_var.set(f"Indexing complete: {total:,} file(s) indexed.")

            threading.Thread(target=worker, daemon=True).start()

        def cancel():
            stop_event.set()

        btns = ttk.Frame(win)
        btns.pack(pady=15)
        ttk.Button(btns, text="Build / Rebuild Index", command=rebuild).pack(side="left", padx=10)
        ttk.Button(btns, text="Cancel", command=cancel).pack(side="left", padx=10)

        ttk.Label(
            win,
            text="Note: Indexing is optional and does not affect the current direct search.\n"
                 "It will be used in the future to speed up repeated searches on the same folders.",
            wraplength=460, justify="right", font=("Arial", 8)
        ).pack(pady=10)


if __name__ == "__main__":
    root = tk.Tk()
    app = AdvancedSearchApp(root)
    root.mainloop()
