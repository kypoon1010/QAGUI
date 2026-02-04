from Function.common import *
import tkinter as tk

class InfoTab(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)

        self.radio_var = tk.StringVar()
        radio_frame = create_env_radio(self, self.radio_var)
        radio_frame.pack(anchor='w', pady=10, padx=10)

        self.display_button = tk.Button(self, text="Show Selection", command=self.show_selection)
        self.display_button.pack(anchor='w', padx=10, pady=5)

        self.result_label = tk.Label(self, text="", font=("Consolas", 11), anchor='w', justify='left')
        self.result_label.pack(anchor='w', padx=10, pady=5)

    def show_selection(self):
        selected_value = self.radio_var.get()
        self.result_label.config(text=f"Selected environment: {selected_value}")
