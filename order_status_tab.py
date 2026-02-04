import tkinter as tk

from Function.change_order_status import api_Function_Order_RECEIVED_BY_CUSTOMER
from Function.common import create_env_radio


class OrderStatusTab(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)

        line_pady = 10
        entry_width = 20

        # env
        self.env_radio_var = tk.StringVar()
        env_radio_frame = create_env_radio(self, self.env_radio_var)
        env_radio_frame.pack(anchor="w", pady=10, padx=10)

        # order number
        order_row = tk.Frame(self)
        order_row.pack(anchor="w", padx=10, pady=line_pady)
        tk.Label(order_row, text="Order number *").pack(side="left")
        self.order_number_entry = tk.Entry(order_row, width=entry_width)
        self.order_number_entry.pack(side="left", padx=(5, 15))

        # customer type / tel / pw / store
        cust_frame = tk.Frame(self)
        cust_frame.pack(anchor="w", padx=10, pady=line_pady)

        self.customer_type_var = tk.StringVar(value="B")

        tk.Radiobutton(
            cust_frame,
            variable=self.customer_type_var,
            value="B",
            command=self._on_customer_type_change,
        ).grid(row=0, column=0, sticky="w")

        tk.Radiobutton(
            cust_frame,
            variable=self.customer_type_var,
            value="A",
            command=self._on_customer_type_change,
        ).grid(row=1, column=0, sticky="w")

        tk.Label(cust_frame, text="Tel").grid(row=0, column=1, sticky="w", padx=(15, 5))
        self.tel_entry = tk.Entry(cust_frame, width=entry_width)
        self.tel_entry.grid(row=0, column=2, sticky="w")

        tk.Label(cust_frame, text="Password").grid(row=0, column=3, sticky="w", padx=(15, 5))
        self.password_entry = tk.Entry(cust_frame, width=entry_width, show="*")
        self.password_entry.grid(row=0, column=4, sticky="w")

        tk.Label(cust_frame, text="Store Code").grid(row=1, column=1, sticky="w", padx=(15, 5))
        self.store_code_entry = tk.Entry(cust_frame, width=entry_width)
        self.store_code_entry.grid(row=1, column=2, sticky="w")

        self._on_customer_type_change()

        # status dropdown
        status_frame = tk.Frame(self)
        status_frame.pack(anchor="w", padx=10, pady=line_pady)

        tk.Label(status_frame, text="Status").pack(side="left")
        status_options = sorted(
            {
                "RECEIVED_BY_CUSTOMER",
                "ORDER_COMPLETE",
                "CONFIRMED",
                "ACKNOWLEDGED",
                "PICKED",
                "CS_CANCEL",
                "CANCELLED",
                "OVERSEAS_PACKED",
                "PACKED",
                "CS_CANCEL_MERCHANT_PAYMENT",
                "IN_HUB",
                "DISPATCHED",
                "IN_ROUTE",
                "IN_ROUTE_FIXED",
                "SKIPPED",
                "PACKAGE_LOST",
            }
        )
        default_status = "Select status..."
        self.status_var = tk.StringVar(value=default_status)
        tk.OptionMenu(status_frame, self.status_var, *([default_status] + status_options)).pack(
            side="left", padx=5
        )

        # Submit + Loading
        action_row = tk.Frame(self)
        action_row.pack(anchor="w", padx=10, pady=line_pady)

        self.submit_button = tk.Button(action_row, text="Submit", command=self.submit)
        self.submit_button.pack(side="left")

        tk.Label(action_row, text="   ").pack(side="left")

        self.loading_label = tk.Label(action_row, text="", fg="blue")
        self.loading_label.pack(side="left")

        # result label + text
        result_frame = tk.Frame(self)
        result_frame.pack(anchor="w", padx=10)

        tk.Label(result_frame, text="Result:").pack(anchor="w")

        self.result_text = tk.Text(
            result_frame,
            font=("Consolas", 11),
            height=9,
            width=60,
            wrap="word",
        )
        self.result_text.pack(side="left", anchor="w")

        scrollbar = tk.Scrollbar(result_frame, command=self.result_text.yview)
        scrollbar.pack(side="left", fill="y")

        self.result_text.config(yscrollcommand=scrollbar.set)

    # helpers

    def _set_loading(self, is_loading):
        self.submit_button.config(state="disabled" if is_loading else "normal")
        self.loading_label.config(text="Loading, please wait..." if is_loading else "")
        self.loading_label.update_idletasks()

    def _on_customer_type_change(self):
        a_type = self.customer_type_var.get() == "A"
        self.store_code_entry.config(state="normal" if a_type else "disabled")
        self.tel_entry.config(state="disabled" if a_type else "normal")
        self.password_entry.config(state="disabled" if a_type else "normal")

    def _println(self, text):
        self.result_text.insert(tk.END, text + "\n")

    # main entry

    def submit(self):
        self._set_loading(True)
        self.result_text.delete("1.0", tk.END)
        success = False
        try:
            env = self.env_radio_var.get()
            order_number = self.order_number_entry.get().strip()
            store_code = self.store_code_entry.get().strip()
            tel = self.tel_entry.get().strip()
            password = self.password_entry.get().strip()
            target_status = self.status_var.get()
            ctype = self.customer_type_var.get()

            if target_status == "Select status...":
                self._println("Failed: Please select a target status.")
                return False
            if not order_number:
                self._println("Failed: Please enter Order number.")
                return False

            try:
                if ctype == "A":
                    if not store_code:
                        self._println("Failed: Please enter Store Code.")
                        return False
                    api_Function_Order_RECEIVED_BY_CUSTOMER(
                        env=env,
                        order=order_number,
                        store_code=store_code,
                        sku=None,
                        uid=None,
                        tel=None,
                        pw=None,
                        status=target_status,
                    )
                else:
                    if not tel or not password:
                        self._println("Failed: Please enter Tel and Password.")
                        return False
                    api_Function_Order_RECEIVED_BY_CUSTOMER(
                        env=env,
                        order=order_number,
                        store_code=None,
                        sku=None,
                        uid=None,      # 讓 core 用 tel+pw → uid
                        tel=tel,
                        pw=password,
                        status=target_status,
                    )

                self._println("Success")
                success = True

            except Exception as e:
                self._println(f"Failed: {e}")
                success = False

            return success

        finally:
            self._set_loading(False)



# import tkinter as tk
# from Function.change_order_status import (
#     get_consignment_code,
#     create_customer_received_batch,
#     split_and_update_consignment_status,
#     get_user_list_by_search_text,
#     get_oauth_token,
#     get_order_with_batches,
# )
# from Function.common import create_env_radio
#
#
# class OrderStatusTab(tk.Frame):
#     def __init__(self, parent):
#         super().__init__(parent)
#
#         line_pady = 10
#         entry_width = 20
#
#         # env
#         self.env_radio_var = tk.StringVar()
#         env_radio_frame = create_env_radio(self, self.env_radio_var)
#         env_radio_frame.pack(anchor="w", pady=10, padx=10)
#
#         # order number
#         order_row = tk.Frame(self)
#         order_row.pack(anchor="w", padx=10, pady=line_pady)
#         tk.Label(order_row, text="Order number *").pack(side="left")
#         self.order_number_entry = tk.Entry(order_row, width=entry_width)
#         self.order_number_entry.pack(side="left", padx=(5, 15))
#
#         # customer type / tel / pw / store
#         cust_frame = tk.Frame(self)
#         cust_frame.pack(anchor="w", padx=10, pady=line_pady)
#
#         self.customer_type_var = tk.StringVar(value="B")
#
#         tk.Radiobutton(
#             cust_frame,
#             text="",
#             variable=self.customer_type_var,
#             value="B",
#             command=self._on_customer_type_change,
#         ).grid(row=0, column=0, sticky="w")
#
#         tk.Radiobutton(
#             cust_frame,
#             text="",
#             variable=self.customer_type_var,
#             value="A",
#             command=self._on_customer_type_change,
#         ).grid(row=1, column=0, sticky="w")
#
#         tk.Label(cust_frame, text="Tel").grid(row=0, column=1, sticky="w", padx=(15, 5))
#         self.tel_entry = tk.Entry(cust_frame, width=entry_width)
#         self.tel_entry.grid(row=0, column=2, sticky="w")
#
#         tk.Label(cust_frame, text="Password").grid(row=0, column=3, sticky="w", padx=(15, 5))
#         self.password_entry = tk.Entry(cust_frame, width=entry_width)
#         self.password_entry.grid(row=0, column=4, sticky="w")
#
#         tk.Label(cust_frame, text="Store Code").grid(row=1, column=1, sticky="w", padx=(15, 5))
#         self.store_code_entry = tk.Entry(cust_frame, width=entry_width)
#         self.store_code_entry.grid(row=1, column=2, sticky="w")
#
#         self._on_customer_type_change()
#
#         # status dropdown
#         status_frame = tk.Frame(self)
#         status_frame.pack(anchor="w", padx=10, pady=line_pady)
#
#         tk.Label(status_frame, text="Status").pack(side="left")
#         status_options = sorted(
#             {
#                 "RECEIVED_BY_CUSTOMER",
#                 "ORDER_COMPLETE",
#                 "CONFIRMED",
#                 "ACKNOWLEDGED",
#                 "PICKED",
#                 "CS_CANCEL",
#                 "CANCELLED",
#                 "OVERSEAS_PACKED",
#                 "PACKED",
#                 "CS_CANCEL_MERCHANT_PAYMENT",
#                 "IN_HUB",
#                 "DISPATCHED",
#                 "IN_ROUTE",
#                 "IN_ROUTE_FIXED",
#                 "SKIPPED",
#                 "PACKAGE_LOST",
#             }
#         )
#         default_status = "Select status..."
#         self.status_var = tk.StringVar(value=default_status)
#         tk.OptionMenu(status_frame, self.status_var, *([default_status] + status_options)).pack(
#             side="left", padx=5
#         )
#
#         # Submit + Loading 在同一行
#         action_row = tk.Frame(self)
#         action_row.pack(anchor="w", padx=10, pady=line_pady)
#
#         self.submit_button = tk.Button(action_row, text="Submit", command=self.submit)
#         self.submit_button.pack(side="left")
#
#         tk.Label(action_row, text="   ").pack(side="left")  # 小空白
#
#         self.loading_label = tk.Label(action_row, text="", fg="blue")
#         self.loading_label.pack(side="left")
#
#         # result label + text
#         result_frame = tk.Frame(self)
#         result_frame.pack(anchor="w", padx=10)
#
#         tk.Label(result_frame, text="Result:").pack(anchor="w")
#
#         self.result_text = tk.Text(
#             result_frame,
#             font=("Consolas", 11),
#             height=9,
#             width=60,
#             wrap="word",
#         )
#         self.result_text.pack(side="left", anchor="w")
#
#         scrollbar = tk.Scrollbar(result_frame, command=self.result_text.yview)
#         scrollbar.pack(side="left", fill="y")
#
#         self.result_text.config(yscrollcommand=scrollbar.set)
#
#     # helpers
#
#     def _set_loading(self, is_loading):
#         self.submit_button.config(state="disabled" if is_loading else "normal")
#         self.loading_label.config(text="Loading, please wait..." if is_loading else "")
#         self.loading_label.update_idletasks()
#
#     def _on_customer_type_change(self):
#         a_type = self.customer_type_var.get() == "A"
#         self.store_code_entry.config(state="normal" if a_type else "disabled")
#         self.tel_entry.config(state="disabled" if a_type else "normal")
#         self.password_entry.config(state="disabled" if a_type else "normal")
#
#     # main entry
#
#     def submit(self):
#         self._set_loading(True)
#         self.result_text.delete("1.0", tk.END)
#         try:
#             env = self.env_radio_var.get()
#             order_number = self.order_number_entry.get().strip()
#             store_code = self.store_code_entry.get().strip()
#             tel = self.tel_entry.get().strip()
#             password = self.password_entry.get().strip()
#             target_status = self.status_var.get()
#             ctype = self.customer_type_var.get()
#
#             if target_status == "Select status...":
#                 self._println("Please select a target status.")
#                 return
#             if not order_number:
#                 self._println("Please enter Order number.")
#                 return
#
#             if ctype == "A":
#                 if not store_code:
#                     self._println("Please enter Store Code for type A.")
#                     return
#                 self._flow_store_code(env, order_number, store_code, target_status)
#             else:
#                 if not tel or not password:
#                     self._println("Please enter Tel and Password for type B.")
#                     return
#                 self._flow_tel_password(env, order_number, tel, password, target_status)
#         finally:
#             self._set_loading(False)
#
#     def _println(self, text):
#         self.result_text.insert(tk.END, text + "\n")
#
#     # flow A
#
#     def _flow_store_code(self, env, order_number, store_code, target_status):
#         consignment_code, status, msg = get_consignment_code(env, order_number, store_code)
#         if msg != "Success":
#             self._println(msg)
#             return
#         if status and status.upper() == "ORDER_COMPLETE":
#             self._println("Consignment already ORDER_COMPLETE. No further actions accepted.")
#             return
#
#         self._println(f"Consignment Code: {consignment_code}")
#         self._println(f"Current Status: {status}")
#         self._println(f"Target Status: {target_status}")
#
#         try:
#             create_customer_received_batch(env, consignment_code, consignment_code)
#             self._println("Customer received batch creation succeeded or already exists.")
#             new_status = split_and_update_consignment_status(env, consignment_code, target_status)
#             self._println(f"Consignment status updated to: {new_status}")
#         except Exception as e:
#             self._println(f"Operation failed: {e}")
#
#     # flow B
#
#     def _flow_tel_password(self, env, order_number, tel, password, target_status):
#         summary_state = "N/A"
#
#         # 1) UID
#         uid, uid_msg = get_user_list_by_search_text(env, tel)
#         uid_ok = bool(uid)
#         self._println(f"[1] Get UID: {'Success' if uid_ok else 'Failed'}")
#         self._println(f"     {uid or uid_msg}")
#         if not uid_ok:
#             summary_state = "Failed"
#             self._prepend_summary(summary_state)
#             return
#
#         # 2) Token
#         token, token_msg = get_oauth_token(env, uid, password)
#         token_ok = bool(token)
#         self._println(f"[2] Get Token: {'Success' if token_ok else 'Failed'}")
#         self._println(f"     {token or token_msg}")
#         if not token_ok:
#             summary_state = "Failed"
#             self._prepend_summary(summary_state)
#             return
#
#         # 3) Order
#         order_data, order_msg = get_order_with_batches(env, uid, order_number, token)
#         order_ok = bool(order_data)
#         self._println(f"[3] Get OrderID: {'Success' if order_ok else 'Failed'}")
#         if not order_ok:
#             self._println(f"     {order_msg}")
#             summary_state = "Failed"
#             self._prepend_summary(summary_state)
#             return
#
#         sub_orders = self._extract_sub_orders(order_data)
#         self._println("     Sub Orders:")
#         if sub_orders:
#             for s in sub_orders:
#                 self._println(f"       {s}")
#         else:
#             self._println("       (none)")
#
#         # 4) Consignments
#         self._println("\n[4] Consignment updates:")
#         if not sub_orders:
#             self._println("  Failed - no sub-orders found")
#             summary_state = "Failed"
#         else:
#             summary_state = "Success" if self._update_consignments_for_suborders(
#                 env, order_number, sub_orders, target_status
#             ) else "Failed"
#
#         self._prepend_summary(summary_state)
#         # self._println(f"[DONE] env={env}, order={order_number}, tel={tel}, target={target_status}")
#
#     def _extract_sub_orders(self, order_data):
#         sub_orders = []
#         for batch in order_data.get("deliveryBatches", []):
#             for entry in batch.get("entries", []):
#                 sub_no = entry.get("subOrderNumber")
#                 if sub_no:
#                     sub_orders.append(sub_no)
#         return sub_orders
#
#     def _update_consignments_for_suborders(self, env, order_number, sub_orders, target_status):
#         all_ok = True
#         for sub_no in sub_orders:
#             try:
#                 _, store_code = sub_no.split("-", 1)
#             except ValueError:
#                 self._println(f"  {sub_no}: Failed")
#                 self._println("    invalid subOrder format")
#                 all_ok = False
#                 continue
#
#             cons_code, cur_status, msg = get_consignment_code(env, order_number, store_code)
#             if msg != "Success":
#                 self._println(f"  {sub_no}: Failed")
#                 self._println(f"    {msg}")
#                 all_ok = False
#                 continue
#
#             if cur_status and cur_status.upper() == "ORDER_COMPLETE":
#                 self._println(f"  {sub_no}: Failed")
#                 self._println(f"    {cur_status} (ORDER_COMPLETE, skipped)")
#                 all_ok = False
#                 continue
#
#             batch_ok = status_ok = False
#             error_msg = None
#             new_status = cur_status
#
#             try:
#                 create_customer_received_batch(env, cons_code, cons_code)
#                 batch_ok = True
#                 new_status = split_and_update_consignment_status(env, cons_code, target_status)
#                 status_ok = True
#             except Exception as e:
#                 error_msg = str(e)
#                 all_ok = False
#
#             this_ok = (
#                     batch_ok
#                     and status_ok
#                     and isinstance(new_status, str)
#                     and new_status.upper() == target_status.upper()
#             )
#             if not this_ok:
#                 all_ok = False
#
#             self._println(f"  {sub_no}: {'Success' if this_ok else 'Failed'}")
#             detail = (
#                 f"    {cur_status} -> {new_status} "
#                 f"(batch={'OK' if batch_ok else 'FAIL'}, status={'OK' if status_ok else 'FAIL'})"
#             )
#             if error_msg:
#                 detail += f" [{error_msg}]"
#             self._println(detail)
#
#         return all_ok
#
#     def _prepend_summary(self, state):
#         self.result_text.insert("1.0", f"[Summary] Consignment updates: {state}\n\n")
