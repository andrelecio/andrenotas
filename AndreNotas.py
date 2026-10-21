"""AndreNotas v0.9 — editor leve, um documento por vez, Python/Tkinter."""
from __future__ import annotations

import json
import time
import hashlib
import codecs
import os
import re
import keyword
import sys
import webbrowser
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, font as tkfont, messagebox, ttk

APP_NAME = "AndreNotas"
VERSION = "1.0"
BG = "#f4f8fd"
SURFACE = "#ffffff"
BLUE = "#d9ebfb"
BLUE_HOVER = "#c3ddf7"
BLUE_TEXT = "#24527e"
TEXT = "#263a51"
MUTED = "#7389a3"
LINE_BG = "#eaf3fc"
BORDER = "#d8e5f2"
SELECT = "#c5e0f8"
# Filtros curtos: as extensões detalhadas ficam nos padrões, não nos rótulos.
EXTENSIONS = [
    ("Texto (*.txt)", "*.txt"),
    ("Texto e documentos", "*.txt *.text *.md *.markdown *.rst *.log *.csv *.tsv"),
    ("Python", "*.py *.pyw"),
    ("Web", "*.html *.htm *.css *.scss *.sass *.js *.jsx *.ts *.tsx *.php *.phtml *.vue *.svelte"),
    ("Dados e configuração", "*.json *.jsonl *.xml *.svg *.yaml *.yml *.toml *.ini *.cfg *.conf *.env *.properties"),
    ("Banco de dados SQL", "*.sql"),
    ("C, C++ e C#", "*.c *.h *.cpp *.hpp *.cc *.cxx *.cs"),
    ("Java, Kotlin, Go e Rust", "*.java *.kt *.kts *.go *.rs"),
    ("Scripts", "*.sh *.bat *.cmd *.ps1 *.rb *.lua *.pl"),
    ("Outras linguagens", "*.r *.swift *.dart *.scala *.ex *.exs *.erl *.hs *.vb *.asm *.pas *.f90"),
    ("Todos os arquivos", "*.*"),
]



class AndreNotas(tk.Tk):
    def __init__(self):
        super().__init__()
        self.geometry("1000x750")
        self.minsize(420, 340)
        self.configure(bg=BG)
        self.path: Path | None = None
        self.encoding = "utf-8"
        self.newline = "\n"
        self.changed = False
        self.data_dir = Path(os.environ.get("LOCALAPPDATA") or (Path.home() / ".andrenotas")) / "AndreNotas"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.settings_file = self.data_dir / "config.json"
        self.recovery_file = self.data_dir / "recuperacao.json"
        try:
            self.preferences = json.loads(self.settings_file.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            self.preferences = {}
        self.wrap_on = tk.BooleanVar(value=self.preferences.get("wrap", True))
        self.readonly_on = tk.BooleanVar(value=False)
        self.last_path = self.preferences.get("last_path", "")
        self._recovery_job = None
        self._recovery_enabled = False
        self._restored_recovery = False
        self.show_lines = tk.BooleanVar(value=self.preferences.get("lines", True))
        self.syntax_on = tk.BooleanVar(value=self.preferences.get("syntax", True))
        self._syntax_job = None
        self.find_dialog = None
        self.search_var = tk.StringVar()
        self.replace_var = tk.StringVar()
        self.match_case = tk.BooleanVar(value=False)
        self.status = tk.StringVar()
        self.font_family = "Kumbh Sans"
        self.editor_font = tkfont.Font(family=self.font_family, size=max(8, min(32, int(self.preferences.get("font_size", 11)))))
        self.interface_font = tkfont.Font(family=self.font_family, size=10)
        self.number_font = tkfont.Font(family=self.font_family, size=self.editor_font.cget("size"))
        try:
            self.iconbitmap(str(Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)) / "andrenote.ico"))
        except tk.TclError:
            pass
        self._set_native_appearance()
        self._build_style()
        self._build_menus()
        self._build_ui()
        self._bind_keys()
        self.protocol("WM_DELETE_WINDOW", self.quit_app)
        self.new_file(first=True)
        self._recovery_enabled = True
        self.after(1000, self._startup_recovery)
        self.after(15000, self._periodic_recovery)
        # Abertura de arquivo via duplo clique / Abrir com no Windows.
        if len(sys.argv) > 1:
            self.after(150, lambda p=sys.argv[1]: self._open_path(p))

    def _set_native_appearance(self):
        if os.name == "nt":
            try:
                import ctypes
                ctypes.windll.shcore.SetProcessDpiAwareness(1)
            except Exception:
                pass
            try:
                import ctypes
                # Rounded corners and light title bar on Windows 11 (ignored on older Windows).
                hwnd = self.winfo_id()
                corner = ctypes.c_int(2)
                light = ctypes.c_int(0)
                ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 33, ctypes.byref(corner), ctypes.sizeof(corner))
                ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(light), ctypes.sizeof(light))
            except Exception:
                pass

    def _build_style(self):
        style = ttk.Style(self)
        if "vista" in style.theme_names():
            style.theme_use("vista")
        style.configure("Pastel.TFrame", background=BG)
        style.configure("Vertical.TScrollbar", arrowsize=13)

    def _build_menus(self):
        menu = tk.Menu(self, font=(self.font_family, 10))
        file_menu = tk.Menu(menu, tearoff=False, font=(self.font_family, 10))
        file_menu.add_command(label="Novo", accelerator="Ctrl+N", command=self.new_file)
        file_menu.add_command(label="Abrir...", accelerator="Ctrl+O", command=self.open_file)
        file_menu.add_command(label="Reabrir último arquivo", command=self.reopen_last_file)
        file_menu.add_command(label="Codificação do documento...", command=self.choose_encoding)
        file_menu.add_separator()
        file_menu.add_command(label="Salvar", accelerator="Ctrl+S", command=self.save_file)
        file_menu.add_command(label="Salvar como...", accelerator="Ctrl+Shift+S", command=self.save_as)
        file_menu.add_separator()
        file_menu.add_command(label="Imprimir...", accelerator="Ctrl+P", command=self.print_document)
        file_menu.add_command(label="Fechar documento", accelerator="Ctrl+W", command=self.close_document)
        file_menu.add_separator()
        file_menu.add_command(label="Sair", command=self.quit_app)
        menu.add_cascade(label="Arquivo", menu=file_menu)
        edit = tk.Menu(menu, tearoff=False, font=(self.font_family, 10))
        for label, event, shortcut in [
            ("Desfazer", "<<Undo>>", "Ctrl+Z"), ("Refazer", "<<Redo>>", "Ctrl+Y"),
            ("Recortar", "<<Cut>>", "Ctrl+X"), ("Copiar", "<<Copy>>", "Ctrl+C"),
            ("Colar", "<<Paste>>", "Ctrl+V"),
        ]:
            edit.add_command(label=label, accelerator=shortcut, command=lambda ev=event: self.text.event_generate(ev))
        edit.add_separator()
        edit.add_command(label="Selecionar tudo", accelerator="Ctrl+A", command=self.select_all)
        menu.add_cascade(label="Editar", menu=edit)
        find_menu = tk.Menu(menu, tearoff=False, font=(self.font_family, 10))
        find_menu.add_command(label="Localizar...", accelerator="Ctrl+F", command=self.show_search)
        find_menu.add_command(label="Localizar e substituir...", accelerator="Ctrl+H", command=self.show_search)
        find_menu.add_separator()
        find_menu.add_command(label="Próximo resultado", accelerator="F3", command=self.find_next)
        find_menu.add_command(label="Resultado anterior", accelerator="Shift+F3", command=self.find_previous)
        find_menu.add_separator()
        find_menu.add_command(label="Ir para linha...", accelerator="Ctrl+G", command=self.goto_line)
        menu.add_cascade(label="Localizar", menu=find_menu)
        view = tk.Menu(menu, tearoff=False, font=(self.font_family, 10))
        view.add_checkbutton(label="Mostrar números das linhas", variable=self.show_lines, command=self.toggle_lines)
        view.add_checkbutton(label="Realce de sintaxe", variable=self.syntax_on, command=self.toggle_syntax)
        view.add_checkbutton(label="Quebra automática de linha", variable=self.wrap_on, command=self.toggle_wrap)
        view.add_checkbutton(label="Somente leitura", variable=self.readonly_on, command=self.toggle_readonly)
        view.add_separator()
        view.add_command(label="Aumentar zoom", accelerator="Ctrl++", command=lambda: self.zoom(1))
        view.add_command(label="Diminuir zoom", accelerator="Ctrl+-", command=lambda: self.zoom(-1))
        view.add_command(label="Configurações...", command=self.show_settings)
        menu.add_cascade(label="Exibir", menu=view)
        about_menu = tk.Menu(menu, tearoff=False, font=(self.font_family, 10))
        about_menu.add_command(label="Sobre AndreNotas...", command=self.show_about)
        menu.add_cascade(label="Sobre", menu=about_menu)
        self.config(menu=menu)

    def _build_ui(self):
        # Barra leve com 14 ícones, usando imagens PNG locais e tooltips.
        self._build_toolbar()
        # Embedded search inspired by idea 3: two input rows on the left and grouped controls on the right.
        self.search_panel = tk.Frame(self, bg=SURFACE, highlightbackground=BORDER, highlightthickness=1)
        self.search_panel.grid_columnconfigure(1, weight=1)

        left_area = tk.Frame(self.search_panel, bg=SURFACE)
        left_area.grid(row=0, column=0, sticky="nsew", padx=(10, 10), pady=10)
        left_area.grid_columnconfigure(1, weight=1)

        tk.Label(left_area, text="Buscar", bg=SURFACE, fg=TEXT,
                 font=(self.font_family, 12)).grid(row=0, column=0, sticky="w", padx=(6, 14), pady=(2, 10))
        self.find_entry = tk.Entry(left_area, textvariable=self.search_var,
                                   font=(self.font_family, 11), relief="flat", bg="#ffffff", fg=TEXT,
                                   highlightthickness=1, highlightbackground="#a9bfd8",
                                   highlightcolor="#5f9ff0", insertbackground=BLUE_TEXT)
        self.find_entry.grid(row=0, column=1, sticky="ew", ipady=9, pady=(0, 10))

        tk.Label(left_area, text="Substituir", bg=SURFACE, fg=TEXT,
                 font=(self.font_family, 12)).grid(row=1, column=0, sticky="w", padx=(6, 14))
        self.replace_entry = tk.Entry(left_area, textvariable=self.replace_var,
                                      font=(self.font_family, 11), relief="flat", bg="#ffffff", fg=TEXT,
                                      highlightthickness=1, highlightbackground="#b9c8d8",
                                      highlightcolor="#5f9ff0", insertbackground=BLUE_TEXT)
        self.replace_entry.grid(row=1, column=1, sticky="ew", ipady=9)

        controls = tk.Frame(self.search_panel, bg=SURFACE)
        controls.grid(row=0, column=1, sticky="ns", pady=10, padx=(0, 10))

        def sep(parent):
            return tk.Frame(parent, bg=BORDER, width=1, height=96)

        group_actions = tk.Frame(controls, bg=SURFACE)
        group_actions.pack(side="left", padx=(0, 10), fill="y")
        self._button(group_actions, "Buscar", self.search_all, primary=True, width=10).pack(pady=(0, 8))
        self._button(group_actions, "Substituir", self.replace_one, width=10).pack()

        sep(controls).pack(side="left", fill="y", padx=(0, 10))

        group_nav = tk.Frame(controls, bg=SURFACE)
        group_nav.pack(side="left", padx=(0, 10), fill="y")
        self._button(group_nav, "Anterior", self.find_previous, width=9).pack(pady=(0, 8))
        self._button(group_nav, "Próximo", self.find_next, width=9).pack()

        sep(controls).pack(side="left", fill="y", padx=(0, 10))

        group_info = tk.Frame(controls, bg=SURFACE)
        group_info.pack(side="left", padx=(0, 10), fill="y")
        self.result_var = tk.StringVar(value="0 resultados")
        tk.Label(group_info, textvariable=self.result_var, font=(self.font_family, 11),
                 bg=SURFACE, fg=TEXT, width=11, anchor="center").pack(pady=(5, 16))
        tk.Checkbutton(group_info, text="Aa", variable=self.match_case, command=self.search_all,
                       bg=SURFACE, fg=TEXT, selectcolor=SURFACE, activebackground=SURFACE,
                       font=(self.font_family, 11), bd=0, highlightthickness=0).pack(anchor="w", padx=8)

        sep(controls).pack(side="left", fill="y", padx=(0, 10))

        group_more = tk.Frame(controls, bg=SURFACE)
        group_more.pack(side="left", padx=(0, 10), fill="y")
        self._button(group_more, "Substituir tudo", self.replace_all, width=14).pack(pady=(0, 8))

        close_group = tk.Frame(controls, bg=SURFACE)
        close_group.pack(side="left", fill="y")
        self._button(close_group, "×", self.close_search, width=2).pack(pady=(0, 48))

        self.find_entry.bind("<Return>", lambda e: self.search_all())
        self.find_entry.bind("<Escape>", lambda e: self.close_search())
        self.replace_entry.bind("<Return>", lambda e: self.replace_one())
        self.search_var.trace_add("write", lambda *_: self._schedule_search())

        border = tk.Frame(self, bg=BORDER, padx=1, pady=1)
        border.pack(fill="both", expand=True, padx=12, pady=(2, 5))
        editor = tk.Frame(border, bg=SURFACE)
        editor.pack(fill="both", expand=True)
        editor.grid_rowconfigure(0, weight=1)
        editor.grid_columnconfigure(1, weight=1)
        self.gutter = tk.Canvas(editor, width=47, bg=LINE_BG, highlightthickness=0, bd=0)
        self.gutter.grid(row=0, column=0, sticky="ns")
        self.text = tk.Text(editor, wrap="word", undo=True, autoseparators=True, maxundo=-1,
                            bg=SURFACE, fg=TEXT, insertbackground=BLUE_TEXT,
                            selectbackground=SELECT, selectforeground=TEXT,
                            relief="flat", bd=0, padx=12, pady=12, font=self.editor_font,
                            spacing1=1, spacing3=1, tabs=("2c",))
        self.text.grid(row=0, column=1, sticky="nsew")
        self.scroll = ttk.Scrollbar(editor, orient="vertical", command=self._scroll_y,
                                    style="Vertical.TScrollbar")
        self.scroll.grid(row=0, column=2, sticky="ns")
        self.text.configure(yscrollcommand=self._on_scroll)
        self.text.configure(wrap="word" if self.wrap_on.get() else "none")
        self.text.bind("<Control-MouseWheel>", self._zoom_mouse, add="+")
        footer = tk.Frame(self, bg=BG)
        footer.pack(fill="x", padx=13, pady=(0, 5))
        status_row = tk.Frame(footer, bg=BG)
        status_row.pack(fill="x")
        tk.Label(status_row, textvariable=self.status, font=(self.font_family, 9), fg=MUTED,
                 bg=BG, anchor="w").pack(side="left", fill="x", expand=True)
        self._make_switch(status_row, "Linhas", self.show_lines, self.toggle_lines)
        self._make_switch(status_row, "Sintaxe", self.syntax_on, self.toggle_syntax)
        tk.Label(footer, text="Software gratuito desenvolvido por André Henrique G. Lécio (andrelecio)",
                 font=(self.font_family, 8), fg=MUTED, bg=BG, anchor="center").pack(fill="x", pady=(2, 0))
        self.text.bind("<<Modified>>", self._modified)
        self.text.bind("<KeyRelease>", self._refresh, add="+")
        self.text.bind("<ButtonRelease-1>", self._refresh, add="+")
        self.text.bind("<MouseWheel>", self._refresh, add="+")
        self.text.bind("<Configure>", self._refresh, add="+")
        self.text.bind("<Button-4>", self._refresh, add="+")
        self.text.bind("<Button-5>", self._refresh, add="+")
        self.text.bind("<Control-a>", self._select_event)
        self.bind_all("<F3>", lambda e: (self.find_next(), "break")[1])
        self.bind_all("<Shift-F3>", lambda e: (self.find_previous(), "break")[1])
        self.text.bind("<Button-3>", self._context_menu)
        self.context_menu = tk.Menu(self, tearoff=False, font=(self.font_family, 10))
        for label, command in (("Desfazer", lambda: self.text.event_generate("<<Undo>>")),
                               ("Refazer", lambda: self.text.event_generate("<<Redo>>")),
                               ("Recortar", lambda: self.text.event_generate("<<Cut>>")),
                               ("Copiar", lambda: self.text.event_generate("<<Copy>>")),
                               ("Colar", lambda: self.text.event_generate("<<Paste>>")),
                               ("Selecionar tudo", self.select_all),
                               ("Localizar", self.show_search)):
            self.context_menu.add_command(label=label, command=command)

    def _resource_dir(self):
        # No onefile PyInstaller, PNGs are expanded into _MEIPASS.
        return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)) / "icons"

    def _build_toolbar(self):
        toolbar = tk.Frame(self, bg="#edf5fd", height=38, highlightbackground=BORDER, highlightthickness=1)
        toolbar.pack(fill="x", padx=12, pady=(7, 5))
        self._icon_images = []
        actions = [
            ("new", "Novo", self.new_file), ("open", "Abrir", self.open_file),
            ("save", "Salvar", self.save_file), ("save_as", "Salvar como", self.save_as),
            ("close", "Fechar documento", self.close_document), ("print", "Imprimir", self.print_document),
            (None, None, None),
            ("find", "Localizar", self.show_search), ("prev", "Resultado anterior", self.find_previous),
            ("next", "Próximo resultado", self.find_next),
            (None, None, None),
            ("redo", "Refazer", lambda: self.text.event_generate("<<Redo>>")),
            ("undo", "Desfazer", lambda: self.text.event_generate("<<Undo>>")),
            ("cut", "Recortar", lambda: self.text.event_generate("<<Cut>>")),
            ("copy", "Copiar", lambda: self.text.event_generate("<<Copy>>")),
            ("paste", "Colar", lambda: self.text.event_generate("<<Paste>>")),
        ]
        for icon, title, command in actions:
            if icon is None:
                tk.Frame(toolbar, bg="#cadbee", width=1, height=23).pack(side="left", padx=6, pady=6)
                continue
            try:
                photo = tk.PhotoImage(file=str(self._resource_dir() / f"{icon}.png"))
                self._icon_images.append(photo)
                btn = tk.Button(toolbar, image=photo, command=command, relief="flat", bd=0,
                                bg="#edf5fd", activebackground="#d5e8fc", cursor="hand2",
                                padx=5, pady=4, highlightthickness=0)
            except tk.TclError:
                btn = tk.Button(toolbar, text=title, command=command, relief="flat", bd=0,
                                bg="#edf5fd", cursor="hand2", padx=5, pady=4)
            btn.pack(side="left", padx=1, pady=3)
            btn.bind("<Enter>", lambda ev, b=btn: b.configure(bg="#d5e8fc"))
            btn.bind("<Leave>", lambda ev, b=btn: b.configure(bg="#edf5fd"))
            self._tooltip(btn, title)

    def _tooltip(self, widget, title):
        state = {"id": None, "window": None}
        def show():
            state["id"] = None
            if state["window"] or not widget.winfo_exists():
                return
            w = tk.Toplevel(self)
            w.wm_overrideredirect(True)
            w.wm_geometry(f"+{widget.winfo_rootx()}+{widget.winfo_rooty()+widget.winfo_height()+3}")
            tk.Label(w, text=title, bg="#fffce8", fg=TEXT, relief="solid", bd=1,
                     font=(self.font_family, 9), padx=6, pady=3).pack()
            state["window"] = w
        def enter(event):
            state["id"] = widget.after(600, show)
        def leave(event):
            if state["id"]:
                widget.after_cancel(state["id"])
                state["id"] = None
            if state["window"]:
                state["window"].destroy()
                state["window"] = None
        widget.bind("<Enter>", enter, add="+")
        widget.bind("<Leave>", leave, add="+")
        widget.bind("<Button-1>", leave, add="+")

    def _make_switch(self, parent, label, variable, callback):
        wrap = tk.Frame(parent, bg=BG)
        wrap.pack(side="right", padx=(10, 0))
        tk.Label(wrap, text=label, font=(self.font_family, 9), fg=BLUE_TEXT, bg=BG).pack(side="left", padx=(0, 5))
        w, h = 38, 20
        canvas = tk.Canvas(wrap, width=w, height=h, bg=BG, bd=0, highlightthickness=0, cursor="hand2")
        canvas.pack(side="left")
        def paint(*_):
            canvas.delete("all")
            enabled = variable.get()
            track = "#16b536" if enabled else "#d33c3c"
            canvas.create_oval(0, 0, h, h, fill=track, outline=track)
            canvas.create_oval(w-h, 0, w, h, fill=track, outline=track)
            canvas.create_rectangle(h/2, 0, w-h/2, h, fill=track, outline=track)
            cx = w-h/2-1 if enabled else h/2+1
            canvas.create_oval(cx-8, 2, cx+8, 18, fill="#f4f6f8", outline="#b8c2cc", width=1)
        def click(event):
            variable.set(not variable.get())
            callback()
            paint()
        canvas.bind("<Button-1>", click)
        variable.trace_add("write", paint)
        paint()

    def close_document(self):
        if self._confirm_discard_recovery_cleanup():
            self.close_search() if self.search_panel.winfo_manager() else None
            self._replace_document("")

    def print_document(self):
        # Windows printing through default registered text handler.
        if os.name != "nt":
            messagebox.showinfo("Impressão", "Impressão disponível no Windows.", parent=self)
            return
        import tempfile
        data = self.text.get("1.0", "end-1c")
        if not data:
            messagebox.showinfo("Impressão", "O documento está vazio.", parent=self)
            return
        try:
            temp = Path(tempfile.gettempdir()) / "AndreNotas_impressao.txt"
            temp.write_text(data, encoding="utf-8-sig")
            os.startfile(str(temp), "print")
        except (OSError, ValueError) as exc:
            messagebox.showerror("Impressão", f"Não foi possível enviar para impressão: {exc}", parent=self)

    def show_about(self):
        dialog = tk.Toplevel(self)
        dialog.title("Sobre o AndreNotas")
        dialog.configure(bg=BG)
        dialog.geometry("440x235")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()
        for label, size, weight in [
            (f"AndreNotas — Versão {VERSION}", 15, "bold"),
            ("FREEWARE", 11, "bold"),
            ("Desenvolvido por André Henrique G. Lécio", 11, "normal"),
        ]:
            tk.Label(dialog, text=label, bg=BG, fg=BLUE_TEXT,
                     font=(self.font_family, size, weight)).pack(pady=(15, 3))
        link = tk.Label(dialog, text="https://andrelecio.net.br", bg=BG, fg="#1761b3",
                        cursor="hand2", font=(self.font_family, 11, "underline"))
        link.pack(pady=8)
        link.bind("<Button-1>", lambda e: webbrowser.open("https://andrelecio.net.br"))
        tk.Button(dialog, text="Fechar", command=dialog.destroy, font=self.interface_font,
                  bg=BLUE, fg=BLUE_TEXT, relief="flat", padx=16, pady=5).pack(pady=9)

    def _button(self, parent, text, command, primary=False, width=None):
        return tk.Button(parent, text=text, command=command,
                         font=(self.font_family, 10), bg="#dcebf9" if primary else "#edf4fb",
                         fg=BLUE_TEXT, activebackground="#c9e0f5", relief="flat", bd=0,
                         padx=6, pady=5, cursor="hand2", width=width, highlightthickness=0)

    def _context_menu(self, event):
        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()
        return "break"

    def _bind_keys(self):
        for sequence, callback in [
            ("<Control-n>", self.new_file), ("<Control-w>", self.close_document), ("<Control-p>", self.print_document), ("<Control-o>", self.open_file),
            ("<Control-plus>", lambda: self.zoom(1)), ("<Control-minus>", lambda: self.zoom(-1)), ("<Control-g>", self.goto_line), ("<Control-s>", self.save_file), ("<Control-f>", self.show_search), ("<Control-h>", self.show_search), ("<Control-Shift-s>", self.save_as),
            ("<Control-Shift-S>", self.save_as),
        ]:
            self.bind_all(sequence, lambda event, fn=callback: (fn(), "break")[1])

    def _select_event(self, _event):
        self.select_all()
        return "break"

    def select_all(self):
        self.text.tag_add("sel", "1.0", "end-1c")
        self.text.mark_set("insert", "1.0")
        self.text.see("insert")
        self._refresh()

    def _modified(self, _event=None):
        if self.text.edit_modified():
            self.changed = True
            self.text.edit_modified(False)
            self._update_title()
        self._refresh()
        self._schedule_syntax()
        if self._recovery_enabled and self.changed:
            self._schedule_recovery()
        if self.search_panel.winfo_manager():
            self._schedule_search()

    def _update_title(self):
        name = self.path.name if self.path else "Sem título"
        self.title(f"{'* ' if self.changed else ''}{name} — {APP_NAME} v{VERSION}")

    def _refresh(self, _event=None):
        line, col = self.text.index("insert").split(".")
        name = str(self.path) if self.path else "Novo documento"
        total_lines = int(self.text.index("end-1c").split(".")[0])
        chars = len(self.text.get("1.0", "end-1c"))
        self.status.set(f"Ln {line}, Col {int(col) + 1}  |  {total_lines} linhas  |  {chars:,} caracteres  |  {self.encoding.upper()}  |  {name}")
        self.after_idle(self.draw_lines)

    def _scroll_y(self, *args):
        self.text.yview(*args)
        self.after_idle(self.draw_lines)

    def _on_scroll(self, first, last):
        self.scroll.set(first, last)
        self.after_idle(self.draw_lines)

    def toggle_lines(self):
        self._persist_preferences()
        if self.show_lines.get():
            self.gutter.grid()
        else:
            self.gutter.grid_remove()
        self.after_idle(self.draw_lines)

    def draw_lines(self):
        if not self.show_lines.get() or not self.gutter.winfo_exists():
            return
        self.gutter.delete("all")
        # dlineinfo usa coordenadas de linhas VISUAIS do Text e considera as quebras.
        # A numeração usa apenas o início de cada linha LÓGICA.
        index = self.text.index("@0,0 linestart")
        canvas_height = self.gutter.winfo_height()
        while True:
            info = self.text.dlineinfo(index)
            if info is not None:
                x, y, w, line_height, baseline = info
                if y >= canvas_height:
                    break
                self.gutter.create_text(36, y + line_height / 2,
                                        text=index.split(".")[0], anchor="e",
                                        fill=MUTED, font=self.number_font)
            next_index = self.text.index(f"{index} + 1 line linestart")
            if self.text.compare(next_index, "<=", index) or self.text.compare(next_index, ">=", "end"):
                break
            index = next_index

    def _confirm_discard(self):
        if not self.changed:
            return True
        name = self.path.name if self.path else "Sem título"
        result = messagebox.askyesnocancel("Alterações não salvas", f"Deseja salvar as alterações em {name}?", parent=self)
        if result is None:
            return False
        return self.save_file() if result else True

    def _replace_document(self, content, path=None, encoding="utf-8", newline="\n"):
        self.path = Path(path) if path else None
        self.encoding = encoding
        self.newline = newline
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.insert("1.0", content)
        self.text.edit_reset()
        self.text.edit_modified(False)
        self.changed = False
        self._update_title()
        self._refresh()
        self._schedule_syntax()
        self.text.configure(state="normal")
        self.readonly_on.set(False)
        self.text.focus_set()

    def new_file(self, first=False):
        if not first and not self._confirm_discard():
            return
        self._remove_recovery()
        self._replace_document("")

    @staticmethod
    def _decode(raw):
        for bom, encoding in ((codecs.BOM_UTF32_LE, "utf-32"), (codecs.BOM_UTF32_BE, "utf-32"),
                              (codecs.BOM_UTF8, "utf-8-sig"), (codecs.BOM_UTF16_LE, "utf-16"),
                              (codecs.BOM_UTF16_BE, "utf-16")):
            if raw.startswith(bom):
                return raw.decode(encoding), encoding
        if b"\x00" in raw:
            raise ValueError("Este arquivo parece ser binário, não texto.")
        for encoding in ("utf-8", "cp1252"):
            try:
                return raw.decode(encoding), encoding
            except UnicodeDecodeError:
                pass
        raise UnicodeError("Não foi possível identificar a codificação do texto.")

    def open_file(self):
        # Select path before warning about discarding current document.
        filename = filedialog.askopenfilename(parent=self, title="Abrir arquivo", filetypes=EXTENSIONS)
        if not filename:
            return
        return self._open_path(filename)

    def _open_path(self, filename):
        target = Path(filename)
        if self.path and os.path.normcase(str(self.path.resolve())) == os.path.normcase(str(target.resolve())):
            return
        try:
            raw = target.read_bytes()
            content, encoding = self._decode(raw)
            newline = "\r\n" if b"\r\n" in raw else ("\r" if b"\r" in raw and b"\n" not in raw else "\n")
        except (OSError, UnicodeError, ValueError) as exc:
            messagebox.showerror("Não foi possível abrir", str(exc), parent=self)
            return
        if not self._confirm_discard():
            return
        self._remove_recovery()
        self._replace_document(content, target, encoding, newline)
        self.last_path = str(target)
        self._persist_preferences()
        return True

    def save_file(self):
        if self.path is None:
            return self.save_as()
        return self._save_to(self.path)

    def save_as(self):
        filename = filedialog.asksaveasfilename(parent=self, title="Salvar como",
                                                initialfile=self.path.name if self.path else "Sem título.txt",
                                                defaultextension=".txt", filetypes=EXTENSIONS)
        return self._save_to(Path(filename)) if filename else False

    def _save_to(self, target):
        try:
            content = self.text.get("1.0", "end-1c").replace("\r\n", "\n").replace("\r", "\n")
            content = content.replace("\n", self.newline)
            target.write_bytes(content.encode(self.encoding))
        except (OSError, UnicodeError) as exc:
            messagebox.showerror("Erro ao salvar", str(exc), parent=self)
            return False
        self.path = target
        self.last_path = str(target)
        self._persist_preferences()
        self._remove_recovery()
        self.changed = False
        self.text.edit_modified(False)
        self._update_title()
        self._refresh()
        self._schedule_syntax()
        return True


    def toggle_syntax(self):
        self._persist_preferences()
        if self.syntax_on.get():
            self._schedule_syntax()
        else:
            for tag in ("syn_comment", "syn_string", "syn_number", "syn_keyword", "syn_tag", "syn_attr"):
                self.text.tag_remove(tag, "1.0", "end")

    def _schedule_syntax(self):
        if self._syntax_job is not None:
            self.after_cancel(self._syntax_job)
        self._syntax_job = self.after(250, self._highlight)

    def _highlight(self):
        self._syntax_job = None
        for name, color in (("syn_comment", "#76939a"), ("syn_string", "#277e70"),
                            ("syn_number", "#a66e24"), ("syn_keyword", "#346ab5"),
                            ("syn_tag", "#347ac0"), ("syn_attr", "#8a69a9")):
            self.text.tag_configure(name, foreground=color)
            self.text.tag_remove(name, "1.0", "end")
        if not self.syntax_on.get():
            return
        content = self.text.get("1.0", "end-1c")
        # Keep the editor responsive with large logs or source files.
        if len(content) > 250_000:
            return
        ext = self.path.suffix.lower() if self.path else ""
        python_mode = ext in (".py", ".pyw")
        markup = ext in (".html", ".htm", ".xml", ".svg", ".vue", ".svelte")
        sql = ext == ".sql"
        common_code = ext in (".js", ".jsx", ".ts", ".tsx", ".php", ".c", ".h", ".cpp", ".hpp", ".java", ".cs", ".go", ".rs", ".rb", ".lua", ".sh", ".ps1", ".css", ".scss", ".json", ".yaml", ".yml", ".toml", ".sql", ".bat")
        if not (python_mode or markup or common_code):
            return
        spans = []
        def add(tag, a, b):
            spans.append((tag, a, b))
        if markup:
            for m in re.finditer(r'<!--.*?-->|<[^>]*>', content, re.S):
                add("syn_comment" if m.group().startswith("<!--") else "syn_tag", *m.span())
        else:
            words = list(keyword.kwlist) if python_mode else ["if", "else", "for", "while", "return", "function", "class", "const", "let", "var", "import", "from", "def", "try", "except", "new", "public", "private", "static", "void", "int", "string", "true", "false", "null", "None", "True", "False", "SELECT", "FROM", "WHERE", "INSERT", "UPDATE", "DELETE", "JOIN", "CREATE", "TABLE", "AND", "OR", "NOT", "AS", "SET", "VALUES", "ORDER", "BY", "GROUP", "LIMIT"]
            pattern = r'\b(?:' + '|'.join(map(re.escape, words)) + r')\b'
            flags = re.I if sql else 0
            for m in re.finditer(pattern, content, flags):
                add("syn_keyword", *m.span())
            for m in re.finditer(r'\b\d+(?:\.\d+)?\b', content):
                add("syn_number", *m.span())
            # Later spans override keywords and numbers inside strings/comments.
            tokens = r"\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*'|//[^\n]*|/\*[\s\S]*?\*/|\#[^\n]*"
            for m in re.finditer(tokens, content):
                value = m.group()
                is_comment = value.startswith(("//", "/*", "#"))
                if value.startswith("#") and ext in (".css", ".scss"):
                    continue
                add("syn_comment" if is_comment else "syn_string", *m.span())
        for tag, start, end in spans:
            self.text.tag_add(tag, f"1.0+{start}c", f"1.0+{end}c")
        self.text.tag_raise("sel")

    def show_search(self):
        if not self.search_panel.winfo_manager():
            self.search_panel.pack(fill="x", padx=12, pady=(0, 6), before=self.text.master.master)
        selection = self.text.tag_ranges("sel")
        if selection:
            chosen = self.text.get(*selection)
            if chosen and "\n" not in chosen and len(chosen) < 150:
                self.search_var.set(chosen)
        self.find_entry.focus_set()
        self.find_entry.select_range(0, "end")
        self.search_all()

    def close_search(self):
        self.search_panel.pack_forget()
        self.text.tag_remove("search_hit", "1.0", "end")
        self.result_var.set("0 resultados")
        self.text.focus_set()

    def _schedule_search(self):
        if getattr(self, "_find_job", None):
            self.after_cancel(self._find_job)
        self._find_job = self.after(180, self.search_all)

    def _matches(self):
        needle = self.search_var.get()
        if not needle:
            return []
        content = self.text.get("1.0", "end-1c")
        flags = 0 if self.match_case.get() else re.IGNORECASE
        return [(m.start(), m.end()) for m in re.finditer(re.escape(needle), content, flags)]

    def search_all(self):
        self._find_job = None
        self.text.tag_configure("search_hit", background="#ffedaa", foreground=TEXT)
        self.text.tag_remove("search_hit", "1.0", "end")
        matches = self._matches()
        for start, end in matches[:10000]:
            self.text.tag_add("search_hit", f"1.0+{start}c", f"1.0+{end}c")
        self.result_var.set(f"{len(matches)} resultado{'s' if len(matches) != 1 else ''}")
        if matches:
            self._navigate(1)

    def _navigate(self, direction=1):
        matches = self._matches()
        if not matches:
            self.result_var.set("0 resultados")
            return
        cursor = self.text.count("1.0", "insert", "chars")[0]
        selection = self.text.tag_ranges("sel")
        if selection:
            cursor = self.text.count("1.0", str(selection[0] if direction < 0 else selection[1]), "chars")[0]
        if direction > 0:
            pos = next((i for i, (a, b) in enumerate(matches) if a >= cursor), 0)
        else:
            pos = next((i for i in range(len(matches)-1, -1, -1) if matches[i][1] <= cursor), len(matches)-1)
        start, end = matches[pos]
        self.text.tag_remove("sel", "1.0", "end")
        self.text.tag_add("sel", f"1.0+{start}c", f"1.0+{end}c")
        self.text.mark_set("insert", f"1.0+{end}c")
        self.text.see(f"1.0+{start}c")
        self.result_var.set(f"{pos+1} de {len(matches)}")
        self._refresh()

    def find_next(self):
        self._navigate(1)

    def find_previous(self):
        self._navigate(-1)

    def replace_one(self):
        needle = self.search_var.get()
        if not needle:
            return
        selection = self.text.tag_ranges("sel")
        if selection:
            actual = self.text.get(*selection)
            equals = actual == needle if self.match_case.get() else actual.casefold() == needle.casefold()
            if equals:
                start = str(selection[0])
                self.text.delete(*selection)
                self.text.insert(start, self.replace_var.get())
        self.search_all()

    def replace_all(self):
        needle = self.search_var.get()
        if not needle:
            return
        hay = self.text.get("1.0", "end-1c")
        flags = 0 if self.match_case.get() else re.IGNORECASE
        updated, count = re.subn(re.escape(needle), lambda m: self.replace_var.get(), hay, flags=flags)
        if count:
            self.text.edit_separator()
            self.text.delete("1.0", "end")
            self.text.insert("1.0", updated)
            self.text.edit_separator()
            self._schedule_syntax()
        self.search_all()
        self.result_var.set(f"{count} {'substituições' if count != 1 else 'substituição'}")

    def _persist_preferences(self):
        self.preferences.update(font_size=self.editor_font.cget("size"),
                                wrap=self.wrap_on.get(), lines=self.show_lines.get(),
                                syntax=self.syntax_on.get(), last_path=self.last_path)
        try:
            self.settings_file.write_text(json.dumps(self.preferences, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError:
            pass

    def toggle_wrap(self):
        self.text.configure(wrap="word" if self.wrap_on.get() else "none")
        self._persist_preferences()
        self._refresh()

    def toggle_readonly(self):
        self.text.configure(state="disabled" if self.readonly_on.get() else "normal")

    def zoom(self, delta):
        size = max(8, min(32, self.editor_font.cget("size") + delta))
        self.editor_font.configure(size=size)
        self.number_font.configure(size=size)
        self._persist_preferences()
        self._refresh()

    def _zoom_mouse(self, event):
        self.zoom(1 if event.delta > 0 else -1)
        return "break"

    def goto_line(self):
        from tkinter import simpledialog
        total = int(self.text.index("end-1c").split(".")[0])
        line = simpledialog.askinteger("Ir para linha", f"Número da linha (1 a {total}):", parent=self, minvalue=1, maxvalue=total)
        if line is not None:
            self.text.mark_set("insert", f"{line}.0")
            self.text.see("insert")
            self.text.focus_set()
            self._refresh()

    def show_settings(self):
        window = tk.Toplevel(self)
        window.title("Configurações — AndreNotas")
        window.geometry("390x340")
        window.resizable(False, False)
        window.configure(bg=BG)
        window.transient(self)
        window.grab_set()
        panel = tk.Frame(window, bg=BG, padx=20, pady=14)
        panel.pack(fill="both", expand=True)
        tk.Label(panel, text="Preferências do editor", bg=BG, fg=BLUE_TEXT,
                 font=(self.font_family, 14, "bold")).pack(anchor="w", pady=(0, 12))
        font_row = tk.Frame(panel, bg=BG)
        font_row.pack(fill="x", pady=5)
        tk.Label(font_row, text="Fonte: Kumbh Sans", bg=BG, fg=TEXT, font=self.interface_font).pack(side="left")
        size_var = tk.IntVar(value=self.editor_font.cget("size"))
        tk.Spinbox(font_row, from_=8, to=32, width=4, textvariable=size_var,
                   font=self.interface_font).pack(side="right")
        tk.Checkbutton(panel, text="Quebra automática de linha", bg=BG, fg=TEXT,
                       variable=self.wrap_on, command=self.toggle_wrap).pack(anchor="w", pady=4)
        tk.Checkbutton(panel, text="Numeração das linhas", bg=BG, fg=TEXT,
                       variable=self.show_lines, command=self.toggle_lines).pack(anchor="w", pady=4)
        tk.Checkbutton(panel, text="Realce de sintaxe", bg=BG, fg=TEXT,
                       variable=self.syntax_on, command=self.toggle_syntax).pack(anchor="w", pady=4)
        tk.Label(panel, text="Os arquivos são salvos em TXT por padrão.", bg=BG,
                 fg=MUTED, font=(self.font_family, 9)).pack(anchor="w", pady=(13, 6))
        def apply():
            size = max(8, min(32, size_var.get()))
            self.editor_font.configure(size=size)
            self.number_font.configure(size=size)
            self._persist_preferences()
            self._refresh()
            window.destroy()
        tk.Button(panel, text="Salvar configurações", command=apply, bg=BLUE,
                  fg=BLUE_TEXT, padx=12, pady=6, relief="flat").pack(anchor="e", pady=10)

    def _schedule_recovery(self):
        if self._recovery_job is not None:
            self.after_cancel(self._recovery_job)
        self._recovery_job = self.after(2500, self._write_recovery)

    def _write_recovery(self):
        self._recovery_job = None
        if not self.changed or not self._recovery_enabled:
            return
        try:
            content = self.text.get("1.0", "end-1c")
            item = {"path": str(self.path) if self.path else "", "content": content,
                    "encoding": self.encoding, "newline": self.newline, "saved_at": time.time()}
            tmp = self.recovery_file.with_suffix(".tmp")
            tmp.write_text(json.dumps(item, ensure_ascii=False), encoding="utf-8")
            tmp.replace(self.recovery_file)
        except OSError:
            pass

    def _periodic_recovery(self):
        if self.changed:
            self._write_recovery()
        self.after(15000, self._periodic_recovery)

    def _remove_recovery(self):
        try:
            self.recovery_file.unlink(missing_ok=True)
        except OSError:
            pass

    def _startup_recovery(self):
        if not self.winfo_exists():
            return
        if not self.recovery_file.exists():
            self._offer_last_file()
            return
        # Don't replace a document explicitly supplied by Windows command line.
        if len(sys.argv) > 1 or self.changed:
            return
        try:
            data = json.loads(self.recovery_file.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            self._offer_last_file()
            return
        content = data.get("content", "")
        if not isinstance(content, str):
            return
        if messagebox.askyesno("Recuperação automática", "Foi encontrada uma edição não salva. Deseja recuperá-la?", parent=self):
            path = data.get("path") or None
            self._replace_document(content, path, data.get("encoding", "utf-8"), data.get("newline", "\n"))
            self.changed = True
            self._update_title()
            self._restored_recovery = True
        else:
            self._remove_recovery()
            self._offer_last_file()

    def _offer_last_file(self):
        if len(sys.argv) > 1 or self.path or self.changed:
            return
        if self.last_path and Path(self.last_path).is_file():
            if messagebox.askyesno("Último documento", "Deseja reabrir o último arquivo utilizado?", parent=self):
                self.reopen_last_file()

    def choose_encoding(self):
        window = tk.Toplevel(self)
        window.title("Codificação do documento")
        window.geometry("370x210")
        window.configure(bg=BG)
        window.resizable(False, False)
        window.transient(self)
        window.grab_set()
        frame = tk.Frame(window, bg=BG, padx=18, pady=15)
        frame.pack(fill="both", expand=True)
        tk.Label(frame, text="Codificação para salvar o arquivo", bg=BG, fg=TEXT,
                 font=self.interface_font).pack(anchor="w", pady=(0, 12))
        available = {"UTF-8": "utf-8", "UTF-8 BOM": "utf-8-sig", "ANSI (Windows-1252)": "cp1252", "UTF-16": "utf-16"}
        current = next((k for k, v in available.items() if v == self.encoding), "UTF-8")
        chosen = tk.StringVar(value=current)
        picker = ttk.Combobox(frame, textvariable=chosen, values=list(available), state="readonly")
        picker.pack(fill="x", pady=(0, 12))
        def apply():
            encoding = available[chosen.get()]
            content = self.text.get("1.0", "end-1c")
            try:
                content.encode(encoding)
            except UnicodeEncodeError:
                messagebox.showerror("Codificação", "O texto contém caracteres incompatíveis com a codificação escolhida.", parent=window)
                return
            if self.encoding != encoding:
                self.encoding = encoding
                self.changed = True
                self._update_title()
                self._refresh()
                self._schedule_recovery()
            window.destroy()
        tk.Button(frame, text="Aplicar", command=apply, bg=BLUE, fg=BLUE_TEXT,
                  relief="flat", padx=10, pady=5).pack(anchor="e")

    def reopen_last_file(self):
        if self.last_path and Path(self.last_path).is_file():
            return self._open_path(self.last_path)
        messagebox.showinfo("Último arquivo", "Nenhum arquivo anterior disponível.", parent=self)

    def _confirm_discard_recovery_cleanup(self):
        ok = self._confirm_discard()
        if ok:
            self._remove_recovery()
        return ok

    def quit_app(self):
        if self._confirm_discard():
            self._remove_recovery()
            self._persist_preferences()
            self.destroy()


if __name__ == "__main__":
    AndreNotas().mainloop()
