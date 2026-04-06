import logging
import os
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes, CallbackQueryHandler
)
from video_generator import generate_video

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

user_settings = {}

def get_user_settings(user_id: int) -> dict:
    if user_id not in user_settings:
        user_settings[user_id] = {
            "language": "uk",
            "style": "dark",
            "font_size": 40,
        }
    return user_settings[user_id]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    keyboard = [
        [InlineKeyboardButton("⚙️ Налаштування", callback_data="settings")],
        [InlineKeyboardButton("ℹ️ Довідка", callback_data="help")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"👋 Привіт, {user.first_name}!\n\n"
        "🎬 Я створюю відео з твого тексту — з озвучкою та субтитрами.\n\n"
        "📝 *Просто надішли мені текст* — і я зроблю відео!\n\n"
        "Або оціни налаштування нижче 👇",
        parse_mode="Markdown",
        reply_markup=reply_markup,
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *Як користуватись ботом:*\n\n"
        "1️⃣ Надішли текст (до 500 символів)\n"
        "2️⃣ Я озвучу його та додам субтитри\n"
        "3️⃣ Отримай готове відео!\n\n"
        "⚙️ *Команди:*\n"
        "/start — Головне меню\n"
        "/settings — Налаштування\n"
        "/help — Довідка\n\n"
        "🌐 *Мови:* Українська, Англійська, Польська\n"
        "🎨 *Стилі:* Темний, Світлий, Синій",
        parse_mode="Markdown",
    )


async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_settings(update, context, from_command=True)


async def show_settings(update: Update, context: ContextTypes.DEFAULT_TYPE, from_command=False):
    user_id = update.effective_user.id
    settings = get_user_settings(user_id)

    lang_map = {"uk": "🇺🇦 Українська", "en": "🇬🇧 Англійська", "pl": "🇵🇱 Польська"}
    style_map = {"dark": "🌑 Темний", "light": "☀️ Світлий", "blue": "🔵 Синій"}

    keyboard = [
        [InlineKeyboardButton("🌐 Мова озвучки", callback_data="set_lang")],
        [InlineKeyboardButton("🎨 Стиль відео", callback_data="set_style")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = (
        "⚙️ *Налаштування*\n\n"
        f"🌐 Мова: {lang_map[settings['language']]}\n"
        f"🎨 Стиль: {style_map[settings['style']]}\n"
    )

    if from_command:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=reply_markup)
    else:
        await update.callback_query.edit_message_text(text, parse_mode="Markdown", reply_markup=reply_markup)


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    settings = get_user_settings(user_id)
    data = query.data

    if data == "settings":
        await show_settings(update, context)

    elif data == "help":
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")]]
        await query.edit_message_text(
            "📖 *Як користуватись:*\n\n"
            "Надішли текст — і я зроблю відео з озвучкою!\n\n"
            "Ліміт: 500 символів за раз.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    elif data == "back_to_menu":
        keyboard = [
            [InlineKeyboardButton("⚙️ Налаштування", callback_data="settings")],
            [InlineKeyboardButton("ℹ️ Довідка", callback_data="help")],
        ]
        await query.edit_message_text(
            "🎬 *Головне меню*\n\nНадішли текст — і я створю відео!",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    elif data == "set_lang":
        keyboard = [
            [InlineKeyboardButton("🇺🇦 Українська", callback_data="lang_uk")],
            [InlineKeyboardButton("🇬🇧 Англійська", callback_data="lang_en")],
            [InlineKeyboardButton("🇵🇱 Польська", callback_data="lang_pl")],
            [InlineKeyboardButton("🔙 Назад", callback_data="settings")],
        ]
        await query.edit_message_text(
            "🌐 Оберіть мову озвучки:",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    elif data.startswith("lang_"):
        lang = data.split("_")[1]
        settings["language"] = lang
        await show_settings(update, context)

    elif data == "set_style":
        keyboard = [
            [InlineKeyboardButton("🌑 Темний", callback_data="style_dark")],
            [InlineKeyboardButton("☀️ Світлий", callback_data="style_light")],
            [InlineKeyboardButton("🔵 Синій", callback_data="style_blue")],
            [InlineKeyboardButton("🔙 Назад", callback_data="settings")],
        ]
        await query.edit_message_text(
            "🎨 Оберіть стиль відео:",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    elif data.startswith("style_"):
        style = data.split("_")[1]
        settings["style"] = style
        await show_settings(update, context)


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user_id = update.effective_user.id
    settings = get_user_settings(user_id)

    if len(text) > 500:
        await update.message.reply_text(
            "⚠️ Текст занадто довгий! Максимум 500 символів.\n"
            f"Зараз: {len(text)} символів."
        )
        return

    if len(text) < 5:
        await update.message.reply_text("⚠️ Текст занадто короткий. Напишіть більше!")
        return

    status_msg = await update.message.reply_text(
        "⏳ Генерую відео...\n\n"
        "🎙️ Озвучка тексту...\n"
        "🎬 Це займе 15-30 секунд."
    )

    try:
        loop = asyncio.get_event_loop()
        video_path = await loop.run_in_executor(
            None,
            generate_video,
            text,
            settings["language"],
            settings["style"],
            user_id,
        )

        await status_msg.edit_text("📤 Відправляю відео...")

        with open(video_path, "rb") as video_file:
            await update.message.reply_video(
                video=video_file,
                caption=f"🎬 Твоє відео готове!\n\n📝 _{text[:80]}{'...' if len(text) > 80 else ''}_",
                parse_mode="Markdown",
            )

        await status_msg.delete()

        # Cleanup
        if os.path.exists(video_path):
            os.remove(video_path)

    except Exception as e:
        logger.error(f"Error generating video: {e}")
        await status_msg.edit_text(
            "❌ Виникла помилка при генерації відео.\n"
            "Спробуй ще раз або зменш текст."
        )


def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("settings", settings_command))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    logger.info("Bot started!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
