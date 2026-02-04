# HAC_tab.py
import tkinter as tk
from tkinter import filedialog

from Function.common import create_env_radio
from Function.hac_script import (
    run_single,
    run_impex,
    run_excel_ppp,
    run_excel_aaa,
    read_ppp_excel,
    read_aaa_excel,
    build_ppp_script_from_row,
    build_aaa_script_from_row,
)


class HACTab(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)

        line_pady = 10

        # ----- env (Dev / Staging) -----
        self.env_radio_var = tk.StringVar(value="Dev")
        env_radio_frame = create_env_radio(self, self.env_radio_var)
        env_radio_frame.pack(anchor="w", pady=10, padx=10)

        # ----- Row 0: HAC username/password -----
        cred_row = tk.Frame(self)
        cred_row.pack(anchor="w", padx=10, pady=(0, line_pady))

        tk.Label(cred_row, text="HAC User:").grid(row=0, column=0, sticky="w")
        self.user_entry = tk.Entry(cred_row, width=20)
        self.user_entry.grid(row=0, column=1, padx=(5, 15))

        tk.Label(cred_row, text="Password:").grid(row=0, column=2, sticky="w")
        self.pw_entry = tk.Entry(cred_row, width=20)
        self.pw_entry.grid(row=0, column=3, padx=(5, 0))

        self._set_dev_default_creds()
        self.env_radio_var.trace_add("write", lambda *args: self._on_env_change())

        # ----- mode: impex / single / excel -----
        self.mode_var = tk.StringVar(value="impex")

        mode_row = tk.Frame(self)
        mode_row.pack(anchor="w", padx=10, pady=line_pady)

        self.impex_radio = tk.Radiobutton(
            mode_row,
            text="Single Impex",
            variable=self.mode_var,
            value="impex",
            command=self._on_mode_change,
        )
        self.impex_radio.pack(side="left")

        tk.Label(mode_row, text="   ").pack(side="left")

        self.single_radio = tk.Radiobutton(
            mode_row,
            text="Single script",
            variable=self.mode_var,
            value="single",
            command=self._on_mode_change,
        )
        self.single_radio.pack(side="left")

        # Row 1: textarea（Impex / Single 共用）
        single_row = tk.Frame(self)
        single_row.pack(anchor="w", padx=10, pady=line_pady)

        self.single_text = tk.Text(single_row, width=55, height=3)
        self.single_text.pack(side="left")

        # Row 2: excel radio + file chooser
        excel_row = tk.Frame(self)
        excel_row.pack(anchor="w", padx=10, pady=line_pady)

        self.excel_radio = tk.Radiobutton(
            excel_row,
            text="Upload Excel Batch file",
            variable=self.mode_var,
            value="excel",
            command=self._on_mode_change,
        )
        self.excel_radio.pack(side="left")

        self.excel_path_var = tk.StringVar(value="No file selected")
        self.excel_entry = tk.Entry(
            excel_row,
            textvariable=self.excel_path_var,
            state="readonly",
            width=40,
        )
        self.excel_entry.pack(side="left", padx=(10, 5))

        self.browse_btn = tk.Button(
            excel_row, text="Browse", command=self._browse_excel
        )
        self.browse_btn.pack(side="left")

        # Row 2.5: Excel type (PPP / AAA)
        excel_type_row = tk.Frame(self)
        excel_type_row.pack(anchor="w", padx=10, pady=(0, line_pady))

        tk.Label(excel_type_row, text="Excel type:").pack(side="left")

        self.excel_type_var = tk.StringVar(value="PPP")  # default PPP

        self.ppp_type_radio = tk.Radiobutton(
            excel_type_row,
            text="PPP Excel",
            variable=self.excel_type_var,
            value="PPP",
            state="disabled",
        )
        self.ppp_type_radio.pack(side="left", padx=(5, 10))

        # self.aaa_type_radio = tk.Radiobutton(
        #     excel_type_row,
        #     text="AAA Excel (Fake)",
        #     variable=self.excel_type_var,
        #     value="AAA",
        #     state="disabled",
        # )
        # self.aaa_type_radio.pack(side="left")

        # Row 3: Submit + Preview + Template URL
        btn_row = tk.Frame(self)
        btn_row.pack(anchor="w", padx=10, pady=line_pady)

        self.submit_button = tk.Button(btn_row, text="Submit", command=self.submit)
        self.submit_button.pack(side="left")

        tk.Label(btn_row, text="   ").pack(side="left")

        self.preview_button = tk.Button(
            btn_row, text="Preview", command=self.preview_script, state="disabled"
        )
        self.preview_button.pack(side="left")

        tk.Label(btn_row, text="   ").pack(side="left")

        self.template_button = tk.Button(
            btn_row,
            text="Template URL",
            command=self.download_template,
            state="disabled",
        )
        self.template_button.pack(side="left")

        # Row 4: Result textarea
        result_frame = tk.Frame(self)
        result_frame.pack(anchor="w", padx=10, pady=(0, line_pady))

        tk.Label(result_frame, text="Result:").pack(anchor="w")
        self.result_text = tk.Text(result_frame, width=55, height=7)
        self.result_text.pack(anchor="w")

        self._on_mode_change()

    # ---------- UI helpers ----------

    def _set_dev_default_creds(self):
        self.user_entry.delete(0, tk.END)
        self.user_entry.insert(0, "admin")
        self.pw_entry.delete(0, tk.END)
        self.pw_entry.insert(0, "philipsspilihp")

    def _clear_creds(self):
        self.user_entry.delete(0, tk.END)
        self.pw_entry.delete(0, tk.END)

    def _on_env_change(self):
        if self.env_radio_var.get() == "Dev":
            self._set_dev_default_creds()
        else:
            self._clear_creds()

    def _update_excel_controls_state(self):
        """根據 mode + 是否有檔案，控制 Excel type / preview / template 的啟用狀態。"""
        mode = self.mode_var.get()
        path = self.excel_path_var.get().strip()
        has_file = bool(path) and path != "No file selected"

        if mode != "excel":
            self.ppp_type_radio.config(state="disabled")
            # self.aaa_type_radio.config(state="disabled")
            self.preview_button.config(state="disabled")
            self.template_button.config(state="disabled")
        else:
            self.ppp_type_radio.config(state="normal")
            # self.aaa_type_radio.config(state="normal")
            self.template_button.config(state="normal")
            if has_file:
                self.preview_button.config(state="normal")
            else:
                self.preview_button.config(state="disabled")

    def _on_mode_change(self):
        mode = self.mode_var.get()
        if mode in ("single", "impex"):
            self.single_text.config(state="normal")
            self.browse_btn.config(state="disabled")
        else:
            self.single_text.config(state="disabled")
            self.browse_btn.config(state="normal")

        self._update_excel_controls_state()

    def _browse_excel(self):
        if self.browse_btn["state"] == "disabled":
            return
        filename = filedialog.askopenfilename(
            title="Select Excel file",
            filetypes=[("Excel files", "*.xlsx *.xls")],
        )
        if filename:
            self.excel_path_var.set(filename)
        else:
            self.excel_path_var.set("No file selected")

        self._update_excel_controls_state()

    def _set_output(self, text: str):
        self.result_text.config(state="normal")
        self.result_text.delete("1.0", "end")
        self.result_text.insert("end", text)
        self.result_text.config(state="disabled")

    # ---------- main actions ----------

    def submit(self):
        env = self.env_radio_var.get()
        username = self.user_entry.get().strip()
        password = self.pw_entry.get().strip()

        if not username or not password:
            self._set_output("Please enter HAC username and password.")
            return

        mode = self.mode_var.get()

        if mode in ("single", "impex"):
            state = self.single_text.cget("state")
            if state == "disabled":
                self.single_text.config(state="normal")
                text_value = self.single_text.get("1.0", "end").strip()
                self.single_text.config(state="disabled")
            else:
                text_value = self.single_text.get("1.0", "end").strip()

            if not text_value:
                self._set_output("Textarea is empty, nothing to execute.")
                return

            if mode == "single":
                result = run_single(env, username, password, text_value)
            else:
                result = run_impex(env, username, password, text_value)

            self._set_output(result)
        else:
            excel_path = self.excel_path_var.get()
            if not excel_path or excel_path == "No file selected":
                self._set_output("No Excel file selected")
                return

            excel_type = self.excel_type_var.get()
            if excel_type == "PPP":
                result = run_excel_ppp(env, username, password, excel_path)
            else:
                result = run_excel_aaa(env, username, password, excel_path)

            self._set_output(result)

    def preview_script(self):
        if self.mode_var.get() != "excel":
            self._set_output("Preview only works in 'Upload Excel file' mode.")
            return

        excel_path = self.excel_path_var.get()
        if not excel_path or excel_path == "No file selected":
            self._set_output("No Excel file selected for preview.")
            return

        excel_type = self.excel_type_var.get()

        try:
            if excel_type == "PPP":
                df = read_ppp_excel(excel_path)
            else:
                df = read_aaa_excel(excel_path)
        except Exception as e:
            self._set_output(f"Failed to read Excel: {e}")
            return

        if df.empty:
            self._set_output("Excel has no data.")
            return

        row = df.iloc[0]
        if excel_type == "PPP":
            script_text = build_ppp_script_from_row(row)
        else:
            script_text = build_aaa_script_from_row(row)

        win = tk.Toplevel(self)
        win.title(f"Script Preview ({excel_type} Row 1)")
        text = tk.Text(win, width=100, height=30)
        text.pack(fill="both", expand=True)
        text.insert("1.0", script_text)
        text.config(state="disabled")

    def download_template(self):
        excel_type = self.excel_type_var.get()

        if excel_type == "PPP":
            template_url = (
                "https://docs.google.com/spreadsheets/d/"
                "1XjIGmipmdzqhnL8LARaKGwebxdzFLY0U/edit?usp=sharing&ouid="
                "108055125443022893204&rtpof=true&sd=true"
            )
        else:
            template_url = "fake ga"

        self._set_output(template_url)
