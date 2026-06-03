import sqlite3
import json
import os

DB_NAME = "enterprise.db"

def generate_er_diagram():
    """Генерирует ER-диаграмму (PDF или TXT)"""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas

        pdf_path = "ER_Diagram.pdf"
        c = canvas.Canvas(pdf_path, pagesize=A4)
        w, h = A4

        c.setFont("Helvetica-Bold", 16)
        c.drawString(50, h - 50, "ER-диаграмма информационной системы (производство)")

        y = h - 100
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, y, "products (Продукция)")
        y -= 20
        c.setFont("Helvetica", 10)
        c.drawString(70, y, "PK id_product INTEGER")
        y -= 15
        c.drawString(70, y, "name TEXT NOT NULL")
        y -= 25

        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, y, "materials (Материалы)")
        y -= 20
        c.setFont("Helvetica", 10)
        c.drawString(70, y, "PK id_material INTEGER")
        y -= 15
        c.drawString(70, y, "name TEXT NOT NULL")
        y -= 15
        c.drawString(70, y, "price REAL NOT NULL")
        y -= 25

        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, y, "product_materials (Спецификация)")
        y -= 20
        c.setFont("Helvetica", 10)
        c.drawString(70, y, "PK id_product INTEGER (FK -> products)")
        y -= 15
        c.drawString(70, y, "PK id_material INTEGER (FK -> materials)")
        y -= 15
        c.drawString(70, y, "quantity_per_unit REAL (норма расхода на 1 шт.)")
        y -= 25

        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, y, "customers (Заказчики)")
        y -= 20
        c.setFont("Helvetica", 10)
        c.drawString(70, y, "PK id_customer INTEGER")
        y -= 15
        c.drawString(70, y, "full_name TEXT NOT NULL")
        y -= 15
        c.drawString(70, y, "phone TEXT")
        y -= 15
        c.drawString(70, y, "email TEXT")
        y -= 25

        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, y, "orders (Заказы)")
        y -= 20
        c.setFont("Helvetica", 10)
        c.drawString(70, y, "PK id_order INTEGER")
        y -= 15
        c.drawString(70, y, "order_number TEXT")
        y -= 15
        c.drawString(70, y, "order_date TEXT")
        y -= 15
        c.drawString(70, y, "customer_id INTEGER (FK -> customers)")
        y -= 25

        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, y, "order_items (Позиции заказа)")
        y -= 20
        c.setFont("Helvetica", 10)
        c.drawString(70, y, "PK id_order_item INTEGER")
        y -= 15
        c.drawString(70, y, "id_order INTEGER (FK -> orders)")
        y -= 15
        c.drawString(70, y, "id_product INTEGER (FK -> products)")
        y -= 15
        c.drawString(70, y, "quantity INTEGER")
        y -= 25

        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, y, "Связи:")
        y -= 20
        c.setFont("Helvetica", 10)
        c.drawString(70, y, "products (M) --- product_materials --- (M) materials (многие ко многим)")
        y -= 15
        c.drawString(70, y, "customers (1) ---< orders (many) — один заказчик может иметь много заказов")
        y -= 15
        c.drawString(70, y, "orders (1) ---< order_items (many) ---< products (1)")

        c.save()
        return pdf_path
    except ImportError:
        txt_path = "ER_Diagram.txt"
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write("ER-диаграмма (текстовое описание)\n\n")
            f.write("Таблицы:\n")
            f.write("- products (PK id_product, name)\n")
            f.write("- materials (PK id_material, name, price)\n")
            f.write("- product_materials (PK id_product, PK id_material, quantity_per_unit)\n")
            f.write("- customers (PK id_customer, full_name, phone, email)\n")
            f.write("- orders (PK id_order, order_number, order_date, customer_id FK)\n")
            f.write("- order_items (PK id_order_item, id_order FK, id_product FK, quantity)\n\n")
            f.write("Связи:\n")
            f.write("- products (M) -< product_materials >- (M) materials\n")
            f.write("- customers (1) -< orders (many)\n")
            f.write("- orders (1) -< order_items (many) -< products (1)\n")
        return txt_path


# МОДУЛЬ 2

def create_tables():
    """Создание всех таблиц (предварительно удаляем старые)"""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("DROP TABLE IF EXISTS order_items")
    cur.execute("DROP TABLE IF EXISTS orders")
    cur.execute("DROP TABLE IF EXISTS customers")
    cur.execute("DROP TABLE IF EXISTS product_materials")
    cur.execute("DROP TABLE IF EXISTS materials")
    cur.execute("DROP TABLE IF EXISTS products")

    cur.execute('''
        CREATE TABLE products (
            id_product INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        )
    ''')
    cur.execute('''
        CREATE TABLE materials (
            id_material INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            price REAL NOT NULL
        )
    ''')
    cur.execute('''
        CREATE TABLE product_materials (
            id_product INTEGER NOT NULL,
            id_material INTEGER NOT NULL,
            quantity_per_unit REAL NOT NULL,
            FOREIGN KEY (id_product) REFERENCES products(id_product),
            FOREIGN KEY (id_material) REFERENCES materials(id_material),
            PRIMARY KEY (id_product, id_material)
        )
    ''')
    cur.execute('''
        CREATE TABLE customers (
            id_customer INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            phone TEXT,
            email TEXT
        )
    ''')
    cur.execute('''
        CREATE TABLE orders (
            id_order INTEGER PRIMARY KEY AUTOINCREMENT,
            order_number TEXT,
            order_date TEXT,
            customer_id INTEGER NOT NULL,
            FOREIGN KEY (customer_id) REFERENCES customers(id_customer)
        )
    ''')
    cur.execute('''
        CREATE TABLE order_items (
            id_order_item INTEGER PRIMARY KEY AUTOINCREMENT,
            id_order INTEGER NOT NULL,
            id_product INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            FOREIGN KEY (id_order) REFERENCES orders(id_order),
            FOREIGN KEY (id_product) REFERENCES products(id_product)
        )
    ''')
    conn.commit()
    conn.close()


def fill_products():
    products = ["Хлеб белый 1 кг", "Хлеб ржаной 800г", "Булочка с изюмом"]
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    for name in products:
        cur.execute("INSERT OR IGNORE INTO products (name) VALUES (?)", (name,))
    conn.commit()
    conn.close()


def fill_materials():
    materials = [
        ("Изюм", 150.0),
        ("Масло сливочное", 124.0),
        ("Молоко нормализованное", 34.0),
        ("Яйца", 80.0),
        ("Мука", 220.0),
        ("Сода", 60.0),
        ("Вода", 0.0),
        ("Соль", 10.0),
        ("Дрожжи", 100.0),
        ("Мука ржаная", 120.0)
    ]
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    for name, price in materials:
        cur.execute("INSERT OR IGNORE INTO materials (name, price) VALUES (?, ?)", (name, price))
    conn.commit()
    conn.close()


def fill_specifications():
    specs = {
        "Булочка с изюмом": [
            ("Изюм", 0.02),
            ("Масло сливочное", 0.02),
            ("Молоко нормализованное", 0.15),
            ("Яйца", 0.25),
            ("Мука", 0.1),
            ("Сода", 0.005)
        ],
        "Хлеб белый 1 кг": [
            ("Мука", 0.7),
            ("Вода", 0.3),
            ("Соль", 0.01),
            ("Дрожжи", 0.01)
        ],
        "Хлеб ржаной 800г": [
            ("Мука ржаная", 0.5),
            ("Мука", 0.2),
            ("Вода", 0.3),
            ("Соль", 0.01),
            ("Дрожжи", 0.01)
        ]
    }
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    for prod_name, mat_list in specs.items():
        cur.execute("SELECT id_product FROM products WHERE name = ?", (prod_name,))
        prod = cur.fetchone()
        if not prod:
            continue
        prod_id = prod[0]
        for mat_name, qty in mat_list:
            cur.execute("SELECT id_material FROM materials WHERE name = ?", (mat_name,))
            mat = cur.fetchone()
            if mat:
                cur.execute('''
                    INSERT OR REPLACE INTO product_materials (id_product, id_material, quantity_per_unit)
                    VALUES (?, ?, ?)
                ''', (prod_id, mat[0], qty))
    conn.commit()
    conn.close()


def fill_customers_from_json():
    json_path = "Заказчики.json"
    if not os.path.exists(json_path):
        print(f"Файл {json_path} не найден. Таблица customers останется пустой.")
        return

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    for item in data:
        full_name = item.get("name")
        if not full_name:
            continue
        phone = item.get("phone", "")
        email = ""
        cur.execute('''
            INSERT INTO customers (full_name, phone, email)
            VALUES (?, ?, ?)
        ''', (full_name, phone, email))
    conn.commit()
    conn.close()


def fill_order_and_items():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("SELECT id_customer FROM customers WHERE full_name = ?", ("ООО \"Фрегат\"",))
    customer = cur.fetchone()
    if not customer:

        cur.execute("SELECT id_customer, full_name FROM customers LIMIT 1")
        first = cur.fetchone()
        if not first:
            print("Нет ни одного заказчика. Заказ не будет добавлен.")
            conn.close()
            return
        customer_id = first[0]
        print(f"Заказчик 'ООО \"Фрегат\"' не найден. Использую первого: {first[1]}")
    else:
        customer_id = customer[0]

    cur.execute('''
        INSERT INTO orders (order_number, order_date, customer_id)
        VALUES (?, ?, ?)
    ''', ("3", "2025-06-07", customer_id))
    order_id = cur.lastrowid

    def get_product_id(name):
        cur.execute("SELECT id_product FROM products WHERE name = ?", (name,))
        row = cur.fetchone()
        return row[0] if row else None

    white_id = get_product_id("Хлеб белый 1 кг")
    rye_id = get_product_id("Хлеб ржаной 800г")

    if white_id:
        cur.execute("INSERT INTO order_items (id_order, id_product, quantity) VALUES (?, ?, ?)",
                    (order_id, white_id, 8))
    if rye_id:
        cur.execute("INSERT INTO order_items (id_order, id_product, quantity) VALUES (?, ?, ?)",
                    (order_id, rye_id, 7))

    conn.commit()
    conn.close()


def init_database():
    create_tables()
    fill_products()
    fill_materials()
    fill_specifications()
    fill_customers_from_json()
    fill_order_and_items()
    print("База данных успешно создана и заполнена.")


# МОДУЛЬ 3

def get_order_total_cost(order_id: int) -> float:
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    query = '''
        SELECT SUM(oi.quantity * pm.quantity_per_unit * m.price)
        FROM order_items oi
        JOIN products p ON oi.id_product = p.id_product
        JOIN product_materials pm ON p.id_product = pm.id_product
        JOIN materials m ON pm.id_material = m.id_material
        WHERE oi.id_order = ?
    '''
    cur.execute(query, (order_id,))
    result = cur.fetchone()[0]
    conn.close()
    return result if result is not None else 0.0


if __name__ == "__main__":
    init_database()
    er_file = generate_er_diagram()
    print(f"ER-диаграмма сохранена в {er_file}")

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT id_order, order_number FROM orders WHERE order_number = '3'")
    order = cur.fetchone()
    conn.close()
    if order:
        order_id, order_num = order
        cost = get_order_total_cost(order_id)
        print(f"Себестоимость заказа №{order_num} = {cost:.2f} руб.")
    else:
        print("Заказ №3 не найден.")