import logging
import os
import pandas as pd
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.utils import executor

# Bot token
TOKEN = "7038697688:AAHwcFapPFZUYep4kpoptLrKvnvk0go922k"  # Bot tokeningizni kiriting
CHANNEL_ID = "@nkbrandd"  # Kanal ID'sini kiriting

# Initialize bot and dispatcher
bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

# CSV file for storing user data and promocodes
USER_DATA_FILE = "data/users.csv"
PROMO_CODES_FILE = "data/promocodes.csv"

# Logging configuration
logging.basicConfig(level=logging.INFO)

# Ensure CSV files exist
if not os.path.exists(USER_DATA_FILE):
    pd.DataFrame(columns=["user_id", "name", "phone", "coins", "referrals"]).to_csv(USER_DATA_FILE, index=False)
if not os.path.exists(PROMO_CODES_FILE):
    pd.DataFrame(columns=["promo_code", "coins"]).to_csv(PROMO_CODES_FILE, index=False)

# Keyboard buttons
main_menu = ReplyKeyboardMarkup(resize_keyboard=True)
main_menu.add(KeyboardButton("Mening ma'lumotim"))
main_menu.add(KeyboardButton("Promokod"))

main_menu.add(KeyboardButton("Coin shop"))
main_menu.add(KeyboardButton("Referral link"))

# Helper functions
def load_user_data():
    return pd.read_csv(USER_DATA_FILE)

def save_user_data(df):
    df.to_csv(USER_DATA_FILE, index=False)

def load_promocodes():
    return pd.read_csv(PROMO_CODES_FILE)

async def check_channel_subscription(user_id):
    """
    Check if the user is a member of the channel.
    """
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception as e:
        logging.error(f"Error checking subscription: {e}")
        return False

@dp.message_handler(commands=["start"])
async def start_handler(message: types.Message):
    user_id = message.from_user.id
    df = load_user_data()
    args = message.get_args()

    # Check if user exists in the database
    if str(user_id) not in df["user_id"].astype(str).values:
        new_user = pd.DataFrame([{
            "user_id": user_id,
            "name": message.from_user.full_name,
            "phone": "",
            "coins": 0,
            "referrals": 0
        }])
        df = pd.concat([df, new_user], ignore_index=True)
        save_user_data(df)

        # Check if referred by another user
        if args and args.isdigit():
            referrer_id = int(args)
            if referrer_id in df["user_id"].values:
                df.loc[df["user_id"] == referrer_id, "coins"] += 5
                df.loc[df["user_id"] == referrer_id, "referrals"] += 1
                save_user_data(df)

    # Check if the user is subscribed to the channel
    if not await check_channel_subscription(user_id):
        await bot.send_message(
            chat_id=message.chat.id,
            text="Botdan foydalanish uchun kanalimizga qo'shiling./start",
            reply_markup=types.InlineKeyboardMarkup().add(
                types.InlineKeyboardButton("Kanalga qo'shilish", url=f"https://t.me/{CHANNEL_ID[1:]}"),
            ),
        )
        return

    # Welcome message
    await message.reply(
        "Assalomu alaykum! Botdan foydalanishingiz mumkin.",
        reply_markup=main_menu,
    )

@dp.message_handler(lambda message: message.text == "Mening ma'lumotim")
async def my_info_handler(message: types.Message):
    user_id = message.from_user.id

    # Check subscription
    if not await check_channel_subscription(user_id):
        await message.reply("Botdan foydalanish uchun kanalimizga qo'shiling./start ")

        return

    df = load_user_data()
    user_data = df[df["user_id"] == user_id]

    if not user_data.empty:
        user_data = user_data.iloc[0]
        if not user_data["phone"]:
            await message.reply("Telefon raqamingizni kiriting (namuna: +998901234567):", reply_markup=ReplyKeyboardRemove())
            return

        await message.reply(
            f"Ism: {user_data['name']}\n"
            f"Telefon: {user_data['phone']}\n"
            f"Taklif qilganlar soni: {user_data['referrals']}\n"
            f"Coinlar: {user_data['coins']}",
            reply_markup=main_menu,
        )
@dp.message_handler(lambda message: message.text == "Promokod")
async def promocode_handler(message: types.Message):
    await message.reply("Promo kodni kiriting:", reply_markup=types.ForceReply())

@dp.message_handler(lambda message: message.reply_to_message and message.reply_to_message.text == "Promo kodni kiriting:")
async def process_promocode(message: types.Message):
    promocode = message.text.strip()
    df_promo = load_promocodes()  # Promo kodlarni yuklab olish
    df_users = load_user_data()   # Foydalanuvchi ma'lumotlarini yuklab olish

    user_id = message.from_user.id
    if promocode in df_promo["promo_code"].values:  # Agar promo kod mavjud bo'lsa
        promo_data = df_promo[df_promo["promo_code"] == promocode].iloc[0]
        coins = promo_data["coins"]

        df_users.loc[df_users["user_id"] == user_id, "coins"] += coins  # Foydalanuvchiga coin qo'shish
        save_user_data(df_users)
        await message.reply(f"Tabriklaymiz! Siz {coins} coin qo'lga kiritdingiz!", reply_markup=main_menu)
    else:
        await message.reply("Promo kod noto'g'ri yoki amal qilish muddati tugagan.", reply_markup=main_menu)

@dp.message_handler(lambda message: message.text.startswith("+"))
async def save_phone_number_handler(message: types.Message):
    user_id = message.from_user.id
    phone_number = message.text.strip()

    if phone_number.startswith("+") and len(phone_number) >= 10:
        df = load_user_data()
        df.loc[df["user_id"] == user_id, "phone"] = phone_number
        save_user_data(df)
        await message.reply("Telefon raqamingiz saqlandi!", reply_markup=main_menu)
    else:
        await message.reply("Telefon raqam formati noto'g'ri. Qayta kiriting (namuna: +998901234567):")


@dp.message_handler(lambda message: message.text == "Referral link")
async def referral_link_handler(message: types.Message):
    user_id = message.from_user.id

    # Get bot's username using get_me()
    bot_info = await bot.get_me()
    referral_link = f"https://t.me/{bot_info.username}?start={user_id}"  # Referral link to share

    await message.reply(f"Sizning referral link: {referral_link}", reply_markup=main_menu)


if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
