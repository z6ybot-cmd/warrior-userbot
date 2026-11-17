import os
import re
import asyncio
import sqlite3
import secrets
import io
import aiohttp
import time
import logging
import random
import json
from html.parser import HTMLParser
from datetime import datetime, timedelta
from dotenv import load_dotenv
from telethon import TelegramClient, events, Button, errors
from telethon.tl import types as tl_types

# ==========================================
# 1. نظام سجلات الأحداث (Logging System)
# ==========================================
logging.basicConfig(
    format='[%(levelname)s] %(asctime)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger("AuraESIMBot")

load_dotenv()

API_ID = 20867472
API_HASH = "abedd7fb77eaf1f88bd3f286ea952253"
BOT_TOKEN = "8095468555:AAGE__Qf3hEOKY0deVsGgzHjPLvFCTAmhUY"
DEV_ID = 115431561

OPENROUTER_API_KEY = "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"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

DEFAULT_LPA = "LPA:1$hfy.prod.ondemandconnectivity.com$FA1BEB0FB081104C79BAD7E29424A4101C6BD12873E8733BD856AFF7A7B6DECC"
DEFAULT_BARCODE = f"https://api.qrserver.com/v1/create-qr-code/?data={DEFAULT_LPA}&size=500x500"

CHANNEL_ID = -1003968712197
CUSTOM_EMOJIS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "custom_emojis.json")

# ==========================================
# 2. نظام إدارة Telegram Premium Custom Emojis
# ==========================================
DEFAULT_CUSTOM_EMOJI_SCHEMA = {
    "store": {"store_logo": "", "store_banner": "", "home": "", "personal_section": "", "welcome_spark": ""},
    "products": {"product": "", "vodafone": "", "holafly": "", "maya": "", "sim_card": "", "global_plan": "", "discount": "", "stock": ""},
    "countries": {"countries_globe": "", "coverage": "", "country_default": ""},
    "wallet": {"wallet": "", "balance": "", "deposit": "", "withdraw": "", "referral": ""},
    "payments": {"payment": "", "binance": "", "bybit": "", "crypto": "", "invoice": "", "receipt": ""},
    "orders": {"orders": "", "cart": "", "cart_add": "", "cart_remove": "", "qr_code": "", "lpa_code": ""},
    "vip": {"vip": "", "premium": "", "crown": "", "warranty": ""},
    "dealers": {"dealer": "", "api_key": "", "wholesale": ""},
    "admin": {"admin_panel": "", "users": "", "categories": "", "ban": "", "broadcast": "", "stats": ""},
    "developers": {"developer": "", "system": "", "logs": ""},
    "support": {"support": "", "ticket": "", "reply": ""},
    "success": {"success": "", "verified": "", "approved": ""},
    "failure": {"error": "", "rejected": "", "out_of_stock": ""},
    "warning": {"warning": "", "low_stock": "", "alert": ""},
    "pending": {"pending": "", "loading": "", "processing": ""},
    "settings": {"settings": "", "language": "", "lang_ar": "", "lang_en": ""},
}

CATEGORY_LABELS_AR = {
    "store": "المتجر",
    "products": "المنتجات والباقات",
    "countries": "الدول",
    "wallet": "المحفظة",
    "payments": "المدفوعات",
    "orders": "الطلبات",
    "vip": "VIP وPremium",
    "dealers": "التجار",
    "admin": "الإدارة",
    "developers": "المطورين",
    "support": "الدعم الفني",
    "success": "النجاح",
    "failure": "الفشل",
    "warning": "التحذير",
    "pending": "الانتظار",
    "settings": "الإعدادات",
}


class PremiumEmojiManager:
    """مدير مركزي لإيموجيات Telegram Premium المخصصة فقط بدون أي Unicode Emojis."""

    def __init__(self, config_path: str = CUSTOM_EMOJIS_FILE):
        self.config_path = config_path
        self.data = {}
        self.load()

    @staticmethod
    def validate_id(raw_val) -> str:
        if raw_val is None:
            return ""
        s = str(raw_val).strip()
        if not s:
            return ""
        if not s.isdigit():
            return ""
        if len(s) < 10 or int(s) <= 0:
            return ""
        return s

    def load(self):
        merged = {cat: dict(keys) for cat, keys in DEFAULT_CUSTOM_EMOJI_SCHEMA.items()}
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                if isinstance(raw, dict):
                    for cat, keys in raw.items():
                        if cat.startswith("_") or not isinstance(keys, dict):
                            continue
                        if cat not in merged:
                            merged[cat] = {}
                        for k, v in keys.items():
                            merged[cat][k] = self.validate_id(v)
            except Exception as e:
                logger.warning(f"Failed loading custom_emojis.json: {e}")
        self.data = merged

    def save(self):
        payload = {
            "_meta": {
                "description": "Centralized Telegram Premium Custom Emoji IDs for Aura eSIM Elite.",
                "version": "1.0",
            }
        }
        payload.update(self.data)
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed saving custom_emojis.json: {e}")

    def sync_from_db(self, db_conn):
        try:
            row = db_conn.execute("SELECT value FROM settings WHERE key='custom_emojis_json'").fetchone()
            if row and row[0]:
                raw = json.loads(row[0])
                if isinstance(raw, dict):
                    for cat, keys in raw.items():
                        if cat.startswith("_") or not isinstance(keys, dict):
                            continue
                        self.data.setdefault(cat, {})
                        for k, v in keys.items():
                            self.data[cat][k] = self.validate_id(v)
        except Exception as e:
            logger.warning(f"sync_from_db custom emojis skipped: {e}")

    def save_to_db(self, db_conn):
        try:
            db_conn.execute(
                "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                ("custom_emojis_json", json.dumps(self.data, ensure_ascii=False))
            )
            db_conn.commit()
        except Exception as e:
            logger.error(f"save_to_db custom emojis error: {e}")

    def get_id(self, key: str, category: str = None) -> str:
        if category and category in self.data:
            return self.validate_id(self.data[category].get(key, ""))
        for cat, keys in self.data.items():
            if key in keys:
                return self.validate_id(keys[key])
        return ""

    def set_id(self, category: str, key: str, raw_id: str, db_conn=None) -> tuple:
        if category not in self.data:
            return False, "تصنيف الإيموجي غير موجود."
        s = str(raw_id or "").strip()
        if s in ("", "0", "clear", "none", "-"):
            self.data[category][key] = ""
            self.save()
            if db_conn is not None:
                self.save_to_db(db_conn)
            return True, "تم مسح معرف الإيموجي المخصص بنجاح."
        valid = self.validate_id(s)
        if not valid:
            return False, "معرف Custom Emoji غير صالح. يجب أن يكون رقماً صحيحاً مكوناً من 10 أرقام على الأقل."
        self.data[category][key] = valid
        self.save()
        if db_conn is not None:
            self.save_to_db(db_conn)
        return True, "تم حفظ معرف الإيموجي المخصص بنجاح."

    def tag(self, key: str, category: str = None, space_after: bool = True) -> str:
        eid = self.get_id(key, category=category)
        if not eid:
            return ""
        suffix = " " if space_after else ""
        return f'<tg-emoji emoji-id="{eid}">✦</tg-emoji>{suffix}'


emoji_mgr = PremiumEmojiManager()


def ce(key: str, category: str = None, space_after: bool = True) -> str:
    return emoji_mgr.tag(key, category=category, space_after=space_after)


def _utf16_len(s: str) -> int:
    return len(s.encode("utf-16-le")) // 2


class _TelethonHTMLParser(HTMLParser):
    """محلل HTML متوافق مع Telethon يدعم <tg-emoji> و <blockquote> مع حساب إزاحات UTF-16 بدقة."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.text_parts = []
        self.utf16_offset = 0
        self.stack = []
        self.entities = []

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        attr_map = dict(attrs)
        self.stack.append((tag, self.utf16_offset, attr_map))

    def handle_data(self, data):
        if not data:
            return
        self.text_parts.append(data)
        self.utf16_offset += _utf16_len(data)

    def handle_endtag(self, tag):
        tag = tag.lower()
        idx = None
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                idx = i
                break
        if idx is None:
            return
        _, start_off, attr_map = self.stack.pop(idx)
        length = self.utf16_offset - start_off
        if length <= 0:
            return

        if tag in ("b", "strong") and hasattr(tl_types, "MessageEntityBold"):
            self.entities.append(tl_types.MessageEntityBold(start_off, length))
        elif tag in ("i", "em") and hasattr(tl_types, "MessageEntityItalic"):
            self.entities.append(tl_types.MessageEntityItalic(start_off, length))
        elif tag == "u" and hasattr(tl_types, "MessageEntityUnderline"):
            self.entities.append(tl_types.MessageEntityUnderline(start_off, length))
        elif tag in ("s", "del", "strike") and hasattr(tl_types, "MessageEntityStrike"):
            self.entities.append(tl_types.MessageEntityStrike(start_off, length))
        elif tag == "code" and hasattr(tl_types, "MessageEntityCode"):
            self.entities.append(tl_types.MessageEntityCode(start_off, length))
        elif tag == "pre" and hasattr(tl_types, "MessageEntityPre"):
            self.entities.append(tl_types.MessageEntityPre(start_off, length, attr_map.get("language", "")))
        elif tag == "a" and attr_map.get("href") and hasattr(tl_types, "MessageEntityTextUrl"):
            self.entities.append(tl_types.MessageEntityTextUrl(start_off, length, attr_map["href"]))
        elif tag == "blockquote" and hasattr(tl_types, "MessageEntityBlockquote"):
            self.entities.append(tl_types.MessageEntityBlockquote(start_off, length))
        elif tag == "tg-emoji":
            eid = PremiumEmojiManager.validate_id(attr_map.get("emoji-id"))
            if eid and hasattr(tl_types, "MessageEntityCustomEmoji"):
                self.entities.append(tl_types.MessageEntityCustomEmoji(start_off, length, int(eid)))


def render_html_entities(html_text: str) -> tuple:
    if not html_text:
        return "", []
    parser = _TelethonHTMLParser()
    parser.feed(html_text)
    parser.close()
    plain = "".join(parser.text_parts)
    return plain, parser.entities


def strip_custom_emoji_entities(entities: list) -> list:
    custom_cls = getattr(tl_types, "MessageEntityCustomEmoji", None)
    if not custom_cls:
        return list(entities or [])
    return [e for e in (entities or []) if not isinstance(e, custom_cls)]


def _is_custom_emoji_error(exc: Exception) -> bool:
    name = type(exc).__name__.upper()
    msg = str(exc).upper()
    return any(tok in name or tok in msg for tok in ("DOCUMENT_INVALID", "DOCUMENTINVALID", "CUSTOM_EMOJI", "ENTITY"))


async def safe_answer(event, text: str = None, alert: bool = False):
    try:
        if text is not None:
            await event.answer(text, alert=alert)
        else:
            await event.answer()
    except Exception:
        pass


async def safe_send(peer, html_text: str, buttons=None, file=None):
    plain, entities = render_html_entities(html_text)
    try:
        if file is not None:
            return await client.send_file(peer, file, caption=plain, formatting_entities=entities, buttons=buttons)
        return await client.send_message(peer, plain, formatting_entities=entities, buttons=buttons)
    except Exception as e:
        if _is_custom_emoji_error(e):
            clean_ent = strip_custom_emoji_entities(entities)
            if file is not None:
                return await client.send_file(peer, file, caption=plain, formatting_entities=clean_ent, buttons=buttons)
            return await client.send_message(peer, plain, formatting_entities=clean_ent, buttons=buttons)
        raise


async def safe_reply(event, html_text: str, buttons=None, file=None):
    plain, entities = render_html_entities(html_text)
    try:
        if file is not None:
            return await event.reply(plain, file=file, formatting_entities=entities, buttons=buttons)
        return await event.reply(plain, formatting_entities=entities, buttons=buttons)
    except Exception as e:
        if _is_custom_emoji_error(e):
            clean_ent = strip_custom_emoji_entities(entities)
            if file is not None:
                return await event.reply(plain, file=file, formatting_entities=clean_ent, buttons=buttons)
            return await event.reply(plain, formatting_entities=clean_ent, buttons=buttons)
        raise


async def safe_respond(event, html_text: str, buttons=None):
    plain, entities = render_html_entities(html_text)
    try:
        return await event.respond(plain, formatting_entities=entities, buttons=buttons)
    except Exception as e:
        if _is_custom_emoji_error(e):
            clean_ent = strip_custom_emoji_entities(entities)
            return await event.respond(plain, formatting_entities=clean_ent, buttons=buttons)
        raise


async def safe_edit(event, html_text: str, buttons=None):
    plain, entities = render_html_entities(html_text)
    try:
        return await event.edit(plain, formatting_entities=entities, buttons=buttons)
    except errors.MessageNotModifiedError:
        return None
    except Exception as e:
        if _is_custom_emoji_error(e):
            try:
                clean_ent = strip_custom_emoji_entities(entities)
                return await event.edit(plain, formatting_entities=clean_ent, buttons=buttons)
            except errors.MessageNotModifiedError:
                return None
            except Exception:
                return await safe_reply(event, html_text, buttons=buttons)
        try:
            return await safe_reply(event, html_text, buttons=buttons)
        except Exception:
            return None


class DebounceManager:
    """منع الضغط المتكرر على الأزرار الحساسة وتكرار الطلبات."""

    def __init__(self):
        self._locks = {}

    def allow(self, uid: int, action: str, cooldown: float = 1.8) -> bool:
        key = (int(uid), str(action))
        now = time.monotonic()
        last = self._locks.get(key, 0.0)
        if now - last < cooldown:
            return False
        self._locks[key] = now
        return True


debounce = DebounceManager()


class UITheme:
    """نظام الهوية البصرية الفاخرة والموحدة للبوت."""

    DIVIDER = "━━━━━━━━━━━━━━━━━━━━"

    @staticmethod
    def header(title: str, icon_key: str = "store_logo", category: str = None) -> str:
        ic = ce(icon_key, category=category)
        return f"<blockquote>{ic}<b>{title}</b></blockquote>"

    @staticmethod
    def success(title: str, body: str) -> str:
        ic = ce("success", category="success")
        return f"<blockquote>{ic}<b>[نجاح] {title}</b>\n{UITheme.DIVIDER}\n{body}</blockquote>"

    @staticmethod
    def error(title: str, body: str) -> str:
        ic = ce("error", category="failure")
        return f"<blockquote>{ic}<b>[تنبيه] {title}</b>\n{UITheme.DIVIDER}\n{body}</blockquote>"

    @staticmethod
    def warning(title: str, body: str) -> str:
        ic = ce("warning", category="warning")
        return f"<blockquote>{ic}<b>[تحذير] {title}</b>\n{UITheme.DIVIDER}\n{body}</blockquote>"

    @staticmethod
    def pending(title: str, body: str) -> str:
        ic = ce("pending", category="pending")
        return f"<blockquote>{ic}<b>[قيد المعالجة] {title}</b>\n{UITheme.DIVIDER}\n{body}</blockquote>"


LANGS = {
    'ar': {
        'welcome_sub': "البوابة الرقمية الفاخرة لخدمات الاتصال والإنترنت العالمي Aura eSIM Elite.",
        'choose_lang': "<blockquote><b>يرجى اختيار لغتك المفضلة للمتابعة:</b></blockquote>",
        'lang_changed': "تم تحويل اللغة بنجاح إلى العربية.",
        'btn_personal': "قسم الأفراد | الباقات الشخصية",
        'btn_dealer': "قسم التجار | خصم 50%",
        'btn_dealer_api': "تفعيل نظام الـ API للتجار ($100)",
        'btn_vodafone': "باقات Vodafone (اتصال + إنترنت)",
        'btn_holafly': "باقات Holafly (إنترنت لا محدود)",
        'btn_maya': "باقات Maya (استخدام عادل 5GB/يوم)",
        'btn_dealer_vf': "باقات Vodafone تجار (10 شرائح)",
        'btn_dealer_hf': "باقات Holafly تجار (10 شرائح)",
        'btn_dealer_maya': "باقات Maya تجار (10 شرائح)",
        'btn_countries': "الدول المدعومة والتغطية",
        'btn_search_plans': "بحث عن باقة",
        'btn_cart': "سلة المشتريات",
        'btn_wallet': "محفظتي الشخصية",
        'btn_transactions': "سجل المعاملات",
        'btn_orders': "طلباتي المكتملة",
        'btn_vip': "حالة VIP والعضوية",
        'btn_support': "الدعم الفني",
        'btn_verify_payment': "التحقق من الدفع",
        'btn_admin': "لوحة التحكم الإدارية",
        'btn_lang': "الإعدادات واللغة / Language",
        'back': "رجوع",
        'home': "الرئيسية",
        'admin_panel_title': "لوحة التحكم الإدارية — Aura eSIM Elite",
        'stats_sales': "إجمالي الطلبات المكتملة",
        'stats_wallets': "إجمالي أرصدة المحافظ",
        'stats_esims': "إجمالي المخزون المتاح",
        'error_msg': "عذراً، حدث خطأ غير متوقع. يرجى المحاولة مرة أخرى.",
        'insufficient_balance': "رصيدك غير كافي لإتمام هذه العملية. يرجى شحن محفظتك أولاً.",
        'success_buy': "تمت عملية الشراء بنجاح. إليك تفاصيل التفعيل الفوري:",
        'buy_now': "شراء الآن",
        'add_to_cart': "إضافة إلى السلة",
        'confirm_buy': "تأكيد الشراء النهائي",
        'pay_wallet': "الدفع الفوري من المحفظة",
        'pay_binance': "الدفع عبر الشبكات والمنصات",
        'type_global': "باقة عالمية (تغطية شاملة)",
        'type_country': "تحديد دولة معينة",
        'select_type': "حدد نطاق التغطية المناسب لباقتك:",
        'select_country_prompt': "اختر الدولة المستهدفة أو ابحث عنها بالاسم:",
        'search_country_btn': "بحث عن دولة",
        'search_prompt': "أرسل اسم الدولة التي تبحث عنها (بالعربية أو الإنجليزية):",
        'wallet_title': "محفظتك الرقمية",
        'current_balance': "الرصيد المتاح حالياً",
        'charge_wallet_btn': "شحن المحفظة",
        'charge_prompt': "<blockquote><b>شحن المحفظة</b>\n━━━━━━━━━━━━━━━━━━━━\nأرسل الآن المبلغ المراد إيداعه بالدولار (الحد الأدنى <code>$20</code>):</blockquote>",
        'min_charge_err': "عذراً، الحد الأدنى لعملية الشحن هو $20.",
        'invalid_number_err': "يرجى إدخال رقم صحيح وموجب حصرياً.",
        'my_orders_title': "سجل طلباتك المكتملة",
        'no_orders': "ليس لديك أي طلبات شراء مكتملة حتى الآن.",
        'dealer_title': "قسم التجار والموزعين (عروض الجملة ونظام الـ API)",
        'verify_prompt': "<blockquote><b>نظام التحقق من المدفوعات</b>\n━━━━━━━━━━━━━━━━━━━━\nأرسل الآن معرف المعاملة (TxID) أو صورة الإيصال:</blockquote>",
        'verify_sent': "تم استلام إيصالك بنجاح، وجاري مراجعته وتفعيل الرصيد فور التحقق.",
        'support_prompt': "<blockquote><b>نظام تذاكر الدعم الفني المباشر</b>\n━━━━━━━━━━━━━━━━━━━━\nاكتب رسالتك أو استفسارك وسيتم تحويله لفريق المختصين فوراً:</blockquote>",
        'support_sent': "تم إرسال تذكرتك بنجاح وسيتم الرد عليك في أقرب وقت ممكن.",
        'network_not_found': "عذراً، طريقة الدفع المختارة غير متوفرة حالياً.",
        'show_all_payments_title': "<blockquote><b>بوابة الدفع الشاملة — Aura eSIM</b>\nالمبلغ المطلوب تحويله: <code>$$amount</code></blockquote>",
        'show_all_payments_footer': "<blockquote>قم بالتحويل عبر إحدى الطرق أعلاه، ثم اضغط على زر التحقق لإرسال الإيصال.</blockquote>",
        'btn_verify_now': "التحقق من الدفع وإرسال الإيصال",
        'countries_header': "الدول المدعومة في شبكة Aura eSIM (COUNTRIES_COUNT دولة):",
        'prev_page': "السابق",
        'next_page': "التالي"
    },
    'en': {
        'welcome_sub': "Luxury Global Connectivity & Digital eSIM Gateway — Aura eSIM Elite.",
        'choose_lang': "<blockquote><b>Please select your preferred language:</b></blockquote>",
        'lang_changed': "Language successfully changed to English.",
        'btn_personal': "Personal Plans",
        'btn_dealer': "Wholesale & Dealers (50% OFF)",
        'btn_dealer_api': "Activate Dealer API ($100)",
        'btn_vodafone': "Vodafone Plans (Voice + Data)",
        'btn_holafly': "Holafly Plans (Unlimited Data)",
        'btn_maya': "Maya Plans (5GB/Day FUP)",
        'btn_dealer_vf': "Vodafone Dealer (10 eSIMs)",
        'btn_dealer_hf': "Holafly Dealer (10 eSIMs)",
        'btn_dealer_maya': "Maya Dealer (10 eSIMs)",
        'btn_countries': "Supported Countries",
        'btn_search_plans': "Search Plans",
        'btn_cart': "Shopping Cart",
        'btn_wallet': "My Wallet",
        'btn_transactions': "Transactions",
        'btn_orders': "My Orders",
        'btn_vip': "VIP & Membership",
        'btn_support': "Support",
        'btn_verify_payment': "Verify Payment",
        'btn_admin': "Admin Panel",
        'btn_lang': "Settings & Language",
        'back': "Back",
        'home': "Home",
        'admin_panel_title': "Admin Control Panel — Aura eSIM Elite",
        'stats_sales': "Completed Orders",
        'stats_wallets': "Total Wallets Balance",
        'stats_esims': "Total Stock",
        'error_msg': "An unexpected error occurred. Please try again.",
        'insufficient_balance': "Insufficient balance. Please charge your wallet first.",
        'success_buy': "Purchase completed successfully. Activation details:",
        'buy_now': "Buy Now",
        'add_to_cart': "Add to Cart",
        'confirm_buy': "Confirm Order",
        'pay_wallet': "Pay from Wallet",
        'pay_binance': "Pay via Payment Networks",
        'type_global': "Global Plan (All Countries)",
        'type_country': "Specific Country",
        'select_type': "Choose coverage type for your plan:",
        'select_country_prompt': "Select the desired country or search:",
        'search_country_btn': "Search Country",
        'search_prompt': "Send the country name to search (Arabic or English):",
        'wallet_title': "Personal Digital Wallet",
        'current_balance': "Current Balance",
        'charge_wallet_btn': "Charge Wallet",
        'charge_prompt': "<blockquote><b>Charge Wallet</b>\n━━━━━━━━━━━━━━━━━━━━\nSend the deposit amount in USD (Minimum <code>$20</code>):</blockquote>",
        'min_charge_err': "Minimum deposit amount is $20.",
        'invalid_number_err': "Please send a valid positive number.",
        'my_orders_title': "Completed Orders History",
        'no_orders': "You have no completed orders yet.",
        'dealer_title': "Dealers & API Section (Wholesale & 50% OFF)",
        'verify_prompt': "<blockquote><b>Payment Verification</b>\n━━━━━━━━━━━━━━━━━━━━\nSend your transaction ID (TxID) or receipt image:</blockquote>",
        'verify_sent': "Your receipt has been received and is under review.",
        'support_prompt': "<blockquote><b>Direct Support Ticket</b>\n━━━━━━━━━━━━━━━━━━━━\nSend your message or inquiry now:</blockquote>",
        'support_sent': "Your support ticket has been sent. We will reply shortly.",
        'network_not_found': "Selected payment method is unavailable.",
        'show_all_payments_title': "<blockquote><b>Payment Gateway — Aura eSIM</b>\nAmount due: <code>$$amount</code></blockquote>",
        'show_all_payments_footer': "<blockquote>Transfer using any method above, then click Verify to submit your receipt.</blockquote>",
        'btn_verify_now': "Verify Payment & Send Receipt",
        'countries_header': "Supported Countries (COUNTRIES_COUNT countries):",
        'prev_page': "Previous",
        'next_page': "Next"
    }
}

WARRANTY_POLICY_TEXT = {
    'ar': """<blockquote><b>سياسات ومميزات الشرائح حسب المزود:</b>
• <b>Holafly:</b> إنترنت لا محدود بالكامل بدون سياسة استخدام عادل.
• <b>Maya:</b> تخضع لسياسة الاستخدام العادل (5 جيجا يومياً بسرعة 5G ثم سرعة مخفضة).
• <b>Vodafone:</b> إنترنت فائق السرعة مع دقائق اتصال محلية ودولية رسمية.
• <b>ملاحظة:</b> باقات Maya وHolafly للإنترنت فقط بدون رقم اتصال.</blockquote>

<blockquote><b>الضمان الذهبي (3 أشهر):</b>
• دعم فني متخصص على مدار الساعة.
• تعويض فوري وآمن بتمديد الفترة أو شريحة بديلة.
• مرونة الاحتفاظ بالشريحة وتفعيلها خلال 3 أشهر.</blockquote>""",
    'en': """<blockquote><b>eSIM Policies & Features:</b>
• <b>Holafly:</b> True unlimited data with zero Fair Usage Policy (FUP).
• <b>Maya:</b> 5 GB/day at full 5G speed, then unlimited data at reduced speed.
• <b>Vodafone:</b> High-speed data + official local & international calling minutes.
• <b>Note:</b> Maya and Holafly are data-only plans.</blockquote>

<blockquote><b>Golden Warranty (3 Months):</b>
• 24/7 dedicated technical support.
• Instant replacement or extension policy.
• Activate anytime within 3 months of purchase.</blockquote>"""
}

client = TelegramClient('esim_market', API_ID, API_HASH)

conn = sqlite3.connect('esim_market.db', check_same_thread=False)
conn.execute("PRAGMA journal_mode=WAL;")
conn.execute("PRAGMA synchronous=NORMAL;")
cur = conn.cursor()

# جدول الأقسام مع ميزة الإخفاء والإظهار
cur.execute('''CREATE TABLE IF NOT EXISTS categories (
    slug TEXT PRIMARY KEY,
    name_ar TEXT,
    name_en TEXT,
    is_visible INTEGER DEFAULT 1
)''')

cur.execute('''CREATE TABLE IF NOT EXISTS esims (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT,
    name TEXT,
    code_key TEXT UNIQUE,
    price_usd REAL,
    minutes INTEGER,
    months INTEGER,
    stock INTEGER DEFAULT 5000,
    min_qty INTEGER DEFAULT 1,
    is_dealer INTEGER DEFAULT 0,
    description TEXT
)''')

cur.execute('''CREATE TABLE IF NOT EXISTS wallets (
    user_id INTEGER PRIMARY KEY,
    balance REAL DEFAULT 0,
    total_deposited REAL DEFAULT 0,
    created_date TEXT
)''')

cur.execute('''CREATE TABLE IF NOT EXISTS wallet_transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    type TEXT,
    amount REAL,
    balance_after REAL,
    description TEXT,
    date TEXT
)''')

cur.execute('''CREATE TABLE IF NOT EXISTS orders (
    order_id TEXT PRIMARY KEY,
    user_id INTEGER,
    esim_id INTEGER,
    quantity INTEGER,
    price_usd REAL,
    total_usd REAL,
    invoice_id TEXT,
    status TEXT,
    is_dealer INTEGER DEFAULT 0,
    is_wallet INTEGER DEFAULT 0,
    created_date TEXT,
    paid_date TEXT
)''')

cur.execute("CREATE INDEX IF NOT EXISTS idx_orders_user ON orders(user_id);")
cur.execute("CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);")

cur.execute('''CREATE TABLE IF NOT EXISTS cart (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    esim_id INTEGER,
    scope TEXT,
    price REAL
)''')

cur.execute('''CREATE TABLE IF NOT EXISTS users_settings (
    user_id INTEGER PRIMARY KEY,
    lang TEXT DEFAULT 'ar',
    referred_by INTEGER,
    is_dealer_tier INTEGER DEFAULT 0
)''')

cur.execute('''CREATE TABLE IF NOT EXISTS dealer_api_keys (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER UNIQUE,
    api_key TEXT UNIQUE,
    created_date TEXT
)''')

cur.execute('''CREATE TABLE IF NOT EXISTS admins (
    user_id INTEGER PRIMARY KEY
)''')

cur.execute('''CREATE TABLE IF NOT EXISTS bans (
    user_id INTEGER PRIMARY KEY
)''')

cur.execute('''CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
)''')

cur.execute('''CREATE TABLE IF NOT EXISTS binance_networks (
    network_key TEXT PRIMARY KEY,
    network_name TEXT,
    address TEXT,
    binance_id TEXT
)''')

cur.execute('''CREATE TABLE IF NOT EXISTS user_sessions (
    user_id INTEGER PRIMARY KEY,
    state_key TEXT,
    state_data TEXT,
    expires_at TEXT
)''')

conn.commit()

# إدراج الأقسام الافتراضية
DEFAULT_CATEGORIES = [
    ('vodafone', 'باقات Vodafone (اتصال + إنترنت)', 'Vodafone Plans', 1),
    ('holafly', 'باقات Holafly (إنترنت لا محدود)', 'Holafly Plans', 1),
    ('maya', 'باقات Maya (سياسة استخدام عادل)', 'Maya Plans', 1),
    ('dealer_vf', 'باقات Vodafone تجار (10 شرائح)', 'Vodafone Dealer Plans', 1),
    ('dealer_hf', 'باقات Holafly تجار (10 شرائح)', 'Holafly Dealer Plans', 1),
    ('dealer_maya', 'باقات Maya تجار (10 شرائح)', 'Maya Dealer Plans', 1),
]
for slug, nar, nen, vis in DEFAULT_CATEGORIES:
    cur.execute("INSERT OR IGNORE INTO categories (slug, name_ar, name_en, is_visible) VALUES (?, ?, ?, ?)", (slug, nar, nen, vis))
conn.commit()

DEFAULT_NETWORKS = [
    ('binance_id', 'Binance ID / Pay ID', '', ''),
    ('bybit_id', 'Bybit ID', '', '159349409'),
    ('usdt_bep20', 'USDT (BEP20 / BSC)', '0x334c55fe51757ac79a3d290523298bd5d327df64', ''),
    ('usdt_aptos', 'USDT (APTOS)', '0xb53e2bab33e422673b7b1d6c1e18731628d1cf965965355973d9d2bef5465230', ''),
    ('usdt_trc20', 'USDT (TRC20)', 'TM5SqP85qKa9pait6DkqCPDcr3hDNJmDGd', ''),
    ('usdt_erc20', 'USDT (ERC20)', '0x334c55fe51757ac79a3d290523298bd5d327df64', ''),
    ('usdc_aptos', 'USDC (APTOS)', '', ''),
    ('usdc_polygon', 'USDC (Polygon)', '', ''),
    ('ton', 'TON & GRAM', '', ''),
    ('ltc', 'Litecoin (LTC)', 'LRbz7QkKmQ9ASjkAuJSD5eYbziApzidZ9b', '')
]

for n_key, n_name, n_addr, n_id in DEFAULT_NETWORKS:
    cur.execute("INSERT OR IGNORE INTO binance_networks (network_key, network_name, address, binance_id) VALUES (?, ?, ?, ?)", (n_key, n_name, n_addr, n_id))
conn.commit()

cur.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (DEV_ID,))
conn.commit()
emoji_mgr.sync_from_db(conn)

DEFAULT_PLANS = [
    ('vodafone', 'Vodafone Unlimited 1 Month', 'vf_1m', 20.0, 850, 1, 765, 1, 0, 'بيانات لا محدودة + 850 دقيقة اتصال'),
    ('vodafone', 'Vodafone Unlimited 3 Months', 'vf_3m', 35.0, 1600, 3, 765, 1, 0, 'بيانات لا محدودة + 1600 دقيقة اتصال'),
    ('vodafone', 'Vodafone Unlimited 6 Months', 'vf_6m', 60.0, 2300, 6, 454, 1, 0, 'بيانات لا محدودة + 2300 دقيقة اتصال'),
    ('vodafone', 'Vodafone Unlimited 12 Months', 'vf_12m', 80.0, 3700, 12, 864, 1, 0, 'بيانات لا محدودة + 3700 دقيقة اتصال'),
    
    ('holafly', 'Holafly Unlimited 1 Month', 'hf_1m', 15.0, 0, 1, 778, 1, 0, 'هولافلاي إنترنت لا محدود بالكامل - بدون استخدام عادل'),
    ('holafly', 'Holafly Unlimited 3 Months', 'hf_3m', 30.0, 0, 3, 876, 1, 0, 'هولافلاي إنترنت لا محدود بالكامل - بدون استخدام عادل'),
    ('holafly', 'Holafly Unlimited 6 Months', 'hf_6m', 50.0, 0, 6, 446, 1, 0, 'هولافلاي إنترنت لا محدود بالكامل - بدون استخدام عادل'),
    ('holafly', 'Holafly Unlimited 12 Months', 'hf_12m', 70.0, 0, 12, 654, 1, 0, 'هولافلاي إنترنت لا محدود بالكامل - بدون استخدام عادل'),

    ('maya', 'Maya Unlimited 1 Month', 'maya_1m', 12.0, 0, 1, 455, 1, 0, 'مايا بيانات لا محدودة - تخضع للاستخدام العادل 5 جيجا يومياً'),
    ('maya', 'Maya Unlimited 3 Months', 'maya_3m', 25.0, 0, 3, 754, 1, 0, 'مايا بيانات لا محدودة - تخضع للاستخدام العادل 5 جيجا يومياً'),

    ('dealer_hf', 'Holafly 10 شرائح - 1 شهر', 'dealer_hf_1m', 100.0, 0, 1, 234, 10, 1, 'عرض 10 شرائح هولافلاي لمدة 1 شهر'),
    ('dealer_hf', 'Holafly 10 شرائح - 3 أشهر', 'dealer_hf_3m', 130.0, 0, 3, 365, 10, 1, 'عرض 10 شرائح هولافلاي لمدة 3 أشهر'),
    ('dealer_hf', 'Holafly 10 شرائح - 6 أشهر', 'dealer_hf_6m', 150.0, 0, 6, 975, 10, 1, 'عرض 10 شرائح هولافلاي لمدة 6 أشهر'),
    ('dealer_hf', 'Holafly 10 شرائح - 12 شهر', 'dealer_hf_12m', 180.0, 0, 12, 356, 10, 1, 'عرض 10 شرائح هولافلاي لمدة 12 شهر'),
    
    ('dealer_vf', 'Vodafone 10 شرائح - 1 شهر', 'dealer_vf_1m', 120.0, 850, 1, 344, 10, 1, 'عرض 10 شرائح فودافون لمدة 1 شهر (850 دقيقة لكل شريحة)'),
    ('dealer_vf', 'Vodafone 10 شرائح - 3 أشهر', 'dealer_vf_3m', 150.0, 1600, 3, 324, 10, 1, 'عرض 10 شرائح فودافون لمدة 3 أشهر (1600 دقيقة لكل شريحة)'),
    ('dealer_vf', 'Vodafone 10 شرائح - 6 أشهر', 'dealer_vf_6m', 170.0, 2300, 6, 645, 10, 1, 'عرض 10 شرائح فودافون لمدة 6 أشهر (2300 دقيقة لكل شريحة)'),
    ('dealer_vf', 'Vodafone 10 شرائح - 12 شهر', 'dealer_vf_12m', 220.0, 3700, 12, 345, 10, 1, 'عرض 10 شرائح فودافون لمدة 12 شهر (3700 دقيقة لكل شريحة)'),

    ('dealer_maya', 'Maya 10 شرائح - 1 شهر', 'dealer_maya_1m', 90.0, 0, 1, 354, 10, 1, 'عرض 10 شرائح مايا لمدة 1 شهر'),
    ('dealer_maya', 'Maya 10 شرائح - 3 أشهر', 'dealer_maya_3m', 120.0, 0, 3, 345, 10, 1, 'عرض 10 شرائح مايا لمدة 3 أشهر'),
]

for cat, name, code, price, mins, months, stock, min_q, is_dlr, desc in DEFAULT_PLANS:
    cur.execute('''INSERT INTO esims 
        (category, name, code_key, price_usd, minutes, months, stock, min_qty, is_dealer, description)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(code_key) DO UPDATE SET 
        minutes=excluded.minutes, description=excluded.description, price_usd=excluded.price_usd''', 
        (cat, name, code, price, mins, months, stock, min_q, is_dlr, desc))
conn.commit()

class SessionManager:
    @staticmethod
    def set(uid, key, data=None):
        expires = (datetime.now() + timedelta(hours=2)).strftime("%Y-%m-%d %H:%M")
        data_str = json.dumps(data) if data else ""
        c_db = sqlite3.connect('esim_market.db', check_same_thread=False)
        c_db.execute("INSERT OR REPLACE INTO user_sessions (user_id, state_key, state_data, expires_at) VALUES (?, ?, ?, ?)", (uid, key, data_str, expires))
        c_db.commit()
        c_db.close()

    @staticmethod
    def get(uid, key):
        c_db = sqlite3.connect('esim_market.db', check_same_thread=False)
        row = c_db.execute("SELECT state_data, expires_at FROM user_sessions WHERE user_id=? AND state_key=?", (uid, key)).fetchone()
        c_db.close()
        if not row: return None
        data_str, exp_str = row
        if datetime.now() > datetime.strptime(exp_str, "%Y-%m-%d %H:%M"):
            SessionManager.remove(uid, key)
            return None
        return json.loads(data_str) if data_str else True

    @staticmethod
    def has(uid, key):
        return SessionManager.get(uid, key) is not None

    @staticmethod
    def pop(uid, key):
        val = SessionManager.get(uid, key)
        SessionManager.remove(uid, key)
        return val

    @staticmethod
    def remove(uid, key):
        c_db = sqlite3.connect('esim_market.db', check_same_thread=False)
        c_db.execute("DELETE FROM user_sessions WHERE user_id=? AND state_key=?", (uid, key))
        c_db.commit()
        c_db.close()

lang_cache = {}
admin_cache = {}
ban_cache = {}
wallet_locks = {}
user_rate_limits = {}

def is_admin(uid):
    if uid == DEV_ID: return True
    if uid in admin_cache: return admin_cache[uid]
    row = cur.execute("SELECT user_id FROM admins WHERE user_id=?", (uid,)).fetchone()
    res = row is not None
    admin_cache[uid] = res
    return res

def is_banned(uid):
    if uid in ban_cache: return ban_cache[uid]
    row = cur.execute("SELECT user_id FROM bans WHERE user_id=?", (uid,)).fetchone()
    res = row is not None
    ban_cache[uid] = res
    return res

def get_user_lang(uid):
    if uid in lang_cache: return lang_cache[uid]
    row = cur.execute("SELECT lang FROM users_settings WHERE user_id=?", (uid,)).fetchone()
    lang = row[0] if row else None
    if lang:
        lang_cache[uid] = lang
    return lang

def set_user_lang(uid, lang):
    cur.execute("INSERT OR REPLACE INTO users_settings (user_id, lang) VALUES (?, ?)", (uid, lang))
    conn.commit()
    lang_cache[uid] = lang

def get_wallet_balance(uid):
    row = cur.execute("SELECT balance FROM wallets WHERE user_id=?", (uid,)).fetchone()
    return row[0] if row else 0

def update_wallet(uid, amount, type, desc):
    cur.execute("INSERT OR IGNORE INTO wallets (user_id, created_date) VALUES (?,?)", (uid, datetime.now().strftime("%Y-%m-%d %H:%M")))
    cur.execute("UPDATE wallets SET balance=balance+? WHERE user_id=?", (amount, uid))
    if amount > 0:
        cur.execute("UPDATE wallets SET total_deposited=total_deposited+? WHERE user_id=?", (amount, uid))
    new_balance = get_wallet_balance(uid)
    cur.execute("INSERT INTO wallet_transactions (user_id,type,amount,balance_after,description,date) VALUES (?,?,?,?,?,?)",
                (uid, type, amount, new_balance, desc, datetime.now().strftime("%Y-%m-%d %H:%M")))
    conn.commit()
    return new_balance

async def check_low_stock_and_alert(esim_id):
    row = cur.execute("SELECT name, stock FROM esims WHERE id=?", (esim_id,)).fetchone()
    if row:
        name, stock = row
        if stock <= 10:
            try:
                alert_msg = UITheme.warning("تنبيه انخفاض مخزون شريحة", f"• الباقة: <b>{name}</b>\n• المتبقي حالياً: <code>{stock} قطع</code>\n\nيرجى إعادة تعبئة المخزون مبكراً.")
                await safe_send(DEV_ID, alert_msg)
            except Exception as e:
                logger.error(f"Low stock alert error: {e}")


COUNTRIES_DATA = [
    {"name": "Afghanistan", "flag": "[AF]", "operators": "AWCC, Etisalat"},
    {"name": "Albania", "flag": "[AL]", "operators": "Vodafone, Telekom"},
    {"name": "Algeria", "flag": "[DZ]", "operators": "Djezzy, Mobilis"},
    {"name": "Andorra", "flag": "[AD]", "operators": "Andorra Telecom, Orange"},
    {"name": "Angola", "flag": "[AO]", "operators": "Unitel, Movicel"},
    {"name": "Antigua and Barbuda", "flag": "[AG]", "operators": "Flow, Digicel"},
    {"name": "Argentina", "flag": "[AR]", "operators": "Claro, Movistar"},
    {"name": "Armenia", "flag": "[AM]", "operators": "VivaCell, Beeline"},
    {"name": "Australia", "flag": "[AU]", "operators": "Telstra, Optus, Vodafone"},
    {"name": "Austria", "flag": "[AT]", "operators": "A1, T-Mobile, Magenta"},
    {"name": "Azerbaijan", "flag": "[AZ]", "operators": "Azercell, Bakcell"},
    {"name": "Bahamas", "flag": "[BS]", "operators": "BTC, Aliv"},
    {"name": "Bahrain", "flag": "[BH]", "operators": "Batelco, Zain, STC"},
    {"name": "Bangladesh", "flag": "[BD]", "operators": "Grameenphone, Robi"},
    {"name": "Barbados", "flag": "[BB]", "operators": "Flow, Digicel"},
    {"name": "Belarus", "flag": "[BY]", "operators": "MTS, A1"},
    {"name": "Belgium", "flag": "[BE]", "operators": "Proximus, Orange, Base"},
    {"name": "Belize", "flag": "[BZ]", "operators": "BTL, Digi"},
    {"name": "Benin", "flag": "[BJ]", "operators": "MTN, Moov"},
    {"name": "Bhutan", "flag": "[BT]", "operators": "B-Mobile, TashiCell"},
    {"name": "Bolivia", "flag": "[BO]", "operators": "Tigo, Entel"},
    {"name": "Bosnia and Herzegovina", "flag": "[BA]", "operators": "BH Telecom, m:tel"},
    {"name": "Botswana", "flag": "[BW]", "operators": "Mascom, Orange"},
    {"name": "Brazil", "flag": "[BR]", "operators": "Vivo, TIM, Claro"},
    {"name": "Brunei", "flag": "[BN]", "operators": "DST, Progresif"},
    {"name": "Bulgaria", "flag": "[BG]", "operators": "A1, Vivacom, Telenor"},
    {"name": "Burkina Faso", "flag": "[BF]", "operators": "Orange, Telmob"},
    {"name": "Burundi", "flag": "[BI]", "operators": "Econet, Lumitel"},
    {"name": "Cambodia", "flag": "[KH]", "operators": "Smart, Cellcard, Metfone"},
    {"name": "Cameroon", "flag": "[CM]", "operators": "MTN, Orange"},
    {"name": "Canada", "flag": "[CA]", "operators": "Rogers, Bell, Telus"},
    {"name": "Cape Verde", "flag": "[CV]", "operators": "CVMovel, Unitel"},
    {"name": "Central African Republic", "flag": "[CF]", "operators": "Orange, Telecel"},
    {"name": "Chad", "flag": "[TD]", "operators": "Airtel, Tigo"},
    {"name": "Chile", "flag": "[CL]", "operators": "Entel, Claro, Movistar"},
    {"name": "China", "flag": "[CN]", "operators": "China Mobile, China Unicom, China Telecom"},
    {"name": "Colombia", "flag": "[CO]", "operators": "Claro, Movistar, Tigo"},
    {"name": "Comoros", "flag": "[KM]", "operators": "Comores Telecom, Telma"},
    {"name": "Congo", "flag": "[CG]", "operators": "MTN, Airtel"},
    {"name": "Costa Rica", "flag": "[CR]", "operators": "Kölbi, Claro, Movistar"},
    {"name": "Croatia", "flag": "[HR]", "operators": "HT, A1, Telemach"},
    {"name": "Cuba", "flag": "[CU]", "operators": "ETECSA"},
    {"name": "Cyprus", "flag": "[CY]", "operators": "Cyta, MTN, Epic"},
    {"name": "Czech Republic", "flag": "[CZ]", "operators": "O2, T-Mobile, Vodafone"},
    {"name": "Denmark", "flag": "[DK]", "operators": "TDC, Telia, Telenor"},
    {"name": "Djibouti", "flag": "[DJ]", "operators": "Djibouti Telecom"},
    {"name": "Dominica", "flag": "[DM]", "operators": "Flow, Digicel"},
    {"name": "Dominican Republic", "flag": "[DO]", "operators": "Claro, Altice, Viva"},
    {"name": "Ecuador", "flag": "[EC]", "operators": "Claro, Movistar, CNT"},
    {"name": "Egypt", "flag": "[EG]", "operators": "Vodafone, Orange, Etisalat, WE"},
    {"name": "El Salvador", "flag": "[SV]", "operators": "Claro, Tigo, Movistar"},
    {"name": "Equatorial Guinea", "flag": "[GQ]", "operators": "Geocom, Orange"},
    {"name": "Eritrea", "flag": "[ER]", "operators": "EriTel"},
    {"name": "Estonia", "flag": "[EE]", "operators": "Telia, Elisa, Tele2"},
    {"name": "Eswatini", "flag": "[SZ]", "operators": "Eswatini Mobile, MTN"},
    {"name": "Ethiopia", "flag": "[ET]", "operators": "Ethio Telecom, Safaricom"},
    {"name": "Fiji", "flag": "[FJ]", "operators": "Vodafone, Digicel"},
    {"name": "Finland", "flag": "[FI]", "operators": "Elisa, Telia, DNA"},
    {"name": "France", "flag": "[FR]", "operators": "Orange, SFR, Free, Bouygues"},
    {"name": "Gabon", "flag": "[GA]", "operators": "Gabon Telecom, Airtel"},
    {"name": "Gambia", "flag": "[GM]", "operators": "Qcell, Africell"},
    {"name": "Georgia", "flag": "[GE]", "operators": "Magti, Cellfie, Beeline"},
    {"name": "Germany", "flag": "[DE]", "operators": "T-Mobile, Vodafone, O2"},
    {"name": "Ghana", "flag": "[GH]", "operators": "MTN, Vodafone, AirtelTigo"},
    {"name": "Greece", "flag": "[GR]", "operators": "Cosmote, Vodafone, Nova"},
    {"name": "Grenada", "flag": "[GD]", "operators": "Flow, Digicel"},
    {"name": "Guatemala", "flag": "[GT]", "operators": "Claro, Tigo"},
    {"name": "Guinea", "flag": "[GN]", "operators": "Orange, MTN, Cellcom"},
    {"name": "Guinea-Bissau", "flag": "[GW]", "operators": "MTN, Orange"},
    {"name": "Guyana", "flag": "[GY]", "operators": "GTT, Digicel"},
    {"name": "Haiti", "flag": "[HT]", "operators": "Natcom, Digicel"},
    {"name": "Honduras", "flag": "[HN]", "operators": "Tigo, Claro"},
    {"name": "Hong Kong", "flag": "[HK]", "operators": "CSL, 3, SmarTone"},
    {"name": "Hungary", "flag": "[HU]", "operators": "Magyar Telekom, Telenor, Vodafone"},
    {"name": "Iceland", "flag": "[IS]", "operators": "Síminn, Vodafone, Nova"},
    {"name": "India", "flag": "[IN]", "operators": "Jio, Airtel, Vi"},
    {"name": "Indonesia", "flag": "[ID]", "operators": "Telkomsel, Indosat, XL Axiata"},
    {"name": "Iran", "flag": "[IR]", "operators": "MCI, Irancell, Rightel"},
    {"name": "Iraq", "flag": "[IQ]", "operators": "Zain, Asiacell, Korek"},
    {"name": "Ireland", "flag": "[IE]", "operators": "Vodafone, Three, Eir"},
    {"name": "Israel", "flag": "[IL]", "operators": "Cellcom, Pelephone, Partner"},
    {"name": "Italy", "flag": "[IT]", "operators": "TIM, Vodafone, WindTre, Iliad"},
    {"name": "Jamaica", "flag": "[JM]", "operators": "Digicel, Flow"},
    {"name": "Japan", "flag": "[JP]", "operators": "NTT Docomo, KDDI, SoftBank, Rakuten"},
    {"name": "Jordan", "flag": "[JO]", "operators": "Orange, Zain, Umniah"},
    {"name": "Kazakhstan", "flag": "[KZ]", "operators": "Kcell, Beeline, Tele2"},
    {"name": "Kenya", "flag": "[KE]", "operators": "Safaricom, Airtel, Telkom"},
    {"name": "Kiribati", "flag": "[KI]", "operators": "Telecom Kiribati"},
    {"name": "Kuwait", "flag": "[KW]", "operators": "Zain, Ooredoo, STC"},
    {"name": "Kyrgyzstan", "flag": "[KG]", "operators": "Beeline, MegaCom, O!"},
    {"name": "Laos", "flag": "[LA]", "operators": "Lao Telecom, Unitel, ETL"},
    {"name": "Latvia", "flag": "[LV]", "operators": "LMT, Tele2, Bite"},
    {"name": "Lebanon", "flag": "[LB]", "operators": "Alfa, Touch"},
    {"name": "Lesotho", "flag": "[LS]", "operators": "Vodacom, Econet"},
    {"name": "Liberia", "flag": "[LR]", "operators": "Orange, MTN"},
    {"name": "Libya", "flag": "[LY]", "operators": "LTT, Almadar, Libyana"},
    {"name": "Liechtenstein", "flag": "[LI]", "operators": "Telecom Liechtenstein, Salt"},
    {"name": "Lithuania", "flag": "[LT]", "operators": "Telia, Tele2, Bite"},
    {"name": "Luxembourg", "flag": "[LU]", "operators": "POST, Orange, Tango"},
    {"name": "Madagascar", "flag": "[MG]", "operators": "Orange, Telma, Airtel"},
    {"name": "Malawi", "flag": "[MW]", "operators": "Airtel, TNM"},
    {"name": "Malaysia", "flag": "[MY]", "operators": "Maxis, Celcom, Digi, U Mobile"},
    {"name": "Maldives", "flag": "[MV]", "operators": "Dhiraagu, Ooredoo"},
    {"name": "Mali", "flag": "[ML]", "operators": "Orange, Malitel"},
    {"name": "Malta", "flag": "[MT]", "operators": "GO, Melita, Epic"},
    {"name": "Marshall Islands", "flag": "[MH]", "operators": "NTA"},
    {"name": "Mauritania", "flag": "[MR]", "operators": "Mauritel, Chinguitel, Mattel"},
    {"name": "Mauritius", "flag": "[MU]", "operators": "My.T, Emtel, Chili"},
    {"name": "Mexico", "flag": "[MX]", "operators": "Telcel, AT&T, Movistar"},
    {"name": "Micronesia", "flag": "[FM]", "operators": "FSM Telecom"},
    {"name": "Moldova", "flag": "[MD]", "operators": "Orange, Moldcell, Unite"},
    {"name": "Monaco", "flag": "[MC]", "operators": "Monaco Telecom"},
    {"name": "Mongolia", "flag": "[MN]", "operators": "Mobicom, Unitel, Skytel"},
    {"name": "Montenegro", "flag": "[ME]", "operators": "Telekom, Telenor, M-tel"},
    {"name": "Morocco", "flag": "[MA]", "operators": "Maroc Telecom, Orange, Inwi"},
    {"name": "Mozambique", "flag": "[MZ]", "operators": "Vodacom, Movitel"},
    {"name": "Myanmar", "flag": "[MM]", "operators": "MPT, Ooredoo, Telenor/Atom, Mytel"},
    {"name": "Namibia", "flag": "[NA]", "operators": "MTC, Telecom Namibia"},
    {"name": "Nauru", "flag": "[NR]", "operators": "Digicel"},
    {"name": "Nepal", "flag": "[NP]", "operators": "Nepal Telecom, Ncell"},
    {"name": "Netherlands", "flag": "[NL]", "operators": "KPN, Vodafone, T-Mobile"},
    {"name": "New Zealand", "flag": "[NZ]", "operators": "Spark, Vodafone, 2degrees"},
    {"name": "Nicaragua", "flag": "[NI]", "operators": "Claro, Tigo"},
    {"name": "Niger", "flag": "[NE]", "operators": "Airtel, Moov"},
    {"name": "Nigeria", "flag": "[NG]", "operators": "MTN, Airtel, Glo, 9mobile"},
    {"name": "North Korea", "flag": "[KP]", "operators": "Koryolink"},
    {"name": "North Macedonia", "flag": "[MK]", "operators": "Telekom, A1"},
    {"name": "Norway", "flag": "[NO]", "operators": "Telenor, Telia, Ice"},
    {"name": "Oman", "flag": "[OM]", "operators": "Omantel, Ooredoo, Vodafone"},
    {"name": "Pakistan", "flag": "[PK]", "operators": "Jazz, Zong, Telenor, Ufone"},
    {"name": "Palau", "flag": "[PW]", "operators": "PNCC"},
    {"name": "Palestine", "flag": "[PS]", "operators": "Jawwal, Ooredoo"},
    {"name": "Panama", "flag": "[PA]", "operators": "Cable & Wireless, Tigo, Claro"},
    {"name": "Papua New Guinea", "flag": "[PG]", "operators": "Digicel, bmobile"},
    {"name": "Paraguay", "flag": "[PY]", "operators": "Tigo, Claro, Personal"},
    {"name": "Peru", "flag": "[PE]", "operators": "Claro, Movistar, Entel, Bitel"},
    {"name": "Philippines", "flag": "[PH]", "operators": "Globe, Smart, Dito"},
    {"name": "Poland", "flag": "[PL]", "operators": "Orange, Play, T-Mobile, Plus"},
    {"name": "Portugal", "flag": "[PT]", "operators": "MEO, NOS, Vodafone"},
    {"name": "Qatar", "flag": "[QA]", "operators": "Ooredoo, Vodafone"},
    {"name": "Romania", "flag": "[RO]", "operators": "Orange, Vodafone, Digi, Telekom"},
    {"name": "Russia", "flag": "[RU]", "operators": "MTS, Beeline, Megafon, Tele2"},
    {"name": "Rwanda", "flag": "[RW]", "operators": "MTN, Airtel"},
    {"name": "Saint Kitts and Nevis", "flag": "[KN]", "operators": "Flow, Digicel"},
    {"name": "Saint Lucia", "flag": "[LC]", "operators": "Flow, Digicel"},
    {"name": "Samoa", "flag": "[WS]", "operators": "Vodafone, Digicel"},
    {"name": "San Marino", "flag": "[SM]", "operators": "TIM, San Marino Telecom"},
    {"name": "Sao Tome and Principe", "flag": "[ST]", "operators": "CSTmóvel"},
    {"name": "Saudi Arabia", "flag": "[SA]", "operators": "STC, Mobily, Zain"},
    {"name": "Senegal", "flag": "[SN]", "operators": "Orange, Free, Expresso"},
    {"name": "Serbia", "flag": "[RS]", "operators": "Telekom Srbija, Yettel, A1"},
    {"name": "Seychelles", "flag": "[SC]", "operators": "Airtel, Cable & Wireless"},
    {"name": "Sierra Leone", "flag": "[SL]", "operators": "Orange, Africell"},
    {"name": "Singapore", "flag": "[SG]", "operators": "Singtel, StarHub, M1, SIMBA"},
    {"name": "Slovakia", "flag": "[SK]", "operators": "Orange, Telekom, O2, 4ka"},
    {"name": "Slovenia", "flag": "[SI]", "operators": "Telekom Slovenije, A1, Telemach"},
    {"name": "Solomon Islands", "flag": "[SB]", "operators": "Our Telekom, Bintang"},
    {"name": "Somalia", "flag": "[SO]", "operators": "Hormuud, Somtel"},
    {"name": "South Africa", "flag": "[ZA]", "operators": "Vodacom, MTN, Cell C, Telkom"},
    {"name": "South Korea", "flag": "[KR]", "operators": "SK Telecom, KT, LG Uplus"},
    {"name": "South Sudan", "flag": "[SS]", "operators": "MTN, Zain"},
    {"name": "Spain", "flag": "[ES]", "operators": "Movistar, Vodafone, Orange, Yoigo"},
    {"name": "Sri Lanka", "flag": "[LK]", "operators": "Dialog, Mobitel, Hutch"},
    {"name": "Sudan", "flag": "[SD]", "operators": "Zain, MTN, Sudani"},
    {"name": "Suriname", "flag": "[SR]", "operators": "Telesur, Digicel"},
    {"name": "Sweden", "flag": "[SE]", "operators": "Telia, Telenor, Tele2, Tre"},
    {"name": "Switzerland", "flag": "[CH]", "operators": "Swisscom, Sunrise, Salt"},
    {"name": "Syria", "flag": "[SY]", "operators": "Syriatel, MTN"},
    {"name": "Taiwan", "flag": "[TW]", "operators": "Chunghwa Telecom, Taiwan Mobile, FarEasTone"},
    {"name": "Tajikistan", "flag": "[TJ]", "operators": "Tcell, Beeline, Megafon"},
    {"name": "Tanzania", "flag": "[TZ]", "operators": "Vodacom, Airtel, Tigo, Halotel"},
    {"name": "Thailand", "flag": "[TH]", "operators": "AIS, True Move H, DTAC"},
    {"name": "Timor-Leste", "flag": "[TL]", "operators": "Telemor, Timor Telecom, Telkomcel"},
    {"name": "Togo", "flag": "[TG]", "operators": "Togocel, Moov"},
    {"name": "Tonga", "flag": "[TO]", "operators": "Digicel, Tones"},
    {"name": "Trinidad and Tobago", "flag": "[TT]", "operators": "TSTT, Digicel"},
    {"name": "Tunisia", "flag": "[TN]", "operators": "Ooredoo, Orange, Tunisie Telecom"},
    {"name": "Turkey", "flag": "[TR]", "operators": "Turkcell, Vodafone, Türk Telekom"},
    {"name": "Turkmenistan", "flag": "[TM]", "operators": "TM Cell"},
    {"name": "Tuvalu", "flag": "[TV]", "operators": "Tuvalu Telecom"},
    {"name": "Uganda", "flag": "[UG]", "operators": "MTN, Airtel"},
    {"name": "Ukraine", "flag": "[UA]", "operators": "Kyivstar, Vodafone, lifecell"},
    {"name": "United Arab Emirates", "flag": "[AE]", "operators": "Etisalat (e&), du, Virgin Mobile"},
    {"name": "United Kingdom", "flag": "[GB]", "operators": "EE, Vodafone, O2, Three"},
    {"name": "United States", "flag": "[US]", "operators": "Verizon, AT&T, T-Mobile"},
    {"name": "Uruguay", "flag": "[UY]", "operators": "Antel, Movistar, Claro"},
    {"name": "Uzbekistan", "flag": "[UZ]", "operators": "Ucell, Beeline, Uzmobile, UMS"},
    {"name": "Vanuatu", "flag": "[VU]", "operators": "Digicel, Vodafone"},
    {"name": "Vatican City", "flag": "[VA]", "operators": "Vatican Telecom"},
    {"name": "Venezuela", "flag": "[VE]", "operators": "Movistar, Digicel, Movilnet"},
    {"name": "Vietnam", "flag": "[VN]", "operators": "Viettel, Vinaphone, Mobifone"},
    {"name": "Yemen", "flag": "[YE]", "operators": "You, Sabafon, Yemen Mobile"},
    {"name": "Zambia", "flag": "[ZM]", "operators": "Airtel, MTN, Zamtel"},
    {"name": "Zimbabwe", "flag": "[ZW]", "operators": "Econet, NetOne, Telecel"}
]

COUNTRY_ALIASES = {
    'أفغانستان': 'Afghanistan', 'afghanistan': 'Afghanistan', 'افغانستان': 'Afghanistan', '阿富汗': 'Afghanistan',
    'ألبانيا': 'Albania', 'albania': 'Albania', 'آلبانی': 'Albania', '阿尔巴尼亚': 'Albania',
    'الجزائر': 'Algeria', 'algeria': 'Algeria', 'الجزایر': 'Algeria', '阿尔及利亚': 'Algeria',
    'أندورا': 'Andorra', 'andorra': 'Andorra', 'آندورا': 'Andorra', '安道尔': 'Andorra',
    'أنغولا': 'Angola', 'angola': 'Angola', 'آنگولا': 'Angola', '安哥拉': 'Angola',
    'أنتيغوا وبربودا': 'Antigua and Barbuda', 'antigua and barbuda': 'Antigua and Barbuda', 'آنتیگوا و باربودا': 'Antigua and Barbuda', '安提瓜和巴布达': 'Antigua and Barbuda',
    'الأرجنتين': 'Argentina', 'argentina': 'Argentina', 'آرژانتین': 'Argentina', '阿根廷': 'Argentina',
    'أرمينيا': 'Armenia', 'armenia': 'Armenia', 'ارمنستان': 'Armenia', '亚美尼亚': 'Armenia',
    'أستراليا': 'Australia', 'australia': 'Australia', 'استرالیا': 'Australia', '澳大利亚': 'Australia',
    'النمسا': 'Austria', 'austria': 'Austria', 'اتریش': 'Austria', '奥地利': 'Austria',
    'أذربيجان': 'Azerbaijan', 'azerbaijan': 'Azerbaijan', 'آذربایجان': 'Azerbaijan', '阿塞拜疆': 'Azerbaijan',
    'الباهاما': 'Bahamas', 'bahamas': 'Bahamas', 'باهاما': 'Bahamas', '巴哈马': 'Bahamas',
    'البحرين': 'Bahrain', 'bahrain': 'Bahrain', 'بحرین': 'Bahrain', '巴林': 'Bahrain',
    'بنغلاديش': 'Bangladesh', 'bangladesh': 'Bangladesh', 'بنگلادش': 'Bangladesh', '孟加拉国': 'Bangladesh',
    'بربادوس': 'Barbados', 'barbados': 'Barbados', 'باربادوس': 'Barbados', '巴巴多斯': 'Barbados',
    'بيلاروسيا': 'Belarus', 'belarus': 'Belarus', 'بلاروس': 'Belarus', '白俄罗斯': 'Belarus',
    'بلجيكا': 'Belgium', 'belgium': 'Belgium', 'بلژیک': 'Belgium', '比利时': 'Belgium',
    'بيليز': 'Belize', 'belize': 'Belize', 'بلیز': 'Belize', '伯利兹': 'Belize',
    'بنين': 'Benin', 'benin': 'Benin', 'بنین': 'Benin', '贝宁': 'Benin',
    'بوتان': 'Bhutan', 'bhutan': 'Bhutan', 'بوتان': 'Bhutan', '不丹': 'Bhutan',
    'بوليفيا': 'Bolivia', 'bolivia': 'Bolivia', 'بولیوی': 'Bolivia', '玻利维亚': 'Bolivia',
    'البوسنة والهرسك': 'Bosnia and Herzegovina', 'bosnia and herzegovina': 'Bosnia and Herzegovina', 'بوسنی و هرزگوین': 'Bosnia and Herzegovina', '波斯尼亚和黑塞哥维那': 'Bosnia and Herzegovina',
    'بوتسوانا': 'Botswana', 'botswana': 'Botswana', 'بوتسوانا': 'Botswana', '博茨瓦纳': 'Botswana',
    'البرازيل': 'Brazil', 'brazil': 'Brazil', 'برزیل': 'Brazil', '巴西': 'Brazil',
    'بروناي': 'Brunei', 'brunei': 'Brunei', 'برونئی': 'Brunei', '文莱': 'Brunei',
    'بلغاريا': 'Bulgaria', 'bulgaria': 'Bulgaria', 'بلغارستان': 'Bulgaria', '保加利亚': 'Bulgaria',
    'بوركينا فاسو': 'Burkina Faso', 'burkina faso': 'Burkina Faso', 'بورکینافاسو': 'Burkina Faso', '布基纳法索': 'Burkina Faso',
    'بوروندي': 'Burundi', 'burundi': 'Burundi', 'بوروندی': 'Burundi', '布隆迪': 'Burundi',
    'كمبوديا': 'Cambodia', 'cambodia': 'Cambodia', 'کامبوج': 'Cambodia', '柬埔寨': 'Cambodia',
    'الكاميرون': 'Cameroon', 'cameroon': 'Cameroon', 'کامرون': 'Cameroon', '喀麦隆': 'Cameroon',
    'كندا': 'Canada', 'canada': 'Canada', 'کانادا': 'Canada', '加拿大': 'Canada',
    'الرأس الأخضر': 'Cape Verde', 'cape verde': 'Cape Verde', 'کیپ ورد': 'Cape Verde', '佛得角': 'Cape Verde',
    'جمهورية أفريقيا الوسطى': 'Central African Republic', 'central african republic': 'Central African Republic', 'جمهوری آفریقای مرکزی': 'Central African Republic', '中非共和国': 'Central African Republic',
    'تشاد': 'Chad', 'chad': 'Chad', 'چاد': 'Chad', '乍得': 'Chad',
    'تشيلي': 'Chile', 'chile': 'Chile', 'شیلی': 'Chile', '智利': 'Chile',
    'الصين': 'China', 'china': 'China', 'چین': 'China', '中国': 'China',
    'كولومبيا': 'Colombia', 'colombia': 'Colombia', 'کلمبیا': 'Colombia', '哥伦比亚': 'Colombia',
    'جزر القمر': 'Comoros', 'comoros': 'Comoros', 'قمر': 'Comoros', '科摩罗': 'Comoros',
    'الكونغو': 'Congo', 'congo': 'Congo', 'کنگو': 'Congo', '刚果': 'Congo',
    'كوستاريكا': 'Costa Rica', 'costa rica': 'Costa Rica', 'کاستاریکا': 'Costa Rica', '哥斯达黎加': 'Costa Rica',
    'كرواتيا': 'Croatia', 'croatia': 'Croatia', 'کرواسی': 'Croatia', '克罗地亚': 'Croatia',
    'كوبا': 'Cuba', 'cuba': 'Cuba', 'کوبا': 'Cuba', '古巴': 'Cuba',
    'قبرص': 'Cyprus', 'cyprus': 'Cyprus', 'قبرس': 'Cyprus', '塞浦路斯': 'Cyprus',
    'التشيك': 'Czech Republic', 'czech republic': 'Czech Republic', 'جمهوری چک': 'Czech Republic', '捷克': 'Czech Republic',
    'الدنمارك': 'Denmark', 'denmark': 'Denmark', 'دانمارک': 'Denmark', '丹麦': 'Denmark',
    'جيبوتي': 'Djibouti', 'djibouti': 'Djibouti', 'جیبوتی': 'Djibouti', '吉布提': 'Djibouti',
    'دومينيكا': 'Dominica', 'dominica': 'Dominica', 'دومینیکا': 'Dominica', '多米尼克': 'Dominica',
    'جمهورية الدومينيكان': 'Dominican Republic', 'dominican republic': 'Dominican Republic', 'جمهوری دومینیکن': 'Dominican Republic', '多米尼加共和国': 'Dominican Republic',
    'الإكوادور': 'Ecuador', 'ecuador': 'Ecuador', 'اکوادور': 'Ecuador', '厄瓜多尔': 'Ecuador',
    'مصر': 'Egypt', 'egypt': 'Egypt', 'مصر': 'Egypt', '埃及': 'Egypt',
    'السلفادور': 'El Salvador', 'el salvador': 'El Salvador', 'السالوادور': 'El Salvador', '萨尔瓦多': 'El Salvador',
    'غينيا الاستوائية': 'Equatorial Guinea', 'equatorial guinea': 'Equatorial Guinea', 'گینه استوایی': 'Equatorial Guinea', '赤道几内亚': 'Equatorial Guinea',
    'إريتريا': 'Eritrea', 'eritrea': 'Eritrea', 'اریتره': 'Eritrea', '厄立特里亚': 'Eritrea',
    'إستونيا': 'Estonia', 'estonia': 'Estonia', 'استونی': 'Estonia', '爱沙尼亚': 'Estonia',
    'إسواتيني': 'Eswatini', 'eswatini': 'Eswatini', 'اسواتینی': 'Eswatini', '斯威士兰': 'Eswatini',
    'إثيوبيا': 'Ethiopia', 'ethiopia': 'Ethiopia', 'اتیوپی': 'Ethiopia', '埃塞俄比亚': 'Ethiopia',
    'فيجي': 'Fiji', 'fiji': 'Fiji', 'فیجی': 'Fiji', '斐济': 'Fiji',
    'فنلندا': 'Finland', 'finland': 'Finland', 'فنلاند': 'Finland', '芬兰': 'Finland',
    'فرنسا': 'France', 'france': 'France', 'فرانسه': 'France', '法国': 'France',
    'غابون': 'Gabon', 'gabon': 'Gabon', 'گابن': 'Gabon', '加蓬': 'Gabon',
    'غامبي': 'Gambia', 'gambia': 'Gambia', 'گامبیا': 'Gambia', '冈比亚': 'Gambia',
    'جورجيا': 'Georgia', 'georgia': 'Georgia', 'گرجستان': 'Georgia', '格鲁吉亚': 'Georgia',
    'ألمانيا': 'Germany', 'germany': 'Germany', 'آلمان': 'Germany', '德国': 'Germany',
    'غانا': 'Ghana', 'ghana': 'Ghana', 'غنا': 'Ghana', '加纳': 'Ghana',
    'اليونان': 'Greece', 'greece': 'Greece', 'یونان': 'Greece', '希腊': 'Greece',
    'غرينادا': 'Grenada', 'grenada': 'Grenada', 'گرنادا': 'Grenada', '格林纳达': 'Grenada',
    'غواتيمالا': 'Guatemala', 'guatemala': 'Guatemala', 'گواتمالا': 'Guatemala', '危地马拉': 'Guatemala',
    'غينيا': 'Guinea', 'guinea': 'Guinea', 'گینه': 'Guinea', '几内亚': 'Guinea',
    'غينيا بيساو': 'Guinea-Bissau', 'guinea-bissau': 'Guinea-Bissau', 'گینه بیسائو': 'Guinea-Bissau', '几内亚比绍': 'Guinea-Bissau',
    'غيانا': 'Guyana', 'guyana': 'Guyana', 'گویان': 'Guyana', '圭亚那': 'Guyana',
    'هايتي': 'Haiti', 'haiti': 'Haiti', 'هائیتی': 'Haiti', '海地': 'Haiti',
    'هندوراس': 'Honduras', 'honduras': 'Honduras', 'هندوراس': 'Honduras', '洪都拉斯': 'Honduras',
    'هونغ كونغ': 'Hong Kong', 'hong kong': 'Hong Kong', 'هنگ کنگ': 'Hong Kong', '香港': 'Hong Kong',
    'المجر': 'Hungary', 'hungary': 'Hungary', 'مجارستان': 'Hungary', '匈牙利': 'Hungary',
    'آيسلندا': 'Iceland', 'iceland': 'Iceland', 'ایسلند': 'Iceland', '冰岛': 'Iceland',
    'الهند': 'India', 'india': 'India', 'هند': 'India', '印度': 'India',
    'إندونيسيا': 'Indonesia', 'indonesia': 'Indonesia', 'اندونزی': 'Indonesia', '印度尼西亚': 'Indonesia',
    'إيران': 'Iran', 'iran': 'Iran', 'ایران': 'Iran', '伊朗': 'Iran',
    'العراق': 'Iraq', 'iraq': 'Iraq', 'عراق': 'Iraq', '伊拉克': 'Iraq',
    'أيرلندا': 'Ireland', 'ireland': 'Ireland', 'ایرلند': 'Ireland', '爱尔兰': 'Ireland',
    'إسرائيل': 'Israel', 'israel': 'Israel', 'اسرائیل': 'Israel', '以色列': 'Israel',
    'إيطاليا': 'Italy', 'italy': 'Italy', 'ایتالیا': 'Italy', '意大利': 'Italy',
    'جامايكا': 'Jamaica', 'jamaica': 'Jamaica', 'جامائیکا': 'Jamaica', '牙买加': 'Jamaica',
    'اليابان': 'Japan', 'japan': 'Japan', 'ژاپن': 'Japan', '日本': 'Japan',
    'الأردن': 'Jordan', 'jordan': 'Jordan', 'اردن': 'Jordan', '约旦': 'Jordan',
    'كازاخستان': 'Kazakhstan', 'kazakhstan': 'Kazakhstan', 'قزاقستان': 'Kazakhstan', '哈萨克斯坦': 'Kazakhstan',
    'كينيا': 'Kenya', 'kenya': 'Kenya', 'کنیا': 'Kenya', '肯尼亚': 'Kenya',
    'كيريباتي': 'Kiribati', 'kiribati': 'Kiribati', 'کیریباتی': 'Kiribati', '基里巴斯': 'Kiribati',
    'الكويت': 'Kuwait', 'kuwait': 'Kuwait', 'کویت': 'Kuwait', '科威特': 'Kuwait',
    'قيرغيزستان': 'Kyrgyzstan', 'kyrgyzstan': 'Kyrgyzstan', 'قرقیزستان': 'Kyrgyzstan', '吉尔吉斯斯坦': 'Kyrgyzstan',
    'لاوس': 'Laos', 'laos': 'Laos', 'لائوس': 'Laos', '老挝': 'Laos',
    'لاتفيا': 'Latvia', 'latvia': 'Latvia', 'لتونی': 'Latvia', '拉脱维亚': 'Latvia',
    'لبنان': 'Lebanon', 'lebanon': 'Lebanon', 'لبنان': 'Lebanon', '黎巴嫩': 'Lebanon',
    'ليسوتو': 'Lesotho', 'lesotho': 'Lesotho', 'لسوتو': 'Lesotho', '莱索托': 'Lesotho',
    'ليبيريا': 'Liberia', 'liberia': 'Liberia', 'لیبریا': 'Liberia', '利比里亚': 'Liberia',
    'ليبيا': 'Libya', 'libya': 'Libya', 'لیبی': 'Libya', '利比亚': 'Libya',
    'ليختنشتاين': 'Liechtenstein', 'liechtenstein': 'Liechtenstein', 'لیختن‌اشتاین': 'Liechtenstein', '列支敦士登': 'Liechtenstein',
    'ليتوانيا': 'Lithuania', 'lithuania': 'Lithuania', 'لیتوانی': 'Lithuania', '立陶宛': 'Lithuania',
    'لوكسمبورغ': 'Luxembourg', 'luxembourg': 'Luxembourg', 'لوکزامبورگ': 'Luxembourg', '卢森堡': 'Luxembourg',
    'مدغشقر': 'Madagascar', 'madagascar': 'Madagascar', 'ماداگاسکار': 'Madagascar', '马达加斯加': 'Madagascar',
    'مالاوى': 'Malawi', 'malawi': 'Malawi', 'مالاوی': 'Malawi', '马拉维': 'Malawi',
    'ماليزيا': 'Malaysia', 'malaysia': 'Malaysia', 'مالزی': 'Malaysia', '马来西亚': 'Malaysia',
    'جزر المالديف': 'Maldives', 'maldives': 'Maldives', 'مالدیو': 'Maldives', '马尔代夫': 'Maldives',
    'مالي': 'Mali', 'mali': 'Mali', 'مالی': 'Mali', '马里': 'Malized',
    'مالطا': 'Malta', 'malta': 'Malta', 'مالت': 'Malta', '马耳他': 'Malta',
    'جزر مارشال': 'Marshall Islands', 'marshall islands': 'Marshall Islands', 'جزایر مارشال': 'Marshall Islands', '马绍尔群岛': 'Marshall Islands',
    'موريتانيا': 'Mauritania', 'mauritania': 'Mauritania', 'موریتانی': 'Mauritania', '毛里塔尼亚': 'Mauritania',
    'موريشيوس': 'Mauritius', 'mauritius': 'Mauritius', 'موریس': 'Mauritius', '毛里求斯': 'Mauritius',
    'المكسيك': 'Mexico', 'mexico': 'Mexico', 'مکزیک': 'Mexico', '墨西哥': 'Mexico',
    'ميكرونيزيا': 'Micronesia', 'micronesia': 'Micronesia', 'میکرونزی': 'Micronesia', '密克罗尼西亚': 'Micronesia',
    'مولدوفا': 'Moldova', 'moldova': 'Moldova', 'مولداوی': 'Moldova', '摩尔多瓦': 'Moldova',
    'موناكو': 'Monaco', 'monaco': 'Monaco', 'موناکو': 'Monaco', '摩纳哥': 'Monaco',
    'منغوليا': 'Mongolia', 'mongolia': 'Mongolia', 'مغولستان': 'Mongolia', '蒙古': 'Mongolia',
    'الجبل الأسود': 'Montenegro', 'montenegro': 'Montenegro', 'مونته‌نگرو': 'Montenegro', '黑山': 'Montenegro',
    'المغرب': 'Morocco', 'morocco': 'Morocco', 'مراکش': 'Morocco', '摩洛哥': 'Morocco',
    'موزمبيق': 'Mozambique', 'mozambique': 'Mozambique', 'موزامبیک': 'Mozambique', '莫桑比克': 'Mozambique',
    'ميانمار': 'Myanmar', 'myanmar': 'Myanmar', 'میانمار': 'Myanmar', '缅甸': 'Myanmar',
    'ناميبيا': 'Namibia', 'namibia': 'Namibia', 'نامیبیا': 'Namibia', '纳米比亚': 'Namibia',
    'ناورو': 'Nauru', 'nauru': 'Nauru', 'نائورو': 'Nauru', '瑙鲁': 'Nauru',
    'نيبال': 'Nepal', 'nepal': 'Nepal', 'نپال': 'Nepal', '尼泊尔': 'Nepal',
    'هولندا': 'Netherlands', 'netherlands': 'Netherlands', 'هلند': 'Netherlands', '荷兰': 'Netherlands',
    'نيوزيلندا': 'New Zealand', 'new zealand': 'New Zealand', 'نیوزیلند': 'New Zealand', '新西兰': 'New Zealand',
    'نيكاراغوا': 'Nicaragua', 'nicaragua': 'Nicaragua', 'نیکاراگوئه': 'Nicaragua', '尼加拉瓜': 'Nicaragua',
    'النيجر': 'Niger', 'niger': 'Niger', 'نیجر': 'Niger', '尼日尔': 'Niger',
    'نيجيريا': 'Nigeria', 'nigeria': 'Nigeria', 'نیجریه': 'Nigeria', '尼日利亚': 'Nigeria',
    'كوريا الشمالية': 'North Korea', 'north korea': 'North Korea', 'کره شمالی': 'North Korea', '朝鲜': 'North Korea',
    'مقدونيا الشمالية': 'North Macedonia', 'north macedonia': 'North Macedonia', 'مقدونیه شمالی': 'North Macedonia', '北马其顿': 'North Macedonia',
    'النرويج': 'Norway', 'norway': 'Norway', 'نروژ': 'Norway', '挪威': 'Norway',
    'عمان': 'Oman', 'oman': 'Oman', 'عمان': 'Oman', '阿曼': 'Oman',
    'باكستان': 'Pakistan', 'pakistan': 'Pakistan', 'پاکستان': 'Pakistan', '巴基斯坦': 'Pakistan',
    'بالاو': 'Palau', 'palau': 'Palau', 'پالائو': 'Palau', '帕劳': 'Palau',
    'فلسطين': 'Palestine', 'palestine': 'Palestine', 'فلسطین': 'Palestine', '巴勒斯坦': 'Palestine',
    'بنما': 'Panama', 'panama': 'Panama', 'پاناما': 'Panama', '巴拿马': 'Panama',
    'بابوا غينيا الجديدة': 'Papua New Guinea', 'papua new guinea': 'Papua New Guinea', 'پاپوآ گینه نو': 'Papua New Guinea', '巴布亚新几内亚': 'Papua New Guinea',
    'باراغواي': 'Paraguay', 'paraguay': 'Paraguay', 'پاراگوئه': 'Paraguay', '巴拉圭': 'Paraguay',
    'بيرو': 'Peru', 'peru': 'Peru', 'پرو': 'Peru', '秘鲁': 'Peru',
    'الفلبين': 'Philippines', 'philippines': 'Philippines', 'فیلیپین': 'Philippines', '菲律宾': 'Philippines',
    'بولندا': 'Poland', 'poland': 'Poland', 'لهستان': 'Poland', '波兰': 'Poland',
    'البرتغال': 'Portugal', 'portugal': 'Portugal', 'پرتغال': 'Portugal', '葡萄牙': 'Portugal',
    'قطر': 'Qatar', 'qatar': 'Qatar', 'قطر': 'Qatar', '卡塔尔': 'Qatar',
    'رومانيا': 'Romania', 'romania': 'Romania', 'رومانی': 'Romania', '罗马尼亚': 'Romania',
    'روسيا': 'Russia', 'russia': 'Russia', 'روسیه': 'Russia', '俄罗斯': 'Russia',
    'رواندا': 'Rwanda', 'rwanda': 'Rwanda', 'رواندا': 'Rwanda', '卢旺达': 'Rwanda',
    'سانت كيتس ونيفيس': 'Saint Kitts and Nevis', 'saint kitts and nevis': 'Saint Kitts and Nevis', 'سنت کیتس و نویس': 'Saint Kitts and Nevis', '圣基茨和尼维斯': 'Saint Kitts and Nevis',
    'سانت لوسيا': 'Saint Lucia', 'saint lucia': 'Saint Lucia', 'سنت لوسیا': 'Saint Lucia', '圣卢西亚': 'Saint Lucia',
    'ساموا': 'Samoa', 'samoa': 'Samoa', 'ساموآ': 'Samoa', '萨摩亚': 'Samoa',
    'سان مارينو': 'San Marino', 'san marino': 'San Marino', 'سن مارینو': 'San Marino', '圣马力诺': 'San Marino',
    'ساو تومي وبرينسيب': 'Sao Tome and Principe', 'sao tome and principe': 'Sao Tome and Principe', 'سائوتومه و پرینسیپ': 'Sao Tome and Principe', '圣多美和普林西比': 'Sao Tome and Principe',
    'السعودية': 'Saudi Arabia', 'saudi arabia': 'Saudi Arabia', 'ksa': 'Saudi Arabia', 'عربستان': 'Saudi Arabia', '沙特阿拉伯': 'Saudi Arabia',
    'السنغال': 'Senegal', 'senegal': 'Senegal', 'سنگال': 'Senegal', '塞内加尔': 'Senegal',
    'صربيا': 'Serbia', 'serbia': 'Serbia', 'صربستان': 'Serbia', '塞尔维亚': 'Serbia',
    'سيشل': 'Seychelles', 'seychelles': 'Seychelles', 'سیشل': 'Seychelles', '塞舌尔': 'Seychelles',
    'سيراليون': 'Sierra Leone', 'sierra leone': 'Sierra Leone', 'سیرالئون': 'Sierra Leone', '塞拉利昂': 'Sierra Leone',
    'سنغافورة': 'Singapore', 'singapore': 'Singapore', 'سنگاپور': 'Singapore', '新加坡': 'Singapore',
    'سلوفاكيا': 'Slovakia', 'slovakia': 'Slovakia', 'اسلواکی': 'Slovakia', '斯洛伐克': 'Slovakia',
    'سلوفينيا': 'Slovenia', 'slovenia': 'Slovenia', 'اسلوونی': 'Slovenia', '斯洛文尼亚': 'Slovenia',
    'جزر سليمان': 'Solomon Islands', 'solomon islands': 'Solomon Islands', 'جزایر سلیمان': 'Solomon Islands', '所罗门群岛': 'Solomon Islands',
    'الصومال': 'Somalia', 'somalia': 'Somalia', 'سومالی': 'Somalia', '索马里': 'Somalia',
    'جنوب أفريقيا': 'South Africa', 'south africa': 'South Africa', 'آریقای جنوبی': 'South Africa', '南非': 'South Africa',
    'كوريا الجنوبية': 'South Korea', 'south korea': 'South Korea', 'کره جنوبی': 'South Korea', '韩国': 'South Korea',
    'جنوب السودان': 'South Sudan', 'south sudan': 'South Sudan', 'سودان جنوبی': 'South Sudan', '南苏丹': 'South Sudan',
    'إسبانيا': 'Spain', 'spain': 'Spain', 'اسپانیا': 'Spain', '西班牙': 'Spain',
    'سريلانكا': 'Sri Lanka', 'sri lanka': 'Sri Lanka', 'سریلانکا': 'Sri Lanka', '斯里兰卡': 'Sri Lanka',
    'السودان': 'Sudan', 'sudan': 'Sudan', 'سودان': 'Sudan', '苏丹': 'Sudan',
    'سورينام': 'Suriname', 'suriname': 'Suriname', 'سورینام': 'Suriname', '苏里南': 'Suriname',
    'السويد': 'Sweden', 'sweden': 'Sweden', 'سوئد': 'Sweden', '瑞典': 'Sweden',
    'سويسرا': 'Switzerland', 'switzerland': 'Switzerland', 'سوئیس': 'Switzerland', '瑞士': 'Switzerland',
    'سوريا': 'Syria', 'syria': 'Syria', 'سوریه': 'Syria', '叙利亚': 'Syria',
    'تايوان': 'Taiwan', 'taiwan': 'Taiwan', 'تایوان': 'Taiwan', '台湾': 'Taiwan',
    'طاجيكستان': 'Tajikistan', 'tajikistan': 'Tajikistan', 'تاجیکستان': 'Tajikistan', '塔吉克斯坦': 'Tajikistan',
    'تنزانيا': 'Tanzania', 'tanzania': 'Tanzania', 'تانزانیا': 'Tanzania', '坦桑尼亚': 'Tanzania',
    'تايلاند': 'Thailand', 'thailand': 'Thailand', 'تایلند': 'Thailand', '泰国': 'Thailand',
    'تيمور الشرقية': 'Timor-Leste', 'timor-leste': 'Timor-Leste', 'تیمور شرقی': 'Timor-Leste', '东帝汶': 'Timor-Leste',
    'توغو': 'Togo', 'togo': 'Togo', 'توگو': 'Togo', '多哥': 'Togo',
    'تونغا': 'Tonga', 'tonga': 'Tonga', 'تونگا': 'Tonga', '汤加': 'Tonga',
    'ترينيداد وتوباغو': 'Trinidad and Tobago', 'trinidad and tobago': 'Trinidad and Tobago', 'ترینیداد و توباگو': 'Trinidad and Tobago', '特立尼达和多巴哥': 'Trinidad and Tobago',
    'تونس': 'Tunisia', 'tunisia': 'Tunisia', 'تونس': 'Tunisia', '突尼斯': 'Tunisia',
    'تركيا': 'Turkey', 'turkey': 'Turkey', 'türkiye': 'Turkey', 'ترکیه': 'Turkey', '土耳其': 'Turkey',
    'تركمانستان': 'Turkmenistan', 'turkmenistan': 'Turkmenistan', 'ترکمنستان': 'Turkmenistan', '土库曼斯坦': 'Turkmenistan',
    'توفالو': 'Tuvalu', 'tuvalu': 'Tuvalu', 'تووالو': 'Tuvalu', '图瓦卢': 'Tuvalu',
    'أوغندا': 'Uganda', 'uganda': 'Uganda', 'اوگاندا': 'Uganda', '乌干达': 'Uganda',
    'أوكرانيا': 'Ukraine', 'ukraine': 'Ukraine', 'اوکراین': 'Ukraine', '乌克兰': 'Ukraine',
    'الإمارات': 'United Arab Emirates', 'uae': 'United Arab Emirates', 'dubai': 'United Arab Emirates', 'امارات': 'United Arab Emirates', '阿联酋': 'United Arab Emirates',
    'بريطانيا': 'United Kingdom', 'uk': 'United Kingdom', 'england': 'United Kingdom', 'انگلستان': 'United Kingdom', '英国': 'United Kingdom',
    'أمريكا': 'United States', 'usa': 'United States', 'united states': 'United States', 'آمریکا': 'United States', '美国': 'United States',
    'أوروغواي': 'Uruguay', 'uruguay': 'Uruguay', 'اوروگوئه': 'Uruguay', '乌拉圭': 'Uruguay',
    'أوزبكستان': 'Uzbekistan', 'uzbekistan': 'Uzbekistan', 'ازبکستان': 'Uzbekistan', '乌兹别克斯坦': 'Uzbekistan',
    'فانواتو': 'Vanuatu', 'vanuatu': 'Vanuatu', 'وانواتو': 'Vanuatu', '瓦努阿图': 'Vanuatu',
    'الفاتيكان': 'Vatican City', 'vatican city': 'Vatican City', 'واتیکان': 'Vatican City', '梵蒂冈': 'Vatican City',
    'فنزويلا': 'Venezuela', 'venezuela': 'Venezuela', 'ونزوئلا': 'Venezuela', '委内瑞拉': 'Venezuela',
    'فيتنام': 'Vietnam', 'vietnam': 'Vietnam', 'ویتنام': 'Vietnam', '越南': 'Vietnam',
    'اليمن': 'Yemen', 'yemen': 'Yemen', 'یمن': 'Yemen', '也门': 'Yemen',
    'زامبيا': 'Zambia', 'zambia': 'Zambia', 'زامبیا': 'Zambia', '赞比亚': 'Zambia',
    'زيمبابوي': 'Zimbabwe', 'zimbabwe': 'Zimbabwe', 'زیمبابوه': 'Zimbabwe', '津巴布韦': 'Zimbabwe',
}

def get_user_display_name(user_entity, uid: int) -> str:
    if user_entity and getattr(user_entity, "first_name", None):
        return str(user_entity.first_name)
    return f"عميل #{uid}"


def get_membership_info(uid: int, lang: str = 'ar') -> dict:
    api_row = cur.execute("SELECT api_key, created_date FROM dealer_api_keys WHERE user_id=?", (uid,)).fetchone()
    if is_admin(uid):
        return {
            "tier": "إدارة / مطور" if lang == 'ar' else "Admin / Developer",
            "key": "admin",
            "discount": 50 if api_row else 0,
            "has_api": api_row is not None,
            "api_key": api_row[0] if api_row else "",
            "created": api_row[1] if api_row else "",
        }
    if api_row:
        return {
            "tier": "تاجر API (خصم 50%)" if lang == 'ar' else "API Dealer (50% OFF)",
            "key": "dealer",
            "discount": 50,
            "has_api": True,
            "api_key": api_row[0],
            "created": api_row[1],
        }
    return {
        "tier": "عضو قياسي" if lang == 'ar' else "Standard Member",
        "key": "standard",
        "discount": 0,
        "has_api": False,
        "api_key": "",
        "created": "",
    }


def main_menu(uid: int, first_name: str = ""):
    lang = get_user_lang(uid) or 'ar'
    t = LANGS.get(lang, LANGS['ar'])
    balance = get_wallet_balance(uid)
    orders_cnt = cur.execute("SELECT COUNT(*) FROM orders WHERE user_id=? AND status='paid'", (uid,)).fetchone()[0]
    cart_cnt = cur.execute("SELECT COUNT(*) FROM cart WHERE user_id=?", (uid,)).fetchone()[0]
    mem = get_membership_info(uid, lang)

    greet_name = first_name.strip() if first_name else f"#{uid}"
    if lang == 'ar':
        text = (
            f"{UITheme.header('Aura eSIM Elite — المتجر الرقمي الفاخر', 'store_logo', 'store')}\n\n"
            f"<blockquote>{ce('welcome_spark', 'store')}مرحباً بك، <b>{greet_name}</b>\n"
            f"{t['welcome_sub']}</blockquote>\n\n"
            f"<blockquote>{ce('wallet', 'wallet')}<b>رصيد المحفظة:</b> <code>${balance:.2f}</code>\n"
            f"{ce('vip', 'vip')}<b>حالة العضوية:</b> <b>{mem['tier']}</b>\n"
            f"{ce('orders', 'orders')}<b>الطلبات المكتملة:</b> <code>{orders_cnt}</code> | "
            f"{ce('cart', 'orders')}<b>السلة:</b> <code>{cart_cnt}</code></blockquote>"
        )
    else:
        text = (
            f"{UITheme.header('Aura eSIM Elite — Luxury Gateway', 'store_logo', 'store')}\n\n"
            f"<blockquote>{ce('welcome_spark', 'store')}Welcome, <b>{greet_name}</b>\n"
            f"{t['welcome_sub']}</blockquote>\n\n"
            f"<blockquote>{ce('wallet', 'wallet')}<b>Wallet Balance:</b> <code>${balance:.2f}</code>\n"
            f"{ce('vip', 'vip')}<b>Membership:</b> <b>{mem['tier']}</b>\n"
            f"{ce('orders', 'orders')}<b>Completed Orders:</b> <code>{orders_cnt}</code> | "
            f"{ce('cart', 'orders')}<b>Cart:</b> <code>{cart_cnt}</code></blockquote>"
        )

    btn = [
        [Button.inline(t['btn_personal'], b'personal_section'), Button.inline(t['btn_search_plans'], b'search_plans_prompt')],
        [Button.inline(t['btn_dealer'], b'dealer_section')],
    ]
    if not mem['has_api']:
        btn.append([Button.inline(t['btn_dealer_api'], b'buy_api_sub_menu')])

    btn.extend([
        [Button.inline(f"{t['btn_cart']} ({cart_cnt})", b'view_cart'), Button.inline(f"{t['btn_wallet']} (${balance:.2f})", b'wallet')],
        [Button.inline(f"{t['btn_orders']} ({orders_cnt})", b'my_orders_0'), Button.inline(t['btn_vip'], b'vip_membership')],
        [Button.inline(t['btn_countries'], b'countries_list_0'), Button.inline(t['btn_support'], b'support_ticket')],
        [Button.inline(t['btn_lang'], b'change_language')]
    ])
    if is_admin(uid):
        btn.append([Button.inline(t['btn_admin'], b'admin_panel')])
    return text, btn


@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    uid = event.sender_id
    if is_banned(uid):
        return

    user_entity = None
    try:
        user_entity = await event.sender
        u_name = user_entity.first_name if user_entity else "مستخدم"
        u_uname = f"@{user_entity.username}" if user_entity and user_entity.username else "بدون معرف"
        notif_text = UITheme.header("إشعار دخول مستخدم للبوت", "alert", "warning") + (
            f"\n<blockquote>• <b>الاسم:</b> {u_name}\n"
            f"• <b>المعرف:</b> {u_uname}\n"
            f"• <b>الآيدي:</b> <code>{uid}</code>\n"
            f"• <b>الوقت:</b> {datetime.now().strftime('%Y-%m-%d %H:%M')}</blockquote>"
        )
        await safe_send(DEV_ID, notif_text)
    except Exception as e:
        logger.error(f"User join notification error: {e}")

    args = event.text.split()
    if len(args) > 1 and args[1].startswith('ref'):
        try:
            ref_id = int(args[1].replace('ref', ''))
            if ref_id != uid:
                existing = cur.execute("SELECT referred_by FROM users_settings WHERE user_id=?", (uid,)).fetchone()
                if not existing or not existing[0]:
                    cur.execute("INSERT OR IGNORE INTO users_settings (user_id, referred_by) VALUES (?, ?)", (uid, ref_id))
                    cur.execute("UPDATE users_settings SET referred_by=? WHERE user_id=?", (ref_id, uid))
                    conn.commit()
        except Exception:
            pass

    current_lang = get_user_lang(uid)
    if not current_lang:
        btn = [
            [Button.inline("[AR] العربية", b'set_lang_ar'), Button.inline("[EN] English", b'set_lang_en')]
        ]
        await safe_reply(
            event,
            "<blockquote><b>Welcome to Aura eSIM Elite</b>\n━━━━━━━━━━━━━━━━━━━━\nاختر لغتك المفضلة / Please select your preferred language:</blockquote>",
            buttons=btn
        )
        return

    fname = get_user_display_name(user_entity, uid)
    text, btn = main_menu(uid, fname)
    await safe_reply(event, text, buttons=btn)


@client.on(events.CallbackQuery)
async def callback(event):
    uid = event.sender_id
    if is_banned(uid):
        return
    data = event.data.decode()
    lang = get_user_lang(uid) or 'ar'
    t = LANGS.get(lang, LANGS['ar'])

    if data.startswith('set_lang_'):
        new_l = data.split('_')[2]
        set_user_lang(uid, new_l)
        new_t = LANGS.get(new_l, LANGS['ar'])
        await safe_answer(event, new_t['lang_changed'], alert=True)
        sender = await event.get_sender()
        text, btn = main_menu(uid, get_user_display_name(sender, uid))
        await safe_edit(event, text, buttons=btn)
        return

    if data == 'main':
        await safe_answer(event)
        sender = await event.get_sender()
        text, btn = main_menu(uid, get_user_display_name(sender, uid))
        await safe_edit(event, text, buttons=btn)

    elif data == 'change_language':
        await safe_answer(event)
        btn = [
            [Button.inline("[AR] العربية", b'set_lang_ar'), Button.inline("[EN] English", b'set_lang_en')],
            [Button.inline(t['back'], b'main')]
        ]
        await safe_edit(
            event,
            UITheme.header("إعدادات اللغة / Language Settings", "language", "settings") + "\n\n" + t['choose_lang'],
            buttons=btn
        )

    # ------------------ قسم الأفراد والمتجر ------------------
    elif data == 'personal_section':
        await safe_answer(event)
        cats = cur.execute("SELECT slug, name_ar, name_en FROM categories WHERE slug NOT LIKE 'dealer_%' AND is_visible=1").fetchall()
        btn = []
        for slug, nar, nen in cats:
            lbl = nar if lang == 'ar' else nen
            btn.append([Button.inline(lbl, f'open_cat_{slug}_0'.encode())])
        btn.append([Button.inline(t['btn_search_plans'], b'search_plans_prompt')])
        btn.append([Button.inline(t['back'], b'main')])
        await safe_edit(
            event,
            UITheme.header(t['btn_personal'], "personal_section", "store") + "\n\n<blockquote>اختر المزود أو التصنيف المناسب لعرض الباقات المتاحة:</blockquote>",
            buttons=btn
        )

    elif data == 'search_plans_prompt':
        await safe_answer(event)
        SessionManager.set(uid, f'search_plans_{uid}', True)
        await safe_edit(
            event,
            UITheme.header("البحث عن باقة", "product", "products") + "\n\n<blockquote>أرسل اسم الباقة أو المزود أو المدة للبحث السريع (مثال: Vodafone أو Holafly أو 3 Months):</blockquote>",
            buttons=[[Button.inline(t['back'], b'personal_section')]]
        )

    elif data.startswith('open_cat_'):
        await safe_answer(event)
        raw = data.replace('open_cat_', '')
        if raw.rsplit('_', 1)[-1].isdigit():
            cat, page_str = raw.rsplit('_', 1)
            page = max(0, int(page_str))
        else:
            cat, page = raw, 0

        plans = cur.execute("SELECT id, name, price_usd, months, minutes, stock FROM esims WHERE category=? ORDER BY months ASC", (cat,)).fetchall()
        per_page = 6
        total_pages = max(1, (len(plans) + per_page - 1) // per_page)
        page = min(page, total_pages - 1)
        slice_plans = plans[page * per_page:(page + 1) * per_page]

        btn = []
        for pid, name, price, m, mins, st in slice_plans:
            min_str = f" | {mins} د" if mins > 0 else ""
            st_str = " [نفد]" if st <= 0 else ""
            btn.append([Button.inline(f"{name}{min_str} — ${price:.0f}{st_str}", f'show_plan_{pid}_1'.encode())])

        if total_pages > 1:
            nav = []
            if page > 0:
                nav.append(Button.inline(t['prev_page'], f'open_cat_{cat}_{page-1}'.encode()))
            nav.append(Button.inline(f"{page+1}/{total_pages}", b'noop'))
            if page + 1 < total_pages:
                nav.append(Button.inline(t['next_page'], f'open_cat_{cat}_{page+1}'.encode()))
            btn.append(nav)

        back_btn = b'personal_section' if not cat.startswith('dealer_') else b'dealer_section'
        btn.append([Button.inline(t['back'], back_btn), Button.inline(t['home'], b'main')])

        cat_info = cur.execute("SELECT name_ar, name_en FROM categories WHERE slug=?", (cat,)).fetchone()
        title_cat = (cat_info[0] if lang == 'ar' else cat_info[1]) if cat_info else cat
        policy = WARRANTY_POLICY_TEXT.get(lang, WARRANTY_POLICY_TEXT['ar'])
        select_dur = "اختر الباقة والمدة المطلوبة:" if lang == 'ar' else "Select desired plan:"
        await safe_edit(
            event,
            f"{UITheme.header(title_cat, 'product', 'products')}\n\n{policy}\n\n<blockquote>{ce('sim_card', 'products')}<b>{select_dur}</b></blockquote>",
            buttons=btn
        )

    # ------------------ تفاصيل الباقة والكمية والمراجعة ------------------
    elif data.startswith('show_plan_'):
        await safe_answer(event)
        parts = data.split('_')
        pid = int(parts[2])
        qty = int(parts[3]) if len(parts) > 3 else 1
        qty = max(1, min(50, qty))

        plan = cur.execute("SELECT id, name, price_usd, minutes, months, stock, category, is_dealer, description FROM esims WHERE id=?", (pid,)).fetchone()
        if not plan:
            return await safe_answer("الباقة غير متوفرة.", alert=True)

        esim_id, name, unit_price, mins, months, stock, cat, is_dealer, desc = plan
        if stock <= 0:
            return await safe_edit(
                event,
                UITheme.error("نفاد المخزون", f"الباقة <b>{name}</b> غير متوفرة حالياً في المخزون."),
                buttons=[[Button.inline(t['back'], f'open_cat_{cat}_0'.encode())]]
            )

        api_row = cur.execute("SELECT id FROM dealer_api_keys WHERE user_id=?", (uid,)).fetchone()
        has_api = api_row is not None
        effective_unit = unit_price * 0.5 if (has_api and is_dealer) else unit_price

        subtotal = effective_unit * qty
        discount_percent = 10 if qty > 1 else 0
        discount_amount = subtotal * (discount_percent / 100.0)
        final_price = subtotal - discount_amount

        existing_sess = SessionManager.get(uid, f'checkout_{uid}')
        scope_label = existing_sess.get('scope', 'Global (عالمية)') if isinstance(existing_sess, dict) and existing_sess.get('esim_id') == esim_id else 'Global (عالمية)'

        SessionManager.set(uid, f'checkout_{uid}', {
            'esim_id': esim_id,
            'qty': qty,
            'unit_price': effective_unit,
            'subtotal': subtotal,
            'discount_amount': discount_amount,
            'final_price': final_price,
            'name': name,
            'is_dealer': is_dealer,
            'scope': scope_label,
        })

        mins_text = f"\n{ce('sim_card', 'products')}<b>دقائق الاتصال:</b> <code>{mins} دقيقة رسمية</code>" if mins > 0 else f"\n{ce('sim_card', 'products')}<b>النوع:</b> بيانات إنترنت فقط"
        discount_badge = f"\n{ce('discount', 'products')}<b>خصم الكميات (10%):</b> <code>-${discount_amount:.2f}</code>" if discount_percent > 0 else ""

        info_text = (
            f"{UITheme.header(name, 'product', 'products')}\n\n"
            f"<blockquote>"
            f"{ce('coverage', 'countries')}<b>التغطية:</b> <code>{scope_label}</code>\n"
            f"{ce('pending', 'pending')}<b>المدة:</b> <code>{months} شهر</code>{mins_text}\n"
            f"{ce('balance', 'wallet')}<b>سعر الوحدة:</b> <code>${effective_unit:.2f}</code>\n"
            f"{ce('stock', 'products')}<b>المخزون المتاح:</b> <code>{stock} شريحة</code>\n"
            f"<b>المواصفات:</b> {desc}"
            f"</blockquote>\n\n"
            f"<blockquote>"
            f"<b>ملخص التسعير:</b>\n"
            f"• <b>الكمية:</b> <code>{qty}</code>\n"
            f"• <b>المجموع الفرعي:</b> <code>${subtotal:.2f}</code>{discount_badge}\n"
            f"• <b>الإجمالي النهائي:</b> <code>${final_price:.2f}</code>\n"
            f"<i>خصم 10% تلقائي عند اختيار أكثر من شريحة.</i>"
            f"</blockquote>"
        )

        btn = [
            [
                Button.inline("- تقليل", f'show_plan_{pid}_{qty-1}'.encode()),
                Button.inline(f"الكمية: {qty}", b'noop'),
                Button.inline("+ زيادة", f'show_plan_{pid}_{qty+1}'.encode())
            ],
            [
                Button.inline("1", f'show_plan_{pid}_1'.encode()),
                Button.inline("2 (خصم 10%)", f'show_plan_{pid}_2'.encode()),
                Button.inline("5 (خصم 10%)", f'show_plan_{pid}_5'.encode())
            ],
            [Button.inline(t['type_country'], f'pick_country_{pid}_0'.encode())],
            [Button.inline(f"مراجعة وتأكيد الشراء (${final_price:.2f})", f'review_buy_now_{pid}'.encode())],
            [Button.inline(t['pay_binance'], f'show_order_payments_{pid}'.encode()), Button.inline(t['add_to_cart'], f'add_cart_now_{pid}_{qty}'.encode())],
            [Button.inline(t['back'], f'open_cat_{cat}_0'.encode()), Button.inline(t['home'], b'main')]
        ]
        await safe_edit(event, info_text, buttons=btn)

    elif data.startswith('pick_country_'):
        await safe_answer(event)
        parts = data.split('_')
        pid = int(parts[2])
        page = int(parts[3]) if len(parts) > 3 else 0
        per_page = 12
        total_pages = max(1, (len(COUNTRIES_DATA) + per_page - 1) // per_page)
        page = max(0, min(page, total_pages - 1))
        chunk = COUNTRIES_DATA[page * per_page:(page + 1) * per_page]

        btn = []
        row = []
        for c in chunk:
            row.append(Button.inline(f"{c['flag']} {c['name']}", f"set_plan_country_{pid}_{c['name']}".encode()))
            if len(row) == 2:
                btn.append(row)
                row = []
        if row:
            btn.append(row)

        nav = []
        if page > 0:
            nav.append(Button.inline(t['prev_page'], f'pick_country_{pid}_{page-1}'.encode()))
        nav.append(Button.inline(f"{page+1}/{total_pages}", b'noop'))
        if page + 1 < total_pages:
            nav.append(Button.inline(t['next_page'], f'pick_country_{pid}_{page+1}'.encode()))
        btn.append(nav)
        btn.append([Button.inline(t['search_country_btn'], f'search_country_plan_{pid}'.encode())])
        btn.append([Button.inline(t['back'], f'show_plan_{pid}_1'.encode())])
        await safe_edit(event, UITheme.header(t['select_country_prompt'], "countries_globe", "countries"), buttons=btn)

    elif data.startswith('search_country_plan_'):
        await safe_answer(event)
        pid = int(data.split('_')[3])
        SessionManager.set(uid, f'search_country_for_{uid}', pid)
        await safe_edit(event, UITheme.header(t['search_prompt'], "countries_globe", "countries"), buttons=[[Button.inline(t['back'], f'pick_country_{pid}_0'.encode())]])

    elif data.startswith('set_plan_country_'):
        await safe_answer(event, "تم تحديد الدولة بنجاح.", alert=False)
        rest = data.replace('set_plan_country_', '')
        pid_str, cname = rest.split('_', 1)
        pid = int(pid_str)
        sess = SessionManager.get(uid, f'checkout_{uid}')
        qty = sess['qty'] if isinstance(sess, dict) else 1
        if isinstance(sess, dict):
            sess['scope'] = cname
            SessionManager.set(uid, f'checkout_{uid}', sess)
        event.data = f'show_plan_{pid}_{qty}'.encode()
        await callback(event)

    elif data == 'noop':
        await safe_answer(event, "استخدم الأزرار المتاحة للتنقل أو تعديل الكمية.", alert=False)

    elif data.startswith('add_cart_now_'):
        parts = data.split('_')
        pid = int(parts[3])
        qty = int(parts[4])
        sess = SessionManager.get(uid, f'checkout_{uid}')
        price = sess['final_price'] if isinstance(sess, dict) else 20.0
        scope_txt = sess.get('scope', 'Global') if isinstance(sess, dict) else 'Global'
        cur.execute("INSERT INTO cart (user_id, esim_id, scope, price) VALUES (?, ?, ?, ?)", (uid, pid, f"{scope_txt} | Qty: {qty}", price))
        conn.commit()
        await safe_answer(event, "تمت الإضافة إلى سلة المشتريات بنجاح.", alert=True)

    elif data.startswith('review_buy_now_'):
        await safe_answer(event)
        pid = int(data.split('_')[3])
        sess = SessionManager.get(uid, f'checkout_{uid}')
        if not isinstance(sess, dict) or sess.get('esim_id') != pid:
            return await safe_answer("انتهت جلسة الطلب، يرجى اختيار الباقة مجدداً.", alert=True)
        bal = get_wallet_balance(uid)
        review_txt = (
            f"{UITheme.header('مراجعة الطلب قبل الدفع', 'invoice', 'payments')}\n\n"
            f"<blockquote>"
            f"• <b>المنتج:</b> {sess['name']}\n"
            f"• <b>التغطية:</b> {sess.get('scope', 'Global')}\n"
            f"• <b>الكمية:</b> <code>{sess['qty']}</code>\n"
            f"• <b>الإجمالي المطلوب:</b> <code>${sess['final_price']:.2f}</code>\n"
            f"• <b>رصيد محفظتك الحالي:</b> <code>${bal:.2f}</code>"
            f"</blockquote>"
        )
        btn = [
            [Button.inline(f"تأكيد ودفع الآن (${sess['final_price']:.2f})", f'pay_wallet_now_{pid}'.encode())],
            [Button.inline(t['pay_binance'], f'show_order_payments_{pid}'.encode())],
            [Button.inline(t['back'], f"show_plan_{pid}_{sess['qty']}".encode())]
        ]
        await safe_edit(event, review_txt, buttons=btn)

    elif data.startswith('pay_wallet_now_'):
        if not debounce.allow(uid, f'pay_wallet_{data}', cooldown=2.5):
            return await safe_answer(event, "جاري تنفيذ طلبك بالفعل، يرجى الانتظار...", alert=True)
        await safe_answer(event)
        pid = int(data.split('_')[3])
        sess = SessionManager.get(uid, f'checkout_{uid}')
        if not isinstance(sess, dict) or sess.get('esim_id') != pid:
            return await safe_answer("انتهت الجلسة، يرجى إعادة المحاولة.", alert=True)

        final_price = sess['final_price']
        qty = sess['qty']
        name = sess['name']

        if uid not in wallet_locks:
            wallet_locks[uid] = asyncio.Lock()

        async with wallet_locks[uid]:
            stock_row = cur.execute("SELECT stock FROM esims WHERE id=?", (pid,)).fetchone()
            if not stock_row or stock_row[0] < qty:
                return await safe_edit(
                    event,
                    UITheme.error("المخزون غير كافٍ", f"الكمية المتاحة حالياً أقل من المطلوب ({qty})."),
                    buttons=[[Button.inline(t['back'], f'show_plan_{pid}_1'.encode())]]
                )
            bal = get_wallet_balance(uid)
            if bal < final_price:
                btn = [
                    [Button.inline("شحن المحفظة الآن", b'charge_wallet')],
                    [Button.inline(t['back'], b'main')]
                ]
                return await safe_edit(
                    event,
                    UITheme.error("رصيد غير كافٍ", f"الرصيد المتاح: <code>${bal:.2f}</code>\nالمبلغ المطلوب: <code>${final_price:.2f}</code>"),
                    buttons=btn
                )

            order_id = f"AURA{secrets.token_hex(4).upper()}"
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
            update_wallet(uid, -final_price, 'purchase', f"شراء {qty}x {name}")
            cur.execute("INSERT INTO orders VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                        (order_id, uid, pid, qty, final_price / qty, final_price, None, 'paid', sess['is_dealer'], 1, now_str, now_str))
            cur.execute("UPDATE esims SET stock = stock - ? WHERE id=?", (qty, pid))
            conn.commit()
            await check_low_stock_and_alert(pid)

        SessionManager.remove(uid, f'checkout_{uid}')

        if qty > 1:
            lpa_list = f"أكواد الشرائح المشتراة (طلب #{order_id}) - عدد {qty} شرائح:\n" + "\n".join([f"شريحة {i+1}: {DEFAULT_LPA}" for i in range(qty)])
            bio = io.BytesIO(lpa_list.encode('utf-8'))
            bio.name = f"Aura_eSIMs_{order_id}.txt"
            bio.seek(0)
            success_text = UITheme.success(
                "تم الشراء بنجاح مع خصم الكميات",
                f"• <b>معرف الطلب:</b> <code>{order_id}</code>\n"
                f"• <b>الباقة:</b> {name}\n"
                f"• <b>العدد:</b> <code>{qty}</code>\n"
                f"• <b>المبلغ المخصوم:</b> <code>${final_price:.2f}</code>\n"
                f"تم إرفاق ملف أكواد التفعيل أدناه."
            )
            await safe_reply(event, success_text, file=bio)
        else:
            success_single = UITheme.success(
                "تم الشراء بنجاح تام",
                f"• <b>معرف الطلب:</b> <code>{order_id}</code>\n"
                f"• <b>الباقة:</b> {name}\n"
                f"• <b>المبلغ المخصوم:</b> <code>${final_price:.2f}</code>\n\n"
                f"{ce('lpa_code', 'orders')}<b>كود التفعيل الفوري (LPA):</b>\n<code>{DEFAULT_LPA}</code>\n\n"
                f"{ce('qr_code', 'orders')}امسح الباركود المرفق لتفعيل الشريحة مباشرة."
            )
            await safe_reply(event, success_single, file=DEFAULT_BARCODE)

        sender = await event.get_sender()
        text, btn = main_menu(uid, get_user_display_name(sender, uid))
        await safe_respond(event, text, buttons=btn)

    # ------------------ قسم التجار وVIP ------------------
    elif data == 'vip_membership':
        await safe_answer(event)
        mem = get_membership_info(uid, lang)
        bal = get_wallet_balance(uid)
        orders_cnt = cur.execute("SELECT COUNT(*) FROM orders WHERE user_id=? AND status='paid'", (uid,)).fetchone()[0]
        if mem['has_api']:
            benefits = "• خصم دائم 50% على كافة باقات التجار.\n• وصول كامل لمفتاح الـ API الرسمي.\n• أولوية في الدعم الفني والتجهيز."
            start_dt = mem['created'] or "مفعل"
            exp_dt = "اشتراك دائم"
        else:
            benefits = "• خصم 10% تلقائي عند شراء أكثر من شريحة.\n• ضمان ذهبي لمدة 3 أشهر على جميع الشرائح.\n• إمكانية الترقية إلى باقة التجار API بخصم 50%."
            start_dt = "منذ التسجيل"
            exp_dt = "مستمر"
        vip_txt = (
            f"{UITheme.header('حالة العضوية وVIP', 'vip', 'vip')}\n\n"
            f"<blockquote>"
            f"{ce('crown', 'vip')}<b>العضوية الحالية:</b> <b>{mem['tier']}</b>\n"
            f"{ce('pending', 'pending')}<b>تاريخ البداية:</b> <code>{start_dt}</code>\n"
            f"{ce('pending', 'pending')}<b>الصلاحية:</b> <code>{exp_dt}</code>\n"
            f"{ce('balance', 'wallet')}<b>الرصيد:</b> <code>${bal:.2f}</code> | <b>الطلبات:</b> <code>{orders_cnt}</code>"
            f"</blockquote>\n\n"
            f"<blockquote><b>المميزات والصلاحيات المتاحة لك:</b>\n{benefits}</blockquote>"
        )
        btn = []
        if not mem['has_api']:
            btn.append([Button.inline(t['btn_dealer_api'], b'buy_api_sub_menu')])
        btn.append([Button.inline(t['back'], b'main')])
        await safe_edit(event, vip_txt, buttons=btn)

    elif data == 'dealer_section':
        await safe_answer(event)
        mem = get_membership_info(uid, lang)
        bal = get_wallet_balance(uid)
        dlr_orders = cur.execute("SELECT COUNT(*), COALESCE(SUM(total_usd), 0) FROM orders WHERE user_id=? AND is_dealer=1 AND status='paid'", (uid,)).fetchone()
        cats = cur.execute("SELECT slug, name_ar, name_en FROM categories WHERE slug LIKE 'dealer_%' AND is_visible=1").fetchall()
        btn = []
        for slug, nar, nen in cats:
            lbl = nar if lang == 'ar' else nen
            btn.append([Button.inline(lbl, f'open_cat_{slug}_0'.encode())])

        if not mem['has_api']:
            btn.append([Button.inline(t['btn_dealer_api'], b'buy_api_sub_menu')])
        else:
            btn.append([Button.inline("تفاصيل مفتاح الـ API", b'view_api_key_info'), Button.inline("سجل معاملات التاجر", b'wallet_transactions_0')])
        btn.append([Button.inline(t['back'], b'main')])

        dlr_txt = (
            f"{UITheme.header(t['dealer_title'], 'dealer', 'dealers')}\n\n"
            f"<blockquote>"
            f"{ce('wholesale', 'dealers')}<b>حالة الحساب:</b> <b>{mem['tier']}</b>\n"
            f"{ce('balance', 'wallet')}<b>رصيد التاجر:</b> <code>${bal:.2f}</code>\n"
            f"{ce('orders', 'orders')}<b>طلبات الجملة:</b> <code>{dlr_orders[0]}</code> | <b>إجمالي المشتريات:</b> <code>${dlr_orders[1]:.2f}</code>"
            f"</blockquote>"
        )
        await safe_edit(event, dlr_txt, buttons=btn)

    elif data == 'buy_api_sub_menu':
        await safe_answer(event)
        api_row = cur.execute("SELECT api_key FROM dealer_api_keys WHERE user_id=?", (uid,)).fetchone()
        if api_row:
            return await safe_answer("لديك اشتراك API مفعل مسبقاً.", alert=True)
        btn = [
            [Button.inline("تأكيد وشراء API الآن ($100)", b'confirm_buy_api_sub')],
            [Button.inline(t['back'], b'dealer_section')]
        ]
        desc_sub = (
            f"{UITheme.header('تفعيل نظام الـ API للتجار', 'api_key', 'dealers')}\n\n"
            f"<blockquote>• <b>تكلفة التفعيل لمرة واحدة:</b> <code>$100.00</code>\n"
            f"• <b>المميزات:</b> خصم دائم <b>50%</b> على باقات التجار + مفتاح API رسمي خاص بك.</blockquote>"
        )
        await safe_edit(event, desc_sub, buttons=btn)

    elif data == 'confirm_buy_api_sub':
        if not debounce.allow(uid, 'buy_api_sub', cooldown=3.0):
            return await safe_answer(event, "جاري المعالجة، يرجى الانتظار...", alert=True)
        await safe_answer(event)
        if uid not in wallet_locks:
            wallet_locks[uid] = asyncio.Lock()
        async with wallet_locks[uid]:
            existing = cur.execute("SELECT api_key FROM dealer_api_keys WHERE user_id=?", (uid,)).fetchone()
            if existing:
                return await safe_answer("لديك اشتراك API مفعل مسبقاً.", alert=True)
            balance = get_wallet_balance(uid)
            if balance < 100.0:
                return await safe_answer(t['insufficient_balance'], alert=True)
            update_wallet(uid, -100.0, 'api_subscription', 'شراء تفعيل نظام API للتجار')
            api_key = f"AURA_API_{secrets.token_hex(16).upper()}"
            cur.execute("INSERT OR REPLACE INTO dealer_api_keys (user_id, api_key, created_date) VALUES (?, ?, ?)",
                        (uid, api_key, datetime.now().strftime("%Y-%m-%d %H:%M")))
            conn.commit()
        success_txt = UITheme.success(
            "تم تفعيل اشتراك الـ API بنجاح",
            f"مفتاح الـ API الخاص بك:\n<code>{api_key}</code>\n\nتم تفعيل خصم 50% على باقات الجملة."
        )
        await safe_edit(event, success_txt, buttons=[[Button.inline(t['back'], b'dealer_section')]])

    elif data == 'view_api_key_info':
        await safe_answer(event)
        api_row = cur.execute("SELECT api_key, created_date FROM dealer_api_keys WHERE user_id=?", (uid,)).fetchone()
        if not api_row:
            return await safe_answer("ليس لديك اشتراك API مفعل.", alert=True)
        info_msg = (
            f"{UITheme.header('بيانات مفتاح الـ API الخاص بك', 'api_key', 'dealers')}\n\n"
            f"<blockquote>• <b>المفتاح:</b>\n<code>{api_row[0]}</code>\n"
            f"• <b>تاريخ التفعيل:</b> <code>{api_row[1]}</code>\n"
            f"• <b>الخصم المطبق:</b> <code>50%</code></blockquote>"
        )
        await safe_edit(event, info_msg, buttons=[[Button.inline(t['back'], b'dealer_section')]])

    # ------------------ المحفظة والمعاملات ------------------
    elif data == 'wallet':
        await safe_answer(event)
        balance = get_wallet_balance(uid)
        dep_row = cur.execute("SELECT COALESCE(total_deposited, 0) FROM wallets WHERE user_id=?", (uid,)).fetchone()
        total_dep = dep_row[0] if dep_row else 0.0
        bot_me = await client.get_me()
        ref_link = f"https://t.me/{bot_me.username}?start=ref{uid}"
        text = (
            f"{UITheme.header(t['wallet_title'], 'wallet', 'wallet')}\n\n"
            f"<blockquote>"
            f"{ce('balance', 'wallet')}<b>{t['current_balance']}:</b> <code>${balance:.2f}</code>\n"
            f"{ce('deposit', 'wallet')}<b>إجمالي الإيداعات:</b> <code>${total_dep:.2f}</code>"
            f"</blockquote>\n\n"
            f"<blockquote>{ce('referral', 'wallet')}<b>رابط الإحالة الخاص بك:</b>\n<code>{ref_link}</code></blockquote>"
        )
        btn = [
            [Button.inline(t['charge_wallet_btn'], b'charge_wallet'), Button.inline(t['btn_transactions'], b'wallet_transactions_0')],
            [Button.inline(t['btn_verify_payment'], b'verify_payment_menu')],
            [Button.inline(t['back'], b'main')]
        ]
        await safe_edit(event, text, buttons=btn)

    elif data == 'charge_wallet':
        await safe_answer(event)
        SessionManager.set(uid, f'charge_amount_prompt_{uid}', True)
        await safe_edit(event, t['charge_prompt'], buttons=[[Button.inline(t['back'], b'wallet')]])

    elif data == 'wallet_transactions' or data.startswith('wallet_transactions_'):
        await safe_answer(event)
        page = int(data.split('_')[2]) if data.startswith('wallet_transactions_') else 0
        per_page = 6
        total = cur.execute("SELECT COUNT(*) FROM wallet_transactions WHERE user_id=?", (uid,)).fetchone()[0]
        total_pages = max(1, (total + per_page - 1) // per_page)
        page = max(0, min(page, total_pages - 1))
        txs = cur.execute(
            "SELECT id, type, amount, balance_after, description, date FROM wallet_transactions WHERE user_id=? ORDER BY id DESC LIMIT ? OFFSET ?",
            (uid, per_page, page * per_page)
        ).fetchall()
        if not txs:
            return await safe_edit(
                event,
                UITheme.header("سجل المعاملات المالية", "invoice", "payments") + "\n\n<blockquote>لا توجد حركات مالية مسجلة في محفظتك حتى الآن.</blockquote>",
                buttons=[[Button.inline(t['back'], b'wallet')]]
            )
        tx_text = f"{UITheme.header('سجل المعاملات المالية', 'invoice', 'payments')}\n\n"
        for tx_id, t_type, amt, b_after, desc, date in txs:
            sign = "+" if amt > 0 else ""
            tx_text += (
                f"<blockquote>• <b>#{tx_id} — {desc}</b>\n"
                f"  المبلغ: <code>{sign}${amt:.2f}</code> | الرصيد بعد: <code>${b_after:.2f}</code>\n"
                f"  التاريخ: <code>{date}</code></blockquote>\n"
            )
        btn = []
        if total_pages > 1:
            nav = []
            if page > 0:
                nav.append(Button.inline(t['prev_page'], f'wallet_transactions_{page-1}'.encode()))
            nav.append(Button.inline(f"{page+1}/{total_pages}", b'noop'))
            if page + 1 < total_pages:
                nav.append(Button.inline(t['next_page'], f'wallet_transactions_{page+1}'.encode()))
            btn.append(nav)
        btn.append([Button.inline(t['back'], b'wallet')])
        await safe_edit(event, tx_text, buttons=btn)

    # ------------------ السلة ------------------
    elif data == 'view_cart':
        await safe_answer(event)
        items = cur.execute("SELECT c.id, c.esim_id, e.name, e.price_usd, c.scope, c.price FROM cart c JOIN esims e ON c.esim_id=e.id WHERE c.user_id=?", (uid,)).fetchall()
        if not items:
            return await safe_edit(
                event,
                UITheme.header(t['btn_cart'], "cart", "orders") + "\n\n<blockquote>سلة المشتريات فارغة تماماً.</blockquote>",
                buttons=[[Button.inline("تصفح الباقات", b'personal_section')], [Button.inline(t['back'], b'main')]]
            )
        total_cart = sum(i[5] for i in items)
        cart_text = f"{UITheme.header('سلة المشتريات', 'cart', 'orders')}\n\n"
        btn = []
        for cid, eid, name, unit_p, sc, pr in items:
            cart_text += f"<blockquote>• <b>{name}</b> ({sc})\n  السعر الفردي: <code>${unit_p:.2f}</code> | الإجمالي: <code>${pr:.2f}</code></blockquote>\n"
            btn.append([
                Button.inline(f"+ زيادة ({name[:12]})", f"cart_qty_{cid}_1".encode()),
                Button.inline("حذف", f"cart_del_{cid}".encode())
            ])
        cart_text += f"\n<blockquote><b>الإجمالي النهائي للسلة:</b> <code>${total_cart:.2f}</code></blockquote>"
        btn.append([Button.inline(f"تأكيد وشراء السلة (${total_cart:.2f})", b'cart_confirm')])
        btn.append([Button.inline(t['back'], b'main')])
        await safe_edit(event, cart_text, buttons=btn)

    elif data.startswith('cart_qty_'):
        parts = data.split('_')
        cid = int(parts[2])
        row = cur.execute("SELECT c.esim_id, c.scope, c.price, e.price_usd FROM cart c JOIN esims e ON c.esim_id=e.id WHERE c.id=? AND c.user_id=?", (cid, uid)).fetchone()
        if row:
            eid, sc, old_pr, unit_p = row
            m_q = re.search(r"Qty:\s*(\d+)", sc or "")
            qty = int(m_q.group(1)) if m_q else 1
            qty = min(50, qty + 1)
            new_sc = re.sub(r"Qty:\s*\d+", f"Qty: {qty}", sc) if m_q else f"{sc} | Qty: {qty}"
            sub = unit_p * qty
            new_pr = sub * (0.9 if qty > 1 else 1.0)
            cur.execute("UPDATE cart SET scope=?, price=? WHERE id=? AND user_id=?", (new_sc, new_pr, cid, uid))
            conn.commit()
        await safe_answer(event, "تم تحديث الكمية وتطبيق الخصم.", alert=False)
        event.data = b'view_cart'
        await callback(event)

    elif data.startswith('cart_del_'):
        cid = int(data.split('_')[2])
        cur.execute("DELETE FROM cart WHERE id=? AND user_id=?", (cid, uid))
        conn.commit()
        await safe_answer(event, "تم حذف المنتج من السلة.", alert=False)
        event.data = b'view_cart'
        await callback(event)

    elif data == 'cart_confirm':
        await safe_answer(event)
        items = cur.execute("SELECT c.esim_id, c.price, e.name FROM cart c JOIN esims e ON c.esim_id=e.id WHERE c.user_id=?", (uid,)).fetchall()
        if not items:
            return await safe_answer("السلة فارغة.", alert=True)
        total_price = sum(item[1] for item in items)
        bal = get_wallet_balance(uid)
        confirm_txt = (
            f"{UITheme.header('تأكيد شراء السلة', 'invoice', 'payments')}\n\n"
            f"<blockquote>• <b>عدد العناصر:</b> <code>{len(items)}</code>\n"
            f"• <b>الإجمالي النهائي:</b> <code>${total_price:.2f}</code>\n"
            f"• <b>رصيد محفظتك:</b> <code>${bal:.2f}</code></blockquote>"
        )
        btn = [
            [Button.inline(f"دفع الآن (${total_price:.2f})", b'cart_checkout')],
            [Button.inline(t['back'], b'view_cart')]
        ]
        await safe_edit(event, confirm_txt, buttons=btn)

    elif data == 'cart_checkout':
        if not debounce.allow(uid, 'cart_checkout', cooldown=2.5):
            return await safe_answer(event, "جاري تنفيذ طلبك، يرجى الانتظار...", alert=True)
        await safe_answer(event)
        items = cur.execute("SELECT c.esim_id, c.price, e.name FROM cart c JOIN esims e ON c.esim_id=e.id WHERE c.user_id=?", (uid,)).fetchall()
        if not items:
            return await safe_answer("السلة فارغة.", alert=True)
        total_price = sum(item[1] for item in items)
        if uid not in wallet_locks:
            wallet_locks[uid] = asyncio.Lock()
        async with wallet_locks[uid]:
            bal = get_wallet_balance(uid)
            if bal < total_price:
                return await safe_answer(t['insufficient_balance'], alert=True)
            order_id = f"AURA{secrets.token_hex(4).upper()}"
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
            update_wallet(uid, -total_price, 'purchase', f"شراء سلة مشتريات {order_id}")
            for eid, pr, nm in items:
                cur.execute("INSERT INTO orders VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                            (f"{order_id}_{eid}", uid, eid, 1, pr, pr, None, 'paid', 0, 1, now_str, now_str))
                cur.execute("UPDATE esims SET stock=stock-1 WHERE id=?", (eid,))
            cur.execute("DELETE FROM cart WHERE user_id=?", (uid,))
            conn.commit()
        await safe_reply(
            event,
            UITheme.success("تم دفع السلة بنجاح", f"رقم العملية: <code>{order_id}</code>\nكود التفعيل (LPA):\n<code>{DEFAULT_LPA}</code>"),
            file=DEFAULT_BARCODE
        )
        sender = await event.get_sender()
        text, btn = main_menu(uid, get_user_display_name(sender, uid))
        await safe_respond(event, text, buttons=btn)

    # ------------------ الطلبات ------------------
    elif data == 'my_orders' or data.startswith('my_orders_'):
        await safe_answer(event)
        page = int(data.split('_')[2]) if data.startswith('my_orders_') else 0
        per_page = 6
        total = cur.execute("SELECT COUNT(*) FROM orders WHERE user_id=? AND status='paid'", (uid,)).fetchone()[0]
        if not total:
            return await safe_edit(
                event,
                UITheme.header(t['my_orders_title'], "orders", "orders") + f"\n\n<blockquote>{t['no_orders']}</blockquote>",
                buttons=[[Button.inline(t['back'], b'main')]]
            )
        total_pages = max(1, (total + per_page - 1) // per_page)
        page = max(0, min(page, total_pages - 1))
        orders = cur.execute(
            "SELECT o.order_id, e.name, o.quantity, o.total_usd, o.created_date FROM orders o JOIN esims e ON o.esim_id=e.id WHERE o.user_id=? AND o.status='paid' ORDER BY o.created_date DESC LIMIT ? OFFSET ?",
            (uid, per_page, page * per_page)
        ).fetchall()
        text = f"{UITheme.header(t['my_orders_title'], 'orders', 'orders')}\n\n"
        btn = []
        for order_id, name, qty, total_u, date in orders:
            text += f"<blockquote>• <b>{qty}x {name}</b>\n  المبلغ: <code>${total_u:.2f}</code> | التاريخ: <code>{date}</code></blockquote>\n"
            btn.append([Button.inline(f"عرض تفاصيل #{order_id}", f"reload_{order_id}".encode())])
        if total_pages > 1:
            nav = []
            if page > 0:
                nav.append(Button.inline(t['prev_page'], f'my_orders_{page-1}'.encode()))
            nav.append(Button.inline(f"{page+1}/{total_pages}", b'noop'))
            if page + 1 < total_pages:
                nav.append(Button.inline(t['next_page'], f'my_orders_{page+1}'.encode()))
            btn.append(nav)
        btn.append([Button.inline(t['back'], b'main')])
        await safe_edit(event, text, buttons=btn)

    elif data.startswith('reload_'):
        await safe_answer(event)
        oid = data.replace('reload_', '')
        row = cur.execute("SELECT o.order_id, e.name, o.quantity, o.total_usd, o.created_date FROM orders o LEFT JOIN esims e ON o.esim_id=e.id WHERE o.order_id=? AND o.user_id=?", (oid, uid)).fetchone()
        if not row:
            return await safe_answer("الطلب غير موجود.", alert=True)
        _, ename, qty, tot, dt = row
        await safe_reply(
            event,
            UITheme.header(f"فاتورة وتفاصيل الطلب #{oid}", "invoice", "payments") + (
                f"\n\n<blockquote>• <b>الباقة:</b> {ename}\n"
                f"• <b>الكمية:</b> <code>{qty}</code> | <b>الإجمالي:</b> <code>${tot:.2f}</code>\n"
                f"• <b>التاريخ:</b> <code>{dt}</code>\n\n"
                f"{ce('lpa_code', 'orders')}<b>كود LPA الموحد:</b>\n<code>{DEFAULT_LPA}</code></blockquote>"
            ),
            file=DEFAULT_BARCODE
        )

    # ------------------ الدول المدعومة ------------------
    elif data == 'countries_list' or data.startswith('countries_list_'):
        await safe_answer(event)
        page = int(data.split('_')[2]) if data.startswith('countries_list_') else 0
        per_page = 25
        total_pages = max(1, (len(COUNTRIES_DATA) + per_page - 1) // per_page)
        page = max(0, min(page, total_pages - 1))
        chunk = COUNTRIES_DATA[page * per_page:(page + 1) * per_page]
        c_text = "".join([f"• <code>{c['flag']}</code> <b>{c['name']}</b> — {c['operators']}\n" for c in chunk])
        header = UITheme.header(t['countries_header'].replace("COUNTRIES_COUNT", str(len(COUNTRIES_DATA))), "countries_globe", "countries")
        btn = []
        nav = []
        if page > 0:
            nav.append(Button.inline(t['prev_page'], f'countries_list_{page-1}'.encode()))
        nav.append(Button.inline(f"{page+1}/{total_pages}", b'noop'))
        if page + 1 < total_pages:
            nav.append(Button.inline(t['next_page'], f'countries_list_{page+1}'.encode()))
        btn.append(nav)
        btn.append([Button.inline(t['back'], b'main')])
        await safe_edit(event, f"{header}\n\n<blockquote>{c_text}</blockquote>", buttons=btn)

    elif data == 'verify_payment_menu':
        await safe_answer(event)
        SessionManager.set(uid, f'verify_payment_{uid}', True)
        await safe_edit(event, t['verify_prompt'], buttons=[[Button.inline(t['back'], b'wallet')]])

    elif data == 'support_ticket':
        await safe_answer(event)
        SessionManager.set(uid, f'support_ticket_{uid}', True)
        await safe_edit(event, t['support_prompt'], buttons=[[Button.inline(t['back'], b'main')]])

    elif data.startswith('show_order_payments_'):
        await safe_answer(event)
        pid = int(data.split('_')[3])
        sess = SessionManager.get(uid, f'checkout_{uid}')
        price = sess['final_price'] if isinstance(sess, dict) else 20.0
        networks = cur.execute("SELECT network_name, address, binance_id FROM binance_networks").fetchall()
        details_text = UITheme.header(f"بوابة الدفع الشاملة — المطلوب: ${price:.2f}", "payment", "payments") + "\n\n"
        for idx, (n_name, n_addr, n_id) in enumerate(networks, 1):
            details_text += f"<blockquote><b>{idx}. {n_name}</b>\n"
            if n_id:
                details_text += f"• <b>ID:</b> <code>{n_id}</code>\n"
            if n_addr:
                details_text += f"• <b>Address:</b> <code>{n_addr}</code>\n"
            details_text += "</blockquote>\n"
        btn = [
            [Button.inline(t['btn_verify_now'], b'verify_payment_menu')],
            [Button.inline(t['back'], f'show_plan_{pid}_{sess["qty"] if isinstance(sess, dict) else 1}'.encode())]
        ]
        await safe_edit(event, details_text, buttons=btn)

    # ========================================================
    # 7. لوحة تحكم الأدمن الاحترافية (PRO ADMIN PANEL)
    # ========================================================
    elif data == 'admin_panel' and is_admin(uid):
        await safe_answer(event)
        total_sales = cur.execute("SELECT COUNT(*) FROM orders WHERE status='paid'").fetchone()[0]
        total_rev = cur.execute("SELECT COALESCE(SUM(total_usd), 0) FROM orders WHERE status='paid'").fetchone()[0]
        total_balance = cur.execute("SELECT COALESCE(SUM(balance), 0) FROM wallets").fetchone()[0]
        total_esims = cur.execute("SELECT COALESCE(SUM(stock), 0) FROM esims").fetchone()[0]
        total_users = cur.execute("SELECT COUNT(*) FROM users_settings").fetchone()[0]
        total_dealers = cur.execute("SELECT COUNT(*) FROM dealer_api_keys").fetchone()[0]
        btn = [
            [Button.inline("إدارة الأقسام", b'adm_cats_mgr'), Button.inline("إدارة الباقات والمخزون", b'adm_plans_mgr_0')],
            [Button.inline("إضافة شريحة جديدة", b'adm_plan_add_start'), Button.inline("طرق وشبكات الدفع", b'adm_pay_mgr')],
            [Button.inline("إدارة المستخدمين", b'adm_users_mgr_0'), Button.inline("التجار ومفاتيح API", b'adm_dealers_mgr')],
            [Button.inline("الطلبات الأخيرة", b'adm_orders_mgr_0'), Button.inline("الإيموجيات المخصصة", b'adm_emojis_mgr')],
            [Button.inline("شحن رصيد لعميل", b'admin_add_balance'), Button.inline("خصم رصيد", b'admin_sub_balance')],
            [Button.inline("تصفير رصيد عميل", b'admin_zero_balance'), Button.inline("إضافة مخزون عام", b'admin_add_stock')],
            [Button.inline("حظر / فك حظر", b'admin_manage_bans'), Button.inline("إذاعة عامة", b'admin_broadcast_msg')],
            [Button.inline(t['back'], b'main')]
        ]
        panel_txt = (
            f"{UITheme.header(t['admin_panel_title'], 'admin_panel', 'admin')}\n\n"
            f"<blockquote>"
            f"{ce('users', 'admin')}<b>المستخدمون:</b> <code>{total_users}</code> | <b>التجار API:</b> <code>{total_dealers}</code>\n"
            f"{ce('stats', 'admin')}<b>{t['stats_sales']}:</b> <code>{total_sales}</code> (<code>${total_rev:.2f}</code>)\n"
            f"{ce('wallet', 'wallet')}<b>{t['stats_wallets']}:</b> <code>${total_balance:.2f}</code>\n"
            f"{ce('stock', 'products')}<b>{t['stats_esims']}:</b> <code>{total_esims}</code>"
            f"</blockquote>"
        )
        await safe_edit(event, panel_txt, buttons=btn)

    # ------------------ إدارة الإيموجيات المخصصة ------------------
    elif data == 'adm_emojis_mgr' and is_admin(uid):
        await safe_answer(event)
        btn = []
        row = []
        for cat in DEFAULT_CUSTOM_EMOJI_SCHEMA:
            lbl = CATEGORY_LABELS_AR.get(cat, cat)
            cnt_set = sum(1 for v in emoji_mgr.data.get(cat, {}).values() if v)
            tot_k = len(emoji_mgr.data.get(cat, {}))
            row.append(Button.inline(f"{lbl} ({cnt_set}/{tot_k})", f"adm_emo_cat_{cat}".encode()))
            if len(row) == 2:
                btn.append(row)
                row = []
        if row:
            btn.append(row)
        btn.append([Button.inline(t['back'], b'admin_panel')])
        await safe_edit(
            event,
            UITheme.header("إدارة الإيموجيات المخصصة (Custom Emojis)", "settings", "settings") + "\n\n<blockquote>اختر التصنيف لإضافة أو تعديل أو اختبار معرفات Telegram Premium Custom Emoji الحقيقية:</blockquote>",
            buttons=btn
        )

    elif data.startswith('adm_emo_cat_') and is_admin(uid):
        await safe_answer(event)
        cat = data.replace('adm_emo_cat_', '')
        keys = emoji_mgr.data.get(cat, {})
        lbl = CATEGORY_LABELS_AR.get(cat, cat)
        txt = f"{UITheme.header(f'تصنيف الإيموجيات: {lbl}', 'settings', 'settings')}\n\n"
        btn = []
        for k, eid in keys.items():
            status = "مفعل" if eid else "فارغ"
            txt += f"• <code>{k}</code>: {ce(k, cat)}<code>{eid if eid else 'غير محدد'}</code>\n"
            btn.append([Button.inline(f"{k} [{status}]", f"adm_emo_set_{cat}|{k}".encode())])
        btn.append([Button.inline(t['back'], b'adm_emojis_mgr')])
        await safe_edit(event, txt, buttons=btn)

    elif data.startswith('adm_emo_set_') and is_admin(uid):
        await safe_answer(event)
        payload = data.replace('adm_emo_set_', '')
        cat, k = payload.split('|', 1)
        SessionManager.set(uid, f'adm_emo_input_{uid}', {"cat": cat, "key": k})
        cur_id = emoji_mgr.get_id(k, cat)
        await safe_edit(
            event,
            UITheme.header(f"تعيين معرف: {k}", "settings", "settings") + f"\n\n<blockquote>المعرف الحالي: <code>{cur_id or 'فارغ'}</code>\nأرسل رقم Custom Emoji ID الصحيح الآن، أو أرسل <code>clear</code> لمسحه:</blockquote>",
            buttons=[[Button.inline(t['back'], f'adm_emo_cat_{cat}'.encode())]]
        )

    # ------------------ إدارة المستخدمين ------------------
    elif data.startswith('adm_users_mgr_') and is_admin(uid):
        await safe_answer(event)
        page = int(data.split('_')[3])
        per_page = 8
        total = cur.execute("SELECT COUNT(*) FROM users_settings").fetchone()[0]
        total_pages = max(1, (total + per_page - 1) // per_page)
        page = max(0, min(page, total_pages - 1))
        rows = cur.execute(
            "SELECT u.user_id, u.lang, COALESCE(w.balance, 0) FROM users_settings u LEFT JOIN wallets w ON u.user_id=w.user_id ORDER BY u.user_id DESC LIMIT ? OFFSET ?",
            (per_page, page * per_page)
        ).fetchall()
        txt = f"{UITheme.header(f'إدارة المستخدمين ({total})', 'users', 'admin')}\n\n"
        btn = []
        for u_id, u_lang, u_bal in rows:
            banned_lbl = " [محظور]" if is_banned(u_id) else ""
            btn.append([Button.inline(f"ID: {u_id} | ${u_bal:.2f} | {u_lang}{banned_lbl}", f"adm_user_det_{u_id}".encode())])
        nav = []
        if page > 0:
            nav.append(Button.inline(t['prev_page'], f'adm_users_mgr_{page-1}'.encode()))
        nav.append(Button.inline(f"{page+1}/{total_pages}", b'noop'))
        if page + 1 < total_pages:
            nav.append(Button.inline(t['next_page'], f'adm_users_mgr_{page+1}'.encode()))
        if total_pages > 1:
            btn.append(nav)
        btn.append([Button.inline("بحث برقم الآيدي", b'adm_user_search'), Button.inline(t['back'], b'admin_panel')])
        await safe_edit(event, txt, buttons=btn)

    elif data == 'adm_user_search' and is_admin(uid):
        await safe_answer(event)
        SessionManager.set(uid, f'adm_user_search_{uid}', True)
        await safe_edit(event, UITheme.header("بحث عن مستخدم", "users", "admin") + "\n\n<blockquote>أرسل رقم آيدي المستخدم (User ID):</blockquote>", buttons=[[Button.inline(t['back'], b'adm_users_mgr_0')]])

    elif data.startswith('adm_user_det_') and is_admin(uid):
        await safe_answer(event)
        tid = int(data.split('_')[3])
        bal = get_wallet_balance(tid)
        ord_cnt = cur.execute("SELECT COUNT(*), COALESCE(SUM(total_usd), 0) FROM orders WHERE user_id=? AND status='paid'", (tid,)).fetchone()
        mem = get_membership_info(tid, 'ar')
        ban_st = "محظور" if is_banned(tid) else "نشط"
        txt = (
            f"{UITheme.header(f'ملف المستخدم: {tid}', 'users', 'admin')}\n\n"
            f"<blockquote>• <b>الحالة:</b> <b>{ban_st}</b>\n"
            f"• <b>العضوية:</b> <b>{mem['tier']}</b>\n"
            f"• <b>الرصيد:</b> <code>${bal:.2f}</code>\n"
            f"• <b>الطلبات:</b> <code>{ord_cnt[0]}</code> (<code>${ord_cnt[1]:.2f}</code>)</blockquote>"
        )
        btn = [
            [Button.inline("تبديل الحظر", f"adm_user_toggle_ban_{tid}".encode())],
            [Button.inline(t['back'], b'adm_users_mgr_0')]
        ]
        await safe_edit(event, txt, buttons=btn)

    elif data.startswith('adm_user_toggle_ban_') and is_admin(uid):
        tid = int(data.split('_')[4])
        if tid == DEV_ID:
            return await safe_answer(event, "لا يمكن حظر المطور الأساسي.", alert=True)
        if is_banned(tid):
            cur.execute("DELETE FROM bans WHERE user_id=?", (tid,))
            ban_cache.pop(tid, None)
            msg = "تم فك الحظر بنجاح."
        else:
            cur.execute("INSERT OR REPLACE INTO bans (user_id) VALUES (?)", (tid,))
            ban_cache[tid] = True
            msg = "تم حظر المستخدم بنجاح."
        conn.commit()
        await safe_answer(event, msg, alert=True)
        event.data = f"adm_user_det_{tid}".encode()
        await callback(event)

    elif data == 'adm_dealers_mgr' and is_admin(uid):
        await safe_answer(event)
        rows = cur.execute("SELECT user_id, api_key, created_date FROM dealer_api_keys ORDER BY id DESC LIMIT 20").fetchall()
        txt = f"{UITheme.header(f'التجار ومفاتيح API ({len(rows)})', 'dealer', 'dealers')}\n\n"
        if not rows:
            txt += "<blockquote>لا يوجد تجار API مسجلين حالياً.</blockquote>"
        else:
            for d_uid, d_key, d_dt in rows:
                txt += f"<blockquote>• <b>الآيدي:</b> <code>{d_uid}</code>\n  المفتاح: <code>{d_key[:14]}...</code> | {d_dt}</blockquote>\n"
        await safe_edit(event, txt, buttons=[[Button.inline(t['back'], b'admin_panel')]])

    elif data.startswith('adm_orders_mgr_') and is_admin(uid):
        await safe_answer(event)
        page = int(data.split('_')[3])
        per_page = 8
        total = cur.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
        total_pages = max(1, (total + per_page - 1) // per_page)
        page = max(0, min(page, total_pages - 1))
        rows = cur.execute("SELECT o.order_id, o.user_id, e.name, o.quantity, o.total_usd, o.status, o.created_date FROM orders o LEFT JOIN esims e ON o.esim_id=e.id ORDER BY o.created_date DESC LIMIT ? OFFSET ?", (per_page, page * per_page)).fetchall()
        txt = f"{UITheme.header(f'إدارة الطلبات ({total})', 'orders', 'orders')}\n\n"
        if not rows:
            txt += "<blockquote>لا توجد طلبات مسجلة.</blockquote>"
        else:
            for oid, u_id, ename, qty, tot, st_o, dt in rows:
                txt += f"<blockquote>• <b>#{oid}</b> | عميل: <code>{u_id}</code>\n  {qty}x {ename} | <code>${tot:.2f}</code> | {st_o} | {dt}</blockquote>\n"
        btn = []
        if total_pages > 1:
            nav = []
            if page > 0:
                nav.append(Button.inline(t['prev_page'], f'adm_orders_mgr_{page-1}'.encode()))
            nav.append(Button.inline(f"{page+1}/{total_pages}", b'noop'))
            if page + 1 < total_pages:
                nav.append(Button.inline(t['next_page'], f'adm_orders_mgr_{page+1}'.encode()))
            btn.append(nav)
        btn.append([Button.inline(t['back'], b'admin_panel')])
        await safe_edit(event, txt, buttons=btn)

    # ------------------ إدارة الأقسام ------------------
    elif data == 'adm_cats_mgr' and is_admin(uid):
        await safe_answer(event)
        cats = cur.execute("SELECT slug, name_ar, is_visible FROM categories").fetchall()
        txt = f"{UITheme.header('إدارة الأقسام (إخفاء / إظهار / حذف / إضافة)', 'categories', 'admin')}\n\n"
        btn = []
        for slug, nar, vis in cats:
            status_lbl = "ظاهر" if vis == 1 else "مخفي"
            btn.append([Button.inline(f"{nar} [{status_lbl}]", f"adm_cat_det_{slug}".encode())])
        btn.append([Button.inline("إضافة قسم جديد", b'adm_cat_add')])
        btn.append([Button.inline(t['back'], b'admin_panel')])
        await safe_edit(event, txt, buttons=btn)

    elif data.startswith('adm_cat_det_') and is_admin(uid):
        await safe_answer(event)
        slug = data.replace('adm_cat_det_', '')
        cat = cur.execute("SELECT name_ar, is_visible FROM categories WHERE slug=?", (slug,)).fetchone()
        if not cat:
            return
        nar, vis = cat
        toggle_label = "إخفاء القسم عن المستخدمين" if vis == 1 else "إظهار القسم للمستخدمين"
        btn = [
            [Button.inline(toggle_label, f"adm_cat_toggle_{slug}".encode())],
            [Button.inline("حذف القسم مع شرائحه", f"adm_cat_del_confirm_{slug}".encode())],
            [Button.inline(t['back'], b'adm_cats_mgr')]
        ]
        await safe_edit(event, f"{UITheme.header(f'إدارة القسم: {nar}', 'categories', 'admin')}\n\n<blockquote>الحالة الحالية: <b>{'ظاهر' if vis==1 else 'مخفي'}</b></blockquote>", buttons=btn)

    elif data.startswith('adm_cat_toggle_') and is_admin(uid):
        slug = data.replace('adm_cat_toggle_', '')
        cur.execute("UPDATE categories SET is_visible = CASE WHEN is_visible=1 THEN 0 ELSE 1 END WHERE slug=?", (slug,))
        conn.commit()
        await safe_answer(event, "تم تبديل حالة القسم بنجاح.", alert=True)
        event.data = f"adm_cat_det_{slug}".encode()
        await callback(event)

    elif data.startswith('adm_cat_del_confirm_') and is_admin(uid):
        await safe_answer(event)
        slug = data.replace('adm_cat_del_confirm_', '')
        btn = [
            [Button.inline("تأكيد الحذف النهائي", f"adm_cat_delete_{slug}".encode())],
            [Button.inline("إلغاء", f"adm_cat_det_{slug}".encode())]
        ]
        await safe_edit(event, UITheme.warning("تأكيد حذف القسم", f"هل أنت متأكد من حذف القسم <code>{slug}</code> وكافة شرائحه؟"), buttons=btn)

    elif data.startswith('adm_cat_delete_') and is_admin(uid):
        slug = data.replace('adm_cat_delete_', '')
        cur.execute("DELETE FROM categories WHERE slug=?", (slug,))
        cur.execute("DELETE FROM esims WHERE category=?", (slug,))
        conn.commit()
        await safe_answer(event, "تم حذف القسم وكافة شرائحه بنجاح.", alert=True)
        event.data = b'adm_cats_mgr'
        await callback(event)

    elif data == 'adm_cat_add' and is_admin(uid):
        await safe_answer(event)
        SessionManager.set(uid, f'adm_new_cat_{uid}', True)
        await safe_edit(event, "<blockquote>أرسل بيانات القسم الجديد بالصيغة:\n<code>المعرف(slug) | اسم القسم بالعربي | Name in English</code>\n\nمثال:\n<code>zain | باقات زين الدولية | Zain Plans</code></blockquote>", buttons=[[Button.inline(t['back'], b'adm_cats_mgr')]])

    # ------------------ إضافة وإدارة الشرائح ------------------
    elif data == 'adm_plan_add_start' and is_admin(uid):
        await safe_answer(event)
        cats = cur.execute("SELECT slug, name_ar FROM categories").fetchall()
        cats_list_str = "\n".join([f"• <code>{s}</code> ({n})" for s, n in cats])
        SessionManager.set(uid, f'adm_add_plan_input_{uid}', True)
        msg_input = (
            f"{UITheme.header('إضافة شريحة جديدة لقسم معين', 'product', 'products')}\n\n"
            f"<blockquote>الأقسام المتاحة حالياً:\n{cats_list_str}\n\n"
            f"أرسل البيانات بسطر واحد بالصيغة التالية:\n"
            f"<code>المعرف(slug) | اسم الشريحة | السعر | الدقائق | الشهور | المخزون | جملة(1 أو 0) | الوصف</code></blockquote>"
        )
        await safe_edit(event, msg_input, buttons=[[Button.inline(t['back'], b'admin_panel')]])

    elif (data == 'adm_plans_mgr' or data.startswith('adm_plans_mgr_')) and is_admin(uid):
        await safe_answer(event)
        page = int(data.split('_')[3]) if data.startswith('adm_plans_mgr_') else 0
        per_page = 10
        total = cur.execute("SELECT COUNT(*) FROM esims").fetchone()[0]
        total_pages = max(1, (total + per_page - 1) // per_page)
        page = max(0, min(page, total_pages - 1))
        plans = cur.execute("SELECT id, name, price_usd, stock FROM esims ORDER BY id ASC LIMIT ? OFFSET ?", (per_page, page * per_page)).fetchall()
        txt = f"{UITheme.header(f'إدارة الشرائح والمخزون ({total})', 'stock', 'products')}\n\n<blockquote>اختر شريحة لتعديل سعرها أو مخزونها أو تصفيرها:</blockquote>"
        btn = []
        for pid, name, pr, st in plans:
            btn.append([Button.inline(f"{name} | ${pr:.0f} | متبقي: {st}", f"adm_plan_det_{pid}".encode())])
        if total_pages > 1:
            nav = []
            if page > 0:
                nav.append(Button.inline(t['prev_page'], f'adm_plans_mgr_{page-1}'.encode()))
            nav.append(Button.inline(f"{page+1}/{total_pages}", b'noop'))
            if page + 1 < total_pages:
                nav.append(Button.inline(t['next_page'], f'adm_plans_mgr_{page+1}'.encode()))
            btn.append(nav)
        btn.append([Button.inline(t['back'], b'admin_panel')])
        await safe_edit(event, txt, buttons=btn)

    elif data.startswith('adm_plan_det_') and is_admin(uid):
        await safe_answer(event)
        pid = int(data.split('_')[3])
        plan = cur.execute("SELECT id, name, price_usd, stock, minutes, months FROM esims WHERE id=?", (pid,)).fetchone()
        if not plan:
            return
        esim_id, name, pr, st, mins, mo = plan
        SessionManager.set(uid, f'target_plan_id_{uid}', pid)
        info = (
            f"{UITheme.header(f'إدارة الشريحة: {name}', 'product', 'products')}\n\n"
            f"<blockquote>• <b>المدة:</b> <code>{mo} شهر</code>\n"
            f"• <b>الدقائق:</b> <code>{mins} دقيقة</code>\n"
            f"• <b>السعر:</b> <code>${pr:.2f}</code>\n"
            f"• <b>المخزون الحالي:</b> <code>{st} قطعة</code></blockquote>"
        )
        btn = [
            [Button.inline("تصفير مخزون الشريحة", f"adm_plan_zero_{pid}".encode())],
            [Button.inline("تعديل السعر", b'adm_edit_plan_price'), Button.inline("تعديل المخزون", b'adm_edit_plan_stock')],
            [Button.inline("حذف الشريحة نهائياً", f"adm_plan_del_confirm_{pid}".encode())],
            [Button.inline(t['back'], b'adm_plans_mgr_0')]
        ]
        await safe_edit(event, info, buttons=btn)

    elif data.startswith('adm_plan_zero_') and is_admin(uid):
        pid = int(data.split('_')[3])
        cur.execute("UPDATE esims SET stock = 0 WHERE id=?", (pid,))
        conn.commit()
        await safe_answer(event, "تم تصفير مخزون الشريحة بنجاح.", alert=True)
        event.data = f"adm_plan_det_{pid}".encode()
        await callback(event)

    elif data.startswith('adm_plan_del_confirm_') and is_admin(uid):
        await safe_answer(event)
        pid = int(data.split('_')[4])
        btn = [
            [Button.inline("تأكيد الحذف النهائي", f"adm_plan_delete_{pid}".encode())],
            [Button.inline("إلغاء", f"adm_plan_det_{pid}".encode())]
        ]
        await safe_edit(event, UITheme.warning("تأكيد حذف الشريحة", "هل أنت متأكد من حذف هذه الشريحة نهائياً؟"), buttons=btn)

    elif data.startswith('adm_plan_delete_') and is_admin(uid):
        pid = int(data.split('_')[3])
        cur.execute("DELETE FROM esims WHERE id=?", (pid,))
        conn.commit()
        await safe_answer(event, "تم حذف الشريحة نهائياً.", alert=True)
        event.data = b'adm_plans_mgr_0'
        await callback(event)

    elif data == 'adm_edit_plan_price' and is_admin(uid):
        await safe_answer(event)
        SessionManager.set(uid, f'action_plan_price_{uid}', True)
        await safe_edit(event, "<blockquote>أرسل السعر الجديد بالدولار لهذه الشريحة (مثال: <code>25.5</code>):</blockquote>", buttons=[[Button.inline(t['back'], b'adm_plans_mgr_0')]])

    elif data == 'adm_edit_plan_stock' and is_admin(uid):
        await safe_answer(event)
        SessionManager.set(uid, f'action_plan_stock_{uid}', True)
        await safe_edit(event, "<blockquote>أرسل كمية المخزون الجديدة للشريحة (مثال: <code>100</code>):</blockquote>", buttons=[[Button.inline(t['back'], b'adm_plans_mgr_0')]])

    # ------------------ إدارة طرق وشبكات الدفع ------------------
    elif data == 'adm_pay_mgr' and is_admin(uid):
        await safe_answer(event)
        nets = cur.execute("SELECT network_key, network_name, address, binance_id FROM binance_networks").fetchall()
        txt = f"{UITheme.header('إدارة طرق وشبكات الدفع', 'payment', 'payments')}\n\n<blockquote>اختر وسيلة لتعديلها أو حذفها، أو أضف وسيلة جديدة:</blockquote>"
        btn = []
        for k, name, addr, bid in nets:
            val = bid if bid else ((addr[:12] + "...") if addr else "غير محدد")
            btn.append([Button.inline(f"{name} ({val})", f"adm_pay_det_{k}".encode())])
        btn.append([Button.inline("إضافة وسيلة دفع جديدة", b'adm_pay_add')])
        btn.append([Button.inline(t['back'], b'admin_panel')])
        await safe_edit(event, txt, buttons=btn)

    elif data.startswith('adm_pay_det_') and is_admin(uid):
        await safe_answer(event)
        key = data.replace('adm_pay_det_', '')
        net = cur.execute("SELECT network_key, network_name, address, binance_id FROM binance_networks WHERE network_key=?", (key,)).fetchone()
        if not net:
            return
        k, name, addr, bid = net
        SessionManager.set(uid, f'target_pay_key_{uid}', k)
        info = (
            f"{UITheme.header(f'تعديل طريقة الدفع: {name}', 'payment', 'payments')}\n\n"
            f"<blockquote>• <b>العنوان:</b> <code>{addr if addr else 'غير محدد'}</code>\n"
            f"• <b>ID / Pay ID:</b> <code>{bid if bid else 'غير محدد'}</code></blockquote>"
        )
        btn = [
            [Button.inline("تعديل العنوان", b'adm_pay_set_addr'), Button.inline("تعديل الـ ID", b'adm_pay_set_id')],
            [Button.inline("حذف وسيلة الدفع", f"adm_pay_del_confirm_{k}".encode())],
            [Button.inline(t['back'], b'adm_pay_mgr')]
        ]
        await safe_edit(event, info, buttons=btn)

    elif data.startswith('adm_pay_del_confirm_') and is_admin(uid):
        await safe_answer(event)
        key = data.replace('adm_pay_del_confirm_', '')
        btn = [
            [Button.inline("تأكيد الحذف", f"adm_pay_delete_{key}".encode())],
            [Button.inline("إلغاء", f"adm_pay_det_{key}".encode())]
        ]
        await safe_edit(event, UITheme.warning("تأكيد حذف وسيلة الدفع", f"هل أنت متأكد من حذف وسيلة الدفع <code>{key}</code>؟"), buttons=btn)

    elif data.startswith('adm_pay_delete_') and is_admin(uid):
        key = data.replace('adm_pay_delete_', '')
        cur.execute("DELETE FROM binance_networks WHERE network_key=?", (key,))
        conn.commit()
        await safe_answer(event, "تم حذف وسيلة الدفع بنجاح.", alert=True)
        event.data = b'adm_pay_mgr'
        await callback(event)

    elif data == 'adm_pay_set_addr' and is_admin(uid):
        await safe_answer(event)
        SessionManager.set(uid, f'adm_pay_set_addr_{uid}', True)
        await safe_edit(event, "<blockquote>أرسل العنوان الجديد (Wallet Address):</blockquote>", buttons=[[Button.inline(t['back'], b'adm_pay_mgr')]])

    elif data == 'adm_pay_set_id' and is_admin(uid):
        await safe_answer(event)
        SessionManager.set(uid, f'adm_pay_set_id_{uid}', True)
        await safe_edit(event, "<blockquote>أرسل الـ ID الجديد (Binance / Bybit / Pay ID):</blockquote>", buttons=[[Button.inline(t['back'], b'adm_pay_mgr')]])

    elif data == 'adm_pay_add' and is_admin(uid):
        await safe_answer(event)
        SessionManager.set(uid, f'adm_new_pay_{uid}', True)
        await safe_edit(event, "<blockquote>أرسل وسيلة الدفع الجديدة بالصيغة:\n<code>اسم الشبكة | العنوان أو المحفظة | ID المنصة (اختياري)</code></blockquote>", buttons=[[Button.inline(t['back'], b'adm_pay_mgr')]])

    # ------------------ الرصيد والمخزون والإذاعة وقبول الإيصالات ------------------
    elif data == 'admin_add_balance' and is_admin(uid):
        await safe_answer(event)
        SessionManager.set(uid, f'add_balance_{uid}', True)
        await safe_edit(event, "<blockquote>أرسل آيدي العميل ثم المبلغ (مثال: <code>123456789 50</code>):</blockquote>", buttons=[[Button.inline(t['back'], b'admin_panel')]])

    elif data == 'admin_sub_balance' and is_admin(uid):
        await safe_answer(event)
        SessionManager.set(uid, f'sub_balance_{uid}', True)
        await safe_edit(event, "<blockquote>أرسل آيدي العميل ثم المبلغ (مثال: <code>123456789 20</code>):</blockquote>", buttons=[[Button.inline(t['back'], b'admin_panel')]])

    elif data == 'admin_zero_balance' and is_admin(uid):
        await safe_answer(event)
        SessionManager.set(uid, f'zero_balance_{uid}', True)
        await safe_edit(event, "<blockquote>أرسل آيدي العميل لتصفير محفظته:</blockquote>", buttons=[[Button.inline(t['back'], b'admin_panel')]])

    elif data == 'admin_add_stock' and is_admin(uid):
        await safe_answer(event)
        SessionManager.set(uid, f'add_stock_{uid}', True)
        await safe_edit(event, "<blockquote>أرسل الكمية المراد إضافتها لجميع الشرائح:</blockquote>", buttons=[[Button.inline(t['back'], b'admin_panel')]])

    elif data == 'admin_manage_bans' and is_admin(uid):
        await safe_answer(event)
        SessionManager.set(uid, f'manage_bans_{uid}', True)
        await safe_edit(event, "<blockquote>أرسل آيدي المستخدم لحظر / فك حظره:</blockquote>", buttons=[[Button.inline(t['back'], b'admin_panel')]])

    elif data == 'admin_broadcast_msg' and is_admin(uid):
        await safe_answer(event)
        SessionManager.set(uid, f'broadcast_{uid}', True)
        await safe_edit(event, "<blockquote>أرسل الرسالة المراد إذاعتها لجميع المستخدمين:</blockquote>", buttons=[[Button.inline(t['back'], b'admin_panel')]])

    elif data.startswith('admin_approve_dep_') and is_admin(uid):
        await safe_answer(event)
        parts = data.split('_')
        target_uid = int(parts[3])
        dep_amount = float(parts[4])
        update_wallet(target_uid, dep_amount, 'admin_deposit', f"شحن إيصال مقبول بقيمة ${dep_amount}")
        try:
            await safe_send(target_uid, UITheme.success("تم قبول إيصال الدفع", f"تمت إضافة مبلغ <code>${dep_amount:.2f}</code> إلى محفظتك بنجاح."))
        except Exception:
            pass
        await safe_edit(event, UITheme.success("تم شحن المحفظة", f"تم قبول الطلب وشحن <code>${dep_amount:.2f}</code> للمستخدم <code>{target_uid}</code>."), buttons=[[Button.inline("لوحة التحكم", b'admin_panel')]])

    elif data.startswith('admin_reject_dep_') and is_admin(uid):
        await safe_answer(event)
        parts = data.split('_')
        target_uid = int(parts[3])
        try:
            await safe_send(target_uid, UITheme.error("تم رفض إيصال الدفع", "عذراً، لم يتم قبول الإيصال المرسل. يرجى التواصل مع الدعم الفني."))
        except Exception:
            pass
        await safe_edit(event, UITheme.warning("تم رفض الإيصال", "تم رفض الإيصال وإبلاغ المستخدم."), buttons=[[Button.inline("لوحة التحكم", b'admin_panel')]])


# ==========================================
# 8. معالجة الرسائل والمدخلات
# ==========================================
@client.on(events.NewMessage)
async def handler(event):
    uid = event.sender_id
    if is_banned(uid) or (event.text and event.text.startswith('/')):
        return

    now = time.time()
    if uid in user_rate_limits and now - user_rate_limits[uid] < 0.3:
        return
    user_rate_limits[uid] = now

    text = event.text.strip() if event.text else ""
    lang = get_user_lang(uid) or 'ar'
    t = LANGS.get(lang, LANGS['ar'])

    # البحث عن الباقات
    if SessionManager.has(uid, f'search_plans_{uid}'):
        SessionManager.remove(uid, f'search_plans_{uid}')
        q = text.lower()
        rows = cur.execute("SELECT id, name, price_usd, stock FROM esims WHERE LOWER(name) LIKE ? OR LOWER(description) LIKE ? OR LOWER(category) LIKE ? LIMIT 15", (f"%{q}%", f"%{q}%", f"%{q}%")).fetchall()
        if not rows:
            return await safe_reply(event, UITheme.warning("لا توجد نتائج", f"لم يتم العثور على باقات مطابقة لـ <code>{text}</code>."), buttons=[[Button.inline(t['back'], b'personal_section')]])
        btn = [[Button.inline(f"{nm} — ${pr:.0f} (المتاح: {st})", f"show_plan_{pid}_1".encode())] for pid, nm, pr, st in rows]
        btn.append([Button.inline(t['back'], b'personal_section')])
        await safe_reply(event, UITheme.header(f"نتائج البحث عن: {text}", "product", "products"), buttons=btn)
        return

    # البحث عن دولة للباقة
    elif SessionManager.has(uid, f'search_country_for_{uid}'):
        pid = SessionManager.pop(uid, f'search_country_for_{uid}')
        q = text.lower().strip()
        canonical = COUNTRY_ALIASES.get(q, text)
        matches = [c for c in COUNTRIES_DATA if q in c['name'].lower() or canonical.lower() in c['name'].lower()]
        if not matches:
            return await safe_reply(event, UITheme.warning("الدولة غير موجودة", f"لم يتم العثور على دولة مطابقة لـ <code>{text}</code>."), buttons=[[Button.inline(t['back'], f'pick_country_{pid}_0'.encode())]])
        btn = [[Button.inline(f"{c['flag']} {c['name']} ({c['operators']})", f"set_plan_country_{pid}_{c['name']}".encode())] for c in matches[:10]]
        btn.append([Button.inline(t['back'], f'pick_country_{pid}_0'.encode())])
        await safe_reply(event, UITheme.header(f"نتائج البحث عن دولة: {text}", "countries_globe", "countries"), buttons=btn)
        return

    # شحن المحفظة
    elif SessionManager.has(uid, f'charge_amount_prompt_{uid}'):
        SessionManager.remove(uid, f'charge_amount_prompt_{uid}')
        try:
            amount = float(text)
            if amount < 20:
                await safe_reply(event, UITheme.warning("الحد الأدنى للشحن", t['min_charge_err']))
                SessionManager.set(uid, f'charge_amount_prompt_{uid}', True)
                return
            SessionManager.set(uid, f'charging_amount_{uid}', amount)
            networks = cur.execute("SELECT network_name, address, binance_id FROM binance_networks").fetchall()
            details_text = t['show_all_payments_title'].replace("$amount", str(amount)) + "\n\n"
            for idx, (n_name, n_addr, n_id) in enumerate(networks, 1):
                details_text += f"<blockquote><b>{idx}. {n_name}</b>\n"
                if n_id:
                    details_text += f"• <b>ID:</b> <code>{n_id}</code>\n"
                if n_addr:
                    details_text += f"• <b>Address:</b> <code>{n_addr}</code>\n"
                details_text += "</blockquote>\n"
            details_text += t['show_all_payments_footer']
            btn = [
                [Button.inline(t['btn_verify_now'], b'verify_payment_menu')],
                [Button.inline(t['back'], b'wallet')]
            ]
            await safe_reply(event, details_text, buttons=btn)
        except Exception:
            await safe_reply(event, UITheme.error("قيمة غير صالحة", t['invalid_number_err']))
            SessionManager.set(uid, f'charge_amount_prompt_{uid}', True)
        return

    elif SessionManager.has(uid, f'verify_payment_{uid}'):
        SessionManager.remove(uid, f'verify_payment_{uid}')
        await safe_reply(event, UITheme.pending("جاري مراجعة الإيصال", t['verify_sent']), buttons=[[Button.inline(t['back'], b'wallet')]])
        u = await event.sender
        uname = f"@{u.username}" if u and u.username else "بدون معرف"
        fname = u.first_name if u else "مستخدم"
        dep_amt = SessionManager.pop(uid, f'charging_amount_{uid}') or 20.0
        admin_msg = UITheme.header("طلب تحقق من إيصال دفع", "receipt", "payments") + (
            f"\n\n<blockquote>• <b>العميل:</b> {fname} ({uname})\n"
            f"• <b>الآيدي:</b> <code>{uid}</code>\n"
            f"• <b>المبلغ المطلوب:</b> <code>${dep_amt:.2f}</code>\n"
            f"• <b>البيان:</b> {text if text else 'صورة مرفقة'}</blockquote>"
        )
        admin_btns = [
            [Button.inline("قبول وشحن الرصيد", f"admin_approve_dep_{uid}_{dep_amt}".encode()),
             Button.inline("رفض الإيصال", f"admin_reject_dep_{uid}".encode())]
        ]
        if event.media:
            await safe_send(DEV_ID, admin_msg, buttons=admin_btns, file=event.media)
        else:
            await safe_send(DEV_ID, admin_msg, buttons=admin_btns)
        return

    elif SessionManager.has(uid, f'support_ticket_{uid}'):
        SessionManager.remove(uid, f'support_ticket_{uid}')
        await safe_reply(event, UITheme.success("تم إرسال التذكرة", t['support_sent']), buttons=[[Button.inline(t['back'], b'main')]])
        await safe_send(DEV_ID, UITheme.header(f"تذكرة دعم من: {uid}", "ticket", "support") + f"\n\n<blockquote>{text}</blockquote>")
        return

    # أوامر الأدمن: تعيين Custom Emoji ID
    elif SessionManager.has(uid, f'adm_emo_input_{uid}') and is_admin(uid):
        info = SessionManager.pop(uid, f'adm_emo_input_{uid}')
        cat, key = info["cat"], info["key"]
        ok, msg = emoji_mgr.set_id(cat, key, text, db_conn=conn)
        res_html = UITheme.success("تم التحديث", f"{msg}\n{ce(key, cat)}<code>{key}</code>") if ok else UITheme.error("خطأ في المعرف", msg)
        await safe_reply(event, res_html, buttons=[[Button.inline("العودة للتصنيف", f"adm_emo_cat_{cat}".encode())]])
        return

    # أوامر الأدمن: بحث مستخدم
    elif SessionManager.has(uid, f'adm_user_search_{uid}') and is_admin(uid):
        SessionManager.remove(uid, f'adm_user_search_{uid}')
        if not text.isdigit():
            return await safe_reply(event, UITheme.error("صيغة خاطئة", "يرجى إرسال رقم الآيدي الصحيح للمستخدم."), buttons=[[Button.inline(t['back'], b'adm_users_mgr_0')]])
        tid = int(text)
        bal = get_wallet_balance(tid)
        mem = get_membership_info(tid, 'ar')
        await safe_reply(
            event,
            UITheme.header(f"نتيجة البحث: {tid}", "users", "admin") + f"\n\n<blockquote>• <b>الرصيد:</b> <code>${bal:.2f}</code>\n• <b>العضوية:</b> <b>{mem['tier']}</b></blockquote>",
            buttons=[[Button.inline("فتح الملف الكامل", f"adm_user_det_{tid}".encode())], [Button.inline(t['back'], b'adm_users_mgr_0')]]
        )
        return

    # أوامر الأدمن: إضافة شريحة جديدة
    elif SessionManager.has(uid, f'adm_add_plan_input_{uid}') and is_admin(uid):
        SessionManager.remove(uid, f'adm_add_plan_input_{uid}')
        try:
            parts = [x.strip() for x in text.split('|')]
            cat, name, price, mins, months, stock, is_dlr, desc = parts
            code_key = f"{cat}_{secrets.token_hex(3)}"
            cur.execute("""INSERT INTO esims 
                (category, name, code_key, price_usd, minutes, months, stock, min_qty, is_dealer, description)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (cat, name, code_key, float(price), int(mins), int(months), int(stock), 1, int(is_dlr), desc))
            conn.commit()
            await safe_reply(event, UITheme.success("تمت الإضافة", f"تمت إضافة الشريحة <b>{name}</b> إلى القسم <code>{cat}</code>."), buttons=[[Button.inline("إدارة الشرائح", b'adm_plans_mgr_0')]])
        except Exception as e:
            await safe_reply(event, UITheme.error("خطأ أثناء الإضافة", f"تأكد من الصيغة المطلوبة: <code>{e}</code>"))

    # أوامر الأدمن: إضافة قسم جديد
    elif SessionManager.has(uid, f'adm_new_cat_{uid}') and is_admin(uid):
        SessionManager.remove(uid, f'adm_new_cat_{uid}')
        try:
            slug, nar, nen = [x.strip() for x in text.split('|')]
            cur.execute("INSERT OR REPLACE INTO categories (slug, name_ar, name_en, is_visible) VALUES (?, ?, ?, 1)", (slug, nar, nen))
            conn.commit()
            await safe_reply(event, UITheme.success("تمت إضافة القسم", f"تمت إضافة القسم <b>{nar}</b> بنجاح."), buttons=[[Button.inline("إدارة الأقسام", b'adm_cats_mgr')]])
        except Exception as e:
            await safe_reply(event, UITheme.error("خطأ بالصيغة", str(e)))

    # أوامر الأدمن: تعديل سعر شريحة
    elif SessionManager.has(uid, f'action_plan_price_{uid}') and is_admin(uid):
        SessionManager.remove(uid, f'action_plan_price_{uid}')
        pid = SessionManager.get(uid, f'target_plan_id_{uid}')
        try:
            pr = float(text)
            cur.execute("UPDATE esims SET price_usd=? WHERE id=?", (pr, pid))
            conn.commit()
            await safe_reply(event, UITheme.success("تم تحديث السعر", f"السعر الجديد: <code>${pr:.2f}</code>."), buttons=[[Button.inline("إدارة الشرائح", b'adm_plans_mgr_0')]])
        except Exception:
            await safe_reply(event, UITheme.error("قيمة خاطئة", "يرجى إرسال رقم صحيح."))

    # أوامر الأدمن: تعديل مخزون شريحة
    elif SessionManager.has(uid, f'action_plan_stock_{uid}') and is_admin(uid):
        SessionManager.remove(uid, f'action_plan_stock_{uid}')
        pid = SessionManager.get(uid, f'target_plan_id_{uid}')
        try:
            st = int(text)
            cur.execute("UPDATE esims SET stock=? WHERE id=?", (st, pid))
            conn.commit()
            await safe_reply(event, UITheme.success("تم تحديث المخزون", f"المخزون الجديد: <code>{st}</code> قطعة."), buttons=[[Button.inline("إدارة الشرائح", b'adm_plans_mgr_0')]])
        except Exception:
            await safe_reply(event, UITheme.error("قيمة خاطئة", "يرجى إرسال رقم صحيح."))

    # أوامر الأدمن: إضافة وسيلة دفع
    elif SessionManager.has(uid, f'adm_new_pay_{uid}') and is_admin(uid):
        SessionManager.remove(uid, f'adm_new_pay_{uid}')
        try:
            parts = [x.strip() for x in text.split('|')]
            name = parts[0]
            addr = parts[1] if len(parts) > 1 else ""
            bid = parts[2] if len(parts) > 2 else ""
            k = f"pay_{secrets.token_hex(4)}"
            cur.execute("INSERT OR REPLACE INTO binance_networks (network_key, network_name, address, binance_id) VALUES (?, ?, ?, ?)", (k, name, addr, bid))
            conn.commit()
            await safe_reply(event, UITheme.success("تمت الإضافة", f"تمت إضافة وسيلة الدفع <b>{name}</b> بنجاح."), buttons=[[Button.inline("إدارة طرق الدفع", b'adm_pay_mgr')]])
        except Exception as e:
            await safe_reply(event, UITheme.error("خطأ", str(e)))

    elif SessionManager.has(uid, f'adm_pay_set_addr_{uid}') and is_admin(uid):
        SessionManager.remove(uid, f'adm_pay_set_addr_{uid}')
        k = SessionManager.get(uid, f'target_pay_key_{uid}')
        cur.execute("UPDATE binance_networks SET address=? WHERE network_key=?", (text, k))
        conn.commit()
        await safe_reply(event, UITheme.success("تم التحديث", "تم تحديث العنوان بنجاح."), buttons=[[Button.inline("إدارة طرق الدفع", b'adm_pay_mgr')]])

    elif SessionManager.has(uid, f'adm_pay_set_id_{uid}') and is_admin(uid):
        SessionManager.remove(uid, f'adm_pay_set_id_{uid}')
        k = SessionManager.get(uid, f'target_pay_key_{uid}')
        cur.execute("UPDATE binance_networks SET binance_id=? WHERE network_key=?", (text, k))
        conn.commit()
        await safe_reply(event, UITheme.success("تم التحديث", "تم تحديث الـ ID بنجاح."), buttons=[[Button.inline("إدارة طرق الدفع", b'adm_pay_mgr')]])

    # الرصيد والمخزون والإذاعة
    elif SessionManager.has(uid, f'add_balance_{uid}') and is_admin(uid):
        SessionManager.remove(uid, f'add_balance_{uid}')
        try:
            target_uid, amt = text.split()
            update_wallet(int(target_uid), float(amt), 'admin_deposit', "إضافة رصيد بواسطة الأدمن")
            await safe_reply(event, UITheme.success("تمت إضافة الرصيد", f"تمت إضافة <code>${float(amt):.2f}</code> إلى محفظة <code>{target_uid}</code>."), buttons=[[Button.inline("لوحة التحكم", b'admin_panel')]])
            try:
                await safe_send(int(target_uid), UITheme.success("شحن رصيد", f"تمت إضافة مبلغ <code>${float(amt):.2f}</code> إلى محفظتك."))
            except Exception:
                pass
        except Exception:
            await safe_reply(event, UITheme.error("صيغة خاطئة", "مثال: <code>123456789 50</code>"))

    elif SessionManager.has(uid, f'sub_balance_{uid}') and is_admin(uid):
        SessionManager.remove(uid, f'sub_balance_{uid}')
        try:
            target_uid, amt = text.split()
            update_wallet(int(target_uid), -float(amt), 'admin_withdraw', "خصم رصيد بواسطة الأدمن")
            await safe_reply(event, UITheme.success("تم خصم الرصيد", f"تم خصم <code>${float(amt):.2f}</code> من محفظة <code>{target_uid}</code>."), buttons=[[Button.inline("لوحة التحكم", b'admin_panel')]])
        except Exception:
            await safe_reply(event, UITheme.error("صيغة خاطئة", "مثال: <code>123456789 20</code>"))

    elif SessionManager.has(uid, f'zero_balance_{uid}') and is_admin(uid):
        SessionManager.remove(uid, f'zero_balance_{uid}')
        try:
            target_uid = int(text)
            bal = get_wallet_balance(target_uid)
            if bal > 0:
                update_wallet(target_uid, -bal, 'admin_zero', "تصفير الرصيد")
            await safe_reply(event, UITheme.success("تم التصفير", f"تم تصفير رصيد المستخدم <code>{target_uid}</code>."), buttons=[[Button.inline("لوحة التحكم", b'admin_panel')]])
        except Exception:
            await safe_reply(event, UITheme.error("آيدي خاطئ", "أرسل آيدي صحيح."))

    elif SessionManager.has(uid, f'add_stock_{uid}') and is_admin(uid):
        SessionManager.remove(uid, f'add_stock_{uid}')
        try:
            cur.execute("UPDATE esims SET stock = stock + ?", (int(text),))
            conn.commit()
            await safe_reply(event, UITheme.success("تم تحديث المخزون", f"تمت إضافة <code>{text}</code> إلى المخزون بنجاح."), buttons=[[Button.inline("لوحة التحكم", b'admin_panel')]])
        except Exception:
            await safe_reply(event, UITheme.error("قيمة خاطئة", "أرسل رقماً صحيحاً."))

    elif SessionManager.has(uid, f'manage_bans_{uid}') and is_admin(uid):
        SessionManager.remove(uid, f'manage_bans_{uid}')
        try:
            tid = int(text)
            if is_banned(tid):
                cur.execute("DELETE FROM bans WHERE user_id=?", (tid,))
                ban_cache.pop(tid, None)
                msg = f"تم فك حظر المستخدم <code>{tid}</code>."
            else:
                cur.execute("INSERT OR REPLACE INTO bans (user_id) VALUES (?)", (tid,))
                ban_cache[tid] = True
                msg = f"تم حظر المستخدم <code>{tid}</code>."
            conn.commit()
            await safe_reply(event, UITheme.success("تحديث الحظر", msg), buttons=[[Button.inline("لوحة التحكم", b'admin_panel')]])
        except Exception:
            await safe_reply(event, UITheme.error("آيدي خاطئ", "أرسل آيدي صحيح."))

    elif SessionManager.has(uid, f'broadcast_{uid}') and is_admin(uid):
        SessionManager.remove(uid, f'broadcast_{uid}')
        users = cur.execute("SELECT user_id FROM users_settings").fetchall()
        succ, fail = 0, 0
        status_msg = await safe_reply(event, UITheme.pending("جاري الإذاعة", "يتم إرسال الرسالة إلى المستخدمين..."))
        b_text = UITheme.header("إعلان رسمي من Aura eSIM", "broadcast", "admin") + f"\n\n<blockquote>{text}</blockquote>"
        for (u_id,) in users:
            try:
                await safe_send(u_id, b_text)
                succ += 1
                await asyncio.sleep(0.04)
            except errors.FloodWaitError as e:
                await asyncio.sleep(e.seconds)
                try:
                    await safe_send(u_id, b_text)
                    succ += 1
                except Exception:
                    fail += 1
            except Exception:
                fail += 1
        plain_done, ent_done = render_html_entities(UITheme.success("اكتملت الإذاعة", f"• <b>نجاح:</b> <code>{succ}</code>\n• <b>فشل:</b> <code>{fail}</code>"))
        await status_msg.edit(plain_done, formatting_entities=ent_done)


# ==========================================
# 9. نقطة البداية
# ==========================================
async def main():
    await client.start(bot_token=BOT_TOKEN)
    logger.info("Aura eSIM Elite Premium Bot running smoothly.")
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
