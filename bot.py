import os
import requests
import pandas as pd
import datetime
import logging
from telegram import Bot, Update
from telegram.ext import Updater, CommandHandler, CallbackContext

# إعداد سجل الأخطاء
logging.basicConfig(level=logging.INFO)

# جلب المتغيرات من البيئة
BOT_TOKEN = os.environ.get("BOT_TOKEN")
BOT_ID = os.environ.get("BOT_ID")  # معرف الدردشة الذي ستُرسل إليه الرسائل

# إعدادات التداول
SYMBOL = "AUD/CAD"
TIMEZONE_OFFSET = -3  # UTC-3
API_URL = "https://api.example.com/market-data"  # ضع رابط API المناسب لجلب بيانات السوق من Quotex

# إنشاء كائن البوت
bot = Bot(token=BOT_TOKEN)

def get_market_data():
    """
    يجلب بيانات السوق من API خارجي ويحولها إلى DataFrame.
    """
    try:
        response = requests.get(API_URL)
        if response.status_code == 200:
            data = pd.DataFrame(response.json())
            return data
        else:
            logging.error("خطأ في جلب بيانات السوق: " + str(response.status_code))
            return None
    except Exception as e:
        logging.error(f"استثناء أثناء جلب بيانات السوق: {e}")
        return None

def calculate_macd_rsi(data):
    """
    يحسب مؤشري MACD و RSI على بيانات السوق.
    """
    short_window = 12
    long_window = 26
    signal_window = 9

    # حساب المتوسطات الأسية وحساب MACD
    data["EMA12"] = data["close"].ewm(span=short_window, adjust=False).mean()
    data["EMA26"] = data["close"].ewm(span=long_window, adjust=False).mean()
    data["MACD"] = data["EMA12"] - data["EMA26"]
    data["Signal"] = data["MACD"].ewm(span=signal_window, adjust=False).mean()

    # حساب مؤشر RSI
    delta = data["close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    data["RSI"] = 100 - (100 / (1 + rs))
    return data

def check_trade_signal(data):
    """
    يتحقق من الإشارة بناءً على MACD و RSI.
    - إذا كان MACD > Signal و RSI > 30 => إشارة شراء.
    - إذا كان MACD < Signal و RSI < 70 => إشارة بيع.
    """
    latest = data.iloc[-1]
    if latest["MACD"] > latest["Signal"] and latest["RSI"] > 30:
        return "BUY"
    elif latest["MACD"] < latest["Signal"] and latest["RSI"] < 70:
        return "SELL"
    return None

def send_trade(context: CallbackContext):
    """
    يجلب بيانات السوق، يحسب المؤشرات، ويتحقق من الإشارة.
    ثم يرسل رسالة إلى الدردشة المحددة.
    """
    market_data = get_market_data()
    if market_data is not None:
        market_data = calculate_macd_rsi(market_data)
        signal = check_trade_signal(market_data)
        now = datetime.datetime.utcnow() + datetime.timedelta(hours=TIMEZONE_OFFSET)
        timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
        if signal:
            message = (f"🔔 إشارة {signal} تم اكتشافها!\n"
                       f"⏰ الوقت: {timestamp} (UTC-3)\n"
                       f"📈 الزوج: {SYMBOL}")
        else:
            message = "⚠️ لا توجد صفقة مناسبة حالياً. يرجى الانتظار."
    else:
        message = "❌ فشل في جلب بيانات السوق."
    
    context.bot.send_message(chat_id=BOT_ID, text=message)

def start(update: Update, context: CallbackContext):
    """
    عند استقبال أمر /start، يرسل رسالة ترحيب.
    """
    update.message.reply_text("✅ مرحباً، بوت التداول بدأ العمل وسيُرسل إشارات التداول تلقائيًا!")

def main():
    """
    الدالة الرئيسية لتشغيل البوت.
    تُرسل رسالة ترحيب عند بدء التشغيل وتُجدول إرسال الإشارات تلقائيًا.
    """
    updater = Updater(BOT_TOKEN)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))

    # جدولة إرسال الإشارات تلقائيًا كل 10 دقائق (600 ثانية)
    job_queue = updater.job_queue
    job_queue.run_repeating(send_trade, interval=600, first=0, context=BOT_ID)

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main() 
