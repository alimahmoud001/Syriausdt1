from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes, ConversationHandler, JobQueue
import requests
from bs4 import BeautifulSoup
from config import TOKEN, ADMIN_CHAT_ID

# حالات المحادثة للشراء
BUY_NAME, BUY_PHONE, BUY_CITY, BUY_AMOUNT, BUY_PAYMENT_METHOD, BUY_WALLET_ADDRESS, BUY_NETWORK = range(7)

# حالات المحادثة للبيع
SELL_NAME, SELL_PHONE, SELL_CITY, SELL_AMOUNT, SELL_RECEIVE_METHOD, SELL_NETWORK = range(7, 13)

def get_syp_exchange_rate():
    url = "https://www.sp-today.com/currency/us_dollar"
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an HTTPError for bad responses (4xx or 5xx)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        target_table = None
        tables = soup.find_all('table')
        for table in tables:
            if "1 دولار أمريكي" in table.text:
                target_table = table
                break

        if target_table:
            row = target_table.find(lambda tag: tag.name == 'tr' and "1 دولار أمريكي" in tag.text)
            if row:
                cols = row.find_all('td')
                if len(cols) >= 2:
                    syp_rate_str = cols[1].text.replace('ليرة سورية', '').replace(',', '').strip()
                    return float(syp_rate_str)
        return None
    except requests.exceptions.RequestException as e:
        print(f"Error fetching exchange rate: {e}")
        return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    exchange_rate = get_syp_exchange_rate()
    rate_message = "جاري تحديث سعر الصرف..."
    if exchange_rate:
        rate_message = f"سعر الدولار اليوم: {exchange_rate} ليرة سورية"
    
    keyboard = [
        [InlineKeyboardButton("شراء USDT", callback_data='buy_usdt')],
        [InlineKeyboardButton("بيع USDT", callback_data='sell_usdt')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_html(
        f"مرحباً {user.mention_html()}!\nماذا يمكن لهذا البوت فعله؟\nشراء وبيع USDT عن طريق وسائل الدفع المتاحة في سوريا.\nالتحويل 0.05% من المبلغ الكامل.\n{rate_message}",
        reply_markup=reply_markup
    )

async def buy_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(text="لقد اخترت شراء USDT. يرجى تزويدنا بالمعلومات التالية:\nاسمك الثلاثي:")
    return BUY_NAME

async def buy_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['buy_name'] = update.message.text
    await update.message.reply_text("رقم هاتفك:")
    return BUY_PHONE

async def buy_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['buy_phone'] = update.message.text
    await update.message.reply_text("المدينة:")
    return BUY_CITY

async def buy_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['buy_city'] = update.message.text
    await update.message.reply_text("الكمية المطلوبة (USDT):")
    return BUY_AMOUNT

async def buy_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['buy_amount'] = update.message.text
    payment_methods = [["شام كاش"], ["سيريتل كاش"], ["حوالة الفؤاد"], ["حوالة الهرم"], ["بنك البركة"], ["البنك الاسلامي"]]
    reply_markup = ReplyKeyboardMarkup(payment_methods, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("طريقة الدفع المناسبة:", reply_markup=reply_markup)
    return BUY_PAYMENT_METHOD

async def buy_payment_method(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['buy_payment_method'] = update.message.text
    await update.message.reply_text("عنوان محفظة USDT:", reply_markup=ReplyKeyboardRemove())
    return BUY_WALLET_ADDRESS

async def buy_wallet_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['buy_wallet_address'] = update.message.text
    networks = [["bep20"], ["trc20"], ["erc20"], ["ton"], ["sol"], ["avax"]]
    reply_markup = ReplyKeyboardMarkup(networks, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("عنوان الشبكة (bep20, trc20, erc20, ton, sol, avax):")
    return BUY_NETWORK

async def buy_network(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['buy_network'] = update.message.text

    user_info = context.user_data
    message_to_admin = (
        f"طلب شراء USDT جديد:\n"
        f"الاسم: {user_info.get('buy_name')}\n"
        f"الهاتف: {user_info.get('buy_phone')}\n"
        f"المدينة: {user_info.get('buy_city')}\n"
        f"الكمية: {user_info.get('buy_amount')} USDT\n"
        f"طريقة الدفع: {user_info.get('buy_payment_method')}\n"
        f"عنوان المحفظة: {user_info.get('buy_wallet_address')}\n"
        f"الشبكة: {user_info.get('buy_network')}\n"
    )

    await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=message_to_admin)
    await update.message.reply_text("تم إرسال طلبك بنجاح! سيتم التواصل معك قريباً.", reply_markup=ReplyKeyboardRemove())

    return ConversationHandler.END

async def sell_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(text="لقد اخترت بيع USDT. يرجى تزويدنا بالمعلومات التالية:\nاسمك الثلاثي:")
    return SELL_NAME

async def sell_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['sell_name'] = update.message.text
    await update.message.reply_text("رقم هاتفك:")
    return SELL_PHONE

async def sell_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['sell_phone'] = update.message.text
    await update.message.reply_text("المدينة:")
    return SELL_CITY

async def sell_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['sell_city'] = update.message.text
    await update.message.reply_text("الكمية التي ستبيعها (USDT):")
    return SELL_AMOUNT

async def sell_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['sell_amount'] = update.message.text
    receive_methods = [["حوالة هرم"], ["حوالة الفؤاد"], ["سيريتل كاش"], ["شام كاش"]]
    reply_markup = ReplyKeyboardMarkup(receive_methods, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("طريقة استلام المبلغ بالليرة السورية:", reply_markup=reply_markup)
    return SELL_RECEIVE_METHOD

async def sell_receive_method(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['sell_receive_method'] = update.message.text
    networks = [["bep20"], ["trc20"], ["erc20"]]
    reply_markup = ReplyKeyboardMarkup(networks, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("عنوان الشبكة (bep20, trc20, erc20):")
    return SELL_NETWORK

async def sell_network(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['sell_network'] = update.message.text

    network = context.user_data['sell_network'].lower()
    wallet_address = ""
    if network == "bep20":
        wallet_address = "0x21802218d8d661d66F2C7959347a6382E1cc614F"
    elif network == "trc20":
        wallet_address = "TD2LoErPRkVPBxDk72ZErtiyi6agirZQjX"
    elif network == "erc20":
        wallet_address = "0x21802218d8d661d66F2C7959347a6382E1cc614F"
    else:
        wallet_address = "شبكة غير مدعومة حالياً."

    context.user_data['sell_wallet_address'] = wallet_address

    user_info = context.user_data
    message_to_admin = (
        f"طلب بيع USDT جديد:\n"
        f"الاسم: {user_info.get('sell_name')}\n"
        f"الهاتف: {user_info.get('sell_phone')}\n"
        f"المدينة: {user_info.get('sell_city')}\n"
        f"الكمية: {user_info.get('sell_amount')} USDT\n"
        f"طريقة الاستلام: {user_info.get('sell_receive_method')}\n"
        f"الشبكة: {user_info.get('sell_network')}\n"
        f"عنوان المحفظة لإرسال USDT إليه: {user_info.get('sell_wallet_address')}\n"
    )

    await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=message_to_admin)
    await update.message.reply_text(f"تم إرسال طلبك بنجاح! يرجى إرسال الـ USDT إلى العنوان التالي: {wallet_address}", reply_markup=ReplyKeyboardRemove())

    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        'تم إلغاء العملية.', reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

def main():
    application = Application.builder().token(TOKEN).build()

    buy_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(buy_start, pattern='^buy_usdt$')],
        states={
            BUY_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, buy_name)],
            BUY_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, buy_phone)],
            BUY_CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, buy_city)],
            BUY_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, buy_amount)],
            BUY_PAYMENT_METHOD: [MessageHandler(filters.TEXT & ~filters.COMMAND, buy_payment_method)],
            BUY_WALLET_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, buy_wallet_address)],
            BUY_NETWORK: [MessageHandler(filters.TEXT & ~filters.COMMAND, buy_network)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    sell_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(sell_start, pattern='^sell_usdt$')],
        states={
            SELL_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, sell_name)],
            SELL_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, sell_phone)],
            SELL_CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, sell_city)],
            SELL_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, sell_amount)],
            SELL_RECEIVE_METHOD: [MessageHandler(filters.TEXT & ~filters.COMMAND, sell_receive_method)],
            SELL_NETWORK: [MessageHandler(filters.TEXT & ~filters.COMMAND, sell_network)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(buy_conv_handler)
    application.add_handler(sell_conv_handler)

    application.run_polling()

if __name__ == '__main__':
    main()


