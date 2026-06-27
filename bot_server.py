import os
import telebot
import re
from google import genai
from google.genai import types

# =====================================================================
# 1. ТОКЕНДЕРДІ ЖҮЙЕДЕН ОҚУ (ҚАУІПСІЗ ӘДІС)
# =====================================================================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

bot = telebot.TeleBot(BOT_TOKEN)
ai_client = genai.Client(api_key=GEMINI_API_KEY)

# 🧠 Әр қолданушының диалог тарихын сақтайтын қарапайым әрі қауіпсіз жад
user_history = {}

# =====================================================================
# 2. ЕРКІН ӘРІ ЖАҚЫН СӨЙЛЕСУ ПРОМПТЫ
# =====================================================================
ROBOTICS_EXPERT_PROMPT = """
Сен — робототехника мен электрониканы судай сапыратын кәсіби инженерсің, бірақ пайдаланушымен өте жақын досы сияқты еркін, қарапайым тілде сөйлесесің.

🔴 СӨЙЛЕСУ СТИЛІ:
- Тым ресми сөздерді ("Құрметті пайдаланушы", "Сізге көмектесуге дайынмын") мүлдем қолданба.
- Кәдімгі досыңа түсіндіріп жатқандай еркін сөйле. "Сәлем" деп тек диалогтың ең басында 1-ақ рет айт, ары қарай әр хабарлама сайын амандасып басты қатырма.
- Жауаптарың тым ұзын, жалықтыратын болмасын. Нақты, қысқа әрі түсінікті қылып қайтар. 
- Қазақша сөйлескенде техникалық терминдерді жастар түсінетіндей жеңіл жеткіз.

⚠️ ТЕЛЕГРАМ HTML ЕРЕЖЕСІ:
Мәтінді безендіру керек болса, ТЕК мына HTML тегтерін қолдан:
- <b>қалың мәтін</b>
- <i>көлбеу мәтін</i>
- <code>код жолы</code>
- <pre>код блогы</pre>
Басқа ешқандай веб-тегтерді (<p>, <ul>, <li>) жазба. Тізімді жай ғана сызықшамен (-) немесе сандармен көрсет.
"""


# =====================================================================
# ҚОСЫМША ФУНКЦИЯ: HTML тегтерін тазалау
# =====================================================================
def clean_html(raw_html):
    cleanr = re.compile('<.*?>')
    return re.sub(cleanr, '', raw_html)


# =====================================================================
# 3. /START БҰЙРЫҒЫ (Тарихты толық тазалау)
# =====================================================================
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    user_id = message.chat.id
    # Қолданушы тарихын нөлге түсіреміз
    user_history[user_id] = []

    welcome_text = (
        "🤖 <b>О, сәлем! Мен дайынмын.</b>\n\n"
        "Робототехника, схемалар немесе Ардуино бойынша қандай идея не сұрақ бар? "
        "Қысылмай жаза бер, досым, бірге шешеміз! 👇"
    )
    bot.reply_to(message, welcome_text, parse_mode="HTML")


# =====================================================================
# 4. ПАЙДАЛАНУШЫ СҰРАҚТАРЫН ӨҢДЕУ
# =====================================================================
@bot.message_handler(func=lambda message: True)
def handle_robotics_chat(message):
    user_id = message.chat.id
    user_query = message.text

    bot.send_chat_action(user_id, 'typing')

    # Егер бұл қолданушы жадта әлі жоқ болса, оған бос тарих ашамыз
    if user_id not in user_history:
        user_history[user_id] = []

    # Пайдаланушының жаңа сұрағын тарихқа қосамыз
    user_history[user_id].append(types.Content(role="user", parts=[types.Part.from_text(text=user_query)]))

    try:
        # Gemini ЖИ-ге бүкіл тарихты жібереміз (бұл әдіс ешқашан кептелмейді!)
        response = ai_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=user_history[user_id],
            config=types.GenerateContentConfig(
                system_instruction=ROBOTICS_EXPERT_PROMPT,
                temperature=0.8
            )
        )

        ai_text = response.text

        # ЖИ-дің берген жауабын да тарихқа жазып қоямыз (келесі жолы еске сақтап тұру үшін)
        user_history[user_id].append(types.Content(role="model", parts=[types.Part.from_text(text=ai_text)]))

        # Хабарламаны Телеграмға қауіпсіз жіберу
        try:
            bot.send_message(user_id, ai_text, parse_mode="HTML")
        except Exception as html_err:
            print(f"HTML қатесі шықты, таза мәтін жіберіледі: {html_err}")
            safe_text = clean_html(ai_text)

            # Егер мәтін ұзын болса, бөліп жіберу
            for i in range(0, len(safe_text), 3500):
                bot.send_message(user_id, safe_text[i:i + 3500])

    except Exception as e:
        print(f"Жүйелік қателік: {e}")
        bot.send_message(user_id, "Ой, сәл қате шығып кетті. Қайтадан жазып жіберші, досым.")


# =====================================================================
# 5. БОТТЫ ІСКЕ ҚОСУ
# =====================================================================
if __name__ == '__main__':
    print("🤖 Кептелмейтін, тұрақты әрі еркін бот қосылды...")
    bot.polling(none_stop=True)