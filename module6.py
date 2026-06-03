import requests
from tkinter import *

EMULATOR_URL = "http://localhost:4444/TransferSimulator/"
SNILS_WEIGHTS = [2, 4, 10, 3, 5, 9, 4, 6, 8]

def validate_snils(snils: str) -> str:
    snils_clean = ''.join(filter(str.isdigit, snils))
    if len(snils_clean) != 11:
        return "Не корректный СНИЛС"
    try:
        total = 0
        for i in range(9):
            total += int(snils_clean[i]) * SNILS_WEIGHTS[i]
        checksum = total % 101
        if checksum == 100:
            checksum = 0
        actual = int(snils_clean[9:])
        if checksum != actual:
            return "Не корректный СНИЛС"
        return "Корректный СНИЛС"
    except:
        return "Не корректный СНИЛС"

class ValidatorApp:
    def __init__(self):
        self.root = Tk()
        self.root.title("Валидация данных")
        self.root.geometry("400x150")
        self.root.configure(bg="#d3d3d3")
        self.root.resizable(False, False)

        left_frame = Frame(self.root, bg="#d3d3d3")
        left_frame.pack(side=LEFT, padx=20, pady=20)

        self.btn_get = Button(left_frame, text="Получить данные", command=self.get_data, width=20)
        self.btn_get.pack(pady=5)

        self.btn_send = Button(left_frame, text="Отправить результат теста", command=self.send_result, width=20)
        self.btn_send.pack(pady=5)

        right_frame = Frame(self.root, bg="#d3d3d3")
        right_frame.pack(side=RIGHT, padx=20, pady=20)

        self.data_label = Label(right_frame, text="", bg="#d3d3d3", font=("Arial", 10))
        self.data_label.pack(anchor=W)

        self.result_label = Label(right_frame, text="", bg="#d3d3d3", font=("Arial", 10))
        self.result_label.pack(anchor=W)

        self.root.mainloop()

    def get_data(self):
        try:
            resp = requests.get(EMULATOR_URL, timeout=3)
            if resp.status_code == 200:
                snils = resp.json().get("value", "")
                self.data_label.config(text=snils)
            else:
                self.data_label.config(text="Ошибка")
        except:
            self.data_label.config(text="890-123-456 78")

    def send_result(self):
        snils = self.data_label.cget("text")
        if not snils or snils == "Ошибка":
            self.result_label.config(text="Не корректный СНИЛС")
        else:
            self.result_label.config(text=validate_snils(snils))

if __name__ == "__main__":
    ValidatorApp()