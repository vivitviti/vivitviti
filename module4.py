import sqlite3
import hashlib
import random
import os
from tkinter import *
from tkinter import ttk, messagebox
from PIL import Image, ImageTk, ImageDraw

DB_NAME = "enterprise.db"

def init_users_table():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id_user INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL,
            is_blocked INTEGER DEFAULT 0,
            failed_attempts INTEGER DEFAULT 0
        )
    ''')
    cur.execute("SELECT COUNT(*) FROM users")
    if cur.fetchone()[0] == 0:
        admin_hash = hashlib.sha256("admin123".encode()).hexdigest()
        user_hash = hashlib.sha256("user123".encode()).hexdigest()
        cur.execute("INSERT INTO users (username, password_hash, role) VALUES (?,?,?)",
                    ("admin", admin_hash, "admin"))
        cur.execute("INSERT INTO users (username, password_hash, role) VALUES (?,?,?)",
                    ("user", user_hash, "user"))
    conn.commit()
    conn.close()


class PuzzleCaptcha:
    def __init__(self, parent, on_success_callback):
        self.parent = parent
        self.on_success = on_success_callback
        self.fragments = []
        self.buttons = []
        self.correct_order = [0, 1, 2, 3]
        self.current_order = []
        self.failed_attempts = 0
        self.MAX_ATTEMPTS = 3
        self.selected_index = None
        self.locked = False
        self.frame = Frame(parent, bg="white", bd=2, relief=GROOVE)
        self.load_fragments()
        self.create_puzzle_grid()

    def load_fragments(self):
        fragment_files = ["1.png", "2.png", "3.png", "4.png"]
        for f in fragment_files:
            img = Image.open(f)
            img = img.resize((100, 100), Image.Resampling.LANCZOS)
            self.fragments.append(ImageTk.PhotoImage(img))
        self.current_order = self.correct_order.copy()
        random.shuffle(self.current_order)

    def create_puzzle_grid(self):
        for w in self.frame.winfo_children():
            w.destroy()
        self.buttons.clear()
        self.selected_index = None
        for idx, frag_idx in enumerate(self.current_order):
            btn = Button(self.frame, image=self.fragments[frag_idx],
                         command=lambda i=idx: self.on_fragment_click(i))
            btn.grid(row=idx//2, column=idx%2, padx=2, pady=2, sticky="nsew")
            self.buttons.append(btn)
        for i in range(2):
            self.frame.grid_rowconfigure(i, weight=1)
            self.frame.grid_columnconfigure(i, weight=1)

    def on_fragment_click(self, clicked_index):
        if self.locked:
            return
        if self.selected_index is None:
            self.selected_index = clicked_index
            self.buttons[clicked_index].config(relief=SUNKEN, bg="lightblue")
        else:
            if self.selected_index == clicked_index:
                self.buttons[self.selected_index].config(relief=RAISED, bg="SystemButtonFace")
                self.selected_index = None
                return
            self.current_order[self.selected_index], self.current_order[clicked_index] = \
                self.current_order[clicked_index], self.current_order[self.selected_index]
            self.buttons[self.selected_index].config(relief=RAISED, bg="SystemButtonFace")
            self.selected_index = None
            self.create_puzzle_grid()

    def check_solution(self):
        if self.locked:
            return True
        if self.current_order == self.correct_order:
            self.locked = True
            for btn in self.buttons:
                btn.config(state=DISABLED)
            if self.on_success:
                self.on_success()
            return True
        else:
            self.failed_attempts += 1
            if self.failed_attempts >= self.MAX_ATTEMPTS:
                self.locked = True
                for btn in self.buttons:
                    btn.config(state=DISABLED, text="ЗАБЛОКИРОВАНО")
                return "blocked"
            return False

    def get_frame(self):
        return self.frame


class LoginWindow:
    def __init__(self, master):
        self.master = master
        self.master.title("Авторизация - Информационная система предприятия")
        self.master.minsize(450, 650)
        self.master.geometry("500x700")
        self.captcha_ok = False
        self.setup_ui()

    def setup_ui(self):
        Label(self.master, text="Вход в систему", font=("Arial", 18, "bold")).pack(pady=20)
        main_frame = Frame(self.master)
        main_frame.pack(fill=BOTH, expand=True, padx=20, pady=10)

        cred_frame = LabelFrame(main_frame, text="Учётные данные", font=("Arial", 12))
        cred_frame.pack(fill=X, pady=5)
        Label(cred_frame, text="Логин:", font=("Arial", 12)).grid(row=0, column=0, padx=5, pady=10, sticky="e")
        self.entry_login = Entry(cred_frame, width=30, font=("Arial", 12))
        self.entry_login.grid(row=0, column=1, padx=5, pady=10)
        Label(cred_frame, text="Пароль:", font=("Arial", 12)).grid(row=1, column=0, padx=5, pady=10, sticky="e")
        self.entry_password = Entry(cred_frame, width=30, font=("Arial", 12), show="*")
        self.entry_password.grid(row=1, column=1, padx=5, pady=10)

        captcha_frame = LabelFrame(main_frame, text="Капча (соберите пазл)", font=("Arial", 12))
        captcha_frame.pack(fill=BOTH, expand=True, pady=5)
        Label(captcha_frame, text="Кликните на два фрагмента для обмена", font=("Arial", 10)).pack(pady=5)
        self.captcha = PuzzleCaptcha(captcha_frame, self.on_captcha_success)
        self.captcha.get_frame().pack(pady=10)

        btn_frame = Frame(main_frame)
        btn_frame.pack(pady=10)
        self.btn_check = Button(btn_frame, text="Проверить пазл", command=self.check_captcha,
                                bg="orange", fg="white", font=("Arial", 12), width=15)
        self.btn_check.pack(side=LEFT, padx=5)
        self.btn_login = Button(btn_frame, text="Войти", command=self.do_login,
                                bg="green", fg="white", font=("Arial", 12), width=15, state=DISABLED)
        self.btn_login.pack(side=LEFT, padx=5)

        self.status_label = Label(main_frame, text="", font=("Arial", 10))
        self.status_label.pack(pady=5)

    def on_captcha_success(self):
        self.captcha_ok = True
        self.btn_login.config(state=NORMAL)
        self.status_label.config(text="Пазл собран верно! Можете войти.", fg="green")

    def check_captcha(self):
        result = self.captcha.check_solution()
        if result == "blocked":
            self.status_label.config(text="Вы заблокированы. Обратитесь к администратору", fg="red")
            self.btn_check.config(state=DISABLED)
            self.btn_login.config(state=DISABLED)

    def do_login(self):
        if not self.captcha_ok:
            messagebox.showerror("Ошибка", "Сначала соберите пазл и нажмите 'Проверить'")
            return
        login = self.entry_login.get().strip()
        password = self.entry_password.get()
        if not login or not password:
            messagebox.showerror("Ошибка", "Заполните все поля")
            return
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute("SELECT is_blocked FROM users WHERE username = ?", (login,))
        blocked = cur.fetchone()
        if blocked and blocked[0] == 1:
            messagebox.showerror("Доступ запрещен", "Вы заблокированы. Обратитесь к администратору")
            conn.close()
            return
        pwd_hash = hashlib.sha256(password.encode()).hexdigest()
        cur.execute("SELECT id_user, username, role FROM users WHERE username = ? AND password_hash = ?",
                    (login, pwd_hash))
        user = cur.fetchone()
        if user:
            cur.execute("UPDATE users SET failed_attempts = 0 WHERE id_user = ?", (user[0],))
            conn.commit()
            conn.close()
            messagebox.showinfo("Успех", "Вы успешно авторизовались")
            self.master.destroy()
            if user[2] == "admin":
                AdminApp(user[1])
            else:
                UserApp(user[1])
        else:
            cur.execute("SELECT id_user, failed_attempts FROM users WHERE username = ?", (login,))
            u = cur.fetchone()
            if u:
                uid, att = u
                att += 1
                if att >= 3:
                    cur.execute("UPDATE users SET failed_attempts = ?, is_blocked = 1 WHERE id_user = ?", (att, uid))
                    conn.commit()
                    messagebox.showerror("Блокировка", "Вы заблокированы. Обратитесь к администратору")
                else:
                    cur.execute("UPDATE users SET failed_attempts = ? WHERE id_user = ?", (att, uid))
                    conn.commit()
                    messagebox.showerror("Ошибка", "Вы ввели неверный логин или пароль. Пожалуйста проверьте ещё раз введенные данные")
            else:
                messagebox.showerror("Ошибка", "Вы ввели неверный логин или пароль. Пожалуйста проверьте ещё раз введенные данные")
            conn.close()


class AdminApp:
    def __init__(self, username):
        self.root = Tk()
        self.root.title(f"Административная панель - {username}")
        self.root.minsize(600, 400)
        self.root.geometry("800x500")
        Label(self.root, text=f"Добро пожаловать, {username} (Администратор)",
              font=("Arial", 16, "bold")).pack(pady=10)
        main_frame = Frame(self.root)
        main_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)

        self.tree = ttk.Treeview(main_frame, columns=("ID", "Логин", "Роль", "Заблокирован"), show="headings")
        for col in self.tree["columns"]:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=150)
        self.tree.pack(fill=BOTH, expand=True)

        btn_frame = Frame(main_frame)
        btn_frame.pack(fill=X, pady=10)
        Button(btn_frame, text="Добавить пользователя", command=self.add_user, bg="green", fg="white").pack(side=LEFT, padx=5)
        Button(btn_frame, text="Редактировать", command=self.edit_user, bg="orange", fg="white").pack(side=LEFT, padx=5)
        Button(btn_frame, text="Снять блокировку", command=self.unblock_user, bg="blue", fg="white").pack(side=LEFT, padx=5)
        Button(btn_frame, text="Обновить", command=self.load_users, bg="gray", fg="white").pack(side=LEFT, padx=5)
        Button(btn_frame, text="Выйти", command=self.root.destroy, bg="red", fg="white").pack(side=LEFT, padx=5)
        self.load_users()
        self.root.mainloop()

    def load_users(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute("SELECT id_user, username, role, is_blocked FROM users")
        for u in cur.fetchall():
            self.tree.insert("", END, values=(u[0], u[1], u[2], "Да" if u[3] else "Нет"))
        conn.close()

    def add_user(self):
        AddUserDialog(self.root, self.load_users)

    def edit_user(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showerror("Ошибка", "Выберите пользователя")
            return
        data = self.tree.item(sel[0])["values"]
        EditUserDialog(self.root, data[0], data[1], self.load_users)

    def unblock_user(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showerror("Ошибка", "Выберите пользователя")
            return
        uid = self.tree.item(sel[0])["values"][0]
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute("UPDATE users SET is_blocked = 0, failed_attempts = 0 WHERE id_user = ?", (uid,))
        conn.commit()
        conn.close()
        messagebox.showinfo("Успех", "Блокировка снята")
        self.load_users()


class AddUserDialog(Toplevel):
    def __init__(self, parent, refresh_cb):
        super().__init__(parent)
        self.refresh = refresh_cb
        self.title("Добавить пользователя")
        self.geometry("300x250")
        self.grab_set()
        Label(self, text="Логин:").pack(pady=5)
        self.entry_login = Entry(self)
        self.entry_login.pack(pady=5)
        Label(self, text="Пароль:").pack(pady=5)
        self.entry_password = Entry(self, show="*")
        self.entry_password.pack(pady=5)
        Label(self, text="Роль:").pack(pady=5)
        self.role_var = StringVar(value="user")
        OptionMenu(self, self.role_var, "admin", "user").pack(pady=5)
        Button(self, text="Сохранить", command=self.save).pack(pady=20)

    def save(self):
        login = self.entry_login.get().strip()
        pwd = self.entry_password.get()
        role = self.role_var.get()
        if not login or not pwd:
            messagebox.showerror("Ошибка", "Заполните все поля")
            return
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute("SELECT id_user FROM users WHERE username = ?", (login,))
        if cur.fetchone():
            messagebox.showerror("Ошибка", "Пользователь с таким логином уже существует")
            conn.close()
            return
        pwd_hash = hashlib.sha256(pwd.encode()).hexdigest()
        cur.execute("INSERT INTO users (username, password_hash, role, is_blocked, failed_attempts) VALUES (?,?,?,0,0)",
                    (login, pwd_hash, role))
        conn.commit()
        conn.close()
        messagebox.showinfo("Успех", "Пользователь добавлен")
        self.refresh()
        self.destroy()


class EditUserDialog(Toplevel):
    def __init__(self, parent, uid, current_login, refresh_cb):
        super().__init__(parent)
        self.uid = uid
        self.refresh = refresh_cb
        self.title("Редактировать пользователя")
        self.geometry("300x250")
        self.grab_set()
        Label(self, text="Логин:").pack(pady=5)
        self.entry_login = Entry(self)
        self.entry_login.insert(0, current_login)
        self.entry_login.pack(pady=5)
        Label(self, text="Новый пароль (оставьте пустым, чтобы не менять):").pack(pady=5)
        self.entry_password = Entry(self, show="*")
        self.entry_password.pack(pady=5)
        Button(self, text="Сохранить", command=self.save).pack(pady=20)

    def save(self):
        new_login = self.entry_login.get().strip()
        new_pwd = self.entry_password.get()
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        if new_pwd:
            pwd_hash = hashlib.sha256(new_pwd.encode()).hexdigest()
            cur.execute("UPDATE users SET username = ?, password_hash = ? WHERE id_user = ?",
                        (new_login, pwd_hash, self.uid))
        else:
            cur.execute("UPDATE users SET username = ? WHERE id_user = ?", (new_login, self.uid))
        conn.commit()
        conn.close()
        messagebox.showinfo("Успех", "Данные обновлены")
        self.refresh()
        self.destroy()


class UserApp:
    def __init__(self, username):
        self.root = Tk()
        self.root.title(f"Панель пользователя - {username}")
        self.root.minsize(400, 300)
        self.root.geometry("600x400")
        Label(self.root, text=f"Добро пожаловать, {username}", font=("Arial", 16, "bold")).pack(pady=50)
        Label(self.root, text="Это основное окно для пользователя с ролью 'Пользователь'", font=("Arial", 12)).pack(pady=10)
        Button(self.root, text="Выйти", command=self.root.destroy, bg="red", fg="white").pack(pady=30)
        self.root.mainloop()


if __name__ == "__main__":
    init_users_table()
    root = Tk()
    root.withdraw()
    login_win = LoginWindow(Toplevel(root))
    root.mainloop()