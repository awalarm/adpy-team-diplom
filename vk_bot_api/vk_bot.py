from random import randrange
import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
import time

from config import token_vk


def get_start_keyboard():
    """Стартовая клавиатура"""
    keyboard = VkKeyboard(one_time=True)
    keyboard.add_button("Начать поиск", color=VkKeyboardColor.PRIMARY)
    return keyboard.get_keyboard()


def get_main_keyboard():
    """Клавиатура Главное меню"""
    keyboard = VkKeyboard(one_time=False)
    keyboard.add_button("👀 Смотреть анкеты", color=VkKeyboardColor.PRIMARY)
    keyboard.add_line()
    keyboard.add_button("❤️ Мои фавориты", color=VkKeyboardColor.POSITIVE)
    keyboard.add_button("🚫 Черный список", color=VkKeyboardColor.NEGATIVE)
    keyboard.add_line()
    keyboard.add_button("️⚙️ Настроить параметры поиска", color=VkKeyboardColor.SECONDARY)
    return keyboard.get_keyboard()


def get_profiles_keyboard():
    """Клавиатура работа с кандидатами (найденные пользователи вк)"""
    keyboard = VkKeyboard(one_time=False)
    keyboard.add_button("❤️ Нравится", color=VkKeyboardColor.POSITIVE)
    keyboard.add_button("🚫 В черный список", color=VkKeyboardColor.NEGATIVE)
    keyboard.add_button("➡️ Следующий", color=VkKeyboardColor.PRIMARY)
    keyboard.add_line()
    keyboard.add_button("📋 Информация о поиске", color=VkKeyboardColor.SECONDARY)
    keyboard.add_button("Назад", color=VkKeyboardColor.NEGATIVE)
    return keyboard.get_keyboard()


def get_favorites_keyboard():
    """Клавиатура фаворитов"""
    keyboard = VkKeyboard(one_time=False)
    keyboard.add_button("➡️ Следующий фаворит", color=VkKeyboardColor.PRIMARY)
    keyboard.add_button("🗑️ Удалить фаворита", color=VkKeyboardColor.NEGATIVE)
    keyboard.add_line()
    keyboard.add_button("📋 Главное меню", color=VkKeyboardColor.SECONDARY)
    return keyboard.get_keyboard()


def get_blacklist_keyboard():
    """Клавиатура черного списка"""
    keyboard = VkKeyboard(one_time=False)
    keyboard.add_button("➡️ Следующий в ЧС", color=VkKeyboardColor.PRIMARY)
    keyboard.add_button("🗑️ Удалить из ЧС", color=VkKeyboardColor.NEGATIVE)
    keyboard.add_line()
    keyboard.add_button("📋 Главное меню", color=VkKeyboardColor.SECONDARY)
    return keyboard.get_keyboard()


def write_msg(user_id, message, keyboard=None, attachment=None):
    """метод отправляет сообщение пользователю ВКонтакте через VK API"""
    local_vk_session = vk_api.VkApi(token=token_vk)
    local_vk = local_vk_session.get_api()

    params = {
        "user_id": user_id,
        "message": message,
        "random_id": randrange(10 ** 7),
    }
    if keyboard:
        params["keyboard"] = keyboard
    if attachment:
        params["attachment"] = attachment

    local_vk.messages.send(**params)


def show_candidate(user_id, candidate_data=None):
    """поиск кандидатов"""
    if not candidate_data:
        write_msg(
            user_id,
            "🔄 Ищу новых кандидатов... Ожидайте🔄",
            get_profiles_keyboard(),
        )
        write_msg(
            user_id,
            "👤 Кандидат (тестовый)\n\n"
            "📋 Информация:\n"
            "• Имя: Тестовый Кандидат\n"
            "• Ссылка: https://vk.com/id1\n\n"
            "💡 Выберите действие:",
            get_profiles_keyboard(),
        )
    else:
        write_msg(
            user_id,
            f"👤 Кандидат\n\n"
            f"📋 Информация:\n"
            f"• Имя: {candidate_data['first_name']} "
            f"{candidate_data['last_name']}\n"
            f"• Ссылка: {candidate_data['profile_link']}\n\n"
            f"💡 Выберите действие:",
            get_profiles_keyboard(),
        )


def show_favorite(user_id, favorite_data=None):
    """работа с Фаворитами"""
    if not favorite_data:
        write_msg(
            user_id,
            "🎉 Вы просмотрели всех фаворитов!\nНачните заново.",
            get_main_keyboard(),
        )
    else:
        write_msg(
            user_id,
            f"❤️ Фаворит\n\n"
            f"📋 Информация:\n"
            f"• Имя: {favorite_data['first_name']} "
            f"{favorite_data['last_name']}\n"
            f"• Ссылка: {favorite_data['profile_link']}\n\n"
            f"💡 Выберите действие:",
            get_favorites_keyboard(),
        )


def show_blacklist(user_id, blacklist_data=None):
    """работа с черным списком"""
    if not blacklist_data:
        write_msg(
            user_id,
            "🎉 Вы просмотрели всех в черном списке!\nНачните заново.",
            get_main_keyboard(),
        )
    else:
        write_msg(
            user_id,
            f"🚫 Черный список\n\n"
            f"📋 Информация:\n"
            f"• Имя: {blacklist_data['first_name']} "
            f"{blacklist_data['last_name']}\n"
            f"• Ссылка: {blacklist_data['profile_link']}\n\n"
            f"💡 Выберите действие:",
            get_blacklist_keyboard(),
        )


def show_current_settings(user_id):
    message = (
        "⚙️ Текущие параметры поиска:\n\n"
        "• Возраст: 25 лет\n"
        "• Пол: Мужской\n"
        "• Город: Москва\n\n"
        "\n\n"
        "1. Возраст\n"
        "2. Пол\n"
        "3. Город\n"
        "4. Отмена"
    )
    write_msg(user_id, message)


def run_bot():
    print("Бот запущен и ожидает сообщений...")

    # Определяем приветственное сообщение как переменную для повторного использования
    welcome_message = (
        "👋 Я — бот для знакомств «Conspicere» - Взаимный взгляд.\n"
        "📋 Что я умею:\n"
        "• Искать людей по возрасту, городу и полу\n"
        "• Показывать фото профиля\n"
        "• Сохранять понравившихся в избранное\n"
        "• Вести черный список\n\n"
        "Нажмите '👀 Смотреть анкеты'"
    )

    temp_user_data = {}
    edit_user_data = {}

    while True:
        vk_session = vk_api.VkApi(token=token_vk)
        longpoll = VkLongPoll(vk_session, wait=25)
        events = longpoll.check()

        for event in events:
            if event.type == VkEventType.MESSAGE_NEW and event.to_me:
                user_id = event.user_id
                text = event.text

                print(f"Получено сообщение от {user_id}: '{text}'")

                # Приветствие (используем welcome_message)
                if text.lower() in ["привет", "старт", "начать", "start", "👋"]:
                    write_msg(user_id, welcome_message, get_main_keyboard())

                elif text == "Начать поиск" or text.lower() == "поиск":
                    write_msg(
                        user_id,
                        "✅ Настройки поиска!\nВведите возраст кандидата (например: 25):",
                    )
                    temp_user_data[user_id] = {}

                elif text == "👀 Смотреть анкеты" or "смотреть анкеты" in text.lower():
                    show_candidate(user_id)

                elif text == "❤️ Нравится" or "нравится" in text.lower():
                    write_msg(user_id, "✅ Добавлено в избранное!", get_profiles_keyboard())
                    show_candidate(user_id)

                elif text == "🚫 В черный список" or "в черный список" in text.lower():
                    write_msg(user_id, "✅ Добавлено в черный список!", get_profiles_keyboard())
                    show_candidate(user_id)

                elif text == "❤️ Мои фавориты" or "мои фавориты" in text.lower():
                    write_msg(
                        user_id,
                        "❤️ У вас 5 фаворитов\n\nВыберите действие:",
                        get_favorites_keyboard(),
                    )
                    show_favorite(user_id, {"first_name": "Тестовый", "last_name": "Фаворит",
                                            "profile_link": "https://vk.com/id2"})

                elif text == "🚫 Черный список" or "черный список" in text.lower():
                    write_msg(
                        user_id,
                        "🚫 В черном списке: 3 \n\nВыберите действие:",
                        get_blacklist_keyboard(),
                    )
                    show_blacklist(user_id, {"first_name": "Тестовый", "last_name": "Черный список",
                                             "profile_link": "https://vk.com/id3"})

                elif "настроить" in text.lower() or "⚙️" in text:
                    edit_user_data[user_id] = {"step": "show_settings"}
                    show_current_settings(user_id)

                elif user_id in temp_user_data and "age" not in temp_user_data[user_id]:
                    if text.isdigit() and 18 <= int(text) <= 100:
                        temp_user_data[user_id]["age"] = int(text)
                        write_msg(user_id, "Введите город:")
                    else:
                        write_msg(user_id, "Введите возраст 18-100:")

                elif (user_id in temp_user_data and "age" in temp_user_data[user_id] and
                      "city" not in temp_user_data[user_id]):
                    temp_user_data[user_id]["city"] = text
                    write_msg(user_id, "Введите пол (1-женский, 2-мужской):")

                elif (user_id in temp_user_data and "age" in temp_user_data[user_id] and
                      "city" in temp_user_data[user_id]):
                    if text in ["1", "2"]:
                        gender_text = 'Мужской' if text == "2" else 'Женский'
                        write_msg(
                            user_id,
                            f"✅ Параметры поиска введены!\n"
                            f"Возраст: {temp_user_data[user_id]['age']} лет\n"
                            f"Город: {temp_user_data[user_id]['city']}\n"
                            f"Пол: {gender_text}\n\n"
                            f"Нажмите '👀 Смотреть анкеты'",
                            get_main_keyboard(),
                        )
                        del temp_user_data[user_id]
                    else:
                        write_msg(user_id, "Введите 1 или 2:")

                elif user_id in edit_user_data and edit_user_data[user_id]["step"] == "show_settings":
                    if text == "1" or "возраст" in text.lower():
                        edit_user_data[user_id] = {"step": "edit_age"}
                        write_msg(user_id, "Введите новый возраст кандидата (например: 25):")
                    elif text == "2" or "пол" in text.lower():
                        edit_user_data[user_id] = {"step": "edit_gender"}
                        write_msg(user_id, "Введите новый пол (1-женский, 2-мужской):")
                    elif text == "3" or "город" in text.lower():
                        edit_user_data[user_id] = {"step": "edit_city"}
                        write_msg(user_id, "Введите новый город:")
                    elif text == "4" or "отмена" in text.lower():
                        del edit_user_data[user_id]
                        # ЗАМЕНА: вместо "Изменения отменены." выводим welcome_message
                        write_msg(user_id, welcome_message, get_main_keyboard())
                    else:
                        write_msg(user_id, "Выберите параметр для изменения (1-4):")

                elif user_id in edit_user_data and edit_user_data[user_id]["step"] == "edit_age":
                    if text.isdigit() and 18 <= int(text) <= 100:
                        write_msg(
                            user_id,
                            f"✅ Возраст обновлен на {text} лет!\n\n"
                            f"Новые параметры поиска:\n"
                            f"• Возраст: {text} лет\n"
                            f"• Пол: Мужской\n"
                            f"• Город: Москва",
                            get_main_keyboard(),
                        )
                        del edit_user_data[user_id]
                    else:
                        write_msg(user_id, "Введите возраст 18-100:")

                elif user_id in edit_user_data and edit_user_data[user_id]["step"] == "edit_gender":
                    if text in ["1", "2"]:
                        gender_text = 'женский' if text == '1' else 'мужской'
                        write_msg(
                            user_id,
                            f"✅ Пол обновлен на {gender_text}!\n\n"
                            f"Новые параметры поиска:\n"
                            f"• Возраст: 25 лет\n"
                            f"• Пол: {'Женский' if text == '1' else 'Мужской'}\n"
                            f"• Город: Москва",
                            get_main_keyboard(),
                        )
                        del edit_user_data[user_id]
                    else:
                        write_msg(user_id, "Введите 1 или 2:")

                elif user_id in edit_user_data and edit_user_data[user_id]["step"] == "edit_city":
                    write_msg(
                        user_id,
                        f"✅ Город обновлен на {text}!\n\n"
                        f"Новые параметры поиска:\n"
                        f"• Возраст: 25 лет\n"
                        f"• Пол: Мужской\n"
                        f"• Город: {text}",
                        get_main_keyboard(),
                    )
                    del edit_user_data[user_id]

                elif "следующий" in text.lower() and text != "➡️ Следующий фаворит" and text != "➡️ Следующий в ЧС":
                    show_candidate(user_id)

                elif "следующий фаворит" in text.lower():
                    show_favorite(user_id, {"first_name": "Следующий", "last_name": "Фаворит",
                                            "profile_link": "https://vk.com/id4"})

                elif "удалить фаворита" in text.lower():
                    write_msg(user_id, "🗑️ Фаворит удален!", get_favorites_keyboard())
                    show_favorite(user_id)

                elif "следующий в чс" in text.lower():
                    show_blacklist(user_id, {"first_name": "Следующий", "last_name": "Черный список",
                                             "profile_link": "https://vk.com/id5"})

                elif "удалить из чс" in text.lower():
                    write_msg(user_id, "🗑️ Удалено из черного списка!", get_blacklist_keyboard())
                    show_blacklist(user_id)

                elif "главное меню" in text.lower():
                    if user_id in temp_user_data:
                        del temp_user_data[user_id]
                    if user_id in edit_user_data:
                        del edit_user_data[user_id]
                    # ЗАМЕНА: вместо "Главное меню" выводим welcome_message
                    write_msg(user_id, welcome_message, get_main_keyboard())

                elif text.lower() == "назад":
                    if user_id in temp_user_data:
                        del temp_user_data[user_id]
                    if user_id in edit_user_data:
                        del edit_user_data[user_id]
                    # ЗАМЕНА: выводим welcome_message
                    write_msg(user_id, welcome_message, get_main_keyboard())

                elif "информация" in text.lower():
                    message = (
                        "📋 Статистика:\n"
                        "• Непросмотренных кандидатов: 10\n"
                        "• В избранном: 5\n"
                        "• В черном списке: 3\n\n"
                        "📊 Параметры поиска:\n"
                        "• Возраст: 25 лет\n"
                        "• Пол: Мужской\n"
                        "• Город: Москва"
                    )
                    write_msg(user_id, message, get_profiles_keyboard())

                else:
                    if user_id in temp_user_data or user_id in edit_user_data:
                        write_msg(user_id, "Завершите регистрацию/редактирование или введите 'отмена'")
                    else:
                        # ЗАМЕНА: вместо "Не понял. Нажмите 'Начать поиск'" выводим welcome_message
                        write_msg(user_id, welcome_message, get_main_keyboard())

        time.sleep(0.1)
