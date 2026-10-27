import json
from pathlib import Path

import telebot
from telebot import custom_filters, types
from telebot.handler_backends import State, StatesGroup
from telebot.storage import StateMemoryStorage

from config import TOKEN

MENYU = {
    1: {
        "savol": "Python'da ro'yxat qaysi qavsda yoziladi?",
        "variantlar": ["[ ]", "( )", "{ }"],
        "javob": "[ ]",
    },
    2: {
        "savol": "2³ nechaga teng?",
        "variantlar": ["6", "8", "9"],
        "javob": "8",
    },
    3: {
        "savol": "Bot tokenini kim beradi?",
        "variantlar": ["@BotFather", "@Python", "Google"],
        "javob": "@BotFather",
    },
}

FAYL = Path(__file__).with_name("testjavoblar.json")
bot = telebot.TeleBot(TOKEN, state_storage=StateMemoryStorage())

class Tests(StatesGroup):
    ism = State()
    test_javob = State()


def asosiy_menyu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.row("🎮 Boshlash", "ℹ️ Yordam")
    return markup

def savol_yubor(message):
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        raqam = data["savol_raqami"]

    savol = MENYU[raqam]
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    for variant in savol["variantlar"]:
        markup.row(variant)

    bot.send_message(
        message.chat.id,
        f"❓ {raqam}-savol: {savol['savol']}",
        reply_markup=markup,
    )

def natija_saqlash(user_id, ism, ball):
    try:
        natijalar = json.loads(FAYL.read_text(encoding="utf-8"))
    except FileNotFoundError:
        natijalar = []

    if not isinstance(natijalar, list):
        raise ValueError("Natijalar faylida JSON da yo'q (.")

    natijalar.append({"user_id": user_id, "ism": ism, "ball": ball, "jami_savollar": len(MENYU)})
    FAYL.write_text(
        json.dumps(natijalar, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )



@bot.message_handler(commands=["start"])
def start(message):
    bot.delete_state(message.from_user.id, message.chat.id)
    bot.send_message(
        message.chat.id,
        "Salom! 🧠 Mini viktorinaga xush kelibsiz.",
        reply_markup=asosiy_menyu(),
    )

@bot.message_handler(commands=["help"])
@bot.message_handler(func=lambda m: m.text == "ℹ️ Yordam")
def yordam(message):
    bot.send_message(
        message.chat.id,
        "🎮 Boshlash — 3 ta savol. Javob tugmasini bosing.\n"
        "/cancel — to'xtatish",
    )

@bot.message_handler(state="*", commands=["cancel"])
def cancel(message):
    bot.delete_state(message.from_user.id, message.chat.id)
    bot.send_message(message.chat.id, "❌ To'xtatildi", reply_markup=asosiy_menyu())


@bot.message_handler(func=lambda m: m.text == "🎮 Boshlash")
def boshlash(message):
    bot.delete_state(message.from_user.id, message.chat.id)
    bot.set_state(message.from_user.id, Tests.ism, message.chat.id)
    bot.send_message(message.chat.id, "Ismingiz?", reply_markup=types.ReplyKeyboardRemove())


@bot.message_handler(state=Tests.ism, content_types=["text"])
def ism_olish(message):
    ism = message.text.strip()

    bot.add_data(
        message.from_user.id, message.chat.id, ism=ism, savol_raqami=1, ball=0
    )
    bot.set_state(message.from_user.id, Tests.test_javob, message.chat.id)
    savol_yubor(message)


@bot.message_handler(state=Tests.test_javob, content_types=["text"])
def javob_olish(message):
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        raqam = data["savol_raqami"]
        savol = MENYU[raqam]
        javob = message.text.strip()

        if javob not in savol["variantlar"]:
            bot.send_message(message.chat.id, "Javobni tugmalardan tanlang.")
            return

        if javob == savol["javob"]:
            data["ball"] += 1
            xabar = "✅ To'g'ri!"
        else:
            xabar = f"❌ Xato. To'g'ri javob: {savol['javob']}"

        data["savol_raqami"] += 1
        ism, ball = data["ism"], data["ball"]

    bot.send_message(message.chat.id, xabar)
    if raqam < len(MENYU):
        savol_yubor(message)
        return

    saqlandi = True
    try:
        natija_saqlash(message.from_user.id, ism, ball)
    except (OSError, ValueError, UnicodeError):
        saqlandi = False
        telebot.logger.exception("Natijani faylga saqlashda xato")

    bot.delete_state(message.from_user.id, message.chat.id)
    bot.send_message(
        message.chat.id,
        f"🏁 {ism}, natijangiz: {ball}/{len(MENYU)}",
        reply_markup=asosiy_menyu(),
    )
    if not saqlandi:
        bot.send_message(message.chat.id, "Natijani faylga saqlab bo'lmadi.")


@bot.message_handler(func=lambda m: True, content_types=["text"])
def boshqa_xabar(message):
    bot.send_message(
        message.chat.id, "Boshlash uchun 🎮 Boshlash tugmasini bosing.",
        reply_markup=asosiy_menyu(),
    )


bot.add_custom_filter(custom_filters.StateFilter(bot))

if __name__ == "__main__":
    bot.infinity_polling(skip_pending=True)