# -*- coding: utf-8 -*-
from telegram import Update, InputFile
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from PIL import Image, ImageDraw, ImageFont, ImageOps
import requests
from io import BytesIO
import os

# Ваш токен
BOT_TOKEN = "8177576526:AAENu0zsL6KRr20VZ4c8ymLh3pIbj_nCaTc"

# Путь к папке шрифтов
FONT_DIR = os.path.join(os.path.dirname(__file__), "fonts")
REGULAR_FONT_PATH = os.path.join(FONT_DIR, "LiberationSans-Regular.ttf")
ITALIC_FONT_PATH = os.path.join(FONT_DIR, "LiberationSans-Italic.ttf")

async def quote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /quote."""
    if not update.message.reply_to_message:
        await update.message.reply_text("Пожалуйста, используйте эту команду в ответ на сообщение с текстом.")
        return

    # Извлекаем текст и данные о пользователе из реплая
    received_message = update.message
    reply = received_message.reply_to_message

    # Логирование reply для отладки
    print("LOGGING: reply_to_message:", reply)

    # Если сообщение содержит выделенную цитату (Quote & Reply), используем её
    quote_text = None
    if hasattr(received_message, "quote") and received_message.quote:
        quote_text = received_message.quote
    elif reply.text and reply.text != "":
        quote_text = reply.text
    elif reply.caption and reply.caption != "":
        quote_text = reply.caption

    if not quote_text:
        await update.message.reply_text("Не удалось извлечь текст для цитаты.")
        return

    user_name = reply.from_user.full_name or reply.from_user.username or "Без имени"

    # Ограничение на длину текста
    max_chars = 300
    if len(quote_text) > max_chars:
        quote_text = quote_text[:max_chars] + '...'
    
    # Попробуем получить аватар пользователя
    avatar_url = None
    try:
        photos = await context.bot.get_user_profile_photos(reply.from_user.id)
        if photos and photos.total_count > 0:
            photo = photos.photos[0][-1]  # Берем фото максимального размера
            file = await context.bot.get_file(photo.file_id)
            avatar_url = file.file_path
    except Exception as e:
        print(f"Не удалось получить аватар пользователя: {e}")

    # Генерируем изображение
    image = generate_quote_image(quote_text, user_name, avatar_url)

    # Сохраняем изображение в байтовый поток
    bio = BytesIO()
    bio.name = "quote.png"
    image.save(bio, "PNG")
    bio.seek(0)

    # Отправляем изображение
    await update.message.reply_photo(photo=InputFile(bio), caption="Вот ваша цитата!")

def wrap_text(draw, text, font, max_width):
    """Функция для переноса текста по словам."""
    words = text.split(' ')
    lines = []
    current_line = words[0]

    for word in words[1:]:
        bbox = draw.textbbox((0, 0), current_line + ' ' + word, font=font)
        width = bbox[2] - bbox[0]
        if width <= max_width:
            current_line += ' ' + word
        else:
            lines.append(current_line)
            current_line = word

    lines.append(current_line)
    return '\n'.join(lines)

def generate_quote_image(text, user_name, avatar_url):
    """Генерирует изображение с цитатой."""
    # Размеры изображения
    width, height = 800, 400
    background_color = (30, 30, 30)
    text_color = (255, 255, 255)

    # Создаем изображение
    img = Image.new("RGB", (width, height), color=background_color)
    draw = ImageDraw.Draw(img)

    # Загружаем шрифты
    small_font = ImageFont.truetype(REGULAR_FONT_PATH, 24)
    header_font = ImageFont.truetype(REGULAR_FONT_PATH, 28)

    # Шрифт для цитаты с динамическим размером
    min_font_size = 24
    max_font_size = 36
    font_size = max_font_size

    # Выбираем размер шрифта в зависимости от длины текста
    while font_size > min_font_size:
        italic_font = ImageFont.truetype(ITALIC_FONT_PATH, font_size)
        quote_text_wrapped = wrap_text(draw, f'"{text}"', italic_font, max_width=700)
        quote_bbox = draw.multiline_textbbox((0, 0), quote_text_wrapped, font=italic_font)
        quote_height = quote_bbox[3] - quote_bbox[1]

        # Проверяем, помещается ли текст с текущим шрифтом
        if quote_height < height - 200:  # Оставляем место для заголовка и аватара
            break

        font_size -= 2

    # Добавляем заголовок в верхней части
    header_text = "Цитаты великих людей"
    header_bbox = draw.textbbox((0, 0), header_text, font=header_font)
    header_width = header_bbox[2] - header_bbox[0]
    draw.text(((width - header_width) // 2, 30), header_text, fill=text_color, font=header_font)

    # Добавляем текст цитаты в кавычках и наклонным шрифтом
    quote_text = wrap_text(draw, f'"{text}"', italic_font, max_width=700)
    quote_bbox = draw.multiline_textbbox((0, 0), quote_text, font=italic_font)
    quote_width = quote_bbox[2] - quote_bbox[0]
    quote_height = quote_bbox[3] - quote_bbox[1]
    draw.multiline_text(((width - quote_width) // 2, (height - quote_height) // 2 - 30), quote_text, fill=text_color, font=italic_font, align="center")

    # Добавляем имя пользователя и аватар внизу
    avatar_size = 100
    if avatar_url:
        response = requests.get(avatar_url)
        avatar = Image.open(BytesIO(response.content)).convert("RGBA")
        avatar = avatar.resize((avatar_size, avatar_size))

        # Обрезаем аватар в кружок
        mask = Image.new("L", avatar.size, 0)
        draw_mask = ImageDraw.Draw(mask)
        draw_mask.ellipse((0, 0, avatar_size, avatar_size), fill=255)
        avatar = ImageOps.fit(avatar, mask.size, centering=(0.5, 0.5))
        avatar.putalpha(mask)

        # Вставляем аватар
        img.paste(avatar, (50, height - avatar_size - 20), avatar)

    # Добавляем имя пользователя рядом с аватаром
    draw.text((50 + avatar_size + 20, height - avatar_size - 20 + avatar_size // 4), f"\u00a9 {user_name}", fill=text_color, font=small_font)

    return img

if __name__ == "__main__":
    # Создаем приложение
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Добавляем обработчик для команды /quote
    app.add_handler(CommandHandler("quote", quote))

    # Настраиваем Webhook
    WEBHOOK_URL = "https://www.crownberry.link/quoter_bot"
    app.run_webhook(listen="0.0.0.0",
                    port=8443,  # Используйте безопасный порт
                    url_path="quoter_bot",
                    webhook_url=WEBHOOK_URL)
