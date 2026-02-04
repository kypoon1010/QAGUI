import tkinter as tk

def create_env_radio(parent, var, default="Dev"):
    """
    建立 Dev / Staging radio button，回傳包裝好的 frame

    :param parent: 父容器
    :param var: tk.StringVar，綁定環境值
    :param default: 預設值
    """
    var.set(default)
    frame = tk.Frame(parent)
    tk.Radiobutton(frame, text="Dev", variable=var, value="Dev").pack(side=tk.LEFT)
    tk.Radiobutton(frame, text="Staging", variable=var, value="Staging").pack(side=tk.LEFT, padx=16)
    return frame


