"""Selva — mijozlar savollariga avtomatik javob beradigan Telegram bot (Claude asosida).

Ishga tushirish:
    pip install -r requirements.txt
    export TELEGRAM_BOT_TOKEN=...      # @BotFather'dan
    export ANTHROPIC_API_KEY=...       # console.anthropic.com'dan
    python bot.py

Biznes haqidagi ma'lumotlar knowledge.md faylida — o'sha faylni to'ldiring.
"""

import logging
import os
from collections import defaultdict, deque
from pathlib import Path

import anthropic
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s: %(message)s", level=logging.INFO
)
for _name in ("httpx", "httpx2"):
    logging.getLogger(_name).setLevel(logging.WARNING)
log = logging.getLogger("selva-bot")

BASE_DIR = Path(__file__).parent
MODEL = os.environ.get("CLAUDE_MODEL", "claude-opus-5-5")
MAX_HISTORY_TURNS = 10  # har bir mijoz uchun eslab qolinadigan oxirgi savol-javoblar soni
TELEGRAM_LIMIT = 4096

KNOWLEDGE = (BASE_DIR / "knowledge.md").read_text(encoding="utf-8")

# System prompt o'zgarmas bo'lishi kerak — shunda prompt caching ishlaydi va arzonlashadi.
SYSTEM_PROMPT = f"""Siz Selva kompaniyasining Telegram'dagi mijozlarga xizmat ko'rsatish yordamchisisiz.

Vazifangiz: mijozlarning savollariga quyidagi bilimlar bazasi asosida qisqa, aniq va xushmuomala javob berish.

Qoidalar:
- Mijoz qaysi tilda yozsa (o'zbek, rus, ingliz), o'sha tilda javob bering.
- Faqat bilimlar bazasidagi ma'lumotga tayaning. Narx, muddat, manzil yoki shartlarni o'zingizdan to'qib chiqarmang.
- Javob bazada bo'lmasa, buni ochiq ayting va mijozni bazadagi aloqa ma'lumotlari orqali menejerga yo'naltiring.
- Mijoz shikoyat qilsa yoki inson bilan gaplashmoqchi bo'lsa, uzr so'rang va menejer kontaktini bering.
- Javoblar Telegram uchun: 1–5 gap, kerak bo'lsa qisqa ro'yxat. Markdown sarlavhalar ishlatmang.
- Kompaniyaga aloqasi yo'q mavzularda xushmuomalalik bilan suhbatni kompaniya xizmatlariga qaytaring.

<bilimlar_bazasi>
{KNOWLEDGE}
</bilimlar_bazasi>"""

client = anthropic.AsyncAnthropic()

# chat_id -> oxirgi xabarlar (xotirada; bot qayta ishga tushsa tozalanadi)
histories: dict[int, deque] = defaultdict(lambda: deque(maxlen=MAX_HISTORY_TURNS * 2))

FALLBACK_REPLY = (
    "Kechirasiz, hozir javob bera olmadim. Iltimos, birozdan so'ng qayta yozing "
    "yoki menejerimiz bilan bog'laning."
)


async def ask_claude(chat_id: int, question: str) -> str:
    history = histories[chat_id]
    messages = list(history) + [{"role": "user", "content": question}]

    response = await client.beta.messages.create(
        model=MODEL,
        max_tokens=2000,
        system=SYSTEM_PROMPT,
        messages=messages,
        cache_control={"type": "ephemeral"},  # system + tarixni keshlaydi
        output_config={"effort": "low"},  # oddiy chat uchun tez va arzon
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",  # model rad etsa, avtomatik boshqa modelda qayta urinadi
    )

    if response.stop_reason == "refusal":
        log.warning("Refusal for chat %s: %s", chat_id, response.stop_details)
        return FALLBACK_REPLY

    answer = "".join(b.text for b in response.content if b.type == "text").strip()
    if not answer:
        return FALLBACK_REPLY

    history.append({"role": "user", "content": question})
    history.append({"role": "assistant", "content": answer})
    log.info(
        "chat=%s in=%s cache_read=%s out=%s",
        chat_id,
        response.usage.input_tokens,
        response.usage.cache_read_input_tokens,
        response.usage.output_tokens,
    )
    return answer


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    histories.pop(update.effective_chat.id, None)
    await update.message.reply_text(
        "Assalomu alaykum! Men Selva yordamchisiman. Savolingizni yozing — "
        "darhol javob beraman. 😊"
    )


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    histories.pop(update.effective_chat.id, None)
    await update.message.reply_text("Suhbat tarixi tozalandi. Yangi savolingizni yozing.")


async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)

    try:
        answer = await ask_claude(chat_id, update.message.text)
    except anthropic.RateLimitError:
        log.warning("Rate limited")
        answer = FALLBACK_REPLY
    except anthropic.APIStatusError as e:
        log.error("Claude API error %s: %s", e.status_code, e.message)
        answer = FALLBACK_REPLY
    except anthropic.APIConnectionError:
        log.error("Claude API connection error")
        answer = FALLBACK_REPLY

    for i in range(0, len(answer), TELEGRAM_LIMIT):
        await update.message.reply_text(answer[i : i + TELEGRAM_LIMIT])


def main() -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise SystemExit("TELEGRAM_BOT_TOKEN o'rnatilmagan.")

    app = Application.builder().token(token).concurrent_updates(True).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))

    log.info("Bot ishga tushdi (model: %s)", MODEL)
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
