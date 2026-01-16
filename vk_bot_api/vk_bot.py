from random import randrange
import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
import time
import requests
import sys

from vk_bot_api.tokens import token_vk, ACCESS_TOKEN_VK
from vk_bot_api.city_id import get_city_id
from vk_bot_api.vk_people import search_vk_users
from vk_bot_api.vk_photos import get_candidate_photos

# from database.adapter import DatabaseAdapter
from database.db_models import Candidate, Photo


def get_start_keyboard():
    keyboard = VkKeyboard(one_time=True)
    keyboard.add_button("Начать поиск", color=VkKeyboardColor.PRIMARY)
    return keyboard.get_keyboard()


def get_main_keyboard():
    keyboard = VkKeyboard(one_time=False)
    keyboard.add_button("👀 Смотреть анкеты",
                        color=VkKeyboardColor.PRIMARY)
    keyboard.add_line()
    keyboard.add_button("❤️ Мои фавориты",
                        color=VkKeyboardColor.POSITIVE)
    keyboard.add_button("🚫 Черный список",
                        color=VkKeyboardColor.NEGATIVE)
    keyboard.add_line()
    keyboard.add_button(
        "️⚙️ Настроить параметры поиска", color=VkKeyboardColor.SECONDARY
    )
    return keyboard.get_keyboard()


def get_profiles_keyboard():
    keyboard = VkKeyboard(one_time=False)
    keyboard.add_button("❤️ Нравится",
                        color=VkKeyboardColor.POSITIVE)
    keyboard.add_button("🚫 В черный список",
                        color=VkKeyboardColor.NEGATIVE)
    keyboard.add_button("➡️ Следующий",
                        color=VkKeyboardColor.PRIMARY)
    keyboard.add_line()
    keyboard.add_button(
        "📋 Информация о поиске", color=VkKeyboardColor.SECONDARY
    )
    keyboard.add_button("Назад", color=VkKeyboardColor.NEGATIVE)
    return keyboard.get_keyboard()


def get_favorites_keyboard():
    keyboard = VkKeyboard(one_time=False)
    keyboard.add_button("➡️ Следующий фаворит",
                        color=VkKeyboardColor.PRIMARY)
    keyboard.add_button("🗑️ Удалить фаворита",
                        color=VkKeyboardColor.NEGATIVE)
    keyboard.add_line()
    keyboard.add_button("📋 Главное меню",
                        color=VkKeyboardColor.SECONDARY)
    return keyboard.get_keyboard()


def get_blacklist_keyboard():
    keyboard = VkKeyboard(one_time=False)
    keyboard.add_button("➡️ Следующий в ЧС",
                        color=VkKeyboardColor.PRIMARY)
    keyboard.add_button("🗑️ Удалить из ЧС",
                        color=VkKeyboardColor.NEGATIVE)
    keyboard.add_line()
    keyboard.add_button("📋 Главное меню",
                        color=VkKeyboardColor.SECONDARY)
    return keyboard.get_keyboard()


def run_bot(adapter):
    token = token_vk

    # Функция для удаления непросмотренных кандидатов при изменении параметров
    def delete_candidates_on_parameter_change(user_id):
        """Удалить кандидатов пользователя (кроме избранных и черного списка)
        при изменении параметров"""
        try:
            # Находим всех кандидатов у которых favorite_status=0 и
            # blacklist_status=0
            candidates_to_delete = (
                adapter.session.query(Candidate)
                .filter(
                    Candidate.searcher_vk_id == user_id,
                    Candidate.favorite_status == 0,
                    Candidate.blacklist_status == 0,
                )
                .all()
            )

            deleted_count = 0
            if candidates_to_delete:
                for candidate in candidates_to_delete:
                    # Удаляем фото кандидата
                    adapter.session.query(Photo).filter(
                        Photo.candidates_id == candidate.candidate_id
                    ).delete()
                    # Удаляем кандидата
                    adapter.session.delete(candidate)
                    deleted_count += 1

                adapter.session.commit()
                print(
                    f"Удалено {deleted_count} кандидатов "
                    f"для пользователя {user_id}"
                )

            return deleted_count
        except Exception as e:
            print(f"Ошибка при удалении кандидатов: {e}")
            adapter.session.rollback()
            return 0

    def get_candidates_count_to_delete(user_id):
        """Получить количество кандидатов, которые будут удалены
        при изменении параметров"""
        count = (
            adapter.session.query(Candidate)
            .filter(
                Candidate.searcher_vk_id == user_id,
                Candidate.favorite_status == 0,
                Candidate.blacklist_status == 0,
            )
            .count()
        )
        return count

    # Вспомогательные функции, которые используют adapter
    def search_and_save_candidates(user_id, count=50):
        """Найти и сохранить 50 кандидатов через VK API"""
        user_data = adapter.get_user_data(user_id)
        age = user_data.get("age", 25)
        gender = user_data.get("gender", 2)
        city = user_data.get("city", "Москва")

        city_id, city_name = get_city_id(city)

        user_update = {
            "vk_user_id": user_id,
            "age": age,
            "gender": gender,
            "city": city,
            "city_id": city_id,
        }
        adapter.save_or_update_user(user_update)

        search_gender = gender

        candidates = search_vk_users(
            ACCESS_TOKEN_VK, city_id, age, age, search_gender
        )

        if not candidates:
            return 0

        saved_count = 0
        for candidate in candidates[:count]:
            photos = get_candidate_photos(ACCESS_TOKEN_VK, candidate["id"])

            result = adapter.save_candidate_with_photos(
                candidate, photos, user_id
            )
            if result:
                saved_count += 1

        return saved_count

    def get_next_candidate(user_id):
        """Получить следующего кандидата"""
        # Сначала ищем с view_status=2 (текущий просматриваемый)
        candidate = (
            adapter.session.query(Candidate)
            .filter(
                Candidate.searcher_vk_id == user_id,
                Candidate.view_status == 2,
                Candidate.favorite_status == 0,
                Candidate.blacklist_status == 0,
            )
            .first()
        )

        if not candidate:
            # Если нет текущего, ищем непросмотренного
            candidate = (
                adapter.session.query(Candidate)
                .filter(
                    Candidate.searcher_vk_id == user_id,
                    Candidate.view_status == 0,
                    Candidate.favorite_status == 0,
                    Candidate.blacklist_status == 0,
                )
                .first()
            )

            if not candidate:
                return None

        # Делаем его текущим (статус 2)
        candidate.view_status = 2
        adapter.session.commit()

        photos = (
            adapter.session.query(Photo)
            .filter(Photo.candidates_id == candidate.candidate_id)
            .all()
        )

        photos_data = []
        for photo in photos[:3]:
            photos_data.append(
                {
                    "vk_photo_id": photo.vk_photo_id,
                    "photo_link": photo.photo_link,
                    "owner_id": candidate.vk_user_id,
                }
            )

        return {
            "id": candidate.vk_user_id,
            "first_name": candidate.first_name,
            "last_name": candidate.last_name,
            "profile_link": candidate.profile_link,
            "candidate_id": candidate.candidate_id,
            "photos": photos_data,
        }

    def get_next_favorite(user_id):
        """Получить следующего фаворита"""
        # Сначала ищем текущего фаворита (favorite_status=2)
        current_favorite = (
            adapter.session.query(Candidate)
            .filter(
                Candidate.searcher_vk_id == user_id,
                Candidate.favorite_status == 2,
            )
            .first()
        )

        # Если есть текущий, меняем его статус на 3 (просмотренный фаворит)
        if current_favorite:
            current_favorite.favorite_status = 3
            adapter.session.commit()

        # Ищем следующего фаворита со статусом 1
        candidate = (
            adapter.session.query(Candidate)
            .filter(
                Candidate.searcher_vk_id == user_id,
                Candidate.favorite_status == 1,
            )
            .first()
        )

        if not candidate:
            # Если не нашли, сбрасываем всех просмотренных (3) в 1
            adapter.session.query(Candidate).filter(
                Candidate.searcher_vk_id == user_id,
                Candidate.favorite_status == 3,
            ).update({"favorite_status": 1})
            adapter.session.commit()

            # Пробуем снова найти фаворита
            candidate = (
                adapter.session.query(Candidate)
                .filter(
                    Candidate.searcher_vk_id == user_id,
                    Candidate.favorite_status == 1,
                )
                .first()
            )

        if not candidate:
            return None

        # Делаем его текущим фаворитом (статус 2)
        candidate.favorite_status = 2
        adapter.session.commit()

        photos = (
            adapter.session.query(Photo)
            .filter(Photo.candidates_id == candidate.candidate_id)
            .all()
        )

        photos_data = []
        for photo in photos[:3]:
            photos_data.append(
                {
                    "vk_photo_id": photo.vk_photo_id,
                    "photo_link": photo.photo_link,
                    "owner_id": candidate.vk_user_id,
                }
            )

        return {
            "id": candidate.vk_user_id,
            "first_name": candidate.first_name,
            "last_name": candidate.last_name,
            "profile_link": candidate.profile_link,
            "candidate_id": candidate.candidate_id,
            "photos": photos_data,
        }

    def get_next_blacklist(user_id):
        """Получить следующего кандидата из черного списка"""
        # Сначала ищем текущего в ЧС (blacklist_status=2)
        current_blacklist = (
            adapter.session.query(Candidate)
            .filter(
                Candidate.searcher_vk_id == user_id,
                Candidate.blacklist_status == 2,
            )
            .first()
        )

        # Если есть текущий, меняем его статус на 3 (просмотренный в ЧС)
        if current_blacklist:
            current_blacklist.blacklist_status = 3
            adapter.session.commit()

        # Ищем следующего в ЧС со статусом 1
        candidate = (
            adapter.session.query(Candidate)
            .filter(
                Candidate.searcher_vk_id == user_id,
                Candidate.blacklist_status == 1,
            )
            .first()
        )

        if not candidate:
            # Если не нашли, сбрасываем всех просмотренных (3) в 1
            adapter.session.query(Candidate).filter(
                Candidate.searcher_vk_id == user_id,
                Candidate.blacklist_status == 3,
            ).update({"blacklist_status": 1})
            adapter.session.commit()

            # Пробуем снова найти в ЧС
            candidate = (
                adapter.session.query(Candidate)
                .filter(
                    Candidate.searcher_vk_id == user_id,
                    Candidate.blacklist_status == 1,
                )
                .first()
            )

        if not candidate:
            return None

        # Делаем его текущим в ЧС (статус 2)
        candidate.blacklist_status = 2
        adapter.session.commit()

        photos = (
            adapter.session.query(Photo)
            .filter(Photo.candidates_id == candidate.candidate_id)
            .all()
        )

        photos_data = []
        for photo in photos[:3]:
            photos_data.append(
                {
                    "vk_photo_id": photo.vk_photo_id,
                    "photo_link": photo.photo_link,
                    "owner_id": candidate.vk_user_id,
                }
            )

        return {
            "id": candidate.vk_user_id,
            "first_name": candidate.first_name,
            "last_name": candidate.last_name,
            "profile_link": candidate.profile_link,
            "candidate_id": candidate.candidate_id,
            "photos": photos_data,
        }

    def show_candidate(user_id, candidate_data):
        """Показать кандидата"""
        if not candidate_data:
            # Сначала удаляем всех просмотренных кандидатов
            candidates_to_delete = (
                adapter.session.query(Candidate)
                .filter(
                    Candidate.searcher_vk_id == user_id,
                    Candidate.view_status == 1,
                    Candidate.favorite_status == 0,
                    Candidate.blacklist_status == 0,
                )
                .all()
            )

            if candidates_to_delete:
                for candidate in candidates_to_delete:
                    adapter.session.query(Photo).filter(
                        Photo.candidates_id == candidate.candidate_id
                    ).delete()
                    adapter.session.delete(candidate)
                adapter.session.commit()
                print(
                    f"✅ Удалено {len(candidates_to_delete)} "
                    f"просмотренных кандидатов"
                )

            write_msg(
                user_id, "🔄 Ищу новых кандидатов...",
                get_profiles_keyboard()
            )
            saved_count = search_and_save_candidates(user_id, 50)

            if saved_count > 0:
                candidate = get_next_candidate(user_id)
                if candidate:
                    show_candidate(user_id, candidate)
                    return
                else:
                    write_msg(
                        user_id,
                        "🎉 Вы просмотрели всех кандидатов!",
                        get_main_keyboard(),
                    )
                    return
            else:
                write_msg(
                    user_id, "Кандидаты не найдены 😢",
                    get_main_keyboard()
                )
                return

        message = (
            f"👤 Кандидат\n\n"
            f"📋 Информация:\n"
            f"• Имя: {candidate_data['first_name']} "
            f"{candidate_data['last_name']}\n"
            f"• Ссылка: {candidate_data['profile_link']}\n\n"
            f"💡 Выберите действие:"
        )

        attachments = []
        for photo in candidate_data["photos"][:3]:
            attachments.append(
                f"photo{photo['owner_id']}_{photo['vk_photo_id']}"
            )

        if attachments:
            write_msg(
                user_id,
                message,
                get_profiles_keyboard(),
                ",".join(attachments),
            )
        else:
            write_msg(
                user_id,
                message + "\n\n⚠️ Нет фото профиля",
                get_profiles_keyboard(),
            )

    def show_favorite(user_id, favorite_data):
        """Показать фаворита"""
        if not favorite_data:
            write_msg(
                user_id,
                "🎉 Вы просмотрели всех фаворитов!\n"
                "" "Начните заново.",
                get_main_keyboard(),
            )
            return

        message = (
            f"❤️ Фаворит\n\n"
            f"📋 Информация:\n"
            f"• Имя: {favorite_data['first_name']} "
            f"{favorite_data['last_name']}\n"
            f"• Ссылка: {favorite_data['profile_link']}\n\n"
            f"💡 Выберите действие:"
        )

        attachments = []
        for photo in favorite_data["photos"][:3]:
            attachments.append(
                f"photo{photo['owner_id']}_{photo['vk_photo_id']}"
            )

        if attachments:
            write_msg(
                user_id,
                message,
                get_favorites_keyboard(),
                ",".join(attachments),
            )
        else:
            write_msg(
                user_id,
                message + "\n\n⚠️ Нет фото профиля",
                get_favorites_keyboard(),
            )

    def show_blacklist(user_id, blacklist_data):
        """Показать кандидата из черного списка"""
        if not blacklist_data:
            write_msg(
                user_id,
                "🎉 Вы просмотрели всех в черном списке!\n"
                "Начните заново.",
                get_main_keyboard(),
            )
            return

        message = (
            f"🚫 Черный список\n\n"
            f"📋 Информация:\n"
            f"• Имя: {blacklist_data['first_name']} "
            f"{blacklist_data['last_name']}\n"
            f"• Ссылка: {blacklist_data['profile_link']}\n\n"
            f"💡 Выберите действие:"
        )

        attachments = []
        for photo in blacklist_data["photos"][:3]:
            attachments.append(
                f"photo{photo['owner_id']}_{photo['vk_photo_id']}"
            )

        if attachments:
            write_msg(
                user_id,
                message,
                get_blacklist_keyboard(),
                ",".join(attachments),
            )
        else:
            write_msg(
                user_id,
                message + "\n\n⚠️ Нет фото профиля",
                get_blacklist_keyboard(),
            )

    def show_current_settings(user_id):
        """Показать текущие настройки пользователя"""
        user_data = adapter.get_user_data(user_id)
        if user_data:
            get_candidates_count_to_delete(user_id)

            message = (
                f"⚙️ Текущие параметры поиска:\n\n"
                f"• Возраст: {user_data.get('age', 'не указан')} лет\n"
                f"• Пол: "
                f"{'Мужской' if user_data.get('gender') == 2 else 'Женский'}\n"
                f"• Город: {user_data.get('city', 'не указан')}\n"
                f"1. Возраст\n"
                f"2. Пол\n"
                f"3. Город\n"
                f"4. Отмена"
            )
            write_msg(user_id, message)
        else:
            write_msg(
                user_id,
                "У вас еще нет настроек поиска. " 
                "Сначала зарегистрируйтесь.",
                get_start_keyboard(),
            )

    # Глобальная функция отправки сообщений (исправленная версия)
    def write_msg(user_id, message, keyboard=None, attachment=None):
        try:
            # Создаем новую сессию для отправки
            local_vk_session = vk_api.VkApi(token=token)
            local_vk = local_vk_session.get_api()

            params = {
                "user_id": user_id,
                "message": message,
                "random_id": randrange(10**7),
            }
            if keyboard:
                params["keyboard"] = keyboard
            if attachment:
                params["attachment"] = attachment

            # Правильный вызов метода
            local_vk.messages.send(**params)
            return True

        except Exception as e:
            print(f"Ошибка при отправке сообщения пользователю {user_id}: {e}")
            return False

    temp_user_data = {}
    edit_user_data = {}

    welcome_message = (
        "👋 Я — бот для знакомств «Conspicere» - Взаимный взгляд.\n"
        "📋 Что я умею:\n"
        "• Искать людей по возрасту, городу и полу\n"
        "• Показывать фото профиля\n"
        "• Сохранять понравившихся в избранное\n"
        "• Вести черный список\n\n"
        "Нажмите кнопку 'Начать поиск' чтобы начать!"
    )

    print("Бот запущен и ожидает сообщений...")

    while True:
        try:
            # Создаем новое соединение для каждой итерации
            vk_session = vk_api.VkApi(token=token)
            longpoll = VkLongPoll(vk_session, wait=25)  # wait=25 секунд

            # Проверяем события (неблокирующий метод)
            events = longpoll.check()

            for event in events:
                if event.type == VkEventType.MESSAGE_NEW and event.to_me:
                    user_id = event.user_id
                    text = event.text

                    print(f"Получено сообщение от {user_id}: '{text}'")

                    # Приветствие
                    if text.lower() in [
                        "привет",
                        "старт",
                        "начать",
                        "start",
                        "👋",
                    ]:
                        write_msg(
                            user_id, welcome_message, get_start_keyboard()
                        )

                    # Начало поиска
                    elif text == "Начать поиск" or text.lower() == "поиск":
                        existing_user = adapter.get_user_data(user_id)

                        if existing_user:
                            write_msg(
                                user_id,
                                "✅ Вы уже зарегистрированы!\n"
                                "Нажимайте '👀 Смотреть анкеты'",
                                get_main_keyboard(),
                            )
                        else:
                            temp_user_data[user_id] = {}
                            write_msg(
                                user_id,
                                "Введите возраст кандидата " 
                                "(например: 25):",
                            )

                    # Смотреть анкеты
                    elif (
                        text == "👀 Смотреть анкеты"
                        or "смотреть анкеты" in text.lower()
                    ):
                        existing_user = adapter.get_user_data(user_id)

                        if not existing_user:
                            write_msg(
                                user_id,
                                "Сначала настройте" 
                                " параметры поиска!",
                                get_start_keyboard(),
                            )
                            continue

                        candidate = get_next_candidate(user_id)
                        show_candidate(user_id, candidate)

                    # Кнопка "Нравится"
                    elif text == "❤️ Нравится" or "нравится" in text.lower():
                        # Находим текущего кандидата (view_status=2)
                        current_candidate = (
                            adapter.session.query(Candidate)
                            .filter(
                                Candidate.searcher_vk_id == user_id,
                                Candidate.view_status == 2,
                            )
                            .first()
                        )

                        if not current_candidate:
                            write_msg(
                                user_id,
                                "Сначала выберите кандидата",
                                get_main_keyboard(),
                            )
                            continue

                        # Добавляем в фавориты: favorite_status=1,
                        # view_status=1
                        current_candidate.favorite_status = 1
                        current_candidate.view_status = 1
                        adapter.session.commit()

                        write_msg(
                            user_id,
                            "✅ Добавлено в избранное!",
                            get_profiles_keyboard(),
                        )

                        next_candidate = get_next_candidate(user_id)
                        show_candidate(user_id, next_candidate)

                    # Кнопка "В черный список"
                    elif (
                        text == "🚫 В черный список"
                        or "в черный список" in text.lower()
                    ):
                        current_candidate = (
                            adapter.session.query(Candidate)
                            .filter(
                                Candidate.searcher_vk_id == user_id,
                                Candidate.view_status == 2,
                            )
                            .first()
                        )

                        if not current_candidate:
                            write_msg(
                                user_id,
                                "Сначала выберите кандидата",
                                get_main_keyboard(),
                            )
                            continue

                        # Добавляем в черный список: blacklist_status=1,
                        # view_status=1
                        current_candidate.blacklist_status = 1
                        current_candidate.view_status = 1
                        adapter.session.commit()

                        write_msg(
                            user_id,
                            "✅ Добавлено в черный список!",
                            get_profiles_keyboard(),
                        )

                        next_candidate = get_next_candidate(user_id)
                        show_candidate(user_id, next_candidate)

                    # Мои фавориты
                    elif (
                        text == "❤️ Мои фавориты"
                        or "мои фавориты" in text.lower()
                    ):
                        favorites_count = (
                            adapter.session.query(Candidate)
                            .filter(
                                Candidate.searcher_vk_id == user_id,
                                Candidate.favorite_status.in_([1, 2, 3]),
                            )
                            .count()
                        )

                        if favorites_count == 0:
                            write_msg(
                                user_id,
                                "❤️ В вашем избранном "
                                "пока никого нет 😢",
                                get_main_keyboard(),
                            )
                            continue

                        write_msg(
                            user_id,
                            f"❤️ У вас {favorites_count} фаворитов\n"
                            f"\nВыберите действие:",
                            get_favorites_keyboard(),
                        )

                        favorite = get_next_favorite(user_id)
                        show_favorite(user_id, favorite)

                    # Черный список
                    elif (
                        text == "🚫 Черный список"
                        or "черный список" in text.lower()
                    ):
                        blacklist_count = (
                            adapter.session.query(Candidate)
                            .filter(
                                Candidate.searcher_vk_id == user_id,
                                Candidate.blacklist_status.in_([1, 2, 3]),
                            )
                            .count()
                        )

                        if blacklist_count == 0:
                            write_msg(
                                user_id,
                                "🚫 Черный список пуст 😊",
                                get_main_keyboard(),
                            )
                            continue

                        write_msg(
                            user_id,
                            f"🚫 В черном списке: {blacklist_count} "
                            f"\n\nВыберите действие:",
                            get_blacklist_keyboard(),
                        )

                        candidate = get_next_blacklist(user_id)
                        show_blacklist(user_id, candidate)

                    # Кнопка "Настроить параметры поиска"
                    elif "настроить" in text.lower() or "⚙️" in text:
                        existing_user = adapter.get_user_data(user_id)
                        if not existing_user:
                            write_msg(
                                user_id,
                                "Сначала зарегистрируйтесь!",
                                get_start_keyboard(),
                            )
                            continue

                        edit_user_data[user_id] = {"step": "show_settings"}
                        show_current_settings(user_id)

                    # Регистрация: возраст
                    elif (
                        user_id in temp_user_data
                        and "age" not in temp_user_data[user_id]
                    ):
                        if text.isdigit() and 18 <= int(text) <= 100:
                            temp_user_data[user_id]["age"] = int(text)
                            write_msg(user_id, "Введите город:")
                        else:
                            write_msg(user_id, "Введите возраст "
                                               "18-100:")

                    # Регистрация: город
                    elif (
                        user_id in temp_user_data
                        and "age" in temp_user_data[user_id]
                        and "city" not in temp_user_data[user_id]
                    ):
                        try:
                            city_id, city_name = get_city_id(text)
                            temp_user_data[user_id]["city"] = city_name
                            temp_user_data[user_id]["city_id"] = city_id
                            write_msg(
                                user_id,
                                "Введите пол (1-женский, " 
                                "2-мужской):",
                            )
                        except (ValueError, KeyError, Exception):
                            write_msg(
                                user_id, "Город не найден. "
                                         "Попробуйте еще раз:"
                            )

                    # Регистрация: пол и сохранение
                    elif (
                        user_id in temp_user_data
                        and "age" in temp_user_data[user_id]
                        and "city" in temp_user_data[user_id]
                    ):
                        if text in ["1", "2"]:
                            user_data = {
                                "vk_user_id": user_id,
                                "age": temp_user_data[user_id]["age"],
                                "gender": int(text),
                                "city": temp_user_data[user_id]["city"],
                                "city_id": temp_user_data[user_id]["city_id"],
                            }

                            adapter.save_or_update_user(user_data)
                            del temp_user_data[user_id]

                            write_msg(
                                user_id,
                                f"✅ Регистрация завершена!\n"
                                f"Возраст: {user_data['age']} лет\n"
                                f"Город: {user_data['city']}\n"
                                f"Пол: "
                                f"{'Мужской' if user_data['gender'] == 2 
                                else 'Женский'}\n\n"
                                f"Нажмите '👀 Смотреть анкеты'",
                                get_main_keyboard(),
                            )
                        else:
                            write_msg(user_id, "Введите 1 или 2:")

                    # Редактирование параметров: выбор параметра
                    elif (
                        user_id in edit_user_data
                        and edit_user_data[user_id]["step"] == "show_settings"
                    ):
                        if text == "1" or "возраст" in text.lower():
                            edit_user_data[user_id] = {"step": "edit_age"}
                            write_msg(
                                user_id,
                                "Введите новый возраст"
                                " кандидата (например: 25):",
                            )
                        elif text == "2" or "пол" in text.lower():
                            edit_user_data[user_id] = {"step": "edit_gender"}
                            write_msg(
                                user_id,
                                "Введите новый пол " "(1-женский, "
                                "2-мужской):",
                            )
                        elif text == "3" or "город" in text.lower():
                            edit_user_data[user_id] = {"step": "edit_city"}
                            write_msg(user_id, "Введите новый город:")
                        elif text == "4" or "отмена" in text.lower():
                            del edit_user_data[user_id]
                            write_msg(
                                user_id,
                                "Изменения отменены.",
                                get_main_keyboard(),
                            )
                        else:
                            write_msg(
                                user_id,
                                "Выберите параметр для "
                                "изменения (1-4):",
                            )

                    # Редактирование: возраст
                    elif (
                        user_id in edit_user_data
                        and edit_user_data[user_id]["step"] == "edit_age"
                    ):
                        if text.isdigit() and 18 <= int(text) <= 100:
                            # Удаляем существующих кандидатов
                            delete_candidates_on_parameter_change(user_id)

                            # Обновляем возраст
                            user_data = adapter.get_user_data(user_id)
                            user_data["age"] = int(text)
                            adapter.save_or_update_user(user_data)
                            del edit_user_data[user_id]

                            write_msg(
                                user_id,
                                f"✅ Возраст обновлен на"
                                f" {text} лет!\n\n"
                                f"Новые параметры поиска:\n"
                                f"• Возраст: {text} лет\n"
                                f"• Пол: "
                                f"{'Мужской' if user_data.get('gender') == 2 
                                else 'Женский'}\n"
                                f"• Город: {user_data.get('city', 
                                                          'не указан')}",
                                get_main_keyboard(),
                            )
                        else:
                            write_msg(user_id, "Введите возраст "
                                               "18-100:")

                    # Редактирование: пол
                    elif (
                        user_id in edit_user_data
                        and edit_user_data[user_id]["step"] == "edit_gender"
                    ):
                        if text in ["1", "2"]:
                            # Удаляем существующих кандидатов
                            delete_candidates_on_parameter_change(user_id)

                            # Обновляем пол
                            user_data = adapter.get_user_data(user_id)
                            user_data["gender"] = int(text)
                            adapter.save_or_update_user(user_data)
                            del edit_user_data[user_id]

                            write_msg(
                                user_id,
                                f"✅ Пол обновлен на "
                                f"{'женский' if text == '1' else 'мужской'}"
                                f"!\n\n"
                                f"Новые параметры поиска:\n"
                                f"• Возраст: "
                                f"{user_data.get('age', 'не указан')} лет\n"
                                f"• Пол: "
                                f"{'Женский' if text == '1' else 'Мужской'}\n"
                                f"• Город: "
                                f"{user_data.get('city', 'не указан')}",
                                get_main_keyboard(),
                            )
                        else:
                            write_msg(user_id, "Введите 1 или 2:")

                    # Редактирование: город
                    elif (
                        user_id in edit_user_data
                        and edit_user_data[user_id]["step"] == "edit_city"
                    ):
                        try:
                            city_id, city_name = get_city_id(text)
                            # Удаляем существующих кандидатов
                            delete_candidates_on_parameter_change(user_id)

                            # Обновляем город
                            user_data = adapter.get_user_data(user_id)
                            user_data["city"] = city_name
                            user_data["city_id"] = city_id
                            adapter.save_or_update_user(user_data)
                            del edit_user_data[user_id]

                            write_msg(
                                user_id,
                                f"✅ Город обновлен "
                                f"на {city_name}!\n\n"
                                f"Новые параметры поиска:\n"
                                f"• Возраст: "
                                f"{user_data.get('age', 'не указан')} лет\n"
                                f"• Пол: "
                                f"{'Мужской' if user_data.get('gender') == 2 
                                else 'Женский'}\n"
                                f"• Город: {city_name}",
                                get_main_keyboard(),
                            )
                        except (KeyError, ValueError):
                            write_msg(
                                user_id, "Город не найден. "
                                         "Попробуйте еще раз:"
                            )

                    # Кнопка "Следующий" (кандидаты)
                    elif (
                        "следующий" in text.lower()
                        and text != "➡️ Следующий фаворит"
                        and text != "➡️ Следующий в ЧС"
                    ):
                        current_candidate = (
                            adapter.session.query(Candidate)
                            .filter(
                                Candidate.searcher_vk_id == user_id,
                                Candidate.view_status == 2,
                            )
                            .first()
                        )

                        if current_candidate:
                            # Просто отмечаем как просмотренного: view_status=1
                            current_candidate.view_status = 1
                            adapter.session.commit()

                        next_candidate = get_next_candidate(user_id)
                        show_candidate(user_id, next_candidate)

                    # Кнопка "Следующий фаворит"
                    elif "следующий фаворит" in text.lower():
                        next_favorite = get_next_favorite(user_id)
                        show_favorite(user_id, next_favorite)

                    # Кнопка "Удалить фаворита"
                    elif "удалить фаворита" in text.lower():
                        current_favorite = (
                            adapter.session.query(Candidate)
                            .filter(
                                Candidate.searcher_vk_id == user_id,
                                Candidate.favorite_status == 2,
                            )
                            .first()
                        )

                        if not current_favorite:
                            write_msg(
                                user_id,
                                "Сначала выберите фаворита",
                                get_favorites_keyboard(),
                            )
                            continue

                        # Удаляем фото
                        adapter.session.query(Photo).filter(
                            Photo.candidates_id
                            == current_favorite.candidate_id
                        ).delete()

                        # Удаляем кандидата
                        adapter.session.delete(current_favorite)
                        adapter.session.commit()

                        write_msg(
                            user_id,
                            "🗑️ Фаворит удален!",
                            get_favorites_keyboard(),
                        )

                        # Показываем следующего фаворита
                        next_favorite = get_next_favorite(user_id)
                        show_favorite(user_id, next_favorite)

                    # Кнопка "Следующий в ЧС"
                    elif "следующий в чс" in text.lower():
                        next_blacklist = get_next_blacklist(user_id)
                        show_blacklist(user_id, next_blacklist)

                    # Кнопка "Удалить из ЧС"
                    elif "удалить из чс" in text.lower():
                        current_blacklist = (
                            adapter.session.query(Candidate)
                            .filter(
                                Candidate.searcher_vk_id == user_id,
                                Candidate.blacklist_status == 2,
                            )
                            .first()
                        )

                        if not current_blacklist:
                            write_msg(
                                user_id,
                                "Сначала выберите " "кандидата из ЧС",
                                get_blacklist_keyboard(),
                            )
                            continue

                        # Удаляем фото
                        adapter.session.query(Photo).filter(
                            Photo.candidates_id
                            == current_blacklist.candidate_id
                        ).delete()

                        # Удаляем кандидата
                        adapter.session.delete(current_blacklist)
                        adapter.session.commit()

                        write_msg(
                            user_id,
                            "🗑️ Удалено из черного списка!",
                            get_blacklist_keyboard(),
                        )

                        # Показываем следующего из ЧС
                        next_blacklist = get_next_blacklist(user_id)
                        show_blacklist(user_id, next_blacklist)

                    # Главное меню
                    elif "главное меню" in text.lower():
                        # Очищаем все временные данные
                        if user_id in temp_user_data:
                            del temp_user_data[user_id]
                        if user_id in edit_user_data:
                            del edit_user_data[user_id]
                        write_msg(user_id, "Главное меню",
                                  get_main_keyboard())

                    # Назад
                    elif text.lower() == "назад":
                        # Очищаем все временные данные
                        if user_id in temp_user_data:
                            del temp_user_data[user_id]
                        if user_id in edit_user_data:
                            del edit_user_data[user_id]
                        write_msg(
                            user_id,
                            "👋 Я — бот для знакомств «Conspicere» - "
                            "Взаимный взгляд.\n"
                            "📋 Что я умею:\n"
                            "• Искать людей по возрасту, городу и полу\n"
                            "• Показывать фото профиля\n"
                            "• Сохранять понравившихся в избранное\n"
                            "• Вести черный список\n",
                            get_main_keyboard(),
                        )

                    # Информация о поиске
                    elif "информация" in text.lower():
                        existing_user = adapter.get_user_data(user_id)
                        if existing_user:
                            unviewed_count = (
                                adapter.session.query(Candidate)
                                .filter(
                                    Candidate.searcher_vk_id == user_id,
                                    Candidate.view_status == 0,
                                    Candidate.favorite_status == 0,
                                    Candidate.blacklist_status == 0,
                                )
                                .count()
                            )

                            favorites_count = (
                                adapter.session.query(Candidate)
                                .filter(
                                    Candidate.searcher_vk_id == user_id,
                                    Candidate.favorite_status.in_([1, 2, 3]),
                                )
                                .count()
                            )

                            blacklist_count = (
                                adapter.session.query(Candidate)
                                .filter(
                                    Candidate.searcher_vk_id == user_id,
                                    Candidate.blacklist_status.in_([1, 2, 3]),
                                )
                                .count()
                            )

                            message = (
                                f"📋 Статистика:\n"
                                f"• Непросмотренных кандидатов: {unviewed_count}\n"
                                f"• В избранном: {favorites_count}\n"
                                f"• В черном списке: {blacklist_count}\n\n"
                                f"📊 Параметры поиска:\n"
                                f"• Возраст: {existing_user.get('age',
                                                                'не указан')} лет\n"
                                f"• Пол: "
                                f"{'Мужской' 
                                if existing_user.get('gender') == 2 
                                else 'Женский'}\n"
                                f"• Город: {existing_user.get('city', 
                                                              'не указан')}"
                            )
                            write_msg(
                                user_id, message, get_profiles_keyboard()
                            )
                        else:
                            write_msg(
                                user_id,
                                "Сначала зарегистрируйтесь!",
                                get_start_keyboard(),
                            )

                    # Неизвестная команда
                    else:
                        if (
                            user_id in temp_user_data
                            or user_id in edit_user_data
                        ):
                            write_msg(
                                user_id,
                                "Завершите "
                                "регистрацию/редактирование или "
                                "введите 'отмена'",
                            )
                        else:
                            write_msg(
                                user_id,
                                "Не понял. Нажмите " "'Начать поиск'",
                                get_start_keyboard(),
                            )

            # Короткая пауза между итерациями
            time.sleep(0.1)

        except (
            requests.exceptions.ConnectionError,
            requests.exceptions.ReadTimeout,
            requests.exceptions.ChunkedEncodingError,
            vk_api.exceptions.ApiHttpError,
            vk_api.exceptions.ApiError,
        ) as e:
            print(
                f"Ошибка соединения: {e}. Переподключение через 3 секунды..."
            )
            time.sleep(3)

        except KeyboardInterrupt:
            print("\nБот остановлен пользователем")
            sys.exit(0)

        except Exception as e:
            print(
                f"Неожиданная ошибка: {e}. "
                f"Продолжение работы через 5 секунд..."
            )
            import traceback

            traceback.print_exc()
            time.sleep(5)
