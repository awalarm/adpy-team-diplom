from vk_api.keyboard import VkKeyboard, VkKeyboardColor


def get_start_keyboard():
    """Стартовая клавиатура"""
    keyboard = VkKeyboard(one_time=True)
    keyboard.add_button("Создать анкету", color=VkKeyboardColor.PRIMARY)
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
    keyboard.add_button("🗑️ Удалить фаворита", color=VkKeyboardColor.NEGATIVE)
    keyboard.add_button("➡️ Следующий фаворит", color=VkKeyboardColor.PRIMARY)
    keyboard.add_line()
    keyboard.add_button("📋 Главное меню", color=VkKeyboardColor.SECONDARY)
    return keyboard.get_keyboard()


def get_blacklist_keyboard():
    """Клавиатура черного списка"""
    keyboard = VkKeyboard(one_time=False)
    keyboard.add_button("🗑️ Удалить из ЧС", color=VkKeyboardColor.NEGATIVE)
    keyboard.add_button("➡️ Следующий в ЧС", color=VkKeyboardColor.PRIMARY)
    keyboard.add_line()
    keyboard.add_button("📋 Главное меню", color=VkKeyboardColor.SECONDARY)
    return keyboard.get_keyboard()
