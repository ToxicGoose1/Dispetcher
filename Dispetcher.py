import sys
import requests
import json
from PyQt5.QtWidgets import QApplication, QWidget, QGridLayout,QSizePolicy, QVBoxLayout, QTabWidget, QLabel, QSplitter, QTableWidget, QTableWidgetItem,QAbstractItemView, QPushButton, QButtonGroup, QMessageBox,QListWidget, QListWidgetItem, QHeaderView, QLineEdit, QCheckBox, QHBoxLayout
from PyQt5.QtCore import Qt, QTime, QTimer, QDate, QThread, pyqtSignal, QUrl, QSize, QStandardPaths
from PyQt5.QtWebEngineWidgets import QWebEngineView
from datetime import datetime, timedelta
from PyQt5.QtGui import QFont, QIcon
import pygame
import re
import threading
from queue import Empty, Queue
import queue
import os
import functools
import time 
from functools import partial
from PyQt5 import QtCore
from requests.exceptions import HTTPError
from PyQt5.QtGui import QColor
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent,QSound
from itertools import groupby
from operator import itemgetter


class AudioPlayer(QThread):
    finished = pyqtSignal()
    audio_pered_finished = pyqtSignal()
    
    def __init__(self, audio_path):
        super().__init__()
        self.audio_path = audio_path

    def run(self):
        pygame.mixer.init()
        pygame.mixer.music.load(self.audio_path)
        pygame.mixer.music.play()

        while pygame.mixer.music.get_busy():
            pygame.time.delay(100)

        pygame.mixer.quit()
        self.finished.emit()
class MyWindow(QWidget):
    def __init__(self):
        super().__init__()

        # Окно закрытия
        self.setWindowTitle('Подтверждение закрытия')
        self.setStyleSheet("""
            QDialog {
                background-color: #f0f0f0;
            }
        """)

        user_profile_path = os.environ['USERPROFILE']
        
        # Устанавливаем иконку приложения
        icon_path = os.path.join(user_profile_path, 'Desktop', 'Prog', 'bus.ico')
        self.setWindowIcon(QIcon(icon_path))



        self.days_checkboxes = []

        global username
        username = os.getlogin()

        # Инициализация Pygame.mixer
        pygame.mixer.init()
        pygame.init()

        self.index_history = {}

        self.play_count_dict = {}
        self.play_first_audio = True
        self.audio_pered_played = False

        self.mediaPlayer = QMediaPlayer(self)

        # Очередь для хранения аудиофайлов
        self.audio_queue = queue.Queue()
        self.playing = False
        self.audio_check_timer = QTimer()

        # Запуск потока для воспроизведения аудио из очереди
        self.play_thread = threading.Thread(target=self.play_from_queue)
        self.play_thread.start()

        # Таймер для обновления данных каждый час
    
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_data)
        self.timer.start(3600000)  # 3600000 milliseconds = 1 hour
        # Создаем список для хранения элементов, которые необходимо сохранить
        self.saved_entries = set()

        # Создание виджета вкладок
        self.tab_widget = QTabWidget()

        # Создание вкладок
        tab1 = QWidget()
        tab2 = QWidget()
        tab3 = QWidget()
        # Добавление виджетов во вкладки
        self.tab_widget.addTab(tab1, "Межгородские автобусы")
        self.tab_widget.addTab(tab2, "Настройка времени воспроизведения аудио")
        self.tab_widget.addTab(tab3, "Настройка маршрутов")
        # Создание вертикальных линий разделения
        splitter_tab1 = QSplitter()
        splitter_tab2 = QSplitter()
        splitter_tab3 = QSplitter()

        # Добавление вертикальных линий во вкладки
        layout_tab1 = QVBoxLayout(tab1)
        layout_tab1.addWidget(splitter_tab1)
        tab1.setLayout(layout_tab1)

        layout_tab2 = QVBoxLayout(tab2)
        layout_tab2.addWidget(splitter_tab2)
        tab2.setLayout(layout_tab2)

        layout_tab3 = QVBoxLayout(tab3)
        layout_tab3.addWidget(splitter_tab3)
        tab3.setLayout(layout_tab3)

        # Добавление текстовых полей на третью вкладку
        self.text_field1 = QLineEdit()
        self.text_field2 = QLineEdit()
        self.text_field3 = QLineEdit()
        self.save_button = QPushButton('Сохранить', self)
        self.save_button.clicked.connect(self.save_text)

        days_layout = QHBoxLayout()
        for idx, day in enumerate(['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье']):
            checkbox = QCheckBox(day, self)
            checkbox.stateChanged.connect(self.update_text_field3)
            days_layout.addWidget(checkbox)
            self.days_checkboxes.append(checkbox)


        desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
        prog_path = os.path.join(desktop_path, "Prog")
        json_file_path = os.path.join(prog_path, "reis.json")
        with open(json_file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
    
        # Создание таблицы для третьей вкладки "Настройка маршрутов"
        self.table_routes = QTableWidget()
        self.table_routes.setColumnCount(3)   # Установка двух колонок
            
        self.table_routes.setHorizontalHeaderLabels(["Маршруты", "Время отправления", "Дни недели отправления"])
        self.set_table_properties()
        self.table_routes.setRowCount(len(data))

        
        # Устанавливаем шрифт для заголовков колонок и содержимого ячеек
        font_header = QFont()
        font_header.setPointSize(11)  # Устанавливаем размер шрифта
        font_header.setWeight(60)     # Устанавливаем стиль шрифта (менее жирный)
        self.table_routes.horizontalHeader().setFont(font_header)
        self.table_routes.setFont(font_header)


        # Добавление записей в таблицу
        day_of_week_mapping = {
            0: "Понедельник",
            1: "Вторник",
            2: "Среда",
            3: "Четверг",
            4: "Пятница",
            5: "Суббота",
            6: "Воскресенье"
        }


        # Добавление записей в таблицу
        for row, (route, info) in enumerate(data.items()):
            route_item = QTableWidgetItem(route)
            route_item.setFlags(route_item.flags() ^ Qt.ItemIsEditable)
            self.table_routes.setItem(row, 0, route_item)
            
            # Получаем список времен отправления из ключа "times"
            times = info.get("times", [])

            # Заполняем вторую колонку временами отправления
            time_item = QTableWidgetItem(", ".join(times))
            time_item.setFlags(time_item.flags() ^ Qt.ItemIsEditable)
            self.table_routes.setItem(row, 1, time_item)

            # Получаем список дней недели из ключа "selected_days" и преобразуем их в дни недели
            selected_days = info.get("selected_days", [])
            days_of_week = [day_of_week_mapping[day] for day in selected_days]

            # Заполняем третью колонку днями недели
            days_item = QTableWidgetItem(", ".join(days_of_week))
            days_item.setFlags(days_item.flags() ^ Qt.ItemIsEditable)
            self.table_routes.setItem(row, 2, days_item)

        self.table_routes.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)


        # Добавление на третью вкладку
        layout_tab3.addWidget(self.table_routes)

        # Добавление остальных элементов
        layout_tab3.addWidget(self.text_field1)
        layout_tab3.addWidget(self.text_field2)
        layout_tab3.addWidget(self.text_field3)
        layout_tab3.addLayout(days_layout)
        layout_tab3.addWidget(self.save_button)


    
         # Создание таблицы для левой части вкладки "Межгородские автобусы"
        self.table_right = QTableWidget(self)
        self.table_right.setColumnCount(3)
        self.table_right.setRowCount(6)  # Устанавливаем количество строк
        # Устанавливаем фиксированный размер ячеек
  
         # Получаем абсолютный путь к файлу изображения
        current_dir = os.path.dirname(os.path.realpath(__file__))
        image_path = os.path.join(current_dir, "background.png").replace("\\", "/")

        # Устанавливаем фон только для вкладки tab1
        self.tab_widget.setStyleSheet("#tab1 { background-image: url('" + image_path + "'); background-repeat: no-repeat; background-position: center;}")

        # Устанавливаем идентификатор для вкладки tab1
        tab1.setObjectName("tab1")

       # Устанавливаем заголовки колонок с настройками шрифта и веса
        font_header = QFont()
        font_header.setPointSize(10)  # Замените 13 на желаемый размер шрифта
        font_header.setWeight(60)     # Установка менее жирного шрифта
        self.table_right.setHorizontalHeaderLabels(["", "Через сколько минут воспроизводится аудио", ""])
        self.table_right.horizontalHeader().setFont(font_header)

        font = QFont()
        font.setPointSize(13)  # Замените 13 на желаемый размер шрифта
        font.setWeight(60)     # Установка менее жирного шрифта
        self.table_right.setFont(font)

        splitter_tab2.addWidget(self.table_right)


          # Различные настройки
        self.settings = [
            ("Аудио о посадке по билетам", 126),  # 2.1 часа
            ("Аудио о проезжей части", 96),       # 1.6 часа
            ("Аудио о террористических актах", 210),  # 3.5 часа
            ("Доп аудио 1", 0),
            ("Доп аудио 2", 0),  
            ("Доп аудио 3", 0)  
        ]

    
        # Добавление записей в таблицу table_right
        for row, (setting, value) in enumerate(self.settings):
            setting_item = QTableWidgetItem(setting)
            setting_item.setFlags(setting_item.flags() & ~Qt.ItemIsEditable)  # Только чтение
            value_item = QTableWidgetItem(str(value))  
            value_item.setFlags(value_item.flags() | Qt.ItemIsEditable)  # Разрешение редактирования
            edit_button = QPushButton("Изменить время")
            edit_button.clicked.connect(self.get_edit_function(value_item))
            self.table_right.setItem(row, 0, setting_item)
            self.table_right.setItem(row, 1, value_item)
            self.table_right.setCellWidget(row, 2, edit_button)  # Устанавливаем кнопку в ячейку

        self.table_right.resizeColumnsToContents()
        
                    

    


         # Создание таблицы для левой части вкладки "Межгородские автобусы"
        self.table_left = QTableWidget(self)
        self.table_left.setColumnCount(5)
       # Устанавливаем заголовки колонок с настройками шрифта и веса
        font_header = QFont()
        font_header.setPointSize(10)  # Замените 13 на желаемый размер шрифта
        font_header.setWeight(60)     # Установка менее жирного шрифта
        self.table_left.setHorizontalHeaderLabels(["Номер", "Название", "Время отправления", "Платформа","Время прибытия"])
        self.table_left.horizontalHeader().setFont(font_header)
        self.table_left.resizeColumnsToContents()
        self.table_left.setColumnWidth(1, 310)

        font = QFont()
        font.setPointSize(13)  # Замените 13 на желаемый размер шрифта
        font.setWeight(60)     # Установка менее жирного шрифта
        self.table_left.setFont(font)
       
       
        for row in range(self.table_left.rowCount()):
            for col in range(self.table_left.columnCount()):
                item = self.table_left.item(row, col)
                if item:
                    if col in [2, 3]:  # Выравнивание для "Времени отправления" и "Платформы"
                        item.setTextAlignment(Qt.AlignCenter)
                    else:
                        item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)  # Выравнивание для остальных ячеек
        # Задание жирного шрифта для каждой ячейки таблицы
      
      
        for row in range(self.table_left.rowCount()):
            for col in range(self.table_left.columnCount()):
                item = self.table_left.item(row, col)
                if item is not None:
                    item.setFont(font)

        # Добавление таблицы в левую часть
        splitter_tab1.addWidget(self.table_left)

        # Запрещаем редактирование ячеек
        self.table_left.setEditTriggers(QAbstractItemView.NoEditTriggers)

        # Создание виджета для кнопок "Платформы" с названием
        platforms_widget = QWidget()

        platforms_layout = QVBoxLayout(platforms_widget)

        # Добавление названия
        label_platforms = QLabel("Выбор платформы <br> при изменении расписания")
        
        # Установка размера шрифта
        font_label = QFont()
        font_label.setFamily("Arial")
        font_label.setPointSize(12)  # Замените 16 на желаемый размер шрифта
        label_platforms.setFont(font_label)

                # Устанавливаем разметку HTML для разрешения переноса строки
        label_platforms.setWordWrap(True)

        label_platforms.setAlignment(Qt.AlignHCenter)
        platforms_layout.addWidget(label_platforms, alignment=Qt.AlignHCenter)

        # Создание кнопок и добавление их в виджет
        grid_layout = QGridLayout()
        for row in range(10):
            for col in range(2):
                platform_button = QPushButton(str(row * 2 + col + 1))
                platform_button.clicked.connect(self.handle_platform_button_click)

                # Устанавливаем стили для уменьшения размера кнопок и уменьшения расстояния сверху
                platform_button.setStyleSheet("QPushButton {"
                                    "    background-color: #e3e6e5;"
                                    "    border: 2px solid #8f8f91;"
                                    "    border-radius: 8px;"
                                    "    font-size: 14px;"
                                    "    padding: 2px;"
                                    "}"
                                    "QPushButton:hover {"
                                    "    background-color: #f0f0f0;  /* Изменение цвета фона при наведении */"
                                    "}"
                                    "QPushButton:pressed {"
                                    "    background-color: #dcdcdc;  /* Изменение цвета фона при нажатии */"
                                    "}")

                grid_layout.addWidget(platform_button, row, col*2)

        # Добавление кнопок в layout после названия
        platforms_layout.addLayout(grid_layout)

        # Подгонка размеров виджета под размер его содержимого
        platforms_widget.setFixedSize(250, 350)

        splitter_tab1.addWidget(platforms_widget)

        # Создание правой части с текущей датой и временем
        right_panel = QWidget()
        layout_right_panel = QVBoxLayout(right_panel)

        self.label_datetime = QLabel()
        layout_right_panel.addWidget(self.label_datetime)

        self.message_list = QListWidget(self)
        self.message_list.setStyleSheet("font-size: 16px;")  # Замените 14px на желаемый размер
        layout_right_panel.addWidget(self.message_list)



        status_buttons = QButtonGroup(self)
        status_buttons.setExclusive(True)



        self.last_button_label = None
        # Добавьте другие инициализации, если необходимо

        status_labels = ["Прибытие на посадку", "Продолжается посадка","Завершается посадка", "Задерживается", "Отменен"]

        self.status_buttons = QButtonGroup()  # Предполагается, что это ваш объект для управления кнопками

        for status_label in status_labels:
            status_button = QPushButton(status_label)
            self.status_buttons.addButton(status_button)

            # Обновленный обработчик нажатия кнопки
            status_button.clicked.connect(partial(self.handle_button_click, label=status_label))

             # Установка стиля шрифта для кнопок
            font = QFont()
            font.setPointSize(13)  # Замените 16 на желаемый размер шрифта
            status_button.setFont(font)
            layout_right_panel.addWidget(status_button)

        splitter_tab1.addWidget(right_panel)

        # CSS-стиль для закругленных кнопок
        rounded_button_style = """
        QPushButton {
            font-size: 16px;
            border: 2px solid #8f8f91;  /* Установка цвета границы */
            border-radius: 10px;  /* Закругление углов */
            padding: 8px;  /* Отступы внутри кнопки */
            min-width: 100px;  /* Минимальная ширина кнопки */
            background-color: #e3e6e5;
        }

        QPushButton:hover {
            background-color: #f0f0f0;  /* Изменение цвета фона при наведении */
        }

        QPushButton:pressed {
            background-color: #dcdcdc;  /* Изменение цвета фона при нажатии */
        }
        """

        # Применение CSS-стиля ко всем кнопкам в self.status_buttons
        for status_button in self.status_buttons.buttons():
            status_button.setStyleSheet(rounded_button_style)


       
        # Размещаем виджет вкладок на вертикальной панели
        layout = QVBoxLayout(self)
        layout.addWidget(self.tab_widget)



        # Устанавливаем размеры окна и заголовок
        self.setGeometry(100, 100, 1600, 600)
        self.setWindowTitle('Avtovokzal')

        self.table_left.setFixedSize(700, 800)  # Замените размеры на желаемые


        

        # Создаем QLabel для отображения времени
        self.time_label = QLabel(self)
        self.time_label.setAlignment(Qt.AlignCenter)
        self.time_label.setStyleSheet("font-size: 16px;")  # Уменьшаем шрифт
        layout.addWidget(self.time_label)  # Добавляем метку в вертикальный контейнер

        self.date_label = QLabel(self)
        self.date_label.setAlignment(Qt.AlignCenter)
        self.date_label.setStyleSheet("font-size: 12px; color: gray;")
        layout.addWidget(self.date_label)

        # Создаем таймер для обновления времени каждую секунду
        timer = QTimer(self)
        timer.timeout.connect(self.update_time)
        timer.start(1000)



        # Get data and populate the tables
        self.update_data()
        

        # Создаем таймер для проверки окончания воспроизведения аудио
        self.audio_check_timer = QTimer(self)
        self.audio_check_timer.timeout.connect(self.check_audio_finished)

        # Подключение сигнала itemDoubleClicked к функции обработки двойного клика на ячейке
        self.table_left.itemDoubleClicked.connect(self.handle_table_item_double_click)

        # Включение возможности выделения целых строк
        self.table_left.setSelectionBehavior(QAbstractItemView.SelectRows)

        # Подключение сигнала keyPressEvent к функции обработки нажатия клавиши
        self.table_left.keyPressEvent = self.handle_key_press_event

         # Подключение обработчика двойного клика на виджете message_list
        self.message_list.itemDoubleClicked.connect(self.handle_message_double_click)
    
        self.audio_stop_timer = QTimer(self)
        self.audio_stop_timer.timeout.connect(self.stop_audio)



        # Таймер для добавления аудио о посадке по билетам через 2.1 часа
        self.boarding_audio_to_queue = QTimer(self)
        self.boarding_audio_to_queue.timeout.connect(self.add_boarding_audio_to_queue)
        self.boarding_audio_to_queue.start(int(2.1*60* 60 * 1000)) # 2* 60 минут * 60 секунд * 1000 миллисекунд = 2 час

        # Таймер для добавления аудио о проезжей части через 1.5 часа
        self.traffic_audio_to_queue_timer = QTimer(self)
        self.traffic_audio_to_queue_timer.timeout.connect(self.add_traffic_audio_to_queue)
        self.traffic_audio_to_queue_timer.start(int(1.6 * 60 * 60 * 1000))  # 1.6 часа * 60 минут * 60 секунд * 1000 миллисекунд
        # Таймер для добавления аудио о террористических актах через 3.5 часа   
        self.terror_acts_audio_to_queue_timer = QTimer(self)
        self.terror_acts_audio_to_queue_timer.timeout.connect(self.add_terror_acts_audio_to_queue)
        self.terror_acts_audio_to_queue_timer.start(int(3.5 * 60 * 60 * 1000))  # 3.5 часа * 60 минут * 60 секунд * 1000 миллисекунд

        self.dop_audio_1_to_queue_timer = QTimer(self)
        self.dop_audio_1_to_queue_timer.timeout.connect(self.add_dop_audio_1_queue)
        self.dop_audio_1_to_queue_timer.setSingleShot(False) 

        if value != 0:
            self.dop_audio_1_to_queue_timer.start(int(value * 60 * 1000))
        else:
            print("Таймер для дополнительного аудио 1 не будет запущен, так как значение равно 0")

        self.dop_audio_2_to_queue_timer = QTimer(self)
        self.dop_audio_2_to_queue_timer.timeout.connect(self.add_dop_audio_2_queue)
        self.dop_audio_2_to_queue_timer.setSingleShot(False) 

        if value != 0:
            self.dop_audio_2_to_queue_timer.start(int(value * 60 * 1000))
        else:
            print("Таймер для дополнительного аудио 2 не будет запущен, так как значение равно 0")

        self.dop_audio_3_to_queue_timer = QTimer(self)
        self.dop_audio_3_to_queue_timer.timeout.connect(self.add_dop_audio_3_queue)
        self.dop_audio_3_to_queue_timer.setSingleShot(False) 

        if value != 0:
            self.dop_audio_3_to_queue_timer.start(int(value * 60 * 1000))
        else:
            print("Таймер для дополнительного аудио 3 не будет запущен, так как значение равно 0")

        self.create_web_view()

    def create_web_view(self):
        # Create a QWebEngineView widget
        self.web_view = QWebEngineView(self)
        self.web_view.setGeometry(0, 0, 1600, 910)  # Set geometry as needed

        # Load HTML content into the web view
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                .loader {
}

.container {
  width: 300px;
  height: 280px;
  position: absolute;
  top: calc(50% - 140px);
  left: calc(50% - 150px);
}

.coffee-header {
  width: 100%;
  height: 80px;
  position: absolute;
  top: 0;
  left: 0;
  background-color: #ddcfcc;
  border-radius: 10px;
}

.coffee-header__buttons {
  width: 25px;
  height: 25px;
  position: absolute;
  top: 25px;
  background-color: #282323;
  border-radius: 50%;
}

.coffee-header__buttons::after {
  content: "";
  width: 8px;
  height: 8px;
  position: absolute;
  bottom: -8px;
  left: calc(50% - 4px);
  background-color: #615e5e;
}

.coffee-header__button-one {
  left: 15px;
}

.coffee-header__button-two {
  left: 50px;
}

.coffee-header__display {
  width: 50px;
  height: 50px;
  position: absolute;
  top: calc(50% - 25px);
  left: calc(50% - 25px);
  border-radius: 50%;
  background-color: #9acfc5;
  border: 5px solid #43beae;
  box-sizing: border-box;
}

.coffee-header__details {
  width: 8px;
  height: 20px;
  position: absolute;
  top: 10px;
  right: 10px;
  background-color: #9b9091;
  box-shadow: -12px 0 0 #9b9091, -24px 0 0 #9b9091;
}

.coffee-medium {
  width: 90%;
  height: 160px;
  position: absolute;
  top: 80px;
  left: calc(50% - 45%);
  background-color: #bcb0af;
}

.coffee-medium:before {
  content: "";
  width: 90%;
  height: 100px;
  background-color: #776f6e;
  position: absolute;
  bottom: 0;
  left: calc(50% - 45%);
  border-radius: 20px 20px 0 0;
}

.coffe-medium__exit {
  width: 60px;
  height: 20px;
  position: absolute;
  top: 0;
  left: calc(50% - 30px);
  background-color: #231f20;
}

.coffe-medium__exit::before {
  content: "";
  width: 50px;
  height: 20px;
  border-radius: 0 0 50% 50%;
  position: absolute;
  bottom: -20px;
  left: calc(50% - 25px);
  background-color: #231f20;
}

.coffe-medium__exit::after {
  content: "";
  width: 10px;
  height: 10px;
  position: absolute;
  bottom: -30px;
  left: calc(50% - 5px);
  background-color: #231f20;
}

.coffee-medium__arm {
  width: 70px;
  height: 20px;
  position: absolute;
  top: 15px;
  right: 25px;
  background-color: #231f20;
}

.coffee-medium__arm::before {
  content: "";
  width: 15px;
  height: 5px;
  position: absolute;
  top: 7px;
  left: -15px;
  background-color: #9e9495;
}

.coffee-medium__cup {
  width: 80px;
  height: 47px;
  position: absolute;
  bottom: 0;
  left: calc(50% - 40px);
  background-color: #FFF;
  border-radius: 0 0 70px 70px / 0 0 110px 110px;
}

.coffee-medium__cup::after {
  content: "";
  width: 20px;
  height: 20px;
  position: absolute;
  top: 6px;
  right: -13px;
  border: 5px solid #FFF;
  border-radius: 50%;
}

@keyframes liquid {
  0% {
    height: 0px;
    opacity: 1;
  }

  5% {
    height: 0px;
    opacity: 1;
  }

  20% {
    height: 62px;
    opacity: 1;
  }

  95% {
    height: 62px;
    opacity: 1;
  }

  100% {
    height: 62px;
    opacity: 0;
  }
}

.coffee-medium__liquid {
  width: 6px;
  height: 63px;
  opacity: 0;
  position: absolute;
  top: 50px;
  left: calc(50% - 3px);
  background-color: #74372b;
  animation: liquid 4s 4s linear infinite;
}

.coffee-medium__smoke {
  width: 8px;
  height: 20px;
  position: absolute;
  border-radius: 5px;
  background-color: #b3aeae;
}

@keyframes smokeOne {
  0% {
    bottom: 20px;
    opacity: 0;
  }

  40% {
    bottom: 50px;
    opacity: .5;
  }

  80% {
    bottom: 80px;
    opacity: .3;
  }

  100% {
    bottom: 80px;
    opacity: 0;
  }
}

@keyframes smokeTwo {
  0% {
    bottom: 40px;
    opacity: 0;
  }

  40% {
    bottom: 70px;
    opacity: .5;
  }

  80% {
    bottom: 80px;
    opacity: .3;
  }

  100% {
    bottom: 80px;
    opacity: 0;
  }
}

.coffee-medium__smoke-one {
  opacity: 0;
  bottom: 50px;
  left: 102px;
  animation: smokeOne 3s 4s linear infinite;
}

.coffee-medium__smoke-two {
  opacity: 0;
  bottom: 70px;
  left: 118px;
  animation: smokeTwo 3s 5s linear infinite;
}

.coffee-medium__smoke-three {
  opacity: 0;
  bottom: 65px;
  right: 118px;
  animation: smokeTwo 3s 6s linear infinite;
}

.coffee-medium__smoke-for {
  opacity: 0;
  bottom: 50px;
  right: 102px;
  animation: smokeOne 3s 5s linear infinite;
}

.coffee-footer {
  width: 95%;
  height: 15px;
  position: absolute;
  bottom: 25px;
  left: calc(50% - 47.5%);
  background-color: #41bdad;
  border-radius: 10px;
}

.coffee-footer::after {
  content: "";
  width: 106%;
  height: 26px;
  position: absolute;
  bottom: -25px;
  left: -8px;
  background-color: #000;
}
.loading-message {
   position: fixed;
   top: 70%;
   left: 50%;
   transform: translate(-50%, -50%);
   font-size: 30px;
   color: #333; /* Цвет текста */
   background-color: #fff; /* Цвет фона */
   padding: 10px 20px;
   border-radius: 5px;
   z-index: 9999; /* Чтобы убедиться, что текст отображается поверх всего */
}
 
}
            </style>
        </head>
        <body>
            

   <div class="loader">
      <div class="container">
      <div class="coffee-header">
        <div class="coffee-header__buttons coffee-header__button-one"></div>
        <div class="coffee-header__buttons coffee-header__button-two"></div>
        <div class="coffee-header__display"></div>
        <div class="coffee-header__details"></div>
      </div>
      <div class="coffee-medium">
        <div class="coffe-medium__exit"></div>
        <div class="coffee-medium__arm"></div>
        <div class="coffee-medium__liquid"></div>
        <div class="coffee-medium__smoke coffee-medium__smoke-one"></div>
        <div class="coffee-medium__smoke coffee-medium__smoke-two"></div>
        <div class="coffee-medium__smoke coffee-medium__smoke-three"></div>
        <div class="coffee-medium__smoke coffee-medium__smoke-for"></div>
        <div class="coffee-medium__cup"></div>
      </div>
      <div class="coffee-footer"></div>
      <div class="loading-message">Загрузка данных, подождите</div>
    </div>
   </div>


        </body>
        </html>
        """
        self.web_view.setHtml(html_content)



    def add_boarding_audio_to_queue(self):
        base_path = os.path.dirname(os.path.abspath(__file__))
        sounds_folder = "Sound\drygoe"
        boarding_audio_filename = "Посадка-по-билетам.mp3"
        boarding_audio_path = os.path.join(base_path, sounds_folder, boarding_audio_filename)

        is_audio_playing = self.is_audio_playing()

        boarding_index = 52 if is_audio_playing or self.message_list.count() != 0 else 0
        self.audio_queue.put((boarding_index, boarding_audio_path))
        boarding_message = "Воспроизводится аудио о посадке по билетам"
        self.add_message(boarding_message, label=None)

        if not is_audio_playing or self.message_list.count() != 0:
            self.play_from_queue()

        self.index_history[boarding_index] = boarding_audio_path
        print(self.index_history)

   

    def add_traffic_audio_to_queue(self):
        base_path = os.path.dirname(os.path.abspath(__file__))
        sounds_folder = "Sound\drygoe"
        traffic_audio_filename = "Проезжая-часть.mp3"
        traffic_audio_path = os.path.join(base_path, sounds_folder, traffic_audio_filename)

        is_audio_playing = self.is_audio_playing()

        traffic_index = 54 if is_audio_playing or self.message_list.count() != 0 else 0
        self.audio_queue.put((traffic_index, traffic_audio_path))
        traffic_message = "Воспроизводится аудио о проезжей части"
        self.add_message(traffic_message, label=None)

        if not is_audio_playing or self.message_list.count() != 0:
            self.play_from_queue()

        self.index_history[traffic_index] = traffic_audio_path
        print(self.index_history)

    def add_terror_acts_audio_to_queue(self):
        base_path = os.path.dirname(os.path.abspath(__file__))
        sounds_folder = "Sound/drygoe"
        terror_acts_audio_filename = "Террор акты.mp3"
        terror_acts_audio_path = os.path.join(base_path, sounds_folder, terror_acts_audio_filename)

        is_audio_playing = self.is_audio_playing()
        terror_acts_index = 55

        if (is_audio_playing and not self.audio_queue.empty()) or self.message_list.count() != 0:
            self.audio_queue.put((terror_acts_index, terror_acts_audio_path))
            terror_acts_message = "Воспроизводится аудио о террористических актах"
            self.add_message(terror_acts_message, label=None)
            self.play_from_queue()
        else:
            terror_acts_message = 0
            self.audio_queue.put((terror_acts_index, terror_acts_audio_path))
            self.add_message(terror_acts_message, label=None)
            self.play_from_queue()

        self.index_history[terror_acts_message] = terror_acts_audio_path
        print(self.index_history)


    def add_dop_audio_1_queue(self):
        print("Функция add_dop_audio_1_queue вызвана")
        
        # Абсолютный путь к каталогу с звуковыми файлами
        base_path = "C:/Users/{}/Desktop/Prog/Sound/drygoe".format(username)
        dop_audio_filename = "dop1.mp3"  # Имя файла аудио о курении
        dop_audio_path = os.path.join(base_path, dop_audio_filename)
        
        # Проверяем, воспроизводится ли аудио
        is_audio_playing = self.is_audio_playing()
        dop_audio_index = 70
        
        if is_audio_playing and not self.audio_queue.empty():
            # Если аудио воспроизводится и виджет не пуст, добавляем сообщение в конец
            self.audio_queue.put((dop_audio_index, dop_audio_path))
            dop_audio_message = "Воспроизводится доп аудио 1"
            self.add_message(dop_audio_message, label=None)

        elif self.message_list.count() != 0:
            # Если аудио не воспроизводится и виджет пуст, добавляем сообщение в начало
            self.audio_queue.put((dop_audio_index, dop_audio_path))
            dop_audio_message = "Воспроизводится доп аудио 1"
            self.add_message(dop_audio_message, label=None)
            self.play_from_queue()

        else:
            # Если аудио не воспроизводится или виджет пуст, добавляем сообщение в начало
            self.audio_queue.put((dop_audio_index, dop_audio_path))
            dop_audio_message = "Воспроизводится доп аудио 1"
            self.add_message(dop_audio_message, label=None)
            self.play_from_queue()

        self.index_history[dop_audio_index] = dop_audio_path
        print(self.index_history)


    def add_dop_audio_2_queue(self):
        print("Функция add_dop_audio_1_queue вызвана")
        # Добавляем аудио о курении в очередь
        base_path = "C:/Users/{}/Desktop/Prog/Sound/drygoe".format(username) 
        dop_audio_filename = "dop2.mp3"  # Имя файла аудио о курении
        dop_audio_path = os.path.join(base_path, dop_audio_filename)

        # Проверяем, воспроизводится ли аудио
        is_audio_playing = self.is_audio_playing()
        dop_audio_index = 71

        if is_audio_playing and not self.audio_queue.empty():
            # Если аудио воспроизводится и виджет не пуст, добавляем сообщение в конец
            self.audio_queue.put((dop_audio_index, dop_audio_path))
            dop_audio_message = "Воспроизводится доп аудио 2"
            self.add_message(dop_audio_message, label=None)
        elif self.message_list.count() != 0:
            # Если аудио не воспроизводится и виджет пуст, добавляем сообщение в начало
            self.audio_queue.put((dop_audio_index, dop_audio_path))
            dop_audio_message = "Воспроизводится доп аудио 2"
            self.add_message(dop_audio_message, label=None)
            self.play_from_queue()
        else:
            # Если аудио не воспроизводится или виджет пуст, добавляем сообщение в начало
            dop_audio_index = 0 
            self.audio_queue.put((dop_audio_index, dop_audio_path))
            dop_audio_message = "Воспроизводится доп аудио 2"
            self.add_message(dop_audio_message, label=None)
            self.play_from_queue()

        self.index_history[dop_audio_index] = dop_audio_path
        print(self.index_history)

    def add_dop_audio_3_queue(self):
        print("Функция add_dop_audio_3_queue вызвана")
        # Добавляем аудио о курении в очередь
        base_path = "C:/Users/{}/Desktop/Prog/Sound/drygoe".format(username) 
        dop_audio_filename = "dop3.mp3"  # Имя файла аудио о курении
        dop_audio_path = os.path.join(base_path, dop_audio_filename)

        
        # Проверяем, воспроизводится ли аудио
        is_audio_playing = self.is_audio_playing()

        if is_audio_playing and not self.audio_queue.empty():
            dop_audio_index = 72  # Вы можете выбрать уникальный индекс для аудио о курении
            # Если аудио воспроизводится и виджет не пуст, добавляем сообщение в конец
            self.audio_queue.put((dop_audio_index, dop_audio_path))
            dop_audio_message = "Воспроизводится доп аудио 3"
            self.add_message(dop_audio_message, label=None)

        elif self.message_list.count() != 0:
            dop_audio_index = 72
            # Если аудио не воспроизводится и виджет пуст, добавляем сообщение в начало
            self.audio_queue.put((dop_audio_index, dop_audio_path))
            dop_audio_message = "Воспроизводится доп аудио 3"
            self.add_message(dop_audio_message, label=None)
            self.play_from_queue()

        else:
            # Если аудио не воспроизводится или виджет пуст, добавляем сообщение в начало
            dop_audio_index = 0 
            self.audio_queue.put((dop_audio_index, dop_audio_path))
            dop_audio_message = "Воспроизводится доп аудио 3"
            self.add_message(dop_audio_message, label=None)
            self.play_from_queue()

        self.index_history[dop_audio_index] = dop_audio_path
        print(self.index_history)


    def get_edit_function(self, value_item):
        def wrapper():
            setting = value_item.tableWidget().item(value_item.row(), 0).text()
            value = int(value_item.text())
            if setting == "Аудио о посадке по билетам":
                self.save_boarding_audio_settings(value)
            elif setting == "Аудио о проезжей части":
                self.save_traffic_audio_settings(value)
            elif setting == "Аудио о террористических актах":
                self.save_terror_acts_audio_settings(value)
            elif setting == "Доп аудио 1":
                self.save_dop_audio_1(value)
            elif setting == "Доп аудио 2":
                self.save_dop_audio_2(value)
            elif setting == "Доп аудио 3":
                self.save_dop_audio_3(value)
            else:
                print("Функция сохранения для данной настройки не определена.")
        return wrapper




    def save_boarding_audio_settings(self, value):
        if value == 0:
            self.boarding_audio_to_queue.stop()
            print("Воспроизведение аудио о посадке по билетам прекращено.")  
        else:
            self.boarding_audio_to_queue.stop()
            self.boarding_audio_to_queue.start(value * 60 * 1000)
            print(f"Настройки аудио о посадке по билетам сохранены и применены к таймеру, воспроизведение через {value} мин.")


    def save_traffic_audio_settings(self, value):
        if value == 0:
            self.traffic_audio_to_queue_timer.stop()
            print("Воспроизведение аудио о проезжей части прекращено.")  
        else:
            self.traffic_audio_to_queue_timer.stop()
            self.traffic_audio_to_queue_timer.start(value * 60 * 1000)
            print(f"Настройки аудио о проезжей части сохранены и применены к таймеру, воспроизведение через {value} мин.")

    def save_terror_acts_audio_settings(self, value):
        if value == 0:
            self.terror_acts_audio_to_queue_timer.stop()
            print("Воспроизведение аудио о террористических актах прекращено.")  
        else:
            self.terror_acts_audio_to_queue_timer.stop()
            self.terror_acts_audio_to_queue_timer.start(value * 60 * 1000)
            print(f"Настройки аудио о террористических актах сохранены и применены к таймеру, воспроизведение через {value} мин.")

    def save_dop_audio_1(self, value):
        if value == 0:
            self.dop_audio_1_to_queue_timer.stop()
            print("Воспроизведение доп аудио 1 прекращено.")  
        else:
            self.dop_audio_1_to_queue_timer.stop()
            self.dop_audio_1_to_queue_timer.start(value * 60 * 1000)
            print(f"Настройки доп аудио 1 применены к таймеру, воспроизведение через {value} мин.")

    def save_dop_audio_2(self, value):
        if value == 0:
            self.dop_audio_2_to_queue_timer.stop()
            print("Воспроизведение доп аудио 2 прекращено.")  
        else:
            self.dop_audio_2_to_queue_timer.stop()
            self.dop_audio_2_to_queue_timer.start(value * 60 * 1000)
            print(f"Настройки доп аудио 2 применены к таймеру, воспроизведение через {value} мин.")

    def save_dop_audio_3(self, value):
        if value == 0:
            self.dop_audio_3_to_queue_timer.stop()
            print("Воспроизведение доп аудио 3 прекращено.")  
        else:
            self.dop_audio_3_to_queue_timer.stop()
            self.dop_audio_3_to_queue_timer.start(value * 60 * 1000)
            print(f"Настройки доп аудио 3 применены к таймеру, воспроизведение через {value} мин.")




            

    def is_audio_playing(self):
        # Инициализация Pygame, если она еще не была произведена
        if not pygame.mixer.get_init():
            pygame.mixer.init()

        # Проверка статуса звукового потока
        return pygame.mixer.music.get_busy()




    def handle_button_click(self, label):
            self.last_button_label = label
            self.show_confirmation(label) 
            


    def show_confirmation(self, label):
        items_to_remove = []  # Создаем список элементов для удаления
        # Словарь для сопоставления меток с функциями
        confirmation_tabs = {
            "Прибытие на посадку": self.show_confirmation_tab1,
            "Продолжается посадка": self.show_confirmation_tab5,
            "Завершается посадка": self.show_confirmation_tab2,
            "Отменен": self.show_confirmation_tab3,
            "Задерживается": self.show_confirmation_tab4
        }

        for index in range(self.message_list.count()):
            current_item = self.message_list.item(index)
            if current_item is not None:
                existing_label = current_item.data(Qt.UserRole)
                try:
                    if existing_label is None and label is not None:
                        # Фильтрация сообщений
                        if any(substring in current_item.text() for substring in ["Воспроизводится аудио о посадке по билетам", "Воспроизводится аудио о проезжей части", "Воспроизводится аудио о террористических актах", "Воспроизводится доп аудио 1", "Воспроизводится доп аудио 2", "Воспроизводится доп аудио 3"]):
                            continue 

                        current_item.setData(Qt.UserRole, label)
                        # Использование словаря для вызова соответствующей функции
                        confirmation_function = confirmation_tabs.get(label)
                        if confirmation_function:
                            confirmation_function(current_item)

                        status_text = f"{current_item.text()} ⸺ {label}"
                        current_item.setText(status_text)
                except Exception as e:
                    print(f"Error processing confirmation: {e}")

            # Удаляем элементы, которые не соответствуют условиям
            for item in items_to_remove:
                self.message_list.takeItem(self.message_list.row(item))




    def set_row_background_color(self, row, color):
        # Установка цвета фона для всех ячеек в указанной строке
        for column in range(self.table_left.columnCount()):
            item = self.table_left.item(row, column)
            if item:
                item.setBackground(color)

    def handle_audio_finished(self):
        self.playing = False
        pygame.time.delay(2000)

        # Проверяем, есть ли сообщения в списке
        if self.message_list.count() > 0:
            # Удаляем первый элемент списка сообщений
            del_item = self.message_list.takeItem(0)
            del del_item

            # Проверяем, остались ли еще сообщения в списке
            if self.message_list.count() > 0:
                # Если есть, проигрываем аудио для следующего сообщения
                next_item = self.message_list.item(0)
                self.play_audio_from_message(next_item.text())
            else:
                # Если нет, останавливаем таймер проверки аудио
                self.audio_check_timer.stop()




    def handle_table_item_double_click(self, item):
        # Обработка двойного клика на элементе таблицы
        if isinstance(item, QTableWidgetItem):
            # Получаем индекс строки выбранного элемента
            row = item.row()

            # Получаем текст из всех ячеек в строке
            row_data = [self.table_left.item(row, c).text() for c in range(self.table_left.columnCount())]

            # Преобразуем список текстов в одну строку
            selected_text = ' | '.join(row_data)

            # Добавляем выбранный текст в виджет
            self.message_list.addItem(selected_text)

            label = item.data(Qt.UserRole)
            print("Received label:", label)

    def handle_message_double_click(self, item):
        # Обработка двойного клика на элементе в message_list
        if isinstance(item, QListWidgetItem):
            # Получаем текст элемента, который будет удален
            deleted_text = item.text()

            # Получаем индекс выбранного элемента
            row = self.message_list.row(item)

            # Сохраняем сообщение перед удалением
            split_text = deleted_text.split(" | ")

            # Проверяем, содержит ли split_text достаточное количество элементов
            if len(split_text) < 4:
                # Если элементов недостаточно, выводим сообщение об ошибке
                QMessageBox.warning(self, " ", "Эту аудиозапись нельзя удалить.")
                return

            # Формируем сообщение для удаления
            deleted_message = " | ".join([split_text[0], split_text[2], split_text[3]])



            # Удаляем только элемент из списка сообщений
            self.message_list.takeItem(row)

            # Проверяем, остались ли еще записи в списке сообщений
            if self.message_list.count() == 0:
                self.playing = False

            # Устанавливаем белый цвет для удаленной записи в таблице
            for i in range(self.table_left.rowCount()):
                # Получаем атрибуты ячейки таблицы
                flight_number = self.table_left.item(i, 0).text()
                departure_time = self.table_left.item(i, 2).text()

                # Сравниваем атрибуты с удаленной записью
                if flight_number == split_text[0] and departure_time == split_text[2]:
                    # Устанавливаем белый цвет для соответствующей строки
                    for j in range(self.table_left.columnCount()):
                        self.table_left.item(i, j).setBackground(QColor(255, 255, 255))

            # Выводим сообщение и его индекс, которые были удалены
            print("Удаленное сообщение:", deleted_message)

            # Выводим все сообщения в index_history для отладки
            print("Сообщения в index_history:")
            for index, route_info in self.index_history.items():
                print(f"Индекс: {index}, Значения о рейсе: {route_info}")

            # Сравниваем удаленное сообщение с записями в index_history
            found_match = False
            for index, route_info in self.index_history.items():
                # Получаем сообщение из записи в index_history
                saved_message = f"{route_info[0]} | {route_info[1]} | {route_info[2]}"  # Форматируем сообщение для сравнения

                # Сравниваем форматированное сохраненное сообщение с удаленным сообщением
                if saved_message == deleted_message:
                    print("Найдено совпадение. Индекс:", index)
                    found_match = True

                    # Удаление аудио из очереди по найденному индексу
                    temp_queue = queue.Queue()  # Создаем временную очередь для хранения элементов, которые нужно сохранить
                    while not self.audio_queue.empty():
                        item_index, _ = self.audio_queue.get()  # Получаем индекс из элемента в очереди
                        if item_index != index:  # Проверяем индекс на соответствие
                            temp_queue.put((item_index, _))  # Если индекс не совпадает, добавляем элемент обратно во временную очередь
                    self.audio_queue = temp_queue  # Заменяем исходную очередь временной очередью

                    # Удаление элемента из index_history
                    if index in self.index_history:
                        del self.index_history[index]

                    break

            if not found_match:
                print("Не найдено совпадение")



    def handle_key_press_event(self, event):
        # Обработка нажатия клавиши

        if event.key() == Qt.Key_1:
            label = "Прибытие на посадку"
            self.last_button_label = label
            self.handle_button_click(label)

        if event.key() == Qt.Key_3:
            label = "Завершается посадка"
            self.last_button_label = label
            self.handle_button_click(label)

        if event.key() == Qt.Key_5:
            label = "Отменен"
            self.last_button_label = label
            self.handle_button_click(label)

        if event.key() == Qt.Key_4:
            label = "Задерживается"
            self.last_button_label = label
            self.handle_button_click(label)

        if event.key() == Qt.Key_2:
            label = "Продолжается посадка"
            self.last_button_label = label
            self.handle_button_click(label)

        if event.modifiers() == Qt.ControlModifier and event.key() == Qt.Key_G:
            print("Ctrl + G pressed")

            # Получение количества элементов в списке
            num_items = self.message_list.count()

            # Обновление виджета сообщений для указания, что воспроизводится pesnya1
            if num_items > 0:
                # Если уже есть элементы, добавляем новое сообщение в конец
                self.message_list.addItem("Сейчас воспроизводится - pesnya1")

                # Проверяем, инициализирован ли audio_queue, если нет, то инициализируем его
                if not hasattr(self, 'audio_queue'):
                    self.audio_queue = Queue()

                # Строим путь к аудиофайлу (измените эту часть в соответствии со структурой вашего проекта)
                base_path = "C:/Users/{}/Desktop/Prog".format(username) 
                sounds_folder = "Sound/drygoe"
                audio_path = os.path.join(base_path, sounds_folder, "pesnya1.mp3")

                # Добавляем правильную информацию об аудио в очередь
                self.audio_queue.put((59, audio_path))
            else:
                self.message_list.addItem("Сейчас воспроизводится - pesnya1")

                # Строим путь к аудиофайлу (измените эту часть в соответствии со структурой вашего проекта)
                base_path = "C:/Users/{}/Desktop/Prog".format(username) 
                sounds_folder = "Sound/drygoe"
                audio_path = os.path.join(base_path, sounds_folder, "pesnya1.mp3")

                # Воспроизведение аудио
                self.play_audio((0, audio_path), None)  # Передавайте метку как None или обновляйте по мере необходимости
                self.playing = True



        if event.modifiers() == Qt.ControlModifier and event.key() == Qt.Key_H:
            print("Ctrl + H pressed")

            # Получение количества элементов в списке
            num_items = self.message_list.count()

            # Обновление виджета сообщений для указания, что воспроизводится pesnya2
            if num_items > 0:
                # Если уже есть элементы, добавляем новое сообщение в конец
                self.message_list.addItem("Сейчас воспроизводится - pesnya2")

                # Проверяем, инициализирован ли audio_queue, если нет, то инициализируем его
                if not hasattr(self, 'audio_queue'):
                    self.audio_queue = Queue()

                # Строим путь к аудиофайлу (измените эту часть в соответствии со структурой вашего проекта)
                base_path = "C:/Users/{}/Desktop/Prog".format(username) 
                sounds_folder = "Sound/drygoe"
                audio_path = os.path.join(base_path, sounds_folder, "pesnya2.mp3")

                # Добавляем правильную информацию об аудио в очередь
                self.audio_queue.put((58, audio_path))
            else:
                self.message_list.addItem("Сейчас воспроизводится - pesnya2")

                # Строим путь к аудиофайлу (измените эту часть в соответствии со структурой вашего проекта)
                base_path = "C:/Users/{}/Desktop/Prog".format(username) 
                sounds_folder = "Sound/drygoe"
                audio_path = os.path.join(base_path, sounds_folder, "pesnya2.mp3")

                # Воспроизведение аудио
                self.play_audio((0, audio_path), None)  # Передавайте метку как None или обновляйте по мере необходимости
                self.playing = True

                
        if event.modifiers() == Qt.ControlModifier and event.key() == Qt.Key_J:
            print("Ctrl + J pressed")

            # Получение количества элементов в списке
            num_items = self.message_list.count()

            # Обновление виджета сообщений для указания, что воспроизводится pesnya3
            if num_items > 0:
                # Если уже есть элементы, добавляем новое сообщение в конец
                self.message_list.addItem("Сейчас воспроизводится - pesnya3")

                # Проверяем, инициализирован ли audio_queue, если нет, то инициализируем его
                if not hasattr(self, 'audio_queue'):
                    self.audio_queue = Queue()

                # Строим путь к аудиофайлу (измените эту часть в соответствии со структурой вашего проекта)
                base_path = "C:/Users/{}/Desktop/Prog".format(username) 
                sounds_folder = "Sound/drygoe"
                audio_path = os.path.join(base_path, sounds_folder, "pesnya3.mp3")

                # Добавляем правильную информацию об аудио в очередь
                self.audio_queue.put((57, audio_path))
            else:
                self.message_list.addItem("Сейчас воспроизводится - pesnya3")

                # Строим путь к аудиофайлу (измените эту часть в соответствии со структурой вашего проекта)
                base_path = "C:/Users/{}/Desktop/Prog".format(username) 
                sounds_folder = "Sound/drygoe"
                audio_path = os.path.join(base_path, sounds_folder, "pesnya3.mp3")

                # Воспроизведение аудио
                self.play_audio((0, audio_path), None)  # Передавайте метку как None или обновляйте по мере необходимости
                self.playing = True


        if event.modifiers() == Qt.ControlModifier and event.key() == Qt.Key_K:
            print("Ctrl + K pressed")

            # Получение количества элементов в списке
            num_items = self.message_list.count()

            # Обновление виджета сообщений для указания, что воспроизводится pesnya4
            if num_items > 0:
                # Если уже есть элементы, добавляем новое сообщение в конец
                self.message_list.addItem("Сейчас воспроизводится - pesnya4")

                # Проверяем, инициализирован ли audio_queue, если нет, то инициализируем его
                if not hasattr(self, 'audio_queue'):
                    self.audio_queue = Queue()

                # Строим путь к аудиофайлу (измените эту часть в соответствии со структурой вашего проекта)
                base_path = "C:/Users/{}/Desktop/Prog".format(username) 
                sounds_folder = "Sound/drygoe"
                audio_path = os.path.join(base_path, sounds_folder, "pesnya4.mp3")

                # Добавляем правильную информацию об аудио в очередь
                self.audio_queue.put((56, audio_path))
            else:
                self.message_list.addItem("Сейчас воспроизводится - pesnya4")

                # Строим путь к аудиофайлу (измените эту часть в соответствии со структурой вашего проекта)
                base_path = "C:/Users/{}/Desktop/Prog".format(username) 
                sounds_folder = "Sound/drygoe"
                audio_path = os.path.join(base_path, sounds_folder, "pesnya4.mp3")

                # Воспроизведение аудио
                self.play_audio((0, audio_path), None)  # Передавайте метку как None или обновляйте по мере необходимости
                self.playing = True


        if event.modifiers() == Qt.ControlModifier and event.key() == Qt.Key_L:
            print("Ctrl + L pressed")

            # Получение количества элементов в списке
            num_items = self.message_list.count()

            # Обновление виджета сообщений для указания, что воспроизводится pesnya5
            if num_items > 0:
                # Если уже есть элементы, добавляем новое сообщение в конец
                self.message_list.addItem("Сейчас воспроизводится - pesnya5")

                # Проверяем, инициализирован ли audio_queue, если нет, то инициализируем его
                if not hasattr(self, 'audio_queue'):
                    self.audio_queue = Queue()

                # Строим путь к аудиофайлу (измените эту часть в соответствии со структурой вашего проекта)
                base_path = "C:/Users/{}/Desktop/Prog".format(username) 
                sounds_folder = "Sound/drygoe"
                audio_path = os.path.join(base_path, sounds_folder, "pesnya5.mp3")

                # Добавляем правильную информацию об аудио в очередь
                self.audio_queue.put((60, audio_path))
            else:
                self.message_list.addItem("Сейчас воспроизводится - pesnya5")

                # Строим путь к аудиофайлу (измените эту часть в соответствии со структурой вашего проекта)
                base_path = "C:/Users/{}/Desktop/Prog".format(username) 
                sounds_folder = "Sound/drygoe"
                audio_path = os.path.join(base_path, sounds_folder, "pesnya5.mp3")

                # Воспроизведение аудио
                self.play_audio((0, audio_path), None)  # Передавайте метку как None или обновляйте по мере необходимости
                self.playing = True


        if event.modifiers() == Qt.ControlModifier and event.key() == Qt.Key_M:
            print("Ctrl + M pressed")

            # Получение количества элементов в списке
            num_items = self.message_list.count()

            # Обновление виджета сообщений для указания, что воспроизводится аудио о ФСБ
            if num_items > 0:
                # Если уже есть элементы, добавляем новое сообщение в конец
                self.message_list.addItem("Сейчас воспроизводится аудио о ФСБ")

                # Проверяем, инициализирован ли audio_queue, если нет, то инициализируем его
                if not hasattr(self, 'audio_queue'):
                    self.audio_queue = Queue()

                # Строим путь к аудиофайлу (измените эту часть в соответствии со структурой вашего проекта)
                base_path = "C:/Users/{}/Desktop/Prog".format(username) 
                sounds_folder = "Sound/drygoe"
                audio_path = os.path.join(base_path, sounds_folder, "FSB.mp3")

                # Добавляем правильную информацию об аудио в очередь
                self.audio_queue.put((61, audio_path))
            else:
                self.message_list.addItem("Сейчас воспроизводится аудио о ФСБ")

                # Строим путь к аудиофайлу (измените эту часть в соответствии со структурой вашего проекта)
                base_path = "C:/Users/{}/Desktop/Prog".format(username) 
                sounds_folder = "Sound/drygoe"
                audio_path = os.path.join(base_path, sounds_folder, "FSB.mp3")

                # Воспроизведение аудио
                self.play_audio((0, audio_path), None)  # Передавайте метку как None или обновляйте по мере необходимости
                self.playing = True


        if event.key() in [Qt.Key_Up, Qt.Key_Down]:
            selected_item = self.table_left.currentItem()

            if selected_item:
                # Получаем индексы строки и колонки выбранной ячейки
                row = selected_item.row()

                # Обработка стрелок вверх и вниз
                if event.key() == Qt.Key_Up:
                    row -= 1
                elif event.key() == Qt.Key_Down:
                    row += 1

                # Ограничиваем значения индекса строки
                row = max(0, min(row, self.table_left.rowCount() - 1))

                # Устанавливаем текущий элемент
                self.table_left.setCurrentItem(self.table_left.item(row, 0))

        if event.key() in [Qt.Key_Left, Qt.Key_Right]:
            # Обработка стрелок влево и вправо
            if event.key() == Qt.Key_Left:
                # Перемещаемся к предыдущей записи в виджете
                current_row = self.message_list.currentRow()
                self.message_list.setCurrentRow(max(0, current_row - 1))
            elif event.key() == Qt.Key_Right:
                # Перемещаемся к следующей записи в виджете
                current_row = self.message_list.currentRow()
                self.message_list.setCurrentRow(min(self.message_list.count() - 1, current_row + 1))

        # Добавление обработчика для нажатия клавиши Delete
        if event.key() == Qt.Key_Delete:
            # Удаление выделенных записей при нажатии клавиши Delete
            selected_items = self.message_list.selectedItems()
            for item in selected_items:
                self.handle_message_double_click(item)


        if event.key() == Qt.Key_Enter or event.key() == Qt.Key_Return:
            selected_item = self.table_left.currentItem()

            if selected_item:
                # Получаем индексы строки и колонки выбранной ячейки
                row = selected_item.row()

                # Получаем текст из всех ячеек в строке
                row_data = [self.table_left.item(row, c).text() for c in range(self.table_left.columnCount())]

                # Преобразуем список текстов в одну строку
                selected_text = ' | '.join(row_data)

                # Добавляем выбранный текст в виджет
                self.message_list.addItem(selected_text)

        # Передаем событие родительскому классу
        super().keyPressEvent(event)



    def add_message(self, message_text, label=None):
        # Ищем существующее сообщение с таким текстом
        existing_item = next((item for item in self.message_list.findItems(message_text, Qt.MatchExactly) if item.data(Qt.UserRole) is not None), None)

        if existing_item is None:
            # Сообщение с таким текстом еще не добавлено, добавляем его
            item = QListWidgetItem(message_text)
            self.message_list.addItem(item)
        else:
            # Сообщение с таким текстом уже существует, обновляем его метку
            item = existing_item

        # Проверяем, есть ли у нового сообщения метка
        if label is not None and item.data(Qt.UserRole) is None:
            # Если у нового сообщения нет метки и у существующего нет, и label не None, добавляем метку
            item.setData(Qt.UserRole, label)

        # Если метка уже установлена, обновим ее
        if label is not None:
            item.setData(Qt.UserRole, label)
        
        

        # Если проигрывание не запущено, начинаем проигрывание
        if not self.playing:
            self.play_from_queue()





    def remove_message(self, row):
        # Удаление сообщения из виджета
        current_item = self.message_list.takeItem(row)

        # Поиск строки в таблице по номеру автобуса и времени отправления
        bus_number = self.extract_bus_number(current_item.text())
        departure_time = self.extract_departure_time(current_item.text())
        table_row = self.find_row_by_bus_number_and_departure_time(bus_number, departure_time)

        if table_row != -1:
            # Устанавливаем стиль для выделения строки в белый цвет
            for column in range(self.table_left.columnCount()):
                self.table_left.item(table_row, column).setBackground(QColor(255, 255, 255))

        # Удаление сообщения из таблицы, если label равен "Завершается посадка"
        if hasattr(self, 'current_index') and self.current_index is not None:
            self.remove_message_from_table(current_item)







    def remove_message_from_table(self, item):
        bus_number = self.extract_bus_number(item.text())
        departure_time = self.extract_departure_time(item.text())

        # Проверка, что label равен "Завершается посадка"
        if item.data(Qt.UserRole) == "Завершается посадка":
            rows_to_remove = []

            for row in range(self.table_left.rowCount()):
                current_bus_number = self.table_left.item(row, 0).text()
                current_departure_time = self.table_left.item(row, 2).text()

                if current_bus_number == bus_number and current_departure_time == departure_time:
                    rows_to_remove.append(row)

            # Вывод значений перед удалением
            print(f"Values to remove: Bus Number - {bus_number}, Departure Time - {departure_time}")

            # Удаляем строки после завершения цикла
            for row in reversed(rows_to_remove):
                self.table_left.removeRow(row)
        else:
            # Вывод сообщения, если label не равен "Завершается посадка"
            print("Skipping removal from table. Label is not 'Завершается посадка'.")


    
    def find_row_by_bus_number_and_departure_time(self, bus_number, departure_time, route=None):
        # Поиск строк по номеру автобуса
        items = self.table_left.findItems(bus_number, Qt.MatchExactly)
        for item in items:
            row = item.row()
            # Получение элемента времени отправления для найденной строки
            departure_item = self.table_left.item(row, 2)
            if departure_item and departure_item.text() == departure_time:
                # Дополнительная проверка по маршруту, если указан
                if route is not None and bus_number in ["217", "223", "231", "399", "400", "802", "900", "905", "1337", "8522"]:
                    route_item = self.table_left.item(row, 1)
                    if route_item and route_item.text() == route:
                        return row
                else:
                    return row
        # Возвращаем -1, если запись не найдена
        return -1




    def check_audio_finished(self):
        if not pygame.mixer.music.get_busy():
                self.playing = False
                self.play_from_queue()

                if self.audio_queue.empty():
                    self.audio_check_timer.stop()

    def stop_audio(self):
        # Остановка аудио и остановка таймера
        if pygame.mixer.get_init():
            pygame.mixer.music.stop()
        self.audio_stop_timer.stop()


    def play_audio_from_message(self, item, bus_number, departure_time, platform, route, label, index):
        if label is None:
            self.message_list.clear()
            self.current_index = 0

        if label == 0:
            return 

        if index is None or index in self.index_history:
            if not self.index_history:
                index = 0
            else:
                index = max(self.index_history.keys()) + 1

        # Создаем кортеж с остальными значениями о рейсе
        route_info = (bus_number, departure_time, platform, route, label)

        # Записываем значение индекса в словарь вместе с остальной информацией о рейсе
        self.index_history[index] = route_info

        # Печатаем список индексов
        print("Список индексов:", list(self.index_history.keys()))
        print("Список индексов со значениями о рейсе:")
        for idx, info in self.index_history.items():
            print(f"Индекс: {idx}, Значения о рейсе: {info}")

        # Получаем значение индекса из self.index_history
        bus_number, departure_time, platform, route, label = route_info

        bus_number = route if bus_number in ["555", "566", "580", "680", "583"] else bus_number

        # Генерируем пути для звуков на русском
        bus_audio_path_ru, platform_audio_path_ru, hour_audio_path_ru, minute_audio_path_ru = self.generate_audio_path(bus_number, departure_time, platform, label)



        # Выводим информацию о сообщении
        print(f"Bus Number: {bus_number}")
        print(f"Индекс: {index}")  # Выводим новый индекс
        print(f"Bus audio path: {bus_audio_path_ru}")
        print(f"Platform audio path: {platform_audio_path_ru}")
        print(f"Hours audio path: {hour_audio_path_ru}")
        print(f"Minutes audio path: {minute_audio_path_ru}")
        print(f"Label: {label}")

        # Помещаем аудио-файлы в очередь воспроизведения
        if bus_number == route:
            self.audio_queue.put((index, platform_audio_path_ru))
            self.audio_queue.put((index, bus_audio_path_ru))
            self.audio_queue.put((index, hour_audio_path_ru))
            self.audio_queue.put((index, minute_audio_path_ru))

        else:
            self.audio_queue.put((index, platform_audio_path_ru))
            self.audio_queue.put((index, bus_audio_path_ru))
            self.audio_queue.put((index, hour_audio_path_ru))
            self.audio_queue.put((index, minute_audio_path_ru))

        # Если воспроизведение не начато, начинаем его
        if not self.playing:
            self.play_from_queue()


    


    def play_audio_from_message_finish(self, item, bus_number, departure_time, platform, route, label, index):

        # Очищаем список сообщений и устанавливаем текущий индекс, если метка пуста
        if label is None:
            self.message_list.clear()
            self.current_index = 0
            return
        
        if label == 0:
            return
            
        # Генерация нового индекса, если он не указан или уже существует в self.index_history
        if index is None or index in self.index_history:
            if not self.index_history:
                index = 0
            else:
                index = max(self.index_history.keys()) + 1
        
    # Записываем значение индекса в словарь
        self.index_history[index] = (bus_number, departure_time, platform, route, label)

        # Выводим список индексов с соответствующими значениями о рейсе
        print("Список индексов со значениями о рейсе:")
        for idx, info in self.index_history.items():
            print(f"Индекс: {idx}, Значения о рейсе: {info}")

        # Получаем значение индекса из self.index_history
        bus_number, departure_time, platform, route, label = self.index_history[index]

        bus_number = route if bus_number in ["555", "566", "580", "680", "583"] else bus_number

        # Генерация путей к аудиофайлам на русском и английском языках
        bus_audio_path_ru, platform_audio_path_ru, hour_audio_path_ru, minute_audio_path_ru = self.generate_audio_path(bus_number, departure_time, platform, label)

        print(f"Индекс: {index}")
        print(f"Bus audio path: {bus_audio_path_ru}")
        print(f"Platform_finish audio path: {platform_audio_path_ru}")
        print(f"Hours audio path: {hour_audio_path_ru}")
        print(f"Minutes audio path: {minute_audio_path_ru}")
        print(f"Label: {label}")

        # Добавление индекса в очередь вместе с путем к аудио
        if bus_number == route:
            # Если номер автобуса соответствует условию, добавить оба языка в очередь
            self.audio_queue.put((index, platform_audio_path_ru))
            self.audio_queue.put((index, bus_audio_path_ru))
            self.audio_queue.put((index, hour_audio_path_ru))
            self.audio_queue.put((index, minute_audio_path_ru))

        else:
            # Если номер автобуса не соответствует условию, добавить только русский язык в очередь
            self.audio_queue.put((index, platform_audio_path_ru))
            self.audio_queue.put((index, bus_audio_path_ru))
            self.audio_queue.put((index, hour_audio_path_ru))
            self.audio_queue.put((index, minute_audio_path_ru))

        # Запуск воспроизведения из очереди, если она пуста
        if not self.playing:
            self.play_from_queue()




    def play_audio_from_message_otmen(self, item, bus_number, departure_time, platform, route, label, index):

         # Очищаем список сообщений и устанавливаем текущий индекс, если метка пуста
        if label is None:
            self.message_list.clear()
            self.current_index = 0
            return
        
        if label == 0:
            return
            
        # Генерация нового индекса, если он не указан или уже существует в self.index_history
        if index is None or index in self.index_history:
            if not self.index_history:
                index = 0
            else:
                index = max(self.index_history.keys()) + 1
        
    # Записываем значение индекса в словарь
        self.index_history[index] = (bus_number, departure_time, platform, route, label)

        # Выводим список индексов с соответствующими значениями о рейсе
        print("Список индексов со значениями о рейсе:")
        for idx, info in self.index_history.items():
            print(f"Индекс: {idx}, Значения о рейсе: {info}")

        # Получаем значение индекса из self.index_history
        bus_number, departure_time, platform, route, label = self.index_history[index]

        bus_number = route if bus_number in ["555", "566", "580", "680", "583"] else bus_number

        # Генерация путей к аудиофайлам на русском и английском языках
        bus_audio_path_ru, platform_audio_path_ru, hour_audio_path_ru, minute_audio_path_ru = self.generate_audio_path(bus_number, departure_time, platform, label)
        print(f"Индекс: {index}")
        print(f"Bus audio path: {bus_audio_path_ru}")
        print(f"Platform_finish audio path: {platform_audio_path_ru}")
        print(f"Hours audio path: {hour_audio_path_ru}")
        print(f"Minutes audio path: {minute_audio_path_ru}")
        print(f"Label: {label}")

        # Добавление индекса в очередь вместе с путем к аудио
        if bus_number == route:
            # Если номер автобуса соответствует условию, добавить оба языка в очередь
            
            self.audio_queue.put((index, bus_audio_path_ru))
            self.audio_queue.put((index, hour_audio_path_ru))
            self.audio_queue.put((index, minute_audio_path_ru))
            self.audio_queue.put((index, platform_audio_path_ru))

        else:
            # Если номер автобуса не соответствует условию, добавить только русский язык в очередь
            self.audio_queue.put((index, bus_audio_path_ru))
            self.audio_queue.put((index, hour_audio_path_ru))
            self.audio_queue.put((index, minute_audio_path_ru))
            self.audio_queue.put((index, platform_audio_path_ru))

        # Запуск воспроизведения из очереди, если она пуста
        if not self.playing:
            self.play_from_queue()


    def play_audio_from_message_zader(self, item, bus_number, departure_time, platform, route, label, index):

        # Очищаем список сообщений и устанавливаем текущий индекс, если метка пуста
        if label is None:
            self.message_list.clear()
            self.current_index = 0
            return
            
        if label == 0:
            return

        # Генерация нового индекса, если он не указан или уже существует в self.index_history
        if index is None or index in self.index_history:
            if not self.index_history:
                index = 0
            else:
                index = max(self.index_history.keys()) + 1

       # Записываем значение индекса в словарь
        self.index_history[index] = (bus_number, departure_time, platform, route, label)

        # Выводим список индексов с соответствующими значениями о рейсе
        print("Список индексов со значениями о рейсе:")
        for idx, info in self.index_history.items():
            print(f"Индекс: {idx}, Значения о рейсе: {info}")

        # Получаем значение индекса из self.index_history
        bus_number, departure_time, platform, route, label = self.index_history[index]

        bus_number = route if bus_number in ["555", "566", "580", "680", "583"] else bus_number
        # Генерация путей к аудиофайлам на русском и английском языках
        bus_audio_path_ru, platform_audio_path_ru, hour_audio_path_ru, minute_audio_path_ru = self.generate_audio_path(bus_number, departure_time, platform, label)


        print(f"Индекс: {index}")
        print(f"Bus audio path: {bus_audio_path_ru}")
        print(f"Platform_finish audio path: {platform_audio_path_ru}")
        print(f"Hours audio path: {hour_audio_path_ru}")
        print(f"Minutes audio path: {minute_audio_path_ru}")
        print(f"Label: {label}")

        # Добавление индекса в очередь вместе с путем к аудио
        if bus_number == route:
            # Если номер автобуса соответствует условию, добавить оба языка в очередь
            self.audio_queue.put((index, bus_audio_path_ru))
            self.audio_queue.put((index, hour_audio_path_ru))
            self.audio_queue.put((index, minute_audio_path_ru))
            self.audio_queue.put((index, platform_audio_path_ru))

        else:
            # Если номер автобуса не соответствует условию, добавить только русский язык в очередь
            self.audio_queue.put((index, bus_audio_path_ru))
            self.audio_queue.put((index, hour_audio_path_ru))
            self.audio_queue.put((index, minute_audio_path_ru))
            self.audio_queue.put((index, platform_audio_path_ru))

        # Запуск воспроизведения из очереди, если она пуста
        if not self.playing:
            self.play_from_queue()


    def play_audio_from_message_prodolj(self, item, bus_number, departure_time, platform, route, label, index):
        # Очищаем self.index_history, если список сообщений пуст
        if not self.message_list:
            self.index_history.clear()

        if label == 0:
            return

        # Очищаем список сообщений и устанавливаем текущий индекс, если метка пуста
        if label is None:
            self.message_list.clear()
            self.current_index = 0
            return
            
        # Генерация нового индекса, если он не указан или уже существует в self.index_history
        if index is None or index in self.index_history:
            if not self.index_history:
                index = 0
            else:
                index = max(self.index_history.keys()) + 1

        # Записываем значение индекса в словарь
        self.index_history[index] = (bus_number, departure_time, platform, route, label)

        # Выводим список индексов с соответствующими значениями о рейсе
        print("Список индексов со значениями о рейсе:")
        for idx, info in self.index_history.items():
            print(f"Индекс: {idx}, Значения о рейсе: {info}")

        # Получаем значение индекса из self.index_history
        bus_number, departure_time, platform, route, label = self.index_history[index]
        print("bus =", bus_number)
        print("route =", route)
        if bus_number in ['555', '566', '580', '583', '680']:
            
            bus_number = route
        else:
            bus_number =bus_number

        # Генерация путей к аудиофайлам на русском и английском языках
        bus_audio_path_ru, platform_audio_path_ru, hour_audio_path_ru, minute_audio_path_ru = self.generate_audio_path(bus_number, departure_time, platform, label)


        print(f"Индекс: {index}")
        print(f"Bus audio path: {bus_audio_path_ru}")
        print(f"Platform_finish audio path: {platform_audio_path_ru}")
        print(f"Hours audio path: {hour_audio_path_ru}")
        print(f"Minutes audio path: {minute_audio_path_ru}")
        print(f"Label: {label}")

        # Добавление индекса в очередь вместе с путем к аудио
        self.audio_queue.put((index, platform_audio_path_ru))
        self.audio_queue.put((index, bus_audio_path_ru))
        self.audio_queue.put((index, hour_audio_path_ru))
        self.audio_queue.put((index, minute_audio_path_ru))

        # Запуск воспроизведения из очереди, если она пуста
        if not self.playing:
            self.play_from_queue()



    def extract_bus_number(self, message_text):
        # Извлечение номера автобуса из текста
        bus_match = re.search(r'\b[a-zA-Zа-яА-Я0-9]+\b', message_text)
        print(bus_match)
        if bus_match:
            bus_number = bus_match.group()
            return bus_number
        else:
            print("Bus number not found")  # Отладочная информация
            return None

    def extract_platform(self, message_text):
    # Реализуйте извлечение двух предпоследних элементов из текста
        platform_match = re.search(r'\|(\s*(\d+)\s*)\|', message_text)
        print(platform_match)
        if platform_match:
            platform1 = platform_match.group(2)
            return platform1
        else:
            print("Platform not found")  # Отладочная информация
            return None

    def extract_platform_finish(self, message_text):
        # Извлечение номера платформы из текста
        platform_match = re.search(r'\b(\d+)\s*$', message_text)
        if platform_match:
            platform = platform_match.group(1)
            return platform
        else:
            print("Platform_finish not found")  # Отладочная информация
            return None

    def extract_departure_time(self, message_text):
        # Извлечение времени отправления из текста
        time_match = re.search(r'\b(\d{1,2}:\d{2})\b', message_text)
        if time_match:
            departure_time = time_match.group(1)
            return departure_time
        else:
            print("Departure time not found")  # Отладочная информация
            return None

    def extract_route(self, message_text):
        # Регулярное выражение для извлечения маршрута
        pattern = re.compile(r"(\d+) \| (.+?) — (.+?) \| (\d{2}:\d{2}) \| (\d+) \| (.+)")
        match = pattern.match(message_text)
        print(match)
        if match:
            # Извлечение номера маршрута, города отправления и прибытия
            route_number = match.group(1)
            departure_city = match.group(2)
            arrival_city = match.group(3)
            # Форматирование строки маршрута и возврат результата
            return f"{route_number}: {departure_city} — {arrival_city}"
        else:
            return None






    def generate_audio_path(self, bus_number, departure_time, platform, label):
        # Реализуйте формирование пути к аудиозаписи на основе извлеченной информации

        base_path = os.path.dirname(os.path.abspath(__file__))  # Получаем путь к каталогу, где находится скрипт
        sounds_folder = 'Sound'  # Имя подкаталога с звуковыми файлами


        # Словарь для номеров автобусов
        bus_audio_files_ru = {
            '101': os.path.join(base_path, sounds_folder, "bus", "reis 101.mp3"),
            '102': os.path.join(base_path, sounds_folder, "bus", "reis 102.mp3"),
            '105': os.path.join(base_path, sounds_folder, "bus", "reis 105.mp3"),
            '105ж': os.path.join(base_path, sounds_folder, "bus", "reis 105ж.mp3"),
            '105к': os.path.join(base_path, sounds_folder, "bus", "reis 105к.mp3"),
            '110': os.path.join(base_path, sounds_folder, "bus", "reis 110.mp3"),
            '119': os.path.join(base_path, sounds_folder, "bus", "reis 119.mp3"),
            '127': os.path.join(base_path, sounds_folder, "bus", "reis 127.mp3"),
            '127к': os.path.join(base_path, sounds_folder, "bus", "reis 127к.mp3"),
            '343': os.path.join(base_path, sounds_folder, "bus", "reis 343.mp3"),
            '363': os.path.join(base_path, sounds_folder, "bus", "reis 363.mp3"),
            '503А': os.path.join(base_path, sounds_folder, "bus", "reis 503А.mp3"),
            '520А': os.path.join(base_path, sounds_folder, "bus", "reis 520.mp3"),
            '530': os.path.join(base_path, sounds_folder, "bus", "reis 530.mp3"),
            '554': os.path.join(base_path, sounds_folder, "bus", "reis 554.mp3"),
            '564А': os.path.join(base_path, sounds_folder, "bus", "reis 564А.mp3"),
            '565': os.path.join(base_path, sounds_folder, "bus", "reis 565.mp3"),
            '567А': os.path.join(base_path, sounds_folder, "bus", "reis 567А.mp3"),


            '555: Карамышево — Калининград': os.path.join(base_path, sounds_folder, "bus", "to_kld_555.mp3"),
            '555: Калининград — Карамышево': os.path.join(base_path, sounds_folder, "bus", "reis 555.mp3"),
            '566: Озерск — Калининград': os.path.join(base_path, sounds_folder, "bus", "to_kld_566.mp3"),
            '566: Калининград — Озерск': os.path.join(base_path, sounds_folder, "bus", "reis 566.mp3"),
            '580: Гусев — Калининград': os.path.join(base_path, sounds_folder, "bus", "to_kld_580.mp3"),
            '580: Калининград — Гусев': os.path.join(base_path, sounds_folder, "bus", "reis 580.mp3"),
            '583: Черняховск — Калининград': os.path.join(base_path, sounds_folder, "bus", "to_kld_583.mp3"),
            '583: Калининград — Чернышевское': os.path.join(base_path, sounds_folder, "bus", "reis 583.mp3"),
    
            '680: Черняховск — Калининград': os.path.join(base_path, sounds_folder, "bus", "to_kld_680э.mp3"),
            '680: Калининград — Черняховск': os.path.join(base_path, sounds_folder, "bus", "reis 680э.mp3"),
            '680: Черняховск — Гусев': os.path.join(base_path, sounds_folder, "bus", "reis 680э.mp3"),
            '680: Гусев — Черняховск': os.path.join(base_path, sounds_folder, "bus", "to_kld_680э.mp3"),
     
        }



        bus_audio_files_otmen_ru = {
            '101': os.path.join(base_path, sounds_folder, "otmen", "reis 101.mp3"),
            '102': os.path.join(base_path, sounds_folder, "otmen", "reis 102.mp3"),
            '105': os.path.join(base_path, sounds_folder, "otmen", "reis 105.mp3"),
            '105ж': os.path.join(base_path, sounds_folder, "otmen", "reis 105ж.mp3"),
            '105к': os.path.join(base_path, sounds_folder, "otmen", "reis 105к.mp3"),
            '110': os.path.join(base_path, sounds_folder, "otmen", "reis 110.mp3"),
            '119': os.path.join(base_path, sounds_folder, "otmen", "reis 119.mp3"),
            '127': os.path.join(base_path, sounds_folder, "otmen", "reis 127.mp3"),
            '127к': os.path.join(base_path, sounds_folder, "otmen", "reis 127к.mp3"),
            '343': os.path.join(base_path, sounds_folder, "otmen", "reis 343.mp3"),
            '363': os.path.join(base_path, sounds_folder, "otmen", "reis 363.mp3"),
            '503А': os.path.join(base_path, sounds_folder, "otmen", "reis 503А.mp3"),
            '520А': os.path.join(base_path, sounds_folder, "otmen", "reis 520.mp3"),
            '530': os.path.join(base_path, sounds_folder, "otmen", "reis 530.mp3"),
            '554': os.path.join(base_path, sounds_folder, "otmen", "reis 554.mp3"),
            '564А': os.path.join(base_path, sounds_folder, "otmen", "reis 564А.mp3"),
            '565': os.path.join(base_path, sounds_folder, "otmen", "reis 565.mp3"),
            '567А': os.path.join(base_path, sounds_folder, "otmen", "reis 567А.mp3"),

            '555: Карамышево — Калининград': os.path.join(base_path, sounds_folder, "otmen", "to_kld_555.mp3"),
            '555: Калининград — Карамышево': os.path.join(base_path, sounds_folder, "otmen", "reis 555.mp3"),
            '566: Озерск — Калининград': os.path.join(base_path, sounds_folder, "otmen", "to_kld_566.mp3"),
            '566: Калининград — Озерск': os.path.join(base_path, sounds_folder, "otmen", "reis 566.mp3"),
            '580: Гусев — Калининград': os.path.join(base_path, sounds_folder, "otmen", "to_kld_580.mp3"),
            '580: Калининград — Гусев': os.path.join(base_path, sounds_folder, "otmen", "reis 580.mp3"),
            '583: Черняховск — Калининград': os.path.join(base_path, sounds_folder, "otmen", "to_kld_583.mp3"),
            '583: Калининград — Чернышевское': os.path.join(base_path, sounds_folder, "otmen", "reis 583.mp3"),
            '680: Черняховск — Калининград': os.path.join(base_path, sounds_folder, "otmen", "to_kld_680э.mp3"),
            '680: Калининград — Черняховск': os.path.join(base_path, sounds_folder, "otmen", "reis 680э.mp3"),
            '680: Черняховск — Гусев': os.path.join(base_path, sounds_folder, "bus", "to_kld_680э.mp3"),
            '680: Гусев — Черняховск': os.path.join(base_path, sounds_folder, "bus", "reis 680э.mp3"),
        }


        bus_audio_files_zader_ru = {
            '101': os.path.join(base_path, sounds_folder, "zader", "reis 101.mp3"),
            '102': os.path.join(base_path, sounds_folder, "zader", "reis 102.mp3"),
            '105': os.path.join(base_path, sounds_folder, "zader", "reis 105.mp3"),
            '105ж': os.path.join(base_path, sounds_folder, "zader", "reis 105ж.mp3"),
            '105к': os.path.join(base_path, sounds_folder, "zader", "reis 105к.mp3"),
            '110': os.path.join(base_path, sounds_folder, "zader", "reis 110.mp3"),
            '119': os.path.join(base_path, sounds_folder, "zader", "reis 119.mp3"),
            '127': os.path.join(base_path, sounds_folder, "zader", "reis 127.mp3"),
            '127к': os.path.join(base_path, sounds_folder, "zader", "reis 127к.mp3"),
            '343': os.path.join(base_path, sounds_folder, "zader", "reis 343.mp3"),
            '363': os.path.join(base_path, sounds_folder, "zader", "reis 363.mp3"),
            '503А': os.path.join(base_path, sounds_folder, "zader", "reis 503А.mp3"),
            '520А': os.path.join(base_path, sounds_folder, "zader", "reis 520.mp3"),
            '530': os.path.join(base_path, sounds_folder, "zader", "reis 530.mp3"),
            '554': os.path.join(base_path, sounds_folder, "zader", "reis 554.mp3"),
            '564А': os.path.join(base_path, sounds_folder, "zader", "reis 564А.mp3"),
            '565': os.path.join(base_path, sounds_folder, "zader", "reis 565.mp3"),
            '567А': os.path.join(base_path, sounds_folder, "zader", "reis 567А.mp3"),

            '555: Озерск — Калининград': os.path.join(base_path, sounds_folder, "zader", "to_kld_555.mp3"),
            '555: Калининград — Озерск': os.path.join(base_path, sounds_folder, "zader", "reis 555.mp3"),
            '566: Озерск — Калининград': os.path.join(base_path, sounds_folder, "zader", "to_kld_566.mp3"),
            '566: Калининград — Озерск': os.path.join(base_path, sounds_folder, "zader", "reis 566.mp3"),
            '580: Гусев — Калининград': os.path.join(base_path, sounds_folder, "zader", "to_kld_580.mp3"),
            '580: Калининград — Гусев': os.path.join(base_path, sounds_folder, "zader", "reis 580.mp3"),
            '583: Черняховск — Калининград': os.path.join(base_path, sounds_folder, "zader", "to_kld_583.mp3"),
            '583: Калининград — Чернышевское': os.path.join(base_path, sounds_folder, "zader", "reis 583.mp3"),
            '680: Черняховск — Калининград': os.path.join(base_path, sounds_folder, "zader", "to_kld_680э.mp3"),
            '680: Калининград — Черняховск': os.path.join(base_path, sounds_folder, "zader", "reis 680э.mp3"),
            '680: Черняховск — Гусев': os.path.join(base_path, sounds_folder, "bus", "to_kld_680э.mp3"),
            '680: Гусев — Черняховск': os.path.join(base_path, sounds_folder, "bus", "reis 680э.mp3"),

        }



        platform_audio_files_ru = {
            '1': os.path.join(base_path, sounds_folder, "platform_nachinaetsya", "platform1.mp3"),
            '2': os.path.join(base_path, sounds_folder,"platform_nachinaetsya", "platform2.mp3"),
            '3': os.path.join(base_path, sounds_folder,"platform_nachinaetsya", "platform3.mp3"),
            '4': os.path.join(base_path, sounds_folder,"platform_nachinaetsya", "platform4.mp3"),
            '5': os.path.join(base_path, sounds_folder,"platform_nachinaetsya", "platform5.mp3"),
            '6': os.path.join(base_path, sounds_folder,"platform_nachinaetsya", "platform6.mp3"),
            '7': os.path.join(base_path, sounds_folder,"platform_nachinaetsya", "platform7.mp3"),
            '8': os.path.join(base_path, sounds_folder,"platform_nachinaetsya", "platform8.mp3"),
            '9': os.path.join(base_path, sounds_folder,"platform_nachinaetsya", "platform9.mp3"),
            '10': os.path.join(base_path, sounds_folder,"platform_nachinaetsya", "platform10.mp3"),
            '11': os.path.join(base_path, sounds_folder,"platform_nachinaetsya", "platform11.mp3"),
            '12': os.path.join(base_path, sounds_folder,"platform_nachinaetsya", "platform12.mp3"),
            '13': os.path.join(base_path, sounds_folder,"platform_nachinaetsya", "platform13.mp3"),
            '14': os.path.join(base_path, sounds_folder,"platform_nachinaetsya", "platform14.mp3"),
            '15': os.path.join(base_path, sounds_folder,"platform_nachinaetsya", "platform15.mp3"),
            '16': os.path.join(base_path, sounds_folder,"platform_nachinaetsya", "platform16.mp3"),
            '17': os.path.join(base_path, sounds_folder,"platform_nachinaetsya", "platform17.mp3"),
            '18': os.path.join(base_path, sounds_folder,"platform_nachinaetsya", "platform18.mp3"),
            '19': os.path.join(base_path, sounds_folder,"platform_nachinaetsya", "platform19.mp3"),
            '20': os.path.join(base_path, sounds_folder,"platform_nachinaetsya", "platform20.mp3"),
        }


        platform_finish_audio_files_ru = {
            '1': os.path.join(base_path, sounds_folder,"platform_zakanch", "platform1.mp3"),
            '2': os.path.join(base_path, sounds_folder,"platform_zakanch", "platform2.mp3"),
            '3': os.path.join(base_path, sounds_folder,"platform_zakanch", "platform3.mp3"),
            '4': os.path.join(base_path, sounds_folder,"platform_zakanch", "platform4.mp3"),
            '5': os.path.join(base_path, sounds_folder,"platform_zakanch", "platform5.mp3"),
            '6': os.path.join(base_path, sounds_folder,"platform_zakanch", "platform6.mp3"),
            '7': os.path.join(base_path, sounds_folder,"platform_zakanch", "platform7.mp3"),
            '8': os.path.join(base_path, sounds_folder,"platform_zakanch", "platform8.mp3"),
            '9': os.path.join(base_path, sounds_folder,"platform_zakanch", "platform9.mp3"),
            '10': os.path.join(base_path, sounds_folder,"platform_zakanch", "platform10.mp3"),
            '11': os.path.join(base_path, sounds_folder,"platform_zakanch", "platform11.mp3"),
            '12': os.path.join(base_path, sounds_folder,"platform_zakanch", "platform12.mp3"),
            '13': os.path.join(base_path, sounds_folder,"platform_zakanch", "platform13.mp3"),
            '14': os.path.join(base_path, sounds_folder,"platform_zakanch", "platform14.mp3"),
            '15': os.path.join(base_path, sounds_folder,"platform_zakanch", "platform15.mp3"),
            '16': os.path.join(base_path, sounds_folder,"platform_zakanch", "platform16.mp3"),
            '17': os.path.join(base_path, sounds_folder,"platform_zakanch", "platform17.mp3"),
            '18': os.path.join(base_path, sounds_folder,"platform_zakanch", "platform18.mp3"),
            '19': os.path.join(base_path, sounds_folder,"platform_zakanch", "platform19.mp3"),
            '20': os.path.join(base_path, sounds_folder,"platform_zakanch", "platform20.mp3"),
        }



        platform_otmen_audio_files_ru = {
            '1': os.path.join(base_path, sounds_folder, "otmen", "otmen.mp3"),
            '2': os.path.join(base_path, sounds_folder,"otmen", "otmen.mp3"),
            '3': os.path.join(base_path, sounds_folder,"otmen", "otmen.mp3"),
            '4': os.path.join(base_path, sounds_folder,"otmen", "otmen.mp3"),
            '5': os.path.join(base_path, sounds_folder,"otmen", "otmen.mp3"),
            '6': os.path.join(base_path, sounds_folder,"otmen", "otmen.mp3"),
            '7': os.path.join(base_path, sounds_folder,"otmen", "otmen.mp3"),
            '8': os.path.join(base_path, sounds_folder,"otmen", "otmen.mp3"),
            '9': os.path.join(base_path, sounds_folder,"otmen", "otmen.mp3"),
            '10': os.path.join(base_path, sounds_folder,"otmen", "otmen.mp3"),
            '11': os.path.join(base_path, sounds_folder,"otmen", "otmen.mp3"),
            '12': os.path.join(base_path, sounds_folder,"otmen", "otmen.mp3"),
            '13': os.path.join(base_path, sounds_folder,"otmen", "otmen.mp3"),
            '14': os.path.join(base_path, sounds_folder,"otmen", "otmen.mp3"),
            '15': os.path.join(base_path, sounds_folder,"otmen", "otmen.mp3"),
            '16': os.path.join(base_path, sounds_folder,"otmen", "otmen.mp3"),
            '17': os.path.join(base_path, sounds_folder,"otmen", "otmen.mp3"),
            '18': os.path.join(base_path, sounds_folder,"otmen", "otmen.mp3"),
            '19': os.path.join(base_path, sounds_folder,"otmen", "otmen.mp3"),
            '20': os.path.join(base_path, sounds_folder,"otmen", "otmen.mp3"),
        }



        platform_zader_audio_files_ru = {
            '1': os.path.join(base_path, sounds_folder,"zader", "zader.mp3"),
            '2': os.path.join(base_path, sounds_folder,"zader", "zader.mp3"),
            '3': os.path.join(base_path, sounds_folder,"zader", "zader.mp3"),
            '4': os.path.join(base_path, sounds_folder,"zader", "zader.mp3"),
            '5': os.path.join(base_path, sounds_folder,"zader", "zader.mp3"),
            '6': os.path.join(base_path, sounds_folder,"zader", "zader.mp3"),
            '7': os.path.join(base_path, sounds_folder,"zader", "zader.mp3"),
            '8': os.path.join(base_path, sounds_folder,"zader", "zader.mp3"),
            '9': os.path.join(base_path, sounds_folder,"zader", "zader.mp3"),
            '10': os.path.join(base_path, sounds_folder,"zader", "zader.mp3"),
            '11': os.path.join(base_path, sounds_folder,"zader", "zader.mp3"),
            '12': os.path.join(base_path, sounds_folder,"zader", "zader.mp3"),
            '13': os.path.join(base_path, sounds_folder,"zader", "zader.mp3"),
            '14': os.path.join(base_path, sounds_folder,"zader", "zader.mp3"),
            '15': os.path.join(base_path, sounds_folder,"zader", "zader.mp3"),
            '16': os.path.join(base_path, sounds_folder,"zader", "zader.mp3"),
            '17': os.path.join(base_path, sounds_folder,"zader", "zader.mp3"),
            '18': os.path.join(base_path, sounds_folder,"zader", "zader.mp3"),
            '19': os.path.join(base_path, sounds_folder,"zader", "zader.mp3"),
            '20': os.path.join(base_path, sounds_folder,"zader", "zader.mp3"),
        }
        platform_prodolj_audio_files_ru = {
            '1': os.path.join(base_path, sounds_folder,"platform_prodolj", "platform1.mp3"),
            '2': os.path.join(base_path, sounds_folder,"platform_prodolj", "platform2.mp3"),
            '3': os.path.join(base_path, sounds_folder,"platform_prodolj", "platform3.mp3"),
            '4': os.path.join(base_path, sounds_folder,"platform_prodolj", "platform4.mp3"),
            '5': os.path.join(base_path, sounds_folder,"platform_prodolj", "platform5.mp3"),
            '6': os.path.join(base_path, sounds_folder,"platform_prodolj", "platform6.mp3"),
            '7': os.path.join(base_path, sounds_folder,"platform_prodolj", "platform7.mp3"),
            '8': os.path.join(base_path, sounds_folder,"platform_prodolj", "platform8.mp3"),
            '9': os.path.join(base_path, sounds_folder,"platform_prodolj", "platform9.mp3"),
            '10': os.path.join(base_path, sounds_folder,"platform_prodolj", "platform10.mp3"),
            '11': os.path.join(base_path, sounds_folder,"platform_prodolj", "platform11.mp3"),
            '12': os.path.join(base_path, sounds_folder,"platform_prodolj", "platform12.mp3"),
            '13': os.path.join(base_path, sounds_folder,"platform_prodolj", "platform13.mp3"),
            '14': os.path.join(base_path, sounds_folder,"platform_prodolj", "platform14.mp3"),
            '15': os.path.join(base_path, sounds_folder,"platform_prodolj", "platform15.mp3"),
            '16': os.path.join(base_path, sounds_folder,"platform_prodolj", "platform16.mp3"),
            '17': os.path.join(base_path, sounds_folder,"platform_prodolj", "platform17.mp3"),
            '18': os.path.join(base_path, sounds_folder,"platform_prodolj", "platform18.mp3"),
            '19': os.path.join(base_path, sounds_folder,"platform_prodolj", "platform19.mp3"),
            '20': os.path.join(base_path, sounds_folder,"platform_prodolj", "platform20.mp3"),
        }

        

        hour_audio_files_ru = {
            5: os.path.join(base_path, sounds_folder, "hours", "hours 5.mp3"),
            6: os.path.join(base_path, sounds_folder, "hours", "hours 6.mp3"),
            7: os.path.join(base_path, sounds_folder, "hours", "hours 7.mp3"),
            8: os.path.join(base_path, sounds_folder, "hours", "hours 8.mp3"),
            9: os.path.join(base_path, sounds_folder, "hours", "hours 9.mp3"),
            10: os.path.join(base_path, sounds_folder, "hours", "hours 10.mp3"),
            11: os.path.join(base_path, sounds_folder, "hours", "hours 11.mp3"),
            12: os.path.join(base_path, sounds_folder, "hours", "hours 12.mp3"),
            13: os.path.join(base_path, sounds_folder, "hours", "hours 13.mp3"),
            14: os.path.join(base_path, sounds_folder, "hours", "hours 14.mp3"),
            15: os.path.join(base_path, sounds_folder, "hours", "hours 15.mp3"),
            16: os.path.join(base_path, sounds_folder, "hours", "hours 16.mp3"),
            17: os.path.join(base_path, sounds_folder, "hours", "hours 17.mp3"),
            18: os.path.join(base_path, sounds_folder, "hours", "hours 18.mp3"),
            19: os.path.join(base_path, sounds_folder, "hours", "hours 19.mp3"),
            20: os.path.join(base_path, sounds_folder, "hours", "hours 20.mp3"),
            21: os.path.join(base_path, sounds_folder, "hours", "hours 21.mp3"),
            22: os.path.join(base_path, sounds_folder, "hours", "hours 22.mp3"),
            23: os.path.join(base_path, sounds_folder, "hours", "hours 23.mp3"),

            # Добавьте другие соответствия часам, если необходимо
        }


        minute_audio_files_ru = {
            0: os.path.join(base_path, sounds_folder, "minut", "minute 00.mp3"),
            1: os.path.join(base_path, sounds_folder, "minut", "minute 1.mp3"),
            2: os.path.join(base_path, sounds_folder, "minut", "minute 2.mp3"),
            3: os.path.join(base_path, sounds_folder, "minut", "minute 3.mp3"),
            4: os.path.join(base_path, sounds_folder, "minut", "minute 4.mp3"),
            5: os.path.join(base_path, sounds_folder, "minut", "minute 5.mp3"),
            6: os.path.join(base_path, sounds_folder, "minut", "minute 6.mp3"),
            7: os.path.join(base_path, sounds_folder, "minut", "minute 7.mp3"),
            8: os.path.join(base_path, sounds_folder, "minut", "minute 8.mp3"),
            9: os.path.join(base_path, sounds_folder, "minut", "minute 9.mp3"),
            10: os.path.join(base_path, sounds_folder, "minut", "minute 10.mp3"),
            11: os.path.join(base_path, sounds_folder, "minut", "minute 11.mp3"),
            12: os.path.join(base_path, sounds_folder, "minut", "minute 12.mp3"),
            13: os.path.join(base_path, sounds_folder, "minut", "minute 13.mp3"),
            14: os.path.join(base_path, sounds_folder, "minut", "minute 14.mp3"),
            15: os.path.join(base_path, sounds_folder, "minut", "minute 15.mp3"),
            16: os.path.join(base_path, sounds_folder, "minut", "minute 16.mp3"),
            17: os.path.join(base_path, sounds_folder, "minut", "minute 17.mp3"),
            18: os.path.join(base_path, sounds_folder, "minut", "minute 18.mp3"),
            19: os.path.join(base_path, sounds_folder, "minut", "minute 19.mp3"),
            20: os.path.join(base_path, sounds_folder, "minut", "minute 20.mp3"),
            21: os.path.join(base_path, sounds_folder, "minut", "minute 21.mp3"),
            22: os.path.join(base_path, sounds_folder, "minut", "minute 22.mp3"),
            23: os.path.join(base_path, sounds_folder, "minut", "minute 23.mp3"),
            24: os.path.join(base_path, sounds_folder, "minut", "minute 24.mp3"),
            25: os.path.join(base_path, sounds_folder, "minut", "minute 25.mp3"),
            26: os.path.join(base_path, sounds_folder, "minut", "minute 26.mp3"),
            27: os.path.join(base_path, sounds_folder, "minut", "minute 27.mp3"),
            28: os.path.join(base_path, sounds_folder, "minut", "minute 28.mp3"),
            29: os.path.join(base_path, sounds_folder, "minut", "minute 29.mp3"),
            30: os.path.join(base_path, sounds_folder, "minut", "minute 30.mp3"),
            31: os.path.join(base_path, sounds_folder, "minut", "minute 31.mp3"),
            32: os.path.join(base_path, sounds_folder, "minut", "minute 32.mp3"),
            33: os.path.join(base_path, sounds_folder, "minut", "minute 33.mp3"),
            34: os.path.join(base_path, sounds_folder, "minut", "minute 34.mp3"),
            35: os.path.join(base_path, sounds_folder, "minut", "minute 35.mp3"),
            36: os.path.join(base_path, sounds_folder, "minut", "minute 36.mp3"),
            37: os.path.join(base_path, sounds_folder, "minut", "minute 37.mp3"),
            38: os.path.join(base_path, sounds_folder, "minut", "minute 38.mp3"),
            39: os.path.join(base_path, sounds_folder, "minut", "minute 39.mp3"),
            40: os.path.join(base_path, sounds_folder, "minut", "minute 40.mp3"),
            41: os.path.join(base_path, sounds_folder, "minut", "minute 41.mp3"),
            42: os.path.join(base_path, sounds_folder, "minut", "minute 42.mp3"),
            43: os.path.join(base_path, sounds_folder, "minut", "minute 43.mp3"),
            44: os.path.join(base_path, sounds_folder, "minut", "minute 44.mp3"),
            45: os.path.join(base_path, sounds_folder, "minut", "minute 45.mp3"),
            46: os.path.join(base_path, sounds_folder, "minut", "minute 46.mp3"),
            47: os.path.join(base_path, sounds_folder, "minut", "minute 47.mp3"),
            48: os.path.join(base_path, sounds_folder, "minut", "minute 48.mp3"),
            49: os.path.join(base_path, sounds_folder, "minut", "minute 49.mp3"),
            50: os.path.join(base_path, sounds_folder, "minut", "minute 50.mp3"),
            51: os.path.join(base_path, sounds_folder, "minut", "minute 51.mp3"),
            52: os.path.join(base_path, sounds_folder, "minut", "minute 52.mp3"),
            53: os.path.join(base_path, sounds_folder, "minut", "minute 53.mp3"),
            54: os.path.join(base_path, sounds_folder, "minut", "minute 54.mp3"),
            55: os.path.join(base_path, sounds_folder, "minut", "minute 55.mp3"),
            56: os.path.join(base_path, sounds_folder, "minut", "minute 56.mp3"),
            57: os.path.join(base_path, sounds_folder, "minut", "minute 57.mp3"),
            58: os.path.join(base_path, sounds_folder, "minut", "minute 58.mp3"),
            59: os.path.join(base_path, sounds_folder, "minut", "minute 59.mp3"),
            # Добавьте другие соответствия минутам, если необходимо
        }

       
        
            # Для Ru языка
        hours, minutes = self.extract_hours_and_minutes(departure_time)
            # Получаем пути к аудиозаписям для часов и минут
        hour_audio_path = hour_audio_files_ru.get(hours, None)
        minute_audio_path = minute_audio_files_ru.get(minutes, None)
        bus_audio_path = bus_audio_files_ru.get(bus_number, None)
        if label == "Прибытие на посадку":
                platform_audio_path = platform_audio_files_ru.get(platform, None)
                bus_audio_path = bus_audio_files_ru.get(bus_number, None)
        elif label == "Завершается посадка":
                platform_audio_path = platform_finish_audio_files_ru.get(platform, None)

        elif label == "Отменен":
                bus_audio_path = bus_audio_files_otmen_ru.get(bus_number, None)
                platform_audio_path = platform_otmen_audio_files_ru.get(platform, None)
        elif label == "Задерживается":
                bus_audio_path = bus_audio_files_zader_ru.get(bus_number, None)
                platform_audio_path = platform_zader_audio_files_ru.get(platform, None)
        elif label == "Продолжается посадка":
                bus_audio_path = bus_audio_files_ru.get(bus_number, None)
                platform_audio_path = platform_prodolj_audio_files_ru.get(platform, None)
         
        else:
            platform_audio_path = None

           

        return bus_audio_path, platform_audio_path, hour_audio_path, minute_audio_path



    def extract_hours_and_minutes(self, time_str):
        # Извлечение часов и минут из строки времени
        time_match = re.search(r'(\d{1,2}):(\d{2})', time_str)
        if time_match:
            hours = int(time_match.group(1))
            minutes = int(time_match.group(2))
            return hours, minutes
        else:
            print("Ошибка извлечения часов и минут.")
            return None, None


    
    def play_audio(self, audio_info, label):
        index, path = audio_info
        print(f"Воспроизведение аудио {index} из пути: {path}")
 

        # Проверка, является ли индекс равным 0 и еще не было воспроизведено аудио "audio_pered.mp3"
        if index == 0 and not self.audio_pered_played:
            # Установка текущего индекса
            self.current_index = index
            audio_file = "audio_pered.mp3"
            
            # Формирование абсолютного пути к аудиофайлу
            base_path = os.path.dirname(os.path.abspath(__file__))  
            sounds_folder = "Sound/drygoe"  
            audio_path = os.path.join(base_path, sounds_folder, audio_file)

            # Создание и запуск потока для проигрывания аудио "audio_pered.mp3"
            self.audio_player_thread = AudioPlayer(audio_path)
            self.audio_player_thread.finished.connect(lambda: self.start_next_audio(index, path, label))
            self.audio_player_thread.label = label
            self.audio_player_thread.start()
        else:
            # Проверка, есть ли текущий индекс и отличается ли он от нового индекса
            if hasattr(self, 'current_index') and self.current_index != index:
                # Удаление текущего сообщения через 2 секунды и запуск следующего аудио
                current_item = self.message_list.item(0)
                current_row = self.message_list.row(current_item)
                self.remove_message(current_row)
                QTimer.singleShot(2000, lambda: self.start_next_audio(index, path, label))
            else:
                # Установка текущего индекса
                self.current_index = index
                # Если аудио "audio_pered.mp3" уже было воспроизведено или текущее аудио отличается, просто воспроизводим следующее аудио
                self.audio_player_thread = AudioPlayer(path)
                self.audio_player_thread.finished.connect(self.on_audio_finished)
                self.audio_player_thread.label = label
                self.audio_player_thread.start()
                
                


    def start_next_audio(self, index, path, label):
      
        # Установка текущего индекса
        self.current_index = index
        # Проверка, является ли индекс равным 0, и установка соответствующего флага
        if index == 0:
            self.audio_pered_played = True  
        # Создание и запуск потока для проигрывания аудио
        self.audio_player_thread = AudioPlayer(path)
        self.audio_player_thread.finished.connect(self.on_audio_finished)
        self.audio_player_thread.label = label
        self.audio_player_thread.start()
        




    def play_from_queue(self):
        
        # Проверка, не проигрывается ли уже аудио, и не пустая ли очередь
        if not self.playing and not self.audio_queue.empty():
            # Получение пути к аудио из очереди
            audio_path = self.audio_queue.get()
        
            # Получение текущего элемента
            current_item = self.message_list.item(0)

            # Проверка, есть ли у текущего элемента метка
            current_label = current_item.data(Qt.UserRole)
            
            # Проверка, связан ли текст сообщения с курением
            current_text = current_item.text()
            if (current_label is not None or "Воспроизводится аудио о посадке по билетам" in current_text  or "Воспроизводится аудио о проезжей части" in current_text or "Воспроизводится аудио о террористических актах" in current_text or "Воспроизводится доп аудио 1" in current_text or "Воспроизводится доп аудио 2" in current_text or "Воспроизводится доп аудио 3" in current_text):
                # Проигрывание аудио
                self.play_audio(audio_path, current_label)
                self.playing = True
            
            else:
                
                self.playing = False



       


    def on_audio_finished(self):
        # Остановка таймера
        self.audio_check_timer.stop()

        # Получение текущего элемента
        current_item = self.message_list.item(0)

        # Получение индекса текущего элемента
        current_row = self.message_list.row(current_item)

        # Очистка аудио-потока
        if pygame.mixer.get_init():
            pygame.mixer.music.stop()

        # Получение метки текущего элемента
        current_label = current_item.data(Qt.UserRole)
        self.playing = False

        if not self.audio_queue.empty():
            # Если в очереди есть аудио, получаем путь к нему и проигрываем
            audio_path = self.audio_queue.get()
            self.play_audio(audio_path, current_label) 
            self.playing = True
        else:
            self.playing = False

            # Увеличение счетчика воспроизведений для текущего элемента
            self.play_count_dict[current_row] = self.play_count_dict.get(current_row, 0) + 1

            # Удаление текущего элемента
            self.remove_message(current_row)

            # Переход к следующему элементу в виджете, если таковой имеется
            if current_row < self.message_list.count():
                next_row = current_row + 1
                while next_row in self.play_count_dict:
                    next_row += 1
                self.current_index = next_row
                next_item = self.message_list.item(current_row)
                message_text = next_item.text()
                bus_number = self.extract_bus_number(message_text)
                departure_time = self.extract_departure_time(message_text)
                platform = self.extract_platform(message_text)

                current_label = next_item.data(Qt.UserRole)

                # Воспроизведение аудио с помощью извлеченных данных
                self.play_audio_from_message(next_item, bus_number, departure_time, platform, current_label, current_row, self.current_index)
            else:
                # Если удален последний элемент, устанавливаем индекс в 0
                self.current_index = 0
                print("Индекс равен", self.current_index)
                self.audio_pered_played = False
                self.index_history.clear()



     
   
    def update_time(self):
        # Получение текущего времени и даты
        current_time = QTime.currentTime()
        current_date = QDate.currentDate()

        # Форматирование времени и даты
        formatted_time = current_time.toString("hh:mm:ss")
        formatted_date = current_date.toString("dddd, MMMM d, yyyy")

        # Обновление метки времени и даты в пользовательском интерфейсе
        self.time_label.setText(formatted_time)
        self.date_label.setText(formatted_date)





    def show_confirmation_tab1(self, current_item):
        message_text = current_item.text()
        bus_number = self.extract_bus_number(message_text)
        departure_time = self.extract_departure_time(message_text)
        platform = self.extract_platform(message_text)
        route = self.extract_route(message_text)
        # Получаем сохраненную метку из данных элемента
        label = current_item.data(Qt.UserRole)

        # Получаем сохраненный индекс из данных элемента
        index = self.message_list.row(current_item)

        # Передаем извлеченные значения, метку и индекс в функцию
        self.play_audio_from_message(current_item, bus_number, departure_time, platform, route, label, index)

        # Поиск строки в таблице по номеру автобуса и времени отправления
        row = self.find_row_by_bus_number_and_departure_time(bus_number, departure_time, route)

        # self.record_message_index(message_text, index)
        # Установка цвета фона в зависимости от значения label (если label не равен None) для найденной строки
        if row != -1:
            if label is not None:
                # Установка другого цвета для случаев, когда label не равен None
                self.set_row_background_color(row, QColor(192, 192, 192))


    def show_confirmation_tab2(self, current_item):
        message_text = current_item.text()
        bus_number = self.extract_bus_number(message_text)
        departure_time = self.extract_departure_time(message_text)
        platform = self.extract_platform(message_text)
        route = self.extract_route(message_text)
        # Получаем сохраненную метку из данных элемента
        label = current_item.data(Qt.UserRole)

        # Получаем сохраненный индекс из данных элемента
        index = self.message_list.row(current_item)

        # Передаем извлеченные значения, метку и индекс в функцию
        self.play_audio_from_message_finish(current_item, bus_number, departure_time, platform, route, label, index)

        # Удаляем информацию о записи из множества, так как она была успешно обработана
        self.saved_entries.discard((bus_number, departure_time))

        # Проверяем, нужно ли обновить цвет фона в таблице
        row = self.find_row_by_bus_number_and_departure_time(bus_number, departure_time, route)
        # self.record_message_index(message_text, index)
        if row != -1:
            self.set_row_background_color(row, QColor(192, 192, 192))

    def show_confirmation_tab3(self, current_item):
        message_text = current_item.text()
        bus_number = self.extract_bus_number(message_text)
        departure_time = self.extract_departure_time(message_text)
        platform = self.extract_platform(message_text)
        route = self.extract_route(message_text)
        # Получаем сохраненную метку из данных элемента
        label = current_item.data(Qt.UserRole)

        # Получаем сохраненный индекс из данных элемента
        index = self.message_list.row(current_item)

        # Передаем извлеченные значения, метку и индекс в функцию
        self.play_audio_from_message_otmen(current_item, bus_number, departure_time, platform, route, label, index)
        
        row = self.find_row_by_bus_number_and_departure_time(bus_number, departure_time, route)

        # self.record_message_index(message_text, index)

        if row != -1:
            if label is not None:
                # Установка другого цвета для случаев, когда label не равен None
                self.set_row_background_color(row, QColor(192, 192, 192)) 

    def show_confirmation_tab4(self, current_item):
        message_text = current_item.text()
        bus_number = self.extract_bus_number(message_text)
        departure_time = self.extract_departure_time(message_text)
        platform = self.extract_platform(message_text)
        route = self.extract_route(message_text)
        # Получаем сохраненную метку из данных элемента
        label = current_item.data(Qt.UserRole)

        # Получаем сохраненный индекс из данных элемента
        index = self.message_list.row(current_item)

        # Передаем извлеченные значения, метку и индекс в функцию
        self.play_audio_from_message_zader(current_item, bus_number, departure_time, platform, route, label, index)

        # Добавляем информацию о записи в множество записей, требующих сохранения
        self.saved_entries.add((bus_number, departure_time))
        
        # Проверяем, нужно ли обновить цвет фона в таблице
        row = self.find_row_by_bus_number_and_departure_time(bus_number, departure_time)
        # self.record_message_index(message_text, index)

        if row != -1:
            self.set_row_background_color(row, QColor(192, 192, 192))

    def show_confirmation_tab5(self, current_item):
        message_text = current_item.text()
        bus_number = self.extract_bus_number(message_text)
        departure_time = self.extract_departure_time(message_text)
        platform = self.extract_platform(message_text)
        route = self.extract_route(message_text)  

        # Получаем сохраненную метку из данных элемента
        label = current_item.data(Qt.UserRole)

        # Получаем сохраненный индекс из данных элемента
        index = self.message_list.row(current_item)

        # Передаем извлеченные значения, метку и индекс в функцию
        self.play_audio_from_message_prodolj(current_item, bus_number, departure_time, platform, route, label, index)

        
        row = self.find_row_by_bus_number_and_departure_time(bus_number, departure_time, route)

        if row != -1:
            if label is not None:
                # Установка другого цвета для случаев, когда label не равен None
                self.set_row_background_color(row, QColor(192, 192, 192))




    def update_data(self):
        def update_data_in_background():
            try:

                # Получаем текущее количество строк в таблице
                current_row_count = self.table_left.rowCount()

                # Создаем список для хранения индексов строк, которые нужно удалить
                rows_to_remove = []

                # Проходим по сохраненным записям и восстанавливаем их после обновления данных
                for bus_number, departure_time in self.saved_entries:
                    row = self.find_row_by_bus_number_and_departure_time(bus_number, departure_time)

                    # Проверяем, есть ли уже такая запись в таблице
                    if row == -1:
                        # Если записи нет, добавляем её
                        row = current_row_count
                        self.table_left.insertRow(row)
                        # Здесь вы можете добавить вашу логику получения данных и установки их в таблицу

                    # Обновляем цвет фона для всех записей в множестве
                    self.set_row_background_color(row, QColor(192, 192, 192))

                # Перебираем текущие строки в таблице
                for row in range(current_row_count):
                    # Получаем данные из соответствующей строки
                    bus_number = self.table_left.item(row, 0).text()
                    departure_time = self.table_left.item(row, 2).text()

                    # Проверяем, нужно ли сохранять данную строку
                    if (bus_number, departure_time) not in self.saved_entries:
                        # Добавляем индекс строки в список для удаления, если номер рейса не из списка исключений
                        if bus_number not in ["217", "223", "231", "399", "400", "802", "900", "905", "1337", "8522"]:
                            rows_to_remove.append(row)

                # Удаляем строки из таблицы в обратном порядке (чтобы не нарушить индексы)
                for row in reversed(rows_to_remove):
                    self.table_left.removeRow(row)




                current_time = datetime.now().time()
                data_list_s9880485 = self.get_data(current_time, "s9880485", "571b7974-0b17-4141-8daf-fa1c129beede") #102
                data_list_s9880480 = self.get_data(current_time, "s9880480", "571b7974-0b17-4141-8daf-fa1c129beede") #105 
                data_list_s9880488 = self.get_data(current_time, "s9880488", "571b7974-0b17-4141-8daf-fa1c129beede") #105ж
                data_list_s9880489 = self.get_data(current_time, "s9880489", "571b7974-0b17-4141-8daf-fa1c129beede") #105к
                data_list_s9880491 = self.get_data(current_time, "s9880491", "571b7974-0b17-4141-8daf-fa1c129beede") #119
                data_list_s9880493 = self.get_data(current_time, "s9880493", "571b7974-0b17-4141-8daf-fa1c129beede") #127к
                data_list_s9880490 = self.get_data(current_time, "s9880490", "571b7974-0b17-4141-8daf-fa1c129beede") #127 
                data_list_s9842458 = self.get_data(current_time, "s9842458", "571b7974-0b17-4141-8daf-fa1c129beede") #343 580 680 583 
                data_list_c20143 = self.get_data(current_time, "c20143", "571b7974-0b17-4141-8daf-fa1c129beede") #565 363 564А 555 566
                data_list_c10860 = self.get_data(current_time, "c10860", "571b7974-0b17-4141-8daf-fa1c129beede") #530 503А
                data_list_c22 = self.get_data(current_time, "c22", "571b7974-0b17-4141-8daf-fa1c129beede") #520А 680 566 567А 580 

            
            

                sorted_data_list1 = sorted( data_list_s9880485  + data_list_s9880480 
                + data_list_s9880488 + data_list_s9880489 + data_list_s9880491 + data_list_s9880493 + data_list_s9880490 + data_list_s9842458 + data_list_c20143 + data_list_c10860 + data_list_c22
                
                , key=lambda x: x["departure_time"])


                platform_mapping = {
                    '101': '5',
                    '102': '5',
                    '105': '6',
                    '105ж': '5',
                    '105к': '5',
                    '110': '6',
                    '119': '',
                    '127к': '',
                    '127': '6',
                    '343': '2',
                    '363': '4',
                    '503А': '3',
                    '520А': '3',
                    '530': '3',
                    '555': '4',
                    '564А': '4',
                    '565': '4',
                    '566': '1',
                    '567А': '3',
                    '580': '2',
                    '583': '1',
                    '680': '2',

                }


                for item in sorted_data_list1:
                    # Создаем новую строку в таблице
                    row_position = self.table_left.rowCount()
                    self.table_left.insertRow(row_position)

                    # Устанавливаем данные в соответствующие ячейки
                    self.table_left.setItem(row_position, 0, QTableWidgetItem(item["number"]))
                    self.table_left.setItem(row_position, 1, QTableWidgetItem(item["title"]))
                    self.table_left.setItem(row_position, 2, QTableWidgetItem(item["departure_time"]))
                    self.table_left.setItem(row_position, 4, QTableWidgetItem(item["arrival_time"])) 
                    bus_number = item["number"]
                    platform = platform_mapping.get(bus_number, "N/A")
                    self.table_left.setItem(row_position, 3, QTableWidgetItem(platform))  
                
            
                    # Очищаем таблицу от строк, где в первом столбце значение "566" и во втором столбце значение "Черняховск — Калининград"
                for row in reversed(range(self.table_left.rowCount())):
                    item_1 = self.table_left.item(row, 0)
                    item_2 = self.table_left.item(row, 1)
                    if item_1 is not None and item_2 is not None and item_1.text() == "566" and item_2.text() == "Черняховск — Калининград":
                        self.table_left.removeRow(row)

                for row in reversed(range(self.table_left.rowCount())):
                    item_1 = self.table_left.item(row, 0)
                    item_2 = self.table_left.item(row, 1)
                    if item_1 is not None and item_2 is not None and item_1.text() == "566" and item_2.text() == "Черняховск — Озерск":
                        self.table_left.removeRow(row)
                
                for row in reversed(range(self.table_left.rowCount())):
                    item_1 = self.table_left.item(row, 0)
                    item_2 = self.table_left.item(row, 1)
                    if item_1 is not None and item_2 is not None and item_1.text() == "583" and item_2.text() == "Гусев — Калининград":
                        self.table_left.removeRow(row)

                for row in reversed(range(self.table_left.rowCount())):
                    item_1 = self.table_left.item(row, 0)
                    item_2 = self.table_left.item(row, 1)
                    if item_1 is not None and item_2 is not None and item_1.text() == "583" and item_2.text() == "Черняховск — Пригородное":
                        self.table_left.removeRow(row)

    # Рейс 101
               # Получаем текущую дату и время
                current_datetime = datetime.now()

                # Определяем текущий день недели (0 - понедельник, ..., 6 - воскресенье)
                current_weekday = current_datetime.weekday()

                # Праздничные дни в формате (год, месяц, день)
                holidays = [
                    (current_datetime.year, 1, 1),    # Новый год
                    (current_datetime.year, 1, 7),    # Рождество Христово (православное Рождество)
                    (current_datetime.year, 2, 23),   # День защитника Отечества
                    (current_datetime.year, 3, 8),    # Международный женский день
                    (current_datetime.year, 5, 1),    # Праздник Весны и Труда
                    (current_datetime.year, 5, 9),    # День Победы
                    (current_datetime.year, 6, 12),   # День России
                    (current_datetime.year, 11, 4),   # День народного единства
                ]

                # Проверяем, является ли текущая дата праздничным днем
                is_holiday = (current_datetime.year, current_datetime.month, current_datetime.day) in holidays

                # Путь к файлу JSON на рабочем столе
                desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
                prog_path = os.path.join(desktop_path, "Prog")
                file_path = os.path.join(prog_path, "reis.json")

                # Прочитайте данные из файла JSON
                with open(file_path, 'r', encoding='utf-8') as file:
                    data = json.load(file)

                # Извлеките данные о рейсе 101 из данных JSON
                route_data_101_weekdays = data.get("101 | Черняховск — пос. Покровское")
                route_data_101_weekends_and_holidays = data.get("101 | Черняховск — пос. Покровское (выходные и праздники)")

                # Извлекаем времена отправления для будних дней
                departure_times_101_weekdays = route_data_101_weekdays.get("times", [])

                # Извлекаем времена отправления для выходных и праздников
                departure_times_101_weekends_and_holidays = route_data_101_weekends_and_holidays.get("times", [])

                # Определяем, какие данные использовать в зависимости от типа дня
                if current_weekday < 5 and not is_holiday:
                    departure_times_101_to_use = departure_times_101_weekdays
                else:
                    departure_times_101_to_use = departure_times_101_weekends_and_holidays

                # Добавляем записи только для рейсов, которые не позже текущего времени на 10 часов
                for time in departure_times_101_to_use:
                    # Преобразование строки времени в datetime.time для корректного сравнения
                    departure_datetime = datetime.strptime(time, "%H:%M").time()

                    # Создаем объект datetime с текущей датой и временем
                    current_datetime_with_time = datetime.combine(current_datetime.date(), departure_datetime)

                    # Добавление записей только для рейсов, которые не позже текущего времени на 10 часов
                    if current_datetime.time() <= departure_datetime <= (current_datetime + timedelta(hours=1)).time():
                        # Устанавливаем данные в ячейки
                        row_position = self.table_left.rowCount()
                        self.table_left.insertRow(row_position)
                        self.table_left.setItem(row_position, 0, QTableWidgetItem("101"))
                        self.table_left.setItem(row_position, 1, QTableWidgetItem("Черняховск — пос. Покровское"))
                        self.table_left.setItem(row_position, 2, QTableWidgetItem(time))
                        self.table_left.setItem(row_position, 4, QTableWidgetItem("N/A"))
                        platform = platform_mapping.get("101", "N/A")
                        self.table_left.setItem(row_position, 3, QTableWidgetItem(platform))


     # Рейс 110
          # Путь к файлу JSON на рабочем столе
                desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
                prog_path = os.path.join(desktop_path, "Prog")
                file_path = os.path.join(prog_path, "reis.json")

                # Прочитайте данные из файла JSON
                with open(file_path, 'r', encoding='utf-8') as file:
                    data = json.load(file)

                # Извлеките времена отправления для маршрута "110 | Калининград — Матросово" из данных JSON
                route_data = data.get("110 | Черняховск — пос. Зеленый Бор")
                if route_data:
                    departure_times_110 = route_data.get("times", [])

                    # Получаем текущую дату и время
                    current_datetime = datetime.now()

                    # Добавляем записи только для рейсов, которые не позже текущего времени на 10 часов
                    for time in departure_times_110:
                        # Преобразование строки времени в datetime.time для корректного сравнения
                        departure_datetime = datetime.strptime(time, "%H:%M").time()

                        # Добавление записей только для рейсов, которые не позже текущего времени на 1 час
                        if current_datetime.time() <= departure_datetime <= (current_datetime + timedelta(hours=1)).time():
                            # Устанавливаем данные в ячейки
                            row_position = self.table_left.rowCount()
                            self.table_left.insertRow(row_position)
                            self.table_left.setItem(self.table_left.rowCount() - 1, 0, QTableWidgetItem("110"))
                            self.table_left.setItem(self.table_left.rowCount() - 1, 1, QTableWidgetItem("Черняховск — пос. Зеленый Бор")) 
                            self.table_left.setItem(self.table_left.rowCount() - 1, 2, QTableWidgetItem(time))
                            self.table_left.setItem(self.table_left.rowCount() - 1, 4, QTableWidgetItem("N/A")) 
                            platform = platform_mapping.get("110", "N/A")
                            self.table_left.setItem(self.table_left.rowCount() - 1, 3, QTableWidgetItem(platform))
            
    # Рейс 555 Карамышево — Калининград

                # Очищаем таблицу от рейсов с номером 555 перед добавлением новых записей
                for row in reversed(range(self.table_left.rowCount())):
                    item = self.table_left.item(row, 0)
                    if item is not None and item.text() == "555":
                        self.table_left.removeRow(row)

                # Определяем день недели (0 - понедельник, 1 - вторник, ..., 6 - воскресенье)
                current_day_of_week = datetime.now().weekday()

                # Путь к файлу JSON на рабочем столе
                desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
                prog_path = os.path.join(desktop_path, "Prog")
                file_path = os.path.join(prog_path, "reis.json")

                # Прочитайте данные из файла JSON
                with open(file_path, 'r', encoding='utf-8') as file:
                    data = json.load(file)

                # Извлекаем данные о рейсе 555 из данных JSON
                route_data_555 = None
                route_data_555_ = None

                # Если текущий день недели совпадает с одним из выбранных дней в selected_days,
                if current_day_of_week in data.get("555 | Карамышево — Калининград", {}).get("selected_days", []):
                    route_data_555 = data.get("555 | Карамышево — Калининград")

                # Если текущий день недели совпадает с одним из выбранных дней в selected_days_,
                elif current_day_of_week in data.get("555 | Карамышево — Калининград ", {}).get("selected_days", []):
                    route_data_555_ = data.get("555 | Карамышево — Калининград ")

                # Если данные были найдены, обрабатываем их
                if route_data_555:
                    departure_times = route_data_555.get("times", [])
                    # Добавление записей только для рейсов, которые не позже текущего времени на 10 часов
                    for time in departure_times:
                        current_datetime = datetime.now()  # Получаем текущую дату и время
                        # Преобразование строки времени в datetime.time для корректного сравнения
                        departure_datetime = datetime.strptime(time, "%H:%M").time()
                        if current_datetime.time() <= departure_datetime <= (current_datetime + timedelta(hours=1)).time():
                            # Устанавливаем данные в ячейки
                            row_position = self.table_left.rowCount()
                            self.table_left.insertRow(row_position)
                            self.table_left.setItem(self.table_left.rowCount() - 1, 0, QTableWidgetItem("555"))
                            self.table_left.setItem(self.table_left.rowCount() - 1, 1, QTableWidgetItem("Карамышево — Калининград")) 
                            self.table_left.setItem(self.table_left.rowCount() - 1, 2, QTableWidgetItem(time))
                            self.table_left.setItem(self.table_left.rowCount() - 1, 4, QTableWidgetItem("N/A")) 
                            platform = platform_mapping.get("555", "N/A")
                            self.table_left.setItem(self.table_left.rowCount() - 1, 3, QTableWidgetItem(platform))

                elif route_data_555_:
                    departure_times = route_data_555_.get("times", [])
                    # Добавление записей только для рейсов, которые не позже текущего времени на 10 часов
                    for time in departure_times:
                        current_datetime = datetime.now()  # Получаем текущую дату и время
                        # Преобразование строки времени в datetime.time для корректного сравнения
                        departure_datetime = datetime.strptime(time, "%H:%M").time()
                        if current_datetime.time() <= departure_datetime <= (current_datetime + timedelta(hours=1)).time():
                            # Устанавливаем данные в ячейки
                            row_position = self.table_left.rowCount()
                            self.table_left.insertRow(row_position)
                            self.table_left.setItem(self.table_left.rowCount() - 1, 0, QTableWidgetItem("555"))
                            self.table_left.setItem(self.table_left.rowCount() - 1, 1, QTableWidgetItem("Карамышево — Калининград")) 
                            self.table_left.setItem(self.table_left.rowCount() - 1, 2, QTableWidgetItem(time))
                            self.table_left.setItem(self.table_left.rowCount() - 1, 4, QTableWidgetItem("N/A")) 
                            platform = platform_mapping.get("555", "N/A")
                            self.table_left.setItem(self.table_left.rowCount() - 1, 3, QTableWidgetItem(platform))

            # Рейс 555 Калининград — Карамышево

                # Определяем день недели (0 - понедельник, 1 - вторник, ..., 6 - воскресенье)
                current_day_of_week = datetime.now().weekday()

                # Путь к файлу JSON на рабочем столе
                desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
                prog_path = os.path.join(desktop_path, "Prog")
                file_path = os.path.join(prog_path, "reis.json")

                # Прочитайте данные из файла JSON
                with open(file_path, 'r', encoding='utf-8') as file:
                    data = json.load(file)

                # Извлекаем данные о рейсе 555 из данных JSON
                route_data_555_from = None
                route_data_555_from_ = None

                # Если текущий день недели совпадает с одним из выбранных дней в selected_days,
                if current_day_of_week in data.get("555 | Калининград — Карамышево", {}).get("selected_days", []):
                    route_data_555_from = data.get("555 | Калининград — Карамышево")

                # Если текущий день недели совпадает с одним из выбранных дней в selected_days_,
                elif current_day_of_week in data.get("555 | Калининград — Карамышево ", {}).get("selected_days", []):
                    route_data_555_from_ = data.get("555 | Калининград — Карамышево ")

                # Если данные были найдены, обрабатываем их
                if route_data_555_from:
                    departure_times = route_data_555_from.get("times", [])
                    # Добавление записей только для рейсов, которые не позже текущего времени на 10 часов
                    for time in departure_times:
                        current_datetime = datetime.now()  # Получаем текущую дату и время
                        # Преобразование строки времени в datetime.time для корректного сравнения
                        departure_datetime = datetime.strptime(time, "%H:%M").time()
                        if current_datetime.time() <= departure_datetime <= (current_datetime + timedelta(hours=1)).time():
                            # Устанавливаем данные в ячейки
                            row_position = self.table_left.rowCount()
                            self.table_left.insertRow(row_position)
                            self.table_left.setItem(self.table_left.rowCount() - 1, 0, QTableWidgetItem("555"))
                            self.table_left.setItem(self.table_left.rowCount() - 1, 1, QTableWidgetItem("Калининград — Карамышево")) 
                            self.table_left.setItem(self.table_left.rowCount() - 1, 2, QTableWidgetItem(time))
                            self.table_left.setItem(self.table_left.rowCount() - 1, 4, QTableWidgetItem("N/A")) 
                            platform = platform_mapping.get("555", "N/A")
                            self.table_left.setItem(self.table_left.rowCount() - 1, 3, QTableWidgetItem(platform))

                elif route_data_555_from_:
                    departure_times = route_data_555_from_.get("times", [])
                    # Добавление записей только для рейсов, которые не позже текущего времени на 10 часов
                    for time in departure_times:
                        current_datetime = datetime.now()  # Получаем текущую дату и время
                        # Преобразование строки времени в datetime.time для корректного сравнения
                        departure_datetime = datetime.strptime(time, "%H:%M").time()
                        if current_datetime.time() <= departure_datetime <= (current_datetime + timedelta(hours=1)).time():
                            # Устанавливаем данные в ячейки
                            row_position = self.table_left.rowCount()
                            self.table_left.insertRow(row_position)
                            self.table_left.setItem(self.table_left.rowCount() - 1, 0, QTableWidgetItem("555"))
                            self.table_left.setItem(self.table_left.rowCount() - 1, 1, QTableWidgetItem("Калининград — Карамышево")) 
                            self.table_left.setItem(self.table_left.rowCount() - 1, 2, QTableWidgetItem(time))
                            self.table_left.setItem(self.table_left.rowCount() - 1, 4, QTableWidgetItem("N/A")) 
                            platform = platform_mapping.get("555", "N/A")
                            self.table_left.setItem(self.table_left.rowCount() - 1, 3, QTableWidgetItem(platform))




                # Сортировка таблицы после добавления новых записей
                self.table_left.sortItems(2, QtCore.Qt.AscendingOrder)

                # Удаление дубликатов записей по номеру автобуса, маршруту и времени отправления
                self.remove_duplicate_entries()

                print("Данные успешно обновлены.")
                self.web_view.deleteLater()
                self.table_left.resizeColumnsToContents()
                self.table_left.setColumnWidth(1, 310)

            except requests.RequestException as e:
                print(f"Error fetching data: {e}")

        update_thread = threading.Thread(target=update_data_in_background)
        update_thread.start()



    def remove_duplicate_entries(self):
        unique_entries = set()  # Множество для хранения уникальных записей
        rows_to_remove = []  # Список для хранения индексов строк, которые нужно удалить

        # Итерация по строкам таблицы
        for row in range(self.table_left.rowCount()):
            # Получаем элемент ячейки таблицы
            item = self.table_left.item(row, 0)
            
            # Проверяем, что элемент не None
            if item is not None:
                # Извлекаем данные из элемента ячейки таблицы
                bus_number = item.text()
                title = self.table_left.item(row, 1).text()
                departure_time = self.table_left.item(row, 2).text()

                # Проверка наличия записи в множестве уникальных записей
                entry_key = (bus_number, title, departure_time)

                # Дополнительная проверка для удаления конкретных рейсов
                if bus_number == "680" and (title == "Гусев — Калининград" or title == "Калининград — Гусев"):
                    rows_to_remove.append(row)
                elif entry_key in unique_entries:
                    # Если запись уже существует, добавляем индекс строки для удаления
                    rows_to_remove.append(row)
                else:
                    # Если запись уникальна, добавляем ее ключ в множество уникальных записей
                    unique_entries.add(entry_key)

        # Удаление строк из таблицы в обратном порядке (чтобы не нарушить индексы)
        for row in reversed(rows_to_remove):
            self.table_left.removeRow(row)






    def get_data(self, current_time, destination_code, api_key):
        data_list = []
        max_retries = 3  # Максимальное количество попыток подключения

        # Получаем текущую дату в формате YYYY-MM-DD
        current_date = datetime.now().strftime("%Y-%m-%d")

        # Определяем URL API для первой ссылки
        api_url1 = f"https://api.rasp.yandex.net/v3.0/search/?apikey={api_key}&format=json&from=s9754279&to={destination_code}&lang=ru_RU&date={current_date}"

        # Вызываем функцию для первой ссылки
        data_list += self.process_api_url(api_url1, current_time, max_retries)

        return data_list

  
  

    def process_api_url(self, api_url, current_time, max_retries):
        # Инициализация пустого списка для хранения полученных данных
        data_list = []
        # Инициализация списка, содержащего словарь с URL API и его статусом использования
        unused_api_urls = [{"url": api_url, "used": False}]
        # Инициализация пустого списка для хранения использованных URL API
        used_api_urls = []

        # Цикл, пока есть неиспользованные URL API
        while unused_api_urls:
            # Извлечение первого URL API из списка
            api_info = unused_api_urls.pop(0)
            # Проверка, использован ли уже этот URL API, и, если да, пропуск
            if api_info["used"]:
                continue
            # Извлечение URL API из словаря
            api_url = api_info["url"]
            # Инициализация количества попыток
            retries = 0
            # Повторная попытка получить данные из API, пока не будет достигнуто максимальное количество попыток
            while retries < max_retries:
                try:
                    # Выполнение GET-запроса к URL API
                    response = requests.get(api_url)
                    # Вызов исключения HTTPError для неуспешных ответов
                    response.raise_for_status()
                    # Преобразование ответа в формат JSON
                    data = response.json()

                    # Итерация по каждому сегменту данных
                    for item in data["segments"]:
                        # Извлечение необходимой информации из сегмента
                        bus_number = item["thread"]["number"]
                        departure_time = datetime.strptime(item["departure"], "%Y-%m-%dT%H:%M:%S%z").time()
                        arrival_time = datetime.strptime(item["arrival"], "%Y-%m-%dT%H:%M:%S%z").time()
                        # Расчет разницы во времени между текущим временем и временем отправления
                        time_difference = datetime.combine(datetime.today(), departure_time) - datetime.combine(
                            datetime.today(), current_time)

                        # Проверка, попадает ли разница во времени в указанный диапазон
                        if timedelta(0) <= time_difference <= timedelta(hours=1):
                            # Форматирование времени отправления и прибытия
                            departure_time_formatted = departure_time.strftime("%H:%M")
                            arrival_time_formatted = arrival_time.strftime("%H:%M")
                            # Добавление соответствующих данных в список данных
                            data_list.append({
                                "number": str(bus_number),
                                "title": item["thread"]["short_title"],
                                "departure_time": departure_time_formatted,
                                "arrival_time": arrival_time_formatted,
                            })

                    # Выход из цикла повторных попыток, если получение данных прошло успешно
                    break
                except requests.exceptions.HTTPError as err:
                    # Обработка HTTP-ошибок
                    if err.response.status_code == 504:  # Время ожидания истекло
                        retries += 1
                        # Вывод информации о повторной попытке
                        print(f"Retry {retries} for {api_url}")
                    else:
                        # Вызов исключения, если это не ошибка времени ожидания
                        raise

            # Пометка URL API как использованный
            api_info["used"] = True
            # Добавление использованного URL API в список использованных URL
            used_api_urls.append(api_info)

        # Вывод использованных URL API
        print("Used API URLs:", used_api_urls)

        # Возврат списка полученных данных
        return data_list





    def handle_platform_button_click(self):
        sender = self.sender()
        platform_number = int(sender.text())

        # Получаем выделенный элемент в виджете сообщений
        selected_item = self.message_list.currentItem()

        if selected_item:
            # Получаем текст из выделенного элемента
            selected_text = selected_item.text()

            # Пытаемся извлечь номер автобуса из текста сообщения
            bus_number = self.extract_bus_number(selected_text)

            if bus_number:
                # Заменяем номер платформы на значение из кнопки
                updated_message_text = self.replace_platform_number(platform_number, selected_text)

                # Обновляем текст в выделенном элементе
                selected_item.setText(updated_message_text)
        else:
            # Если ничего не выделено, изменяем в последнем сообщении
            self.update_last_message_platform(platform_number)

    def update_last_message_platform(self, new_number):
        if self.message_list.count() > 0:
            # Получаем последний элемент в списке сообщений
            last_item = self.message_list.item(self.message_list.count() - 1)

            if last_item:
                # Получаем текст из последнего элемента
                last_text = last_item.text()

                # Заменяем номер платформы на значение из кнопки
                updated_last_text = self.replace_platform_number(new_number, last_text)

                # Обновляем текст в последнем элементе
                last_item.setText(updated_last_text)

    def replace_platform_number(self, new_number, text):
        # Разбиваем текст на части, используя разделитель |
        parts = text.split(' | ')

        if len(parts) >= 4:
            # Заменяем четвертую часть (платформу) на новое значение
            parts[3] = f'{new_number}'

            # Собираем текст обратно
            updated_text = ' | '.join(parts)
            return updated_text

        return text


    def closeEvent(self, event):
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle('Подтверждение закрытия')
        msg_box.setText("Вы уверены, что хотите закрыть программу?")
        msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg_box.setDefaultButton(QMessageBox.No)

        # Устанавливаем текст кнопок
        yes_button = msg_box.button(QMessageBox.Yes)
        yes_button.setText("Подтвердить")
        self.setStyleSheetForMessageBox(yes_button)

        no_button = msg_box.button(QMessageBox.No)
        no_button.setText("Отмена")
        self.setStyleSheetForMessageBox(no_button)

        reply = msg_box.exec_()
        if reply == QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()
    
    def setStyleSheetForMessageBox(self, button):
        button.setStyleSheet("""
            QPushButton {
                height: 2.5em;
                width: 90px;
                border-radius: 3px;
                letter-spacing: 1px;
                background-color: #FFFFFF; /* Adjust color as needed */
                color: #000000; /* Adjust color as needed */
                border: 1px solid #CCCCCC; /* Adjust color as needed */
            }
            
            QPushButton:hover {
                background-color: #F0F0F0; /* Adjust color as needed */
                border-color: #BBBBBB; /* Adjust color as needed */
            }
        """)


    def load_saved_text(self):
        desktop_path = QStandardPaths.writableLocation(QStandardPaths.DesktopLocation)
        prog_path = os.path.join(desktop_path, 'Prog')
        file_path = os.path.join(prog_path, 'reis.json')
        try:
            with open(file_path, 'r') as file:
                data = json.load(file)
                print("Data loaded successfully:", data)  # Добавлено для отладки
                saved_text1 = data.get('text1', '')
                saved_text2 = data.get('text2', '')
                self.text_field1.setText(saved_text1)
                self.text_field2.setText(saved_text2)
                selected_days = data.get('selected_days', [])
                for idx in selected_days:
                    self.days_checkboxes[idx].setChecked(True)
        except FileNotFoundError:
            pass



    def save_text(self):
        # Получаем текст из полей ввода
        text1 = self.text_field1.text()
        text2 = self.text_field2.text()

        # Проверяем, пусты ли компоненты
        if not text1 or not text2 or not any(checkbox.isChecked() for checkbox in self.days_checkboxes):
            QMessageBox.warning(self, "Ошибка сохранения", "Выберите маршрут")
            return

        # Подготавливаем данные для сохранения
        selected_days = [idx for idx, checkbox in enumerate(self.days_checkboxes) if checkbox.isChecked()]
        data = {'times': text2.split(', '), 'selected_days': selected_days}

        desktop_path = QStandardPaths.writableLocation(QStandardPaths.DesktopLocation)
        prog_path = os.path.join(desktop_path, 'Prog')
        # Создаем путь к файлу в папке "Prog"
        file_path = os.path.join(prog_path, 'reis.json')

        # Загружаем существующие данные, если они есть
        try:
            with open(file_path, 'r') as file:
                existing_data = json.load(file)
        except FileNotFoundError:
            existing_data = {}

        # Обновляем данные для существующего ключа или создаем новую запись
        existing_data[text1] = data

        # Сохраняем обновленные данные в файл
        with open(file_path, 'w') as file:
            json.dump(existing_data, file, indent=4)

        # Обновляем таблицу
        self.update_table(existing_data)

        # Очищаем чекбоксы
        for checkbox in self.days_checkboxes:
            checkbox.setChecked(False)

        # Очищаем текстовые поля
        self.text_field1.clear()
        self.text_field2.clear()
        self.text_field3.clear()

        QMessageBox.information(self, "Успешное сохранение", "Значения успешно сохранены")


    def update_table(self, data):
        day_of_week_mapping = {
            0: "Понедельник",
            1: "Вторник",
            2: "Среда",
            3: "Четверг",
            4: "Пятница",
            5: "Суббота",
            6: "Воскресенье"
        }

        # Очистим текущие данные в таблице
        self.table_routes.clearContents()

        # Установим количество строк в таблице
        self.table_routes.setRowCount(len(data))

        # Обновим данные в таблице
        for row, (route, info) in enumerate(data.items()):
            route_item = QTableWidgetItem(route)
            self.table_routes.setItem(row, 0, route_item)
            
            # Получаем список времен отправления из ключа "times"
            times = info.get("times", [])
            time_item = QTableWidgetItem(", ".join(times))
            self.table_routes.setItem(row, 1, time_item)

            # Получаем список дней недели из ключа "selected_days" и преобразуем их в дни недели
            selected_days = info.get("selected_days", [])
            days_of_week = [day_of_week_mapping[day] for day in selected_days]

            # Заполняем третью колонку днями недели
            days_item = QTableWidgetItem(", ".join(days_of_week))
            self.table_routes.setItem(row, 2, days_item)



    def update_text_field3(self):
        selected_days = [checkbox.text() for checkbox in self.days_checkboxes if checkbox.isChecked()]
        self.text_field3.setText(', '.join(selected_days))


    def set_table_properties(self):
        # Устанавливаем режим выделения на FullRowSelection
        self.table_routes.setSelectionBehavior(QAbstractItemView.SelectRows)
        # Устанавливаем выделение только по одной строке за раз
        self.table_routes.setSelectionMode(QAbstractItemView.SingleSelection)
        # Подключение сигнала двойного клика к обработчику
        self.table_routes.doubleClicked.connect(self.handle_double_click_tab3)

    def handle_double_click_tab3(self, index):
        # Получение выбранной строки
        row = index.row()
        # Получение значения маршрута и времени из выбранной строки
        route = self.table_routes.item(row, 0).text()
        time = self.table_routes.item(row, 1).text()
        days = self.table_routes.item(row, 2).text()  # Получение значения дней недели
        # Установка значений в текстовые поля
        self.text_field1.setText(route)
        self.text_field2.setText(time)
        self.text_field3.setText(days)  # Установка значений дней недели в третье текстовое поле
        # Устанавливаем состояние чекбоксов на основе значения из третьего поля
        selected_days = [day.strip() for day in days.split(',')]
        for idx, day in enumerate(['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье']):
            self.days_checkboxes[idx].setChecked(day in selected_days)
    


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MyWindow()
    window.show()
    sys.exit(app.exec_())
    
