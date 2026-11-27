# Selva Telegram bot

Mijozlar savollariga Claude yordamida avtomatik javob beradi.

## 1. Kalitlarni oling
1. **Telegram token:** Telegram'da @BotFather → `/newbot` → bot nomini kiriting → token oling.
2. **Claude API kaliti:** https://console.anthropic.com → API Keys → Create Key. Hisobga balans qo'shing.

## 2. Ma'lumotlarni kiriting
`knowledge.md` faylini oching va narxlar, ish vaqti, manzil, aloqa ma'lumotlarini yozing.

## 3. Ishga tushiring
```bash
cd telegram-bot
pip install -r requirements.txt
export TELEGRAM_BOT_TOKEN="sizning_tokeningiz"
export ANTHROPIC_API_KEY="sizning_kalitingiz"
python bot.py
```
Endi botingizga Telegram'da yozib ko'ring.

## Buyruqlar
- `/start` — salomlashish
- `/reset` — suhbat tarixini tozalash

## Eslatmalar
- Bot kompyuter yoki server yoniq turgan paytda ishlaydi. 24/7 ishlashi uchun VPS'ga
  (masalan, Railway, Render, Hetzner) joylashtiring.
- Model: `claude-opus-5-5` (`CLAUDE_MODEL` muhit o'zgaruvchisi bilan almashtirsa bo'ladi).
- Suhbat tarixi xotirada saqlanadi, bot qayta ishga tushsa tozalanadi.
