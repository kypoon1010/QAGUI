import tkinter as tk
from Function.common import *
from Function.payment_gateway import *

class PaymentTab(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)

        self.radio_var = tk.StringVar()
        radio_frame = create_env_radio(self, self.radio_var)
        radio_frame.pack(anchor='w', pady=10, padx=10)

        # Gateway 按鈕
        button_frame = tk.Frame(self)
        button_frame.pack(anchor='w', padx=10)

        self.buttons = []
        button_info = [
            ("MPGS Only", self.action_mpgs),
            ("Cybersource Only", self.action_cybersource),
            ("Paydollar Only", self.action_paydollar),
            ("All Open", self.action_all_open),
        ]
        for name, func in button_info:
            btn = tk.Button(button_frame, text=name, command=func, width=30)
            btn.pack(pady=0.5, anchor='w')
            self.buttons.append(btn)

        # Manual Select checkbox
        self.chk_manual_var = tk.BooleanVar()
        chk_manual = tk.Checkbutton(self, text="Manual Select", variable=self.chk_manual_var,
                                    command=self.toggle_checkboxes)
        chk_manual.pack(anchor='w', padx=12, pady=(12, 0))

        # Gateway 選擇 checkbox區
        check_submit_frame = tk.Frame(self)
        check_submit_frame.pack(anchor='w', padx=19, pady=6)

        self.chk_var1 = tk.BooleanVar()
        self.chk_var2 = tk.BooleanVar()
        self.chk_var3 = tk.BooleanVar()

        self.chk1 = tk.Checkbutton(check_submit_frame, text="MPGS", variable=self.chk_var1, state='disabled')
        self.chk1.pack(side=tk.LEFT)
        self.chk2 = tk.Checkbutton(check_submit_frame, text="Cybersource", variable=self.chk_var2, state='disabled')
        self.chk2.pack(side=tk.LEFT, padx=(8, 0))
        self.chk3 = tk.Checkbutton(check_submit_frame, text="Paydollar", variable=self.chk_var3, state='disabled')
        self.chk3.pack(side=tk.LEFT, padx=(8, 0))

        self.submit_btn = tk.Button(check_submit_frame, text="Submit", command=self.on_submit, state='disabled',
                                    width=7)
        self.submit_btn.pack(side=tk.LEFT, padx=(8, 0))

        self.label = tk.Label(self, text="", justify='left', anchor='w', font=("Consolas", 11))
        self.label.pack(anchor='w', padx=12, pady=(4, 0))

    def format_gateway_status(self, results):
        lines = []
        # 最大gateway名字長度，例如Cybersource是11
        width = max(len(gw.capitalize()) for gw in ALL_GATEWAYS) + 2
        for gw in ALL_GATEWAYS:
            gw_name = gw.capitalize()
            status_line = next((r for r in results if r and gw in r.lower()), None)
            if status_line and ("open" in status_line.lower()):
                status = "Open"
            elif status_line and ("close" in status_line.lower()):
                status = "Close"
            else:
                status = "Unknown"
            lines.append(f"{gw_name:<{width}}: {status:<10}")
        return "\n".join(lines)

    def update_label_with_result(self, prefix, results):
        has_error = any(r and ("error" in r.lower()) for r in results)
        status = "Fail" if has_error else "Success"
        context_radio = self.radio_var.get()
        gateway_status_text = self.format_gateway_status(results)

        text = (
            f"{context_radio} + {prefix} : {status}\n"
            f"{gateway_status_text}"
        )
        self.label.config(text=text, fg="red" if has_error else "green")

    def get_context(self):
        return {'selected_domain': self.radio_var.get()}

    def action_mpgs(self):
        context = self.get_context()
        results = [
            toggle_gateway(context, MPGSGateway, True),
            toggle_gateway(context, CybersourceGateway, False),
            toggle_gateway(context, PaydollarGateway, False),
        ]
        self.update_label_with_result("MPGS Only", results)

    def action_cybersource(self):
        context = self.get_context()
        results = [
            toggle_gateway(context, MPGSGateway, False),
            toggle_gateway(context, CybersourceGateway, True),
            toggle_gateway(context, PaydollarGateway, False),
        ]
        self.update_label_with_result("Cybersource Only", results)

    def action_paydollar(self):
        context = self.get_context()
        results = [
            toggle_gateway(context, MPGSGateway, False),
            toggle_gateway(context, CybersourceGateway, False),
            toggle_gateway(context, PaydollarGateway, True),
        ]
        self.update_label_with_result("Paydollar Only", results)

    def action_all_open(self):
        context = self.get_context()
        results = [
            toggle_gateway(context, MPGSGateway, True),
            toggle_gateway(context, CybersourceGateway, True),
            toggle_gateway(context, PaydollarGateway, True),
        ]
        self.update_label_with_result("All Open", results)

    def toggle_checkboxes(self):
        if self.chk_manual_var.get():
            self.chk1.config(state='normal')
            self.chk2.config(state='normal')
            self.chk3.config(state='normal')
            self.submit_btn.config(state='normal')
            for btn in self.buttons:
                btn.config(state='disabled')
        else:
            self.chk1.config(state='disabled')
            self.chk2.config(state='disabled')
            self.chk3.config(state='disabled')
            self.submit_btn.config(state='disabled')
            for btn in self.buttons:
                btn.config(state='normal')

    def on_submit(self):
        context = self.get_context()
        checked_set = set()
        if self.chk_var1.get():
            checked_set.add(MPGSGateway)
        if self.chk_var2.get():
            checked_set.add(CybersourceGateway)
        if self.chk_var3.get():
            checked_set.add(PaydollarGateway)

        results = []
        has_error = False

        if not checked_set:
            # 若無勾選，全部關閉
            for gw in ALL_GATEWAYS:
                res = toggle_gateway(context, gw, False)
                results.append(res)
                if res and ("error" in res.lower()):
                    has_error = True
            selected_names = "close all"
        else:
            for gw in ALL_GATEWAYS:
                active = gw in checked_set
                res = toggle_gateway(context, gw, active)
                results.append(res)
                if res and ("error" in res.lower()):
                    has_error = True
            selected_names = ", ".join([gw.capitalize() for gw in checked_set])

        status = "Fail" if has_error else "Success"
        context_radio = self.radio_var.get()
        gateway_status_text = self.format_gateway_status(results)

        text = (
            f"{context_radio} + {selected_names} only : {status}\n"
            f"{gateway_status_text}"
        )
        self.label.config(text=text, fg="red" if has_error else "green")
