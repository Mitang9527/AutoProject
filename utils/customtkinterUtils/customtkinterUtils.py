import customtkinter
import tkinter as tk
customtkinter.set_appearance_mode("Light")
customtkinter.set_default_color_theme("blue")

class CustomApp(customtkinter.CTk):
    def __init__(self):
        super().__init__()
        self.title("CustomTkinter complex_example.py")
        self.geometry(f"{1100}x{580}")

        # 网格布局配置
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=0)

        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # === 创建侧边栏 ===
        self.sidebar_frame = customtkinter.CTkFrame(self, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, rowspan=5, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(20, weight=1)

        self.logo_label = customtkinter.CTkLabel(self.sidebar_frame, text="CustomTkinter",
                                                 font=customtkinter.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=25, pady=(20, 10))

        self.sidebar_button_1 = customtkinter.CTkButton(self.sidebar_frame, command=self.sidebar_button_event)
        self.sidebar_button_1.grid(row=1, column=0, padx=20, pady=10)

        self.sidebar_button_2 = customtkinter.CTkButton(self.sidebar_frame, command=self.sidebar_button_event)
        self.sidebar_button_2.grid(row=2, column=0, padx=20, pady=10)

        self.sidebar_button_3 = customtkinter.CTkButton(self.sidebar_frame, command=self.sidebar_button_event)
        self.sidebar_button_3.grid(row=3, column=0, padx=20, pady=10)

        self.ctk_optionmenu = customtkinter.CTkOptionMenu(
            self.sidebar_frame,
            values=["选项1", "选项2", "选项3"],
            command=self.optionmenu_callback)
        self.ctk_optionmenu.grid(row=4, column=0, padx=20, pady=10)

        self.appearance_mode_label = customtkinter.CTkLabel(self.sidebar_frame, text="Appearance Mode:", anchor="w")
        self.appearance_mode_label.grid(row=21, column=0, padx=20, pady=(10, 0))

        self.appearance_mode_optionemenu = customtkinter.CTkOptionMenu(
            self.sidebar_frame, values=["Light", "Dark", "System"],
            command=self.change_appearance_mode_event)
        self.appearance_mode_optionemenu.grid(row=22, column=0, padx=20, pady=(10, 10))

        self.scaling_label = customtkinter.CTkLabel(self.sidebar_frame, text="UI Scaling:", anchor="w")
        self.scaling_label.grid(row=23, column=0, padx=20, pady=(10, 0))

        self.scaling_optionemenu = customtkinter.CTkOptionMenu(
            self.sidebar_frame, values=["80%", "90%", "100%", "110%", "120%"],
            command=self.change_scaling_event)
        self.scaling_optionemenu.grid(row=24, column=0, padx=20, pady=(10, 20))

        # === 搜索框 ===
        self.search_entry = customtkinter.CTkEntry(self, placeholder_text="搜索关键词")
        self.search_entry.grid(row=0, column=1, padx=(20, 5), pady=(10, 0), sticky="ew")
        self.search_entry.bind("<KeyRelease>", self.on_search_entry_change)

        # === 搜索按钮区域 ===
        self.search_button_frame = customtkinter.CTkFrame(self)
        self.search_button_frame.grid(row=0, column=2, padx=(5, 20), pady=(10, 0), sticky="w")

        self.search_prev_button = customtkinter.CTkButton(
            self.search_button_frame, text="↑", width=25, command=self.search_previous
        )
        self.search_prev_button.pack(side="left", padx=5)

        self.search_next_button = customtkinter.CTkButton(
            self.search_button_frame, text="↓", width=25, command=self.search_next
        )
        self.search_next_button.pack(side="left", padx=5)

        # === JSON 显示窗口 ===
        self.json_textbox = customtkinter.CTkTextbox(self, font=("Courier", 12))
        self.json_textbox.grid(row=1, column=1, padx=(20, 5), pady=(10, 0), sticky="nsew")

        # === JSON 保存按钮 ===
        self.save_json_button = customtkinter.CTkButton(
            self, text="保存", width=68, command=self.sidebar_button_event
        )
        self.save_json_button.grid(row=1, column=2, padx=(8, 20), pady=(10, 0), sticky="n")

        # === 日志窗口 ===
        self.textbox = customtkinter.CTkTextbox(self, font=("Courier", 12))
        self.textbox.grid(row=2, column=1, columnspan=2, padx=(20, 20), pady=(10, 20), sticky="nsew")
        self.textbox.configure(state="disabled")

        # 默认设置
        self.appearance_mode_optionemenu.set("Light")
        self.scaling_optionemenu.set("100%")
        self.sidebar_button_3.configure(state="disabled", text="CTkButton")
        self.ctk_optionmenu.set("选项1")
        self.last_search_index = "1.0"  # 初始化搜索索引

    def create_sidebar_button(self, text, row, command):
        customtkinter.CTkButton(
            self.sidebar_frame,
            text=text,
            command=command
        ).grid(row=row, column=0, padx=20, pady=10)

    def create_optionmenu(self, values, row, command):
        self.ctk_optionmenu = customtkinter.CTkOptionMenu(
            self.sidebar_frame,
            values=values,
            command=command
        )
        self.ctk_optionmenu.grid(row=row, column=0, padx=20, pady=10)

    def sidebar_button_event(self):
        pass

    def change_appearance_mode_event(self, new_appearance_mode: str):
        customtkinter.set_appearance_mode(new_appearance_mode)

    def change_scaling_event(self, new_scaling: str):
        new_scaling_float = int(new_scaling.replace("%", "")) / 100
        customtkinter.set_widget_scaling(new_scaling_float)

    def optionmenu_callback(self, choice):
        pass

    def search_previous(self):
        self.search_term = self.search_entry.get()
        if not self.search_term:
            return

        current_index = self.json_textbox.index(self.last_search_index)
        text_before = self.json_textbox.get("1.0", current_index)

        idx = text_before.lower().rfind(self.search_term.lower())
        if idx != -1:
            line = text_before.count("\n", 0, idx) + 1
            col = idx - text_before.rfind("\n", 0, idx) - 1 if "\n" in text_before[:idx] else idx
            pos = f"{line}.{col}"
            end_pos = f"{pos}+{len(self.search_term)}c"
            self.clear_highlight()
            self.json_textbox.tag_add("highlight", pos, end_pos)
            self.json_textbox.tag_config("highlight", background="yellow", foreground="black")
            self.json_textbox.mark_set(tk.INSERT, pos)
            self.json_textbox.see(pos)
            self.last_search_index = pos
        else:
            self.last_search_index = tk.END

    def search_next(self):
        self.search_term = self.search_entry.get()
        if not self.search_term:
            return

        pos = self.json_textbox.search(self.search_term, self.last_search_index, stopindex=tk.END, nocase=True)
        if pos:
            end_pos = f"{pos}+{len(self.search_term)}c"
            self.clear_highlight()
            self.json_textbox.tag_add("highlight", pos, end_pos)
            self.json_textbox.tag_config("highlight", background="yellow", foreground="black")
            self.json_textbox.mark_set(tk.INSERT, end_pos)
            self.json_textbox.see(pos)
            self.last_search_index = end_pos
        else:
            self.last_search_index = "1.0"

    def on_search_entry_change(self, event=None):
        self.last_search_index = "1.0"
        self.highlight_all_matches()

    def highlight_all_matches(self):
        self.clear_highlight()
        keyword = self.search_entry.get()
        if not keyword:
            return
        start = "1.0"
        while True:
            start = self.json_textbox.search(keyword, start, stopindex=tk.END, nocase=True)
            if not start:
                break
            end = f"{start}+{len(keyword)}c"
            self.json_textbox.tag_add("highlight", start, end)
            self.json_textbox.tag_config("highlight", background="yellow", foreground="black")
            start = end

    def clear_highlight(self):
        self.json_textbox.tag_delete("highlight")

    def show_message(self, title: str, content: str):
        popup = customtkinter.CTkToplevel(self)
        popup.title(title)
        popup.geometry("400x180")
        popup.grab_set()  # 模态弹窗

        # ---------- 内容显示框，可复制 ----------
        text_widget = customtkinter.CTkTextbox(popup, width=360, height=80)
        text_widget.pack(pady=10)
        text_widget.insert("1.0", content)
        text_widget.configure(state="disabled")  # 只读

        def copy_to_clipboard():
            if ":" in content:
                to_copy = content.split(":", 1)[1].strip()
            else:
                to_copy = content
            self.clipboard_clear()
            self.clipboard_append(to_copy)
            self.update()

        btn_copy = customtkinter.CTkButton(popup, text="复制", command=copy_to_clipboard)
        btn_copy.pack(pady=5)

        # # ---------- 确认按钮 ----------
        # btn_ok = customtkinter.CTkButton(popup, text="确定", command=popup.destroy)
        # btn_ok.pack(pady=5)


if __name__ == '__main__':
    app =CustomApp()
    app.mainloop()