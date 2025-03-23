import requests
import pandas as pd
import datetime
import logging
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler

# إعدادات تيليجرام
TELEGRAM_BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
TELEGRAM_CHAT_ID = "YOUR_TELEGRAM_CHAT_ID"

# إعدادات التداول
SYMBOL = "AUD/CAD"
TIMEZONE_OFFSET = -3  # فرق التوقيت UTC-3
API_URL = "https://api.example.com/market-data"  # رابط API بيانات السوق

# تشغيل بوت تيليجرام
bot = Bot(token=TELEGRAM_BOT_TOKEN)

# تفعيل سجل الأخطاء
logging.basicConfig(level=logging.INFO)

def get_market_data():
    """يجلب بيانات السوق من API خارجي"""
    response = requests.get(API_URL)
    if response.status_code == 200:
        return pd.DataFrame(response.json())
    else:
        return None

def calculate_macd_rsi(data):
    """حساب مؤشرات MACD و RSI"""
    short_window = 12
    long_window = 26
    signal_window = 9

    data["EMA12"] = data["close"].ewm(span=short_window, adjust=False).mean()
    data["EMA26"] = data["close"].ewm(span=long_window, adjust=False).mean()
    data["MACD"] = data["EMA12"] - data["EMA26"]
    data["Signal"] = data["MACD"].ewm(span=signal_window, adjust=False).mean()

    delta = data["close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    data["RSI"] = 100 - (100 / (1 + rs))

    return data

def check_trade_signal(data):
    """يتحقق من إشارات الدخول والخروج"""
    latest = data.iloc[-1]

    if latest["MACD"] > latest["Signal"] and latest["RSI"] > 30:
        return "BUY"
    elif latest["MACD"] < latest["Signal"] and latest["RSI"] < 70:
        return "SELL"
    return None

def start(update: Update, context):
    """إرسال رسالة ترحيب وزر طلب الصفقة"""
    keyboard = [[InlineKeyboardButton("🔍 الحصول على إشارة", callback_data="get_signal")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    update.message.reply_text("✅ بوت التداول جاهز! اضغط الزر أدناه للحصول على إشارة السوق.", reply_markup=reply_markup)

def get_signal(update: Update, context):
    """جلب الإشارة عند الضغط على الزر"""
    market_data = get_market_data()
    
    if market_data is not None:
        market_data = calculate_macd_rsi(market_data)
        signal = check_trade_signal(market_data)

        if signal:
            now = datetime.datetime.utcnow() + datetime.timedelta(hours=TIMEZONE_OFFSET)
            timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
            message = f"🔔 إشارة {signal} تم اكتشافها!\n⏰ الوقت: {timestamp} (UTC-3)\n📈 الزوج: {SYMBOL}"
        else:
            message = "⚠️ يرجى الانتظار، لا توجد إشارات حالياً."
    else:
        message = "❌ فشل في جلب بيانات السوق."

    query = update.callback_query
    query.answer()
    query.edit_message_text(text=message)

def main():
    """تشغيل البوت"""
    updater = Updater(TELEGRAM_BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CallbackQueryHandler(get_signal))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
