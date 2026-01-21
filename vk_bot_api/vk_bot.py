import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
import time
import sys

from config import token_vk, ACCESS_TOKEN_VK
from vk_bot_api.keyboard import (
    get_start_keyboard, get_main_keyboard, get_profiles_keyboard,
    get_favorites_keyboard, get_blacklist_keyboard
)
from vk_bot_api.requests_api import search_vk_users, get_candidate_photos
from vk_bot_api.message import (
    write_msg, WELCOME_MESSAGE, START_MESSAGE, REG_ENTER_AGE,
    REG_INVALID_AGE, REG_ENTER_CITY, REG_INVALID_CITY, REG_ENTER_GENDER,
    REG_INVALID_GENDER, REG_COMPLETE, REG_ALREADY_REGISTERED, NEED_SETTINGS,
    NO_CANDIDATES_FOUND, CANDIDATES_SAVED, NO_CANDIDATES_SAVED, SEARCHING_VK,
    API_SEARCH_ERROR, CANDIDATE_INFO, NO_PHOTO_WARNING, NO_CANDIDATE_DATA,
    UNABLE_TO_SHOW, ADDED_TO_FAVORITES, ADDED_TO_BLACKLIST, SELECT_CANDIDATE_FIRST,
    FAVORITES_EMPTY, FAVORITES_ALL_VIEWED, FAVORITE_INFO, UNABLE_LOAD_FAVORITES,
    NO_FAVORITES, SELECT_FAVORITE_TO_DELETE, REMOVED_FROM_FAVORITES,
    RESTARTING_FAVORITES, ALL_FAVORITES_DELETED, ALL_FAVORITES_DELETED_EMPTY,
    BLACKLIST_EMPTY, BLACKLIST_EMPTY_FULL, BLACKLIST_INFO, UNABLE_LOAD_BLACKLIST,
    BLACKLIST_ALL_VIEWED, SELECT_BLACKLIST_TO_DELETE, REMOVED_FROM_BLACKLIST,
    RESTARTING_BLACKLIST, ALL_BLACKLIST_DELETED, ALL_BLACKLIST_DELETED_EMPTY,
    SETTINGS_NO_REG, SETTINGS_CURRENT, SETTINGS_AGE_UPDATED, SETTINGS_GENDER_UPDATED,
    SETTINGS_CITY_UPDATED, SETTINGS_CANCELLED, SETTINGS_CHOOSE_PARAM,
    SETTINGS_ENTER_NEW_AGE, SETTINGS_ENTER_NEW_GENDER, SETTINGS_ENTER_NEW_CITY,
    STATISTICS_INFO, STATISTICS_NO_REG, MAIN_MENU, BACK_TO_MAIN, COMPLETE_REG_OR_CANCEL,
    CHOOSE_ACTION, UNKNOWN_COMMAND, GENDER_FEMALE, GENDER_MALE,
    AGE_NOT_SPECIFIED, CITY_NOT_SPECIFIED
)


def run_bot(adapter):
    print("Бот запущен")

    temp_user_data = {}
    edit_user_data = {}

    def search_and_save_candidates_from_api(user_id):
        """Найти кандидатов через VK API и сохранить в БД"""
        user_data = adapter.get_user_data(user_id)
        if not user_data:
            return 0, NEED_SETTINGS

        age = user_data.get('age')
        gender = user_data.get('gender')
        city = user_data.get('city')

        print(f"Поиск кандидатов через API: город={city}, возраст={age}, пол={gender}")

        try:
            candidates = search_vk_users(
                ACCESS_TOKEN_VK,
                city,
                age,
                age,
                gender,
                offset=0
            )

            print(f"Найдено кандидатов через API: {len(candidates)}")

            if not candidates:
                return 0, NO_CANDIDATES_FOUND

            saved_count = 0
            for candidate in candidates:
                try:
                    photos = get_candidate_photos(ACCESS_TOKEN_VK, candidate['id'])
                    if photos:
                        adapter.save_candidate_with_photos(
                            candidate_data=candidate,
                            photos_data=photos,
                            searcher_vk_id=user_id
                        )
                        saved_count += 1
                        print(f"Сохранен кандидат: {candidate['first_name']} {candidate['last_name']}")

                except Exception as e:
                    print(f"Ошибка сохранения кандидата {candidate['id']}: {e}")
                    continue

            if saved_count == 0:
                return 0, NO_CANDIDATES_SAVED

            return saved_count, CANDIDATES_SAVED.format(saved_count)

        except Exception as e:
            print(f"Ошибка при поиске через API: {e}")
            return 0, API_SEARCH_ERROR.format(str(e))

    def show_candidate_from_db_or_api(user_id):
        """Показать кандидата из БД или найти новых через API"""
        candidate = adapter.get_next_candidate(user_id)

        if candidate:
            show_candidate_info(user_id, candidate)
            return True
        else:
            deleted_count = adapter.delete_viewed_candidates(user_id)
            if deleted_count > 0:
                print(f"Удалено {deleted_count} просмотренных кандидатов")

            write_msg(user_id, SEARCHING_VK, get_profiles_keyboard())

            saved_count, message = search_and_save_candidates_from_api(user_id)

            if saved_count > 0:
                candidate = adapter.get_next_candidate(user_id)
                if candidate:
                    show_candidate_info(user_id, candidate)
                    return True
                else:
                    write_msg(user_id, UNABLE_TO_SHOW, get_main_keyboard())
                    return False
            else:
                write_msg(user_id, f"😔 {message}\n\nПопробуйте изменить параметры поиска.", get_main_keyboard())
                return False

    def show_candidate_info(user_id, candidate_data):
        """Показать информацию о кандидате"""
        if not candidate_data:
            write_msg(user_id, NO_CANDIDATE_DATA, get_main_keyboard())
            return

        message = CANDIDATE_INFO.format(
            candidate_data['first_name'],
            candidate_data['last_name'],
            candidate_data['profile_link']
        )

        attachments = []
        for photo in candidate_data.get('photos', [])[:3]:
            attachments.append(f"photo{photo['owner_id']}_{photo['vk_photo_id']}")

        if attachments:
            write_msg(user_id, message, get_profiles_keyboard(), ','.join(attachments))
        else:
            write_msg(user_id, message + NO_PHOTO_WARNING, get_profiles_keyboard())

    def show_favorite_info(user_id, favorite_data):
        """Показать информацию о фаворите"""
        if not favorite_data:
            write_msg(user_id, FAVORITES_ALL_VIEWED, get_favorites_keyboard())
            return

        message = FAVORITE_INFO.format(
            favorite_data['first_name'],
            favorite_data['last_name'],
            favorite_data['profile_link']
        )

        attachments = []
        for photo in favorite_data.get('photos', [])[:3]:
            attachments.append(f"photo{photo['owner_id']}_{photo['vk_photo_id']}")

        if attachments:
            write_msg(user_id, message, get_favorites_keyboard(), ','.join(attachments))
        else:
            write_msg(user_id, message + NO_PHOTO_WARNING, get_favorites_keyboard())

    def show_blacklist_info(user_id, blacklist_data):
        """Показать информацию о кандидате в черном списке"""
        if not blacklist_data:
            write_msg(user_id, BLACKLIST_EMPTY_FULL, get_blacklist_keyboard())
            return

        message = BLACKLIST_INFO.format(
            blacklist_data['first_name'],
            blacklist_data['last_name'],
            blacklist_data['profile_link']
        )

        attachments = []
        for photo in blacklist_data.get('photos', [])[:3]:
            attachments.append(f"photo{photo['owner_id']}_{photo['vk_photo_id']}")

        if attachments:
            write_msg(user_id, message, get_blacklist_keyboard(), ','.join(attachments))
        else:
            write_msg(user_id, message + NO_PHOTO_WARNING, get_blacklist_keyboard())

    def show_current_settings(user_id):
        """Показать текущие настройки пользователя"""
        user_data = adapter.get_user_data(user_id)
        if user_data:
            gender_text = GENDER_FEMALE if user_data.get('gender') == 1 else GENDER_MALE
            stats = adapter.get_candidates_statistics(user_id)

            message = SETTINGS_CURRENT.format(
                user_data.get('age', AGE_NOT_SPECIFIED),
                gender_text,
                user_data.get('city', CITY_NOT_SPECIFIED),
                stats['unviewed'],
                stats['favorites'],
                stats['blacklist']
            )
            write_msg(user_id, message)
        else:
            write_msg(user_id, SETTINGS_NO_REG, get_start_keyboard())

    # Основной цикл обработки сообщений
    while True:
        try:
            vk_session = vk_api.VkApi(token=token_vk)
            longpoll = VkLongPoll(vk_session, wait=25)
            events = longpoll.check()

            for event in events:
                if event.type == VkEventType.MESSAGE_NEW and event.to_me:
                    user_id = event.user_id
                    text = event.text.strip()

                    print(f"Сообщение от {user_id}: '{text}'")

                    # Приветствие
                    if text.lower() in ['привет', 'старт', 'начать', 'start'] or '👋' in text:
                        write_msg(user_id, WELCOME_MESSAGE, get_start_keyboard())

                    # Начало поиска / Создать анкету
                    elif text.lower() in ['начать поиск', 'поиск', 'создать анкету'] or 'начать поиск' in text.lower():
                        existing_user = adapter.get_user_data(user_id)

                        if existing_user:
                            adapter.reset_viewed_candidates(user_id)
                            write_msg(user_id, REG_ALREADY_REGISTERED, get_main_keyboard())
                        else:
                            temp_user_data[user_id] = {"step": "возраст"}
                            write_msg(user_id, REG_ENTER_AGE)

                    # Регистрация: возраст
                    elif user_id in temp_user_data and temp_user_data[user_id].get("step") == "возраст":
                        if text.lower().isdigit() and 14 <= int(text.lower()) <= 100:
                            temp_user_data[user_id]['age'] = int(text.lower())
                            temp_user_data[user_id]['step'] = "город"
                            write_msg(user_id, REG_ENTER_CITY)
                        else:
                            write_msg(user_id, REG_INVALID_AGE)

                    # Регистрация: город
                    elif user_id in temp_user_data and temp_user_data[user_id].get("step") == "город":
                        if len(text) >= 2:
                            temp_user_data[user_id]['city'] = text
                            temp_user_data[user_id]['step'] = "пол"
                            write_msg(user_id, REG_ENTER_GENDER)
                        else:
                            write_msg(user_id, REG_INVALID_CITY)

                    # Регистрация: пол и сохранение
                    elif user_id in temp_user_data and temp_user_data[user_id].get("step") == "пол":
                        if text.lower() in ['1', '2']:
                            user_data = {
                                "vk_user_id": user_id,
                                "age": temp_user_data[user_id]['age'],
                                "gender": int(text.lower()),
                                "city": temp_user_data[user_id]['city']
                            }

                            adapter.save_or_update_user(user_data)
                            del temp_user_data[user_id]

                            gender_text = GENDER_FEMALE if int(text.lower()) == 1 else GENDER_MALE
                            write_msg(user_id,
                                      REG_COMPLETE.format(
                                          user_data['age'],
                                          user_data['city'],
                                          gender_text
                                      ),
                                      get_main_keyboard())
                        else:
                            write_msg(user_id, REG_INVALID_GENDER)

                    # Смотреть анкеты - с эмодзи
                    elif text == '👀 Смотреть анкеты' or text.lower() == 'смотреть анкеты':
                        existing_user = adapter.get_user_data(user_id)

                        if not existing_user:
                            write_msg(user_id, NEED_SETTINGS, get_start_keyboard())
                            continue

                        show_candidate_from_db_or_api(user_id)

                    # Кнопка "Нравится" - с эмодзи
                    elif text == '❤️ Нравится' or text.lower() == 'нравится':
                        current = adapter.get_current_candidate(user_id)
                        if current:
                            adapter.add_to_favorites(user_id, current['vk_user_id'])
                            write_msg(user_id, ADDED_TO_FAVORITES, get_profiles_keyboard())
                            show_candidate_from_db_or_api(user_id)
                        else:
                            write_msg(user_id, SELECT_CANDIDATE_FIRST, get_main_keyboard())

                    # Кнопка "В черный список" - с эмодзи
                    elif text == '🚫 В черный список' or text.lower() == 'в черный список':
                        current = adapter.get_current_candidate(user_id)
                        if current:
                            adapter.add_to_blacklist(user_id, current['vk_user_id'])
                            write_msg(user_id, ADDED_TO_BLACKLIST, get_profiles_keyboard())
                            show_candidate_from_db_or_api(user_id)
                        else:
                            write_msg(user_id, SELECT_CANDIDATE_FIRST, get_main_keyboard())

                    # Кнопка "Следующий" - с эмодзи (только для обычных кандидатов)
                    elif text == '➡️ Следующий' or text.lower() == 'следующий':
                        current = adapter.get_current_candidate(user_id)
                        if current:
                            adapter.mark_candidate_as_viewed(user_id, current['vk_user_id'])
                        show_candidate_from_db_or_api(user_id)

                    # Мои фавориты - с эмодзи
                    elif text == '❤️ Мои фавориты' or text.lower() == 'мои фавориты':
                        favorites_count = adapter.get_favorites_count(user_id)

                        if favorites_count == 0:
                            write_msg(user_id, FAVORITES_EMPTY, get_main_keyboard())
                            continue

                        adapter.reset_favorites_only_view(user_id)
                        next_favorite = adapter.get_next_favorite(user_id)

                        if next_favorite:
                            show_favorite_info(user_id, next_favorite)
                        else:
                            write_msg(user_id, UNABLE_LOAD_FAVORITES, get_main_keyboard())

                    # Черный список - с эмодзи
                    elif text == '🚫 Черный список' or text.lower() == 'черный список':
                        blacklist_count = adapter.get_blacklist_count(user_id)

                        if blacklist_count == 0:
                            write_msg(user_id, BLACKLIST_EMPTY, get_main_keyboard())
                            continue

                        adapter.reset_blacklist_only_view(user_id)
                        next_blacklist = adapter.get_next_blacklist(user_id)

                        if next_blacklist:
                            show_blacklist_info(user_id, next_blacklist)
                        else:
                            write_msg(user_id, UNABLE_LOAD_BLACKLIST, get_main_keyboard())

                    # НАСТРОЙКА ПАРАМЕТРОВ ПОИСКА - исправленная проверка
                    elif text == '⚙️ Настроить параметры поиска' or text == '️⚙️ Настроить параметры поиска' or text.lower() == 'настроить параметры поиска':
                        existing_user = adapter.get_user_data(user_id)
                        if not existing_user:
                            write_msg(user_id, SETTINGS_NO_REG, get_start_keyboard())
                            continue

                        edit_user_data[user_id] = {'step': 'show_settings'}
                        show_current_settings(user_id)

                    # КНОПКИ В РАЗДЕЛЕ ФАВОРИТОВ
                    # 1. Следующий фаворит - с эмодзи
                    elif text == '➡️ Следующий фаворит' or text.lower() == 'следующий фаворит':
                        current_favorite = adapter.get_current_favorite(user_id)
                        if current_favorite:
                            adapter.mark_favorite_as_viewed(user_id, current_favorite['vk_user_id'])

                        next_favorite = adapter.get_next_favorite(user_id)
                        if next_favorite:
                            show_favorite_info(user_id, next_favorite)
                        else:
                            adapter.reset_favorites_only_view(user_id)
                            next_favorite = adapter.get_next_favorite(user_id)
                            if next_favorite:
                                write_msg(user_id, RESTARTING_FAVORITES, get_favorites_keyboard())
                                show_favorite_info(user_id, next_favorite)
                            else:
                                write_msg(user_id, NO_FAVORITES, get_main_keyboard())

                    # 2. Удалить фаворита - с эмодзи
                    elif text == '🗑️ Удалить фаворита' or text.lower() == 'удалить фаворита':
                        current_favorite = adapter.get_current_favorite(user_id)
                        if not current_favorite:
                            write_msg(user_id, SELECT_FAVORITE_TO_DELETE, get_favorites_keyboard())
                            continue

                        adapter.remove_from_favorites(user_id, current_favorite['vk_user_id'])
                        write_msg(user_id, REMOVED_FROM_FAVORITES, get_favorites_keyboard())

                        next_favorite = adapter.get_next_favorite(user_id)
                        if next_favorite:
                            show_favorite_info(user_id, next_favorite)
                        else:
                            favorites_count = adapter.get_favorites_count(user_id)
                            if favorites_count > 0:
                                adapter.reset_favorites_only_view(user_id)
                                next_favorite = adapter.get_next_favorite(user_id)
                                if next_favorite:
                                    write_msg(user_id, RESTARTING_FAVORITES, get_favorites_keyboard())
                                    show_favorite_info(user_id, next_favorite)
                                else:
                                    write_msg(user_id, ALL_FAVORITES_DELETED, get_main_keyboard())
                            else:
                                write_msg(user_id, ALL_FAVORITES_DELETED_EMPTY, get_main_keyboard())

                    # КНОПКИ В РАЗДЕЛЕ ЧЕРНОГО СПИСКА
                    # 1. Следующий в ЧС - с эмодзи
                    elif text == '➡️ Следующий в ЧС' or text.lower() == 'следующий в чс':
                        current_blacklist = adapter.get_current_blacklist(user_id)
                        if current_blacklist:
                            adapter.mark_blacklist_as_viewed(user_id, current_blacklist['vk_user_id'])

                        next_blacklist = adapter.get_next_blacklist(user_id)
                        if next_blacklist:
                            show_blacklist_info(user_id, next_blacklist)
                        else:
                            adapter.reset_blacklist_only_view(user_id)
                            next_blacklist = adapter.get_next_blacklist(user_id)
                            if next_blacklist:
                                write_msg(user_id, RESTARTING_BLACKLIST, get_blacklist_keyboard())
                                show_blacklist_info(user_id, next_blacklist)
                            else:
                                write_msg(user_id, BLACKLIST_EMPTY_FULL, get_main_keyboard())

                    # 2. Удалить из ЧС - с эмодзи
                    elif text == '🗑️ Удалить из ЧС' or text.lower() == 'удалить из чс':
                        current_blacklist = adapter.get_current_blacklist(user_id)
                        if not current_blacklist:
                            write_msg(user_id, SELECT_BLACKLIST_TO_DELETE, get_blacklist_keyboard())
                            continue

                        adapter.remove_from_blacklist(user_id, current_blacklist['vk_user_id'])
                        write_msg(user_id, REMOVED_FROM_BLACKLIST, get_blacklist_keyboard())

                        next_blacklist = adapter.get_next_blacklist(user_id)
                        if next_blacklist:
                            show_blacklist_info(user_id, next_blacklist)
                        else:
                            blacklist_count = adapter.get_blacklist_count(user_id)
                            if blacklist_count > 0:
                                adapter.reset_blacklist_only_view(user_id)
                                next_blacklist = adapter.get_next_blacklist(user_id)
                                if next_blacklist:
                                    write_msg(user_id, RESTARTING_BLACKLIST, get_blacklist_keyboard())
                                    show_blacklist_info(user_id, next_blacklist)
                                else:
                                    write_msg(user_id, ALL_BLACKLIST_DELETED, get_main_keyboard())
                            else:
                                write_msg(user_id, ALL_BLACKLIST_DELETED_EMPTY, get_main_keyboard())

                    # Редактирование параметров - когда пользователь уже в режиме редактирования
                    elif (user_id in edit_user_data and
                          edit_user_data[user_id]['step'] == 'show_settings'):
                        if text.lower() == '1' or 'возраст' in text.lower():
                            edit_user_data[user_id] = {'step': 'edit_age'}
                            write_msg(user_id, SETTINGS_ENTER_NEW_AGE)
                        elif text.lower() == '2' or 'пол' in text.lower():
                            edit_user_data[user_id] = {'step': 'edit_gender'}
                            write_msg(user_id, SETTINGS_ENTER_NEW_GENDER)
                        elif text.lower() == '3' or 'город' in text.lower():
                            edit_user_data[user_id] = {'step': 'edit_city'}
                            write_msg(user_id, SETTINGS_ENTER_NEW_CITY)
                        elif text.lower() == '4' or 'отмена' in text.lower():
                            del edit_user_data[user_id]
                            write_msg(user_id, SETTINGS_CANCELLED, get_main_keyboard())
                        else:
                            write_msg(user_id, SETTINGS_CHOOSE_PARAM)

                    # Редактирование возраста
                    elif (user_id in edit_user_data and
                          edit_user_data[user_id]['step'] == 'edit_age'):
                        if text.lower().isdigit() and 14 <= int(text.lower()) <= 100:
                            deleted_count = adapter.delete_candidates_on_parameter_change(user_id)
                            user_data = adapter.get_user_data(user_id)
                            user_data['age'] = int(text.lower())
                            adapter.save_or_update_user(user_data)
                            del edit_user_data[user_id]
                            write_msg(user_id,
                                      SETTINGS_AGE_UPDATED.format(text.lower(), deleted_count),
                                      get_main_keyboard())
                        else:
                            write_msg(user_id, REG_INVALID_AGE)

                    # Редактирование пола
                    elif (user_id in edit_user_data and
                          edit_user_data[user_id]['step'] == 'edit_gender'):
                        if text.lower() in ['1', '2']:
                            deleted_count = adapter.delete_candidates_on_parameter_change(user_id)
                            user_data = adapter.get_user_data(user_id)
                            user_data['gender'] = int(text.lower())
                            adapter.save_or_update_user(user_data)
                            del edit_user_data[user_id]
                            gender_text = GENDER_FEMALE if text.lower() == '1' else GENDER_MALE
                            write_msg(user_id,
                                      SETTINGS_GENDER_UPDATED.format(gender_text, deleted_count),
                                      get_main_keyboard())
                        else:
                            write_msg(user_id, REG_INVALID_GENDER)

                    # Редактирование города
                    elif (user_id in edit_user_data and
                          edit_user_data[user_id]['step'] == 'edit_city'):
                        if len(text) >= 2:
                            deleted_count = adapter.delete_candidates_on_parameter_change(user_id)
                            user_data = adapter.get_user_data(user_id)
                            user_data['city'] = text
                            adapter.save_or_update_user(user_data)
                            del edit_user_data[user_id]
                            write_msg(user_id,
                                      SETTINGS_CITY_UPDATED.format(text, deleted_count),
                                      get_main_keyboard())
                        else:
                            write_msg(user_id, REG_INVALID_CITY)

                    # Кнопка "Главное меню" - с эмодзи
                    elif text == '🏠 Главное меню' or text.lower() == 'главное меню':
                        if user_id in temp_user_data:
                            del temp_user_data[user_id]
                        if user_id in edit_user_data:
                            del edit_user_data[user_id]
                        write_msg(user_id, MAIN_MENU, get_main_keyboard())

                    # Назад - с эмодзи
                    elif text == 'Назад' or text.lower() == 'назад':
                        if user_id in temp_user_data:
                            del temp_user_data[user_id]
                        if user_id in edit_user_data:
                            del edit_user_data[user_id]
                        write_msg(user_id, BACK_TO_MAIN, get_main_keyboard())

                    # Информация о поиске - с эмодзи
                    elif text == '📋 Информация о поиске' or text.lower() == 'информация о поиске':
                        existing_user = adapter.get_user_data(user_id)
                        if existing_user:
                            stats = adapter.get_candidates_statistics(user_id)
                            gender_text = GENDER_FEMALE if existing_user.get('gender') == 1 else GENDER_MALE

                            message = STATISTICS_INFO.format(
                                stats['unviewed'],
                                stats['favorites'],
                                stats['blacklist'],
                                existing_user.get('age', AGE_NOT_SPECIFIED),
                                gender_text,
                                existing_user.get('city', CITY_NOT_SPECIFIED)
                            )
                            write_msg(user_id, message, get_main_keyboard())
                        else:
                            write_msg(user_id, STATISTICS_NO_REG, get_start_keyboard())

                    # Неизвестная команда для зарегистрированных пользователей
                    elif adapter.get_user_data(user_id):
                        if user_id in temp_user_data or user_id in edit_user_data:
                            write_msg(user_id, COMPLETE_REG_OR_CANCEL)
                        else:
                            write_msg(user_id, CHOOSE_ACTION, get_main_keyboard())

                    # Неизвестная команда для незарегистрированных пользователей
                    else:
                        write_msg(user_id, START_MESSAGE, get_start_keyboard())

            time.sleep(0.1)

        except (vk_api.exceptions.ApiHttpError, vk_api.exceptions.ApiError) as e:
            print(f"Ошибка VK API: {e}. Переподключение через 3 секунды...")
            time.sleep(3)

        except KeyboardInterrupt:
            print("\nБот остановлен пользователем")
            sys.exit(0)

        except Exception as e:
            print(f"Неожиданная ошибка: {e}. Продолжение работы через 5 секунд...")
            import traceback
            traceback.print_exc()
            time.sleep(5)
