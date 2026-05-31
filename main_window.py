#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import sqlite3
import bcrypt
from datetime import datetime, timedelta
from decimal import Decimal
from dataclasses import dataclass
from contextlib import contextmanager

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

DB_PATH = "techmarket.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        failed_attempts INTEGER DEFAULT 0,
        lockout_end TIMESTAMP)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT,
        price DECIMAL(10,2) NOT NULL,
        discount_percent DECIMAL(5,2) DEFAULT 0,
        image_path TEXT)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS carts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS cart_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cart_id INTEGER NOT NULL REFERENCES carts(id) ON DELETE CASCADE,
        product_id INTEGER NOT NULL REFERENCES products(id),
        quantity INTEGER DEFAULT 1)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL REFERENCES users(id),
        order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        total_amount DECIMAL(10,2) NOT NULL)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS order_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
        product_id INTEGER NOT NULL REFERENCES products(id),
        quantity INTEGER NOT NULL,
        price_at_order DECIMAL(10,2) NOT NULL)''')
    conn.commit()

    cur.execute("SELECT COUNT(*) FROM products")
    if cur.fetchone()[0] == 0:
        test_products = [
            ('Смартфон X100', '6.5" AMOLED, 128GB', 24999.00, 10.0, 'phone.jpg'),
            ('Ноутбук Pro 15', 'Intel i7, 16GB RAM, 512GB SSD', 79999.00, 15.5, 'laptop.jpg'),
            ('Беспроводные наушники', 'Bluetooth 5.2, 30ч работы', 4999.00, 0, 'headphones.jpg'),
            ('Фитнес-браслет', 'Шагомер, пульсометр', 1999.00, 25.0, 'band.jpg'),
            ('Мышь игровая', 'RGB, 6 кнопок', 1299.00, 5.0, 'mouse.jpg'),
            ('Клавиатура механическая', 'Red Switch, RGB', 6590.00, 12.0, 'keyboard.jpg'),
            ('Монитор 27"', 'IPS, 144Hz', 18990.00, 8.5, 'monitor.jpg'),
            ('Внешний SSD 1TB', 'USB-C, 1050MB/s', 7990.00, 20.0, 'ssd.jpg')
        ]
        for p in test_products:
            cur.execute("INSERT INTO products (name, description, price, discount_percent, image_path) VALUES (?,?,?,?,?)", p)

    cur.execute("SELECT COUNT(*) FROM users")
    if cur.fetchone()[0] == 0:
        hashed = bcrypt.hashpw(b'admin123', bcrypt.gensalt()).decode('utf-8')
        cur.execute("INSERT INTO users (username, password_hash) VALUES (?,?)", ('admin', hashed))

    conn.commit()
    conn.close()

@dataclass
class Product:
    id: int
    name: str
    description: str
    price: Decimal
    discount_percent: float
    image_path: str
    @property
    def final_price(self) -> Decimal:
        return self.price * (100 - self.discount_percent) / 100

class DatabaseManager:
    def __init__(self, db_path):
        self.db_path = db_path
    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    def register_user(self, username, password):
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        with self.get_connection() as conn:
            try:
                conn.execute("INSERT INTO users (username, password_hash) VALUES (?,?)", (username, hashed))
                conn.commit()
                return True, None
            except sqlite3.IntegrityError:
                return False, "Логин уже существует"
    def authenticate(self, username, password):
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT lockout_end FROM users WHERE username = ?", (username,))
            row = cur.fetchone()
            if row and row['lockout_end']:
                lock = datetime.fromisoformat(row['lockout_end'])
                if lock > datetime.now():
                    return False, "Аккаунт заблокирован"
            cur.execute("SELECT id, password_hash, failed_attempts FROM users WHERE username = ?", (username,))
            user = cur.fetchone()
            if not user:
                return False, "Неверный логин или пароль"
            if bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
                cur.execute("UPDATE users SET failed_attempts=0, lockout_end=NULL WHERE id=?", (user['id'],))
                conn.commit()
                return True, user['id']
            else:
                attempts = user['failed_attempts'] + 1
                lockout = datetime.now() + timedelta(minutes=5) if attempts >= 3 else None
                cur.execute("UPDATE users SET failed_attempts=?, lockout_end=? WHERE id=?", (attempts, lockout, user['id']))
                conn.commit()
                return False, "Неверный логин или пароль"
    def get_all_products(self):
        with self.get_connection() as conn:
            return conn.execute("SELECT id, name, description, price, discount_percent, image_path FROM products").fetchall()
    def get_products_filtered(self, search_text, discount_range):
        with self.get_connection() as conn:
            query = "SELECT id, name, description, price, discount_percent, image_path FROM products WHERE 1=1"
            params = []
            if search_text:
                query += " AND (name LIKE ? OR description LIKE ?)"
                params.extend([f'%{search_text}%', f'%{search_text}%'])
            if discount_range:
                min_d, max_d = discount_range
                if max_d is None:
                    query += " AND discount_percent >= ?"
                    params.append(min_d)
                else:
                    query += " AND discount_percent BETWEEN ? AND ?"
                    params.extend([min_d, max_d])
            return conn.execute(query, params).fetchall()
    def get_or_create_cart(self, user_id):
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id FROM carts WHERE user_id = ?", (user_id,))
            row = cur.fetchone()
            if row:
                return row['id']
            cur.execute("INSERT INTO carts (user_id) VALUES (?)", (user_id,))
            conn.commit()
            return cur.lastrowid
    def add_to_cart(self, cart_id, product_id, quantity=1):
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id, quantity FROM cart_items WHERE cart_id=? AND product_id=?", (cart_id, product_id))
            item = cur.fetchone()
            if item:
                cur.execute("UPDATE cart_items SET quantity=? WHERE id=?", (item['quantity']+quantity, item['id']))
            else:
                cur.execute("INSERT INTO cart_items (cart_id, product_id, quantity) VALUES (?,?,?)", (cart_id, product_id, quantity))
            conn.commit()
    def get_cart_items_with_details(self, cart_id):
        with self.get_connection() as conn:
            return conn.execute('''
                SELECT ci.id, p.name, p.description, p.price, p.discount_percent, ci.quantity,
                       (p.price * (100 - p.discount_percent) / 100) * ci.quantity AS total
                FROM cart_items ci JOIN products p ON ci.product_id = p.id
                WHERE ci.cart_id = ?
            ''', (cart_id,)).fetchall()
    def remove_cart_item(self, cart_item_id):
        with self.get_connection() as conn:
            conn.execute("DELETE FROM cart_items WHERE id=?", (cart_item_id,))
            conn.commit()
    def clear_cart(self, cart_id):
        with self.get_connection() as conn:
            conn.execute("DELETE FROM cart_items WHERE cart_id=?", (cart_id,))
            conn.commit()
    def create_order(self, user_id, cart_id):
        with self.get_connection() as conn:
            cur = conn.cursor()
            items = cur.execute('''
                SELECT p.id, p.price*(100-p.discount_percent)/100, ci.quantity
                FROM cart_items ci JOIN products p ON ci.product_id=p.id
                WHERE ci.cart_id=?
            ''', (cart_id,)).fetchall()
            if not items:
                raise ValueError("Корзина пуста")
            total = sum(i[1]*i[2] for i in items)
            cur.execute("INSERT INTO orders (user_id, total_amount) VALUES (?,?)", (user_id, total))
            order_id = cur.lastrowid
            for prod_id, price_at, qty in items:
                cur.execute("INSERT INTO order_items (order_id, product_id, quantity, price_at_order) VALUES (?,?,?,?)",
                            (order_id, prod_id, qty, price_at))
            cur.execute("DELETE FROM cart_items WHERE cart_id=?", (cart_id,))
            conn.commit()
            return order_id

class ThemeManager(QObject):
    theme_changed = pyqtSignal()
    def __init__(self):
        super().__init__()
        self.current_theme = "main"
    def toggle_theme(self):
        self.current_theme = "alt" if self.current_theme == "main" else "main"
        self.theme_changed.emit()

class ProductCard(QFrame):
    clicked = pyqtSignal(int)
    def __init__(self, product: Product, theme_manager):
        super().__init__()
        self.product = product
        self.theme_manager = theme_manager
        self.setFrameShape(QFrame.Box)
        self.setFixedSize(350, 120)
        self.setup_ui()
        self.apply_theme()
        theme_manager.theme_changed.connect(self.apply_theme)
    def setup_ui(self):
        layout = QHBoxLayout(self)
        self.pix_label = QLabel()
        self.pix_label.setFixedSize(80,80)
        pix = QPixmap(f"images/{self.product.image_path}" if self.product.image_path else "images/default.png")
        if pix.isNull():
            pix = QPixmap("images/default.png")
        self.pix_label.setPixmap(pix.scaled(80,80, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        layout.addWidget(self.pix_label)
        center = QVBoxLayout()
        self.name_label = QLabel(self.product.name)
        self.name_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        self.desc_label = QLabel(self.product.description)
        self.desc_label.setWordWrap(True)
        center.addWidget(self.name_label)
        center.addWidget(self.desc_label)
        layout.addLayout(center, 1)
        right = QVBoxLayout()
        self.price_label = QLabel(f"{self.product.final_price:.2f} ₽")
        self.price_label.setStyleSheet("font-weight: bold; font-size: 16px; color: #d9534f;")
        right.addWidget(self.price_label)
        if self.product.discount_percent > 0:
            old = QLabel(f"{self.product.price:.2f} ₽")
            old.setStyleSheet("text-decoration: line-through; color: gray;")
            right.addWidget(old)
        layout.addLayout(right)
    def apply_theme(self):
        if self.theme_manager.current_theme == "main":
            self.setStyleSheet("QFrame { background-color: #ffffff; border: 1px solid #359A85; }")
        else:
            self.setStyleSheet("QFrame { background-color: #fff0f0; border: 1px solid #fcb2b2; }")
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.product.id)
        super().mousePressEvent(event)

class CartWindow(QWidget):
    cart_updated = pyqtSignal()
    def __init__(self, db, user_id, theme_manager):
        super().__init__()
        self.db = db
        self.user_id = user_id
        self.theme_manager = theme_manager
        self.cart_id = db.get_or_create_cart(user_id)
        self.setWindowTitle("Корзина")
        self.resize(700,500)
        self.setup_ui()
        self.load_cart()
    def setup_ui(self):
        layout = QVBoxLayout()
        header = QHBoxLayout()
        logo = QLabel()
        logo.setPixmap(QPixmap("images/logo.png").scaled(40,40, Qt.KeepAspectRatio))
        header.addWidget(logo)
        header.addWidget(QLabel("Корзина"), 1)
        btn = QPushButton("Сменить тему")
        btn.clicked.connect(self.theme_manager.toggle_theme)
        header.addWidget(btn)
        layout.addLayout(header)
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Название","Описание","Стоимость"])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_menu)
        layout.addWidget(self.table)
        total_layout = QHBoxLayout()
        total_layout.addWidget(QLabel("Общая сумма заказов:"))
        self.total_label = QLabel("0.00 ₽")
        self.total_label.setStyleSheet("font-weight: bold;")
        total_layout.addWidget(self.total_label)
        total_layout.addStretch()
        layout.addLayout(total_layout)
        bottom = QHBoxLayout()
        self.clear_btn = QPushButton("Очистить корзину")
        self.clear_btn.clicked.connect(self.clear_cart)
        self.order_btn = QPushButton("Оформить заказ")
        self.order_btn.clicked.connect(self.checkout)
        bottom.addWidget(self.clear_btn)
        bottom.addStretch()
        bottom.addWidget(self.order_btn)
        layout.addLayout(bottom)
        self.setLayout(layout)
    def load_cart(self):
        items = self.db.get_cart_items_with_details(self.cart_id)
        self.table.setRowCount(len(items))
        total = 0
        for i, item in enumerate(items):
            self.table.setItem(i,0, QTableWidgetItem(item['name']))
            self.table.setItem(i,1, QTableWidgetItem(item['description'][:50]))
            self.table.setItem(i,2, QTableWidgetItem(f"{item['total']:.2f} ₽"))
            total += item['total']
        self.total_label.setText(f"{total:.2f} ₽")
    def show_menu(self, pos):
        idx = self.table.indexAt(pos)
        if idx.isValid():
            menu = QMenu()
            act = menu.addAction("Удалить из корзины")
            if menu.exec_(self.table.mapToGlobal(pos)) == act:
                row = idx.row()
                items = self.db.get_cart_items_with_details(self.cart_id)
                self.db.remove_cart_item(items[row]['id'])
                self.load_cart()
                self.cart_updated.emit()
    def clear_cart(self):
        if QMessageBox.question(self,"Подтверждение","Очистить всю корзину?") == QMessageBox.Yes:
            self.db.clear_cart(self.cart_id)
            self.load_cart()
            self.cart_updated.emit()
    def checkout(self):
        if QMessageBox.question(self,"Оформление заказа","Подтвердить заказ?") == QMessageBox.Yes:
            try:
                oid = self.db.create_order(self.user_id, self.cart_id)
                QMessageBox.information(self,"Успех",f"Заказ №{oid} оформлен!")
                self.load_cart()
                self.cart_updated.emit()
            except Exception as e:
                QMessageBox.critical(self,"Ошибка",str(e))

class MainWindow(QMainWindow):
    def __init__(self, db, user_id):
        super().__init__()
        self.db = db
        self.user_id = user_id
        self.theme = ThemeManager()
        self.cart_count = 0
        self.setWindowTitle("TechMarket - Каталог")
        self.setMinimumSize(900,600)
        self.setup_ui()
        self.update_products()
        self.update_cart_counter()
    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main = QVBoxLayout(central)
        header = QHBoxLayout()
        logo = QLabel()
        logo.setPixmap(QPixmap("images/logo.png").scaled(60,60, Qt.KeepAspectRatio))
        header.addWidget(logo)
        header.addStretch()
        theme_btn = QPushButton("Сменить тему")
        theme_btn.clicked.connect(self.theme.toggle_theme)
        header.addWidget(theme_btn)
        main.addLayout(header)
        filter_layout = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Поиск...")
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["Без сортировки","от 0% до 14.99%","от 15% до 24.99%","более 25%"])
        self.search_btn = QPushButton("Найти")
        self.search_btn.clicked.connect(self.update_products)
        filter_layout.addWidget(self.search_edit)
        filter_layout.addWidget(self.sort_combo)
        filter_layout.addWidget(self.search_btn)
        main.addLayout(filter_layout)
        self.scroll_area = QScrollArea()
        self.scroll_widget = QWidget()
        self.card_layout = QGridLayout(self.scroll_widget)
        self.scroll_area.setWidget(self.scroll_widget)
        self.scroll_area.setWidgetResizable(True)
        main.addWidget(self.scroll_area, 1)
        bottom = QHBoxLayout()
        self.counter_label = QLabel()
        bottom.addWidget(self.counter_label)
        bottom.addStretch()
        self.cart_btn = QPushButton("Корзина (0)")
        self.cart_btn.clicked.connect(self.open_cart)
        bottom.addWidget(self.cart_btn)
        main.addLayout(bottom)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.global_menu)
    def update_products(self):
        text = self.search_edit.text().strip()
        dr = None
        mode = self.sort_combo.currentText()
        if mode == "от 0% до 14.99%":
            dr = (0, 14.99)
        elif mode == "от 15% до 24.99%":
            dr = (15, 24.99)
        elif mode == "более 25%":
            dr = (25, None)
        data = self.db.get_products_filtered(text, dr)
        self.products = [Product(**dict(p)) for p in data]
        self.display_products()
    def display_products(self):
        for i in reversed(range(self.card_layout.count())):
            w = self.card_layout.itemAt(i).widget()
            if w: w.deleteLater()
        row, col = 0, 0
        for prod in self.products:
            card = ProductCard(prod, self.theme)
            card.clicked.connect(self.on_select)
            card.setContextMenuPolicy(Qt.CustomContextMenu)
            card.customContextMenuRequested.connect(lambda pos, pid=prod.id: self.card_menu(pos, pid))
            self.card_layout.addWidget(card, row, col)
            col += 1
            if col >= 3:
                col = 0
                row += 1
        all_count = len(self.db.get_all_products())
        self.counter_label.setText(f"Показано {len(self.products)} из {all_count}")
    def on_select(self, pid):
        pass
    def card_menu(self, pos, pid):
        menu = QMenu()
        upd = menu.addAction("Обновить")
        add = menu.addAction("Добавить в корзину")
        act = menu.exec_(QCursor.pos())
        if act == upd:
            self.update_products()
        elif act == add:
            cart_id = self.db.get_or_create_cart(self.user_id)
            self.db.add_to_cart(cart_id, pid)
            self.update_cart_counter()
    def global_menu(self, pos):
        menu = QMenu()
        if menu.exec_(self.mapToGlobal(pos)) == menu.addAction("Обновить"):
            self.update_products()
    def update_cart_counter(self):
        cart_id = self.db.get_or_create_cart(self.user_id)
        items = self.db.get_cart_items_with_details(cart_id)
        total = sum(i['quantity'] for i in items)
        self.cart_count = total
        self.cart_btn.setText(f"Корзина ({total})")
    def open_cart(self):
        self.cart_win = CartWindow(self.db, self.user_id, self.theme)
        self.cart_win.cart_updated.connect(self.update_cart_counter)
        self.cart_win.show()

class AuthWindow(QWidget):
    def __init__(self, db, on_success):
        super().__init__()
        self.db = db
        self.on_success = on_success
        self.setWindowTitle("Авторизация")
        self.setFixedSize(400,300)
        self.setup_ui()
    def setup_ui(self):
        layout = QVBoxLayout()
        tabs = QTabWidget()
        login_tab = QWidget()
        reg_tab = QWidget()
        tabs.addTab(login_tab, "Вход")
        tabs.addTab(reg_tab, "Регистрация")
        login_layout = QFormLayout()
        self.login_user = QLineEdit()
        self.login_pass = QLineEdit()
        self.login_pass.setEchoMode(QLineEdit.Password)
        btn_login = QPushButton("Войти")
        btn_login.clicked.connect(self.do_login)
        login_layout.addRow("Логин:", self.login_user)
        login_layout.addRow("Пароль:", self.login_pass)
        login_layout.addRow(btn_login)
        login_tab.setLayout(login_layout)
        reg_layout = QFormLayout()
        self.reg_user = QLineEdit()
        self.reg_pass = QLineEdit()
        self.reg_pass.setEchoMode(QLineEdit.Password)
        self.reg_confirm = QLineEdit()
        self.reg_confirm.setEchoMode(QLineEdit.Password)
        btn_reg = QPushButton("Зарегистрироваться")
        btn_reg.clicked.connect(self.do_register)
        reg_layout.addRow("Логин:", self.reg_user)
        reg_layout.addRow("Пароль:", self.reg_pass)
        reg_layout.addRow("Подтвердите:", self.reg_confirm)
        reg_layout.addRow(btn_reg)
        reg_tab.setLayout(reg_layout)
        layout.addWidget(tabs)
        self.setLayout(layout)
    def do_login(self):
        ok, res = self.db.authenticate(self.login_user.text().strip(), self.login_pass.text())
        if ok:
            self.on_success(res)
            self.close()
        else:
            QMessageBox.critical(self, "Ошибка", res)
    def do_register(self):
        u = self.reg_user.text().strip()
        p = self.reg_pass.text()
        p2 = self.reg_confirm.text()
        if not u or not p:
            QMessageBox.warning(self,"Ошибка","Заполните поля")
            return
        if p != p2:
            QMessageBox.warning(self,"Ошибка","Пароли не совпадают")
            return
        if len(p) < 6:
            QMessageBox.warning(self,"Ошибка","Пароль >=6 символов")
            return
        ok, msg = self.db.register_user(u, p)
        if ok:
            QMessageBox.information(self,"Успех","Регистрация выполнена")
            self.login_user.setText(u)
        else:
            QMessageBox.critical(self,"Ошибка",msg)

def main():
    init_db()
    app = QApplication(sys.argv)
    db = DatabaseManager(DB_PATH)
    def start(user_id):
        win = MainWindow(db, user_id)
        win.show()
    auth = AuthWindow(db, start)
    auth.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()