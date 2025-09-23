import tkinter as tk
import customtkinter

customtkinter.set_appearance_mode("Light")
customtkinter.set_default_color_theme("blue")


class CustomApp(customtkinter.CTk):
    def __init__(self):
        super().__init__()
        self.title("CustomTkinter complex_example.py")
        self.geometry(f"{1100}x{580}")

        # ===== 父窗口网格布局 =====
        self.grid_columnconfigure(0, weight=0)  # 左侧操作区
        self.grid_columnconfigure(1, weight=0)  # 右侧侧边栏
        self.grid_columnconfigure(2, weight=1)  # 主内容区
        self.grid_columnconfigure(3, weight=0)  # 右侧操作按钮列
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # ===== 左侧操作区 =====
        self.middle_button_frame = customtkinter.CTkFrame(self, width=200, corner_radius=0)
        self.middle_button_frame.grid(row=0, column=0, rowspan=3, sticky="nsew", padx=5, pady=10)
        self.middle_button_frame.grid_rowconfigure(10, weight=1)

        self.middle_logo_label = customtkinter.CTkLabel(
            self.middle_button_frame,
            text="CustomTkinter",
            font=customtkinter.CTkFont(size=20, weight="bold")
        )
        self.middle_logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        self.create_middle_button_1 = customtkinter.CTkButton(self.middle_button_frame,1, text="按钮1",command=self.optionmenu_callback)
        self.create_middle_button_1.grid(row=1, column=0, padx=20, pady=10, sticky="ew")

        self.middle_button_2 = customtkinter.CTkButton(self.middle_button_frame,1, text="按钮2",command=self.optionmenu_callback)
        self.middle_button_2.grid(row=2, column=0, padx=20, pady=10, sticky="ew")

        # 底部固定控件
        self.appearance_mode_label = customtkinter.CTkLabel(self.middle_button_frame, text="Appearance Mode:")
        self.appearance_mode_label.grid(row=11, column=0, padx=20, pady=(10, 0), sticky="s")

        self.appearance_mode_optionemenu = customtkinter.CTkOptionMenu(
            self.middle_button_frame, values=["Light", "Dark", "System"],
            command=self.change_appearance_mode_event
        )
        self.appearance_mode_optionemenu.grid(row=12, column=0, padx=20, pady=(0, 10), sticky="s")

        self.scaling_label = customtkinter.CTkLabel(self.middle_button_frame, text="UI Scaling")
        self.scaling_label.grid(row=13, column=0, padx=20, pady=(10, 0), sticky="s")

        self.scaling_optionemenu = customtkinter.CTkOptionMenu(
            self.middle_button_frame, values=["80%", "90%", "100%", "110%", "120%"],
            command=self.change_scaling_event
        )
        self.scaling_optionemenu.grid(row=14, column=0, padx=20, pady=(0, 20), sticky="s")

        # ===== 右侧侧边栏 =====
        self.sidebar_frame = customtkinter.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=1, rowspan=3, sticky="nsew", padx=5, pady=10)

        self.sidebar_logo_label = customtkinter.CTkLabel(
            self.sidebar_frame, text="Button operation", font=customtkinter.CTkFont(size=20, weight="bold")
        )
        self.sidebar_logo_label.grid(row=0, column=0, padx=25, pady=(20, 10))

        # 使用封装方法创建按钮和选项菜单
        self.create_sidebar_button("中间按钮1", 1,command=self.optionmenu_callback)
        self.create_sidebar_button("中间按钮2", 2,command=self.optionmenu_callback)
        self.create_sidebar_button("中间按钮3", 3,command=self.optionmenu_callback)
        self.create_optionmenu(["选项1", "选项2", "选项3"], 5)

        # ===== 中间主内容区 =====
        self.json_textbox = customtkinter.CTkTextbox(self, font=("Courier", 12))
        self.json_textbox.grid(row=1, column=2, padx=20, pady=10, sticky="nsew")

        # ===== 搜索框 =====
        self.search_entry = customtkinter.CTkEntry(self, placeholder_text="搜索关键词")
        self.search_entry.grid(row=0, column=2, padx=20, pady=10, sticky="ew")

        # ===== 右侧操作按钮列 =====
        self.search_button_frame = customtkinter.CTkFrame(self)
        self.search_button_frame.grid(row=0, column=3, padx=20, pady=10, sticky="nw")

        self.search_prev_button = customtkinter.CTkButton(self.search_button_frame, text="↑", width=25,
                                                          command=self.search_previous)
        self.search_prev_button.pack(side="left", padx=5)

        self.search_next_button = customtkinter.CTkButton(self.search_button_frame, text="↓", width=25,
                                                          command=self.search_next)
        self.search_next_button.pack(side="left", padx=5)

        self.save_json_button = customtkinter.CTkButton(self, text="保存", width=68)
        self.save_json_button.grid(row=1, column=3, padx=8, pady=10, sticky="n")

        # ===== 日志区 =====
        self.textbox = customtkinter.CTkTextbox(self, font=("Courier", 12))
        self.textbox.grid(row=2, column=2, columnspan=2, padx=20, pady=10, sticky="nsew")
        self.textbox.configure(state="disabled")

        # 默认设置
        self.appearance_mode_optionemenu.set("Light")
        self.scaling_optionemenu.set("100%")
        self.last_search_index = "1.0"

    def create_middle_button(self, text, row, command=None):
        btn = customtkinter.CTkButton(self.middle_logo_label, text=text, command=command)
        btn.grid(row=row, column=0, padx=20, pady=10)
        return btn

    def create_sidebar_button(self, text, row, command=None):
        btn = customtkinter.CTkButton(self.sidebar_frame, text=text, command=command)
        btn.grid(row=row, column=0, padx=20, pady=10)
        return btn

    def create_optionmenu(self, values, row, command=None):
        optionmenu = customtkinter.CTkOptionMenu(self.sidebar_frame, values=values, command=command)
        optionmenu.grid(row=row, column=0, padx=20, pady=10, sticky="ew")
        return optionmenu

    def optionmenu_callback(self):
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

    def clear_highlight(self):
        self.json_textbox.tag_delete("highlight")

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

    def change_appearance_mode_event(self, new_appearance_mode: str):
        customtkinter.set_appearance_mode(new_appearance_mode)

    def change_scaling_event(self, new_scaling: str):
        new_scaling_float = int(new_scaling.replace("%", "")) / 100
        customtkinter.set_widget_scaling(new_scaling_float)

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


if __name__ == "__main__":
    app = CustomApp()
    app.mainloop()
