import sys
import sqlite3
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QPushButton, QLabel, QLineEdit, QVBoxLayout, QWidget,
    QMessageBox, QTableWidget, QTableWidgetItem, QInputDialog, QHBoxLayout
)
from PyQt6.QtCore import Qt


class Database:
    def __init__(self):
        self.conn = sqlite3.connect("dictionary_app.db")
        self.create_tables()

    def create_tables(self):
        with self.conn:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    role TEXT NOT NULL
                )
            """)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS dictionaries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    created_by INTEGER,
                    FOREIGN KEY (created_by) REFERENCES users (id)
                )
            """)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS words (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    dictionary_id INTEGER,
                    word TEXT NOT NULL,
                    translation TEXT NOT NULL,
                    FOREIGN KEY (dictionary_id) REFERENCES dictionaries (id)
                )
            """)

    def register_user(self, username, password, role):
        try:
            with self.conn:
                self.conn.execute(
                    "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                    (username, password, role)
                )
            return True
        except sqlite3.IntegrityError:
            return False

    def authenticate_user(self, username, password):
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT id, role FROM users WHERE username = ? AND password = ?",
            (username, password)
        )
        return cursor.fetchone()

    def get_dictionaries(self, user_id=None, admin=False):
        cursor = self.conn.cursor()
        if admin:
            cursor.execute("SELECT id, name FROM dictionaries WHERE created_by = ?", (user_id,))
        else:
            cursor.execute("SELECT id, name FROM dictionaries")
        return cursor.fetchall()

    def create_dictionary(self, name, user_id):
        with self.conn:
            self.conn.execute(
                "INSERT INTO dictionaries (name, created_by) VALUES (?, ?)",
                (name, user_id)
            )

    def delete_dictionary(self, dictionary_id):
        with self.conn:
            self.conn.execute("DELETE FROM dictionaries WHERE id = ?", (dictionary_id,))
            self.conn.execute("DELETE FROM words WHERE dictionary_id = ?", (dictionary_id,))

    def get_words(self, dictionary_id):
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, word, translation FROM words WHERE dictionary_id = ?", (dictionary_id,))
        return cursor.fetchall()

    def add_word(self, dictionary_id, word, translation):
        with self.conn:
            self.conn.execute(
                "INSERT INTO words (dictionary_id, word, translation) VALUES (?, ?, ?)",
                (dictionary_id, word, translation)
            )

    def delete_word(self, word_id):
        with self.conn:
            self.conn.execute("DELETE FROM words WHERE id = ?", (word_id,))


class LoginWindow(QMainWindow):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.setWindowTitle("Login")
        self.setGeometry(200, 200, 300, 150)

        layout = QVBoxLayout()

        self.username_input = QLineEdit(self)
        self.username_input.setPlaceholderText("Username")
        layout.addWidget(self.username_input)

        self.password_input = QLineEdit(self)
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.password_input)

        self.login_button = QPushButton("Login", self)
        self.login_button.clicked.connect(self.login)
        layout.addWidget(self.login_button)

        self.register_button = QPushButton("Register", self)
        self.register_button.clicked.connect(self.register)
        layout.addWidget(self.register_button)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def login(self):
        username = self.username_input.text()
        password = self.password_input.text()
        user = self.db.authenticate_user(username, password)

        if user:
            self.main_window = MainWindow(self.db, user)
            self.main_window.show()
            self.close()
        else:
            QMessageBox.warning(self, "Error", "Invalid credentials")

    def register(self):
        username, ok = QInputDialog.getText(self, "Register", "Enter username:")
        if not ok or not username:
            return

        password, ok = QInputDialog.getText(self, "Register", "Enter password:", QLineEdit.EchoMode.Password)
        if not ok or not password:
            return

        role, ok = QInputDialog.getItem(self, "Register", "Select role:", ["user", "admin"], 0, False)
        if not ok:
            return

        if self.db.register_user(username, password, role):
            QMessageBox.information(self, "Success", "User registered successfully")
        else:
            QMessageBox.warning(self, "Error", "Username already exists")


class MainWindow(QMainWindow):
    def __init__(self, db, user):
        super().__init__()
        self.db = db
        self.user_id, self.role = user
        self.setWindowTitle("Dictionary App")
        self.setGeometry(200, 200, 600, 400)

        layout = QVBoxLayout()

        self.dictionaries_table = QTableWidget()
        self.dictionaries_table.setColumnCount(2)
        self.dictionaries_table.setHorizontalHeaderLabels(["ID", "Name"])
        self.dictionaries_table.cellDoubleClicked.connect(self.open_dictionary)
        layout.addWidget(self.dictionaries_table)

        if self.role == "admin":
            self.create_dict_button = QPushButton("Create Dictionary")
            self.create_dict_button.clicked.connect(self.create_dictionary)
            layout.addWidget(self.create_dict_button)

            self.delete_dict_button = QPushButton("Delete Dictionary")
            self.delete_dict_button.clicked.connect(self.delete_dictionary)
            layout.addWidget(self.delete_dict_button)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        self.load_dictionaries()

    def load_dictionaries(self):
        self.dictionaries_table.setRowCount(0)
        dictionaries = self.db.get_dictionaries(
            user_id=self.user_id if self.role == "admin" else None,
            admin=self.role == "admin"
        )
        for row, (dict_id, name) in enumerate(dictionaries):
            self.dictionaries_table.insertRow(row)
            self.dictionaries_table.setItem(row, 0, QTableWidgetItem(str(dict_id)))
            self.dictionaries_table.setItem(row, 1, QTableWidgetItem(name))

    def create_dictionary(self):
        name, ok = QInputDialog.getText(self, "Create Dictionary", "Enter dictionary name:")
        if ok and name:
            self.db.create_dictionary(name, self.user_id)
            self.load_dictionaries()

    def delete_dictionary(self):
        current_row = self.dictionaries_table.currentRow()
        if current_row == -1:
            QMessageBox.warning(self, "Error", "No dictionary selected")
            return

        dict_id = int(self.dictionaries_table.item(current_row, 0).text())
        self.db.delete_dictionary(dict_id)
        self.load_dictionaries()

    def open_dictionary(self, row, column):
        dict_id = int(self.dictionaries_table.item(row, 0).text())
        self.dictionary_window = DictionaryWindow(self.db, dict_id)
        self.dictionary_window.show()


    def load_dictionaries(self):
        self.dictionaries_table.setRowCount(0)
        dictionaries = self.db.get_dictionaries(
            user_id=self.user_id if self.role == "admin" else None,
            admin=self.role == "admin"
        )
        for row, (dict_id, name) in enumerate(dictionaries):
            self.dictionaries_table.insertRow(row)
            self.dictionaries_table.setItem(row, 0, QTableWidgetItem(str(dict_id)))
            self.dictionaries_table.setItem(row, 1, QTableWidgetItem(name))

    def create_dictionary(self):
        name, ok = QInputDialog.getText(self, "Create Dictionary", "Enter dictionary name:")
        if ok and name:
            self.db.create_dictionary(name, self.user_id)
            self.load_dictionaries()

    def delete_dictionary(self):
        current_row = self.dictionaries_table.currentRow()
        if current_row == -1:
            QMessageBox.warning(self, "Error", "No dictionary selected")
            return

        dict_id = int(self.dictionaries_table.item(current_row, 0).text())
        self.db.delete_dictionary(dict_id)
        self.load_dictionaries()

    def open_dictionary(self, row, column):
        dict_id = int(self.dictionaries_table.item(row, 0).text())
        self.dictionary_window = DictionaryWindow(self.db, dict_id)
        self.dictionary_window.show()


class DictionaryWindow(QMainWindow):
    def __init__(self, db, dictionary_id):
        super().__init__()
        self.db = db
        self.dictionary_id = dictionary_id
        self.setWindowTitle("Dictionary")
        self.setGeometry(300, 200, 600, 400)

        layout = QVBoxLayout()

        self.words_table = QTableWidget()
        self.words_table.setColumnCount(3)
        self.words_table.setHorizontalHeaderLabels(["ID", "Word", "Translation"])
        layout.addWidget(self.words_table)

        buttons_layout = QHBoxLayout()
        self.add_word_button = QPushButton("Add Word")
        self.add_word_button.clicked.connect(self.add_word)
        buttons_layout.addWidget(self.add_word_button)

        self.delete_word_button = QPushButton("Delete Word")
        self.delete_word_button.clicked.connect(self.delete_word)
        buttons_layout.addWidget(self.delete_word_button)

        layout.addLayout(buttons_layout)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        self.load_words()

    def load_words(self):
        self.words_table.setRowCount(0)
        words = self.db.get_words(self.dictionary_id)
        for row, (word_id, word, translation) in enumerate(words):
            self.words_table.insertRow(row)
            self.words_table.setItem(row, 0, QTableWidgetItem(str(word_id)))
            self.words_table.setItem(row, 1, QTableWidgetItem(word))
            self.words_table.setItem(row, 2, QTableWidgetItem(translation))

    def add_word(self):
        word, ok = QInputDialog.getText(self, "Add Word", "Enter word:")
        if not ok or not word:
            return

        translation, ok = QInputDialog.getText(self, "Add Translation", "Enter translation:")
        if not ok or not translation:
            return

        self.db.add_word(self.dictionary_id, word, translation)
        self.load_words()

    def delete_word(self):
        current_row = self.words_table.currentRow()
        if current_row == -1:
            QMessageBox.warning(self, "Error", "No word selected")
            return

        word_id = int(self.words_table.item(current_row, 0).text())
        self.db.delete_word(word_id)
        self.load_words()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(open("style.css").read())
    db = Database()
    login_window = LoginWindow(db)
    login_window.show()
    sys.exit(app.exec())
