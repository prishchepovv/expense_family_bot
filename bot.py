import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application, CommandHandler, MessageHandler, 
    filters, CallbackContext, ConversationHandler
)
from database import Database
from keyboards import (
    get_main_keyboard, get_categories_keyboard, 
    get_statistics_keyboard, get_back_keyboard,
    get_settings_keyboard, get_detailed_stats_keyboard,  # Добавлено
    get_categories_for_filter  # Добавлено
)
from config import BOT_TOKEN
from datetime import datetime  # Добавлено

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Состояния для ConversationHandler
AMOUNT, CATEGORY, DESCRIPTION = range(3)
# Добавим новые состояния для детализации
DETAILED_STATS, DATE_RANGE, CATEGORY_FILTER = range(3, 6)

class ExpenseBot:
    def __init__(self, token):
        self.application = Application.builder().token(token).build()
        self.db = Database()
        self.setup_handlers()

    def _format_date(self, date_string):
        """Вспомогательный метод для форматирования даты из базы данных"""
        try:
            if '.' in date_string:
                return datetime.strptime(date_string, '%Y-%m-%d %H:%M:%S.%f').strftime('%d.%m.%Y')
            else:
                return datetime.strptime(date_string, '%Y-%m-%d %H:%M:%S').strftime('%d.%m.%Y')
        except ValueError:
            return date_string.split()[0]       

    def setup_handlers(self):
        """Настройка обработчиков команд"""
        
        # Обработчики команд
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("help", self.help_command))
        
        # ConversationHandler для добавления расходов
        conv_handler = ConversationHandler(
            entry_points=[MessageHandler(filters.Regex("^💸 Добавить расход$"), self.start_add_expense)],
            states={
                AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.get_amount)],
                CATEGORY: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.get_category)],
                DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.get_description)],
            },
            fallbacks=[MessageHandler(filters.Regex("^↩️ Назад$"), self.cancel)],
        )
        self.application.add_handler(conv_handler)
        
        # Обработчики сообщений
        self.application.add_handler(MessageHandler(filters.Regex("^📊 Статистика$"), self.show_statistics_menu))
        self.application.add_handler(MessageHandler(filters.Regex("^📅 Сегодня$"), self.show_today_stats))
        self.application.add_handler(MessageHandler(filters.Regex("^📆 Неделя$"), self.show_week_stats))
        self.application.add_handler(MessageHandler(filters.Regex("^📈 Месяц$"), self.show_month_stats))
        self.application.add_handler(MessageHandler(filters.Regex("^⚙️ Настройки$"), self.show_settings))
        self.application.add_handler(MessageHandler(filters.Regex("^ℹ️ Помощь$"), self.help_command))
        self.application.add_handler(MessageHandler(filters.Regex("^↩️ Назад$"), self.back_to_main))
        
        # Обработчик статистики из меню статистики
        self.application.add_handler(MessageHandler(filters.Regex("^📊 Сегодня$"), self.show_today_detailed))
        self.application.add_handler(MessageHandler(filters.Regex("^📅 Неделя$"), self.show_week_detailed))
        self.application.add_handler(MessageHandler(filters.Regex("^📈 Месяц$"), self.show_month_detailed))
        
        # Добавляем обработчики для детализации
        self.application.add_handler(MessageHandler(filters.Regex("^📋 Детализация$"), self.show_detailed_stats_menu))
        self.application.add_handler(MessageHandler(filters.Regex("^📋 Все расходы$"), self.show_all_expenses))
        self.application.add_handler(MessageHandler(filters.Regex("^💰 Самые крупные$"), self.show_largest_expenses))
        self.application.add_handler(MessageHandler(filters.Regex("^↩️ Назад в статистику$"), self.back_to_statistics))

        # Убираем ConversationHandler и добавляем простые обработчики для даты и категории
        self.application.add_handler(MessageHandler(filters.Regex("^📅 По дате$"), self.ask_date_range))
        self.application.add_handler(MessageHandler(filters.Regex("^📁 По категории$"), self.ask_category_filter))

        # Обработчики для ответов на запросы даты и категории
        self.application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND & ~filters.Regex("^↩️ Назад$"),
            self.handle_detailed_input
        ))

    async def start(self, update: Update, context: CallbackContext):
        """Обработчик команды /start"""
        user = update.effective_user
        self.db.add_user(user.id, user.username, user.first_name)
        
        welcome_text = f"""
👋 Васап, {user.first_name}!

Я бот для учета твоих космических трат...

📊 **Возможности:**
• 💸 Быстрое добавление расходов
• 📊 Статистика за день, неделю и месяц
• 📈 Детализация по категориям
• 👥 Учет для двух пользователей

Нажмите «💸 Добавить расход» чтобы начать!
        """
        
        await update.message.reply_text(
            welcome_text,
            reply_markup=get_main_keyboard(),
            parse_mode='Markdown'
        )

    async def start_add_expense(self, update: Update, context: CallbackContext):
        """Начало процесса добавления расхода"""
        await update.message.reply_text(
            "💵 Введи сумму расхода:",
            reply_markup=get_back_keyboard()
        )
        return AMOUNT

    async def get_amount(self, update: Update, context: CallbackContext):
        """Получение суммы расхода"""
        user_input = update.message.text

        # Обработка кнопки "Назад"
        if user_input == "↩️ Назад":
            await update.message.reply_text(
                "❌ Операция отменена",
                reply_markup=get_main_keyboard()
            )
            context.user_data.clear()
            return ConversationHandler.END
        
        try:
            amount = float(user_input.replace(',', '.'))
            if amount <= 0:
                await update.message.reply_text("❌ Сумма должна быть положительной. Попробуй снова:")
                return AMOUNT
            
            context.user_data['amount'] = amount
            await update.message.reply_text(
                "📁 Выбери категорию:",
                reply_markup=get_categories_keyboard()
            )
            return CATEGORY
        
        except ValueError:
            await update.message.reply_text("❌ Пожалуйста, введи корректную сумму (например: 150.50):")
            return AMOUNT

    async def get_category(self, update: Update, context: CallbackContext):
        """Получение категории"""
        category = update.message.text
        if category == "↩️ Назад":
            await update.message.reply_text(
                "💵 Введи сумму расхода:",
                reply_markup=get_back_keyboard()
            )
            return AMOUNT
        
        # Убираем эмодзи из категории
        clean_category = ' '.join(category.split()[1:]) if ' ' in category else category
        
        context.user_data['category'] = clean_category
        await update.message.reply_text(
            "📝 Введи описание (или нажмите 'Пропустить'):",
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Пропустить")], [KeyboardButton("↩️ Назад")]], resize_keyboard=True)
        )
        return DESCRIPTION

    async def get_description(self, update: Update, context: CallbackContext):
        """Получение описания"""
        description = update.message.text
        
        if description == "↩️ Назад":
            await update.message.reply_text(
                "📁 Выбери категорию:",
                reply_markup=get_categories_keyboard()
            )
            return CATEGORY
        
        if description == "Пропустить":
            description = ""
        
        # Сохраняем расход в базу
        user_id = update.effective_user.id
        amount = context.user_data['amount']
        category = context.user_data['category']
        
        self.db.add_expense(user_id, amount, category, description)
        
        # Формируем сообщение о успешном добавлении
        message = f"""
✅ Расход добавлен!

💵 Сумма: {amount} руб.
📁 Категория: {category}
📝 Описание: {description if description else "не указано"}
        """
        
        await update.message.reply_text(
            message,
            reply_markup=get_main_keyboard()
        )
        
        # Очищаем временные данные
        context.user_data.clear()
        return ConversationHandler.END

    async def cancel(self, update: Update, context: CallbackContext):
        """Отмена операции"""
        context.user_data.clear()
        await update.message.reply_text(
            "❌ Операция отменена",
            reply_markup=get_main_keyboard()
        )
        return ConversationHandler.END

    async def show_statistics_menu(self, update: Update, context: CallbackContext):
        """Показ меню статистики"""
        await update.message.reply_text(
            "📊 Выбери тип статистики:",
            reply_markup=get_statistics_keyboard()
        )

    async def show_today_stats(self, update: Update, context: CallbackContext):
        """Показ статистики за сегодня"""
        user_id = update.effective_user.id
        total = self.db.get_total_today(user_id)
        expenses = self.db.get_today_expenses(user_id)
        
        message = f"📊 **Расходы за сегодня**\n\n"
        message += f"💵 **Общая сумма:** {total:.2f} руб.\n\n"
        
        if expenses:
            message += "**По категориям:**\n"
            for category, amount in expenses:
                message += f"• {category}: {amount:.2f} руб.\n"
        else:
            message += "📝 Расходов за сегодня нет"
        
        await update.message.reply_text(
            message,
            reply_markup=get_main_keyboard(),
            parse_mode='Markdown'
        )

    async def show_week_stats(self, update: Update, context: CallbackContext):
        """Показ статистики за неделю"""
        user_id = update.effective_user.id
        total = self.db.get_total_week(user_id)
        expenses = self.db.get_week_expenses(user_id)
        
        message = f"📅 **Расходы за текущую неделю**\n\n"
        message += f"💵 **Общая сумма:** {total:.2f} руб.\n\n"
        
        if expenses:
            message += "**По категориям:**\n"
            for category, amount in expenses:
                percentage = (amount / total) * 100 if total > 0 else 0
                message += f"• {category}: {amount:.2f} руб. ({percentage:.1f}%)\n"
        else:
            message += "📝 Расходов за неделю нет"
        
        await update.message.reply_text(
            message,
            reply_markup=get_main_keyboard(),
            parse_mode='Markdown'
        )

    async def show_month_stats(self, update: Update, context: CallbackContext):
        """Показ статистики за месяц"""
        user_id = update.effective_user.id
        total = self.db.get_total_month(user_id)
        expenses = self.db.get_month_expenses(user_id)
        
        message = f"📈 **Расходы за текущий месяц**\n\n"
        message += f"💵 **Общая сумма:** {total:.2f} руб.\n\n"
        
        if expenses:
            message += "**По категориям:**\n"
            for category, amount in expenses:
                percentage = (amount / total) * 100 if total > 0 else 0
                message += f"• {category}: {amount:.2f} руб. ({percentage:.1f}%)\n"
        else:
            message += "📝 Расходов за месяц нет"
        
        await update.message.reply_text(
            message,
            reply_markup=get_main_keyboard(),
            parse_mode='Markdown'
        )

    async def show_today_detailed(self, update: Update, context: CallbackContext):
        """Детальная статистика за сегодня"""
        await self.show_today_stats(update, context)

    async def show_week_detailed(self, update: Update, context: CallbackContext):
        """Детальная статистика за неделю"""
        await self.show_week_stats(update, context)

    async def show_month_detailed(self, update: Update, context: CallbackContext):
        """Детальная статистика за месяц"""
        await self.show_month_stats(update, context)

    # НОВЫЕ МЕТОДЫ ДЛЯ ДЕТАЛИЗАЦИИ

    async def show_detailed_stats_menu(self, update: Update, context: CallbackContext):
        """Показ меню детализированной статистики"""
        await update.message.reply_text(
            "📋 **Детализированная статистика**\n\n"
            "Выберите тип отчета:",
            reply_markup=get_detailed_stats_keyboard(),
            parse_mode='Markdown'
        )

    async def show_all_expenses(self, update: Update, context: CallbackContext):
        """Показ всех расходов"""
        user_id = update.effective_user.id
        expenses = self.db.get_all_expenses(user_id)
        
        if not expenses:
            await update.message.reply_text(
                "📝 У вас пока нет записей о расходах",
                reply_markup=get_detailed_stats_keyboard()
            )
            return
        
        message = "📋 **Все расходы**\n\n"
        total = 0
        
        for i, (category, amount, description, date) in enumerate(expenses, 1):
            total += amount
            #Исправляем парсинг даты с микросекундами
            try:
                # Пробуем разные форматы даты
                if '.' in date:
                    # Формат с микросекундами: 2024-01-01 12:00:00.123456
                    date_str = datetime.strptime(date, '%Y-%m-%d %H:%M:%S.%f').strftime('%d.%m.%Y')
                else:
                    # Формат без микросекунд: 2024-01-01 12:00:00
                    date_str = datetime.strptime(date, '%Y-%m-%d %H:%M:%S').strftime('%d.%m.%Y')
            except ValueError:
                # Если не получается распарсить, используем исходную дату
                date_str = date.split()[0]  # Берем только дату без времени

            desc = description if description else "без описания"
            message += f"{i}. **{category}** - {amount:.2f} руб.\n"
            message += f"   📅 {date_str} | 📝 {desc}\n\n"

        message += f"💵 **Итого:** {total:.2f} руб.\n"
        message += f"📊 **Всего записей:** {len(expenses)}"

        # Разбиваем сообщение если оно слишком длинное
        if len(message) > 4000:
            parts = [message[i:i+4000] for i in range(0, len(message), 4000)]
            for part in parts:
                await update.message.reply_text(part, parse_mode='Markdown')
        else:
            await update.message.reply_text(
                message,
                reply_markup=get_detailed_stats_keyboard(),
                parse_mode='Markdown'
            )

    async def ask_date_range(self, update: Update, context: CallbackContext):
        """Запрос периода дат"""
        await update.message.reply_text(
            "📅 **Введите период в формате:**\n"
            "**ДД.ММ.ГГГГ-ДД.ММ.ГГГГ**\n\n"
            "Например: 01.12.2024-15.12.2024\n"
            "Или введите 'месяц' для текущего месяца",
            reply_markup=get_back_keyboard()
        )

    async def process_date_range(self, update: Update, context: CallbackContext):
        """Обработка введенного периода"""
        user_input = update.message.text.strip()
        user_id = update.effective_user.id
        
        if user_input.lower() == 'месяц':
            # Текущий месяц
            today = datetime.now()
            start_date = today.replace(day=1).strftime('%Y-%m-%d')
            end_date = today.strftime('%Y-%m-%d')
            period_text = f"за {today.strftime('%B %Y')}"
        else:
            try:
                # Парсим ввод пользователя
                start_str, end_str = user_input.split('-')
                start_date = datetime.strptime(start_str.strip(), '%d.%m.%Y').strftime('%Y-%m-%d')
                end_date = datetime.strptime(end_str.strip(), '%d.%m.%Y').strftime('%Y-%m-%d')
                period_text = f"с {start_str} по {end_str}"
            except ValueError:
                await update.message.reply_text(
                    "❌ Неверный формат даты. Используйте ДД.ММ.ГГГГ-ДД.ММ.ГГГГ\n"
                    "Попробуйте снова:",
                    reply_markup=get_back_keyboard()
                )
                return
        
        expenses = self.db.get_expenses_by_date_range(user_id, start_date, end_date)
        
        if not expenses:
            await update.message.reply_text(
                f"📝 Расходов {period_text} не найдено",
                reply_markup=get_detailed_stats_keyboard()
            )
            return
        
        message = f"📅 **Расходы {period_text}**\n\n"
        total = 0
        
        for i, (category, amount, description, date) in enumerate(expenses, 1):
            total += amount
            date_str = self._format_date(date)
            desc = description if description else "без описания"
            message += f"{i}. **{category}** - {amount:.2f} руб.\n"
            message += f"   📅 {date_str} | 📝 {desc}\n\n"
        
        message += f"💵 **Итого:** {total:.2f} руб.\n"
        message += f"📊 **Всего записей:** {len(expenses)}"
        
        await update.message.reply_text(
            message,
            reply_markup=get_detailed_stats_keyboard(),
            parse_mode='Markdown'
        )

    async def ask_category_filter(self, update: Update, context: CallbackContext):
        """Запрос категории для фильтрации"""
        await update.message.reply_text(
            "📁 **Выберите категорию для фильтрации:**",
            reply_markup=get_categories_for_filter()
        )

    async def process_category_filter(self, update: Update, context: CallbackContext):
        """Обработка выбранной категории"""
        category_input = update.message.text
        user_id = update.effective_user.id
        
        if category_input == "↩️ Назад":
            await update.message.reply_text(
                "📋 Выберите тип отчета:",
                reply_markup=get_detailed_stats_keyboard()
            )
            return
        
        if category_input == "📋 Все категории":
            await self.show_all_expenses(update, context)
            return
        
        # Убираем эмодзи для поиска в базе
        clean_category = ' '.join(category_input.split()[1:]) if ' ' in category_input else category_input
        
        expenses = self.db.get_expenses_by_category(user_id, clean_category)
        
        if not expenses:
            await update.message.reply_text(
                f"📝 Расходов по категории '{category_input}' не найдено",
                reply_markup=get_detailed_stats_keyboard()
            )
            return
        
        message = f"📁 **Расходы по категории: {category_input}**\n\n"
        total = 0
        
        for i, (category, amount, description, date) in enumerate(expenses, 1):
            total += amount
            date_str = self._format_date(date)
            desc = description if description else "без описания"
            message += f"{i}. {amount:.2f} руб. | 📅 {date_str}\n"
            message += f"   📝 {desc}\n\n"
        
        message += f"💵 **Итого по категории:** {total:.2f} руб.\n"
        message += f"📊 **Всего записей:** {len(expenses)}"
        
        await update.message.reply_text(
            message,
            reply_markup=get_detailed_stats_keyboard(),
            parse_mode='Markdown'
        )

    async def show_largest_expenses(self, update: Update, context: CallbackContext):
        """Показ самых крупных расходов"""
        user_id = update.effective_user.id
        expenses = self.db.get_largest_expenses(user_id)
        
        if not expenses:
            await update.message.reply_text(
                "📝 У вас пока нет записей о расходах",
                reply_markup=get_detailed_stats_keyboard()
            )
            return
        
        message = "💰 **Самые крупные расходы**\n\n"
        total = 0
        
        for i, (category, amount, description, date) in enumerate(expenses, 1):
            total += amount

            # Исправленный парсинг даты с микросекундами
            try:
                if '.' in date:
                    date_str = datetime.strptime(date, '%Y-%m-%d %H:%M:%S.%f').strftime('%d.%m.%Y')
                else:
                    date_str = datetime.strptime(date, '%Y-%m-%d %H:%M:%S').strftime('%d.%m.%Y')
            except ValueError:
                date_str = date.split()[0]  # Берем только дату без времени

            desc = description if description else "без описания"
            message += f"{i}. **{category}** - {amount:.2f} руб.\n"
            message += f"   📅 {date_str} | 📝 {desc}\n\n"

        message += f"💵 **Сумма топ-{len(expenses)} расходов:** {total:.2f} руб."

        await update.message.reply_text(
            message,
            reply_markup=get_detailed_stats_keyboard(),
            parse_mode='Markdown'
        )

    async def back_to_statistics(self, update: Update, context: CallbackContext):
        """Возврат в меню статистики"""
        await update.message.reply_text(
            "📊 Выбери тип статистики:",
            reply_markup=get_statistics_keyboard()
        )

    async def show_settings(self, update: Update, context: CallbackContext):
        """Показ настроек"""
        await update.message.reply_text(
            "⚙️ **Настройки**\n\nЗдесь ты можешь настроить бота под себя",
            reply_markup=get_settings_keyboard(),
            parse_mode='Markdown'
        )

    async def handle_detailed_input(self, update: Update, context: CallbackContext):
        """Обработка ввода для детализированной статистики"""
        user_input = update.message.text.strip()

        # Проверяем, является ли ввод периодом дат (формат ДД.ММ.ГГГГ-ДД.ММ.ГГГГ)
        if self._is_date_period(user_input):
            await self.process_date_range(update, context)
        # Проверяем, является ли ввод категорией (содержит эмодзи)
        elif any(char in user_input for char in ['🍔', '⛽️', '🏠', '👗', '💊', '🍺', '📱', '💡', '🎁', '💸', '🚬', '🐈']):
            await self.process_category_filter(update, context)
        else:
            await update.message.reply_text(
                "❌ Не понимаю ваш запрос. Используйте кнопки меню.",
                reply_markup=get_detailed_stats_keyboard()
            )
    
    def _is_date_period(self, text):
        """Проверяет, является ли текст периодом дат"""
        text = text.strip().lower()

        # Проверяем ключевое слово "месяц"
        if text == 'месяц':
            return True
        
        # Проверяем формат ДД.ММ.ГГГГ-ДД.ММ.ГГГГ
        if '-' in text:
            parts = text.split('-')
            if len(parts) == 2:
                start, end = parts
                # Проверяем, что обе части похожи на даты
                if self._is_date_like(start) and self._is_date_like(end):
                    return True      
        return False
    
    def _is_date_like(self, text):
        """Проверяет, похож ли текст на дату в формате ДД.ММ.ГГГГ"""
        text = text.strip()

        # Проверяем длину и наличие точек
        if len(text) == 10 and text.count('.') == 2:
            parts = text.split('.')
            if len(parts) == 3:
                day, month, year = parts
                # Проверяем, что все части - числа
                if day.isdigit() and month.isdigit() and year.isdigit():
                    # Проверяем разумные диапазоны
                    day_int = int(day)
                    month_int = int(month)
                    year_int = int(year)
                    if (1 <= day_int <= 31 and 1 <= month_int <= 12 and
                        2000 <= year_int <= 2100):
                        return True
        return False

    async def help_command(self, update: Update, context: CallbackContext):
        """Показ помощи"""
        help_text = """
ℹ️ **Помощь по боту**

**Основные команды:**
• 💸 Добавить расход - быстрая запись расхода
• 📊 Статистика - обзор расходов
• 📅 Сегодня - расходы за сегодня
• 📆 Неделя - расходы за текущую неделю
• 📈 Месяц - расходы за текущий месяц
• 📋 Детализация - подробные отчеты по расходам

**Как пользоваться:**
1. Нажми «💸 Добавить расход»
2. Введи сумму
3. Выбери категорию
4. Добавь описание (необязательно)

**Категории расходов:**
🍔 Еда, 🚗 Транспорт, 🏠 Дом, 👗 Одежда и другие

Для начала работы нажми /start
        """
        await update.message.reply_text(
            help_text,
            reply_markup=get_main_keyboard(),
            parse_mode='Markdown'
        )

    async def back_to_main(self, update: Update, context: CallbackContext):
        """Возврат в главное меню"""
        await update.message.reply_text(
            "Главное меню:",
            reply_markup=get_main_keyboard()
        )

    def run(self):
        """Запуск бота"""
        logger.info("Бот запущен...")
        self.application.run_polling()

if __name__ == '__main__':
    bot = ExpenseBot(BOT_TOKEN)
    bot.run()