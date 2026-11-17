# ==============================================================================
# 1. Imports
# ==============================================================================
import asyncio
import base64
import csv
import hashlib
import inspect
import io
import json
import logging
import os
import re
import secrets
import sqlite3
import sys
import time
import zipfile
from dataclasses import dataclass
from datetime import datetime, timedelta

import aiohttp
from cryptography.fernet import Fernet
from dotenv import load_dotenv
from pyrogram import Client, enums, filters
from pyrogram.errors import BadRequest, FloodWait, MessageNotModified
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# ==============================================================================
# 2. Constants
# ==============================================================================
load_dotenv()

DEFAULT_LPA = os.getenv(
    "DEFAULT_LPA",
    "LPA:1$hfy.prod.ondemandconnectivity.com$FA1BEB0FB081104C79BAD7E29424A4101C6BD12873E8733BD856AFF7A7B6DECC",
)
DEFAULT_BARCODE = f"https://api.qrserver.com/v1/create-qr-code/?data={DEFAULT_LPA}&size=500x500"
CHANNEL_ID = int(os.getenv("CHANNEL_ID", "-1003968712197") or -1003968712197)

ROLE_LEVELS = {"user": 1, "vip": 2, "dealer": 3, "moderator": 4, "developer": 5, "owner": 6}
LOYALTY_TIERS = [(0, "Bronze", 0), (500, "Silver", 3), (1500, "Gold", 5), (5000, "Platinum", 10)]

DEFAULT_CATEGORIES = [
    ("vodafone", "باقات Vodafone (اتصال + إنترنت)", "Vodafone Plans", 1),
    ("holafly", "باقات Holafly (إنترنت لا محدود)", "Holafly Plans", 1),
    ("maya", "باقات Maya (سياسة استخدام عادل)", "Maya Plans", 1),
    ("dealer_vf", "باقات Vodafone تجار (10 شرائح)", "Vodafone Dealer Plans", 1),
    ("dealer_hf", "باقات Holafly تجار (10 شرائح)", "Holafly Dealer Plans", 1),
    ("dealer_maya", "باقات Maya تجار (10 شرائح)", "Maya Dealer Plans", 1),
]

DEFAULT_NETWORKS = [
    ("binance_id", "Binance ID / Pay ID", "", ""),
    ("bybit_id", "Bybit ID", "", "159349409"),
    ("usdt_bep20", "USDT (BEP20 / BSC)", "0x334c55fe51757ac79a3d290523298bd5d327df64", ""),
    ("usdt_aptos", "USDT (APTOS)", "0xb53e2bab33e422673b7b1d6c1e18731628d1cf965965355973d9d2bef5465230", ""),
    ("usdt_trc20", "USDT (TRC20)", "TM5SqP85qKa9pait6DkqCPDcr3hDNJmDGd", ""),
    ("usdt_erc20", "USDT (ERC20)", "0x334c55fe51757ac79a3d290523298bd5d327df64", ""),
    ("usdc_aptos", "USDC (APTOS)", "", ""),
    ("usdc_polygon", "USDC (Polygon)", "", ""),
    ("ton", "TON & GRAM", "", ""),
    ("ltc", "Litecoin (LTC)", "LRbz7QkKmQ9ASjkAuJSD5eYbziApzidZ9b", ""),
]

DEFAULT_PLANS = [
    ("vodafone", "Vodafone Unlimited 1 Month", "vf_1m", 20.0, 850, 1, 765, 1, 0, "بيانات لا محدودة + 850 دقيقة اتصال"),
    ("vodafone", "Vodafone Unlimited 3 Months", "vf_3m", 35.0, 1600, 3, 765, 1, 0, "بيانات لا محدودة + 1600 دقيقة اتصال"),
    ("vodafone", "Vodafone Unlimited 6 Months", "vf_6m", 60.0, 2300, 6, 454, 1, 0, "بيانات لا محدودة + 2300 دقيقة اتصال"),
    ("vodafone", "Vodafone Unlimited 12 Months", "vf_12m", 80.0, 3700, 12, 864, 1, 0, "بيانات لا محدودة + 3700 دقيقة اتصال"),
    ("holafly", "Holafly Unlimited 1 Month", "hf_1m", 15.0, 0, 1, 778, 1, 0, "هولافلاي إنترنت لا محدود بالكامل - بدون استخدام عادل"),
    ("holafly", "Holafly Unlimited 3 Months", "hf_3m", 30.0, 0, 3, 876, 1, 0, "هولافلاي إنترنت لا محدود بالكامل - بدون استخدام عادل"),
    ("holafly", "Holafly Unlimited 6 Months", "hf_6m", 50.0, 0, 6, 446, 1, 0, "هولافلاي إنترنت لا محدود بالكامل - بدون استخدام عادل"),
    ("holafly", "Holafly Unlimited 12 Months", "hf_12m", 70.0, 0, 12, 654, 1, 0, "هولافلاي إنترنت لا محدود بالكامل - بدون استخدام عادل"),
    ("maya", "Maya Unlimited 1 Month", "maya_1m", 12.0, 0, 1, 455, 1, 0, "مايا بيانات لا محدودة - تخضع للاستخدام العادل 5 جيجا يومياً"),
    ("maya", "Maya Unlimited 3 Months", "maya_3m", 25.0, 0, 3, 754, 1, 0, "مايا بيانات لا محدودة - تخضع للاستخدام العادل 5 جيجا يومياً"),
    ("dealer_hf", "Holafly 10 شرائح - 1 شهر", "dealer_hf_1m", 100.0, 0, 1, 234, 10, 1, "عرض 10 شرائح هولافلاي لمدة 1 شهر"),
    ("dealer_hf", "Holafly 10 شرائح - 3 أشهر", "dealer_hf_3m", 130.0, 0, 3, 365, 10, 1, "عرض 10 شرائح هولافلاي لمدة 3 أشهر"),
    ("dealer_hf", "Holafly 10 شرائح - 6 أشهر", "dealer_hf_6m", 150.0, 0, 6, 975, 10, 1, "عرض 10 شرائح هولافلاي لمدة 6 أشهر"),
    ("dealer_hf", "Holafly 10 شرائح - 12 شهر", "dealer_hf_12m", 180.0, 0, 12, 356, 10, 1, "عرض 10 شرائح هولافلاي لمدة 12 شهر"),
    ("dealer_vf", "Vodafone 10 شرائح - 1 شهر", "dealer_vf_1m", 120.0, 850, 1, 344, 10, 1, "عرض 10 شرائح فودافون لمدة 1 شهر (850 دقيقة لكل شريحة)"),
    ("dealer_vf", "Vodafone 10 شرائح - 3 أشهر", "dealer_vf_3m", 150.0, 1600, 3, 324, 10, 1, "عرض 10 شرائح فودافون لمدة 3 أشهر (1600 دقيقة لكل شريحة)"),
    ("dealer_vf", "Vodafone 10 شرائح - 6 أشهر", "dealer_vf_6m", 170.0, 2300, 6, 645, 10, 1, "عرض 10 شرائح فودافون لمدة 6 أشهر (2300 دقيقة لكل شريحة)"),
    ("dealer_vf", "Vodafone 10 شرائح - 12 شهر", "dealer_vf_12m", 220.0, 3700, 12, 345, 10, 1, "عرض 10 شرائح فودافون لمدة 3700 دقيقة لكل شريحة"),
    ("dealer_maya", "Maya 10 شرائح - 1 شهر", "dealer_maya_1m", 90.0, 0, 1, 354, 10, 1, "عرض 10 شرائح مايا لمدة 1 شهر"),
    ("dealer_maya", "Maya 10 شرائح - 3 أشهر", "dealer_maya_3m", 120.0, 0, 3, 345, 10, 1, "عرض 10 شرائح مايا لمدة 3 أشهر"),
]

# ==============================================================================
# 3. Configuration
# ==============================================================================
API_ID = 20867472
API_HASH = "abedd7fb77eaf1f88bd3f286ea952253"
BOT_TOKEN = "8095468555:AAGE__Qf3hEOKY0deVsGgzHjPLvFCTAmhUY"
DEV_ID = 115431561

OPENROUTER_API_KEY = "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"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

DEFAULT_LPA = "LPA:1$hfy.prod.ondemandconnectivity.com$FA1BEB0FB081104C79BAD7E29424A4101C6BD12873E8733BD856AFF7A7B6DECC"

DB_PATH = os.getenv("DB_PATH", "esim_market.db").strip()
BACKUP_SECRET = os.getenv("BACKUP_SECRET", "").strip()
WELCOME_BANNER_URL = os.getenv("WELCOME_BANNER_URL", "").strip()

LANGS = {
    "ar": {
        "welcome_sub": "البوابة الرقمية الفاخرة لخدمات الاتصال والإنترنت العالمي Aura eSIM Elite.",
        "lang_changed": "تم تحويل اللغة بنجاح إلى العربية.",
        "btn_personal": "قسم الأفراد",
        "btn_dealer": "قسم التجار (خصم 50%)",
        "btn_dealer_api": "تفعيل نظام الـ API ($100)",
        "btn_countries": "الدول المدعومة",
        "btn_search_plans": "بحث وتصفية",
        "btn_compare": "مقارنة الباقات",
        "btn_cart": "سلة المشتريات",
        "btn_wallet": "المحفظة",
        "btn_transactions": "سجل المعاملات",
        "btn_orders": "طلباتي",
        "btn_vip": "العضوية والولاء",
        "btn_referrals": "الإحالات والأرباح",
        "btn_ai": "المساعد الذكي AI",
        "btn_support": "الدعم الفني",
        "btn_verify_payment": "التحقق من الدفع",
        "btn_admin": "لوحة الإدارة",
        "btn_lang": "الإعدادات واللغة",
        "back": "رجوع",
        "home": "الرئيسية",
        "prev_page": "السابق",
        "next_page": "التالي",
        "insufficient_balance": "رصيدك غير كافٍ لإتمام العملية. يرجى شحن المحفظة أولاً.",
        "type_country": "اختيار دولة محددة",
        "search_country_btn": "بحث عن دولة",
        "search_prompt": "أرسل اسم الدولة للبحث (بالعربية أو الإنجليزية):",
        "min_charge_err": "الحد الأدنى لعملية الشحن هو $20.",
        "invalid_number_err": "يرجى إدخال رقم صحيح وموجب.",
        "verify_sent": "تم استلام إيصالك بنجاح، وجاري مراجعته وتفعيل الرصيد فور التحقق.",
        "support_sent": "تم إنشاء تذكرة الدعم بنجاح وسيتم الرد عليك قريباً.",
    },
    "en": {
        "welcome_sub": "Luxury Global Connectivity & Digital eSIM Gateway — Aura eSIM Elite.",
        "lang_changed": "Language switched to English.",
        "btn_personal": "Personal Plans",
        "btn_dealer": "Dealers (50% OFF)",
        "btn_dealer_api": "Activate API ($100)",
        "btn_countries": "Countries",
        "btn_search_plans": "Search & Filter",
        "btn_compare": "Compare Plans",
        "btn_cart": "Shopping Cart",
        "btn_wallet": "Wallet",
        "btn_transactions": "Transactions",
        "btn_orders": "My Orders",
        "btn_vip": "VIP & Loyalty",
        "btn_referrals": "Referrals",
        "btn_ai": "AI Assistant",
        "btn_support": "Support",
        "btn_verify_payment": "Verify Payment",
        "btn_admin": "Admin Panel",
        "btn_lang": "Settings & Language",
        "back": "Back",
        "home": "Home",
        "prev_page": "Previous",
        "next_page": "Next",
        "insufficient_balance": "Insufficient wallet balance. Please top up first.",
        "type_country": "Choose Country",
        "search_country_btn": "Search Country",
        "search_prompt": "Send the country name to search (Arabic or English):",
        "min_charge_err": "Minimum deposit amount is $20.",
        "invalid_number_err": "Please enter a valid positive number.",
        "verify_sent": "Your receipt has been received and is under review.",
        "support_sent": "Support ticket created successfully. We will reply soon.",
    },
}

WARRANTY_POLICY_TEXT = {
    "ar": (
        "• Holafly: إنترنت لا محدود بالكامل بدون سياسة استخدام عادل.\n"
        "• Maya: 5 جيجا يومياً بسرعة 5G ثم إنترنت لا محدود.\n"
        "• Vodafone: إنترنت فائق السرعة + دقائق اتصال رسمية.\n"
        "• الضمان الذهبي: دعم 24/7 وتعويض فوري ومرونة تفعيل لمدة 3 أشهر."
    ),
    "en": (
        "• Holafly: True unlimited data with zero FUP.\n"
        "• Maya: 5GB/day at 5G speed, then unlimited data.\n"
        "• Vodafone: High-speed data + official calling minutes.\n"
        "• Golden Warranty: 24/7 support, instant replacement, 3-month activation window."
    ),
}

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

# ==============================================================================
# 4. Premium Emojis Registry (132 Real IDs — Dzgjhv_by_fStikBot)
# ==============================================================================
PREMIUM_EMOJIS = {
    "name_1": {"order": 1, "id": 5821216914277407955, "pack": "Dzgjhv_by_fStikBot"},
    "name_2": {"order": 2, "id": 5821252107239432214, "pack": "Dzgjhv_by_fStikBot"},
    "name_3": {"order": 3, "id": 5821043273044598078, "pack": "Dzgjhv_by_fStikBot"},
    "name_4": {"order": 4, "id": 5821279685224439007, "pack": "Dzgjhv_by_fStikBot"},
    "name_5": {"order": 5, "id": 5821263433068191952, "pack": "Dzgjhv_by_fStikBot"},
    "name_6": {"order": 6, "id": 5821345840605702263, "pack": "Dzgjhv_by_fStikBot"},
    "name_7": {"order": 7, "id": 5821333887711715026, "pack": "Dzgjhv_by_fStikBot"},
    "name_8": {"order": 8, "id": 5821047031140982492, "pack": "Dzgjhv_by_fStikBot"},
    "name_9": {"order": 9, "id": 5821381596208442982, "pack": "Dzgjhv_by_fStikBot"},
    "name_10": {"order": 10, "id": 5821054289635713609, "pack": "Dzgjhv_by_fStikBot"},
    "name_11": {"order": 11, "id": 5821258296287306064, "pack": "Dzgjhv_by_fStikBot"},
    "name_12": {"order": 12, "id": 5818898602600179065, "pack": "Dzgjhv_by_fStikBot"},
    "name_13": {"order": 13, "id": 5821008762982374370, "pack": "Dzgjhv_by_fStikBot"},
    "name_14": {"order": 14, "id": 5820913741125918995, "pack": "Dzgjhv_by_fStikBot"},
    "name_15": {"order": 15, "id": 5821087463963107332, "pack": "Dzgjhv_by_fStikBot"},
    "name_16": {"order": 16, "id": 5821249942575915020, "pack": "Dzgjhv_by_fStikBot"},
    "name_17": {"order": 17, "id": 5821443697140571881, "pack": "Dzgjhv_by_fStikBot"},
    "name_18": {"order": 18, "id": 5821145287107814416, "pack": "Dzgjhv_by_fStikBot"},
    "name_19": {"order": 19, "id": 5818939194336093267, "pack": "Dzgjhv_by_fStikBot"},
    "name_20": {"order": 20, "id": 5821193987741982007, "pack": "Dzgjhv_by_fStikBot"},
    "name_21": {"order": 21, "id": 5821371709193728219, "pack": "Dzgjhv_by_fStikBot"},
    "name_22": {"order": 22, "id": 5821314375675289496, "pack": "Dzgjhv_by_fStikBot"},
    "name_23": {"order": 23, "id": 5820985510029434595, "pack": "Dzgjhv_by_fStikBot"},
    "name_24": {"order": 24, "id": 5821418958128946756, "pack": "Dzgjhv_by_fStikBot"},
    "name_25": {"order": 25, "id": 5821203329295852905, "pack": "Dzgjhv_by_fStikBot"},
    "name_26": {"order": 26, "id": 5820933248867376015, "pack": "Dzgjhv_by_fStikBot"},
    "name_27": {"order": 27, "id": 5819034963516857210, "pack": "Dzgjhv_by_fStikBot"},
    "name_28": {"order": 28, "id": 5821389481768394531, "pack": "Dzgjhv_by_fStikBot"},
    "name_29": {"order": 29, "id": 5821189980537497728, "pack": "Dzgjhv_by_fStikBot"},
    "name_30": {"order": 30, "id": 5820948680684872178, "pack": "Dzgjhv_by_fStikBot"},
    "name_31": {"order": 31, "id": 5820937466525261491, "pack": "Dzgjhv_by_fStikBot"},
    "name_32": {"order": 32, "id": 5819130006848151354, "pack": "Dzgjhv_by_fStikBot"},
    "name_33": {"order": 33, "id": 5821258369301749145, "pack": "Dzgjhv_by_fStikBot"},
    "name_34": {"order": 34, "id": 5821064666276700121, "pack": "Dzgjhv_by_fStikBot"},
    "name_35": {"order": 35, "id": 5821462745320531390, "pack": "Dzgjhv_by_fStikBot"},
    "name_36": {"order": 36, "id": 5821449297777925435, "pack": "Dzgjhv_by_fStikBot"},
    "name_37": {"order": 37, "id": 5821412880750223726, "pack": "Dzgjhv_by_fStikBot"},
    "name_38": {"order": 38, "id": 5821028244954030035, "pack": "Dzgjhv_by_fStikBot"},
    "name_39": {"order": 39, "id": 5820941220326677367, "pack": "Dzgjhv_by_fStikBot"},
    "name_40": {"order": 40, "id": 5821051802849649505, "pack": "Dzgjhv_by_fStikBot"},
    "name_41": {"order": 41, "id": 5821078328567669361, "pack": "Dzgjhv_by_fStikBot"},
    "name_42": {"order": 42, "id": 5821269136784761126, "pack": "Dzgjhv_by_fStikBot"},
    "name_43": {"order": 43, "id": 5818875160668675339, "pack": "Dzgjhv_by_fStikBot"},
    "name_44": {"order": 44, "id": 5821107787748351616, "pack": "Dzgjhv_by_fStikBot"},
    "name_45": {"order": 45, "id": 5821041048251538991, "pack": "Dzgjhv_by_fStikBot"},
    "name_46": {"order": 46, "id": 5820951618442501699, "pack": "Dzgjhv_by_fStikBot"},
    "name_47": {"order": 47, "id": 5821115059127983626, "pack": "Dzgjhv_by_fStikBot"},
    "name_48": {"order": 48, "id": 5821164507086462135, "pack": "Dzgjhv_by_fStikBot"},
    "name_49": {"order": 49, "id": 5821293270205997323, "pack": "Dzgjhv_by_fStikBot"},
    "name_50": {"order": 50, "id": 5818874864315932263, "pack": "Dzgjhv_by_fStikBot"},
    "name_51": {"order": 51, "id": 5821159353125706420, "pack": "Dzgjhv_by_fStikBot"},
    "name_52": {"order": 52, "id": 5820908806208494841, "pack": "Dzgjhv_by_fStikBot"},
    "name_53": {"order": 53, "id": 5821378353508129982, "pack": "Dzgjhv_by_fStikBot"},
    "name_54": {"order": 54, "id": 5821219010221451423, "pack": "Dzgjhv_by_fStikBot"},
    "name_55": {"order": 55, "id": 5821160499881978957, "pack": "Dzgjhv_by_fStikBot"},
    "name_56": {"order": 56, "id": 5821134369300947655, "pack": "Dzgjhv_by_fStikBot"},
    "name_57": {"order": 57, "id": 5821282713176383543, "pack": "Dzgjhv_by_fStikBot"},
    "name_58": {"order": 58, "id": 5821248529531673387, "pack": "Dzgjhv_by_fStikBot"},
    "name_59": {"order": 59, "id": 5820971907868008475, "pack": "Dzgjhv_by_fStikBot"},
    "name_60": {"order": 60, "id": 5821248404977622237, "pack": "Dzgjhv_by_fStikBot"},
    "name_61": {"order": 61, "id": 5820968501958942971, "pack": "Dzgjhv_by_fStikBot"},
    "name_62": {"order": 62, "id": 5821323115933737139, "pack": "Dzgjhv_by_fStikBot"},
    "name_63": {"order": 63, "id": 5821415225802366842, "pack": "Dzgjhv_by_fStikBot"},
    "name_64": {"order": 64, "id": 5821381037862690125, "pack": "Dzgjhv_by_fStikBot"},
    "name_65": {"order": 65, "id": 5821405463341703486, "pack": "Dzgjhv_by_fStikBot"},
    "name_66": {"order": 66, "id": 5821345518483152730, "pack": "Dzgjhv_by_fStikBot"},
    "name_67": {"order": 67, "id": 5821043663886621989, "pack": "Dzgjhv_by_fStikBot"},
    "name_68": {"order": 68, "id": 5820960513319773473, "pack": "Dzgjhv_by_fStikBot"},
    "name_69": {"order": 69, "id": 5820910034569142173, "pack": "Dzgjhv_by_fStikBot"},
    "name_70": {"order": 70, "id": 5821144840431213623, "pack": "Dzgjhv_by_fStikBot"},
    "name_71": {"order": 71, "id": 5821114092760343220, "pack": "Dzgjhv_by_fStikBot"},
    "name_72": {"order": 72, "id": 5821016266290241179, "pack": "Dzgjhv_by_fStikBot"},
    "name_73": {"order": 73, "id": 5818743206388441259, "pack": "Dzgjhv_by_fStikBot"},
    "name_74": {"order": 74, "id": 5821346815563275280, "pack": "Dzgjhv_by_fStikBot"},
    "name_75": {"order": 75, "id": 5821110283124349896, "pack": "Dzgjhv_by_fStikBot"},
    "name_76": {"order": 76, "id": 5821394614254313093, "pack": "Dzgjhv_by_fStikBot"},
    "name_77": {"order": 77, "id": 5821089263554404420, "pack": "Dzgjhv_by_fStikBot"},
    "name_78": {"order": 78, "id": 5818916890570924432, "pack": "Dzgjhv_by_fStikBot"},
    "name_79": {"order": 79, "id": 5820978801290517601, "pack": "Dzgjhv_by_fStikBot"},
    "name_80": {"order": 80, "id": 5821174557309935357, "pack": "Dzgjhv_by_fStikBot"},
    "name_81": {"order": 81, "id": 5821201615603902576, "pack": "Dzgjhv_by_fStikBot"},
    "name_82": {"order": 82, "id": 5821419421985414304, "pack": "Dzgjhv_by_fStikBot"},
    "name_83": {"order": 83, "id": 5821243740643138862, "pack": "Dzgjhv_by_fStikBot"},
    "name_84": {"order": 84, "id": 5821182795057208280, "pack": "Dzgjhv_by_fStikBot"},
    "name_85": {"order": 85, "id": 5821442563269205711, "pack": "Dzgjhv_by_fStikBot"},
    "name_86": {"order": 86, "id": 5820959216239649192, "pack": "Dzgjhv_by_fStikBot"},
    "name_87": {"order": 87, "id": 5821211365179662293, "pack": "Dzgjhv_by_fStikBot"},
    "name_88": {"order": 88, "id": 5821189100069199409, "pack": "Dzgjhv_by_fStikBot"},
    "name_89": {"order": 89, "id": 5821359120644579596, "pack": "Dzgjhv_by_fStikBot"},
    "name_90": {"order": 90, "id": 5821151660839279305, "pack": "Dzgjhv_by_fStikBot"},
    "name_91": {"order": 91, "id": 5821380621250862919, "pack": "Dzgjhv_by_fStikBot"},
    "name_92": {"order": 92, "id": 5821070576151698828, "pack": "Dzgjhv_by_fStikBot"},
    "name_93": {"order": 93, "id": 5821199566904499551, "pack": "Dzgjhv_by_fStikBot"},
    "name_94": {"order": 94, "id": 5821164644525415971, "pack": "Dzgjhv_by_fStikBot"},
    "name_95": {"order": 95, "id": 5820917735445503171, "pack": "Dzgjhv_by_fStikBot"},
    "name_96": {"order": 96, "id": 5820994529460774328, "pack": "Dzgjhv_by_fStikBot"},
    "name_97": {"order": 97, "id": 5821313628350980704, "pack": "Dzgjhv_by_fStikBot"},
    "name_98": {"order": 98, "id": 5821178461435208778, "pack": "Dzgjhv_by_fStikBot"},
    "name_99": {"order": 99, "id": 5820927223028261716, "pack": "Dzgjhv_by_fStikBot"},
    "name_100": {"order": 100, "id": 5821156522742259761, "pack": "Dzgjhv_by_fStikBot"},
    "name_101": {"order": 101, "id": 5820910678814236476, "pack": "Dzgjhv_by_fStikBot"},
    "name_102": {"order": 102, "id": 5821041799870815043, "pack": "Dzgjhv_by_fStikBot"},
    "name_103": {"order": 103, "id": 5821342666624869467, "pack": "Dzgjhv_by_fStikBot"},
    "name_104": {"order": 104, "id": 5821049324653518756, "pack": "Dzgjhv_by_fStikBot"},
    "name_105": {"order": 105, "id": 5821313843099345687, "pack": "Dzgjhv_by_fStikBot"},
    "name_106": {"order": 106, "id": 5821261779505782286, "pack": "Dzgjhv_by_fStikBot"},
    "name_107": {"order": 107, "id": 5820949007102385442, "pack": "Dzgjhv_by_fStikBot"},
    "name_108": {"order": 108, "id": 5821270347965538665, "pack": "Dzgjhv_by_fStikBot"},
    "name_109": {"order": 109, "id": 5820930044821773175, "pack": "Dzgjhv_by_fStikBot"},
    "name_110": {"order": 110, "id": 5821310226736881553, "pack": "Dzgjhv_by_fStikBot"},
    "name_111": {"order": 111, "id": 5821309195944729332, "pack": "Dzgjhv_by_fStikBot"},
    "name_112": {"order": 112, "id": 5821062304044686573, "pack": "Dzgjhv_by_fStikBot"},
    "name_113": {"order": 113, "id": 5820963661530799816, "pack": "Dzgjhv_by_fStikBot"},
    "name_114": {"order": 114, "id": 5821053825779243824, "pack": "Dzgjhv_by_fStikBot"},
    "name_115": {"order": 115, "id": 5821002165912608413, "pack": "Dzgjhv_by_fStikBot"},
    "name_116": {"order": 116, "id": 5821340678055009764, "pack": "Dzgjhv_by_fStikBot"},
    "name_117": {"order": 117, "id": 5821403771124587795, "pack": "Dzgjhv_by_fStikBot"},
    "name_118": {"order": 118, "id": 5821168892248072347, "pack": "Dzgjhv_by_fStikBot"},
    "name_119": {"order": 119, "id": 5820905846976029428, "pack": "Dzgjhv_by_fStikBot"},
    "name_120": {"order": 120, "id": 5820917933013999485, "pack": "Dzgjhv_by_fStikBot"},
    "name_121": {"order": 121, "id": 5821140146031959501, "pack": "Dzgjhv_by_fStikBot"},
    "name_122": {"order": 122, "id": 5821277232798113131, "pack": "Dzgjhv_by_fStikBot"},
    "name_123": {"order": 123, "id": 5820938853799697551, "pack": "Dzgjhv_by_fStikBot"},
    "name_124": {"order": 124, "id": 5821309316203829784, "pack": "Dzgjhv_by_fStikBot"},
    "name_125": {"order": 125, "id": 5821386239068086115, "pack": "Dzgjhv_by_fStikBot"},
    "name_126": {"order": 126, "id": 5821407314472608413, "pack": "Dzgjhv_by_fStikBot"},
    "name_127": {"order": 127, "id": 5821199734408224452, "pack": "Dzgjhv_by_fStikBot"},
    "name_128": {"order": 128, "id": 5821242233109620582, "pack": "Dzgjhv_by_fStikBot"},
    "name_129": {"order": 129, "id": 5821116493647060108, "pack": "Dzgjhv_by_fStikBot"},
    "name_130": {"order": 130, "id": 5819140331949531448, "pack": "Dzgjhv_by_fStikBot"},
    "name_131": {"order": 131, "id": 5821130323441755836, "pack": "Dzgjhv_by_fStikBot"},
    "name_132": {"order": 132, "id": 5821398350875860780, "pack": "Dzgjhv_by_fStikBot"},
}

EMOJI_CATEGORY_MAP = {
    "home": {"main": "name_53", "welcome": "name_56", "spark": "name_67"},
    "store": {"main": "name_51", "cart": "name_107", "search": "name_55"},
    "products": {"main": "name_30", "signal": "name_31", "stock": "name_1"},
    "countries": {"main": "name_46", "pin": "name_37"},
    "plans": {"main": "name_119", "fast": "name_62"},
    "prices": {"main": "name_68", "discount": "name_25"},
    "wallet": {"main": "name_78", "deposit": "name_63", "withdraw": "name_64"},
    "payments": {"main": "name_124", "verify": "name_52"},
    "orders": {"main": "name_107", "invoice": "name_58"},
    "success": {"main": "name_1", "check": "name_47"},
    "errors": {"main": "name_75", "cross": "name_111"},
    "warnings": {"main": "name_59", "alert": "name_48"},
    "pending": {"main": "name_35", "spin": "name_121"},
    "vip": {"main": "name_91", "medal": "name_77"},
    "premium": {"main": "name_120", "star": "name_26"},
    "dealers": {"main": "name_57", "api": "name_50"},
    "admin": {"main": "name_49", "broadcast": "name_61"},
    "developers": {"main": "name_110", "gear": "name_60"},
    "support": {"main": "name_65", "call": "name_109"},
    "settings": {"main": "name_60", "recycle": "name_126"},
    "stats": {"main": "name_103", "spark": "name_66"},
}


class PremiumEmojiManager:
    def __init__(self):
        self.registry = PREMIUM_EMOJIS
        self.categories = EMOJI_CATEGORY_MAP

    @staticmethod
    def validate_id(raw_val) -> int:
        if raw_val is None or isinstance(raw_val, bool):
            return 0
        s = str(raw_val).strip()
        if not s.isdigit() or len(s) < 10 or int(s) <= 0:
            return 0
        return int(s)

    def get_id(self, category: str, key: str = "main") -> int:
        cat_map = self.categories.get(category, {})
        ref = cat_map.get(key) or cat_map.get("main")
        if ref and ref in self.registry:
            return self.validate_id(self.registry[ref].get("id"))
        return 0

    def tag(self, category: str, key: str = "main") -> str:
        eid = self.get_id(category, key)
        if not eid:
            return ""
        return f'<emoji id="{eid}">✦</emoji>'


emoji_mgr = PremiumEmojiManager()


def ce(category: str, key: str = "main") -> str:
    return emoji_mgr.tag(category, key)


def line(category: str, text: str, key_left: str = "main", key_right: str = None) -> str:
    left = ce(category, key_left)
    right = ce(category, key_right or key_left)
    if left and right:
        return f"{left} {text} {right}"
    return f"{left} {text}".strip() if left else text


_EMOJI_TAG_RE = re.compile(r'<emoji\s+id=["\']?\d+["\']?>(.*?)</emoji>', re.IGNORECASE | re.DOTALL)


def strip_custom_emojis(html_text: str) -> str:
    if not html_text:
        return ""
    cleaned = _EMOJI_TAG_RE.sub("", html_text)
    return re.sub(r"  +", " ", cleaned).strip()


# ==============================================================================
# 5. Logging
# ==============================================================================
logging.basicConfig(
    format="[%(levelname)s] %(asctime)s - %(name)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("AuraESIMBot")


# ==============================================================================
# 6. Database Manager & 7. Database Models & 8. Database Initialization
# ==============================================================================
@dataclass
class PlanModel:
    id: int
    category: str
    name: str
    price_usd: float
    minutes: int
    months: int
    stock: int
    is_dealer: int
    description: str


class DatabaseManager:
    """طبقة قاعدة البيانات المركزية مع دعم المعاملات الذرية والترحيل الآمن."""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.lock = asyncio.Lock()
        self.init_and_migrate()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=15.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA busy_timeout=5000;")
        return conn

    def init_and_migrate(self):
        conn = self.connect()
        try:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS categories (
                    slug TEXT PRIMARY KEY,
                    name_ar TEXT,
                    name_en TEXT,
                    is_visible INTEGER DEFAULT 1
                );
                CREATE TABLE IF NOT EXISTS esims (
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
                );
                CREATE TABLE IF NOT EXISTS wallets (
                    user_id INTEGER PRIMARY KEY,
                    balance REAL DEFAULT 0,
                    total_deposited REAL DEFAULT 0,
                    created_date TEXT
                );
                CREATE TABLE IF NOT EXISTS wallet_transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    type TEXT,
                    amount REAL,
                    balance_after REAL,
                    description TEXT,
                    date TEXT
                );
                CREATE TABLE IF NOT EXISTS orders (
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
                );
                CREATE TABLE IF NOT EXISTS cart (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    esim_id INTEGER,
                    scope TEXT,
                    price REAL
                );
                CREATE TABLE IF NOT EXISTS users_settings (
                    user_id INTEGER PRIMARY KEY,
                    lang TEXT DEFAULT 'ar',
                    referred_by INTEGER,
                    is_dealer_tier INTEGER DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS dealer_api_keys (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER UNIQUE,
                    api_key TEXT UNIQUE,
                    created_date TEXT
                );
                CREATE TABLE IF NOT EXISTS admins (
                    user_id INTEGER PRIMARY KEY
                );
                CREATE TABLE IF NOT EXISTS bans (
                    user_id INTEGER PRIMARY KEY
                );
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                );
                CREATE TABLE IF NOT EXISTS binance_networks (
                    network_key TEXT PRIMARY KEY,
                    network_name TEXT,
                    address TEXT,
                    binance_id TEXT
                );
                CREATE TABLE IF NOT EXISTS user_sessions (
                    user_id INTEGER PRIMARY KEY,
                    state_key TEXT,
                    state_data TEXT,
                    expires_at TEXT
                );

                -- جداول المميزات المتقدمة الجديدة
                CREATE TABLE IF NOT EXISTS coupons (
                    code TEXT PRIMARY KEY,
                    discount_type TEXT DEFAULT 'percent',
                    discount_value REAL DEFAULT 0,
                    max_uses INTEGER DEFAULT 100,
                    used_count INTEGER DEFAULT 0,
                    dealer_only INTEGER DEFAULT 0,
                    new_users_only INTEGER DEFAULT 0,
                    starts_at TEXT DEFAULT '',
                    expires_at TEXT DEFAULT '',
                    is_active INTEGER DEFAULT 1,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS coupon_uses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT NOT NULL,
                    user_id INTEGER NOT NULL,
                    order_id TEXT DEFAULT '',
                    used_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS loyalty_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    points INTEGER NOT NULL,
                    reason TEXT DEFAULT '',
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS referrals_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    referrer_id INTEGER NOT NULL,
                    referred_id INTEGER NOT NULL,
                    reward_usd REAL DEFAULT 0,
                    status TEXT DEFAULT 'credited',
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS support_tickets (
                    ticket_id TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    category TEXT DEFAULT 'general',
                    status TEXT DEFAULT 'open',
                    assigned_to INTEGER DEFAULT 0,
                    rating INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS ticket_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticket_id TEXT NOT NULL,
                    sender_id INTEGER NOT NULL,
                    sender_role TEXT DEFAULT 'user',
                    message TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    actor_id INTEGER DEFAULT 0,
                    category TEXT DEFAULT 'general',
                    action TEXT NOT NULL,
                    target TEXT DEFAULT '',
                    details TEXT DEFAULT '',
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS idempotency_keys (
                    idem_key TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    action TEXT NOT NULL,
                    result_json TEXT DEFAULT '',
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS stock_reservations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    esim_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    qty INTEGER NOT NULL,
                    status TEXT DEFAULT 'held',
                    expires_at TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS pending_payments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    amount REAL NOT NULL,
                    proof TEXT DEFAULT '',
                    status TEXT DEFAULT 'pending',
                    reviewed_by INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS notification_prefs (
                    user_id INTEGER PRIMARY KEY,
                    orders_notif INTEGER DEFAULT 1,
                    promos_notif INTEGER DEFAULT 1,
                    security_notif INTEGER DEFAULT 1
                );

                CREATE INDEX IF NOT EXISTS idx_orders_user ON orders(user_id);
                CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
                CREATE INDEX IF NOT EXISTS idx_orders_date ON orders(created_date);
                CREATE INDEX IF NOT EXISTS idx_wallet_tx_user ON wallet_transactions(user_id);
                CREATE INDEX IF NOT EXISTS idx_tickets_user ON support_tickets(user_id, status);
                CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_logs(created_at);
                """
            )

            # Safe column migrations on existing tables
            user_cols = {r["name"] for r in conn.execute("PRAGMA table_info(users_settings)").fetchall()}
            for col_name, col_def in (
                ("role", "TEXT DEFAULT 'user'"),
                ("loyalty_points", "INTEGER DEFAULT 0"),
                ("loyalty_tier", "TEXT DEFAULT 'Bronze'"),
                ("vip_expires_at", "TEXT DEFAULT ''"),
                ("created_at", "TEXT DEFAULT ''"),
            ):
                if col_name not in user_cols:
                    conn.execute(f"ALTER TABLE users_settings ADD COLUMN {col_name} {col_def}")

            dlr_cols = {r["name"] for r in conn.execute("PRAGMA table_info(dealer_api_keys)").fetchall()}
            for col_name, col_def in (
                ("tier", "TEXT DEFAULT 'Standard'"),
                ("daily_limit", "INTEGER DEFAULT 100"),
                ("webhook_url", "TEXT DEFAULT ''"),
                ("is_active", "INTEGER DEFAULT 1"),
            ):
                if col_name not in dlr_cols:
                    conn.execute(f"ALTER TABLE dealer_api_keys ADD COLUMN {col_name} {col_def}")

            ord_cols = {r["name"] for r in conn.execute("PRAGMA table_info(orders)").fetchall()}
            for col_name, col_def in (
                ("coupon_code", "TEXT DEFAULT ''"),
                ("discount_usd", "REAL DEFAULT 0"),
                ("idempotency_key", "TEXT DEFAULT ''"),
            ):
                if col_name not in ord_cols:
                    conn.execute(f"ALTER TABLE orders ADD COLUMN {col_name} {col_def}")

            # Seed defaults without overwriting existing data
            for slug, nar, nen, vis in DEFAULT_CATEGORIES:
                conn.execute(
                    "INSERT OR IGNORE INTO categories (slug, name_ar, name_en, is_visible) VALUES (?, ?, ?, ?)",
                    (slug, nar, nen, vis),
                )
            for n_key, n_name, n_addr, n_id in DEFAULT_NETWORKS:
                conn.execute(
                    "INSERT OR IGNORE INTO binance_networks (network_key, network_name, address, binance_id) VALUES (?, ?, ?, ?)",
                    (n_key, n_name, n_addr, n_id),
                )
            for cat, name, code, price, mins, months, stock, min_q, is_dlr, desc in DEFAULT_PLANS:
                conn.execute(
                    """INSERT INTO esims
                    (category, name, code_key, price_usd, minutes, months, stock, min_qty, is_dealer, description)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(code_key) DO UPDATE SET
                    minutes=excluded.minutes, description=excluded.description, price_usd=excluded.price_usd""",
                    (cat, name, code, price, mins, months, stock, min_q, is_dlr, desc),
                )
            conn.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (DEV_ID,))
            conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('ai_enabled', '1')")
            conn.commit()
        finally:
            conn.close()

    def get_setting(self, key: str, default: str = "") -> str:
        conn = self.connect()
        try:
            row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
            return row[0] if row else default
        finally:
            conn.close()

    def set_setting(self, key: str, value: str):
        conn = self.connect()
        try:
            conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
            conn.commit()
        finally:
            conn.close()


class SessionManager:
    def __init__(self, db: DatabaseManager):
        self.db = db

    def set(self, uid: int, key: str, data=None):
        expires = (datetime.now() + timedelta(hours=2)).strftime("%Y-%m-%d %H:%M")
        data_str = json.dumps(data, ensure_ascii=False) if data is not None else ""
        conn = self.db.connect()
        try:
            conn.execute(
                "INSERT OR REPLACE INTO user_sessions (user_id, state_key, state_data, expires_at) VALUES (?, ?, ?, ?)",
                (uid, key, data_str, expires),
            )
            conn.commit()
        finally:
            conn.close()

    def get(self, uid: int, key: str):
        conn = self.db.connect()
        try:
            row = conn.execute(
                "SELECT state_data, expires_at FROM user_sessions WHERE user_id=? AND state_key=?",
                (uid, key),
            ).fetchone()
            if not row:
                return None
            data_str, exp_str = row[0], row[1]
            if datetime.now() > datetime.strptime(exp_str, "%Y-%m-%d %H:%M"):
                self.remove(uid, key)
                return None
            return json.loads(data_str) if data_str else True
        finally:
            conn.close()

    def has(self, uid: int, key: str) -> bool:
        return self.get(uid, key) is not None

    def pop(self, uid: int, key: str):
        val = self.get(uid, key)
        self.remove(uid, key)
        return val

    def remove(self, uid: int, key: str):
        conn = self.db.connect()
        try:
            conn.execute("DELETE FROM user_sessions WHERE user_id=? AND state_key=?", (uid, key))
            conn.commit()
        finally:
            conn.close()


db = DatabaseManager()
sessions = SessionManager(db)



# ==============================================================================
# 9. Utilities
# ==============================================================================


# ==============================================================================
# 10-19. Security, User, Product, Payment, Order, Wallet, Merchant, AI, Notify, Admin Services
# ==============================================================================
class SecurityService:
    def __init__(self):
        self._rate_limits = {}
        self._debounce = {}
        self._admin_cache = {}
        self._ban_cache = {}

    def allow_rate(self, uid: int, interval: float = 0.35) -> bool:
        now = time.monotonic()
        last = self._rate_limits.get(uid, 0.0)
        if now - last < interval:
            return False
        self._rate_limits[uid] = now
        return True

    def allow_action(self, uid: int, action: str, cooldown: float = 2.0) -> bool:
        key = (int(uid), str(action))
        now = time.monotonic()
        last = self._debounce.get(key, 0.0)
        if now - last < cooldown:
            return False
        self._debounce[key] = now
        return True

    def get_role(self, uid: int) -> str:
        if uid == DEV_ID:
            return "owner"
        conn = db.connect()
        try:
            adm = conn.execute("SELECT user_id FROM admins WHERE user_id=?", (uid,)).fetchone()
            row = conn.execute("SELECT role, vip_expires_at FROM users_settings WHERE user_id=?", (uid,)).fetchone()
            dlr = conn.execute("SELECT is_active FROM dealer_api_keys WHERE user_id=?", (uid,)).fetchone()
            if row and row["role"] in ("developer", "moderator"):
                return row["role"]
            if adm:
                return "developer"
            if dlr and dlr["is_active"]:
                return "dealer"
            if row and row["vip_expires_at"]:
                try:
                    if datetime.now() < datetime.fromisoformat(row["vip_expires_at"]):
                        return "vip"
                except Exception:
                    pass
            return "user"
        finally:
            conn.close()

    def is_admin(self, uid: int) -> bool:
        if uid == DEV_ID:
            return True
        if uid in self._admin_cache:
            return self._admin_cache[uid]
        role = self.get_role(uid)
        res = role in ("owner", "developer", "moderator")
        self._admin_cache[uid] = res
        return res

    def is_developer(self, uid: int) -> bool:
        return self.get_role(uid) in ("owner", "developer")

    def invalidate_admin_cache(self, uid: int = None):
        if uid is None:
            self._admin_cache.clear()
        else:
            self._admin_cache.pop(uid, None)

    def is_banned(self, uid: int) -> bool:
        if uid == DEV_ID:
            return False
        if uid in self._ban_cache:
            return self._ban_cache[uid]
        conn = db.connect()
        try:
            res = conn.execute("SELECT user_id FROM bans WHERE user_id=?", (uid,)).fetchone() is not None
            self._ban_cache[uid] = res
            return res
        finally:
            conn.close()

    def set_ban(self, actor_id: int, target_uid: int, banned: bool):
        if target_uid == DEV_ID:
            return False, "لا يمكن حظر مالك البوت."
        conn = db.connect()
        try:
            if banned:
                conn.execute("INSERT OR REPLACE INTO bans (user_id) VALUES (?)", (target_uid,))
                self._ban_cache[target_uid] = True
            else:
                conn.execute("DELETE FROM bans WHERE user_id=?", (target_uid,))
                self._ban_cache[target_uid] = False
            conn.commit()
        finally:
            conn.close()
        self.log_audit(actor_id, "security", "ban" if banned else "unban", str(target_uid))
        return True, "تم الحظر بنجاح." if banned else "تم فك الحظر بنجاح."

    def log_audit(self, actor_id: int, category: str, action: str, target: str = "", details: str = ""):
        conn = db.connect()
        try:
            conn.execute(
                "INSERT INTO audit_logs (actor_id, category, action, target, details, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (actor_id, category, action, str(target), str(details)[:500], datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            )
            conn.commit()
        finally:
            conn.close()

    def _fernet_key(self) -> bytes:
        secret = BACKUP_SECRET or f"aura_backup_{DEV_ID}_key"
        digest = hashlib.sha256(secret.encode("utf-8")).digest()
        return base64.urlsafe_b64encode(digest)

    def create_encrypted_backup(self, out_dir: str = "backups") -> tuple:
        os.makedirs(out_dir, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_path = os.path.join(out_dir, f"aura_backup_{ts}.zip")
        enc_path = zip_path + ".enc"
        snap_db = os.path.join(out_dir, f"snap_{ts}.db")
        try:
            # Online SQLite backup snapshot (safe during WAL)
            src_conn = db.connect()
            dst_conn = db.connect() if False else __import__("sqlite3").connect(snap_db)
            src_conn.backup(dst_conn)
            dst_conn.close()
            src_conn.close()

            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.write(snap_db, arcname="esim_market.db")
                ce_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "custom_emojis.json")
                if os.path.exists(ce_path):
                    zf.write(ce_path, arcname="custom_emojis.json")
                manifest = {"created_at": ts, "db_sha256": hashlib.sha256(open(snap_db, "rb").read()).hexdigest()}
                zf.writestr("manifest.json", json.dumps(manifest))

            fernet = Fernet(self._fernet_key())
            with open(zip_path, "rb") as f:
                enc_data = fernet.encrypt(f.read())
            with open(enc_path, "wb") as f:
                f.write(enc_data)
            return True, enc_path
        except Exception as e:
            logger.error(f"Backup error: {e}")
            return False, str(e)
        finally:
            for p in (zip_path, snap_db):
                if os.path.exists(p):
                    try:
                        os.remove(p)
                    except Exception:
                        pass

    def verify_and_restore_backup(self, enc_path: str, test_only: bool = True) -> tuple:
        try:
            fernet = Fernet(self._fernet_key())
            with open(enc_path, "rb") as f:
                raw_zip = fernet.decrypt(f.read())
            bio = io.BytesIO(raw_zip)
            with zipfile.ZipFile(bio, "r") as zf:
                names = zf.namelist()
                if "esim_market.db" not in names or "manifest.json" not in names:
                    return False, "أرشيف النسخة الاحتياطية غير مكتمل."
                manifest = json.loads(zf.read("manifest.json").decode("utf-8"))
                db_bytes = zf.read("esim_market.db")
                if hashlib.sha256(db_bytes).hexdigest() != manifest.get("db_sha256"):
                    return False, "فشل التحقق من سلامة SHA-256 لقاعدة البيانات."
                if not test_only:
                    with open(DB_PATH, "wb") as f:
                        f.write(db_bytes)
            return True, "تم التحقق من سلامة النسخة الاحتياطية المشفرة بنجاح."
        except Exception as e:
            return False, f"فشل فك التشفير أو التحقق: {e}"


class UserService:
    def ensure_user(self, uid: int, lang: str = None, ref_by: int = None):
        now_s = datetime.now().strftime("%Y-%m-%d %H:%M")
        conn = db.connect()
        try:
            row = conn.execute("SELECT user_id, referred_by FROM users_settings WHERE user_id=?", (uid,)).fetchone()
            if not row:
                conn.execute(
                    "INSERT INTO users_settings (user_id, lang, referred_by, created_at) VALUES (?, ?, ?, ?)",
                    (uid, lang or "ar", ref_by if (ref_by and ref_by != uid) else None, now_s),
                )
            elif lang:
                conn.execute("UPDATE users_settings SET lang=? WHERE user_id=?", (lang, uid))
            conn.execute("INSERT OR IGNORE INTO wallets (user_id, created_date) VALUES (?, ?)", (uid, now_s))
            conn.execute("INSERT OR IGNORE INTO notification_prefs (user_id) VALUES (?)", (uid,))
            conn.commit()
        finally:
            conn.close()

    def get_lang(self, uid: int) -> str:
        conn = db.connect()
        try:
            row = conn.execute("SELECT lang FROM users_settings WHERE user_id=?", (uid,)).fetchone()
            return row["lang"] if row and row["lang"] else ""
        finally:
            conn.close()

    def set_lang(self, uid: int, lang: str):
        self.ensure_user(uid, lang=lang)

    def get_wallet_balance(self, uid: int) -> float:
        conn = db.connect()
        try:
            row = conn.execute("SELECT balance FROM wallets WHERE user_id=?", (uid,)).fetchone()
            return float(row["balance"]) if row else 0.0
        finally:
            conn.close()

    def get_loyalty_info(self, uid: int) -> dict:
        conn = db.connect()
        try:
            row = conn.execute("SELECT loyalty_points, loyalty_tier, vip_expires_at FROM users_settings WHERE user_id=?", (uid,)).fetchone()
            pts = int(row["loyalty_points"] or 0) if row else 0
            tier = row["loyalty_tier"] or "Bronze" if row else "Bronze"
            vip_exp = row["vip_expires_at"] or "" if row else ""
            discount_pct = 0
            for min_pts, t_name, disc in LOYALTY_TIERS:
                if pts >= min_pts:
                    tier = t_name
                    discount_pct = disc
            return {"points": pts, "tier": tier, "tier_discount": discount_pct, "vip_expires_at": vip_exp}
        finally:
            conn.close()

    def add_loyalty_points(self, uid: int, points: int, reason: str):
        if points <= 0:
            return
        now_s = datetime.now().strftime("%Y-%m-%d %H:%M")
        conn = db.connect()
        try:
            row = conn.execute("SELECT loyalty_points FROM users_settings WHERE user_id=?", (uid,)).fetchone()
            cur_pts = int(row["loyalty_points"] or 0) if row else 0
            new_pts = cur_pts + points
            new_tier = "Bronze"
            for min_pts, t_name, _ in LOYALTY_TIERS:
                if new_pts >= min_pts:
                    new_tier = t_name
            conn.execute("UPDATE users_settings SET loyalty_points=?, loyalty_tier=? WHERE user_id=?", (new_pts, new_tier, uid))
            conn.execute("INSERT INTO loyalty_history (user_id, points, reason, created_at) VALUES (?, ?, ?, ?)", (uid, points, reason, now_s))
            conn.commit()
        finally:
            conn.close()

    def get_referral_stats(self, uid: int) -> dict:
        conn = db.connect()
        try:
            invited = conn.execute("SELECT COUNT(*) FROM users_settings WHERE referred_by=?", (uid,)).fetchone()[0]
            earnings = conn.execute("SELECT COALESCE(SUM(reward_usd), 0) FROM referrals_log WHERE referrer_id=?", (uid,)).fetchone()[0]
            return {"invited": int(invited), "earnings": float(earnings)}
        finally:
            conn.close()

    def process_referral_reward(self, buyer_uid: int, order_total: float):
        if order_total < 5.0:
            return None
        conn = db.connect()
        try:
            row = conn.execute("SELECT referred_by FROM users_settings WHERE user_id=?", (buyer_uid,)).fetchone()
            if not row or not row["referred_by"]:
                return None
            ref_uid = int(row["referred_by"])
            if ref_uid == buyer_uid:
                return None
            already = conn.execute("SELECT id FROM referrals_log WHERE referred_id=?", (buyer_uid,)).fetchone()
            if already:
                return None
            reward = round(min(10.0, order_total * 0.05), 2)
            now_s = datetime.now().strftime("%Y-%m-%d %H:%M")
            conn.execute("INSERT OR IGNORE INTO wallets (user_id, created_date) VALUES (?, ?)", (ref_uid, now_s))
            conn.execute("UPDATE wallets SET balance=balance+?, total_deposited=total_deposited+? WHERE user_id=?", (reward, reward, ref_uid))
            bal_after = conn.execute("SELECT balance FROM wallets WHERE user_id=?", (ref_uid,)).fetchone()[0]
            conn.execute(
                "INSERT INTO wallet_transactions (user_id, type, amount, balance_after, description, date) VALUES (?, 'referral_reward', ?, ?, ?, ?)",
                (ref_uid, reward, bal_after, f"مكافأة إحالة المستخدم {buyer_uid}", now_s),
            )
            conn.execute(
                "INSERT INTO referrals_log (referrer_id, referred_id, reward_usd, status, created_at) VALUES (?, ?, ?, 'credited', ?)",
                (ref_uid, buyer_uid, reward, now_s),
            )
            conn.commit()
            return {"referrer_id": ref_uid, "reward": reward}
        finally:
            conn.close()


class ProductService:
    def list_categories(self, dealer_only: bool = False, visible_only: bool = True) -> list:
        conn = db.connect()
        try:
            conds = []
            if dealer_only:
                conds.append("slug LIKE 'dealer_%'")
            else:
                conds.append("slug NOT LIKE 'dealer_%'")
            if visible_only:
                conds.append("is_visible=1")
            where = " AND ".join(conds) if conds else "1=1"
            return [dict(r) for r in conn.execute(f"SELECT * FROM categories WHERE {where}").fetchall()]
        finally:
            conn.close()

    def list_plans(self, category: str = None, search: str = None, max_price: float = None, offset: int = 0, limit: int = 50) -> tuple:
        conn = db.connect()
        try:
            conds, params = ["1=1"], []
            if category:
                conds.append("category=?")
                params.append(category)
            if search:
                q = f"%{search.lower()}%"
                conds.append("(LOWER(name) LIKE ? OR LOWER(description) LIKE ? OR LOWER(category) LIKE ?)")
                params.extend([q, q, q])
            if max_price is not None:
                conds.append("price_usd <= ?")
                params.append(float(max_price))
            where = " AND ".join(conds)
            total = conn.execute(f"SELECT COUNT(*) FROM esims WHERE {where}", params).fetchone()[0]
            rows = conn.execute(
                f"SELECT * FROM esims WHERE {where} ORDER BY months ASC, price_usd ASC LIMIT ? OFFSET ?",
                params + [limit, offset],
            ).fetchall()
            return [dict(r) for r in rows], int(total)
        finally:
            conn.close()

    def get_plan(self, pid: int) -> dict:
        conn = db.connect()
        try:
            row = conn.execute("SELECT * FROM esims WHERE id=?", (int(pid),)).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def search_countries(self, query: str) -> list:
        q = query.strip().lower()
        canonical = COUNTRY_ALIASES.get(q, query).lower()
        return [c for c in COUNTRIES_DATA if q in c["name"].lower() or canonical in c["name"].lower()]


class PaymentService:
    def update_wallet_sync(self, conn, uid: int, amount: float, tx_type: str, desc: str) -> float:
        now_s = datetime.now().strftime("%Y-%m-%d %H:%M")
        conn.execute("INSERT OR IGNORE INTO wallets (user_id, created_date) VALUES (?, ?)", (uid, now_s))
        conn.execute("UPDATE wallets SET balance=balance+? WHERE user_id=?", (amount, uid))
        if amount > 0:
            conn.execute("UPDATE wallets SET total_deposited=total_deposited+? WHERE user_id=?", (amount, uid))
        bal_after = float(conn.execute("SELECT balance FROM wallets WHERE user_id=?", (uid,)).fetchone()[0])
        conn.execute(
            "INSERT INTO wallet_transactions (user_id, type, amount, balance_after, description, date) VALUES (?, ?, ?, ?, ?, ?)",
            (uid, tx_type, amount, bal_after, desc, now_s),
        )
        return bal_after

    async def admin_adjust_wallet(self, actor_id: int, target_uid: int, amount: float, tx_type: str, desc: str) -> float:
        async with db.lock:
            conn = db.connect()
            try:
                conn.execute("BEGIN IMMEDIATE")
                bal = self.update_wallet_sync(conn, target_uid, amount, tx_type, desc)
                conn.execute("COMMIT")
            except Exception:
                conn.execute("ROLLBACK")
                raise
            finally:
                conn.close()
        security_svc.log_audit(actor_id, "finance", tx_type, str(target_uid), f"amount={amount:.2f}")
        return bal

    def validate_coupon(self, code: str, uid: int, is_dealer: bool = False) -> tuple:
        code = code.strip().upper()
        conn = db.connect()
        try:
            c = conn.execute("SELECT * FROM coupons WHERE UPPER(code)=? AND is_active=1", (code,)).fetchone()
            if not c:
                return False, "الكوبون غير صالح أو منتهي.", None
            if c["used_count"] >= c["max_uses"]:
                return False, "تم استنفاد الحد الأقصى لاستخدام الكوبون.", None
            if c["dealer_only"] and not is_dealer:
                return False, "هذا الكوبون مخصص للتجار فقط.", None
            if c["new_users_only"]:
                ord_cnt = conn.execute("SELECT COUNT(*) FROM orders WHERE user_id=? AND status='paid'", (uid,)).fetchone()[0]
                if ord_cnt > 0:
                    return False, "هذا الكوبون للعملاء الجدد فقط.", None
            now_iso = datetime.now().strftime("%Y-%m-%d")
            if c["starts_at"] and now_iso < c["starts_at"]:
                return False, "لم يبدأ موعد هذا الكوبون بعد.", None
            if c["expires_at"] and now_iso > c["expires_at"]:
                return False, "انتهت صلاحية هذا الكوبون.", None
            used_by_me = conn.execute("SELECT id FROM coupon_uses WHERE UPPER(code)=? AND user_id=?", (code, uid)).fetchone()
            if used_by_me:
                return False, "لقد استخدمت هذا الكوبون مسبقاً.", None
            return True, "تم تطبيق الكوبون بنجاح.", dict(c)
        finally:
            conn.close()

    def calculate_price(self, uid: int, plan: dict, qty: int, coupon_code: str = "") -> dict:
        conn = db.connect()
        try:
            dlr = conn.execute("SELECT is_active FROM dealer_api_keys WHERE user_id=?", (uid,)).fetchone()
            has_api = bool(dlr and dlr["is_active"])
        finally:
            conn.close()
        unit_price = float(plan["price_usd"])
        if has_api and plan["is_dealer"]:
            unit_price *= 0.5
        subtotal = round(unit_price * qty, 2)
        qty_discount = round(subtotal * 0.10, 2) if qty > 1 else 0.0
        after_qty = round(subtotal - qty_discount, 2)
        coupon_discount = 0.0
        applied_coupon = ""
        if coupon_code:
            ok, _, c = self.validate_coupon(coupon_code, uid, is_dealer=has_api)
            if ok and c:
                applied_coupon = c["code"]
                if c["discount_type"] == "percent":
                    coupon_discount = round(after_qty * (float(c["discount_value"]) / 100.0), 2)
                else:
                    coupon_discount = round(min(after_qty, float(c["discount_value"])), 2)
        final_price = max(0.01, round(after_qty - coupon_discount, 2))
        return {
            "unit_price": unit_price,
            "subtotal": subtotal,
            "qty_discount": qty_discount,
            "coupon_discount": coupon_discount,
            "applied_coupon": applied_coupon,
            "final_price": final_price,
            "has_api": has_api,
        }

    async def checkout_direct(self, uid: int, pid: int, qty: int, coupon_code: str = "", idem_key: str = "") -> tuple:
        if not idem_key:
            idem_key = f"dir_{uid}_{pid}_{qty}_{int(time.time() // 3)}"
        async with db.lock:
            conn = db.connect()
            try:
                conn.execute("BEGIN IMMEDIATE")
                existing_idem = conn.execute("SELECT result_json FROM idempotency_keys WHERE idem_key=?", (idem_key,)).fetchone()
                if existing_idem and existing_idem["result_json"]:
                    conn.execute("COMMIT")
                    return True, json.loads(existing_idem["result_json"])

                plan_row = conn.execute("SELECT * FROM esims WHERE id=?", (pid,)).fetchone()
                if not plan_row:
                    conn.execute("ROLLBACK")
                    return False, "الباقة غير موجودة."
                plan = dict(plan_row)
                if plan["stock"] < qty:
                    conn.execute("ROLLBACK")
                    return False, f"المخزون المتاح ({plan['stock']}) أقل من الكمية المطلوبة."

                pricing = self.calculate_price(uid, plan, qty, coupon_code)
                final_price = pricing["final_price"]

                w_row = conn.execute("SELECT balance FROM wallets WHERE user_id=?", (uid,)).fetchone()
                bal = float(w_row["balance"]) if w_row else 0.0
                if bal < final_price:
                    conn.execute("ROLLBACK")
                    return False, f"رصيدك غير كافٍ (${bal:.2f} متاح / ${final_price:.2f} مطلوب)."

                order_id = f"AURA{secrets.token_hex(4).upper()}"
                now_s = datetime.now().strftime("%Y-%m-%d %H:%M")
                self.update_wallet_sync(conn, uid, -final_price, "purchase", f"شراء {qty}x {plan['name']}")
                conn.execute(
                    "INSERT INTO orders (order_id, user_id, esim_id, quantity, price_usd, total_usd, invoice_id, status, is_dealer, is_wallet, created_date, paid_date, coupon_code, discount_usd, idempotency_key) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        order_id, uid, pid, qty, final_price / qty, final_price, None, "paid",
                        plan["is_dealer"], 1, now_s, now_s, pricing["applied_coupon"],
                        pricing["qty_discount"] + pricing["coupon_discount"], idem_key,
                    ),
                )
                conn.execute("UPDATE esims SET stock = stock - ? WHERE id=?", (qty, pid))
                if pricing["applied_coupon"]:
                    conn.execute("UPDATE coupons SET used_count = used_count + 1 WHERE code=?", (pricing["applied_coupon"],))
                    conn.execute("INSERT INTO coupon_uses (code, user_id, order_id, used_at) VALUES (?, ?, ?, ?)", (pricing["applied_coupon"], uid, order_id, now_s))

                new_stock = int(conn.execute("SELECT stock FROM esims WHERE id=?", (pid,)).fetchone()[0])
                res_payload = {"order_id": order_id, "final_price": final_price, "qty": qty, "plan_name": plan["name"], "new_stock": new_stock}
                conn.execute(
                    "INSERT OR REPLACE INTO idempotency_keys (idem_key, user_id, action, result_json, created_at) VALUES (?, ?, 'checkout_direct', ?, ?)",
                    (idem_key, uid, json.dumps(res_payload, ensure_ascii=False), now_s),
                )
                conn.execute("COMMIT")
            except Exception as e:
                conn.execute("ROLLBACK")
                logger.error(f"checkout_direct error: {e}")
                return False, f"خطأ أثناء تنفيذ الطلب: {e}"
            finally:
                conn.close()

        pts = max(1, int(res_payload["final_price"]))
        user_svc.add_loyalty_points(uid, pts, f"نقاط شراء #{res_payload['order_id']}")
        ref_res = user_svc.process_referral_reward(uid, res_payload["final_price"])
        res_payload["points_earned"] = pts
        res_payload["referral_reward"] = ref_res
        return True, res_payload

    async def checkout_cart(self, uid: int) -> tuple:
        async with db.lock:
            conn = db.connect()
            try:
                conn.execute("BEGIN IMMEDIATE")
                items = conn.execute(
                    "SELECT c.id, c.esim_id, c.price, e.name, e.stock FROM cart c JOIN esims e ON c.esim_id=e.id WHERE c.user_id=?",
                    (uid,),
                ).fetchall()
                if not items:
                    conn.execute("ROLLBACK")
                    return False, "السلة فارغة."
                for it in items:
                    if it["stock"] < 1:
                        conn.execute("ROLLBACK")
                        return False, f"نفد مخزون {it['name']}."
                total_price = round(sum(float(i["price"]) for i in items), 2)
                w_row = conn.execute("SELECT balance FROM wallets WHERE user_id=?", (uid,)).fetchone()
                bal = float(w_row["balance"]) if w_row else 0.0
                if bal < total_price:
                    conn.execute("ROLLBACK")
                    return False, f"رصيدك غير كافٍ (${bal:.2f} / ${total_price:.2f})."
                order_id = f"AURA{secrets.token_hex(4).upper()}"
                now_s = datetime.now().strftime("%Y-%m-%d %H:%M")
                self.update_wallet_sync(conn, uid, -total_price, "purchase", f"شراء سلة مشتريات {order_id}")
                for it in items:
                    conn.execute(
                        "INSERT INTO orders (order_id, user_id, esim_id, quantity, price_usd, total_usd, invoice_id, status, is_dealer, is_wallet, created_date, paid_date) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                        (f"{order_id}_{it['esim_id']}", uid, it["esim_id"], 1, it["price"], it["price"], None, "paid", 0, 1, now_s, now_s),
                    )
                    conn.execute("UPDATE esims SET stock=stock-1 WHERE id=?", (it["esim_id"],))
                conn.execute("DELETE FROM cart WHERE user_id=?", (uid,))
                conn.execute("COMMIT")
            except Exception as e:
                conn.execute("ROLLBACK")
                return False, str(e)
            finally:
                conn.close()
        user_svc.add_loyalty_points(uid, max(1, int(total_price)), f"نقاط سلة #{order_id}")
        user_svc.process_referral_reward(uid, total_price)
        return True, {"order_id": order_id, "total_price": total_price}

    async def activate_dealer_api(self, uid: int) -> tuple:
        async with db.lock:
            conn = db.connect()
            try:
                conn.execute("BEGIN IMMEDIATE")
                existing = conn.execute("SELECT api_key FROM dealer_api_keys WHERE user_id=?", (uid,)).fetchone()
                if existing:
                    conn.execute("ROLLBACK")
                    return False, "لديك اشتراك API مفعل مسبقاً."
                w_row = conn.execute("SELECT balance FROM wallets WHERE user_id=?", (uid,)).fetchone()
                bal = float(w_row["balance"]) if w_row else 0.0
                if bal < 100.0:
                    conn.execute("ROLLBACK")
                    return False, "رصيدك غير كافٍ ($100 مطلوب)."
                now_s = datetime.now().strftime("%Y-%m-%d %H:%M")
                self.update_wallet_sync(conn, uid, -100.0, "api_subscription", "شراء تفعيل نظام API للتجار")
                api_key = f"AURA_API_{secrets.token_hex(16).upper()}"
                conn.execute(
                    "INSERT OR REPLACE INTO dealer_api_keys (user_id, api_key, created_date, tier, is_active) VALUES (?, ?, ?, 'Pro', 1)",
                    (uid, api_key, now_s),
                )
                conn.execute("COMMIT")
                return True, api_key
            except Exception as e:
                conn.execute("ROLLBACK")
                return False, str(e)
            finally:
                conn.close()


class DealerService:
    def get_dealer_info(self, uid: int) -> dict:
        conn = db.connect()
        try:
            row = conn.execute("SELECT * FROM dealer_api_keys WHERE user_id=?", (uid,)).fetchone()
            orders = conn.execute(
                "SELECT COUNT(*), COALESCE(SUM(total_usd), 0) FROM orders WHERE user_id=? AND is_dealer=1 AND status='paid'",
                (uid,),
            ).fetchone()
            return {
                "has_api": bool(row and row["is_active"]),
                "api_key": row["api_key"] if row else "",
                "tier": row["tier"] if row else "Standard",
                "daily_limit": row["daily_limit"] if row else 100,
                "webhook_url": row["webhook_url"] if row else "",
                "created_date": row["created_date"] if row else "",
                "orders_count": int(orders[0]),
                "orders_total": float(orders[1]),
            }
        finally:
            conn.close()

    def regenerate_key(self, uid: int) -> str:
        new_key = f"AURA_API_{secrets.token_hex(16).upper()}"
        conn = db.connect()
        try:
            conn.execute("UPDATE dealer_api_keys SET api_key=? WHERE user_id=?", (new_key, uid))
            conn.commit()
            return new_key
        finally:
            conn.close()

    def set_webhook(self, uid: int, url: str):
        conn = db.connect()
        try:
            conn.execute("UPDATE dealer_api_keys SET webhook_url=? WHERE user_id=?", (url.strip(), uid))
            conn.commit()
        finally:
            conn.close()


class SupportService:
    def create_ticket(self, uid: int, category: str, message: str) -> str:
        tid = f"TKT-{secrets.token_hex(3).upper()}"
        now_s = datetime.now().strftime("%Y-%m-%d %H:%M")
        conn = db.connect()
        try:
            conn.execute(
                "INSERT INTO support_tickets (ticket_id, user_id, category, status, created_at, updated_at) VALUES (?, ?, ?, 'open', ?, ?)",
                (tid, uid, category, now_s, now_s),
            )
            conn.execute(
                "INSERT INTO ticket_messages (ticket_id, sender_id, sender_role, message, created_at) VALUES (?, ?, 'user', ?, ?)",
                (tid, uid, message, now_s),
            )
            conn.commit()
            return tid
        finally:
            conn.close()

    def add_reply(self, ticket_id: str, sender_id: int, sender_role: str, message: str):
        now_s = datetime.now().strftime("%Y-%m-%d %H:%M")
        conn = db.connect()
        try:
            conn.execute(
                "INSERT INTO ticket_messages (ticket_id, sender_id, sender_role, message, created_at) VALUES (?, ?, ?, ?, ?)",
                (ticket_id, sender_id, sender_role, message, now_s),
            )
            new_status = "answered" if sender_role in ("admin", "developer", "owner") else "open"
            conn.execute("UPDATE support_tickets SET status=?, updated_at=? WHERE ticket_id=?", (new_status, now_s, ticket_id))
            conn.commit()
        finally:
            conn.close()

    def rate_ticket(self, ticket_id: str, rating: int):
        conn = db.connect()
        try:
            conn.execute("UPDATE support_tickets SET rating=?, status='closed' WHERE ticket_id=?", (max(1, min(5, rating)), ticket_id))
            conn.commit()
        finally:
            conn.close()


class AIService:
    def is_enabled(self) -> bool:
        return db.get_setting("ai_enabled", "1") == "1"

    def toggle(self) -> bool:
        new_val = "0" if self.is_enabled() else "1"
        db.set_setting("ai_enabled", new_val)
        return new_val == "1"

    async def ask(self, prompt: str, system_context: str = "") -> str:
        if not self.is_enabled():
            return "المساعد الذكي معطّل حالياً من قبل الإدارة."
        if not OPENROUTER_API_KEY:
            return "خدمة المساعد الذكي غير مفعّلة (يرجى ضبط OPENROUTER_API_KEY في ملف .env)."
        sys_msg = system_context or (
            "أنت المساعد الذكي لمتجر Aura eSIM Elite. أجب باحترافية واختصار باللغة العربية عن باقات "
            "Vodafone (اتصال + إنترنت) وHolafly (إنترنت لا محدود بدون استخدام عادل) وMaya (5 جيجا يومياً)."
        )
        try:
            timeout = aiohttp.ClientTimeout(total=15)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    OPENROUTER_URL,
                    headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json"},
                    json={
                        "model": OPENROUTER_MODEL,
                        "messages": [{"role": "system", "content": sys_msg}, {"role": "user", "content": prompt}],
                        "max_tokens": 350,
                    },
                ) as resp:
                    if resp.status != 200:
                        return "تعذر الاتصال بالمساعد الذكي مؤقتاً. يرجى المحاولة لاحقاً."
                    data = await resp.json()
                    return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            logger.warning(f"AI service fallback: {e}")
            return "الخدمة الذكية مشغولة حالياً. يمكنك تصفح الباقات مباشرة من المتجر."


class AnalyticsService:
    def get_summary(self, period: str = "all") -> dict:
        conn = db.connect()
        try:
            date_filter = ""
            now = datetime.now()
            if period == "today":
                date_filter = f" AND created_date >= '{now.strftime('%Y-%m-%d')}'"
            elif period == "week":
                date_filter = f" AND created_date >= '{(now - timedelta(days=7)).strftime('%Y-%m-%d')}'"
            elif period == "month":
                date_filter = f" AND created_date >= '{(now - timedelta(days=30)).strftime('%Y-%m-%d')}'"

            users_cnt = conn.execute("SELECT COUNT(*) FROM users_settings").fetchone()[0]
            dealers_cnt = conn.execute("SELECT COUNT(*) FROM dealer_api_keys WHERE is_active=1").fetchone()[0]
            orders_cnt = conn.execute(f"SELECT COUNT(*) FROM orders WHERE status='paid'{date_filter}").fetchone()[0]
            revenue = conn.execute(f"SELECT COALESCE(SUM(total_usd), 0) FROM orders WHERE status='paid'{date_filter}").fetchone()[0]
            wallets_sum = conn.execute("SELECT COALESCE(SUM(balance), 0) FROM wallets").fetchone()[0]
            stock_sum = conn.execute("SELECT COALESCE(SUM(stock), 0) FROM esims").fetchone()[0]
            top_plans = conn.execute(
                f"SELECT e.name, SUM(o.quantity) as q FROM orders o JOIN esims e ON o.esim_id=e.id WHERE o.status='paid'{date_filter} GROUP BY o.esim_id ORDER BY q DESC LIMIT 3"
            ).fetchall()
            return {
                "users": int(users_cnt),
                "dealers": int(dealers_cnt),
                "orders": int(orders_cnt),
                "revenue": float(revenue),
                "wallets": float(wallets_sum),
                "stock": int(stock_sum),
                "top_plans": [(r["name"], int(r["q"])) for r in top_plans],
            }
        finally:
            conn.close()

    def export_orders_csv(self) -> bytes:
        conn = db.connect()
        try:
            rows = conn.execute(
                "SELECT o.order_id, o.user_id, e.name, o.quantity, o.total_usd, o.status, o.coupon_code, o.created_date FROM orders o LEFT JOIN esims e ON o.esim_id=e.id ORDER BY o.created_date DESC"
            ).fetchall()
            buf = io.StringIO()
            writer = csv.writer(buf)
            writer.writerow(["Order ID", "User ID", "Plan", "Qty", "Total USD", "Status", "Coupon", "Created At"])
            for r in rows:
                writer.writerow([r["order_id"], r["user_id"], r["name"], r["quantity"], r["total_usd"], r["status"], r["coupon_code"], r["created_date"]])
            return buf.getvalue().encode("utf-8-sig")
        finally:
            conn.close()


security_svc = SecurityService()
user_svc = UserService()
product_svc = ProductService()
payment_svc = PaymentService()
dealer_svc = DealerService()
support_svc = SupportService()
ai_svc = AIService()
analytics_svc = AnalyticsService()



# ==============================================================================
# 20. Telegram Keyboards & UI Theme
# ==============================================================================
_BTN_PARAMS = set(inspect.signature(InlineKeyboardButton.__init__).parameters.keys())
SUPPORTS_BTN_STYLE = "style" in _BTN_PARAMS
SUPPORTS_BTN_ICON = "icon_custom_emoji_id" in _BTN_PARAMS


def pbtn(
    text: str,
    callback_data: str = None,
    style: str = None,
    icon_cat: str = None,
    icon_key: str = "main",
    url: str = None,
) -> InlineKeyboardButton:
    """منشئ أزرار متوافق مع Pyrogram/Bot API 9.4 بدون تمرير أي خصائص غير مدعومة."""
    kwargs = {"text": text}
    if url:
        kwargs["url"] = url
    elif callback_data is not None:
        kwargs["callback_data"] = callback_data
    if SUPPORTS_BTN_STYLE and style in ("primary", "success", "danger"):
        kwargs["style"] = style
    if SUPPORTS_BTN_ICON and icon_cat:
        eid = emoji_mgr.get_id(icon_cat, icon_key)
        if eid:
            kwargs["icon_custom_emoji_id"] = str(eid)
    return InlineKeyboardButton(**kwargs)


def strip_btn_extras(markup: InlineKeyboardMarkup) -> InlineKeyboardMarkup:
    if not markup or not getattr(markup, "inline_keyboard", None):
        return markup
    new_rows = []
    for row in markup.inline_keyboard:
        new_row = []
        for b in row:
            kw = {"text": b.text}
            if getattr(b, "url", None):
                kw["url"] = b.url
            elif getattr(b, "callback_data", None) is not None:
                kw["callback_data"] = b.callback_data
            new_row.append(InlineKeyboardButton(**kw))
        new_rows.append(new_row)
    return InlineKeyboardMarkup(new_rows)


class UITheme:
    DIVIDER = "━━━━━━━━━━━━━━━━━━━━"

    @staticmethod
    def header(title: str, cat: str = "home", key: str = "main") -> str:
        return f"<blockquote>{line(cat, f'<b>{title}</b>', key)}</blockquote>"

    @staticmethod
    def card(cat: str, lines_list: list, key: str = "main") -> str:
        formatted = "\n".join(line(cat, ln, key) for ln in lines_list if ln)
        return f"<blockquote>{formatted}</blockquote>"

    @staticmethod
    def success(title: str, body_lines: list) -> str:
        head = line("success", f"<b>{title}</b>")
        body = "\n".join(line("success", ln, "check") for ln in body_lines)
        return f"<blockquote>{head}\n{UITheme.DIVIDER}\n{body}</blockquote>"

    @staticmethod
    def error(title: str, body_lines: list) -> str:
        head = line("failure", f"<b>{title}</b>")
        body = "\n".join(line("failure", ln, "cross") for ln in body_lines)
        return f"<blockquote>{head}\n{UITheme.DIVIDER}\n{body}</blockquote>"

    @staticmethod
    def warning(title: str, body_lines: list) -> str:
        head = line("warning", f"<b>{title}</b>")
        body = "\n".join(line("warning", ln, "alert") for ln in body_lines)
        return f"<blockquote>{head}\n{UITheme.DIVIDER}\n{body}</blockquote>"

    @staticmethod
    def pending(title: str, body_lines: list) -> str:
        head = line("pending", f"<b>{title}</b>")
        body = "\n".join(line("pending", ln, "spin") for ln in body_lines)
        return f"<blockquote>{head}\n{UITheme.DIVIDER}\n{body}</blockquote>"


async def safe_answer(cb, text: str = None, alert: bool = False):
    try:
        await cb.answer(text or "", show_alert=alert)
    except Exception:
        pass


async def safe_send(client, chat_id: int, html_text: str, reply_markup=None, photo=None, document=None):
    try:
        if photo:
            return await client.send_photo(chat_id, photo=photo, caption=html_text, parse_mode=enums.ParseMode.HTML, reply_markup=reply_markup)
        if document:
            return await client.send_document(chat_id, document=document, caption=html_text, parse_mode=enums.ParseMode.HTML, reply_markup=reply_markup)
        return await client.send_message(chat_id, html_text, parse_mode=enums.ParseMode.HTML, reply_markup=reply_markup)
    except FloodWait as e:
        await asyncio.sleep(e.value)
        return await safe_send(client, chat_id, html_text, reply_markup=reply_markup, photo=photo, document=document)
    except BadRequest as e:
        msg = str(e).upper()
        if any(tok in msg for tok in ("CUSTOM_EMOJI", "DOCUMENT_INVALID", "BUTTON", "STYLE", "ENTITY")):
            clean_txt = strip_custom_emojis(html_text)
            clean_kb = strip_btn_extras(reply_markup)
            if photo:
                return await client.send_photo(chat_id, photo=photo, caption=clean_txt, parse_mode=enums.ParseMode.HTML, reply_markup=clean_kb)
            if document:
                return await client.send_document(chat_id, document=document, caption=clean_txt, parse_mode=enums.ParseMode.HTML, reply_markup=clean_kb)
            return await client.send_message(chat_id, clean_txt, parse_mode=enums.ParseMode.HTML, reply_markup=clean_kb)
        raise


async def safe_edit(cb, html_text: str, reply_markup=None):
    try:
        return await cb.message.edit_text(html_text, parse_mode=enums.ParseMode.HTML, reply_markup=reply_markup)
    except MessageNotModified:
        return None
    except BadRequest as e:
        msg = str(e).upper()
        if any(tok in msg for tok in ("CUSTOM_EMOJI", "DOCUMENT_INVALID", "BUTTON", "STYLE", "ENTITY")):
            try:
                return await cb.message.edit_text(
                    strip_custom_emojis(html_text),
                    parse_mode=enums.ParseMode.HTML,
                    reply_markup=strip_btn_extras(reply_markup),
                )
            except MessageNotModified:
                return None
            except Exception:
                pass
        try:
            return await cb.message.reply_text(
                strip_custom_emojis(html_text),
                parse_mode=enums.ParseMode.HTML,
                reply_markup=strip_btn_extras(reply_markup),
            )
        except Exception:
            return None


def build_main_menu(uid: int, first_name: str = "") -> tuple:
    lang = user_svc.get_lang(uid) or "ar"
    t = LANGS.get(lang, LANGS["ar"])
    bal = user_svc.get_wallet_balance(uid)
    loyalty = user_svc.get_loyalty_info(uid)
    dlr = dealer_svc.get_dealer_info(uid)
    role = security_svc.get_role(uid)

    conn = db.connect()
    try:
        orders_cnt = conn.execute("SELECT COUNT(*) FROM orders WHERE user_id=? AND status='paid'", (uid,)).fetchone()[0]
        cart_cnt = conn.execute("SELECT COUNT(*) FROM cart WHERE user_id=?", (uid,)).fetchone()[0]
    finally:
        conn.close()

    tier_label = "تاجر API (خصم 50%)" if dlr["has_api"] else f"{loyalty['tier']} ({loyalty['points']} نقطة)"
    name_lbl = first_name.strip() if first_name else f"#{uid}"

    text = (
        f"{UITheme.header('Aura eSIM Elite — المنصة الرقمية الفاخرة', 'home', 'main')}\n\n"
        f"{UITheme.card('home', [f'مرحباً بك، <b>{name_lbl}</b>', t['welcome_sub']], 'welcome')}\n\n"
        f"{UITheme.card('wallet', [f'رصيد المحفظة: <code>${bal:.2f}</code>', f'العضوية: <b>{tier_label}</b>', f'الطلبات المكتملة: <code>{orders_cnt}</code> | السلة: <code>{cart_cnt}</code>'])}"
    )

    rows = [
        [
            pbtn(t["btn_personal"], "personal_section", style="primary", icon_cat="store"),
            pbtn(t["btn_search_plans"], "search_plans_prompt", style="primary", icon_cat="store", icon_key="search"),
        ],
        [
            pbtn(t["btn_dealer"], "dealer_section", style="primary", icon_cat="dealers"),
            pbtn(t["btn_compare"], "compare_plans_0", style="primary", icon_cat="plans"),
        ],
    ]
    if not dlr["has_api"]:
        rows.append([pbtn(t["btn_dealer_api"], "buy_api_sub_menu", style="success", icon_cat="dealers", icon_key="api")])

    rows.extend([
        [
            pbtn(f"{t['btn_cart']} ({cart_cnt})", "view_cart", style="primary", icon_cat="orders"),
            pbtn(f"{t['btn_wallet']} (${bal:.2f})", "wallet", style="success", icon_cat="wallet"),
        ],
        [
            pbtn(f"{t['btn_orders']} ({orders_cnt})", "my_orders_0", icon_cat="orders", icon_key="invoice"),
            pbtn(t["btn_vip"], "vip_membership", icon_cat="vip"),
        ],
        [
            pbtn(t["btn_referrals"], "referral_dashboard", icon_cat="premium", icon_key="star"),
            pbtn(t["btn_ai"], "ai_assistant", icon_cat="developers"),
        ],
        [
            pbtn(t["btn_countries"], "countries_list_0", icon_cat="countries"),
            pbtn(t["btn_support"], "support_ticket", icon_cat="support"),
        ],
        [pbtn(t["btn_lang"], "change_language", icon_cat="settings")],
    ])
    if security_svc.is_admin(uid):
        rows.append([pbtn(f"{t['btn_admin']} [{role.upper()}]", "admin_panel", style="danger", icon_cat="admin")])

    return text, InlineKeyboardMarkup(rows)



# ==============================================================================
# 21-22. Telegram Message & Callback Query Handlers
# ==============================================================================
def register_handlers(app: Client):
    """تسجيل كافة معالجات Pyrogram للرسائل والأوامر والأزرار."""

    @app.on_message(filters.command("start") & filters.private)
    async def cmd_start(client: Client, message):
        uid = message.from_user.id
        if security_svc.is_banned(uid):
            return

        ref_by = None
        parts = (message.text or "").split()
        if len(parts) > 1 and parts[1].startswith("ref"):
            try:
                cand = int(parts[1].replace("ref", ""))
                if cand != uid:
                    ref_by = cand
            except Exception:
                pass

        cur_lang = user_svc.get_lang(uid)
        user_svc.ensure_user(uid, ref_by=ref_by)

        try:
            u = message.from_user
            uname = f"@{u.username}" if u.username else "بدون معرف"
            await safe_send(
                client,
                DEV_ID,
                UITheme.card(
                    "warning",
                    [
                        "إشعار دخول مستخدم للبوت",
                        f"الاسم: {u.first_name or 'مستخدم'} ({uname})",
                        f"الآيدي: <code>{uid}</code> | {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                    ],
                    "alert",
                ),
            )
        except Exception as e:
            logger.debug(f"Join notify skipped: {e}")

        if not cur_lang:
            kb = InlineKeyboardMarkup([
                [pbtn("العربية [AR]", "set_lang_ar", style="primary"), pbtn("English [EN]", "set_lang_en", style="primary")]
            ])
            await safe_send(
                client,
                uid,
                UITheme.header("Welcome to Aura eSIM Elite", "home") + "\n\n" + UITheme.card("settings", ["اختر لغتك المفضلة / Select your language"]),
                reply_markup=kb,
            )
            return

        txt, kb = build_main_menu(uid, message.from_user.first_name or "")
        await safe_send(client, uid, txt, reply_markup=kb, photo=WELCOME_BANNER_URL or None)

    @app.on_message(filters.command("admin") & filters.private)
    async def cmd_admin(client: Client, message):
        uid = message.from_user.id
        if not security_svc.is_admin(uid):
            return await safe_send(client, uid, UITheme.error("وصول مرفوض", ["ليس لديك صلاحية الوصول إلى لوحة الإدارة."]))
        txt, kb = _render_admin_panel(uid)
        await safe_send(client, uid, txt, reply_markup=kb)

    @app.on_message(filters.command("ai") & filters.private)
    async def cmd_ai(client: Client, message):
        uid = message.from_user.id
        if security_svc.is_banned(uid):
            return
        sessions.set(uid, f"ai_chat_{uid}", True)
        await safe_send(
            client,
            uid,
            UITheme.header("المساعد الذكي AI", "developers") + "\n\n" + UITheme.card("developers", ["أرسل سؤالك حول الباقات أو الدول وسأساعدك فوراً."]),
            reply_markup=InlineKeyboardMarkup([[pbtn("رجوع", "main", style="danger")]]),
        )

    @app.on_callback_query()
    async def on_callback(client: Client, cb):
        uid = cb.from_user.id
        if security_svc.is_banned(uid):
            return await safe_answer(cb, "حسابك محظور.", alert=True)
        data = cb.data or ""
        lang = user_svc.get_lang(uid) or "ar"
        t = LANGS.get(lang, LANGS["ar"])

        if data.startswith("set_lang_"):
            new_l = data.split("_")[2]
            user_svc.set_lang(uid, new_l)
            await safe_answer(cb, LANGS.get(new_l, LANGS["ar"])["lang_changed"], alert=True)
            txt, kb = build_main_menu(uid, cb.from_user.first_name or "")
            await safe_edit(cb, txt, reply_markup=kb)
            return

        if data == "main":
            await safe_answer(cb)
            txt, kb = build_main_menu(uid, cb.from_user.first_name or "")
            await safe_edit(cb, txt, reply_markup=kb)
            return

        if data == "noop":
            return await safe_answer(cb, "استخدم أزرار التنقل المتاحة.")

        if data == "change_language":
            await safe_answer(cb)
            kb = InlineKeyboardMarkup([
                [pbtn("العربية [AR]", "set_lang_ar", style="primary"), pbtn("English [EN]", "set_lang_en", style="primary")],
                [pbtn(t["back"], "main", style="danger")],
            ])
            await safe_edit(cb, UITheme.header("إعدادات اللغة", "settings") + "\n\n" + UITheme.card("settings", ["اختر اللغة المفضلة:"]), reply_markup=kb)
            return

        # ------------------ المتجر والأقسام ------------------
        if data == "personal_section":
            await safe_answer(cb)
            cats = product_svc.list_categories(dealer_only=False, visible_only=True)
            rows = [[pbtn(c["name_ar"] if lang == "ar" else c["name_en"], f"open_cat_{c['slug']}_0", style="primary", icon_cat="store")] for c in cats]
            rows.append([pbtn(t["btn_search_plans"], "search_plans_prompt", style="success", icon_cat="store", icon_key="search")])
            rows.append([pbtn(t["back"], "main", style="danger")])
            await safe_edit(cb, UITheme.header(t["btn_personal"], "store") + "\n\n" + UITheme.card("products", ["اختر القسم لعرض الباقات المتوفرة:"]), reply_markup=InlineKeyboardMarkup(rows))
            return

        if data == "search_plans_prompt":
            await safe_answer(cb)
            sessions.set(uid, f"search_plans_{uid}", True)
            await safe_edit(
                cb,
                UITheme.header("البحث الذكي عن باقة", "store", "search") + "\n\n" + UITheme.card("products", ["أرسل اسم الباقة أو المزود أو السعر الأقصى (مثال: Vodafone أو 30):"]),
                reply_markup=InlineKeyboardMarkup([[pbtn(t["back"], "personal_section", style="danger")]]),
            )
            return

        if data.startswith("compare_plans_"):
            await safe_answer(cb)
            plans, _ = product_svc.list_plans(offset=0, limit=6)
            lines_cmp = [f"<b>{p['name']}</b> — <code>${p['price_usd']:.0f}</code> | {p['months']} شهر | {p['minutes']} دقيقة" for p in plans]
            await safe_edit(
                cb,
                UITheme.header("مقارنة سريعة لأشهر الباقات", "plans") + "\n\n" + UITheme.card("prices", lines_cmp),
                reply_markup=InlineKeyboardMarkup([[pbtn(t["back"], "main", style="danger")]]),
            )
            return

        if data.startswith("open_cat_"):
            await safe_answer(cb)
            raw = data.replace("open_cat_", "")
            if raw.rsplit("_", 1)[-1].isdigit():
                cat, page_s = raw.rsplit("_", 1)
                page = max(0, int(page_s))
            else:
                cat, page = raw, 0
            per_page = 6
            plans, total = product_svc.list_plans(category=cat, offset=page * per_page, limit=per_page)
            total_pages = max(1, (total + per_page - 1) // per_page)
            rows = []
            for p in plans:
                min_s = f" | {p['minutes']} د" if p["minutes"] > 0 else ""
                st_s = " [نفد]" if p["stock"] <= 0 else ""
                rows.append([pbtn(f"{p['name']}{min_s} — ${p['price_usd']:.0f}{st_s}", f"show_plan_{p['id']}_1", style="primary", icon_cat="plans")])
            if total_pages > 1:
                nav = []
                if page > 0:
                    nav.append(pbtn(t["prev_page"], f"open_cat_{cat}_{page-1}"))
                nav.append(pbtn(f"{page+1}/{total_pages}", "noop"))
                if page + 1 < total_pages:
                    nav.append(pbtn(t["next_page"], f"open_cat_{cat}_{page+1}"))
                rows.append(nav)
            back_cb = "dealer_section" if cat.startswith("dealer_") else "personal_section"
            rows.append([pbtn(t["back"], back_cb, style="danger"), pbtn(t["home"], "main")])
            pol_lines = WARRANTY_POLICY_TEXT.get(lang, WARRANTY_POLICY_TEXT["ar"]).splitlines()
            await safe_edit(cb, UITheme.header(f"باقات {cat}", "plans") + "\n\n" + UITheme.card("vip", pol_lines), reply_markup=InlineKeyboardMarkup(rows))
            return

        if data.startswith("show_plan_"):
            await safe_answer(cb)
            parts = data.split("_")
            pid = int(parts[2])
            qty = max(1, min(50, int(parts[3]) if len(parts) > 3 else 1))
            plan = product_svc.get_plan(pid)
            if not plan:
                return await safe_answer(cb, "الباقة غير متوفرة.", alert=True)
            if plan["stock"] <= 0:
                return await safe_edit(cb, UITheme.error("نفاد المخزون", [f"الباقة <b>{plan['name']}</b> غير متوفرة حالياً."]), reply_markup=InlineKeyboardMarkup([[pbtn(t["back"], f"open_cat_{plan['category']}_0", style="danger")]]))

            existing_sess = sessions.get(uid, f"checkout_{uid}")
            scope_lbl = existing_sess.get("scope", "Global") if isinstance(existing_sess, dict) and existing_sess.get("esim_id") == pid else "Global"
            coupon_code = existing_sess.get("coupon", "") if isinstance(existing_sess, dict) and existing_sess.get("esim_id") == pid else ""

            pricing = payment_svc.calculate_price(uid, plan, qty, coupon_code)
            sessions.set(uid, f"checkout_{uid}", {
                "esim_id": pid,
                "qty": qty,
                "final_price": pricing["final_price"],
                "name": plan["name"],
                "is_dealer": plan["is_dealer"],
                "scope": scope_lbl,
                "coupon": pricing["applied_coupon"],
            })

            info_lines = [
                f"التغطية: <code>{scope_lbl}</code> | المدة: <code>{plan['months']} شهر</code>",
                f"الدقائق: <code>{plan['minutes']}</code> | المخزون: <code>{plan['stock']}</code>",
                f"سعر الوحدة: <code>${pricing['unit_price']:.2f}</code> | الكمية: <code>{qty}</code>",
                f"الخصم: <code>-${pricing['qty_discount'] + pricing['coupon_discount']:.2f}</code>",
                f"الإجمالي النهائي: <code>${pricing['final_price']:.2f}</code>",
            ]
            rows = [
                [
                    pbtn("- تقليل", f"show_plan_{pid}_{qty-1}", style="danger"),
                    pbtn(f"الكمية: {qty}", "noop"),
                    pbtn("+ زيادة", f"show_plan_{pid}_{qty+1}", style="success"),
                ],
                [pbtn(t["type_country"], f"pick_country_{pid}_0"), pbtn("إدخال كوبون خصم", f"coupon_prompt_{pid}")],
                [pbtn(f"مراجعة وتأكيد (${pricing['final_price']:.2f})", f"review_buy_now_{pid}", style="success", icon_cat="payments")],
                [pbtn("شراء عبر الشبكات", f"show_order_payments_{pid}", style="primary"), pbtn(t["btn_cart"], f"add_cart_now_{pid}_{qty}")],
                [pbtn(t["back"], f"open_cat_{plan['category']}_0", style="danger"), pbtn(t["home"], "main")],
            ]
            await safe_edit(cb, UITheme.header(plan["name"], "plans") + "\n\n" + UITheme.card("prices", info_lines), reply_markup=InlineKeyboardMarkup(rows))
            return

        if data.startswith("coupon_prompt_"):
            await safe_answer(cb)
            pid = int(data.split("_")[2])
            sessions.set(uid, f"coupon_input_{uid}", pid)
            await safe_edit(cb, UITheme.header("تطبيق كوبون خصم", "prices", "discount") + "\n\n" + UITheme.card("prices", ["أرسل كود الكوبون الآن:"]), reply_markup=InlineKeyboardMarkup([[pbtn(t["back"], f"show_plan_{pid}_1", style="danger")]]))
            return

        if data.startswith("pick_country_"):
            await safe_answer(cb)
            parts = data.split("_")
            pid, page = int(parts[2]), int(parts[3]) if len(parts) > 3 else 0
            per_page = 10
            total_pages = max(1, (len(COUNTRIES_DATA) + per_page - 1) // per_page)
            page = max(0, min(page, total_pages - 1))
            chunk = COUNTRIES_DATA[page * per_page:(page + 1) * per_page]
            rows, row = [], []
            for c in chunk:
                row.append(pbtn(f"{c['flag']} {c['name']}", f"set_plan_country_{pid}_{c['name']}"))
                if len(row) == 2:
                    rows.append(row)
                    row = []
            if row:
                rows.append(row)
            nav = []
            if page > 0:
                nav.append(pbtn(t["prev_page"], f"pick_country_{pid}_{page-1}"))
            nav.append(pbtn(f"{page+1}/{total_pages}", "noop"))
            if page + 1 < total_pages:
                nav.append(pbtn(t["next_page"], f"pick_country_{pid}_{page+1}"))
            rows.append(nav)
            rows.append([pbtn(t["search_country_btn"], f"search_country_plan_{pid}", style="primary")])
            rows.append([pbtn(t["back"], f"show_plan_{pid}_1", style="danger")])
            await safe_edit(cb, UITheme.header("اختر الدولة المستهدفة", "countries"), reply_markup=InlineKeyboardMarkup(rows))
            return

        if data.startswith("search_country_plan_"):
            await safe_answer(cb)
            pid = int(data.split("_")[3])
            sessions.set(uid, f"search_country_for_{uid}", pid)
            await safe_edit(cb, UITheme.header(t["search_prompt"], "countries"), reply_markup=InlineKeyboardMarkup([[pbtn(t["back"], f"pick_country_{pid}_0", style="danger")]]))
            return

        if data.startswith("set_plan_country_"):
            rest = data.replace("set_plan_country_", "")
            pid_s, cname = rest.split("_", 1)
            pid = int(pid_s)
            sess = sessions.get(uid, f"checkout_{uid}")
            qty = sess["qty"] if isinstance(sess, dict) else 1
            if isinstance(sess, dict):
                sess["scope"] = cname
                sessions.set(uid, f"checkout_{uid}", sess)
            await safe_answer(cb, f"تم تحديد {cname}")
            cb.data = f"show_plan_{pid}_{qty}"
            await on_callback(client, cb)
            return

        if data.startswith("add_cart_now_"):
            parts = data.split("_")
            pid, qty = int(parts[3]), int(parts[4])
            sess = sessions.get(uid, f"checkout_{uid}")
            price = sess["final_price"] if isinstance(sess, dict) else 20.0
            scope = sess.get("scope", "Global") if isinstance(sess, dict) else "Global"
            conn = db.connect()
            try:
                conn.execute("INSERT INTO cart (user_id, esim_id, scope, price) VALUES (?, ?, ?, ?)", (uid, pid, f"{scope} | Qty: {qty}", price))
                conn.commit()
            finally:
                conn.close()
            return await safe_answer(cb, "تمت الإضافة إلى سلة المشتريات.", alert=True)

        if data.startswith("review_buy_now_"):
            await safe_answer(cb)
            pid = int(data.split("_")[3])
            sess = sessions.get(uid, f"checkout_{uid}")
            if not isinstance(sess, dict) or sess.get("esim_id") != pid:
                return await safe_answer(cb, "انتهت الجلسة.", alert=True)
            bal = user_svc.get_wallet_balance(uid)
            await safe_edit(
                cb,
                UITheme.header("مراجعة الطلب قبل الدفع", "orders", "invoice") + "\n\n" + UITheme.card("prices", [
                    f"الباقة: <b>{sess['name']}</b>",
                    f"التغطية: <code>{sess.get('scope', 'Global')}</code> | الكمية: <code>{sess['qty']}</code>",
                    f"الإجمالي المطلوب: <code>${sess['final_price']:.2f}</code> | رصيدك: <code>${bal:.2f}</code>",
                ]),
                reply_markup=InlineKeyboardMarkup([
                    [pbtn(f"تأكيد ودفع الآن (${sess['final_price']:.2f})", f"pay_wallet_now_{pid}", style="success", icon_cat="success")],
                    [pbtn(t["back"], f"show_plan_{pid}_{sess['qty']}", style="danger")],
                ]),
            )
            return

        if data.startswith("pay_wallet_now_"):
            if not security_svc.allow_action(uid, "pay_wallet_now", cooldown=2.5):
                return await safe_answer(cb, "جاري تنفيذ طلبك، يرجى الانتظار...", alert=True)
            await safe_answer(cb)
            pid = int(data.split("_")[3])
            sess = sessions.get(uid, f"checkout_{uid}")
            if not isinstance(sess, dict) or sess.get("esim_id") != pid:
                return await safe_answer(cb, "انتهت الجلسة.", alert=True)

            ok, res = await payment_svc.checkout_direct(uid, pid, sess["qty"], sess.get("coupon", ""))
            if not ok:
                return await safe_edit(
                    cb,
                    UITheme.error("تعذر إتمام الشراء", [str(res)]),
                    reply_markup=InlineKeyboardMarkup([[pbtn("شحن المحفظة", "charge_wallet", style="success")], [pbtn(t["back"], "main", style="danger")]]),
                )
            sessions.remove(uid, f"checkout_{uid}")
            if res["new_stock"] <= 10:
                try:
                    await safe_send(client, DEV_ID, UITheme.warning("تنبيه انخفاض المخزون", [f"الباقة: {res['plan_name']}", f"المتبقي: <code>{res['new_stock']}</code>"]))
                except Exception:
                    pass

            if res["qty"] > 1:
                lpa_txt = "\n".join([f"eSIM #{i+1}: {DEFAULT_LPA}" for i in range(res["qty"])])
                bio = io.BytesIO(lpa_txt.encode("utf-8"))
                bio.name = f"Aura_eSIMs_{res['order_id']}.txt"
                await safe_send(client, uid, UITheme.success("تم الشراء بنجاح", [f"رقم الطلب: <code>{res['order_id']}</code>", f"المخصوم: <code>${res['final_price']:.2f}</code>", f"نقاط الولاء المكتسبة: <code>+{res['points_earned']}</code>"]), document=bio)
            else:
                await safe_send(client, uid, UITheme.success("تم الشراء بنجاح", [f"رقم الطلب: <code>{res['order_id']}</code>", f"كود LPA:\n<code>{DEFAULT_LPA}</code>", f"نقاط الولاء المكتسبة: <code>+{res['points_earned']}</code>"]), photo=DEFAULT_BARCODE)
            txt, kb = build_main_menu(uid, cb.from_user.first_name or "")
            await safe_send(client, uid, txt, reply_markup=kb)
            return

        # ------------------ السلة ------------------
        if data == "view_cart":
            await safe_answer(cb)
            conn = db.connect()
            try:
                items = conn.execute("SELECT c.id, c.esim_id, e.name, e.price_usd, c.scope, c.price FROM cart c JOIN esims e ON c.esim_id=e.id WHERE c.user_id=?", (uid,)).fetchall()
            finally:
                conn.close()
            if not items:
                return await safe_edit(cb, UITheme.header("سلة المشتريات", "orders") + "\n\n" + UITheme.card("orders", ["السلة فارغة حالياً."]), reply_markup=InlineKeyboardMarkup([[pbtn("تصفح المتجر", "personal_section", style="primary")], [pbtn(t["back"], "main", style="danger")]]))
            tot = sum(float(i["price"]) for i in items)
            lines_c = [f"<b>{i['name']}</b> ({i['scope']}) — <code>${i['price']:.2f}</code>" for i in items]
            lines_c.append(f"الإجمالي النهائي: <code>${tot:.2f}</code>")
            rows = [[pbtn(f"+ زيادة ({i['name'][:12]})", f"cart_qty_{i['id']}_1", style="success"), pbtn("حذف", f"cart_del_{i['id']}", style="danger")] for i in items]
            rows.append([pbtn(f"تأكيد وشراء السلة (${tot:.2f})", "cart_confirm", style="success")])
            rows.append([pbtn(t["back"], "main", style="danger")])
            await safe_edit(cb, UITheme.header("سلة المشتريات", "orders") + "\n\n" + UITheme.card("prices", lines_c), reply_markup=InlineKeyboardMarkup(rows))
            return

        if data.startswith("cart_qty_"):
            cid = int(data.split("_")[2])
            conn = db.connect()
            try:
                r = conn.execute("SELECT c.scope, e.price_usd FROM cart c JOIN esims e ON c.esim_id=e.id WHERE c.id=? AND c.user_id=?", (cid, uid)).fetchone()
                if r:
                    m = re.search(r"Qty:\s*(\d+)", r["scope"] or "")
                    q = min(50, (int(m.group(1)) if m else 1) + 1)
                    new_sc = re.sub(r"Qty:\s*\d+", f"Qty: {q}", r["scope"]) if m else f"{r['scope']} | Qty: {q}"
                    new_pr = round(float(r["price_usd"]) * q * (0.9 if q > 1 else 1.0), 2)
                    conn.execute("UPDATE cart SET scope=?, price=? WHERE id=? AND user_id=?", (new_sc, new_pr, cid, uid))
                    conn.commit()
            finally:
                conn.close()
            await safe_answer(cb, "تم تحديث الكمية.")
            cb.data = "view_cart"
            await on_callback(client, cb)
            return

        if data.startswith("cart_del_"):
            cid = int(data.split("_")[2])
            conn = db.connect()
            try:
                conn.execute("DELETE FROM cart WHERE id=? AND user_id=?", (cid, uid))
                conn.commit()
            finally:
                conn.close()
            await safe_answer(cb, "تم حذف العنصر.")
            cb.data = "view_cart"
            await on_callback(client, cb)
            return

        if data == "cart_confirm":
            await safe_answer(cb)
            await safe_edit(
                cb,
                UITheme.header("تأكيد شراء السلة", "payments") + "\n\n" + UITheme.card("payments", ["هل تريد إتمام الدفع من رصيد المحفظة؟"]),
                reply_markup=InlineKeyboardMarkup([[pbtn("تأكيد الدفع الآن", "cart_checkout", style="success")], [pbtn(t["back"], "view_cart", style="danger")]]),
            )
            return

        if data == "cart_checkout":
            if not security_svc.allow_action(uid, "cart_checkout", cooldown=2.5):
                return await safe_answer(cb, "جاري المعالجة...", alert=True)
            await safe_answer(cb)
            ok, res = await payment_svc.checkout_cart(uid)
            if not ok:
                return await safe_edit(cb, UITheme.error("تعذر إتمام الدفع", [str(res)]), reply_markup=InlineKeyboardMarkup([[pbtn(t["back"], "view_cart", style="danger")]]))
            await safe_send(client, uid, UITheme.success("تم دفع السلة بنجاح", [f"رقم العملية: <code>{res['order_id']}</code>", f"كود LPA:\n<code>{DEFAULT_LPA}</code>"]), photo=DEFAULT_BARCODE)
            return

        # ------------------ المحفظة، الطلبات، الولاء، الإحالات، التجار، AI، الدعم ------------------
        if data == "wallet":
            await safe_answer(cb)
            bal = user_svc.get_wallet_balance(uid)
            me = await client.get_me()
            ref_link = f"https://t.me/{me.username}?start=ref{uid}"
            await safe_edit(
                cb,
                UITheme.header("محفظتك الرقمية", "wallet") + "\n\n" + UITheme.card("wallet", [f"الرصيد المتاح: <code>${bal:.2f}</code>", f"رابط الإحالة:\n<code>{ref_link}</code>"]),
                reply_markup=InlineKeyboardMarkup([
                    [pbtn("شحن المحفظة", "charge_wallet", style="success"), pbtn(t["btn_transactions"], "wallet_transactions_0", style="primary")],
                    [pbtn(t["btn_verify_payment"], "verify_payment_menu")],
                    [pbtn(t["back"], "main", style="danger")],
                ]),
            )
            return

        if data == "charge_wallet":
            await safe_answer(cb)
            sessions.set(uid, f"charge_amount_prompt_{uid}", True)
            await safe_edit(cb, UITheme.header("شحن المحفظة", "wallet", "deposit") + "\n\n" + UITheme.card("prices", ["أرسل المبلغ المراد إيداعه بالدولار (الحد الأدنى $20):"]), reply_markup=InlineKeyboardMarkup([[pbtn(t["back"], "wallet", style="danger")]]))
            return

        if data.startswith("wallet_transactions_"):
            await safe_answer(cb)
            page = int(data.split("_")[2])
            conn = db.connect()
            try:
                rows = conn.execute("SELECT id, amount, balance_after, description, date FROM wallet_transactions WHERE user_id=? ORDER BY id DESC LIMIT 8 OFFSET ?", (uid, page * 8)).fetchall()
            finally:
                conn.close()
            if not rows:
                return await safe_edit(cb, UITheme.header("سجل المعاملات", "payments") + "\n\n" + UITheme.card("payments", ["لا توجد معاملات مسجلة."]), reply_markup=InlineKeyboardMarkup([[pbtn(t["back"], "wallet", style="danger")]]))
            tx_lines = [f"#{r['id']} | <code>{'+' if r['amount']>0 else ''}${r['amount']:.2f}</code> | {r['description']} ({r['date']})" for r in rows]
            await safe_edit(cb, UITheme.header("سجل المعاملات المالية", "payments") + "\n\n" + UITheme.card("payments", tx_lines), reply_markup=InlineKeyboardMarkup([[pbtn(t["back"], "wallet", style="danger")]]))
            return

        if data == "verify_payment_menu":
            await safe_answer(cb)
            sessions.set(uid, f"verify_payment_{uid}", True)
            await safe_edit(cb, UITheme.header("التحقق من الدفع", "payments", "verify") + "\n\n" + UITheme.card("payments", ["أرسل معرف المعاملة (TxID) أو صورة الإيصال:"]), reply_markup=InlineKeyboardMarkup([[pbtn(t["back"], "wallet", style="danger")]]))
            return

        if data.startswith("show_order_payments_"):
            await safe_answer(cb)
            pid = int(data.split("_")[3])
            conn = db.connect()
            try:
                nets = conn.execute("SELECT network_name, address, binance_id FROM binance_networks").fetchall()
            finally:
                conn.close()
            net_lines = [f"<b>{n['network_name']}</b>: <code>{n['binance_id'] or n['address'] or '-'}</code>" for n in nets]
            await safe_edit(
                cb,
                UITheme.header("طرق الدفع المتاحة", "payments") + "\n\n" + UITheme.card("payments", net_lines),
                reply_markup=InlineKeyboardMarkup([[pbtn("إرسال إيصال الدفع", "verify_payment_menu", style="success")], [pbtn(t["back"], f"show_plan_{pid}_1", style="danger")]]),
            )
            return

        if data.startswith("my_orders_"):
            await safe_answer(cb)
            page = int(data.split("_")[2])
            conn = db.connect()
            try:
                rows = conn.execute("SELECT o.order_id, e.name, o.quantity, o.total_usd, o.created_date FROM orders o LEFT JOIN esims e ON o.esim_id=e.id WHERE o.user_id=? AND o.status='paid' ORDER BY o.created_date DESC LIMIT 6 OFFSET ?", (uid, page * 6)).fetchall()
            finally:
                conn.close()
            if not rows:
                return await safe_edit(cb, UITheme.header("طلباتي المكتملة", "orders") + "\n\n" + UITheme.card("orders", ["لا توجد طلبات مكتملة حتى الآن."]), reply_markup=InlineKeyboardMarkup([[pbtn(t["back"], "main", style="danger")]]))
            ord_lines = [f"#{r['order_id']} | {r['quantity']}x {r['name']} — <code>${r['total_usd']:.2f}</code>" for r in rows]
            kb_rows = [[pbtn(f"تفاصيل #{r['order_id']}", f"reload_{r['order_id']}", style="primary")] for r in rows]
            kb_rows.append([pbtn(t["back"], "main", style="danger")])
            await safe_edit(cb, UITheme.header("طلباتي المكتملة", "orders") + "\n\n" + UITheme.card("orders", ord_lines), reply_markup=InlineKeyboardMarkup(kb_rows))
            return

        if data.startswith("reload_"):
            await safe_answer(cb)
            oid = data.replace("reload_", "")
            await safe_send(client, uid, UITheme.header(f"فاتورة الطلب #{oid}", "orders", "invoice") + "\n\n" + UITheme.card("orders", [f"كود التفعيل (LPA):\n<code>{DEFAULT_LPA}</code>"]), photo=DEFAULT_BARCODE)
            return

        if data.startswith("countries_list_"):
            await safe_answer(cb)
            page = int(data.split("_")[2])
            per_page = 25
            total_pages = max(1, (len(COUNTRIES_DATA) + per_page - 1) // per_page)
            page = max(0, min(page, total_pages - 1))
            chunk = COUNTRIES_DATA[page * per_page:(page + 1) * per_page]
            c_lines = [f"<code>{c['flag']}</code> <b>{c['name']}</b> — {c['operators']}" for c in chunk]
            nav = []
            if page > 0:
                nav.append(pbtn(t["prev_page"], f"countries_list_{page-1}"))
            nav.append(pbtn(f"{page+1}/{total_pages}", "noop"))
            if page + 1 < total_pages:
                nav.append(pbtn(t["next_page"], f"countries_list_{page+1}"))
            await safe_edit(cb, UITheme.header(f"الدول المدعومة ({len(COUNTRIES_DATA)})", "countries") + "\n\n" + UITheme.card("countries", c_lines), reply_markup=InlineKeyboardMarkup([nav, [pbtn(t["back"], "main", style="danger")]]))
            return

        if data == "vip_membership":
            await safe_answer(cb)
            loy = user_svc.get_loyalty_info(uid)
            dlr = dealer_svc.get_dealer_info(uid)
            await safe_edit(
                cb,
                UITheme.header("حالة العضوية والولاء VIP", "vip") + "\n\n" + UITheme.card("vip", [
                    f"المستوى الحالي: <b>{loy['tier']}</b>",
                    f"نقاط الولاء: <code>{loy['points']}</code> نقطة",
                    f"خصم المستوى: <code>{loy['tier_discount']}%</code> | وضع التاجر API: <b>{'مفعل' if dlr['has_api'] else 'غير مفعل'}</b>",
                ]),
                reply_markup=InlineKeyboardMarkup([[pbtn(t["back"], "main", style="danger")]]),
            )
            return

        if data == "referral_dashboard":
            await safe_answer(cb)
            st = user_svc.get_referral_stats(uid)
            me = await client.get_me()
            link = f"https://t.me/{me.username}?start=ref{uid}"
            await safe_edit(
                cb,
                UITheme.header("نظام الإحالات والأرباح", "premium", "star") + "\n\n" + UITheme.card("wallet", [
                    f"عدد المدعوين: <code>{st['invited']}</code>",
                    f"إجمالي الأرباح: <code>${st['earnings']:.2f}</code> (5% مكافأة لأول طلب)",
                    f"رابط الدعوة:\n<code>{link}</code>",
                ]),
                reply_markup=InlineKeyboardMarkup([[pbtn(t["back"], "main", style="danger")]]),
            )
            return

        if data == "dealer_section":
            await safe_answer(cb)
            dlr = dealer_svc.get_dealer_info(uid)
            cats = product_svc.list_categories(dealer_only=True, visible_only=True)
            rows = [[pbtn(c["name_ar"] if lang == "ar" else c["name_en"], f"open_cat_{c['slug']}_0", style="primary", icon_cat="dealers")] for c in cats]
            if not dlr["has_api"]:
                rows.append([pbtn(t["btn_dealer_api"], "buy_api_sub_menu", style="success")])
            else:
                rows.append([pbtn("مفتاح الـ API", "view_api_key_info", style="primary"), pbtn("تجديد المفتاح", "dealer_regen_key", style="danger")])
            rows.append([pbtn(t["back"], "main", style="danger")])
            await safe_edit(
                cb,
                UITheme.header("قسم التجار والموزعين", "dealers") + "\n\n" + UITheme.card("dealers", [
                    f"الحالة: <b>{'تاجر API (خصم 50%)' if dlr['has_api'] else 'غير مشترك في API'}</b>",
                    f"طلبات الجملة: <code>{dlr['orders_count']}</code> | الإجمالي: <code>${dlr['orders_total']:.2f}</code>",
                ]),
                reply_markup=InlineKeyboardMarkup(rows),
            )
            return

        if data == "buy_api_sub_menu":
            await safe_answer(cb)
            await safe_edit(
                cb,
                UITheme.header("تفعيل نظام الـ API للتجار", "dealers", "api") + "\n\n" + UITheme.card("prices", ["تكلفة التفعيل: <code>$100.00</code> لمرة واحدة", "المميزات: خصم دائم 50% + مفتاح API خاص."]),
                reply_markup=InlineKeyboardMarkup([[pbtn("تأكيد وشراء ($100)", "confirm_buy_api_sub", style="success")], [pbtn(t["back"], "dealer_section", style="danger")]]),
            )
            return

        if data == "confirm_buy_api_sub":
            await safe_answer(cb)
            ok, res = await payment_svc.activate_dealer_api(uid)
            if not ok:
                return await safe_edit(cb, UITheme.error("تعذر التفعيل", [str(res)]), reply_markup=InlineKeyboardMarkup([[pbtn(t["back"], "dealer_section", style="danger")]]))
            await safe_edit(cb, UITheme.success("تم تفعيل API بنجاح", [f"مفتاحك:\n<code>{res}</code>"]), reply_markup=InlineKeyboardMarkup([[pbtn(t["back"], "dealer_section", style="danger")]]))
            return

        if data == "view_api_key_info":
            await safe_answer(cb)
            dlr = dealer_svc.get_dealer_info(uid)
            if not dlr["has_api"]:
                return await safe_answer(cb, "ليس لديك اشتراك API.", alert=True)
            await safe_edit(cb, UITheme.header("بيانات مفتاح API", "dealers", "api") + "\n\n" + UITheme.card("dealers", [f"المفتاح:\n<code>{dlr['api_key']}</code>", f"الحد اليومي: <code>{dlr['daily_limit']}</code>"]), reply_markup=InlineKeyboardMarkup([[pbtn(t["back"], "dealer_section", style="danger")]]))
            return

        if data == "dealer_regen_key":
            new_k = dealer_svc.regenerate_key(uid)
            await safe_answer(cb, "تم تجديد المفتاح.", alert=True)
            await safe_edit(cb, UITheme.success("تم تجديد مفتاح API", [f"المفتاح الجديد:\n<code>{new_k}</code>"]), reply_markup=InlineKeyboardMarkup([[pbtn(t["back"], "dealer_section", style="danger")]]))
            return

        if data == "ai_assistant":
            await safe_answer(cb)
            sessions.set(uid, f"ai_chat_{uid}", True)
            await safe_edit(
                cb,
                UITheme.header("المساعد الذكي AI", "developers") + "\n\n" + UITheme.card("developers", [f"الحالة: <b>{'مفعل' if ai_svc.is_enabled() else 'معطل'}</b>", "أرسل استفسارك وسيرد عليك المساعد الذكي فوراً."]),
                reply_markup=InlineKeyboardMarkup([[pbtn(t["back"], "main", style="danger")]]),
            )
            return

        if data == "support_ticket":
            await safe_answer(cb)
            sessions.set(uid, f"support_ticket_{uid}", True)
            await safe_edit(cb, UITheme.header("الدعم الفني المباشر", "support") + "\n\n" + UITheme.card("support", ["اكتب مشكلتك أو استفسارك لفتح تذكرة دعم برقم متابعة:"]), reply_markup=InlineKeyboardMarkup([[pbtn(t["back"], "main", style="danger")]]))
            return

        # ------------------ لوحة الإدارة المتقدمة ------------------
        if data == "admin_panel" or data.startswith("adm_") or data.startswith("admin_"):
            if not security_svc.is_admin(uid):
                return await safe_answer(cb, "غير مصرح لك بالوصول.", alert=True)
            await _handle_admin_callbacks(client, cb, uid, data, t)
            return

    @app.on_message(filters.private & ~filters.command(["start", "admin", "ai"]))
    async def on_message(client: Client, message):
        uid = message.from_user.id
        if security_svc.is_banned(uid) or not security_svc.allow_rate(uid):
            return
        text = (message.text or "").strip()
        lang = user_svc.get_lang(uid) or "ar"
        t = LANGS.get(lang, LANGS["ar"])

        if sessions.has(uid, f"ai_chat_{uid}"):
            sessions.remove(uid, f"ai_chat_{uid}")
            reply = await ai_svc.ask(text)
            await safe_send(client, uid, UITheme.header("رد المساعد الذكي", "developers") + "\n\n" + UITheme.card("developers", [reply]), reply_markup=InlineKeyboardMarkup([[pbtn(t["back"], "main", style="danger")]]))
            return

        if sessions.has(uid, f"coupon_input_{uid}"):
            pid = sessions.pop(uid, f"coupon_input_{uid}")
            dlr = dealer_svc.get_dealer_info(uid)
            ok, msg, _ = payment_svc.validate_coupon(text, uid, is_dealer=dlr["has_api"])
            if ok:
                sess = sessions.get(uid, f"checkout_{uid}")
                if isinstance(sess, dict):
                    sess["coupon"] = text.strip().upper()
                    sessions.set(uid, f"checkout_{uid}", sess)
            res_html = UITheme.success("الكوبون", [msg]) if ok else UITheme.error("الكوبون", [msg])
            await safe_send(client, uid, res_html, reply_markup=InlineKeyboardMarkup([[pbtn("العودة للباقة", f"show_plan_{pid}_1", style="primary")]]))
            return

        if sessions.has(uid, f"search_plans_{uid}"):
            sessions.remove(uid, f"search_plans_{uid}")
            max_p = float(text) if text.replace(".", "", 1).isdigit() else None
            plans, _ = product_svc.list_plans(search=None if max_p else text, max_price=max_p, limit=12)
            if not plans:
                return await safe_send(client, uid, UITheme.warning("لا توجد نتائج", [f"لم يتم العثور على باقات مطابقة لـ <code>{text}</code>."]), reply_markup=InlineKeyboardMarkup([[pbtn(t["back"], "personal_section", style="danger")]]))
            rows = [[pbtn(f"{p['name']} — ${p['price_usd']:.0f}", f"show_plan_{p['id']}_1", style="primary")] for p in plans]
            rows.append([pbtn(t["back"], "personal_section", style="danger")])
            await safe_send(client, uid, UITheme.header(f"نتائج البحث: {text}", "store", "search"), reply_markup=InlineKeyboardMarkup(rows))
            return

        if sessions.has(uid, f"search_country_for_{uid}"):
            pid = sessions.pop(uid, f"search_country_for_{uid}")
            matches = product_svc.search_countries(text)
            if not matches:
                return await safe_send(client, uid, UITheme.warning("غير موجودة", ["لم يتم العثور على الدولة."]), reply_markup=InlineKeyboardMarkup([[pbtn(t["back"], f"pick_country_{pid}_0", style="danger")]]))
            rows = [[pbtn(f"{c['flag']} {c['name']}", f"set_plan_country_{pid}_{c['name']}")] for c in matches[:10]]
            rows.append([pbtn(t["back"], f"pick_country_{pid}_0", style="danger")])
            await safe_send(client, uid, UITheme.header("نتائج الدول", "countries"), reply_markup=InlineKeyboardMarkup(rows))
            return

        if sessions.has(uid, f"charge_amount_prompt_{uid}"):
            sessions.remove(uid, f"charge_amount_prompt_{uid}")
            try:
                amt = float(text)
                if amt < 20:
                    sessions.set(uid, f"charge_amount_prompt_{uid}", True)
                    return await safe_send(client, uid, UITheme.warning("تنبيه", [t["min_charge_err"]]))
                sessions.set(uid, f"charging_amount_{uid}", amt)
                conn = db.connect()
                try:
                    nets = conn.execute("SELECT network_name, address, binance_id FROM binance_networks").fetchall()
                finally:
                    conn.close()
                n_lines = [f"<b>{n['network_name']}</b>: <code>{n['binance_id'] or n['address'] or '-'}</code>" for n in nets]
                await safe_send(
                    client,
                    uid,
                    UITheme.header(f"بوابة الشحن — ${amt:.2f}", "payments") + "\n\n" + UITheme.card("payments", n_lines),
                    reply_markup=InlineKeyboardMarkup([[pbtn("إرسال إيصال الدفع", "verify_payment_menu", style="success")], [pbtn(t["back"], "wallet", style="danger")]]),
                )
            except Exception:
                sessions.set(uid, f"charge_amount_prompt_{uid}", True)
                await safe_send(client, uid, UITheme.error("قيمة خاطئة", [t["invalid_number_err"]]))
            return

        if sessions.has(uid, f"verify_payment_{uid}"):
            sessions.remove(uid, f"verify_payment_{uid}")
            dep_amt = sessions.pop(uid, f"charging_amount_{uid}") or 20.0
            await safe_send(client, uid, UITheme.pending("جاري المراجعة", [t["verify_sent"]]), reply_markup=InlineKeyboardMarkup([[pbtn(t["back"], "wallet", style="danger")]]))
            kb = InlineKeyboardMarkup([[pbtn("قبول وشحن", f"admin_approve_dep_{uid}_{dep_amt}", style="success"), pbtn("رفض", f"admin_reject_dep_{uid}", style="danger")]])
            msg_html = UITheme.header("طلب تحقق من دفع", "payments") + "\n\n" + UITheme.card("payments", [f"المستخدم: <code>{uid}</code>", f"المبلغ: <code>${dep_amt:.2f}</code>", f"البيان: {text or 'مرفق'}"])
            await safe_send(client, DEV_ID, msg_html, reply_markup=kb)
            return

        if sessions.has(uid, f"support_ticket_{uid}"):
            sessions.remove(uid, f"support_ticket_{uid}")
            tid = support_svc.create_ticket(uid, "general", text or "رسالة دعم")
            await safe_send(client, uid, UITheme.success("تم إنشاء التذكرة", [f"رقم التذكرة: <code>{tid}</code>", t["support_sent"]]), reply_markup=InlineKeyboardMarkup([[pbtn(t["back"], "main", style="danger")]]))
            await safe_send(client, DEV_ID, UITheme.header(f"تذكرة جديدة {tid}", "support") + "\n\n" + UITheme.card("support", [f"من: <code>{uid}</code>", text]))
            return

        # معالجات إدخال الأدمن المحمية بالصلاحية
        if security_svc.is_admin(uid):
            await _handle_admin_inputs(client, uid, text, t)


def _render_admin_panel(uid: int) -> tuple:
    st = analytics_svc.get_summary("all")
    role = security_svc.get_role(uid)
    txt = (
        f"{UITheme.header(f'لوحة الإدارة الاحترافية [{role.upper()}]', 'admin')}\n\n"
        + UITheme.card('stats', [
            f"المستخدمون: <code>{st['users']}</code> | التجار: <code>{st['dealers']}</code>",
            f"الطلبات: <code>{st['orders']}</code> | الإيرادات: <code>${st['revenue']:.2f}</code>",
            f"المحافظ: <code>${st['wallets']:.2f}</code> | المخزون: <code>{st['stock']}</code>",
        ])
    )
    rows = [
        [pbtn("التحليلات والتقارير", "adm_stats_all", style="primary", icon_cat="stats"), pbtn("تصدير CSV", "adm_export_csv", style="success")],
        [pbtn("المستخدمين", "adm_users_mgr_0", style="primary"), pbtn("الباقات والمخزون", "adm_plans_mgr_0", style="primary")],
        [pbtn("الأقسام", "adm_cats_mgr"), pbtn("الكوبونات", "adm_coupons_mgr")],
        [pbtn("طرق الدفع", "adm_pay_mgr"), pbtn("الإيموجيات المخصصة", "adm_emojis_mgr")],
        [pbtn("سجل Audit", "adm_audit_logs"), pbtn(f"AI: {'مفعل' if ai_svc.is_enabled() else 'معطل'}", "adm_toggle_ai")],
        [pbtn("نسخة احتياطية مشفرة", "adm_backup_now", style="success"), pbtn("إذاعة عامة", "admin_broadcast_msg", style="danger")],
        [pbtn("شحن رصيد", "admin_add_balance"), pbtn("خصم رصيد", "admin_sub_balance")],
        [pbtn("رجوع للرئيسية", "main", style="danger")],
    ]
    return txt, InlineKeyboardMarkup(rows)


async def _handle_admin_callbacks(client: Client, cb, uid: int, data: str, t: dict):
    if data == "admin_panel":
        await safe_answer(cb)
        txt, kb = _render_admin_panel(uid)
        await safe_edit(cb, txt, reply_markup=kb)
        return

    if data.startswith("adm_stats_"):
        await safe_answer(cb)
        period = data.replace("adm_stats_", "")
        st = analytics_svc.get_summary(period)
        top_s = ", ".join(f"{n} ({q})" for n, q in st["top_plans"]) or "لا يوجد"
        await safe_edit(
            cb,
            UITheme.header(f"تحليلات الفترة: {period}", "stats") + "\n\n" + UITheme.card("stats", [f"الطلبات: <code>{st['orders']}</code> | الإيرادات: <code>${st['revenue']:.2f}</code>", f"الأكثر مبيعاً: {top_s}"]),
            reply_markup=InlineKeyboardMarkup([
                [pbtn("اليوم", "adm_stats_today"), pbtn("الأسبوع", "adm_stats_week"), pbtn("الشهر", "adm_stats_month"), pbtn("الكل", "adm_stats_all")],
                [pbtn(t["back"], "admin_panel", style="danger")],
            ]),
        )
        return

    if data == "adm_export_csv":
        await safe_answer(cb)
        csv_bytes = analytics_svc.export_orders_csv()
        bio = io.BytesIO(csv_bytes)
        bio.name = f"orders_report_{datetime.now().strftime('%Y%m%d')}.csv"
        await safe_send(client, uid, UITheme.success("تقرير المبيعات CSV", ["تم تصدير سجل الطلبات بنجاح."]), document=bio)
        return

    if data == "adm_toggle_ai":
        state = ai_svc.toggle()
        security_svc.log_audit(uid, "settings", "toggle_ai", str(state))
        await safe_answer(cb, f"تم {'تفعيل' if state else 'تعطيل'} المساعد الذكي.", alert=True)
        txt, kb = _render_admin_panel(uid)
        await safe_edit(cb, txt, reply_markup=kb)
        return

    if data == "adm_backup_now":
        if not security_svc.is_developer(uid):
            return await safe_answer(cb, "صلاحية المطور مطلوبة للنسخ الاحتياطي.", alert=True)
        await safe_answer(cb)
        ok, path_or_err = security_svc.create_encrypted_backup()
        if not ok:
            return await safe_edit(cb, UITheme.error("فشل النسخ الاحتياطي", [path_or_err]), reply_markup=InlineKeyboardMarkup([[pbtn(t["back"], "admin_panel", style="danger")]]))
        v_ok, v_msg = security_svc.verify_and_restore_backup(path_or_err, test_only=True)
        security_svc.log_audit(uid, "backup", "create_and_verify", path_or_err, v_msg)
        await safe_send(client, uid, UITheme.success("نسخة احتياطية مشفرة", [v_msg]), document=path_or_err)
        return

    if data == "adm_audit_logs":
        await safe_answer(cb)
        conn = db.connect()
        try:
            rows = conn.execute("SELECT actor_id, category, action, target, created_at FROM audit_logs ORDER BY id DESC LIMIT 12").fetchall()
        finally:
            conn.close()
        a_lines = [f"[{r['created_at']}] <code>{r['actor_id']}</code>: {r['category']}.{r['action']} -> {r['target']}" for r in rows] or ["لا توجد سجلات."]
        await safe_edit(cb, UITheme.header("سجل العمليات (Audit Log)", "admin") + "\n\n" + UITheme.card("admin", a_lines), reply_markup=InlineKeyboardMarkup([[pbtn(t["back"], "admin_panel", style="danger")]]))
        return

    if data.startswith("adm_users_mgr_"):
        await safe_answer(cb)
        page = int(data.split("_")[3])
        conn = db.connect()
        try:
            rows = conn.execute("SELECT u.user_id, COALESCE(w.balance, 0) as bal FROM users_settings u LEFT JOIN wallets w ON u.user_id=w.user_id ORDER BY u.user_id DESC LIMIT 8 OFFSET ?", (page * 8,)).fetchall()
        finally:
            conn.close()
        kb_rows = [[pbtn(f"ID: {r['user_id']} | ${r['bal']:.2f}", f"adm_user_det_{r['user_id']}", style="primary")] for r in rows]
        kb_rows.append([pbtn(t["back"], "admin_panel", style="danger")])
        await safe_edit(cb, UITheme.header("إدارة المستخدمين", "admin"), reply_markup=InlineKeyboardMarkup(kb_rows))
        return

    if data.startswith("adm_user_det_"):
        await safe_answer(cb)
        tid = int(data.split("_")[3])
        bal = user_svc.get_wallet_balance(tid)
        banned = security_svc.is_banned(tid)
        await safe_edit(
            cb,
            UITheme.header(f"المستخدم {tid}", "admin") + "\n\n" + UITheme.card("users" if False else "admin", [f"الرصيد: <code>${bal:.2f}</code>", f"الحالة: <b>{'محظور' if banned else 'نشط'}</b>"]),
            reply_markup=InlineKeyboardMarkup([[pbtn("فك الحظر" if banned else "حظر المستخدم", f"adm_user_toggle_ban_{tid}", style="danger")], [pbtn(t["back"], "adm_users_mgr_0")]]),
        )
        return

    if data.startswith("adm_user_toggle_ban_"):
        tid = int(data.split("_")[4])
        ok, msg = security_svc.set_ban(uid, tid, not security_svc.is_banned(tid))
        await safe_answer(cb, msg, alert=True)
        cb.data = f"adm_user_det_{tid}"
        await on_callback_helper(client, cb, uid, t)
        return

    if data.startswith("adm_plans_mgr_"):
        await safe_answer(cb)
        page = int(data.split("_")[3])
        plans, _ = product_svc.list_plans(offset=page * 8, limit=8)
        kb_rows = [[pbtn(f"{p['name']} | ${p['price_usd']:.0f} | مخزون: {p['stock']}", f"adm_plan_det_{p['id']}")] for p in plans]
        kb_rows.append([pbtn(t["back"], "admin_panel", style="danger")])
        await safe_edit(cb, UITheme.header("إدارة الباقات والمخزون", "products"), reply_markup=InlineKeyboardMarkup(kb_rows))
        return

    if data.startswith("adm_plan_det_"):
        await safe_answer(cb)
        pid = int(data.split("_")[3])
        p = product_svc.get_plan(pid)
        if not p:
            return
        await safe_edit(
            cb,
            UITheme.header(p["name"], "products") + "\n\n" + UITheme.card("products", [f"السعر: <code>${p['price_usd']:.2f}</code>", f"المخزون: <code>{p['stock']}</code>"]),
            reply_markup=InlineKeyboardMarkup([[pbtn("تصفير المخزون", f"adm_plan_zero_{pid}", style="danger")], [pbtn(t["back"], "adm_plans_mgr_0")]]),
        )
        return

    if data.startswith("adm_plan_zero_"):
        pid = int(data.split("_")[3])
        conn = db.connect()
        try:
            conn.execute("UPDATE esims SET stock=0 WHERE id=?", (pid,))
            conn.commit()
        finally:
            conn.close()
        security_svc.log_audit(uid, "products", "zero_stock", str(pid))
        await safe_answer(cb, "تم تصفير المخزون.", alert=True)
        cb.data = f"adm_plan_det_{pid}"
        await on_callback_helper(client, cb, uid, t)
        return

    if data == "adm_cats_mgr":
        await safe_answer(cb)
        cats = product_svc.list_categories(dealer_only=False, visible_only=False) + product_svc.list_categories(dealer_only=True, visible_only=False)
        kb_rows = [[pbtn(f"{c['name_ar']} [{'ظاهر' if c['is_visible'] else 'مخفي'}]", f"adm_cat_toggle_{c['slug']}")] for c in cats]
        kb_rows.append([pbtn(t["back"], "admin_panel", style="danger")])
        await safe_edit(cb, UITheme.header("إدارة الأقسام (إضغط للتبديل)", "admin"), reply_markup=InlineKeyboardMarkup(kb_rows))
        return

    if data.startswith("adm_cat_toggle_"):
        slug = data.replace("adm_cat_toggle_", "")
        conn = db.connect()
        try:
            conn.execute("UPDATE categories SET is_visible = CASE WHEN is_visible=1 THEN 0 ELSE 1 END WHERE slug=?", (slug,))
            conn.commit()
        finally:
            conn.close()
        await safe_answer(cb, "تم تحديث حالة القسم.", alert=True)
        cb.data = "adm_cats_mgr"
        await on_callback_helper(client, cb, uid, t)
        return

    if data == "adm_coupons_mgr":
        await safe_answer(cb)
        conn = db.connect()
        try:
            rows = conn.execute("SELECT code, discount_type, discount_value, used_count, max_uses, is_active FROM coupons ORDER BY created_at DESC LIMIT 10").fetchall()
        finally:
            conn.close()
        c_lines = [f"<code>{r['code']}</code> | {r['discount_value']} ({r['discount_type']}) | {r['used_count']}/{r['max_uses']}" for r in rows] or ["لا توجد كوبونات."]
        await safe_edit(cb, UITheme.header("إدارة الكوبونات", "prices") + "\n\n" + UITheme.card("prices", c_lines), reply_markup=InlineKeyboardMarkup([[pbtn("إنشاء كوبون جديد", "adm_coupon_add", style="success")], [pbtn(t["back"], "admin_panel", style="danger")]]))
        return

    if data == "adm_coupon_add":
        await safe_answer(cb)
        sessions.set(uid, f"adm_coupon_add_{uid}", True)
        await safe_edit(cb, UITheme.header("إنشاء كوبون", "prices") + "\n\n" + UITheme.card("prices", ["أرسل الكوبون بالصيغة: <code>CODE | percent/fixed | القيمة | الحد</code>"]), reply_markup=InlineKeyboardMarkup([[pbtn(t["back"], "adm_coupons_mgr", style="danger")]]))
        return

    if data == "adm_pay_mgr":
        await safe_answer(cb)
        conn = db.connect()
        try:
            nets = conn.execute("SELECT network_name, binance_id, address FROM binance_networks").fetchall()
        finally:
            conn.close()
        n_lines = [f"<b>{n['network_name']}</b>: <code>{n['binance_id'] or n['address'] or '-'}</code>" for n in nets]
        await safe_edit(cb, UITheme.header("طرق وشبكات الدفع", "payments") + "\n\n" + UITheme.card("payments", n_lines), reply_markup=InlineKeyboardMarkup([[pbtn(t["back"], "admin_panel", style="danger")]]))
        return

    if data == "adm_emojis_mgr":
        await safe_answer(cb)
        kb_rows, row = [], []
        for cat in emoji_mgr.categories:
            row.append(pbtn(cat, f"adm_emo_cat_{cat}"))
            if len(row) == 3:
                kb_rows.append(row)
                row = []
        if row:
            kb_rows.append(row)
        kb_rows.append([pbtn(t["back"], "admin_panel", style="danger")])
        await safe_edit(cb, UITheme.header("تصنيفات الإيموجيات المخصصة", "premium"), reply_markup=InlineKeyboardMarkup(kb_rows))
        return

    if data.startswith("adm_emo_cat_"):
        await safe_answer(cb)
        cat = data.replace("adm_emo_cat_", "")
        mapping = emoji_mgr.categories.get(cat, {})
        lines_e = [f"<code>{k}</code>: <code>{v or 'فارغ'}</code>" for k, v in mapping.items()]
        await safe_edit(cb, UITheme.header(f"إيموجيات: {cat}", cat) + "\n\n" + UITheme.card(cat, lines_e), reply_markup=InlineKeyboardMarkup([[pbtn(t["back"], "adm_emojis_mgr", style="danger")]]))
        return

    if data in ("admin_add_balance", "admin_sub_balance", "admin_broadcast_msg"):
        await safe_answer(cb)
        sessions.set(uid, f"{data}_{uid}", True)
        prompt = "أرسل آيدي العميل ثم المبلغ (مثال: <code>123456 50</code>)" if "balance" in data else "أرسل نص الإذاعة العامة:"
        await safe_edit(cb, UITheme.header("إجراء إداري", "admin") + "\n\n" + UITheme.card("admin", [prompt]), reply_markup=InlineKeyboardMarkup([[pbtn(t["back"], "admin_panel", style="danger")]]))
        return

    if data.startswith("admin_approve_dep_"):
        await safe_answer(cb)
        parts = data.split("_")
        target_uid, amt = int(parts[3]), float(parts[4])
        await payment_svc.admin_adjust_wallet(uid, target_uid, amt, "admin_deposit", f"إيداع مقبول ${amt:.2f}")
        try:
            await safe_send(client, target_uid, UITheme.success("تم شحن محفظتك", [f"تمت إضافة <code>${amt:.2f}</code> بنجاح."]))
        except Exception:
            pass
        await safe_edit(cb, UITheme.success("تم القبول", [f"تم شحن <code>${amt:.2f}</code> للمستخدم <code>{target_uid}</code>."]), reply_markup=InlineKeyboardMarkup([[pbtn("لوحة الإدارة", "admin_panel")]]))
        return

    if data.startswith("admin_reject_dep_"):
        await safe_answer(cb)
        target_uid = int(data.split("_")[3])
        try:
            await safe_send(client, target_uid, UITheme.error("تم رفض الإيصال", ["يرجى التواصل مع الدعم الفني."]))
        except Exception:
            pass
        await safe_edit(cb, UITheme.warning("تم الرفض", ["تم إبلاغ المستخدم."]), reply_markup=InlineKeyboardMarkup([[pbtn("لوحة الإدارة", "admin_panel")]]))
        return


async def on_callback_helper(client, cb, uid, t):
    await _handle_admin_callbacks(client, cb, uid, cb.data, t)


async def _handle_admin_inputs(client: Client, uid: int, text: str, t: dict):
    if sessions.has(uid, f"admin_add_balance_{uid}"):
        sessions.remove(uid, f"admin_add_balance_{uid}")
        try:
            tid, amt = text.split()
            await payment_svc.admin_adjust_wallet(uid, int(tid), float(amt), "admin_deposit", "شحن إداري")
            await safe_send(client, uid, UITheme.success("تم الشحن", [f"تمت إضافة <code>${float(amt):.2f}</code> لـ <code>{tid}</code>."]))
        except Exception:
            await safe_send(client, uid, UITheme.error("صيغة خاطئة", ["مثال: <code>123456 50</code>"]))
        return

    if sessions.has(uid, f"admin_sub_balance_{uid}"):
        sessions.remove(uid, f"admin_sub_balance_{uid}")
        try:
            tid, amt = text.split()
            await payment_svc.admin_adjust_wallet(uid, int(tid), -float(amt), "admin_withdraw", "خصم إداري")
            await safe_send(client, uid, UITheme.success("تم الخصم", [f"تم خصم <code>${float(amt):.2f}</code> من <code>{tid}</code>."]))
        except Exception:
            await safe_send(client, uid, UITheme.error("صيغة خاطئة", ["مثال: <code>123456 20</code>"]))
        return

    if sessions.has(uid, f"adm_coupon_add_{uid}"):
        sessions.remove(uid, f"adm_coupon_add_{uid}")
        try:
            code, dtype, dval, max_u = [x.strip() for x in text.split("|")]
            conn = db.connect()
            try:
                conn.execute(
                    "INSERT OR REPLACE INTO coupons (code, discount_type, discount_value, max_uses, created_at) VALUES (?, ?, ?, ?, ?)",
                    (code.upper(), dtype, float(dval), int(max_u), datetime.now().strftime("%Y-%m-%d %H:%M")),
                )
                conn.commit()
            finally:
                conn.close()
            await safe_send(client, uid, UITheme.success("تم إنشاء الكوبون", [f"الكود: <code>{code.upper()}</code>"]))
        except Exception as e:
            await safe_send(client, uid, UITheme.error("خطأ", [str(e)]))
        return

    if sessions.has(uid, f"admin_broadcast_msg_{uid}"):
        sessions.remove(uid, f"admin_broadcast_msg_{uid}")
        conn = db.connect()
        try:
            users = [r["user_id"] for r in conn.execute("SELECT user_id FROM users_settings").fetchall()]
        finally:
            conn.close()
        succ, fail = 0, 0
        b_html = UITheme.header("إعلان رسمي من Aura eSIM", "admin", "broadcast") + "\n\n" + UITheme.card("home", [text])
        for target_u in users:
            try:
                await safe_send(client, target_u, b_html)
                succ += 1
                await asyncio.sleep(0.04)
            except FloodWait as e:
                await asyncio.sleep(e.value)
            except Exception:
                fail += 1
        security_svc.log_audit(uid, "broadcast", "send_all", f"succ={succ},fail={fail}")
        await safe_send(client, uid, UITheme.success("اكتملت الإذاعة", [f"نجاح: <code>{succ}</code> | فشل: <code>{fail}</code>"]))
        return



# ==============================================================================
# 23-25. Background Tasks, Startup/Shutdown & Main Execution
# ==============================================================================
async def background_maintenance_loop(app: Client):
    """مهام صيانة دورية: تنظيف الجلسات المنتهية وفحص صحة القاعدة."""
    while True:
        try:
            conn = db.connect()
            try:
                conn.execute("DELETE FROM user_sessions WHERE expires_at < datetime('now', 'localtime')")
                conn.commit()
            finally:
                conn.close()
        except Exception as e:
            logger.warning(f"Maintenance loop warning: {e}")
        await asyncio.sleep(1800)


def create_app() -> Client:
    if not API_ID or not API_HASH or not BOT_TOKEN:
        raise RuntimeError("يرجى ضبط API_ID و API_HASH و BOT_TOKEN في ملف .env قبل تشغيل البوت.")
    app = Client(
        "aura_esim_pyrogram",
        api_id=API_ID,
        api_hash=API_HASH,
        bot_token=BOT_TOKEN,
        in_memory=False,
    )
    register_handlers(app)
    return app


async def run_bot():
    app = create_app()
    await app.start()
    me = await app.get_me()
    logger.info(f"Aura eSIM Elite (Pyrogram) started as @{me.username} | DEV_ID={DEV_ID}")
    maint_task = asyncio.create_task(background_maintenance_loop(app))
    try:
        await asyncio.Event().wait()
    finally:
        maint_task.cancel()
        await app.stop()


if __name__ == "__main__":
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        logger.info("Bot stopped gracefully.")
    except Exception as exc:
        logger.error(f"Startup error: {exc}")
        sys.exit(1)
