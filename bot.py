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
    get_settings_keyboard
)
from config import BOT_TOKEN

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Состояния для ConversationHandler
AMOUNT, CATEGORY, DESCRIPTION = range(3)

class ExpenseBot:
    def __init__(self, token):
        self.application = Application.builder().token(token).build()
        self.db = Database()
        self.setup_handlers()

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
        self.application.add_handler(MessageHandler(filters.Regex("^📆 Месяц$"), self.show_month_stats))
        self.application.add_handler(MessageHandler(filters.Regex("^⚙️ Настройки$"), self.show_settings))
        self.application.add_handler(MessageHandler(filters.Regex("^ℹ️ Помощь$"), self.help_command))
        self.application.add_handler(MessageHandler(filters.Regex("^↩️ Назад$"), self.back_to_main))
        
        # Обработчик статистики
        self.application.add_handler(MessageHandler(filters.Regex("^📊 Сегодня$"), self.show_today_detailed))
        self.application.add_handler(MessageHandler(filters.Regex("^📈 Месяц$"), self.show_month_detailed))

    async def start(self, update: Update, context: CallbackContext):
        """Обработчик команды /start"""
        user = update.effective_user
        self.db.add_user(user.id, user.username, user.first_name)
        
        welcome_text = f"""
👋 Васап, {user.first_name}!

Я бот для учета твоих космических трат...

📊 **Возможности:**
• 💸 Быстрое добавление расходов
• 📊 Статистика за день и месяц
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
        try:
            amount = float(update.message.text.replace(',', '.'))
            if amount <= 0:
                await update.message.reply_text("❌ Сумма должна быть положительной, тупырка. Попробуй снова:")
                return AMOUNT
            
            context.user_data['amount'] = amount
            await update.message.reply_text(
                "📁 Выбери категорию:",
                reply_markup=get_categories_keyboard()
            )
            return CATEGORY
            
        except ValueError:
            await update.message.reply_text("❌ Пожалуйста, пораскинь извилинами и введи корректную сумму (например: 150.50):")
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

    async def show_month_detailed(self, update: Update, context: CallbackContext):
        """Детальная статистика за месяц"""
        await self.show_month_stats(update, context)

    async def show_settings(self, update: Update, context: CallbackContext):
        """Показ настроек"""
        await update.message.reply_text(
            "⚙️ **Настройки**\n\nЗдесь ты можешь настроить бота под себя",
            reply_markup=get_settings_keyboard(),
            parse_mode='Markdown'
        )

    async def help_command(self, update: Update, context: CallbackContext):
        """Показ помощи"""
        help_text = """
ℹ️ **Помощь по боту**

**Основные команды:**
• 💸 Добавить расход - быстрая запись расхода
• 📊 Статистика - обзор расходов
• 📅 Сегодня - расходы за сегодня
• 📆 Месяц - расходы за текущий месяц

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