import sys
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QLineEdit, QPushButton, QListWidget, QMessageBox,
                             QFileDialog, QLabel, QDialog, QTextBrowser,
                             QPlainTextEdit)
from PyQt5.QtCore import QSettings
from collections import deque
import pandas as pd
from PyQt5.QtCore import pyqtSignal, Qt


class ExportWordsDialog(QDialog):
    exportSuccessful = pyqtSignal()

    def __init__(self, words, parent=None):
        super().__init__(parent)

        self.setWindowTitle('Prompt')
        self.setGeometry(200, 200, 400, 300)

        # Ограничиваем количество слов до 15
        self.words = words[:15]

        self.words_browser = QTextBrowser(self)
        self.words_browser.setPlainText(
            f"""
I want you to create a list in Python. This list should contain
definitions for each word in the following format: ['definition1',
'definition2', ...].

words: {self.words}.

You should only return a list with definitions in the output,
even without print
The list should be named 'definitions_list'.
You should not write the following: 'word1: blabla',
but like this: 'blabla'.

Also you need to create two examples of usage for every word.
You should return a list called 'examples_list'
which should look like this:
[ ['first example for the word 1', 'second example for the word 1'],
[first example for the word 2, ...], ...]
            """
        )

        self.add_definitions_button = QPushButton(
            'Add Definitions and Examples', self)
        self.add_definitions_button.clicked.connect(
            self.show_definitions_dialog)

        layout = QVBoxLayout(self)
        layout.addWidget(self.words_browser)
        layout.addWidget(self.add_definitions_button)

    def show_definitions_dialog(self):
        # Создаем диалоговое окно для ввода definitions_list и examples_list
        dialog = DefinitionsDialog(self)
        if dialog.exec_():
            definitions_and_examples = dialog.definitions_and_examples

            # Создаем таблицу Pandas
            data = {
                'word': self.words, 'definition': definitions_and_examples['definitions'], 'examples': [' '.join(definitions_and_examples['examples'][i]) for i in range(len(definitions_and_examples['examples']))]}
            word_table = pd.DataFrame(data)

            # Сохраняем таблицу в файл CSV
            csv_filename, _ = QFileDialog.getSaveFileName(
                self, 'Save CSV', '', 'CSV Files (*.csv)')
            if csv_filename:
                word_table.to_csv(csv_filename, index=False, sep=';')
                self.exportSuccessful.emit()


class DefinitionsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle('Add Definitions and Examples')
        self.setGeometry(200, 200, 400, 300)

        self.definitions_and_examples_input = QPlainTextEdit(self)
        self.ok_button = QPushButton('OK', self)
        self.cancel_button = QPushButton('Cancel', self)

        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel('Enter Definitions and Examples (in the format specified):'))
        layout.addWidget(self.definitions_and_examples_input)
        layout.addWidget(self.ok_button)
        layout.addWidget(self.cancel_button)

    @property
    def definitions_and_examples(self):
        try:
            input_text = self.definitions_and_examples_input.toPlainText()

            definitions_and_examples = {}

            exec(input_text, {}, definitions_and_examples)

            definitions_and_examples['definitions'] = definitions_and_examples.get(
                'definitions_list')
            definitions_and_examples['examples'] = definitions_and_examples.get(
                'examples_list')

            if not isinstance(definitions_and_examples, dict) or 'definitions' not in definitions_and_examples or 'examples' not in definitions_and_examples:
                raise ValueError(
                    "Invalid format. Please provide a dictionary with 'definitions' and 'examples' keys.")
            return definitions_and_examples
        except Exception as e:
            QMessageBox.warning(
                self, 'Warning', f'Invalid format for Definitions and Examples: {e}')
            return {'definitions': [], 'examples': []}


class WordTableDialog(QDialog):
    def __init__(self, word_table, parent=None):
        super().__init__(parent)

        self.setWindowTitle('Word Table')
        self.setGeometry(200, 200, 600, 400)

        self.word_table_browser = QTextBrowser(self)
        self.word_table_browser.setPlainText(str(word_table))

        layout = QVBoxLayout(self)
        layout.addWidget(self.word_table_browser)


class WordListApp(QWidget):
    def __init__(self):
        super().__init__()

        self.words_set = set()  # Множество для хранения уникальных слов
        self.last_words = deque(maxlen=15)
        self.word_storage_file = "word_storage.txt"
        self.settings = QSettings("WordListApp", "Settings")

        self.remove_exported_words_button = QPushButton(
            'Remove Exported Words', self)
        self.remove_exported_words_button.setEnabled(False)
        self.remove_exported_words_button.clicked.connect(
            self.remove_or_keep_exported_words)

        self.init_ui()

    def init_ui(self):
        self.setWindowTitle('Word List App')

        # Создаем виджеты
        self.word_input = QLineEdit(self)
        self.add_button = QPushButton('Add', self)
        self.remove_button = QPushButton(
            'Delete', self)  # Добавлен новый QPushButton
        self.export_button = QPushButton('Export', self)
        self.export_button.clicked.connect(self.export_words)
        self.export_dialog = None
        self.word_list = QListWidget(self)
        self.last_words_label = QLabel(self)

        # Настройка макета
        vbox = QVBoxLayout()
        vbox.addWidget(self.word_input)
        vbox.addWidget(self.add_button)
        vbox.addWidget(self.remove_button)
        vbox.addWidget(self.export_button)
        vbox.addWidget(self.word_list)
        vbox.addWidget(self.last_words_label)
        vbox.addWidget(self.remove_exported_words_button)
        hbox = QHBoxLayout()
        hbox.addLayout(vbox)

        # Настройка обработчиков событий
        self.add_button.clicked.connect(self.add_word)
        self.word_input.returnPressed.connect(self.add_word_from_input)
        # Добавлен новый обработчик для кнопки Удалить
        self.remove_button.clicked.connect(self.remove_word)
        self.export_button.clicked.connect(self.export_words)

        # Устанавливаем макет
        self.setLayout(hbox)

        # Применяем тему
        self.set_dark_theme()

        # Загружаем данные при запуске
        self.load_data()

    def closeEvent(self, event):
        # Сохраняем данные перед закрытием приложения
        self.save_data()
        event.accept()

    def load_data(self):
        # Загружаем первые 15 слов из файла
        with open(self.word_storage_file, 'r') as file:
            lines = file.readlines()
            self.last_words.extend([word.strip() for word in lines[:15]])

        # Загружаем данные из настроек
        saved_words = self.settings.value("words", [])
        self.words_set = set(saved_words)
        self.update_word_list()

    def save_data(self):
        # Сохраняем все слова в файл
        with open(self.word_storage_file, 'w') as file:
            file.write('\n'.join(self.words_set))

        # Сохраняем данные в настройках
        self.settings.setValue("words", list(self.words_set))

    def update_word_list(self):
        # Очищаем список и обновляем его
        self.word_list.clear()
        self.word_list.addItems(sorted(self.words_set))

    def remove_word(self):
        selected_item = self.word_list.currentItem()

        if selected_item:
            word = selected_item.text()
            self.words_set.remove(word)
            self.word_list.takeItem(self.word_list.row(selected_item))
        else:
            QMessageBox.warning(self, 'Warning', 'Choose the word to delete')

    def remove_or_keep_exported_words(self):
        # Prompt the user to choose whether to remove or keep exported words
        choice = QMessageBox.question(self, 'Remove or Keep Words',
                                      'Do you want to remove the exported words from the list?',
                                      QMessageBox.Yes | QMessageBox.No)
        if choice == QMessageBox.Yes:
            # Remove the exported words
            for word in self.export_dialog.words:
                if word in self.words_set:
                    self.words_set.remove(word)
                    self.word_list.takeItem(self.word_list.row(
                        self.word_list.findItems(word, Qt.MatchExactly)[0]))
            # Update the word list
            self.update_word_list()
        # Hide the button
        self.remove_exported_words_button.setEnabled(False)
        self.remove_exported_words_button.hide()

    def set_dark_theme(self):
        # Темный стиль
        dark_stylesheet = """
            QWidget {
                background-color: #333;
                color: #fff;
            }

            QLineEdit {
                background-color: #555;
                color: #fff;
                border: 1px solid #777;
                selection-background-color: #666;
            }

            QPushButton {
                background-color: #555;
                color: #fff;
                border: 1px solid #777;
                padding: 5px;
            }

            QListWidget {
                background-color: #555;
                color: #fff;
                border: 1px solid #777;
                selection-background-color: #666;
            }
        """
        self.setStyleSheet(dark_stylesheet)

    def add_word(self):
        input_text = self.word_input.text()

        # Разбиваем введенный текст на слова с учетом разделителей
        words = [word.strip() for word in input_text.split(',')]

        # Добавляем уникальные слова в множество и отображаем их в списке
        for word in words:
            if word and word not in self.words_set:
                self.words_set.add(word)
                self.last_words.appendleft(word)
                self.word_list.addItem(word)

        # Очищаем поле ввода
        self.word_input.clear()

    def add_word_from_input(self):
        # Добавляем слово при нажатии клавиши Enter
        self.add_word()

    def export_words(self):
        word_list = list(self.last_words)
        # Создаем диалоговое окно для вывода последних 25 слов
        self.export_dialog = ExportWordsDialog(word_list, self)
        self.export_dialog.exportSuccessful.connect(
            self.show_remove_exported_words_button)
        self.export_dialog.exec_()

    def show_remove_exported_words_button(self):
        # Enable and show the button after successful export
        self.remove_exported_words_button.setEnabled(True)
        self.remove_exported_words_button.show()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    word_list_app = WordListApp()
    word_list_app.setGeometry(100, 100, 400, 300)
    word_list_app.show()
    sys.exit(app.exec_())
    # Я хочу сделать так, чтобы я мог, нажав на кнопку, первые 25 слов
    # (или меньше, если их не набирается 25) переместить в промпт, который я
    # введу в chatgpt, потом вбив обратно результат промпта,
    # я хочу получить csv файл,
    # в котором в первой колонке будет название слова,
    # во втором definition,в третьем – два примера
