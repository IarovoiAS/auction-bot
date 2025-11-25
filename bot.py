import re
import time
from datetime import datetime, timedelta
from collections import defaultdict
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# Хранилище заявок: article → список заявок с временем
applications = defaultdict(list)


def parse_application_from_text(text: str):
    blocks = re.split(r'\n(?=Input:)', text.strip())
    results = []
    for block in blocks:
        input_match = re.search(r'Input:\s*(.+)', block)
        article_match = re.search(r'Артикул:\s*(\S+)', block)
        amount_match = re.search(r'Сумма:\s*(\d+)', block)

        if input_match and article_match and amount_match:
            try:
                amount = int(amount_match.group(1))
                results.append({
                    'input': input_match.group(1).strip(),
                    'article': article_match.group(1).strip(),
                    'amount': amount
                })
            except ValueError:
                continue
    return results


async def monitor_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    text = update.message.text
    timestamp = datetime.now()
    apps = parse_application_from_text(text)

    for app in apps:
        applications[app['article']].append({
            'input': app['input'],
            'amount': app['amount'],
            'timestamp': timestamp
        })


def parse_duration(duration_str: str):
    duration_str = duration_str.strip().lower()
    match = re.match(r'^(\d+)\s*([мчд])$', duration_str)
    if not match:
        return None

    value = int(match.group(1))
    unit = match.group(2)

    if unit == 'м':
        return timedelta(minutes=value)
    elif unit == 'ч':
        return timedelta(hours=value)
    elif unit == 'д':
        return timedelta(days=value)
    return None


async def handle_auction_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if not text.startswith("Аукцион"):
        return

    parts = text.split(maxsplit=2)
    if len(parts) < 2:
        await update.message.reply_text(
            "⚠️ Укажите артикул и (опционально) время.\n"
            "Примеры:\n"
            "`Аукцион С7-00076132`\n"
            "`Аукцион С7-00076132 3ч`\n"
            "`Аукцион С7-00076132 30м`",
            parse_mode='Markdown'
        )
        return

    article = parts[1].strip()
    duration = None

    if len(parts) == 3:
        duration = parse_duration(parts[2])
        if duration is None:
            await update.message.reply_text(
                "⚠️ Неверный формат времени. Используйте: `30м`, `2ч`, `1д` и т.п.",
                parse_mode='Markdown'
            )
            return

    all_apps = applications.get(article, [])
    if not all_apps:
        await update.message.reply_text(f"📭 Нет заявок по артикулу: `{article}`", parse_mode='Markdown')
        return

    now = datetime.now()
    if duration:
        cutoff = now - duration
        filtered_apps = [app for app in all_apps if app['timestamp'] >= cutoff]
        period_str = f"за последние {parts[2]}"
    else:
        filtered_apps = all_apps
        period_str = "за всё время"

    if not filtered_apps:
        await update.message.reply_text(
            f"📭 Нет заявок по артикулу `{article}` {period_str}.", parse_mode='Markdown'
        )
        return

    sorted_apps = sorted(filtered_apps, key=lambda x: x['amount'], reverse=True)

    response = f"📋 Аукцион по артикулу: *{article}*\n📅 {period_str}\n\n"
    for app in sorted_apps:
        time_str = app['timestamp'].strftime("%d.%m %H:%M")
        response += f"• *{app['input']}*\n"
        response += f"  Сумма: {app['amount']} ₽\n"
        response += f"  Время: {time_str}\n\n"

    if len(response) > 4000:
        response = response[:4000] + "\n... (обрезано)"

    await update.message.reply_text(response, parse_mode='Markdown')


def main():
    # 🔑 ВСТАВЬТЕ СЮДА ВАШ ТОКЕН ОТ @BotFather
    TOKEN = "8530291650:AAFmFS5V721tGXGhMsgj-BcTnjcO5Vzlk58"

    app = Application.builder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, monitor_messages))
    app.add_handler(MessageHandler(filters.Regex(r'^Аукцион\s+\S+'), handle_auction_command))

    print("✅ Бот запущен! Добавьте его в чат и сделайте админом.")
    app.run_polling()


if __name__ == '__main__':
    main()