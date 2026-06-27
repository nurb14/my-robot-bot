import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import os
import telebot
from google import genai
from google.genai import types

# Токендерді оқу
BOT_TOKEN = os.environ.get("BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

bot = telebot.TeleBot(BOT_TOKEN)
ai_client = genai.Client(api_key=GEMINI_API_KEY)

# Промпт
ROBOTICS_EXPERT_PROMPT = """
Сен — робототехника мен электрониканы жақсы көретін кәсіби инженерсің. Пайдаланушымен өте жақын досы сияқты еркін, қарапайым тілде сөйлес.
Тым ресми сөздерді мүлдем қолданба. Тек қана таза қазақша жауап бер.
Мәтінді безендіру керек болса, ТЕК мына HTML тегтерін қолдан: <b>қалың мәтін</b>, <i>көлбеу мәтін</i>, <code>код жолы</code>.
"""


@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    welcome_text = (
        "🤖 <b>О, сәлем! Мен дайынмын.</b>\n\n"
        "Робототехника, схемалар немесе Ардуино бойынша қандай идея не сұрақ бар? "
        "Қысылмай жаза бер, досым, бірге шешеміз! 👇"
    )
    bot.send_message(message.chat.id, welcome_text, parse_mode="HTML")


@bot.message_handler(func=lambda message: True)
def handle_robotics_chat(message):
    user_id = message.chat.id
    user_query = message.text
    bot.send_chat_action(user_id, 'typing')

    try:
        response = ai_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=user_query,
            config=types.GenerateContentConfig(
                system_instruction=ROBOTICS_EXPERT_PROMPT,
                temperature=0.7
            )
        )
        bot.send_message(user_id, response.text, parse_mode="HTML")
    except Exception as e:
        print(f"Қате: {e}")
        bot.send_message(user_id, "Ой, сәл түсінбей қалдым. Қайтадан жазып жіберші, досым.")


# ВЕБ-СЕРВЕР (Render-дің HEAD және GET сұраныстарына дұрыс жауап беру)
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write("Бот жұмыс істеп тұр!".encode("utf-8"))

    def do_HEAD(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()


def run_health_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()


if __name__ == '__main__':
    # 1. Ботты тоқтатып, Webhook-ты тазалау
    bot.remove_webhook()

    # 2. Хелс-чекті бөлек ағында қосу (Render үшін міндетті)
    server_thread = threading.Thread(target=run_health_server, daemon=True)
    server_thread.start()

    print("🤖 Бот Webhook режимінде іске қосылды...")

    # 3. Қате шықпас үшін polling-ді мүлдем алып тастап, серверді ұстап тұрамыз
    import time

    while True:
        try:
            bot.polling(none_stop=True, interval=0, timeout=20)
        except Exception as e:
            print(f"Polling error, retrying: {e}")
            time.sleep(5)