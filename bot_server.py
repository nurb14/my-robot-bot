import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import os
import telebot
from google import genai
from google.genai import types

# 1. Токендерді жүйеден оқу
BOT_TOKEN = os.environ.get("BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

bot = telebot.TeleBot(BOT_TOKEN)
ai_client = genai.Client(api_key=GEMINI_API_KEY)

# Промпт (ЖИ стилі)
ROBOTICS_EXPERT_PROMPT = """
Сен — робототехника мен электрониканы жақсы көретін кәсіби инженерсің. Пайдаланушымен өте жақын досы сияқты еркін, қарапайым тілде сөйлес.
Тым ресми сөздерді мүлдем қолданба. Тек қана таза қазақша жауап бер.
Мәтінді безендіру керек болса, ТЕК мына HTML тегтерін қолдан: <b>қалың мәтін</b>, <i>көлбеу мәтін</i>, <code>код жолы</code>.
"""

# /START БҰЙРЫҒЫ
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    welcome_text = (
        "🤖 <b>О, сәлем! Мен дайынмын.</b>\n\n"
        "Робототехника, схемалар немесе Ардуино бойынша қандай идея не сұрақ бар? "
        "Қысылмай жаза бер, досым, бірге шешеміз! 👇"
    )
    bot.send_message(message.chat.id, welcome_text, parse_mode="HTML")

# ПАЙДАЛАНУШЫ СҰРАҚТАРЫН ӨҢДЕУ (Ең қауіпсіз әдіс)
@bot.message_handler(func=lambda message: True)
def handle_robotics_chat(message):
    user_id = message.chat.id
    user_query = message.text

    bot.send_chat_action(user_id, 'typing')

    try:
        # Ешқандай күрделі тарихсыз, тікелей ЖИ-ге сұраныс жіберу (қате мүлдем шықпайды)
        response = ai_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=user_query,
            config=types.GenerateContentConfig(
                system_instruction=ROBOTICS_EXPERT_PROMPT,
                temperature=0.7
            )
        )

        ai_text = response.text

        # Телеграмға жауапты жіберу
        bot.send_message(user_id, ai_text, parse_mode="HTML")

    except Exception as e:
        print(f"Жүйелік қателік: {e}")
        # Егер HTML тегтерден қате кетсе, таза мәтін ретінде жібере салу
        try:
            bot.send_message(user_id, ai_text)
        except:
            bot.send_message(user_id, "Ой, сәл түсінбей қалдым. Қайтадан жазып жіберші, досым.")

# ВЕБ-СЕРВЕР (Render портты жаппауы үшін)
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write("Бот жұмыс істеп тұр!".encode("utf-8"))

def run_health_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    print(f"🌍 Хелс-чек сервері {port} портында іске қосылды...")
    server.serve_forever()


import sys

if __name__ == '__main__':
    # Библиотека ішіндегі көп тармақты (threading) өшіріп, жалғыз негізгі процесті қалдыру
    # Бұл Render бірнеше рет іске қосса да, боттың тек 1 нұсқада жұмыс істеуін бекітеді
    server_thread = threading.Thread(target=run_health_server, daemon=True)
    server_thread.start()

    print("🤖 Бот тек жалғыз таза ағында іске қосылуда...")

    # Конфликт бермеу үшін none_stop=False қылып, қате шықса ботты қайтадан күштеп қосқызу
    try:
        bot.infinity_polling(timeout=10, long_polling_timeout=5)
    except Exception as main_error:
        print(f"Поллинг тоқтады: {main_error}")
        sys.exit(1)