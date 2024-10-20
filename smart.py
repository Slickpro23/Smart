import telebot
from telebot import types
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import threading
from datetime import datetime

# Настройка доступа к Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name('key2.json', scope)
client = gspread.authorize(creds)

# Открываем таблицу по ссылке для смартов
spreadsheet_smart_url = 'https://docs.google.com/spreadsheets/d/1F6C-bORTL2iD6Gt5VtpA2oyxYa8ObNMKz2ECxRr7hs8'
spreadsheet_smart = client.open_by_url(spreadsheet_smart_url)

# Выводим все названия листов для проверки
worksheets = spreadsheet_smart.worksheets()
print("Доступные листы:")
for sheet in worksheets:
    print(sheet.title)


# Выбираем лист "Настройки"
settings_sheet = spreadsheet_smart.worksheet('Настройки')
# Выбираем лист "База"

base_sheet = spreadsheet_smart.worksheet('БАЗА')  # Убедитесь, что название листа "База" корректно

# Извлекаем данные из указанных диапазонов
coaches = settings_sheet.get('A2:A40')
lessons = settings_sheet.get('B2:B40')
times = settings_sheet.get('C2:C40')

# Преобразуем списки из формата (значение,) в обычные списки
coaches = [coach[0] for coach in coaches if coach]  # Убираем пустые значения
lessons = [lesson[0] for lesson in lessons if lesson]
times = [time[0] for time in times if time]

# Вывод результатов в консоль (можно убрать в рабочей версии)
print("Список тренеров:", coaches)
print("Список уроков:", lessons)
print("Список времени:", times)

# Вставьте ваш токен
TOKEN = '7964714160:AAF9hsG4e_gheqNIWgmCTeSBY5aMNIgHcv8'  # Замените на ваш токен
bot = telebot.TeleBot(TOKEN)

# Global variable to hold the timer
response_timer = None
lesson_timer = None

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Привет! Используйте команду /check для начала.")

@bot.message_handler(commands=['check'])
def check(message):
    # Проверяем, из какого чата пришла команда
    if message.chat.type == 'private':
        markup = types.InlineKeyboardMarkup()
        row = []  # Создаем временный список для кнопок в одной строке

        for i, coach in enumerate(coaches):
            button = types.InlineKeyboardButton(coach, callback_data=f'coach_{coach}')
            row.append(button)  # Добавляем кнопку в текущую строку

            # Если мы добавили 2 кнопки, добавляем строку в клавиатуру и очищаем row
            if (i + 1) % 2 == 0:
                markup.row(*row)  # Добавляем текущую строку в клавиатуру
                row = []  # Очищаем список для следующей строки

        # Если осталась одна кнопка в row, добавляем ее
        if row:
            markup.row(*row)

        bot.send_message(message.chat.id, 'Выберите тренера:', reply_markup=markup)
    else:
        # Если команда вызвана из группы
        bot.send_message(message.chat.id, "Эта команда не работает в группе. Напишите мне в личку @Check_Smart_bot команду /check. чтобы отметить посетителей на смарт старт")

@bot.callback_query_handler(func=lambda call: call.data.startswith('coach_'))
def select_coach(call):
    selected_coach = call.data.split('_')[1]
    bot.send_message(call.message.chat.id, f'Вы выбрали {selected_coach}. Теперь выберите урок:')
    markup = types.InlineKeyboardMarkup()
    row = []  # Создаем временный список для кнопок в одной строке

    for lesson in lessons:
        button = types.InlineKeyboardButton(lesson, callback_data=f'lesson_{selected_coach}_{lesson}')
        row.append(button)  # Добавляем кнопку в текущую строку

        # Если мы добавили 2 кнопки, добавляем строку в клавиатуру и очищаем row
        if len(row) == 2:
            markup.row(*row)  # Добавляем текущую строку в клавиатуру
            row = []  # Очищаем список для следующей строки

    # Если осталась одна кнопка в row, добавляем ее
    if row:
        markup.row(*row)

    bot.send_message(call.message.chat.id, 'Выберите урок:', reply_markup=markup)


# Callback handler to select lesson
@bot.callback_query_handler(func=lambda call: call.data.startswith('lesson_'))
def select_lesson(call):
    global lesson_timer
    data = call.data.split('_')
    selected_coach = data[1]
    selected_lesson = data[2]

    bot.send_message(call.message.chat.id, f'Вы выбрали {selected_lesson}. Теперь выберите время:')

    markup = types.InlineKeyboardMarkup()
    row = []  # Temporary list for buttons in one row

    for time in times:
        button = types.InlineKeyboardButton(time, callback_data=f'time_{selected_coach}_{selected_lesson}_{time}')
        row.append(button)  # Add button to the current row
        if len(row) == 2:
            markup.row(*row)  # Add the current row to the keyboard
            row = []  # Clear the list for the next row
    if row:
        markup.row(*row)

    bot.send_message(call.message.chat.id, 'Выберите время:', reply_markup=markup)

    # Start the timer for 60 seconds
    lesson_timer = threading.Timer(60.0, timeout_response, args=(call.message.chat.id,))
    lesson_timer.start()


# Timeout response function
def timeout_response(chat_id):
    bot.send_message(chat_id, "Время ожидания истекло. Пожалуйста, попробуйте снова.")


@bot.callback_query_handler(func=lambda call: call.data.startswith('time_'))
def select_time(call):
    global response_timer
    data = call.data.split('_')
    selected_coach = data[1]
    selected_lesson = data[2]
    selected_time = data[3]

    # Запрашиваем количество посетителей
    bot.send_message(call.message.chat.id, "Сколько посетителей пришло на урок?")

    # Start the timer for 60 seconds
    response_timer = threading.Timer(60.0, timeout_response, args=(call.message.chat.id,))
    response_timer.start()

    bot.register_next_step_handler(call.message, record_visitors, selected_coach, selected_lesson, selected_time)


def timeout_response(chat_id):
    # Inform the user that the timeout has occurred
    bot.send_message(chat_id, "Время ожидания ответа истекло. Пожалуйста, попробуйте снова.")


def record_visitors(message, selected_coach, selected_lesson, selected_time):
    global response_timer
    # Cancel the timer since we received a response
    if response_timer is not None:
        response_timer.cancel()

    try:
        # Пытаемся преобразовать ответ в число
        number_of_visitors = int(message.text)

        # Получаем текущую дату и время
        current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Записываем данные в таблицу
        base_sheet.append_row([selected_coach, selected_lesson, selected_time, number_of_visitors, current_datetime])

        # Формируем ответ пользователю
        response_message = f'Вы записали на урок "{selected_lesson}" в "{selected_time}"\n - {number_of_visitors} посетителей к тренеру "{selected_coach}"'
        bot.send_message(message.chat.id, response_message)

        # Получаем никнейм пользователя
        user_nickname = message.from_user.username or "Никнейм не указан"

        # Формируем ответ в группу с никнеймом пользователя
        response_message = f'Тренер @{user_nickname} на урок "{selected_lesson}" в "{selected_time}" \n отметил(ла) {number_of_visitors} посетителей.'
        bot.send_message(-1002175539293, response_message)

    except ValueError:
        # Если произошла ошибка преобразования, сообщаем об этом пользователю
        bot.send_message(message.chat.id, "Пожалуйста, введите корректное число посетителей.")


# Start polling
bot.polling(none_stop=True)
