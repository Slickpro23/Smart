import telebot
from telebot import types
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os

# Настройка доступа к Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name('key2.json', scope)
client = gspread.authorize(creds)
# Открываем таблицу по ссылке
spreadsheet_url = 'https://docs.google.com/spreadsheets/d/1F6C-bORTL2iD6Gt5VtpA2oyxYa8ObNMKz2ECxRr7hs8'
spreadsheet = client.open_by_url(spreadsheet_url)
# Выводим все названия листов для проверки
worksheets = spreadsheet.worksheets()
print("Доступные листы:")
for sheet in worksheets:
    print(sheet.title)
# Выбираем лист "Настройки"
settings_sheet = spreadsheet.worksheet('Настройки')
# Выбираем лист "База"
base_sheet = spreadsheet.worksheet('БАЗА')  # Убедитесь, что название листа "База" корректно
# Извлекаем данные из указанных диапазонов
coaches = settings_sheet.get('G2:G24')
lessons = settings_sheet.get('H2:H10')
times = settings_sheet.get('I2:I14')
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

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Привет! Используйте команду /check для начала.")

@bot.message_handler(commands=['check'])
def check(message):
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

@bot.callback_query_handler(func=lambda call: call.data.startswith('lesson_'))
def select_lesson(call):
    data = call.data.split('_')
    selected_coach = data[1]
    selected_lesson = data[2]
    bot.send_message(call.message.chat.id, f'Вы выбрали {selected_lesson}. Теперь выберите время:')
    markup = types.InlineKeyboardMarkup()
    row = []  # Создаем временный список для кнопок в одной строке

    for time in times:
        button = types.InlineKeyboardButton(time, callback_data=f'time_{selected_coach}_{selected_lesson}_{time}')
        row.append(button)  # Добавляем кнопку в текущую строку
        if len(row) == 2:
            markup.row(*row)  # Добавляем текущую строку в клавиатуру
            row = []  # Очищаем список для следующей строки
    if row:
        markup.row(*row)

    bot.send_message(call.message.chat.id, 'Выберите время:', reply_markup=markup)

user_files = {}


@bot.callback_query_handler(func=lambda call: call.data.startswith('time_'))
def select_time(call):
    data = call.data.split('_')
    selected_coach = data[1]
    selected_lesson = data[2]
    selected_time = data[3]

    # Инициализация данных файлов пользователя
    user_files[call.message.chat.id] = {
        'coach': selected_coach,
        'lesson': selected_lesson,
        'time': selected_time,
        'file_names': []
    }

    bot.send_message(call.message.chat.id, "Пожалуйста, отправьте мне файлы.")
    bot.register_next_step_handler(call.message, handle_files)


def handle_files(message):
    chat_id = message.chat.id

    if chat_id not in user_files:
        bot.send_message(chat_id, "Сессия завершена. Пожалуйста, начните снова.")
        return

    # Проверяем, если сообщение содержит документы
    if message.content_type == 'document':
        add_file_name(chat_id, message.document.file_name)

    # Если сообщение содержит фото
    elif message.content_type == 'photo':
        for photo in message.photo:
            file_info = bot.get_file(photo.file_id)
            file_name = file_info.file_path.split('/')[-1]
            add_file_name(chat_id, file_name)

    # Проверка на завершение загрузки файлов
    if len(user_files[chat_id]['file_names']) < 1:
        bot.send_message(chat_id, "Вы можете отправить еще файлы или завершить процесс.")
        bot.register_next_step_handler(message, handle_files)  # Продолжаем ожидать файлы
    else:
        write_files_to_sheet(chat_id)


def add_file_name(chat_id, file_name):
    file_name_without_extension = os.path.splitext(os.path.basename(file_name))[0]

    if file_name_without_extension not in user_files[chat_id]['file_names']:
        user_files[chat_id]['file_names'].append(file_name_without_extension)
        bot.send_message(chat_id, f'Имя файла {file_name_without_extension} добавлено в список!')
    else:
        bot.send_message(chat_id,
                         f'Файл с именем {file_name_without_extension} уже существует в списке и не будет добавлен.')


def write_files_to_sheet(chat_id):
    try:
        # Предполагаем, что base_sheet уже определен и подключен к вашим Google Sheets
        for file_name in user_files[chat_id]['file_names']:
            base_sheet.append_row(
                [user_files[chat_id]['coach'], user_files[chat_id]['lesson'], user_files[chat_id]['time'], file_name]
            )

        # Формируем список имен файлов для отправки
        files_list = "\n".join(user_files[chat_id]['file_names'])
        bot.send_message(chat_id, f"Все имена файлов записаны в таблицу:\n{files_list}")

        # Очистка данных пользователя после обработки
        del user_files[chat_id]
    except Exception as e:
        bot.send_message(chat_id, "Произошла ошибка при записи в таблицу.")
        print(f"Error: {e}")


# Запуск опроса бота
bot.polling(none_stop=True)
