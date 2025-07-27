import customtkinter as ctk

class customtkinterUtil(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("界面主题选择示例")
        self.geometry("800x600")

        # 左边栏（导航区）
        self.left_sidebar = ctk.CTkFrame(self, width=250)
        self.left_sidebar.pack(side="left", fill="y")
        self.left_sidebar.pack_propagate(False)

        # 右主内容区
        self.main_content = ctk.CTkFrame(self)
        self.main_content.pack(side="left", expand=True, fill="both")


        # 添加主题选择器到左边栏左下角
        self.theme_selector = ThemeSelector(master=self.left_sidebar)
        self.theme_selector.place(relx=0.01, rely=0.99, anchor="sw")  # 左下角对齐

class ThemeSelector(ctk.CTkFrame):
    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)

        # Appearance Mode
        self.mode_label = ctk.CTkLabel(self, text="界面模式:")
        self.mode_label.grid(row=0, column=0, padx=10, pady=10, sticky="w")

        self.mode_option = ctk.CTkOptionMenu(
            self,
            values=["light", "dark", "system"],
            command=self.change_mode
        )
        self.mode_option.set("light")
        self.mode_option.grid(row=0, column=1, padx=10, pady=10)


    def change_mode(self, choice):
        ctk.set_appearance_mode(choice)

