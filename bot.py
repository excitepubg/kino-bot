#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram Kino Bot
Adminlar kinoni yuklaydi va kod beradi
Foydalanuvchilar kod orqali kino olishadi
Majburiy obuna tizimi mavjud
EGA admin - boshqa adminlarni boshqarishi mumkin
"""

import os
import logging
import json
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Set
import asyncio

# Dotenv ni o'rnatish
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import (
    Application, 
    CommandHandler, 
    MessageHandler, 
    CallbackQueryHandler, 
    ContextTypes,
    filters
)

# ========================== KONFIGURATSIYA ==========================
# .env faylidan o'qish yoki default qiymat
BOT_TOKEN = os.getenv("BOT_TOKEN", "8570818233:AAGNh0lZgU4MTRoaM0XyrafOGRLAxHumhis")
OWNER_ID = int(os.getenv("OWNER_ID", "8197301287"))

# Server porti (Render uchun)
PORT = int(os.getenv("PORT", "10000"))

# Adminlar fayli
ADMINS_FILE = "admins.json"

# Ma'lumotlarni saqlash fayllari
MOVIES_FILE = "movies.json"
CHANNELS_FILE = "channels.json"
USERS_FILE = "users.json"

# ========================== LOGGING ==========================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ========================== MA'LUMOTLARNI SAQLASH ==========================
class Database:
    def __init__(self):
        # Fayllar mavjudligini tekshirish
        self.ensure_files_exist()
        self.movies = self.load_data(MOVIES_FILE)
        self.channels = self.load_data(CHANNELS_FILE)
        self.users = self.load_data(USERS_FILE)
        self.admins = self.load_admins()
    
    def ensure_files_exist(self):
        """Fayllar mavjudligini tekshirish va yaratish"""
        for file in [ADMINS_FILE, MOVIES_FILE, CHANNELS_FILE, USERS_FILE]:
            if not os.path.exists(file):
                if file == ADMINS_FILE:
                    data = {"admin_ids": [OWNER_ID]}
                else:
                    data = {}
                
                with open(file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=4)
                logger.info(f"{file} fayli yaratildi")
    
    def load_data(self, filename: str) -> Dict:
        """JSON fayldan ma'lumotlarni yuklash"""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            self.ensure_files_exist()
            return {}
        except json.JSONDecodeError:
            logger.error(f"{filename} faylda JSON xatosi")
            return {}
    
    def load_admins(self) -> Set[int]:
        """Adminlarni yuklash"""
        try:
            with open(ADMINS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                admin_ids = set(data.get("admin_ids", []))
                admin_ids.add(OWNER_ID)  # EGA admin har doim admin
                return admin_ids
        except (FileNotFoundError, json.JSONDecodeError):
            self.ensure_files_exist()
            return {OWNER_ID}
    
    def save_admins(self):
        """Adminlarni saqlash"""
        data = {
            "admin_ids": list(self.admins),
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        with open(ADMINS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    
    def save_data(self, filename: str, data: Dict):
        """Ma'lumotlarni JSON faylga saqlash"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    
    def save_movies(self):
        """Kinolarni saqlash"""
        self.save_data(MOVIES_FILE, self.movies)
    
    def save_channels(self):
        """Kanallarni saqlash"""
        self.save_data(CHANNELS_FILE, self.channels)
    
    def save_users(self):
        """Foydalanuvchilarni saqlash"""
        self.save_data(USERS_FILE, self.users)
    
    # ========== ADMIN FUNKSIYALARI ==========
    def is_admin(self, user_id: int) -> bool:
        """Foydalanuvchi admin ekanligini tekshirish"""
        return user_id in self.admins
    
    def is_owner(self, user_id: int) -> bool:
        """Foydalanuvchi EGA admin ekanligini tekshirish"""
        return user_id == OWNER_ID
    
    def add_admin(self, user_id: int) -> bool:
        """Yangi admin qo'shish (faqat EGA admin uchun)"""
        if user_id not in self.admins:
            self.admins.add(user_id)
            self.save_admins()
            logger.info(f"Yangi admin qo'shildi: {user_id}")
            return True
        return False
    
    def remove_admin(self, user_id: int) -> bool:
        """Adminni o'chirish (faqat EGA admin uchun)"""
        if user_id in self.admins and user_id != OWNER_ID:  # EGAni o'chirib bo'lmaydi
            self.admins.remove(user_id)
            self.save_admins()
            logger.info(f"Admin o'chirildi: {user_id}")
            return True
        return False
    
    def get_admins(self) -> List[int]:
        """Barcha adminlarni olish"""
        return sorted(list(self.admins))
    
    def get_admin_list_for_display(self) -> List[Tuple[int, int]]:
        """Admin ro'yxatini ko'rish uchun tayyorlash"""
        admins = self.get_admins()
        return [(idx + 1, admin_id) for idx, admin_id in enumerate(admins)]
    
    # ========== KINO FUNKSIYALARI ==========
    def add_movie(self, code: str, file_id: str, file_type: str, caption: str = "", uploader_id: int = None):
        """Yangi kino qo'shish"""
        self.movies[code] = {
            "file_id": file_id,
            "file_type": file_type,
            "caption": caption,
            "uploader_id": uploader_id,
            "upload_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "download_count": 0
        }
        self.save_movies()
    
    def get_movie(self, code: str) -> Optional[Dict]:
        """Kod bo'yicha kino olish"""
        return self.movies.get(code)
    
    def increment_download_count(self, code: str):
        """Kino yuklab olish sonini oshirish"""
        if code in self.movies:
            self.movies[code]["download_count"] += 1
            self.save_movies()
    
    def get_all_movies(self) -> Dict:
        """Barcha kinolarni olish"""
        return self.movies
    
    def delete_movie(self, code: str) -> bool:
        """Kino o'chirish"""
        if code in self.movies:
            del self.movies[code]
            self.save_movies()
            logger.info(f"Kino o'chirildi: {code}")
            return True
        return False
    
    # ========== KANAL FUNKSIYALARI ==========
    def add_channel(self, channel_id: str, channel_username: str, channel_name: str):
        """Yangi majburiy kanal qo'shish"""
        self.channels[channel_id] = {
            "username": channel_username,
            "name": channel_name,
            "added_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        self.save_channels()
        logger.info(f"Kanal qo'shildi: {channel_id} - {channel_name}")
    
    def remove_channel(self, channel_id: str) -> bool:
        """Kanal o'chirish"""
        if channel_id in self.channels:
            del self.channels[channel_id]
            self.save_channels()
            logger.info(f"Kanal o'chirildi: {channel_id}")
            return True
        return False
    
    def get_channels(self) -> Dict:
        """Barcha kanallarni olish"""
        return self.channels
    
    def get_channel_ids(self) -> List[str]:
        """Kanallar ID larini olish"""
        return list(self.channels.keys())
    
    def get_channel_list_for_display(self) -> List[Tuple[int, str, Dict]]:
        """Kanal ro'yxatini ko'rish uchun tayyorlash"""
        channel_list = []
        for idx, (channel_id, channel_info) in enumerate(self.channels.items(), 1):
            channel_list.append((idx, channel_id, channel_info))
        return channel_list
    
    # ========== FOYDALANUVCHI FUNKSIYALARI ==========
    def add_user(self, user_id: int):
        """Yangi foydalanuvchi qo'shish"""
        if str(user_id) not in self.users:
            self.users[str(user_id)] = {
                "joined_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "last_activity": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "movies_downloaded": 0,
                "is_subscribed": False
            }
            self.save_users()
    
    def update_user_activity(self, user_id: int):
        """Foydalanuvchi faolligini yangilash"""
        user_id_str = str(user_id)
        if user_id_str in self.users:
            self.users[user_id_str]["last_activity"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.save_users()
    
    def increment_user_downloads(self, user_id: int):
        """Foydalanuvchi yuklab olishlar sonini oshirish"""
        user_id_str = str(user_id)
        if user_id_str in self.users:
            self.users[user_id_str]["movies_downloaded"] += 1
            self.save_users()
    
    def set_user_subscription(self, user_id: int, status: bool):
        """Foydalanuvchi obuna holatini o'rnatish"""
        user_id_str = str(user_id)
        if user_id_str in self.users:
            self.users[user_id_str]["is_subscribed"] = status
            self.save_users()

# Global database obyekti
db = Database()

# ========================== FUNKSIYALAR ==========================
def is_admin(user_id: int) -> bool:
    """Foydalanuvchi admin ekanligini tekshirish"""
    return db.is_admin(user_id)

def is_owner(user_id: int) -> bool:
    """Foydalanuvchi EGA admin ekanligini tekshirish"""
    return db.is_owner(user_id)

def get_admin_keyboard(user_id: int) -> ReplyKeyboardMarkup:
    """Admin paneli uchun pastki tugmalar"""
    if is_owner(user_id):
        # EGA admin uchun maxsus tugmalar
        keyboard = [
            [KeyboardButton("🎬 Kino Yuklash"), KeyboardButton("📢 Kanallarni Ko'rish")],
            [KeyboardButton("➕ Kanal Qo'shish"), KeyboardButton("➖ Kanal O'chirish")],
            [KeyboardButton("👑 Adminlarni Boshqarish"), KeyboardButton("📊 Statistika")],
            [KeyboardButton("📝 Kinolar Ro'yxati"), KeyboardButton("🗑️ Kino O'chirish")],
            [KeyboardButton("🔙 Asosiy Menyu")]
        ]
    else:
        # Oddiy admin uchun tugmalar
        keyboard = [
            [KeyboardButton("🎬 Kino Yuklash"), KeyboardButton("📢 Kanallarni Ko'rish")],
            [KeyboardButton("➕ Kanal Qo'shish"), KeyboardButton("➖ Kanal O'chirish")],
            [KeyboardButton("📊 Statistika"), KeyboardButton("📝 Kinolar Ro'yxati")],
            [KeyboardButton("🗑️ Kino O'chirish"), KeyboardButton("🔙 Asosiy Menyu")]
        ]
    
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

def get_admin_management_keyboard() -> ReplyKeyboardMarkup:
    """Admin boshqaruv uchun pastki tugmalar"""
    keyboard = [
        [KeyboardButton("➕ Yangi Admin Qo'shish")],
        [KeyboardButton("➖ Admin O'chirish")],
        [KeyboardButton("📋 Adminlar Ro'yxati")],
        [KeyboardButton("🔙 Admin Panelga Qaytish")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

def get_user_keyboard() -> ReplyKeyboardMarkup:
    """Foydalanuvchi uchun pastki tugmalar"""
    keyboard = [
        [KeyboardButton("ℹ️ Yordam")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

def get_subscription_keyboard() -> InlineKeyboardMarkup:
    """Obuna bo'lish tugmalari (InlineKeyboard - faqat kanal tugmalari)"""
    channels = db.get_channels()
    keyboard = []
    
    for channel_id, channel_info in channels.items():
        username = channel_info.get("username", "")
        name = channel_info.get("name", "Kanal")
        url = f"https://t.me/{username}" if username else f"https://t.me/{channel_id}"
        keyboard.append([InlineKeyboardButton(f"📢 {name}", url=url)])
    
    keyboard.append([InlineKeyboardButton("✅ Obuna bo'ldim", callback_data="check_subscription")])
    return InlineKeyboardMarkup(keyboard)

async def check_user_subscription(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Foydalanuvchi barcha kanallarga obuna bo'lganligini tekshirish"""
    channels = db.get_channel_ids()
    
    if not channels:
        return True  # Agar kanal yo'q bo'lsa, tekshirish kerak emas
    
    for channel_id in channels:
        try:
            # Kanalga a'zolikni tekshirish
            chat_member = await context.bot.get_chat_member(
                chat_id=channel_id,
                user_id=user_id
            )
            
            # Agar a'zo bo'lmasa yoki chiqib ketgan bo'lsa
            if chat_member.status not in ['member', 'administrator', 'creator']:
                return False
                
        except Exception as e:
            logger.error(f"Kanal tekshirishda xato: {e}")
            # Agar bot kanalda admin bo'lmasa yoki xatolik bo'lsa
            continue
    
    return True

async def force_subscription_check(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Foydalanuvchini majburiy obuna tekshirish"""
    is_subscribed = await check_user_subscription(user_id, context)
    
    if not is_subscribed:
        db.set_user_subscription(user_id, False)
        await update.message.reply_text(
            "⚠️ Botdan foydalanish uchun quyidagi kanallarga obuna bo'ling:",
            reply_markup=get_subscription_keyboard()
        )
        return False
    else:
        db.set_user_subscription(user_id, True)
        return True

async def send_movie_to_user(update: Update, context: ContextTypes.DEFAULT_TYPE, movie_data: Dict):
    """Foydalanuvchiga kino yuborish"""
    file_id = movie_data["file_id"]
    file_type = movie_data["file_type"]
    caption = movie_data.get("caption", "")
    
    try:
        if file_type == "video":
            await context.bot.send_video(chat_id=update.effective_chat.id, video=file_id, caption=caption)
        elif file_type == "document":
            await context.bot.send_document(chat_id=update.effective_chat.id, document=file_id, caption=caption)
        elif file_type == "audio":
            await context.bot.send_audio(chat_id=update.effective_chat.id, audio=file_id, caption=caption)
        else:
            await update.message.reply_text("❌ Kino formati noto'g'ri")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"Kino yuborishda xato: {e}")
        await update.message.reply_text("❌ Kino yuborishda xatolik yuz berdi")
        return False

# ========================== HANDLERLAR ==========================
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/start komandasi"""
    user_id = update.effective_user.id
    db.add_user(user_id)
    db.update_user_activity(user_id)
    
    if is_admin(user_id):
        await update.message.reply_text(
            f"👑 {'EGA Admin' if is_owner(user_id) else 'Admin'} panelga xush kelibsiz!",
            reply_markup=get_admin_keyboard(user_id)
        )
    else:
        # Oddiy foydalanuvchi uchun
        is_subscribed = await check_user_subscription(user_id, context)
        
        if is_subscribed:
            db.set_user_subscription(user_id, True)
            await update.message.reply_text(
                "🎬 Kino botiga xush kelibsiz!\n\n"
                "Kino olish uchun kodni yuboring.\n",
                reply_markup=get_user_keyboard()
            )
        else:
            db.set_user_subscription(user_id, False)
            await update.message.reply_text(
                "⚠️ Botdan foydalanish uchun quyidagi kanallarga obuna bo'ling:",
                reply_markup=get_subscription_keyboard()
            )

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Matnli xabarlarni qayta ishlash"""
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    db.update_user_activity(user_id)
    
    if is_admin(user_id):
        # ========== ADMIN TUGMALARI ==========
        if text == "🎬 Kino Yuklash":
            context.user_data.clear()
            context.user_data['upload_mode'] = True
            context.user_data['awaiting_code'] = True
            
            await update.message.reply_text(
                "📤 Kino yuklash rejimi:\n\n"
                "1. Avval kinoga kod yuboring (faqat raqamlar)\n"
                "2. Keyin kino faylini yuboring (video yoki fayl)\n"
                "3. Izoh yuboring\n\n"
                "Kodni yuboring:"
            )
        
        elif text == "📢 Kanallarni Ko'rish":
            channels = db.get_channels()
            
            if not channels:
                text_msg = "📢 Hozircha hech qanday kanal qo'shilmagan."
            else:
                text_msg = "📢 Majburiy obuna kanallari:\n\n"
                for idx, (channel_id, channel_info) in enumerate(channels.items(), 1):
                    text_msg += f"{idx}. {channel_info['name']}\n"
                    text_msg += f"   ID: {channel_id}\n"
                    text_msg += f"   Username: @{channel_info.get('username', 'yoq')}\n"
                    text_msg += f"   Qo'shilgan: {channel_info['added_date']}\n\n"
            
            await update.message.reply_text(
                text_msg,
                reply_markup=get_admin_keyboard(user_id)
            )
        
        elif text == "➕ Kanal Qo'shish":
            context.user_data.clear()
            context.user_data['add_channel_mode'] = True
            
            await update.message.reply_text(
                "➕ Yangi kanal qo'shish:\n\n"
                "Kanalni shu formatlardan birida yuboring:\n"
                "1. @username (masalan: @kinolar)\n"
                "2. Kanal ID (masalan: -1001234567890)\n\n"
                "Eslatma: Bot kanalda admin bo'lishi kerak!"
            )
        
        elif text == "➖ Kanal O'chirish":
            channels = db.get_channels()
            
            if not channels:
                await update.message.reply_text(
                    "❌ Hozircha hech qanday kanal yo'q.",
                    reply_markup=get_admin_keyboard(user_id)
                )
                return
            
            context.user_data.clear()
            context.user_data['remove_channel_mode'] = True
            
            text_msg = "➖ Kanal o'chirish:\n\n"
            text_msg += "O'chirmoqchi bo'lgan kanalingizni tanlang:\n\n"
            
            for idx, (channel_id, channel_info) in enumerate(channels.items(), 1):
                text_msg += f"{idx}. {channel_info['name']}\n"
                text_msg += f"   ID: {channel_id}\n\n"
            
            text_msg += "🔹 Raqam yuboring (masalan: 1) yoki\n"
            text_msg += "🔹 Bekor qilish uchun: 🔙 Bekor qilish"
            
            await update.message.reply_text(
                text_msg,
                reply_markup=ReplyKeyboardMarkup([[KeyboardButton("🔙 Bekor qilish")]], resize_keyboard=True)
            )
        
        elif text == "👑 Adminlarni Boshqarish" and is_owner(user_id):
            context.user_data.clear()
            await update.message.reply_text(
                "👑 Adminlarni Boshqarish paneli:\n\n"
                "Quyidagi tugmalardan birini tanlang:",
                reply_markup=get_admin_management_keyboard()
            )
        
        elif text == "➕ Yangi Admin Qo'shish" and is_owner(user_id):
            context.user_data.clear()
            context.user_data['add_admin_mode'] = True
            
            await update.message.reply_text(
                "➕ Yangi admin qo'shish:\n\n"
                "Yangi adminning Telegram ID sini yuboring.\n"
                "ID faqat raqamlardan iborat bo'lishi kerak.\n\n"
                "Masalan: 1234567890\n\n"
                "Admin ID sini yuboring:",
                reply_markup=ReplyKeyboardMarkup([[KeyboardButton("🔙 Bekor qilish")]], resize_keyboard=True)
            )
        
        elif text == "➖ Admin O'chirish" and is_owner(user_id):
            admins = db.get_admins()
            
            if len(admins) <= 1:  # Faqat EGA admin bor
                await update.message.reply_text(
                    "❌ Hozircha boshqa adminlar yo'q.\n"
                    "Faqat EGA admin mavjud.",
                    reply_markup=get_admin_management_keyboard()
                )
                return
            
            context.user_data.clear()
            context.user_data['remove_admin_mode'] = True
            
            text_msg = "➖ Admin o'chirish:\n\n"
            text_msg += "O'chirmoqchi bo'lgan adminingiz **raqamini** yuboring:\n\n"
            
            admin_list = []
            for idx, admin_id in enumerate(admins, 1):
                admin_type = "👑 EGA" if admin_id == OWNER_ID else "👤 Admin"
                admin_list.append((idx, admin_id))
                text_msg += f"{idx}. {admin_type} - ID: {admin_id}\n"
            
            context.user_data['admin_list'] = admin_list
            
            await update.message.reply_text(
                text_msg,
                reply_markup=ReplyKeyboardMarkup([[KeyboardButton("🔙 Bekor qilish")]], resize_keyboard=True)
            )
        
        elif text == "📋 Adminlar Ro'yxati" and is_owner(user_id):
            admins = db.get_admins()
            
            text_msg = "👑 Adminlar ro'yxati:\n\n"
            for idx, admin_id in enumerate(admins, 1):
                admin_type = "👑 EGA" if admin_id == OWNER_ID else "👤 Admin"
                text_msg += f"{idx}. {admin_type} - ID: {admin_id}\n"
            
            text_msg += f"\n📊 Jami adminlar: {len(admins)} ta"
            
            await update.message.reply_text(
                text_msg,
                reply_markup=get_admin_management_keyboard()
            )
        
        elif text == "🔙 Admin Panelga Qaytish":
            context.user_data.clear()
            await update.message.reply_text(
                f"👑 {'EGA Admin' if is_owner(user_id) else 'Admin'} panelga qaytildi!",
                reply_markup=get_admin_keyboard(user_id)
            )
        
        elif text == "🔙 Bekor qilish":
            context.user_data.clear()
            await update.message.reply_text(
                f"👑 {'EGA Admin' if is_owner(user_id) else 'Admin'} panelga qaytildi!",
                reply_markup=get_admin_keyboard(user_id)
            )
        
        elif text == "🔙 Asosiy Menyu":
            context.user_data.clear()
            await update.message.reply_text(
                f"👑 {'EGA Admin' if is_owner(user_id) else 'Admin'} panelga xush kelibsiz!",
                reply_markup=get_admin_keyboard(user_id)
            )
        
        elif text == "📊 Statistika":
            movies_count = len(db.get_all_movies())
            channels_count = len(db.get_channels())
            users_count = len(db.users)
            admins_count = len(db.get_admins())
            
            total_downloads = sum(movie.get("download_count", 0) for movie in db.movies.values())
            
            text_msg = f"📊 Bot statistikasi:\n\n"
            text_msg += f"🎬 Kinolar soni: {movies_count}\n"
            text_msg += f"📢 Kanallar soni: {channels_count}\n"
            text_msg += f"👥 Foydalanuvchilar: {users_count}\n"
            text_msg += f"👑 Adminlar soni: {admins_count}\n"
            text_msg += f"📥 Yuklab olishlar: {total_downloads}\n\n"
            
            # Eng ko'p yuklangan kinolar
            if movies_count > 0:
                text_msg += "🏆 Eng ko'p yuklangan kinolar:\n"
                sorted_movies = sorted(
                    db.movies.items(),
                    key=lambda x: x[1].get("download_count", 0),
                    reverse=True
                )[:5]
                
                for idx, (code, movie_info) in enumerate(sorted_movies, 1):
                    text_msg += f"{idx}. {code}: {movie_info.get('download_count', 0)} marta\n"
            
            await update.message.reply_text(
                text_msg,
                reply_markup=get_admin_keyboard(user_id)
            )
        
        elif text == "📝 Kinolar Ro'yxati":
            movies = db.get_all_movies()
            
            if not movies:
                text_msg = "🎬 Hozircha hech qanday kino yuklanmagan."
            else:
                text_msg = "🎬 Barcha kinolar ro'yxati:\n\n"
                for idx, (code, movie_info) in enumerate(movies.items(), 1):
                    text_msg += f"{idx}. Kod: {code}\n"
                    text_msg += f"   Izoh: {movie_info.get('caption', 'Izohsiz')[:50]}...\n"
                    text_msg += f"   Yuklangan: {movie_info['upload_date']}\n"
                    text_msg += f"   Yuklab olishlar: {movie_info.get('download_count', 0)}\n\n"
            
            await update.message.reply_text(
                text_msg,
                reply_markup=get_admin_keyboard(user_id)
            )
        
        elif text == "🗑️ Kino O'chirish":
            movies = db.get_all_movies()
            
            if not movies:
                await update.message.reply_text(
                    "❌ Hozircha hech qanday kino yo'q.",
                    reply_markup=get_admin_keyboard(user_id)
                )
                return
            
            context.user_data.clear()
            context.user_data['delete_movie_mode'] = True
            
            text_msg = "🗑️ Kino o'chirish:\n\n"
            text_msg += "O'chirmoqchi bo'lgan kino kodini yuboring:\n\n"
            
            for idx, (code, movie_info) in enumerate(movies.items(), 1):
                text_msg += f"{idx}. Kod: {code}\n"
                text_msg += f"   Izoh: {movie_info.get('caption', 'Izohsiz')[:30]}...\n\n"
            
            text_msg += "🔹 Kino kodini yuboring\n"
            text_msg += "🔹 Bekor qilish uchun: 🔙 Bekor qilish"
            
            await update.message.reply_text(
                text_msg,
                reply_markup=ReplyKeyboardMarkup([[KeyboardButton("🔙 Bekor qilish")]], resize_keyboard=True)
            )
        
        # ========== KINO O'CHIRISH REJIMI ==========
        elif 'delete_movie_mode' in context.user_data and context.user_data['delete_movie_mode']:
            movie_input = text.strip()
            
            # Bekor qilish tugmasi
            if movie_input == "🔙 Bekor qilish":
                context.user_data.clear()
                await update.message.reply_text(
                    f"👑 {'EGA Admin' if is_owner(user_id) else 'Admin'} panelga qaytildi!",
                    reply_markup=get_admin_keyboard(user_id)
                )
                return
            
            # Kino kodini tekshirish va darhol o'chirish
            movies = db.get_all_movies()
            
            if movie_input in movies:
                movie_info = movies[movie_input]
                
                # Kino o'chirish
                if db.delete_movie(movie_input):
                    await update.message.reply_text(
                        f"✅ Kino muvaffaqiyatli o'chirildi!\n\n"
                        f"📽 Kino kodi: {movie_input}\n"
                        f"📝 Izoh: {movie_info.get('caption', 'Izohsiz')}\n"
                        f"📅 Yuklangan: {movie_info['upload_date']}\n"
                        f"📥 Yuklab olishlar: {movie_info.get('download_count', 0)}\n"
                        f"🗑️ O'chirilgan vaqt: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                        reply_markup=get_admin_keyboard(user_id)
                    )
                else:
                    await update.message.reply_text(
                        "❌ Kino o'chirishda xatolik yuz berdi!",
                        reply_markup=get_admin_keyboard(user_id)
                    )
            else:
                await update.message.reply_text(
                    f"❌ {movie_input} kodli kino topilmadi!\n\n"
                    f"Qaytadan urinib ko'ring yoki '🔙 Bekor qilish' tugmasini bosing.",
                    reply_markup=ReplyKeyboardMarkup([[KeyboardButton("🔙 Bekor qilish")]], resize_keyboard=True)
                )
            
            context.user_data.clear()
        
        # ========== KANAL O'CHIRISH REJIMI ==========
        elif 'remove_channel_mode' in context.user_data and context.user_data['remove_channel_mode']:
            channel_input = text.strip()
            
            # Bekor qilish tugmasi
            if channel_input == "🔙 Bekor qilish":
                context.user_data.clear()
                await update.message.reply_text(
                    f"👑 {'EGA Admin' if is_owner(user_id) else 'Admin'} panelga qaytildi!",
                    reply_markup=get_admin_keyboard(user_id)
                )
                return
            
            # Kanallar ro'yxatidan raqam orqali o'chirish
            if channel_input.isdigit():
                channel_number = int(channel_input)
                channels_list = list(db.get_channels().items())
                
                if 1 <= channel_number <= len(channels_list):
                    channel_id, channel_info = channels_list[channel_number - 1]
                    
                    if db.remove_channel(channel_id):
                        await update.message.reply_text(
                            f"✅ Kanal muvaffaqiyatli o'chirildi!\n"
                            f"📢 Kanal: {channel_info['name']}\n"
                            f"🔗 ID: {channel_id}",
                            reply_markup=get_admin_keyboard(user_id)
                        )
                    else:
                        await update.message.reply_text(
                            f"❌ Kanal o'chirishda xatolik!",
                            reply_markup=get_admin_keyboard(user_id)
                        )
                else:
                    await update.message.reply_text(
                        f"❌ Noto'g'ri raqam: {channel_number}\n"
                        f"Faqat 1 dan {len(channels_list)} gacha raqam yuboring.",
                        reply_markup=ReplyKeyboardMarkup([[KeyboardButton("🔙 Bekor qilish")]], resize_keyboard=True)
                    )
                    return
            
            # To'g'ridan-to'g'ri kanal ID si orqali o'chirish
            else:
                # Kanal ID sini qirqib olish (agar @username bo'lsa)
                if channel_input.startswith('@'):
                    # @username formatidan ID olish uchun tekshirish
                    channels = db.get_channels()
                    found = False
                    
                    for ch_id, ch_info in channels.items():
                        if ch_info.get('username', '').lstrip('@') == channel_input.lstrip('@'):
                            if db.remove_channel(ch_id):
                                await update.message.reply_text(
                                    f"✅ Kanal muvaffaqiyatli o'chirildi!\n"
                                    f"📢 Kanal: {ch_info['name']}\n"
                                    f"🔗 Username: {channel_input}",
                                    reply_markup=get_admin_keyboard(user_id)
                                )
                                found = True
                                break
                    
                    if not found:
                        await update.message.reply_text(
                            f"❌ {channel_input} kanali topilmadi!",
                            reply_markup=get_admin_keyboard(user_id)
                        )
                
                else:
                    # To'g'ridan-to'g'ri kanal ID si
                    channel = db.get_channels().get(channel_input)
                    if channel:
                        if db.remove_channel(channel_input):
                            await update.message.reply_text(
                                f"✅ Kanal muvaffaqiyatli o'chirildi!\n"
                                f"📢 Kanal: {channel['name']}\n"
                                f"🔗 ID: {channel_input}",
                                reply_markup=get_admin_keyboard(user_id)
                            )
                        else:
                            await update.message.reply_text(
                                f"❌ Kanal o'chirishda xatolik!",
                                reply_markup=get_admin_keyboard(user_id)
                            )
                    else:
                        await update.message.reply_text(
                            f"❌ {channel_input} ID li kanal topilmadi!",
                            reply_markup=get_admin_keyboard(user_id)
                        )
            
            context.user_data.clear()
        
        # ========== KINO YUKLASH REJIMI ==========
        elif 'upload_mode' in context.user_data and context.user_data['upload_mode']:
            # Kod kutilmoqda
            if 'awaiting_code' in context.user_data and context.user_data['awaiting_code']:
                code = text
                context.user_data['movie_code'] = code
                context.user_data['awaiting_code'] = False
                
                await update.message.reply_text(
                    f"✅ Kod qabul qilindi: {code}\n"
                    f"Endi kino faylini yuboring (video yoki fayl sifatida)."
                )
            
            # Kino yuklandi, caption kutilmoqda
            elif 'awaiting_caption' in context.user_data and context.user_data['awaiting_caption']:
                caption = text
                movie_data = context.user_data.get('movie_data')
                code = context.user_data.get('movie_code')
                
                if movie_data and code:
                    db.add_movie(
                        code=code,
                        file_id=movie_data['file_id'],
                        file_type=movie_data['file_type'],
                        caption=caption,
                        uploader_id=user_id
                    )
                    
                    await update.message.reply_text(
                        f"✅ Kino muvaffaqiyatli saqlandi!\n"
                        f"Kod: {code}\n"
                        f"Izoh: {caption}",
                        reply_markup=get_admin_keyboard(user_id)
                    )
                    
                    context.user_data.clear()
                else:
                    await update.message.reply_text("❌ Xatolik yuz berdi. Qaytadan boshlang.")
        
        # ========== KANAL QO'SHISH REJIMI ==========
        elif 'add_channel_mode' in context.user_data and context.user_data['add_channel_mode']:
            # Kanal ma'lumotlari formatda: @username yoki -1001234567890
            channel_info = text
            
            try:
                # Kanal ma'lumotlarini olish
                if channel_info.startswith('@'):
                    chat = await context.bot.get_chat(channel_info)
                else:
                    chat = await context.bot.get_chat(int(channel_info))
                
                # Kanalni bazaga qo'shish
                db.add_channel(
                    channel_id=str(chat.id),
                    channel_username=chat.username or "",
                    channel_name=chat.title
                )
                
                await update.message.reply_text(
                    f"✅ Kanal muvaffaqiyatli qo'shildi!\n"
                    f"Nomi: {chat.title}\n"
                    f"ID: {chat.id}\n"
                    f"Username: @{chat.username or 'yoq'}",
                    reply_markup=get_admin_keyboard(user_id)
                )
                
                context.user_data.clear()
                
            except Exception as e:
                await update.message.reply_text(f"❌ Xatolik: {e}\n\nQaytadan urinib ko'ring yoki /start bilan boshlang.")
        
        # ========== YANGI ADMIN QO'SHISH REJIMI ==========
        elif 'add_admin_mode' in context.user_data and context.user_data['add_admin_mode']:
            if text == "🔙 Bekor qilish":
                context.user_data.clear()
                await update.message.reply_text(
                    "👑 Adminlarni Boshqarish paneliga qaytildi!",
                    reply_markup=get_admin_management_keyboard()
                )
                return
            
            if text.isdigit():
                new_admin_id = int(text)
                
                # O'zini qo'shishni oldini olish
                if new_admin_id == user_id:
                    await update.message.reply_text("❌ O'zingizni qo'shib bo'lmaydi!")
                    return
                
                if new_admin_id == OWNER_ID:
                    await update.message.reply_text("❌ EGA admin allaqachon mavjud!")
                    return
                
                if db.add_admin(new_admin_id):
                    await update.message.reply_text(
                        f"✅ Admin muvaffaqiyatli qo'shildi!\n"
                        f"👤 ID: {new_admin_id}\n\n"
                        f"Yangi admin botga /start yuborishi kerak.",
                        reply_markup=get_admin_management_keyboard()
                    )
                else:
                    await update.message.reply_text(
                        f"⚠️ Bu admin allaqachon mavjud!\n"
                        f"👤 ID: {new_admin_id}",
                        reply_markup=get_admin_management_keyboard()
                    )
                
                context.user_data.clear()
            
            else:
                await update.message.reply_text(
                    "❌ Faqat admin ID sini yuboring (raqam).\n"
                    "Masalan: 1234567890",
                    reply_markup=ReplyKeyboardMarkup([[KeyboardButton("🔙 Bekor qilish")]], resize_keyboard=True)
                )
        
        # ========== ADMIN O'CHIRISH REJIMI ==========
        elif 'remove_admin_mode' in context.user_data and context.user_data['remove_admin_mode']:
            if text == "🔙 Bekor qilish":
                context.user_data.clear()
                await update.message.reply_text(
                    "👑 Adminlarni Boshqarish paneliga qaytildi!",
                    reply_markup=get_admin_management_keyboard()
                )
                return
            
            if text.isdigit():
                admin_number = int(text)
                admin_list = context.user_data.get('admin_list', [])
                
                if 1 <= admin_number <= len(admin_list):
                    idx, admin_id = admin_list[admin_number - 1]
                    
                    # EGA adminni o'chirib bo'lmaydi
                    if admin_id == OWNER_ID:
                        await update.message.reply_text(
                            "❌ EGA adminni o'chirib bo'lmaydi!",
                            reply_markup=get_admin_management_keyboard()
                        )
                        context.user_data.clear()
                        return
                    
                    if db.remove_admin(admin_id):
                        await update.message.reply_text(
                            f"✅ Admin muvaffaqiyatli o'chirildi!\n"
                            f"👤 ID: {admin_id}",
                            reply_markup=get_admin_management_keyboard()
                        )
                    else:
                        await update.message.reply_text(
                            f"❌ Admin o'chirishda xatolik!",
                            reply_markup=get_admin_management_keyboard()
                        )
                else:
                    await update.message.reply_text(
                        f"❌ Noto'g'ri raqam: {admin_number}\n"
                        f"Faqat 1 dan {len(admin_list)} gacha raqam yuboring.",
                        reply_markup=ReplyKeyboardMarkup([[KeyboardButton("🔙 Bekor qilish")]], resize_keyboard=True)
                    )
                
                context.user_data.clear()
            
            else:
                # Raqam emas, ehtimol to'g'ridan-to'g'ri ID yuborilgan
                if text.isdigit():
                    admin_id = int(text)
                    
                    if admin_id == OWNER_ID:
                        await update.message.reply_text("❌ EGA adminni o'chirib bo'lmaydi!")
                        return
                    
                    if db.remove_admin(admin_id):
                        await update.message.reply_text(
                            f"✅ Admin muvaffaqiyatli o'chirildi!\n"
                            f"👤 ID: {admin_id}",
                            reply_markup=get_admin_management_keyboard()
                        )
                    else:
                        await update.message.reply_text(
                            f"❌ Admin topilmadi yoki o'chirishda xatolik!",
                            reply_markup=get_admin_management_keyboard()
                        )
                else:
                    await update.message.reply_text(
                        "❌ Faqat raqam yuboring!\n"
                        "Masalan: 1, 2, 3 vahokazo.",
                        reply_markup=ReplyKeyboardMarkup([[KeyboardButton("🔙 Bekor qilish")]], resize_keyboard=True)
                    )
                
                context.user_data.clear()
    
    else:
        # ========== FOYDALANUVCHI ==========
        # Avval obuna tekshirish
        subscribed = await force_subscription_check(update, context, user_id)
        if not subscribed:
            return
        
        # Foydalanuvchi tugmalarini qayta ishlash
        if text == "ℹ️ Yordam":
            await update.message.reply_text(
                "🎬 Kino Bot - Yordam\n\n"
                "📥 Kino olish uchun kanalda tashlangan kodlardan yuboring.\n"
                "📢 Botdan foydalish uchun kanallarga obuna bo'lishingiz kerak ❗\n"
                "🔧 Muammo bo'lsa: @Sanjar_907",
                reply_markup=get_user_keyboard()
            )
        
        else:
            # Kino kodi yuborildi
            # Avval obuna tekshirish
            subscribed = await force_subscription_check(update, context, user_id)
            if not subscribed:
                return
            
            db.set_user_subscription(user_id, True)
            
            movie_data = db.get_movie(text)
            
            if movie_data:
                success = await send_movie_to_user(update, context, movie_data)
                
                if success:
                    db.increment_download_count(text)
                    db.increment_user_downloads(user_id)

            else:
                await update.message.reply_text(
                    "❌ Kino topilmadi.\n"
                    "Kodni tekshirib, qaytadan urinib ko'ring."
                )

async def handle_file_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fayl yuborilganda"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        return
    
    # Admin kino yuklash rejimida bo'lsa
    if 'upload_mode' in context.user_data and context.user_data['upload_mode']:
        if 'movie_code' not in context.user_data:
            await update.message.reply_text("❌ Avval kodni yuboring!")
            return
        
        # Fayl ma'lumotlarini olish
        if update.message.video:
            file_id = update.message.video.file_id
            file_type = "video"
        elif update.message.document:
            file_id = update.message.document.file_id
            file_type = "document"
        elif update.message.audio:
            file_id = update.message.audio.file_id
            file_type = "audio"
        else:
            await update.message.reply_text("❌ Qo'llab-quvvatlanmaydigan fayl turi!")
            return
        
        # Ma'lumotlarni saqlash
        context.user_data['movie_data'] = {
            'file_id': file_id,
            'file_type': file_type
        }
        context.user_data['awaiting_caption'] = True
        
        await update.message.reply_text(
            "✅ Fayl qabul qilindi!\n"
            "Endi kinoga izoh (caption) yuboring.\n"
            "Agar izoh bermoqchi bo'lmasangiz, faqat '.' yuboring."
        )

async def callback_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tugmalar bosilganda"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    if data == "check_subscription":
        # Obuna tekshirish tugmasi
        is_subscribed = await check_user_subscription(user_id, context)
        
        if is_subscribed:
            db.set_user_subscription(user_id, True)
            await query.edit_message_text(
                "✅ Obuna tekshirildi! Botdan foydalanishingiz mumkin.\n\n"
                "Kino olish uchun kodni yuboring.\n"
            )
        else:
            await query.edit_message_text(
                "❌ Hali barcha kanallarga obuna bo'lmagansiz!\n"
                "Iltimos, barcha kanallarga obuna bo'lib, yana tekshiring.",
                reply_markup=get_subscription_keyboard()
            )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xatolarni qayta ishlash"""
    logger.error(f"Xatolik yuz berdi: {context.error}")
    
    try:
        await context.bot.send_message(
            chat_id=OWNER_ID,
            text=f"❌ Botda xatolik:\n{context.error}"
        )
    except:
        pass

async def run_server():
    """Server ishga tushirish"""
    # Bot yaratish
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Handlerlarni qo'shish
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CallbackQueryHandler(callback_query_handler))
    
    # Fayl yuborish handleri
    application.add_handler(MessageHandler(
        filters.VIDEO | filters.Document.ALL | filters.AUDIO,
        handle_file_message
    ))
    
    # Matnli xabarlar handleri
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
    
    # Xatolik handleri
    application.add_error_handler(error_handler)
    
    # Botni ishga tushirish
    print("🤖 Bot ishga tushdi...")
    print(f"👑 EGA Admin ID: {OWNER_ID}")
    print(f"👤 Adminlar soni: {len(db.get_admins())}")
    print(f"🎬 Kinolar soni: {len(db.movies)}")
    print(f"📢 Kanallar soni: {len(db.channels)}")
    print(f"👥 Foydalanuvchilar soni: {len(db.users)}")
    print(f"🌐 PORT: {PORT}")
    
    # Polling ni ishga tushirish
    await application.initialize()
    await application.start()
    await application.updater.start_polling(allowed_updates=Update.ALL_TYPES)

# ========================== ASOSIY FUNKSIYA ==========================
def main():
    """Botni ishga tushirish"""
    # Bot yaratish
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Handlerlarni qo'shish
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CallbackQueryHandler(callback_query_handler))
    
    # Fayl yuborish handleri
    application.add_handler(MessageHandler(
        filters.VIDEO | filters.Document.ALL | filters.AUDIO,
        handle_file_message
    ))
    
    # Matnli xabarlar handleri
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
    
    # Xatolik handleri
    application.add_error_handler(error_handler)
    
    # Botni ishga tushirish
    print("🤖 Bot ishga tushdi...")
    print(f"👑 EGA Admin ID: {OWNER_ID}")
    print(f"👤 Adminlar soni: {len(db.get_admins())}")
    print(f"🎬 Kinolar soni: {len(db.movies)}")
    print(f"📢 Kanallar soni: {len(db.channels)}")
    print(f"👥 Foydalanuvchilar soni: {len(db.users)}")
    print("\n📱 Admin panellari:")
    print("   👑 EGA Admin: 9 ta tugma (admin boshqaruv bilan)")
    print("   👤 Oddiy Admin: 8 ta tugma")
    print("   👤 Foydalanuvchi: 1 ta tugma")
    print("\n👑 Admin Boshqaruv paneli (4 ta tugma):")
    print("   ➕ Yangi Admin Qo'shish")
    print("   ➖ Admin O'chirish") 
    print("   📋 Adminlar Ro'yxati")
    print("   🔙 Admin Panelga Qaytish")
    print("\n🎬 Kino o'chirish funksiyasi - Soddalashtirildi!")
    print("   ✅ '🗑️ Kino O'chirish' tugmasi")
    print("   ✅ Kino kodi yuborilgach darhol o'chiriladi")
    print("   ❌ TASDIQLASH KERAK EMAS!")
    print("   ✅ To'liq ma'lumot bilan o'chirish natijasi")
    print("\n✅ Kanal qo'shish: TO'LIQ ISHLAYDI")
    print("✅ Kanal ko'rish: TO'LIQ ISHLAYDI")
    print("✅ Kanal o'chirish: TO'LIQ ISHLAYDI")
    print("✅ Kino o'chirish: TO'LIQ ISHLAYDI (tasdiqlashsiz!)")
    print("✅ Admin boshqaruv: FAQAT EGA admin uchun")
    print("\n🔧 Kino o'chirish jarayoni ENDI SADDODA:")
    print("   1. '🗑️ Kino O'chirish' tugmasini bosing")
    print("   2. Kino kodini kiriting (masalan: 15)")
    print("   3. Kino DARHOL o'chiriladi")
    print("   4. Bekor qilish uchun '🔙 Bekor qilish' tugmasi")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

# ========================== RENDER.COM uchun QO'SHIMCHA ==========================
if __name__ == "__main__":
    # Fayllarni yaratish (agar mavjud bo'lmasa)
    for file in [MOVIES_FILE, CHANNELS_FILE, USERS_FILE, ADMINS_FILE]:
        if not os.path.exists(file):
            if file == ADMINS_FILE:
                data = {"admin_ids": [OWNER_ID]}
                with open(file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=4)
            else:
                with open(file, 'w', encoding='utf-8') as f:
                    json.dump({}, f, ensure_ascii=False, indent=4)
    
    # RENDER uchun PORT ni ishlatish
    import os
    PORT = int(os.environ.get('PORT', 10000))
    
    print(f"🚀 Render.com da ishga tushmoqda...")
    print(f"🌐 PORT: {PORT}")
    
    # Botni ishga tushirish
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Bot to'xtatildi")
    except Exception as e:
        logger.error(f"Asosiy xatolik: {e}")
        print(f"❌ Xatolik: {e}")

