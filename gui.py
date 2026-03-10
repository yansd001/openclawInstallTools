"""OpenClaw 安装配置工具 - GUI 模块"""

import os
import signal
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog

import installer

# ── 配色常量 ──
BG = "#1e1e2e"
BG_SURFACE = "#282840"
BG_INPUT = "#2e2e48"
FG = "#cdd6f4"
FG_DIM = "#a6adc8"
ACCENT = "#89b4fa"
ACCENT_HOVER = "#74c7ec"
GREEN = "#a6e3a1"
RED = "#f38ba8"
YELLOW = "#f9e2af"
BORDER = "#45475a"


class OpenClawApp:
    """OpenClaw 可视化安装配置工具主窗口"""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("OpenClaw 安装配置工具")
        self.root.geometry("1120x850")
        self.root.resizable(True, True)
        self.root.minsize(950, 650)
        self.root.configure(bg=BG)
        self._center_window()
        self._setup_styles()

        # 模型数据
        self.models: list[dict] = []
        self.primary_model: str = installer.DEFAULT_PRIMARY_MODEL

        # 进程跟踪
        self.gateway_proc: subprocess.Popen | None = None

        self._build_ui()
        self._load_existing_config()
        self._refresh_status()

        # 关闭时清理子进程
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _center_window(self):
        self.root.update_idletasks()
        w, h = 1120, 850
        x = (self.root.winfo_screenwidth() - w) // 2
        y = (self.root.winfo_screenheight() - h) // 2
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")

        # 全局背景
        style.configure(".", background=BG, foreground=FG, fieldbackground=BG_INPUT,
                         bordercolor=BORDER, darkcolor=BG_SURFACE, lightcolor=BG_SURFACE,
                         troughcolor=BG_SURFACE, selectbackground=ACCENT, selectforeground=BG,
                         font=("Microsoft YaHei UI", 9))

        # Frame
        style.configure("TFrame", background=BG)
        style.configure("Surface.TFrame", background=BG_SURFACE)

        # Label
        style.configure("TLabel", background=BG, foreground=FG)
        style.configure("Title.TLabel", font=("Microsoft YaHei UI", 18, "bold"),
                         foreground=ACCENT, background=BG)
        style.configure("Section.TLabelframe", background=BG, foreground=FG,
                         bordercolor=BORDER)
        style.configure("Section.TLabelframe.Label", font=("Microsoft YaHei UI", 10, "bold"),
                         foreground=ACCENT, background=BG)
        style.configure("Status.TLabel", foreground=FG_DIM, background=BG)
        style.configure("Green.TLabel", foreground=GREEN, background=BG)
        style.configure("Red.TLabel", foreground=RED, background=BG)
        style.configure("Url.TLabel", foreground=YELLOW, background=BG,
                         font=("Microsoft YaHei UI", 9, "bold"))

        # Entry
        style.configure("TEntry", fieldbackground=BG_INPUT, foreground=FG,
                         insertcolor=FG, bordercolor=BORDER)
        style.map("TEntry",
                   fieldbackground=[("focus", BG_INPUT), ("!focus", BG_INPUT)],
                   bordercolor=[("focus", ACCENT), ("!focus", BORDER)])

        # Button
        style.configure("Action.TButton", font=("Microsoft YaHei UI", 10), padding=8,
                         background=ACCENT, foreground=BG)
        style.map("Action.TButton",
                   background=[("active", ACCENT_HOVER), ("!active", ACCENT)],
                   foreground=[("active", BG), ("!active", BG)])

        style.configure("Small.TButton", font=("Microsoft YaHei UI", 9), padding=4,
                         background=BG_SURFACE, foreground=FG)
        style.map("Small.TButton",
                   background=[("active", BORDER), ("!active", BG_SURFACE)])

        style.configure("Stop.TButton", font=("Microsoft YaHei UI", 10), padding=8,
                         background=RED, foreground=BG)
        style.map("Stop.TButton",
                   background=[("active", "#eba0ac"), ("!active", RED)],
                   foreground=[("active", BG), ("!active", BG)])

        style.configure("Save.TButton", font=("Microsoft YaHei UI", 10, "bold"), padding=10,
                         background=GREEN, foreground=BG)
        style.map("Save.TButton",
                   background=[("active", "#94e2d5"), ("!active", GREEN)],
                   foreground=[("active", BG), ("!active", BG)])

        # Combobox
        style.configure("TCombobox", fieldbackground=BG_INPUT, foreground=FG,
                         background=BG_SURFACE, arrowcolor=FG)
        style.map("TCombobox",
                   fieldbackground=[("readonly", BG_INPUT)],
                   foreground=[("readonly", FG)],
                   bordercolor=[("focus", ACCENT)])

        # Treeview
        style.configure("Treeview", background=BG_INPUT, foreground=FG,
                         fieldbackground=BG_INPUT, bordercolor=BORDER, font=("Microsoft YaHei UI", 9))
        style.configure("Treeview.Heading", background=BG_SURFACE, foreground=ACCENT,
                         font=("Microsoft YaHei UI", 9, "bold"), bordercolor=BORDER)
        style.map("Treeview",
                   background=[("selected", ACCENT)],
                   foreground=[("selected", BG)])

        # Scrollbar
        style.configure("TScrollbar", background=BG_SURFACE, troughcolor=BG,
                         arrowcolor=FG_DIM, bordercolor=BG)

    def _build_ui(self):
        # ── 顶层左右分栏 ──
        top_pane = ttk.Frame(self.root)
        top_pane.pack(fill=tk.BOTH, expand=True)

        # 左侧：可滚动配置区
        left_container = ttk.Frame(top_pane)
        left_container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._canvas = tk.Canvas(left_container, bg=BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(left_container, orient=tk.VERTICAL, command=self._canvas.yview)
        self.scroll_frame = ttk.Frame(self._canvas, padding=20)

        self.scroll_frame.bind("<Configure>",
                               lambda e: self._canvas.configure(scrollregion=self._canvas.bbox("all")))
        self._canvas_window = self._canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")
        self._canvas.configure(yscrollcommand=scrollbar.set)

        # 让 scroll_frame 跟随 canvas 宽度
        self._canvas.bind("<Configure>", self._on_canvas_resize)

        self._canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 鼠标滚轮
        def _on_mousewheel(event):
            self._canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        self._canvas.bind_all("<MouseWheel>", _on_mousewheel)

        # 右侧：日志输出
        right_panel = ttk.LabelFrame(top_pane, text="  日志输出  ",
                                      style="Section.TLabelframe", padding=8)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(0, 8), pady=8)
        right_panel.configure(width=340)
        right_panel.pack_propagate(False)

        self.log_text = scrolledtext.ScrolledText(
            right_panel, font=("Consolas", 9),
            state=tk.DISABLED, wrap=tk.WORD,
            bg=BG_INPUT, fg=FG, insertbackground=FG,
            selectbackground=ACCENT, selectforeground=BG,
            relief=tk.FLAT, borderwidth=0
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)

        main = self.scroll_frame

        # ── 标题 ──
        ttk.Label(main, text="🐾 OpenClaw 安装配置工具", style="Title.TLabel").pack(pady=(0, 15))

        # ── 环境检测 ──
        env_frame = ttk.LabelFrame(main, text="  环境检测  ", style="Section.TLabelframe", padding=12)
        env_frame.pack(fill=tk.X, pady=(0, 10))

        status_grid = ttk.Frame(env_frame)
        status_grid.pack(fill=tk.X)
        status_grid.columnconfigure(1, weight=1)
        status_grid.columnconfigure(3, weight=1)

        self.status_labels = {}
        items = [("node", "Node.js"), ("npm", "npm"), ("uv", "uv"),
                 ("openclaw", "OpenClaw"), ("config", "配置文件"), ("auth", "密钥文件")]
        for i, (key, name) in enumerate(items):
            row, col = divmod(i, 2)
            ttk.Label(status_grid, text=f"{name}:", foreground=FG_DIM).grid(
                row=row, column=col * 2, sticky=tk.W, padx=(0, 6), pady=3
            )
            lbl = ttk.Label(status_grid, text="检测中...", style="Status.TLabel")
            lbl.grid(row=row, column=col * 2 + 1, sticky=tk.W, padx=(0, 20), pady=3)
            self.status_labels[key] = lbl

        btn_row = ttk.Frame(env_frame)
        btn_row.pack(fill=tk.X, pady=(10, 0))
        ttk.Button(btn_row, text="刷新状态", command=self._refresh_status,
                   style="Small.TButton").pack(side=tk.LEFT)
        self.install_btn = ttk.Button(btn_row, text="安装 OpenClaw",
                                       command=self._install_openclaw, style="Action.TButton")
        self.install_btn.pack(side=tk.LEFT, padx=(10, 0))
        self.uninstall_btn = ttk.Button(btn_row, text="卸载 OpenClaw",
                                         command=self._uninstall_openclaw, style="Stop.TButton")
        self.uninstall_btn.pack(side=tk.LEFT, padx=(10, 0))
        self.install_uv_btn = ttk.Button(btn_row, text="安装 uv",
                                          command=self._install_uv, style="Action.TButton")
        self.install_uv_btn.pack(side=tk.LEFT, padx=(10, 0))
        self.uninstall_uv_btn = ttk.Button(btn_row, text="卸载 uv",
                                            command=self._uninstall_uv, style="Stop.TButton")
        self.uninstall_uv_btn.pack(side=tk.LEFT, padx=(10, 0))

        ttk.Label(env_frame, text="💡 uv 是 Skills 安装所需的 Python 包管理器",
                   foreground=FG_DIM, font=("Microsoft YaHei UI", 8)).pack(anchor=tk.W, pady=(8, 0))

        # 启动服务（嵌入环境检测区）
        launch_row = ttk.Frame(env_frame)
        launch_row.pack(fill=tk.X, pady=(10, 0))
        launch_row.columnconfigure(0, weight=1)
        launch_row.columnconfigure(1, weight=1)

        self.gateway_btn = ttk.Button(launch_row, text="🚀 启动 Gateway",
                                       command=self._toggle_gateway, style="Action.TButton")
        self.gateway_btn.grid(row=0, column=0, sticky=tk.EW, padx=(0, 5))

        ttk.Button(launch_row, text="📊 启动 Dashboard",
                   command=self._launch_dashboard, style="Action.TButton"
                   ).grid(row=0, column=1, sticky=tk.EW, padx=(5, 0))

        # ── API 配置 ──
        config_frame = ttk.LabelFrame(main, text="  API 配置  ", style="Section.TLabelframe", padding=12)
        config_frame.pack(fill=tk.X, pady=(0, 10))

        url_row = ttk.Frame(config_frame)
        url_row.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(url_row, text="API Base URL:").pack(side=tk.LEFT)
        ttk.Label(url_row, text=installer.BASE_URL, style="Url.TLabel").pack(side=tk.LEFT, padx=(10, 0))

        key_grid = ttk.Frame(config_frame)
        key_grid.pack(fill=tk.X)
        key_grid.columnconfigure(1, weight=1)

        self.key_vars = {}
        for i, (key, label) in enumerate([
            ("gpt", "GPT API Key:"),
            ("claude", "Claude API Key:"),
            ("google", "Google API Key:"),
            ("other", "Other API Key:"),
        ]):
            ttk.Label(key_grid, text=label, foreground=FG_DIM).grid(
                row=i, column=0, sticky=tk.W, padx=(0, 10), pady=4
            )
            var = tk.StringVar()
            entry = ttk.Entry(key_grid, textvariable=var, show="•")
            entry.grid(row=i, column=1, sticky=tk.EW, pady=4)
            toggle_btn = ttk.Button(key_grid, text="👁", width=3,
                                    command=lambda e=entry: self._toggle_show(e),
                                    style="Small.TButton")
            toggle_btn.grid(row=i, column=2, padx=(5, 0), pady=4)
            self.key_vars[key] = var

        # ── 模型管理 ──
        model_frame = ttk.LabelFrame(main, text="  模型管理  ", style="Section.TLabelframe", padding=12)
        model_frame.pack(fill=tk.X, pady=(0, 10))

        # Workspace
        ws_row = ttk.Frame(model_frame)
        ws_row.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(ws_row, text="Workspace 路径:", foreground=ACCENT,
                   font=("Microsoft YaHei UI", 9, "bold")).pack(side=tk.LEFT)
        self.workspace_var = tk.StringVar(value=installer.DEFAULT_WORKSPACE)
        ws_entry = ttk.Entry(ws_row, textvariable=self.workspace_var)
        ws_entry.pack(side=tk.LEFT, padx=(10, 5), fill=tk.X, expand=True)
        ttk.Button(ws_row, text="📂 浏览", command=self._browse_workspace,
                   style="Small.TButton").pack(side=tk.LEFT)

        # 默认模型
        primary_row = ttk.Frame(model_frame)
        primary_row.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(primary_row, text="默认模型:", foreground=ACCENT,
                   font=("Microsoft YaHei UI", 9, "bold")).pack(side=tk.LEFT)
        self.primary_var = tk.StringVar()
        self.primary_combo = ttk.Combobox(primary_row, textvariable=self.primary_var,
                                           state="readonly", width=55)
        self.primary_combo.pack(side=tk.LEFT, padx=(10, 0), fill=tk.X, expand=True)
        self.primary_combo.bind("<MouseWheel>", lambda e: "break")

        # Treeview
        tree_frame = ttk.Frame(model_frame)
        tree_frame.pack(fill=tk.X)

        columns = ("provider", "model_id", "name")
        self.model_tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=6)
        self.model_tree.heading("provider", text="Provider")
        self.model_tree.heading("model_id", text="模型 ID")
        self.model_tree.heading("name", text="显示名称")
        self.model_tree.column("provider", width=100, minwidth=70)
        self.model_tree.column("model_id", width=260, minwidth=140)
        self.model_tree.column("name", width=180, minwidth=100)

        tree_scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.model_tree.yview)
        self.model_tree.configure(yscrollcommand=tree_scroll.set)
        self.model_tree.pack(side=tk.LEFT, fill=tk.X, expand=True)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # 添加模型行
        add_frame = ttk.Frame(model_frame)
        add_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Label(add_frame, text="Provider:", foreground=FG_DIM).pack(side=tk.LEFT)
        self.add_provider_var = tk.StringVar()
        provider_labels = [p["label"] for p in installer.PROVIDERS.values()]
        self.add_provider_combo = ttk.Combobox(add_frame, textvariable=self.add_provider_var,
                                                values=provider_labels, state="readonly", width=8)
        self.add_provider_combo.pack(side=tk.LEFT, padx=(5, 10))
        self.add_provider_combo.current(0)

        ttk.Label(add_frame, text="模型ID:", foreground=FG_DIM).pack(side=tk.LEFT)
        self.add_model_id_var = tk.StringVar()
        ttk.Entry(add_frame, textvariable=self.add_model_id_var, width=22).pack(side=tk.LEFT, padx=(5, 10))

        ttk.Label(add_frame, text="名称:", foreground=FG_DIM).pack(side=tk.LEFT)
        self.add_model_name_var = tk.StringVar()
        ttk.Entry(add_frame, textvariable=self.add_model_name_var, width=16).pack(side=tk.LEFT, padx=(5, 10))

        ttk.Button(add_frame, text="➕ 添加", command=self._add_model,
                   style="Small.TButton").pack(side=tk.LEFT)

        action_row = ttk.Frame(model_frame)
        action_row.pack(fill=tk.X, pady=(8, 0))
        ttk.Button(action_row, text="🗑 删除选中", command=self._delete_model,
                   style="Small.TButton").pack(side=tk.LEFT)
        ttk.Button(action_row, text="🔄 恢复默认模型", command=self._reset_models,
                   style="Small.TButton").pack(side=tk.LEFT, padx=(10, 0))

        # ── 保存配置 ──
        save_row = ttk.Frame(main)
        save_row.pack(fill=tk.X, pady=(0, 10))
        ttk.Button(save_row, text="💾 保存全部配置", command=self._save_config,
                   style="Save.TButton").pack(fill=tk.X)

    def _on_canvas_resize(self, event):
        """让 scroll_frame 跟随 canvas 宽度，实现响应式布局"""
        self._canvas.itemconfig(self._canvas_window, width=event.width)

    # ── 模型管理方法 ──

    def _browse_workspace(self):
        current = self.workspace_var.get().strip()
        initial = os.path.expandvars(current) if current else ""
        path = filedialog.askdirectory(title="选择 Workspace 目录",
                                        initialdir=initial if os.path.isdir(initial) else "")
        if path:
            self.workspace_var.set(path)

    def _refresh_model_tree(self):
        for item in self.model_tree.get_children():
            self.model_tree.delete(item)
        for m in self.models:
            label = installer.PROVIDERS.get(m["provider"], {}).get("label", m["provider"])
            self.model_tree.insert("", tk.END, values=(label, m["id"], m["name"]))
        self._refresh_primary_combo()

    def _refresh_primary_combo(self):
        options = []
        for m in self.models:
            full_id = f"{m['provider']}/{m['id']}"
            display = f"{m['name']}  ({full_id})"
            options.append(display)
        self.primary_combo["values"] = options

        for i, m in enumerate(self.models):
            if f"{m['provider']}/{m['id']}" == self.primary_model:
                self.primary_combo.current(i)
                return
        if options:
            self.primary_combo.current(0)

    def _get_selected_primary(self) -> str:
        idx = self.primary_combo.current()
        if 0 <= idx < len(self.models):
            m = self.models[idx]
            return f"{m['provider']}/{m['id']}"
        return installer.DEFAULT_PRIMARY_MODEL

    def _provider_label_to_key(self, label: str) -> str:
        for pkey, pinfo in installer.PROVIDERS.items():
            if pinfo["label"] == label:
                return pkey
        return ""

    def _add_model(self):
        provider_label = self.add_provider_var.get().strip()
        model_id = self.add_model_id_var.get().strip()
        model_name = self.add_model_name_var.get().strip()

        if not provider_label or not model_id:
            messagebox.showwarning("提示", "请填写 Provider 和 模型ID")
            return

        provider_key = self._provider_label_to_key(provider_label)
        if not provider_key:
            messagebox.showerror("错误", "无效的 Provider")
            return

        for m in self.models:
            if m["provider"] == provider_key and m["id"] == model_id:
                messagebox.showwarning("提示", f"模型 {model_id} 已存在于 {provider_label}")
                return

        if not model_name:
            model_name = model_id

        self.models.append({
            "provider": provider_key, "id": model_id, "name": model_name,
            "contextWindow": 128000, "maxTokens": 8192,
        })
        self._refresh_model_tree()
        self.add_model_id_var.set("")
        self.add_model_name_var.set("")
        self._log(f"已添加模型: {provider_label}/{model_id} ({model_name})")

    def _delete_model(self):
        selection = self.model_tree.selection()
        if not selection:
            messagebox.showwarning("提示", "请先选择要删除的模型")
            return
        indices = sorted([self.model_tree.index(s) for s in selection], reverse=True)
        for idx in indices:
            removed = self.models.pop(idx)
            self._log(f"已删除模型: {removed['name']} ({removed['id']})")
        self._refresh_model_tree()

    def _reset_models(self):
        if messagebox.askyesno("确认", "确定要恢复为默认模型列表？\n当前列表将被覆盖。"):
            self.models = [m.copy() for m in installer.DEFAULT_MODELS]
            self.primary_model = installer.DEFAULT_PRIMARY_MODEL
            self._refresh_model_tree()
            self._log("已恢复为默认模型列表")

    # ── 内部方法 ──

    def _toggle_show(self, entry: ttk.Entry):
        entry.configure(show="" if entry.cget("show") == "•" else "•")

    def _log(self, msg: str):
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.insert(tk.END, msg + "\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state=tk.DISABLED)

    def _set_status(self, key: str, ok: bool, text: str):
        self.status_labels[key].configure(text=text, style="Green.TLabel" if ok else "Red.TLabel")

    def _refresh_status(self):
        def _check():
            node_ok, node_ver = installer.check_node_installed()
            npm_ok, npm_ver = installer.check_npm_installed()
            uv_ok, uv_ver = installer.check_uv_installed()
            claw_ok, claw_ver = installer.check_openclaw_installed()
            config_exists, auth_exists = installer.check_config_exists()
            self.root.after(0, self._set_status, "node", node_ok,
                           f"✅ {node_ver}" if node_ok else f"❌ {node_ver}")
            self.root.after(0, self._set_status, "npm", npm_ok,
                           f"✅ v{npm_ver}" if npm_ok else f"❌ {npm_ver}")
            self.root.after(0, self._set_status, "uv", uv_ok,
                           f"✅ {uv_ver}" if uv_ok else f"❌ {uv_ver}")
            self.root.after(0, self._set_status, "openclaw", claw_ok,
                           f"✅ {claw_ver}" if claw_ok else f"❌ {claw_ver}")
            self.root.after(0, self._set_status, "config", config_exists,
                           "✅ 已存在" if config_exists else "❌ 未创建")
            self.root.after(0, self._set_status, "auth", auth_exists,
                           "✅ 已存在" if auth_exists else "❌ 未创建")
        threading.Thread(target=_check, daemon=True).start()

    def _load_existing_config(self):
        gpt_key, claude_key, google_key, other_key = installer.read_existing_auth_keys()
        if gpt_key:
            self.key_vars["gpt"].set(gpt_key)
        if claude_key:
            self.key_vars["claude"].set(claude_key)
        if google_key:
            self.key_vars["google"].set(google_key)
        if other_key:
            self.key_vars["other"].set(other_key)
        self.models = installer.read_existing_models()
        self.primary_model = installer.read_existing_primary_model()
        self._refresh_model_tree()
        self.workspace_var.set(installer.read_existing_workspace())

    def _install_openclaw(self):
        node_ok, _ = installer.check_node_installed()
        if not node_ok:
            messagebox.showerror("错误", "请先安装 Node.js！\n下载地址: https://nodejs.org/")
            return
        self.install_btn.configure(state=tk.DISABLED)
        self._log("正在安装 OpenClaw，请稍候...")

        def _run():
            ok, msg = installer.install_openclaw(
                callback=lambda line: self.root.after(0, self._log, line))
            self.root.after(0, self._on_install_done, ok, msg)
        threading.Thread(target=_run, daemon=True).start()

    def _on_install_done(self, ok: bool, msg: str):
        self.install_btn.configure(state=tk.NORMAL)
        if ok:
            self._log("✅ " + msg)
            messagebox.showinfo("成功", msg)
        else:
            self._log("❌ 安装失败: " + msg)
            messagebox.showerror("安装失败", msg)
        self._refresh_status()

    def _save_config(self):
        gpt_key = self.key_vars["gpt"].get().strip()
        claude_key = self.key_vars["claude"].get().strip()
        google_key = self.key_vars["google"].get().strip()
        other_key = self.key_vars["other"].get().strip()

        if not any([gpt_key, claude_key, google_key, other_key]):
            messagebox.showwarning("提示", "请至少填写一个 API Key")
            return
        if not self.models:
            messagebox.showwarning("提示", "模型列表不能为空")
            return

        primary = self._get_selected_primary()
        workspace = self.workspace_var.get().strip() or installer.DEFAULT_WORKSPACE

        ok1, path1 = installer.save_openclaw_config(self.models, primary, workspace)
        if ok1:
            self._log(f"✅ 配置文件已保存: {path1}")
        else:
            self._log(f"❌ 配置文件保存失败: {path1}")
            messagebox.showerror("错误", f"配置文件保存失败:\n{path1}")
            return

        ok2, path2 = installer.save_auth_profiles(gpt_key, claude_key, google_key, other_key)
        if ok2:
            self._log(f"✅ 密钥文件已保存: {path2}")
        else:
            self._log(f"❌ 密钥文件保存失败: {path2}")
            messagebox.showerror("错误", f"密钥文件保存失败:\n{path2}")
            return

        self.primary_model = primary
        messagebox.showinfo("成功", "配置已保存！")
        self._refresh_status()

        # 如果 Gateway 正在运行，自动重启以应用新配置
        if self._is_proc_alive(self.gateway_proc):
            self._log("🔄 检测到 Gateway 正在运行，正在重启以应用新配置...")
            self._stop_process(self.gateway_proc)
            self.gateway_proc = None
            try:
                self.gateway_proc = installer.launch_gateway()
                self.gateway_btn.configure(text="⏹ 停止 Gateway", style="Stop.TButton")
                self._log("✅ Gateway 已重启")
            except Exception as e:
                self.gateway_btn.configure(text="🚀 启动 Gateway", style="Action.TButton")
                self._log(f"❌ Gateway 重启失败: {e}")

    # ── Gateway / Dashboard 启停 ──

    def _is_proc_alive(self, proc: subprocess.Popen | None) -> bool:
        return proc is not None and proc.poll() is None

    def _toggle_gateway(self):
        if self._is_proc_alive(self.gateway_proc):
            self._stop_process(self.gateway_proc)
            self.gateway_proc = None
            self.gateway_btn.configure(text="🚀 启动 Gateway", style="Action.TButton")
            self._log("⏹ Gateway 已停止")
        else:
            claw_ok, _ = installer.check_openclaw_installed()
            if not claw_ok:
                messagebox.showerror("错误", "OpenClaw 未安装，请先安装")
                return
            try:
                self.gateway_proc = installer.launch_gateway()
                self.gateway_btn.configure(text="⏹ 停止 Gateway", style="Stop.TButton")
                self._log("🚀 Gateway 已启动（新窗口）")
            except Exception as e:
                self._log(f"❌ 启动 Gateway 失败: {e}")
                messagebox.showerror("错误", f"启动失败:\n{e}")

    def _launch_dashboard(self):
        claw_ok, _ = installer.check_openclaw_installed()
        if not claw_ok:
            messagebox.showerror("错误", "OpenClaw 未安装，请先安装")
            return
        try:
            installer.launch_dashboard()
            self._log("📊 Dashboard 已启动（新窗口）")
        except Exception as e:
            self._log(f"❌ 启动 Dashboard 失败: {e}")
            messagebox.showerror("错误", f"启动失败:\n{e}")

    def _stop_process(self, proc: subprocess.Popen):
        """终止进程及其子进程树"""
        try:
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW,
            )
        except Exception:
            try:
                proc.terminate()
            except Exception:
                pass

    def _install_uv(self):
        self.install_uv_btn.configure(state=tk.DISABLED)
        self._log("正在安装 uv，请稍候...")

        def _run():
            ok, msg = installer.install_uv(
                callback=lambda line: self.root.after(0, self._log, line))
            self.root.after(0, self._on_install_uv_done, ok, msg)
        threading.Thread(target=_run, daemon=True).start()

    def _on_install_uv_done(self, ok: bool, msg: str):
        self.install_uv_btn.configure(state=tk.NORMAL)
        if ok:
            self._log("✅ " + msg)
            messagebox.showinfo("成功", msg)
        else:
            self._log("❌ uv 安装失败: " + msg)
            messagebox.showerror("安装失败", msg)
        self._refresh_status()

    def _uninstall_uv(self):
        uv_ok, _ = installer.check_uv_installed()
        if not uv_ok:
            messagebox.showinfo("提示", "uv 未安装，无需卸载")
            return
        if not messagebox.askyesno("确认卸载", "确定要卸载 uv 吗？\n这将移除 uv 可执行文件及其缓存数据。"):
            return
        self.uninstall_uv_btn.configure(state=tk.DISABLED)
        self._log("正在卸载 uv，请稍候...")

        def _run():
            ok, msg = installer.uninstall_uv(
                callback=lambda line: self.root.after(0, self._log, line))
            self.root.after(0, self._on_uninstall_uv_done, ok, msg)
        threading.Thread(target=_run, daemon=True).start()

    def _on_uninstall_uv_done(self, ok: bool, msg: str):
        self.uninstall_uv_btn.configure(state=tk.NORMAL)
        if ok:
            self._log("✅ " + msg)
            messagebox.showinfo("成功", msg)
        else:
            self._log("❌ uv 卸载失败: " + msg)
            messagebox.showerror("卸载失败", msg)
        self._refresh_status()

    def _uninstall_openclaw(self):
        claw_ok, _ = installer.check_openclaw_installed()
        config_exists, auth_exists = installer.check_config_exists()
        if not claw_ok and not config_exists and not auth_exists:
            messagebox.showinfo("提示", "OpenClaw 未安装且无配置文件，无需卸载")
            return
        if not messagebox.askyesno(
            "确认卸载",
            "确定要卸载 OpenClaw 吗？\n\n"
            "此操作将：\n"
            "  • 通过 npm 全局卸载 openclaw\n"
            "  • 删除 ~/.openclaw 配置目录（含配置文件、密钥文件等）\n\n"
            "⚠️ 此操作不可撤销！"
        ):
            return
        # 如果 Gateway 正在运行，先停止
        if self._is_proc_alive(self.gateway_proc):
            self._stop_process(self.gateway_proc)
            self.gateway_proc = None
            self.gateway_btn.configure(text="🚀 启动 Gateway", style="Action.TButton")
            self._log("⏹ 已停止 Gateway")
        self.uninstall_btn.configure(state=tk.DISABLED)
        self._log("正在卸载 OpenClaw，请稍候...")

        def _run():
            ok, msg = installer.uninstall_openclaw(
                callback=lambda line: self.root.after(0, self._log, line))
            self.root.after(0, self._on_uninstall_openclaw_done, ok, msg)
        threading.Thread(target=_run, daemon=True).start()

    def _on_uninstall_openclaw_done(self, ok: bool, msg: str):
        self.uninstall_btn.configure(state=tk.NORMAL)
        if ok:
            self._log("✅ " + msg)
            messagebox.showinfo("成功", msg)
        else:
            self._log("❌ OpenClaw 卸载失败: " + msg)
            messagebox.showerror("卸载失败", msg)
        self._refresh_status()

    def _on_close(self):
        """关闭窗口时清理子进程"""
        if self._is_proc_alive(self.gateway_proc):
            self._stop_process(self.gateway_proc)
        self.root.destroy()

    def run(self):
        self.root.mainloop()
