import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry
from datetime import date, timedelta
import psycopg2
from psycopg2.extras import RealDictCursor
import csv
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet


def get_conn():
    return psycopg2.connect(host="localhost", dbname="dairy_management", user="postgres", password="system")

def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS customers (
        code SERIAL PRIMARY KEY, name TEXT NOT NULL, doj DATE, phone TEXT, address TEXT, animal_type TEXT);""")
    cur.execute("""CREATE TABLE IF NOT EXISTS milk_collection (
        id SERIAL PRIMARY KEY, customer_code INT REFERENCES customers(code), collection_date DATE NOT NULL,
        session TEXT NOT NULL, animal_type TEXT, quantity_liters FLOAT, fat FLOAT, rate FLOAT, amount FLOAT,
        CONSTRAINT unique_collection UNIQUE (customer_code, collection_date, session));""")
    conn.commit()
    cur.close()
    conn.close()
fat_rate_map = {}
try:
    with open('fat_rate.csv', newline='') as file:
        reader = csv.DictReader(file)
        for row in reader:
            fat_rate_map[float(row['Fat'])] = float(row['Rate'])
except FileNotFoundError:
    messagebox.showwarning("CSV Missing", "fat_rate.csv not found. Enter rates manually.")

def insert_customer(name, doj, phone, address, animal_type):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("INSERT INTO customers (name, doj, phone, address, animal_type) VALUES (%s,%s,%s,%s,%s)",
                (name, doj, phone, address, animal_type))
    conn.commit()
    conn.close()

def fetch_customers():
    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT code, name FROM customers ORDER BY code;")
    rows = cur.fetchall()
    conn.close()
    return rows

def fetch_customers_full():
    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT code, name, doj, phone, address, animal_type FROM customers ORDER BY code;")
    rows = cur.fetchall()
    conn.close()
    return rows

def insert_collection(cust_code, collection_date, session, animal_type, qty, fat, rate):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM milk_collection WHERE customer_code=%s AND collection_date=%s AND session=%s",
                (cust_code, collection_date, session))
    if cur.fetchone():
        conn.close()
        raise Exception(f"{session} entry already exists for this customer on {collection_date}")
    cur.execute("""INSERT INTO milk_collection (customer_code, collection_date, session, animal_type,
        quantity_liters, fat, rate, amount) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                (cust_code, collection_date, session, animal_type, qty, fat, rate, qty * rate))
    conn.commit()
    conn.close()

def fetch_bill(cust_code, start_date, end_date):
    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""SELECT collection_date, session, animal_type, quantity_liters, fat, rate, amount
        FROM milk_collection WHERE customer_code=%s AND collection_date BETWEEN %s AND %s
        ORDER BY collection_date;""", (cust_code, start_date, end_date))
    rows = cur.fetchall()
    total = sum(r["amount"] for r in rows)
    conn.close()
    return rows, total

init_db()
root = tk.Tk()
root.title("🥛 Modern Dairy Management")
root.geometry("700x600")
root.configure(bg='#1a1a2e')
COLORS = { 'primary': '#6c5ce7', 'accent': '#fd79a8', 'success': '#00b894', 'danger': '#e17055',
            'bg_primary': '#1a1a2e', 'bg_card': '#0f3460', 'text_primary': '#ffffff'}

style = ttk.Style()
style.theme_use('clam')
style.configure('Modern.TButton', font=('Segoe UI', 11, 'bold'), background=COLORS['primary'],foreground='white', relief='flat', padding=(20, 12))
style.configure('Success.TButton', background=COLORS['success'], foreground='white', padding=(15, 8))
style.configure('Danger.TButton', background=COLORS['danger'], foreground='white', padding=(15, 8))
style.configure('Card.TFrame', background=COLORS['bg_card'], relief='flat', borderwidth=2)
style.configure('Dark.TFrame', background=COLORS['bg_primary'], relief='flat')
style.configure('Title.TLabel', background=COLORS['bg_primary'], foreground=COLORS['text_primary'],font=('Segoe UI', 18, 'bold'))
style.configure('Card.TLabel', background=COLORS['bg_card'], foreground=COLORS['text_primary'])
style.configure('Modern.TEntry', fieldbackground='white', borderwidth=2, font=('Segoe UI', 10))
style.configure('Modern.TCombobox', fieldbackground='white', font=('Segoe UI', 10))
style.configure("Modern.Treeview.Heading", font=('Segoe UI', 10, 'bold'), background=COLORS['primary'],foreground='white', relief='flat')
style.configure("Modern.Treeview", background='white', fieldbackground='white')

def open_customer_form():
    win = tk.Toplevel(root)
    win.title("👤 Customer Registration")
    win.geometry("500x550")
    win.configure(bg=COLORS['bg_primary'])
    container = ttk.Frame(win, style='Dark.TFrame', padding=30)
    container.pack(fill='both', expand=True)
    ttk.Label(container, text="👤 New Customer Registration", style='Title.TLabel').pack(pady=(0, 30))
    form_card = ttk.Frame(container, style='Card.TFrame', padding=25)
    form_card.pack(fill='x')
    fields = [("📝 Full Name *", "entry"), ("📅 Date of Joining", "date"), ("📞 Phone", "entry"), ("📍 Address", "entry")]
    entries = {}

    for i, (label, field_type) in enumerate(fields):
        ttk.Label(form_card, text=label, style='Card.TLabel').grid(row=i, column=0, sticky='w', pady=8, padx=(0, 15))
        if field_type == "date":
            entry = DateEntry(form_card, width=20, background=COLORS['primary'], foreground='white')
        else:
            entry = ttk.Entry(form_card, style='Modern.TEntry', width=25)
        entry.grid(row=i, column=1, sticky='ew', pady=8)
        entries[label.split()[1].lower().replace('*', '')] = entry
    ttk.Label(form_card, text="🐄 Animal Type", style='Card.TLabel').grid(row=4, column=0, sticky='w', pady=8)
    animal_frame = ttk.Frame(form_card, style='Card.TFrame')
    animal_frame.grid(row=4, column=1, sticky='ew', pady=8)
    animal_var = tk.StringVar(value="Cow")
    for text, value in [("🐄 Cow", "Cow"), ("🐃 Buffalo", "Buffalo"), ("🐄🐃 Both", "Buffalo&Cow")]:
        ttk.Radiobutton(animal_frame, text=text, variable=animal_var, value=value).pack(anchor='w')
    form_card.grid_columnconfigure(1, weight=1)

    def save_customer():
        try:
            name = entries['full'].get().strip()
            if not name:
                messagebox.showwarning("⚠️ Input Error", "Customer name is required!")
                return
            insert_customer(name, entries['date'].get_date(), entries['phone'].get().strip(),
                            entries['address'].get().strip(), animal_var.get())
            messagebox.showinfo("✅ Success", "Customer saved successfully!")
            win.destroy()
        except Exception as ex:
            messagebox.showerror("❌ Error", str(ex))

    button_frame = ttk.Frame(container, style='Dark.TFrame')
    button_frame.pack(fill='x', pady=20)
    ttk.Button(button_frame, text="💾 Save Customer", command=save_customer, style='Success.TButton').pack(side='right',padx=5)
    ttk.Button(button_frame, text="❌ Cancel", command=win.destroy, style='Danger.TButton').pack(side='right', padx=5)

def open_customer_list():
    win = tk.Toplevel(root)
    win.title("👥 Customer Directory")
    win.geometry("900x600")
    win.configure(bg=COLORS['bg_primary'])
    container = ttk.Frame(win, style='Dark.TFrame', padding=20)
    container.pack(fill='both', expand=True)
    ttk.Label(container, text="👥 Customer Directory", style='Title.TLabel').pack(pady=(0, 20))
    table_frame = ttk.Frame(container, style='Card.TFrame', padding=15)
    table_frame.pack(fill='both', expand=True)
    columns = ("Code", "Name", "DOJ", "Phone", "Address", "Animal")
    tree = ttk.Treeview(table_frame, columns=columns, show="headings", style='Modern.Treeview')
    for col in columns:
        tree.heading(col, text=col)
        tree.column(col, width=120)
    scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)
    tree.pack(fill='both', expand=True, side='left')
    scrollbar.pack(side='right', fill='y')

    def load_data():
        for item in tree.get_children():
            tree.delete(item)
        customers = fetch_customers_full()
        for c in customers:
            tree.insert("", "end", values=(c["code"], c["name"], c["doj"], c["phone"], c["address"], c["animal_type"]))
    ttk.Button(container, text="🔄 Refresh", command=load_data, style='Modern.TButton').pack(pady=10)
    load_data()

def open_collection_form():
    win = tk.Toplevel(root)
    win.title("🥛 Milk Collection")
    win.geometry("1000x650")
    win.configure(bg=COLORS['bg_primary'])
    container = ttk.Frame(win, style='Dark.TFrame', padding=20)
    container.pack(fill='both', expand=True)
    ttk.Label(container, text="🥛 Milk Collection Manager", style='Title.TLabel').pack(pady=(0, 20))
    content_frame = ttk.Frame(container, style='Dark.TFrame')
    content_frame.pack(fill='both', expand=True)
    form_panel = ttk.Frame(content_frame, style='Card.TFrame', padding=20)
    form_panel.pack(side='left', fill='y', padx=(0, 15))
    customers = fetch_customers()
    customer_options = [f"{c['code']} - {c['name']}" for c in customers]
    form_fields = [ ("👤 Customer", "combobox", customer_options),
                    ("📅 Date", "date", None),
                    ("🌅 Session", "combobox", ["Morning", "Evening"]),
                    ("🥛 Quantity (L)", "entry", None),
                    ("🧈 Fat %", "entry", None),
                    ("💰 Rate", "entry", None)]
    entries = {}
    for i, (label, field_type, values) in enumerate(form_fields):
        ttk.Label(form_panel, text=label, style='Card.TLabel').grid(row=i, column=0, sticky='w', pady=8)
        if field_type == "combobox":
            entry = ttk.Combobox(form_panel, values=values, style='Modern.TCombobox', width=20)
        elif field_type == "date":
            entry = DateEntry(form_panel, width=20, background=COLORS['primary'], foreground='white')
        else:
            entry = ttk.Entry(form_panel, style='Modern.TEntry', width=22)
        entry.grid(row=i, column=1, pady=8, padx=10)
        entries[label.split()[1].lower().replace('(l)', '').replace('%', '')] = entry
    ttk.Label(form_panel, text="🐄 Animal", style='Card.TLabel').grid(row=6, column=0, sticky='w', pady=8)
    animal_var = tk.StringVar(value="Cow")
    animal_frame = ttk.Frame(form_panel, style='Card.TFrame')
    animal_frame.grid(row=6, column=1, pady=8, padx=10)
    for text, value in [("🐄 Cow", "Cow"), ("🐃 Buffalo", "Buffalo")]:
        ttk.Radiobutton(animal_frame, text=text, variable=animal_var, value=value).pack(anchor='w')

    def update_rate(*args):
        try:
            fat_val = round(float(entries['fat'].get()), 1)
            if fat_val in fat_rate_map:
                entries['rate'].delete(0, tk.END)
                entries['rate'].insert(0, str(fat_rate_map[fat_val]))
        except ValueError:
            pass
    entries['fat'].bind("<KeyRelease>", update_rate)
    table_panel = ttk.Frame(content_frame, style='Card.TFrame', padding=15)
    table_panel.pack(side='right', fill='both', expand=True)
    columns = ("ID", "Customer", "Date", "Session", "Qty", "Fat", "Rate", "Amount")
    tree = ttk.Treeview(table_panel, columns=columns, show="headings", style='Modern.Treeview')
    for col in columns:
        tree.heading(col, text=col)
        tree.column(col, width=70)
    scrollbar = ttk.Scrollbar(table_panel, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)
    tree.pack(fill='both', expand=True, side='left')
    scrollbar.pack(side='right', fill='y')

    def on_tree_select(event):
        selected_item = tree.focus()
        if not selected_item:
            return
        item_values = tree.item(selected_item)['values']
        for key in entries:
            entries[key].delete(0, tk.END)
        try:
            customer_code = item_values[1]
            customer_name = get_customer_name(customer_code)
            entries['customer'].set(f"{customer_code} - {customer_name}")
            date_value = item_values[2]
            print(f"Retrieved date: {date_value}")  # Debugging output
            if isinstance(date_value, str):
                year, month, day = map(int, date_value.split('-'))
                if 1 <= month <= 12 and 1 <= day <= 31:  # Basic validation
                    entries['date'].set_date(date(year, month, day))
                else:
                    print(f"Invalid date: {date_value}")  # Debugging output
            else:
                print(f"Unexpected date format: {date_value}")  # Debugging output
            entries['session'].set(item_values[3])
            animal_var.set(item_values[4])
            entries['quantity'].insert(0, item_values[5])
            entries['fat'].insert(0, item_values[6])
            entries['rate'].insert(0, item_values[7])
        except Exception as e:
            print(f"Error populating form: {e}")

    def get_customer_name(code):
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT name FROM customers WHERE code = %s", (code,))
        name = cur.fetchone()
        conn.close()
        return name[0] if name else "Unknown"
    tree.bind('<<TreeviewSelect>>', on_tree_select)

    def load_data():
        for item in tree.get_children():
            tree.delete(item)
        conn = get_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM milk_collection ORDER BY id DESC LIMIT 50;")
        rows = cur.fetchall()
        conn.close()
        for r in rows:
            tree.insert("", "end", values=(r["id"], r["customer_code"], r["collection_date"],r["session"], r["animal_type"],
                                           r["quantity_liters"], r["fat"], r["rate"],f"₹{r['amount']:.2f}"))

    def save_collection():
        try:
            customer_text = entries['customer'].get()
            if not customer_text:
                messagebox.showwarning("⚠️ Error", "Select a customer!")
                return
            cust_code = int(customer_text.split(' - ')[0])
            insert_collection(cust_code, entries['date'].get_date(), entries['session'].get(),
                              animal_var.get(), float(entries['quantity'].get()),
                              float(entries['fat'].get()), float(entries['rate'].get()))
            messagebox.showinfo("✅ Success", "Collection saved!")
            load_data()
        except Exception as ex:
            messagebox.showerror("❌ Error", str(ex))

    def update_collection():
        try:
            selected_item = tree.selection()
            if not selected_item:
                messagebox.showwarning("⚠️ Error", "Select a record to update!")
                return
            item_values = tree.item(selected_item)['values']
            collection_id = item_values[0]
            customer_text = entries['customer'].get()
            if not customer_text:
                messagebox.showwarning("⚠️ Error", "Select a customer!")
                return
            try:
                cust_code = int(customer_text.split(' - ')[0])
            except ValueError:
                messagebox.showerror("❌ Error", "Invalid customer code selected!")
                return
            update_query = """UPDATE milk_collection SET customer_code=%s, collection_date=%s, session=%s,
                              animal_type=%s, quantity_liters=%s, fat=%s, rate=%s, amount=%s WHERE id=%s"""
            quantity = float(entries['quantity'].get())
            fat = float(entries['fat'].get())
            rate = float(entries['rate'].get())
            amount = quantity * rate
            conn = get_conn()
            cur = conn.cursor()
            cur.execute(update_query, (cust_code, entries['date'].get_date(), entries['session'].get(),
                                       animal_var.get(), quantity, fat, rate, amount, collection_id))
            conn.commit()
            conn.close()
            messagebox.showinfo("✅ Success", "Collection updated!")
            load_data()  # Refresh the data after updating
        except Exception as ex:
            messagebox.showerror("❌ Error", str(ex))

    def delete_collection():
        try:
            selected_item = tree.selection()
            if not selected_item:
                messagebox.showwarning("⚠️ Error", "Select a record to delete!")
                return
            collection_id = tree.item(selected_item)['values'][0]
            conn = get_conn()
            cur = conn.cursor()
            cur.execute("DELETE FROM milk_collection WHERE id=%s", (collection_id,))
            conn.commit()
            conn.close()
            messagebox.showinfo("✅ Success", "Collection deleted!")
            load_data()
        except Exception as ex:
            messagebox.showerror("❌ Error", str(ex))

    button_frame = ttk.Frame(container, style='Dark.TFrame')
    button_frame.pack(fill='x', pady=20)
    ttk.Button(button_frame, text="💾 Save", command=save_collection, style='Success.TButton').pack(side='left', padx=5)
    ttk.Button(button_frame, text="🔄 Refresh", command=load_data, style='Modern.TButton').pack(side='left', padx=5)
    ttk.Button(button_frame, text="✏️ Update", command=update_collection, style='Modern.TButton').pack(side='left', padx=5)
    ttk.Button(button_frame, text="🗑️ Delete", command=delete_collection, style='Danger.TButton').pack(side='left', padx=5)

    load_data()

def open_bill_form():
    win = tk.Toplevel(root)
    win.title("🧾 Bill Generation")
    win.geometry("800x600")
    win.configure(bg=COLORS['bg_primary'])

    container = ttk.Frame(win, style='Dark.TFrame', padding=20)
    container.pack(fill='both', expand=True)

    ttk.Label(container, text="🧾 Bill Generation", style='Title.TLabel').pack(pady=(0, 20))

    control_frame = ttk.Frame(container, style='Card.TFrame', padding=15)
    control_frame.pack(fill='x', pady=(0, 15))

    customers = fetch_customers()
    customer_options = [f"{c['code']} - {c['name']}" for c in customers]

    ttk.Label(control_frame, text="👤 Customer:", style='Card.TLabel').grid(row=0, column=0, padx=10, pady=10)
    cb_code = ttk.Combobox(control_frame, values=customer_options, style='Modern.TCombobox', width=25)
    cb_code.grid(row=0, column=1, padx=10)

    ttk.Label(control_frame, text="📅 From:", style='Card.TLabel').grid(row=0, column=2, padx=10)
    start_date = DateEntry(control_frame, width=12, background=COLORS['primary'], foreground='white')
    start_date.set_date(date.today() - timedelta(days=30))
    start_date.grid(row=0, column=3, padx=10)

    ttk.Label(control_frame, text="📅 To:", style='Card.TLabel').grid(row=0, column=4, padx=10)
    end_date = DateEntry(control_frame, width=12, background=COLORS['primary'], foreground='white')
    end_date.set_date(date.today())
    end_date.grid(row=0, column=5, padx=10)

    table_frame = ttk.Frame(container, style='Card.TFrame', padding=15)
    table_frame.pack(fill='both', expand=True)

    columns = ("Date", "Session", "Animal", "Qty", "Fat", "Rate", "Amount")
    tree = ttk.Treeview(table_frame, columns=columns, show="headings", style='Modern.Treeview')
    for col in columns:
        tree.heading(col, text=col)
        tree.column(col, width=100)

    scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)
    tree.pack(fill='both', expand=True, side='left')
    scrollbar.pack(side='right', fill='y')

    total_label = ttk.Label(container, text="Total: ₹0.00", style='Title.TLabel')
    total_label.pack(pady=10)

    def generate_bill():
        try:
            if not cb_code.get():
                messagebox.showwarning("⚠️ Error", "Select a customer!")
                return
            cust_code = int(cb_code.get().split(' - ')[0])
            rows, total = fetch_bill(cust_code, start_date.get_date(), end_date.get_date())

            for item in tree.get_children():
                tree.delete(item)
            for r in rows:
                tree.insert("", "end", values=(r["collection_date"], r["session"], r["animal_type"],
                                               r["quantity_liters"], f"{r['fat']}%", f"₹{r['rate']:.2f}", f"₹{r['amount']:.2f}"))
            total_label.config(text=f"Total: ₹{total:.2f}")
            if not rows:
                messagebox.showinfo("ℹ️ No Data", "No records found for the selected period!")
        except Exception as ex:
            messagebox.showerror("❌ Error", str(ex))

    # ---- Print to PDF ----
    def print_bill():
        try:
            if not cb_code.get():
                messagebox.showwarning("⚠️ Error", "Select a customer first!")
                return
            if not tree.get_children():
                messagebox.showwarning("⚠️ Error", "Generate bill first!")
                return
            cust_code = int(cb_code.get().split(' - ')[0])
            customer_name = cb_code.get().split(' - ')[1]
            rows, total = fetch_bill(cust_code, start_date.get_date(), end_date.get_date())

            filename = f"Bill_{customer_name.replace(' ', '_')}_{start_date.get_date()}_{end_date.get_date()}.pdf"

            doc = SimpleDocTemplate(filename, pagesize=A4)
            story = []
            styles = getSampleStyleSheet()

            # Header
            story.append(Paragraph("<b> Patil Milk Products Pvt. Ltd.</b>", styles['Title']))
            story.append(Paragraph("Milk Bill", styles['Heading2']))
            story.append(Spacer(1, 12))

            # Customer Info
            story.append(Paragraph(f"<b>Customer:</b> {customer_name}", styles['Normal']))
            story.append(Paragraph(f"<b>Bill From:</b> {start_date.get_date()}  <b>To:</b> {end_date.get_date()}",
                                   styles['Normal']))
            story.append(Spacer(1, 12))

            # Table
            data = [["Date", "Session", "Animal", "Qty (L)", "Fat %", "Rate (₹)", "Amount (₹)"]]
            for r in rows:
                data.append([
                    str(r["collection_date"]), r["session"], r["animal_type"],
                    f"{r['quantity_liters']:.2f}", f"{r['fat']:.1f}",
                    f"{r['rate']:.2f}", f"{r['amount']:.2f}"
                ])
            data.append(["", "", "", "", "", "Total", f"{total:.2f}"])

            table = Table(data, colWidths=[70, 60, 70, 60, 60, 60, 80])
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightblue),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("BACKGROUND", (0, 1), (-1, -1), colors.whitesmoke),
            ]))
            story.append(table)

            story.append(Spacer(1, 20))
            story.append(Paragraph(f"<b>Net Payable Amount:</b> ₹{total:.2f}", styles['Heading2']))

            doc.build(story)

            messagebox.showinfo("✅ Bill Printed", f"Bill saved as PDF: {filename}")
        except Exception as ex:
            messagebox.showerror("❌ Error", str(ex))

    # ---- Buttons ----
    button_frame = ttk.Frame(control_frame, style='Card.TFrame')
    button_frame.grid(row=1, column=0, columnspan=6, pady=15)
    ttk.Button(button_frame, text="📊 Generate Bill", command=generate_bill,
               style='Success.TButton').pack(side='left', padx=10)
    ttk.Button(button_frame, text="🖨️ Print to PDF", command=print_bill,
               style='Modern.TButton').pack(side='left', padx=10)
main_frame = ttk.Frame(root, style='Dark.TFrame', padding=40)
main_frame.pack(fill='both', expand=True)
ttk.Label(main_frame, text="🥛 Modern Dairy Management", style='Title.TLabel').pack(pady=(0, 30))
menu_buttons = [    ("👤 Customer Registration", open_customer_form, 'Success.TButton'),
                    ("👥 Customer Directory", open_customer_list, 'Modern.TButton'),
                    ("🥛 Milk Collection", open_collection_form, 'Modern.TButton'),
                    ("🧾 Bill Generation", open_bill_form, 'Modern.TButton'),
                    ("🚪 Exit", root.destroy, 'Danger.TButton') ]
for text, command, style in menu_buttons:
    ttk.Button(main_frame, text=text, command=command, style=style).pack(fill='x', pady=8, padx=20)
root.mainloop()