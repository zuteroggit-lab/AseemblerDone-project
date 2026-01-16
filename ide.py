import tkinter as tk
from tkinter import scrolledtext, filedialog, messagebox, ttk
import os
import re
import requests
import threading
import datetime

# --- КОНФИГУРАЦИЯ ---
VERSION = "1.0.0 (Release)"
RAW_REPO_URL = "https://raw.githubusercontent.com/zuteroggit-lab/PackagesManagerAD-coding/main/packages.json"

# --- ЛОКАЛИЗАЦИЯ (RU / EN) ---
LANG = {
    "ru": {
        "title": "AsmDone IDE",
        "start_title": "Добро пожаловать",
        "btn_new": "НОВЫЙ ПРОЕКТ",
        "btn_open": "ОТКРЫТЬ ПРОЕКТ",
        "explorer": "ПРОВОДНИК",
        "registers": "РЕГИСТРЫ CPU",
        "term_ready": "Терминал готов.",
        "pma_title": "Менеджер пакетов (PMA)",
        "pma_btn": "СКАЧАТЬ В ПРОЕКТ",
        "save_msg": "Сохранено: .ad и .asm",
        "run_start": "--- ЗАПУСК КОДА ---",
        "run_end": "--- ВЫПОЛНЕНО ---",
        "err_file": "Ошибка файла",
        "conv_header": "; АВТОМАТИЧЕСКАЯ КОНВЕРТАЦИЯ ИЗ AD В ASM"
    },
    "en": {
        "title": "AsmDone IDE",
        "start_title": "Welcome",
        "btn_new": "NEW PROJECT",
        "btn_open": "OPEN PROJECT",
        "explorer": "FILE EXPLORER",
        "registers": "CPU REGISTERS",
        "term_ready": "Terminal ready.",
        "pma_title": "Package Manager (PMA)",
        "pma_btn": "DOWNLOAD TO PROJECT",
        "save_msg": "Saved: .ad and .asm exported",
        "run_start": "--- RUNNING CODE ---",
        "run_end": "--- FINISHED ---",
        "err_file": "File Error",
        "conv_header": "; AUTOMATIC CONVERSION FROM AD TO ASM"
    }
}

# Глобальная переменная для выбранного языка (по умолчанию RU)
CURRENT_LANG = "ru"

def T(key): return LANG[CURRENT_LANG].get(key, key)

class LineNumbers(tk.Canvas):
    def __init__(self, master, text_widget, **kwargs):
        super().__init__(master, **kwargs)
        self.text_widget = text_widget
        self.configure(width=50, bg="#252526", bd=0, highlightthickness=0)

    def redraw(self):
        self.delete("all")
        i = self.text_widget.index("@0,0")
        while True:
            dline = self.text_widget.dlineinfo(i)
            if dline is None: break
            y = dline[1]
            linenum = str(i).split(".")[0]
            self.create_text(25, y, anchor="n", text=linenum, fill="#858585", font=("Consolas", 12))
            i = self.text_widget.index("%s + 1 line" % i)

class PMA_Manager(tk.Toplevel):
    def __init__(self, parent, log_func):
        super().__init__(parent)
        self.title(T("pma_title"))
        self.geometry("700x500")
        self.configure(bg="#1e1e1e")
        self.log_func = log_func
        self.pkg_data = []

        tk.Label(self, text=T("pma_title"), fg="#569cd6", bg="#1e1e1e", font=("Segoe UI", 12, "bold")).pack(pady=10)
        self.tree = ttk.Treeview(self, columns=("Name", "Version", "Type"), show="headings")
        self.tree.heading("Name", text="Name"); self.tree.heading("Version", text="Ver"); self.tree.heading("Type", text="Type")
        self.tree.pack(fill="both", expand=True, padx=10)

        tk.Button(self, text=T("pma_btn"), bg="#28a745", fg="white", font=("Segoe UI", 10, "bold"), command=self.start_download).pack(pady=10)
        self.status = tk.Label(self, text="...", fg="#6a9955", bg="#1e1e1e")
        self.status.pack()
        threading.Thread(target=self.load_repo, daemon=True).start()

    def load_repo(self):
        try:
            r = requests.get(RAW_REPO_URL, timeout=5)
            if r.status_code == 200:
                self.pkg_data = r.json().get("packages", [])
                for pkg in self.pkg_data:
                    self.tree.insert("", "end", iid=pkg["name"], values=(pkg["name"], pkg["version"], pkg.get("type", "library")))
                self.status.config(text="Online")
        except: self.status.config(text="Offline / Error")

    def start_download(self):
        selected = self.tree.selection()
        if not selected: return
        info = next((item for item in self.pkg_data if item["name"] == selected[0]), None)
        if info: threading.Thread(target=self.download_task, args=(info,), daemon=True).start()

    def download_task(self, info):
        try:
            r = requests.get(info["url"])
            if r.status_code == 200:
                folder = "packages" if info.get("type") == "library" else "plugins"
                if not os.path.exists(folder): os.makedirs(folder)
                ext = ".ad" if info.get("type") == "library" else ".py"
                f_path = os.path.join(folder, info["name"] + ext)
                with open(f_path, "wb") as f: f.write(r.content)
                self.log_func(f"[PMA] Installed: {f_path}")
                messagebox.showinfo("PMA", f"OK: {f_path}")
        except Exception as e: self.log_func(f"[PMA ERR] {e}")

class AsmDoneIDE:
    def __init__(self, root):
        self.root = root
        self.root.withdraw() # Скрываем главное окно до выбора языка
        self.current_file = None
        self.registers = {"a1": 0, "b2": 0, "c3": 0}
        self.colors = {"action": "#569cd6", "math": "#C586C0", "label": "#dcdcaa", "logic": "#4ec9b0", "number": "#b5cea8", "comment": "#6a9955", "string": "#ce9178"}
        
        # Окно выбора языка
        self.lang_window()

    def lang_window(self):
        lw = tk.Toplevel(self.root)
        lw.title("Language / Язык")
        lw.geometry("300x150")
        lw.configure(bg="#2d2d2d")
        tk.Label(lw, text="Select Language", fg="white", bg="#2d2d2d", font=("Segoe UI", 12)).pack(pady=15)
        
        f = tk.Frame(lw, bg="#2d2d2d")
        f.pack()
        
        def set_lang(l):
            global CURRENT_LANG
            CURRENT_LANG = l
            lw.destroy()
            self.root.deiconify() # Показываем главное окно
            self.init_main_window()
            self.startup_dialog()

        tk.Button(f, text="English", width=10, command=lambda: set_lang("en"), bg="#007acc", fg="white").pack(side="left", padx=10)
        tk.Button(f, text="Русский", width=10, command=lambda: set_lang("ru"), bg="#28a745", fg="white").pack(side="left", padx=10)

    def init_main_window(self):
        self.root.title(f"{T('title')} v{VERSION}")
        self.root.geometry("1280x850")
        self.root.configure(bg="#1e1e1e")
        self.setup_ui()
        self.refresh_explorer()

    def startup_dialog(self):
        win = tk.Toplevel(self.root); win.title("Start"); win.geometry("400x200"); win.configure(bg="#2d2d2d")
        win.transient(self.root); win.grab_set()
        tk.Label(win, text=T("start_title"), fg="#569cd6", bg="#2d2d2d", font=("Segoe UI", 14, "bold")).pack(pady=20)
        tk.Button(win, text=T("btn_new"), width=30, bg="#28a745", fg="white", font=("Segoe UI", 10), command=lambda: [self.new_file(), win.destroy()]).pack(pady=5)
        tk.Button(win, text=T("btn_open"), width=30, bg="#007acc", fg="white", font=("Segoe UI", 10), command=lambda: [self.open_file(), win.destroy()]).pack(pady=5)

    def setup_ui(self):
        # Toolbar
        bar = tk.Frame(self.root, bg="#333333", height=45); bar.pack(fill="x", side="top")
        tk.Button(bar, text="▶ RUN", bg="#28a745", fg="white", font=("Segoe UI", 9, "bold"), command=self.action_run, bd=0, padx=15).pack(side="left", padx=5, pady=5)
        tk.Button(bar, text="💾 SAVE (AD+ASM)", bg="#007acc", fg="white", font=("Segoe UI", 9, "bold"), command=self.action_save, bd=0, padx=15).pack(side="left", padx=5, pady=5)
        tk.Button(bar, text="📦 PMA", bg="#6f42c1", fg="white", font=("Segoe UI", 9, "bold"), command=lambda: PMA_Manager(self.root, self.log), bd=0, padx=15).pack(side="left", padx=20, pady=5)

        self.paned = tk.PanedWindow(self.root, orient="horizontal", bg="#252526", bd=0, sashwidth=4); self.paned.pack(fill="both", expand=True)

        # Explorer
        exp_frame = tk.Frame(self.paned, bg="#252526"); self.paned.add(exp_frame, width=220)
        tk.Label(exp_frame, text=T("explorer"), fg="#cccccc", bg="#252526", font=("Segoe UI", 9, "bold")).pack(pady=5, anchor="w", padx=10)
        self.file_list = tk.Listbox(exp_frame, bg="#252526", fg="#cccccc", bd=0, font=("Segoe UI", 10), selectbackground="#37373d", highlightthickness=0)
        self.file_list.pack(fill="both", expand=True)
        self.file_list.bind("<Double-Button-1>", self.on_explorer_click)

        # Editor
        edit_f = tk.Frame(self.paned, bg="#1e1e1e"); self.paned.add(edit_f, width=800)
        self.code_input = tk.Text(edit_f, font=("Consolas", 14), bg="#1e1e1e", fg="#d4d4d4", insertbackground="white", bd=0, undo=True, wrap="none")
        self.ln = LineNumbers(edit_f, self.code_input); self.ln.pack(side="left", fill="y")
        self.code_input.pack(side="right", fill="both", expand=True)
        self.code_input.bind("<KeyRelease>", self.update_editor)
        self.code_input.bind("<Return>", self.auto_indent) # Bonus Feature

        # Registers
        self.reg_panel = tk.Frame(self.paned, bg="#252526"); self.paned.add(self.reg_panel, width=200)
        tk.Label(self.reg_panel, text=T("registers"), fg="#569cd6", bg="#252526", font=("Segoe UI", 10, "bold")).pack(pady=10)
        self.reg_val_labels = {}
        for reg in self.registers:
            f = tk.Frame(self.reg_panel, bg="#252526"); f.pack(fill="x", padx=10, pady=5)
            tk.Label(f, text=f"{reg}", fg="#9cdcfe", bg="#252526", font=("Consolas", 14)).pack(side="left")
            l = tk.Label(f, text="0", fg="#ce9178", bg="#252526", font=("Consolas", 14, "bold")); l.pack(side="right"); self.reg_val_labels[reg] = l

        # Terminal
        self.term_frame = tk.Frame(self.root, bg="#1e1e1e"); self.term_frame.pack(fill="x", side="bottom")
        self.status_bar = tk.Label(self.term_frame, text="Ready", bg="#007acc", fg="white", anchor="w", font=("Segoe UI", 9)); self.status_bar.pack(fill="x", side="bottom")
        
        self.term_output = tk.Text(self.term_frame, height=10, bg="#181818", fg="#00ff00", font=("Consolas", 12), bd=0, padx=10, pady=5); self.term_output.pack(fill="x")
        self.cmd_input = tk.Entry(self.term_frame, bg="#2d2d2d", fg="white", font=("Consolas", 12), insertbackground="white", bd=0); self.cmd_input.pack(fill="x", padx=0, pady=0)
        self.cmd_input.bind("<Return>", lambda e: self.process_terminal_command())

    def auto_indent(self, event):
        # Бонус: Авто-отступ как в настоящих IDE
        line_idx = self.code_input.index("insert").split(".")[0]
        line_text = self.code_input.get(f"{line_idx}.0", f"{line_idx}.end")
        indent = ""
        for char in line_text:
            if char in (" ", "\t"): indent += char
            else: break
        self.code_input.insert("insert", "\n" + indent)
        return "break"

    def refresh_explorer(self):
        self.file_list.delete(0, "end")
        try:
            for f in os.listdir('.'):
                if os.path.isfile(f) and not f.startswith('.'):
                    self.file_list.insert("end", f)
        except: pass

    def on_explorer_click(self, event):
        sel = self.file_list.get(self.file_list.curselection())
        if sel:
            self.current_file = os.path.abspath(sel)
            self.load_content()
            self.update_status(f"Opened: {sel}")

    def update_status(self, msg):
        self.status_bar.config(text=f" {msg} | Dir: {os.path.basename(os.getcwd())}")

    def set_project_dir(self, filepath):
        pdir = os.path.dirname(os.path.abspath(filepath))
        os.chdir(pdir)
        self.refresh_explorer()
        self.update_status("Ready")

    def log(self, text):
        self.term_output.insert("end", str(text) + "\n"); self.term_output.see("end")

    def update_editor(self, e=None): 
        self.ln.redraw(); self.highlight()
        # Обновление позиции курсора в статус баре
        cursor = self.code_input.index("insert")
        self.update_status(f"Line: {cursor}")

    def highlight(self):
        # Улучшенная подсветка
        for tag in self.colors: self.code_input.tag_remove(tag, "1.0", "end")
        content = self.code_input.get("1.0", "end")
        for tag, color in self.colors.items(): self.code_input.tag_configure(tag, foreground=color)
        
        rules = [
            (r'\b(set|import|show)\b', 'action'),
            (r'\b(add|sub|mul|div)\b', 'math'),
            (r'\b(check|then|if|else)\b', 'logic'),
            (r'\(.*?\)', 'label'),
            (r'>', 'action'),
            (r'\b\d+\b', 'number'),
            (r'#.*', 'comment'),
            (r'".*?"', 'string')
        ]
        for pattern, tag in rules:
            for m in re.finditer(pattern, content):
                self.code_input.tag_add(tag, f"1.0 + {m.start()} chars", f"1.0 + {m.end()} chars")

    def process_terminal_command(self):
        raw = self.cmd_input.get().strip(); self.cmd_input.delete(0, "end")
        if not raw: return
        self.log(f"$ {raw}")
        parts = raw.split(); cmd = parts[0].lower()
        if cmd == "hello": self.log(T("term_ready"))
        elif cmd == "ver": self.log(f"AsmDone Core: {VERSION}")
        elif cmd == "cls": self.term_output.delete("1.0", "end")
        elif cmd == "export" and len(parts) > 2 and parts[1] == "plugin": self.load_plugin(parts[2])
        else: self.log(f"bash: {cmd}: command not found")

    def load_plugin(self, path):
        if not os.path.exists(path): self.log("Err: File not found"); return
        try:
            with open(path, "r", encoding="utf-8") as f: exec(f.read(), {'self': self, 'tk': tk})
            self.log(f"Plugin loaded: {path}")
        except Exception as e: self.log(f"Plugin Err: {e}")

    def new_file(self):
        p = filedialog.asksaveasfilename(defaultextension=".ad", filetypes=[("AsmDone", "*.ad")])
        if p: self.current_file = p; self.set_project_dir(p); self.action_save()

    def open_file(self):
        p = filedialog.askopenfilename(filetypes=[("AsmDone", "*.ad"), ("All", "*.*")])
        if p: self.current_file = p; self.set_project_dir(p); self.load_content()

    def load_content(self):
        if self.current_file:
            self.code_input.delete("1.0", "end")
            try:
                with open(self.current_file, 'r', encoding='utf-8') as f: self.code_input.insert("1.0", f.read())
            except: self.log("Err: Cannot read file")
            self.update_editor()

    def action_save(self):
        if not self.current_file:
            self.current_file = filedialog.asksaveasfilename(defaultextension=".ad", filetypes=[("AsmDone", "*.ad")])
        
        if self.current_file:
            content = self.code_input.get("1.0", "end-1c")
            
            # 1. Сохранение AD
            ad_path = self.current_file
            if not ad_path.endswith('.ad'): ad_path += '.ad'
            with open(ad_path, 'w', encoding='utf-8') as f: f.write(content)
            
            # 2. Конвертация в ASM (Транспиляция)
            asm_path = os.path.splitext(ad_path)[0] + ".asm"
            
            # Простейший алгоритм конвертации для примера:
            # Превращает 'set a1 10' в 'MOV AX, 10' (примерно)
            asm_content = []
            asm_content.append(T("conv_header"))
            asm_content.append(f"; Source: {os.path.basename(ad_path)}")
            asm_content.append(f"; Date: {datetime.datetime.now()}\n")
            asm_content.append("SECTION .text")
            asm_content.append("GLOBAL _start\n_start:")
            
            lines = content.split('\n')
            for line in lines:
                l = line.strip()
                if not l or l.startswith('#'): 
                    asm_content.append(f"    ; {l}")
                    continue
                
                parts = l.split()
                cmd = parts[0]
                
                # Примитивная логика трансляции
                if cmd == "set": asm_content.append(f"    MOV {parts[1]}, {parts[2]}")
                elif cmd == "add": asm_content.append(f"    ADD {parts[1]}, {parts[2]}")
                elif cmd == "sub": asm_content.append(f"    SUB {parts[1]}, {parts[2]}")
                elif cmd == "check": asm_content.append(f"    CMP {parts[1]}, {parts[3]}")
                elif l.startswith('('): asm_content.append(f"{l[1:-1]}:")
                elif cmd == ">": asm_content.append(f"    JMP {parts[1]}")
                else: asm_content.append(f"    ; UNKNOWN: {l}")

            asm_content.append("\n    MOV EAX, 1\n    INT 0x80")
            
            with open(asm_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(asm_content))

            self.log(f"[SAVE] Exported: {os.path.basename(ad_path)} -> {os.path.basename(asm_path)}")
            self.refresh_explorer()
            messagebox.showinfo("Success", T("save_msg"))

    def action_run(self):
        self.log(T("run_start"))
        self.registers = {"a1": 0, "b2": 0, "c3": 0}
        
        # Парсинг для выполнения
        raw_lines = self.code_input.get("1.0", "end").split('\n')
        full_code = []
        
        # Pre-processor (Imports)
        for line in raw_lines:
            t = line.split('#')[0].replace(',', '').split()
            if not t: continue
            if t[0] == "import":
                p = os.path.join("packages", t[1] + ".ad")
                if os.path.exists(p):
                    with open(p, 'r') as f:
                        for l in f:
                            lt = l.split('#')[0].replace(',', '').split()
                            if lt: full_code.append(lt)
                else: self.log(f"[ERR] Lib not found: {t[1]}")
            else: full_code.append(t)
        
        # Interpreter Loop
        labels = {t[0][1:-1]: i for i, t in enumerate(full_code) if t[0].startswith("(")}
        ptr, steps = 0, 0
        MAX_STEPS = 5000
        
        while ptr < len(full_code) and steps < MAX_STEPS:
            t = full_code[ptr]
            cmd = t[0]
            try:
                if cmd == "set": self.registers[t[1]] = int(t[2])
                elif cmd == "add": 
                    val = self.registers[t[2]] if t[2] in self.registers else int(t[2])
                    self.registers[t[1]] += val
                elif cmd == "sub": 
                    val = self.registers[t[2]] if t[2] in self.registers else int(t[2])
                    self.registers[t[1]] -= val
                elif cmd == "check":
                    # Синтаксис: check a1 == 10 then > (LABEL)
                    val1 = self.registers[t[1]]
                    val2 = int(t[3])
                    op = t[2]
                    res = False
                    if op == "==": res = (val1 == val2)
                    elif op == "!=": res = (val1 != val2)
                    elif op == ">": res = (val1 > val2)
                    elif op == "<": res = (val1 < val2)
                    
                    if res and len(t) > 5: 
                         ptr = labels[t[5][1:-1] if t[5].startswith('(') else t[5]]
                         continue

                elif cmd == ">":
                    target = t[1][1:-1] if t[1].startswith('(') else t[1]
                    if target in labels: ptr = labels[target]; continue
                    
                elif cmd == "show": self.log(f"OUT: {t[1]} = {self.registers.get(t[1], 'ERR')}")
            except Exception as e:
                self.log(f"Runtime Err on line {ptr}: {e}")
                break
            ptr += 1; steps += 1
            
        # Update UI Registers
        for r, val in self.registers.items(): self.reg_val_labels[r].config(text=str(val))
        self.log(T("run_end") + f" (Ops: {steps})")

if __name__ == "__main__":
    root = tk.Tk()
    app = AsmDoneIDE(root)
    root.mainloop()