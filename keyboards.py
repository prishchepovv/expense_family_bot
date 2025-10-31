from telegram import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def get_main_keyboard():
    """Основная клавиатура"""
    keyboard = [
        [KeyboardButton("💸 Добавить расход"), KeyboardButton("📊 Статистика")],
        [KeyboardButton("📅 Сегодня"), KeyboardButton("📆 Неделя")],
        [KeyboardButton("📈 Месяц"), KeyboardButton("⚙️ Настройки")],
        [KeyboardButton("ℹ️ Помощь")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_categories_keyboard():
    """Клавиатура с категориями"""
    categories = [
        ["🍔 Еда", "⛽️ Бензин", "🏠 Дом"],
        ["👗 Одежда", "💊 Здоровье", "🍺 Посиделки"],
        ["📱 Связь", "💡 Коммуналка", "🎁 Подарки"],
        ["💸 Кредиты", "🚬 Курение", "🐈 Животные"],
        ["↩️ Назад"]
    ]
    return ReplyKeyboardMarkup(categories, resize_keyboard=True)

def get_statistics_keyboard():
    """Клавиатура для статистики"""
    keyboard = [
        [KeyboardButton("📊 Сегодня"), KeyboardButton("📅 Неделя")],
        [KeyboardButton("📈 Месяц"), KeyboardButton("📋 Детализация")],
        [KeyboardButton("↩️ Назад")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_detailed_stats_keyboard():
    """Клавиатура для детализированной статистики"""
    keyboard = [
        [KeyboardButton("📋 Все расходы"), KeyboardButton("📅 По дате")],
        [KeyboardButton("📁 По категории"), KeyboardButton("💰 Самые крупные")],
        [KeyboardButton("↩️ Назад в статистику")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_categories_for_filter():
    """Клавиатура с категориями для фильтрации"""
    categories = [
        ["🍔 Еда", "⛽️ Бензин", "🏠 Дом"],
        ["👗 Одежда", "💊 Здоровье", "🍺 Посиделки"],
        ["📱 Связь", "💡 Коммуналка", "🎁 Подарки"],
        ["💸 Кредиты", "🚬 Курение", "🐈 Животные"],
        ["📋 Все категории", "↩️ Назад"]
    ]
    return ReplyKeyboardMarkup(categories, resize_keyboard=True)

def get_back_keyboard():
    """Клавиатура с кнопкой Назад"""
    keyboard = [[KeyboardButton("↩️ Назад")]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_settings_keyboard():
    """Клавиатура настроек"""
    keyboard = [
        [KeyboardButton("👤 Мой профиль"), KeyboardButton("📊 Лимиты")],
        [KeyboardButton("🔔 Уведомления"), KeyboardButton("↩️ Назад")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)