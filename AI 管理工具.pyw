# -*- coding: utf-8 -*-
"""
AI CLI 管理工具 - GUI 版本
双击直接启动，无控制台窗口
功能：安装/更新/卸载/启动/检查更新
"""

import customtkinter as ctk
import subprocess
import threading
import os
import signal
from typing import Dict, Optional

# 设置外观
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# CLI 工具配置
CLI_TOOLS: Dict[str, dict] = {
    'qwen': {
        'name': 'Qwen Code',
        'package': '@qwen-code/qwen-code',
        'command': 'qwen',
        'description': '通义千问代码助手',
        'icon': '🤖'
    },
    'gemini': {
        'name': 'Gemini CLI',
        'package': '@google/gemini-cli',
        'command': 'gemini',
        'description': 'Google Gemini 代码助手',
        'icon': '✨'
    },
    'codex': {
        'name': 'OpenAI Codex',
        'package': '@openai/codex',
        'command': 'codex',
        'description': 'OpenAI Codex 代码工具',
        'icon': '🧠'
    }
}


def get_latest_version(package: str) -> str:
    """获取 npm 最新版本"""
    try:
        result = subprocess.run(
            f'npm view {package} version',
            shell=True,
            capture_output=True,
            text=True,
            encoding='utf-8',
            timeout=10
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return ""


def compare_versions(v1: str, v2: str) -> int:
    """比较版本号，返回 -1(小于), 0(等于), 1(大于)"""
    def normalize(v):
        parts = []
        for p in v.split('.'):
            num = ''
            for c in p:
                if c.isdigit():
                    num += c
                else:
                    break
            parts.append(int(num) if num else 0)
        return parts
    
    p1 = normalize(v1)
    p2 = normalize(v2)
    
    while len(p1) < len(p2):
        p1.append(0)
    while len(p2) < len(p1):
        p2.append(0)
    
    for a, b in zip(p1, p2):
        if a < b:
            return -1
        elif a > b:
            return 1
    return 0


class ToolCard(ctk.CTkFrame):
    """工具卡片组件"""
    
    def __init__(self, master, tool_key: str, tool_info: dict, callback):
        super().__init__(master, corner_radius=10, fg_color="#2b2b2b")
        
        self.tool_key = tool_key
        self.tool_info = tool_info
        self.callback = callback
        self.installed = False
        self.version = ""
        self.latest_version = ""
        self.has_update = False
        self.running_process: Optional[subprocess.Popen] = None
        self.is_running = False
        
        self._setup_ui()
        self._check_status()
    
    def _setup_ui(self):
        """设置 UI"""
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=0)
        
        # 左侧信息
        info_frame = ctk.CTkFrame(self, fg_color="transparent")
        info_frame.grid(row=0, column=0, padx=15, pady=15, sticky="w")
        info_frame.grid_columnconfigure(0, weight=1)
        
        # 图标和名称
        name_frame = ctk.CTkFrame(info_frame, fg_color="transparent")
        name_frame.grid(row=0, column=0, sticky="w")
        
        icon_label = ctk.CTkLabel(
            name_frame,
            text=self.tool_info.get('icon', '📦'),
            font=ctk.CTkFont(size=18)
        )
        icon_label.grid(row=0, column=0, padx=(0, 8))
        
        name_label = ctk.CTkLabel(
            name_frame,
            text=self.tool_info['name'],
            font=ctk.CTkFont(size=16, weight="bold"),
            anchor="w"
        )
        name_label.grid(row=0, column=1, sticky="w")
        
        # 描述
        desc_label = ctk.CTkLabel(
            info_frame,
            text=self.tool_info['description'],
            text_color="#888888",
            font=ctk.CTkFont(size=12),
            anchor="w"
        )
        desc_label.grid(row=1, column=0, sticky="w", pady=(5, 0))
        
        # 包名
        pkg_label = ctk.CTkLabel(
            info_frame,
            text=f"包：{self.tool_info['package']}",
            text_color="#666666",
            font=ctk.CTkFont(size=10),
            anchor="w"
        )
        pkg_label.grid(row=2, column=0, sticky="w", pady=(5, 0))
        
        # 状态和运行状态标签
        self.status_frame = ctk.CTkFrame(info_frame, fg_color="transparent")
        self.status_frame.grid(row=3, column=0, sticky="w", pady=(5, 0))
        
        self.status_label = ctk.CTkLabel(
            self.status_frame,
            text="检查中...",
            text_color="#ffa500",
            font=ctk.CTkFont(size=12),
            anchor="w"
        )
        self.status_label.grid(row=0, column=0, padx=(0, 10))
        
        # 更新提示标签
        self.update_label = ctk.CTkLabel(
            self.status_frame,
            text="",
            text_color="#ff9800",
            font=ctk.CTkFont(size=11, weight="bold"),
            anchor="w"
        )
        self.update_label.grid(row=0, column=1, padx=(0, 10))
        
        # 运行状态标签
        self.running_label = ctk.CTkLabel(
            self.status_frame,
            text="",
            text_color="#00ff00",
            font=ctk.CTkFont(size=11, weight="bold"),
            anchor="w"
        )
        self.running_label.grid(row=0, column=2, padx=(0, 10))
        
        # 右侧按钮
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=0, column=1, padx=15, pady=15, sticky="e")
        btn_frame.grid_columnconfigure(0, weight=1)
        btn_frame.grid_columnconfigure(1, weight=1)
        btn_frame.grid_columnconfigure(2, weight=1)
        
        # 启动/停止按钮
        self.launch_btn = ctk.CTkButton(
            btn_frame,
            text="启动",
            width=60,
            height=30,
            fg_color="#2196F3",
            hover_color="#1976D2",
            command=self._on_launch,
            state="disabled"
        )
        self.launch_btn.grid(row=0, column=0, padx=3)
        
        # 操作按钮（安装/更新）- 初始隐藏
        self.action_btn = ctk.CTkButton(
            btn_frame,
            text="安装",
            width=60,
            height=30,
            command=self._on_action
        )
        self.action_btn.grid(row=0, column=1, padx=3)
        
        # 信息按钮
        info_btn = ctk.CTkButton(
            btn_frame,
            text="ℹ️",
            width=35,
            height=30,
            fg_color="#444444",
            hover_color="#555555",
            command=self._show_info
        )
        info_btn.grid(row=0, column=2, padx=3)
    
    def _check_status(self):
        """检查工具状态和更新"""
        def check():
            # 检查是否安装
            try:
                result = subprocess.run(
                    f"{self.tool_info['command']} --version",
                    shell=True,
                    capture_output=True,
                    text=True,
                    encoding='utf-8'
                )
                if result.returncode == 0:
                    self.installed = True
                    self.version = result.stdout.strip()
                    self.after(0, self._update_status_installed)
                else:
                    self.installed = False
                    self.after(0, self._update_status_not_installed)
            except Exception:
                self.installed = False
                self.after(0, self._update_status_not_installed)
            
            # 自动检查最新版本
            latest = get_latest_version(self.tool_info['package'])
            if latest:
                self.latest_version = latest
                if self.installed and compare_versions(self.version, latest) < 0:
                    self.has_update = True
                    self.after(0, self._show_update_available)
                elif self.installed:
                    self.after(0, lambda: self.update_label.configure(text="✓ 最新"))
        
        threading.Thread(target=check, daemon=True).start()
    
    def _update_status_installed(self):
        """更新为已安装状态"""
        self.status_label.configure(
            text=f"✓ v{self.version}",
            text_color="#00ff00"
        )
        self.launch_btn.configure(state="normal")
        
        # 如果有更新才显示更新按钮，否则隐藏
        if self.has_update:
            self.action_btn.configure(
                text="更新",
                fg_color="#ff9800",
                hover_color="#f57c00"
            )
            self.action_btn.grid(row=0, column=1, padx=3)
        else:
            self.action_btn.grid_remove()
    
    def _update_status_not_installed(self):
        """更新为未安装状态"""
        self.status_label.configure(
            text="✗ 未安装",
            text_color="#ff4444"
        )
        self.launch_btn.configure(state="disabled")
        self.update_label.configure(text="")
        self.running_label.configure(text="")
        # 未安装时显示安装按钮
        self.action_btn.configure(
            text="安装",
            fg_color="#4CAF50",
            hover_color="#45a049"
        )
        self.action_btn.grid(row=0, column=1, padx=3)
    
    def _show_update_available(self):
        """显示有更新可用"""
        self.update_label.configure(
            text=f"🔔 新版本：{self.latest_version}"
        )
    
    def _on_action(self):
        """操作按钮点击"""
        if self.installed:
            self.callback('update', self.tool_key)
        else:
            self.callback('install', self.tool_key)
    
    def _on_launch(self):
        """启动/停止工具"""
        if self.is_running:
            self.callback('stop', self.tool_key)
        else:
            self.callback('launch', self.tool_key)
    
    def _show_info(self):
        """显示信息"""
        self.callback('info', self.tool_key)
    
    def set_installing(self):
        """设置安装中状态"""
        self.action_btn.configure(text="安装中...", state="disabled")
        self.action_btn.grid(row=0, column=1, padx=3)
    
    def set_updating(self):
        """设置更新中状态"""
        self.action_btn.configure(text="更新中...", state="disabled")
        self.action_btn.grid(row=0, column=1, padx=3)
    
    def set_removing(self):
        """设置卸载中状态"""
        self.action_btn.configure(text="卸载中...", state="disabled")
        self.action_btn.grid(row=0, column=1, padx=3)
    
    def reset_button(self):
        """重置按钮状态"""
        self.installed = False
        self.version = ""
        self.latest_version = ""
        self.has_update = False
        self._check_status()
    
    def set_running(self, process: subprocess.Popen):
        """设置运行状态"""
        self.is_running = True
        self.running_process = process
        self.running_label.configure(text="● 运行中")
        self.launch_btn.configure(
            text="停止",
            fg_color="#f44336",
            hover_color="#e53935"
        )
    
    def set_stopped(self):
        """设置停止状态"""
        self.is_running = False
        self.running_process = None
        self.running_label.configure(text="")
        self.launch_btn.configure(
            text="启动",
            fg_color="#2196F3",
            hover_color="#1976D2"
        )


class MainWindow(ctk.CTk):
    """主窗口"""
    
    def __init__(self):
        super().__init__()
        
        self.title("AI CLI 管理工具")
        self.geometry("1000x750")
        self.minsize(900, 650)
        
        # 存储启动的进程
        self.processes: Dict[str, subprocess.Popen] = {}
        
        self._setup_ui()
        self._refresh_all_status()
        
        # 窗口关闭时清理进程
        self.protocol("WM_DELETE_WINDOW", self._on_closing)
    
    def _setup_ui(self):
        """设置 UI"""
        # 主容器
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        # 标题栏
        header_frame = ctk.CTkFrame(self, fg_color="#1a1a2e", height=80)
        header_frame.grid(row=0, column=0, sticky="ew")
        header_frame.grid_propagate(False)
        header_frame.grid_columnconfigure(0, weight=1)
        
        title_label = ctk.CTkLabel(
            header_frame,
            text="🤖 AI CLI 管理工具",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title_label.grid(row=0, column=0, pady=20)
        
        subtitle_label = ctk.CTkLabel(
            header_frame,
            text="管理你的 AI 代码助手 - Qwen | Gemini | Codex",
            text_color="#888888",
            font=ctk.CTkFont(size=12)
        )
        subtitle_label.grid(row=1, column=0, pady=(0, 15))
        
        # 滚动容器
        scroll_frame = ctk.CTkScrollableFrame(self, fg_color="#1e1e1e")
        scroll_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=20)
        scroll_frame.grid_columnconfigure(0, weight=1)
        
        # 工具卡片
        self.tool_cards = {}
        for idx, (key, info) in enumerate(CLI_TOOLS.items()):
            card = ToolCard(scroll_frame, key, info, self._on_tool_action)
            card.grid(row=idx, column=0, sticky="ew", padx=10, pady=10)
            self.tool_cards[key] = card
        
        # 底部操作栏
        bottom_frame = ctk.CTkFrame(self, fg_color="#252525", height=60)
        bottom_frame.grid(row=2, column=0, sticky="ew")
        bottom_frame.grid_propagate(False)
        bottom_frame.grid_columnconfigure(0, weight=1)
        
        # 左侧按钮
        left_frame = ctk.CTkFrame(bottom_frame, fg_color="transparent")
        left_frame.grid(row=0, column=0, padx=20, sticky="w")
        
        refresh_btn = ctk.CTkButton(
            left_frame,
            text="🔄 刷新",
            width=80,
            height=35,
            command=self._refresh_all_status
        )
        refresh_btn.pack(side="left", padx=5)
        
        # 停止全部按钮
        self.stop_all_btn = ctk.CTkButton(
            left_frame,
            text="⏹️ 停止全部",
            width=100,
            height=35,
            fg_color="#f44336",
            hover_color="#e53935",
            command=self._stop_all_tools
        )
        self.stop_all_btn.pack(side="left", padx=5)
        
        # 右侧按钮
        right_frame = ctk.CTkFrame(bottom_frame, fg_color="transparent")
        right_frame.grid(row=0, column=0, padx=20, sticky="e")
        
        install_all_btn = ctk.CTkButton(
            right_frame,
            text="全部安装",
            width=90,
            height=35,
            fg_color="#4CAF50",
            hover_color="#45a049",
            command=lambda: self._batch_action('install')
        )
        install_all_btn.pack(side="left", padx=5)
        
        update_all_btn = ctk.CTkButton(
            right_frame,
            text="全部更新",
            width=90,
            height=35,
            fg_color="#ff9800",
            hover_color="#f57c00",
            command=lambda: self._batch_action('update')
        )
        update_all_btn.pack(side="left", padx=5)
        
        remove_all_btn = ctk.CTkButton(
            right_frame,
            text="全部卸载",
            width=90,
            height=35,
            fg_color="#f44336",
            hover_color="#e53935",
            command=lambda: self._batch_action('remove')
        )
        remove_all_btn.pack(side="left", padx=5)
        
        # 状态栏
        self.status_bar = ctk.CTkLabel(
            self,
            text="就绪",
            text_color="#666666",
            font=ctk.CTkFont(size=11),
            anchor="w"
        )
        self.status_bar.grid(row=3, column=0, sticky="ew", padx=20, pady=5)
    
    def _on_tool_action(self, action: str, tool_key: str):
        """工具操作回调"""
        if action == 'install':
            self._install_tool(tool_key)
        elif action == 'update':
            self._update_tool(tool_key)
        elif action == 'remove':
            self._remove_tool(tool_key)
        elif action == 'launch':
            self._launch_tool(tool_key)
        elif action == 'stop':
            self._stop_tool(tool_key)
        elif action == 'info':
            self._show_tool_info(tool_key)
    
    def _install_tool(self, tool_key: str):
        """安装工具"""
        tool = CLI_TOOLS.get(tool_key)
        if not tool:
            return
        
        card = self.tool_cards.get(tool_key)
        if card:
            card.set_installing()
        
        self.status_bar.configure(text=f"正在安装 {tool['name']}...")
        
        def install():
            result = subprocess.run(
                f"npm install -g {tool['package']}",
                shell=True,
                capture_output=True,
                text=True,
                encoding='utf-8'
            )
            
            def update():
                if result.returncode == 0:
                    self.status_bar.configure(text=f"✓ {tool['name']} 安装成功")
                else:
                    self.status_bar.configure(text=f"✗ {tool['name']} 安装失败")
                if card:
                    card.reset_button()
            
            self.after(0, update)
        
        threading.Thread(target=install, daemon=True).start()
    
    def _update_tool(self, tool_key: str):
        """更新工具"""
        tool = CLI_TOOLS.get(tool_key)
        if not tool:
            return
        
        card = self.tool_cards.get(tool_key)
        if card:
            card.set_updating()
        
        self.status_bar.configure(text=f"正在更新 {tool['name']}...")
        
        def update():
            result = subprocess.run(
                f"npm install -g {tool['package']}@latest",
                shell=True,
                capture_output=True,
                text=True,
                encoding='utf-8'
            )
            
            def callback():
                if result.returncode == 0:
                    self.status_bar.configure(text=f"✓ {tool['name']} 更新成功")
                else:
                    self.status_bar.configure(text=f"✗ {tool['name']} 更新失败")
                if card:
                    card.reset_button()
            
            self.after(0, callback)
        
        threading.Thread(target=update, daemon=True).start()
    
    def _remove_tool(self, tool_key: str):
        """卸载工具"""
        tool = CLI_TOOLS.get(tool_key)
        if not tool:
            return
        
        # 先停止运行中的进程
        if tool_key in self.processes:
            self._stop_tool(tool_key)
        
        # 确认对话框
        dialog = ctk.CTkInputDialog(
            title="确认卸载",
            text=f"确定要卸载 {tool['name']} 吗？\n\n输入 'yes' 确认:",
        )
        confirm = dialog.get_input()
        
        if confirm != 'yes':
            card = self.tool_cards.get(tool_key)
            if card:
                card.reset_button()
            return
        
        card = self.tool_cards.get(tool_key)
        if card:
            card.set_removing()
        
        self.status_bar.configure(text=f"正在卸载 {tool['name']}...")
        
        def remove():
            result = subprocess.run(
                f"npm uninstall -g {tool['package']}",
                shell=True,
                capture_output=True,
                text=True,
                encoding='utf-8'
            )
            
            def callback():
                if result.returncode == 0:
                    self.status_bar.configure(text=f"✓ {tool['name']} 卸载成功")
                else:
                    self.status_bar.configure(text=f"✗ {tool['name']} 卸载失败")
                if card:
                    card.reset_button()
            
            self.after(0, callback)
        
        threading.Thread(target=remove, daemon=True).start()
    
    def _launch_tool(self, tool_key: str):
        """启动工具 - 只关闭自己启动的进程"""
        tool = CLI_TOOLS.get(tool_key)
        if not tool:
            return
        
        card = self.tool_cards.get(tool_key)
        if not card:
            return
        
        self.status_bar.configure(text=f"正在启动 {tool['name']}...")
        
        try:
            # 启动新进程，记录 PID
            process = subprocess.Popen(
                f"{tool['command']}",
                shell=True,
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )
            
            # 存储进程引用
            self.processes[tool_key] = process
            
            def check_process():
                """检查进程是否还在运行"""
                if tool_key in self.processes:
                    if self.processes[tool_key].poll() is not None:
                        # 进程已结束
                        self.after(0, lambda: self._on_tool_exited(tool_key))
                    else:
                        # 继续检查
                        self.after(1000, check_process)
            
            check_process()
            
            # 更新 UI
            self.after(0, lambda: self.status_bar.configure(text=f"✓ {tool['name']} 已启动 (PID: {process.pid})"))
            self.after(0, lambda: card.set_running(process))
            
        except Exception as e:
            self.after(0, lambda: self.status_bar.configure(text=f"✗ 启动失败：{str(e)}"))
    
    def _stop_tool(self, tool_key: str):
        """停止工具 - 只关闭自己启动的进程"""
        tool = CLI_TOOLS.get(tool_key)
        if not tool:
            return
        
        # 只关闭我们启动的进程
        if tool_key in self.processes:
            process = self.processes[tool_key]
            try:
                # 获取进程 PID
                pid = process.pid
                
                # Windows 上使用 taskkill 终止进程树
                subprocess.run(
                    f'taskkill /F /T /PID {pid}',
                    shell=True,
                    capture_output=True
                )
                
                self.status_bar.configure(text=f"✓ {tool['name']} 已停止")
                
            except Exception as e:
                self.status_bar.configure(text=f"✗ 停止失败：{str(e)}")
            finally:
                del self.processes[tool_key]
        
        # 更新卡片 UI
        card = self.tool_cards.get(tool_key)
        if card:
            self.after(0, lambda: card.set_stopped())
    
    def _on_tool_exited(self, tool_key: str):
        """工具进程退出后的处理"""
        if tool_key in self.processes:
            del self.processes[tool_key]
        
        card = self.tool_cards.get(tool_key)
        if card:
            self.after(0, lambda: card.set_stopped())
        
        self.status_bar.configure(text=f"ℹ️ {CLI_TOOLS.get(tool_key, {}).get('name', '工具')} 已退出")
    
    def _stop_all_tools(self):
        """停止所有运行中的工具"""
        running_tools = [key for key in self.processes if key in self.processes]
        
        if not running_tools:
            self.status_bar.configure(text="没有运行中的工具")
            return
        
        for tool_key in running_tools:
            self._stop_tool(tool_key)
        
        self.status_bar.configure(text=f"✓ 已停止 {len(running_tools)} 个工具")
    
    def _show_tool_info(self, tool_key: str):
        """显示工具信息"""
        tool = CLI_TOOLS.get(tool_key)
        if not tool:
            return
        
        card = self.tool_cards.get(tool_key)
        version = card.version if card else "未知"
        latest = card.latest_version if card else "未知"
        has_update = card.has_update if card else False
        is_running = card.is_running if card else False
        
        update_status = ""
        if has_update:
            update_status = f"🔔 有更新可用 (最新：{latest})"
        elif card and card.installed:
            update_status = "✓ 已是最新版本"
        else:
            update_status = "未安装"
        
        run_status = "● 运行中" if is_running else "○ 未运行"
        
        # 获取进程 PID
        pid_info = ""
        if tool_key in self.processes:
            pid_info = f"\n进程 PID: {self.processes[tool_key].pid}"
        
        info_text = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  {tool['icon']} {tool['name']}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  键名：{tool_key}
  包名：{tool['package']}
  命令：{tool['command']}
  描述：{tool['description']}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  当前版本：{version}
  最新版本：{latest}
  更新状态：{update_status}
  运行状态：{run_status}{pid_info}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

        info_window = ctk.CTkToplevel(self)
        info_window.title(f"{tool['icon']} {tool['name']} - 信息")
        info_window.geometry("480x400")
        info_window.resizable(False, False)
        
        # 设置窗口置顶，防止跑到主窗口后面
        info_window.attributes('-topmost', True)
        self.after(200, lambda: info_window.attributes('-topmost', False))

        # 居中显示
        info_window.update_idletasks()
        x = (info_window.winfo_screenwidth() - 480) // 2
        y = (info_window.winfo_screenheight() - 400) // 2
        info_window.geometry(f"+{x}+{y}")

        text_box = ctk.CTkTextbox(info_window, wrap="word", font=ctk.CTkFont(size=13))
        text_box.pack(fill="both", expand=True, padx=20, pady=20)
        text_box.insert("0.0", info_text.strip())
        text_box.configure(state="disabled")
    
    def _refresh_all_status(self):
        """刷新所有状态并检查更新"""
        self.status_bar.configure(text="正在检查更新...")
        
        for card in self.tool_cards.values():
            card.reset_button()
        
        self.status_bar.configure(text="就绪 - 已自动检查更新")
    
    def _batch_action(self, action: str):
        """批量操作"""
        if action == 'install':
            self.status_bar.configure(text="正在安装所有工具...")
            for key in CLI_TOOLS:
                self._install_tool(key)
        elif action == 'update':
            self.status_bar.configure(text="正在更新所有工具...")
            for key in CLI_TOOLS:
                card = self.tool_cards.get(key)
                if card and card.installed:
                    self._update_tool(key)
        elif action == 'remove':
            self.status_bar.configure(text="正在卸载所有工具...")
            for key in CLI_TOOLS:
                self._remove_tool(key)
    
    def _on_closing(self):
        """窗口关闭时清理进程"""
        if self.processes:
            # 询问是否关闭运行中的工具
            dialog = ctk.CTkInputDialog(
                title="确认关闭",
                text=f"有 {len(self.processes)} 个工具正在运行\n\n输入 'yes' 关闭所有工具并退出，直接关闭将留下后台进程:",
            )
            confirm = dialog.get_input()
            
            if confirm == 'yes':
                self._stop_all_tools()
        
        self.destroy()


def main():
    """主函数"""
    app = MainWindow()
    
    # 窗口居中
    app.update_idletasks()
    width = 1000
    height = 750
    x = (app.winfo_screenwidth() - width) // 2
    y = (app.winfo_screenheight() - height) // 2
    app.geometry(f'{width}x{height}+{x}+{y}')
    
    app.mainloop()


if __name__ == '__main__':
    main()
