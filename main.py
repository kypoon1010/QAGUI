import tkinter as tk
from tkinter import ttk

from HAC_tab import HACTab
from order_status_tab import OrderStatusTab
from payment_tab import PaymentTab
# from info_tab import InfoTab  # if you use it

def main():
    root = tk.Tk()
    root.title("QA Tools")
    root.geometry("500x500")

    notebook = ttk.Notebook(root)
    notebook.pack(expand=True, fill='both', padx=10, pady=10)

    tab1 = PaymentTab(notebook)
    notebook.add(tab1, text='Payment Gateway')

    tab2 = OrderStatusTab(notebook)
    notebook.add(tab2, text='Order Status')

    tab3 = HACTab(notebook)
    notebook.add(tab3, text='HAC')

    root.mainloop()

if __name__ == "__main__":
    main()
