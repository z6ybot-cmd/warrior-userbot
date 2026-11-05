import os
import asyncio
import sqlite3
import secrets
import io
import aiohttp
import time
import logging
import random
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
from telethon import TelegramClient, events, Button, errors

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

LANGS = {
    'ar': {
        'welcome': """
<blockquote>⧺︰ <b>أهلاً بك في البوابـة الرقمية الفاخرة لـ Aura eSIM Elite</b></blockquote>
<blockquote>⧺︰ <b>نقدم لك أحدث حلول الاتصالات والإنترنت الرقمي العالمي بأعلى معايير الجودة</b></blockquote>
<blockquote>⧺︰ <b>تفعيل فوري، آمن، ومباشر عبر QR Code أو التخطي اليدوي بضغطة زر</b></blockquote>
<blockquote>⧺︰ <b>سرعات فائقة بلا حدود وبدون سياسة استخدام عادل</b></blockquote>
<blockquote>⧺︰ <b>فريق دعم فني متواجد ومستعد لخدمتك على مدار الساعة</b></blockquote>
<blockquote>⧺︰ <b>اختر القسم المناسب لك من القائمة أدناه للبدء بكل سهولة</b></blockquote>
""",
        'choose_lang': "<blockquote>⧺︰ <b>يرجى اختيار لغتك المفضلة للمتابعة بسلاسة:</b></blockquote>",
        'lang_changed': "<blockquote>⧺︰ <b>تم تحويل اللغة بنجاح إلى العربية</b></blockquote>",
        'btn_personal': "قسم الأفراد (باقات الاستخدام الشخصي)",
        'btn_dealer': "قسم التجار والموزعين (الجملة بخصم 50%)",
        'btn_dealer_api': "شراء وتفعيل نظام الـ API ($100)",
        'btn_vodafone': "باقات Vodafone (اتصال + إنترنت)",
        'btn_holafly': "باقات Holafly (إنترنت لا محدود بدون استخدام عادل)",
        'btn_maya': "باقات Maya (سياسة استخدام عادل 5 جيجا يومياً)",
        'btn_dealer_vf': "باقات Vodafone تجار (10 شرائح جملة)",
        'btn_dealer_hf': "باقات Holafly تجار (10 شرائح جملة)",
        'btn_dealer_maya': "باقات Maya تجار (10 شرائح جملة)",
        'btn_countries': "الدول المدعومة وشبكات التغطية",
        'btn_cart': "سلة المشتريات",
        'btn_wallet': "محفظتي الشخصية",
        'btn_transactions': "سجل المعاملات المالية",
        'btn_orders': "طلباتي المكتملة",
        'btn_support': "الدعم الفني المباشر",
        'btn_verify_payment': "التحقق من الدفع وإرسال الإيصال",
        'btn_admin': "لوحة التحكم الإدارية",
        'btn_lang': "تغيير  اللغة / Language",
        'back': "رجوع",
        'admin_panel_title': "<blockquote>⧺︰ <b>لوحة التحكم الذكية والمطورة لإدارة متجر Aura eSIM</b></blockquote>",
        'stats_sales': "إجمالي الطلبات المكتملة",
        'stats_wallets': "إجمالي أرصدة المحافظ",
        'stats_esims': "إجمالي المخزون المتاح",
        'error_msg': "<blockquote>⧺︰ <b>عذراً، حدث خطأ غير متوقع. يرجى المحاولة مرة أخرى.</b></blockquote>",
        'insufficient_balance': "<blockquote>⧺︰ <b>رصيدك غير كافي لإتمام هذه العملية! يرجى شحن محفظتك أولاً.</b></blockquote>",
        'success_buy': "<blockquote>⧺︰ <b>تمت عملية الشراء بنجاح! إليك تفاصيل التفعيل الفوري (باركود أو تخطي يدوي):</b></blockquote>",
        'buy_now': "شراء الآن",
        'add_to_cart': "إضافة إلى سلة المشتريات",
        'confirm_buy': "تأكيد طلب الشراء النهائي",
        'pay_wallet': "الدفع الفوري من رصيد المحفظة",
        'pay_binance': "الدفع عبر المنصات وطرق الدفع المتاحة",
        'type_global': "باقة عالمية (تغطي كافة دول العالم)",
        'type_country': "باقة مخصصة (اختيار دولة معينة)",
        'select_type': "حدد نطاق التغطية المناسب لباقتك:",
        'select_country_prompt': "اختر الدولة المستهدفة أو ابحث عنها بالاسم:",
        'search_country_btn': "بحث عن دولة محدودة",
        'search_prompt': "أرسل اسم الدولة التي تبحث عنها:",
        'wallet_title': "<blockquote>⧺︰ <b>محفظتك الرقمية المتطورة</b></blockquote>",
        'current_balance': "الرصيد المتاح حالياً",
        'charge_wallet_btn': "شحن المحفظة (طرق الدفع والشبكات)",
        'charge_prompt': "<blockquote>⧺︰ <b>شحن المحفظة عبر شبكات العملات الرقمية والمعرفات</b></blockquote>\n\n> ⧺︰ <b>أرسل الآن المبلغ المراد إيداعه بالدولار (الحد الأدنى $20):</b>",
        'min_charge_err': "<blockquote>⧺︰ <b>⚠️ عذراً، الحد الأدنى لعملية الشحن هو $20</b></blockquote>",
        'invalid_number_err': "<blockquote>⧺︰ <b>⚠️ يرجى إدخال رقم صحيح وموجب حصرياً.</b></blockquote>",
        'my_orders_title': "<blockquote>⧺︰ <b>سجل طلباتك المكتملة (اضغط على أي طلب لاستعراض أكواد الباركود أو التخطي اليدوي)</b></blockquote>",
        'no_orders': "<blockquote>⧺︰ <b>ليس لديك أي طلبات شراء سابقة حتى هذه اللحظة.</b></blockquote>",
        'dealer_title': "<blockquote>⧺︰ <b>قسم التجار والموزعين (عروض الجملة 10 شرائح وسحب الخدمات عبر API)</b></blockquote>\n\n> ⧺︰ <b>اختر الخيار المناسب أدناه (خصم 50% دائم لمشتركي الـ API):</b>",
        'verify_prompt': "<blockquote>⧺︰ <b>نظام التحقق الآلي من المدفوعات والإيصالات</b></blockquote>\n\n> ⧺︰ <b>أرسل الآن معرف المعاملة (TxID) أو صورة الإيصال للتحقق السريع:</b>",
        'verify_sent': "<blockquote>⧺︰ <b>تم استلام إيصالك بنجاح وجاري مراجعته وإضافة الرصيد آلياً فور التحقق!</b></blockquote>",
        'support_prompt': "<blockquote>⧺︰ <b>نظام تذاكر الدعم الفني المباشر والاحترافي</b></blockquote>\n\n> ⧺︰ <b>اكتب رسالتك أو استفسارك وسيتم تحويله لفريق المختصين فوراً:</b>",
        'support_sent': "<blockquote>⧺︰ <b>تم إرسال تذكرتك بنجاح تام وسيتم الرد عليك في أقرب وقت ممكن.</b></blockquote>",
        'network_not_found': "عذراً، طريقة الدفع المختارة غير متوفرة أو تم تحديثها مؤخراً.",
        'show_all_payments_title': "<blockquote>⧺︰ <b>بوابة الدفع الشاملة لمتجر Aura eSIM</b>\n⧺︰ <b>المبلغ المطلوب تحويله:</b> <code>$$amount</code></blockquote>\n\n> ⧺︰ <b>إليك كافة عناوين ومعرفات الدفع المتاحة للتحويل:</b>",
        'show_all_payments_footer': "\n> ⧺︰ <b>قم بالتحويل عبر إحدى الطرق أعلاه، ثم اضغط على زر التحقق أدناه لتأكيد طلبك.</b>",
        'btn_verify_now': "التحقق من الدفع وإرسال الإيصال الآن",
        'countries_header': "<blockquote>⧺︰ <b>الدول المدعومة في شبكة Aura eSIM (COUNTRIES_COUNT دولة حول العالم):</b></blockquote>\n\n",
        'prev_page': "السابق",
        'next_page': "التالي"
    },
    'en': {
        'welcome': """
<blockquote>⧺︰ <b>Welcome to Aura eSIM Elite Gateway</b></blockquote>
<blockquote>⧺︰ <b>Providing next-gen global connectivity solutions</b></blockquote>
<blockquote>⧺︰ <b>Instant & secure QR Code or manual activation</b></blockquote>
<blockquote>⧺︰ <b>Ultra-fast speeds without throttling</b></blockquote>
<blockquote>⧺︰ <b>24/7 dedicated professional support</b></blockquote>
<blockquote>⧺︰ <b>Select a category below to get started</b></blockquote>
""",
        'choose_lang': "<blockquote>⧺︰ <b>Please select your preferred language:</b></blockquote>",
        'lang_changed': "<blockquote>⧺︰ <b>Language successfully changed to English</b></blockquote>",
        'btn_personal': "Personal Section",
        'btn_dealer': "Wholesale & Dealers (50% OFF)",
        'btn_dealer_api': "Subscribe & Activate API ($100)",
        'btn_vodafone': "Vodafone Plans (Voice + Data)",
        'btn_holafly': "Holafly Plans (Unlimited Data, No FUP)",
        'btn_maya': "Maya Plans (Fair Usage Policy 5GB/Day)",
        'btn_dealer_vf': "Vodafone Dealer Plans (10 eSIMs)",
        'btn_dealer_hf': "Holafly Dealer Plans (10 eSIMs)",
        'btn_dealer_maya': "Maya Dealer Plans (10 eSIMs)",
        'btn_countries': "Supported Countries & Coverage",
        'btn_cart': "Shopping Cart",
        'btn_wallet': "My Personal Wallet",
        'btn_transactions': "Transactions History",
        'btn_orders': "My Completed Orders",
        'btn_support': "Direct Support",
        'btn_verify_payment': "Verify Payment & Send Receipt",
        'btn_admin': "Admin Panel",
        'btn_lang': "Change Language / اللغة",
        'back': "Back",
        'admin_panel_title': "<blockquote>⧺︰ <b>Aura eSIM Comprehensive Admin Panel</b></blockquote>",
        'stats_sales': "Completed Orders",
        'stats_wallets': "Total Wallets Balance",
        'stats_esims': "Total Stock",
        'error_msg': "<blockquote>⧺︰ <b>An unexpected error occurred. Please try again.</b></blockquote>",
        'insufficient_balance': "<blockquote>⧺︰ <b>Insufficient balance! Please charge your wallet first to purchase.</b></blockquote>",
        'success_buy': "<blockquote>⧺︰ <b>Successfully purchased! Here are your activation details (Barcode or Manual):</b></blockquote>",
        'buy_now': "Buy Now",
        'add_to_cart': "Add to Shopping Cart",
        'confirm_buy': "Confirm Order",
        'pay_wallet': "Pay from Wallet",
        'pay_binance': "Pay via Available Payment Methods",
        'type_global': "Global Plan (Covers All Countries)",
        'type_country': "Choose a Specific Country",
        'select_type': "Choose coverage type for your plan:",
        'select_country_prompt': "Select the desired country or use search:",
        'search_country_btn': "Search Country",
        'search_prompt': "Send the name of the country you want to search for:",
        'wallet_title': "<blockquote>⧺︰ <b>Your Personal Wallet</b></blockquote>",
        'current_balance': "Current Balance",
        'charge_wallet_btn': "Charge Wallet (Available Payment Methods)",
        'charge_prompt': "<blockquote>⧺︰ <b>Charge Wallet via Crypto Networks & IDs</b></blockquote>\n\n> ⧺︰ <b>Send the amount you want to deposit in USD (Minimum $25):</b>",
        'min_charge_err': "<blockquote>⧺︰ <b>⚠️ Minimum deposit amount is $20</b></blockquote>",
        'invalid_number_err': "<blockquote>⧺︰ <b>⚠️ Please send a valid positive number.</b></blockquote>",
        'my_orders_title': "<blockquote>⧺︰ <b>Your Completed Orders (Click any order to reload activation barcode or manual setup)</b></blockquote>",
        'no_orders': "<blockquote>⧺︰ <b>You have no previous orders yet.</b></blockquote>",
        'dealer_title': "<blockquote>⧺︰ <b>Dealers & API Section (50% OFF All Services)</b></blockquote>\n\n> ⧺︰ <b>Choose option below:</b>",
        'verify_prompt': "<blockquote>⧺︰ <b>Automatic Payment Verification</b></blockquote>\n\n> ⧺︰ <b>Send your transaction ID (TxID) or screenshot for instant verification:</b>",
        'verify_sent': "<blockquote>⧺︰ <b>Your receipt has been received successfully. Processing and crediting balance!</b></blockquote>",
        'support_prompt': "<blockquote>⧺︰ <b>Direct Support Ticket System</b></blockquote>\n\n> ⧺︰ <b>Send your message or inquiry now:</b>",
        'support_sent': "<blockquote>⧺︰ <b>Your support ticket has been sent successfully. We will reply soon!</b></blockquote>",
        'network_not_found': "Sorry, the selected payment method does not exist or has been updated.",
        'show_all_payments_title': "<blockquote>⧺︰ <b>Comprehensive Payment Gateway for Aura eSIM</b>\n\n> ⧺︰ <b>Amount to transfer:</b> <code>$$amount</code></blockquote>\n\n> ⧺︰ <b>Here are all available payment methods, IDs, and addresses:</b>",
        'show_all_payments_footer': "\n> ⧺︰ <b>Transfer via any of the methods above, then click the verify button below to send your receipt or TxID.</b>",
        'btn_verify_now': "Verify Payment Now & Send Receipt",
        'countries_header': "<blockquote>⧺︰ <b>Supported Countries in Aura eSIM Store (COUNTRIES_COUNT countries worldwide):</b></blockquote>\n\n",
        'prev_page': "Previous",
        'next_page': "Next"
    }
}

WARRANTY_POLICY_TEXT = {
    'ar': """
<blockquote>⧺︰ <b>سياسات ومميزات الشرائح حسب المزود (Aura eSIM Elite):</b>
⧺︰ <b>شرائح هولافلاي (Holafly) : إنترنت لا محدود بالكامل وبدون أي سياسة استخدام عادل (True Unlimited Data).</b>
⧺︰ <b>شرائح مايا (Maya) : تخضع لسياسة الاستخدام العادل (5 جيجا يومياً بسرعة فائقة 5G، ثم إنترنت لا محدود بسرعات مخفضة).</b>
⧺︰ <b>شرائح فودافون (Vodafone) : إنترنت فائق السرعة مع دقائق اتصال محلية ودولية رسمية.</b>
⧺︰ <b>ملاحظة: باقات Maya وباقات Holafly مخصصة للإنترنت فقط بدون رقم اتصال.</b></blockquote>

<blockquote>⧺︰ <b>باقة الضمان الذهبي والدعم الفني (راحة بالك هي غايتنا):</b>
⧺︰ <b>ضمان شامل ومستمر : دعم فني متخصص ومتاح لخدمتك على مدار الساعة.</b>
⧺︰ <b>سياسة تعويض فورية وآمنة : حقوقك محفوظة بتمديد الفترة أو شريحة بديلة فورا.</b>
⧺︰ <b>ضمان التخزين المرن (3 أشهر) : الاحتفاظ بالشريحة وتفعيلها خلال 3 أشهر.</b></blockquote>
""",
    'en': """
<blockquote>⧺︰ <b>eSIM Policies & Features by Provider:</b>
⧺︰ <b>Holafly Plans : True unlimited data with ZERO Fair Usage Policy (FUP).</b>
⧺︰ <b>Maya Plans : Subject to Fair Usage Policy (5 GB daily at ultra-fast speed, then unlimited data).</b>
⧺︰ <b>Vodafone Plans : Ultra-fast internet with local & international calling minutes.</b>
⧺︰ <b>Note: Maya and Holafly plans are data-only, no number.</b></blockquote>

<blockquote>⧺︰ <b>Golden Warranty & Support Package:</b>
⧺︰ <b>Comprehensive Warranty : 24/7 professional technical support team.</b>
⧺︰ <b>Instant Compensation Policy : Protected with replacement or extension.</b>
⧺︰ <b>Flexible Storage Warranty (3 Months) : Activate within 3 months.</b></blockquote>
"""
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
                alert_msg = f"⚠️ <b>تنبيه انخفاض مخزون شريحة!</b>\n\n• الباقة: <b>{name}</b>\n• المتبقي حالياً: <code>{stock} قطع</code>\n\nيرجى إعادة تعبئة المخزون مبكراً!"
                await client.send_message(DEV_ID, alert_msg, parse_mode='html')
            except Exception as e:
                logger.error(f"Low stock alert error: {e}")

def main_menu(uid):
    lang = get_user_lang(uid) or 'ar'
    t = LANGS.get(lang, LANGS['ar'])
    balance = get_wallet_balance(uid)
    
    api_row = cur.execute("SELECT id FROM dealer_api_keys WHERE user_id=?", (uid,)).fetchone()
    has_api = api_row is not None

    btn = [
        [Button.inline(t['btn_personal'], b'personal_section')],
        [Button.inline(t['btn_dealer'], b'dealer_section')],
    ]
    if not has_api:
        btn.append([Button.inline(t['btn_dealer_api'], b'buy_api_sub_menu')])
        
    btn.extend([
        [Button.inline(t['btn_countries'], b'countries_list')], 
        [Button.inline(t['btn_cart'], b'view_cart'), Button.inline(f"{t['btn_wallet']} : ${balance:.2f}", b'wallet')], 
        [Button.inline(t['btn_orders'], b'my_orders'), Button.inline(t['btn_support'], b'support_ticket')],
        [Button.inline(t['btn_lang'], b'change_language')]
    ])
    if is_admin(uid):
        btn.append([Button.inline(t['btn_admin'], b'admin_panel')])

    text = t['welcome']
    return text, btn

COUNTRIES_DATA = [
    {"name": "Afghanistan", "flag": "🇦🇫", "operators": "AWCC, Etisalat"},
    {"name": "Albania", "flag": "🇦🇱", "operators": "Vodafone, Telekom"},
    {"name": "Algeria", "flag": "🇩🇿", "operators": "Djezzy, Mobilis"},
    {"name": "Andorra", "flag": "🇦🇩", "operators": "Andorra Telecom, Orange"},
    {"name": "Angola", "flag": "🇦🇴", "operators": "Unitel, Movicel"},
    {"name": "Antigua and Barbuda", "flag": "🇦🇬", "operators": "Flow, Digicel"},
    {"name": "Argentina", "flag": "🇦🇷", "operators": "Claro, Movistar"},
    {"name": "Armenia", "flag": "🇦🇲", "operators": "VivaCell, Beeline"},
    {"name": "Australia", "flag": "🇦🇺", "operators": "Telstra, Optus, Vodafone"},
    {"name": "Austria", "flag": "🇦🇹", "operators": "A1, T-Mobile, Magenta"},
    {"name": "Azerbaijan", "flag": "🇦🇿", "operators": "Azercell, Bakcell"},
    {"name": "Bahamas", "flag": "🇧🇸", "operators": "BTC, Aliv"},
    {"name": "Bahrain", "flag": "🇧🇭", "operators": "Batelco, Zain, STC"},
    {"name": "Bangladesh", "flag": "🇧🇩", "operators": "Grameenphone, Robi"},
    {"name": "Barbados", "flag": "🇧🇧", "operators": "Flow, Digicel"},
    {"name": "Belarus", "flag": "🇧🇾", "operators": "MTS, A1"},
    {"name": "Belgium", "flag": "🇧🇪", "operators": "Proximus, Orange, Base"},
    {"name": "Belize", "flag": "🇧🇿", "operators": "BTL, Digi"},
    {"name": "Benin", "flag": "🇧🇯", "operators": "MTN, Moov"},
    {"name": "Bhutan", "flag": "🇧🇹", "operators": "B-Mobile, TashiCell"},
    {"name": "Bolivia", "flag": "🇧🇴", "operators": "Tigo, Entel"},
    {"name": "Bosnia and Herzegovina", "flag": "🇧🇦", "operators": "BH Telecom, m:tel"},
    {"name": "Botswana", "flag": "🇧🇼", "operators": "Mascom, Orange"},
    {"name": "Brazil", "flag": "🇧🇷", "operators": "Vivo, TIM, Claro"},
    {"name": "Brunei", "flag": "🇧🇳", "operators": "DST, Progresif"},
    {"name": "Bulgaria", "flag": "🇧🇬", "operators": "A1, Vivacom, Telenor"},
    {"name": "Burkina Faso", "flag": "🇧🇫", "operators": "Orange, Telmob"},
    {"name": "Burundi", "flag": "🇧🇮", "operators": "Econet, Lumitel"},
    {"name": "Cambodia", "flag": "🇰🇭", "operators": "Smart, Cellcard, Metfone"},
    {"name": "Cameroon", "flag": "🇨🇲", "operators": "MTN, Orange"},
    {"name": "Canada", "flag": "🇨🇦", "operators": "Rogers, Bell, Telus"},
    {"name": "Cape Verde", "flag": "🇨🇻", "operators": "CVMovel, Unitel"},
    {"name": "Central African Republic", "flag": "🇨🇫", "operators": "Orange, Telecel"},
    {"name": "Chad", "flag": "🇹🇩", "operators": "Airtel, Tigo"},
    {"name": "Chile", "flag": "🇨🇱", "operators": "Entel, Claro, Movistar"},
    {"name": "China", "flag": "🇨🇳", "operators": "China Mobile, China Unicom, China Telecom"},
    {"name": "Colombia", "flag": "🇨🇴", "operators": "Claro, Movistar, Tigo"},
    {"name": "Comoros", "flag": "🇰🇲", "operators": "Comores Telecom, Telma"},
    {"name": "Congo", "flag": "🇨🇬", "operators": "MTN, Airtel"},
    {"name": "Costa Rica", "flag": "🇨🇷", "operators": "Kölbi, Claro, Movistar"},
    {"name": "Croatia", "flag": "🇭🇷", "operators": "HT, A1, Telemach"},
    {"name": "Cuba", "flag": "🇨🇺", "operators": "ETECSA"},
    {"name": "Cyprus", "flag": "🇨🇾", "operators": "Cyta, MTN, Epic"},
    {"name": "Czech Republic", "flag": "🇨🇿", "operators": "O2, T-Mobile, Vodafone"},
    {"name": "Denmark", "flag": "🇩🇰", "operators": "TDC, Telia, Telenor"},
    {"name": "Djibouti", "flag": "🇩🇯", "operators": "Djibouti Telecom"},
    {"name": "Dominica", "flag": "🇩🇲", "operators": "Flow, Digicel"},
    {"name": "Dominican Republic", "flag": "🇩🇴", "operators": "Claro, Altice, Viva"},
    {"name": "Ecuador", "flag": "🇪🇨", "operators": "Claro, Movistar, CNT"},
    {"name": "Egypt", "flag": "🇪🇬", "operators": "Vodafone, Orange, Etisalat, WE"},
    {"name": "El Salvador", "flag": "🇸🇻", "operators": "Claro, Tigo, Movistar"},
    {"name": "Equatorial Guinea", "flag": "🇬🇶", "operators": "Geocom, Orange"},
    {"name": "Eritrea", "flag": "🇪🇷", "operators": "EriTel"},
    {"name": "Estonia", "flag": "🇪🇪", "operators": "Telia, Elisa, Tele2"},
    {"name": "Eswatini", "flag": "🇸🇿", "operators": "Eswatini Mobile, MTN"},
    {"name": "Ethiopia", "flag": "🇪🇹", "operators": "Ethio Telecom, Safaricom"},
    {"name": "Fiji", "flag": "🇫🇯", "operators": "Vodafone, Digicel"},
    {"name": "Finland", "flag": "🇫🇮", "operators": "Elisa, Telia, DNA"},
    {"name": "France", "flag": "🇫🇷", "operators": "Orange, SFR, Free, Bouygues"},
    {"name": "Gabon", "flag": "🇬🇦", "operators": "Gabon Telecom, Airtel"},
    {"name": "Gambia", "flag": "🇬🇲", "operators": "Qcell, Africell"},
    {"name": "Georgia", "flag": "🇬🇪", "operators": "Magti, Cellfie, Beeline"},
    {"name": "Germany", "flag": "🇩🇪", "operators": "T-Mobile, Vodafone, O2"},
    {"name": "Ghana", "flag": "🇬🇭", "operators": "MTN, Vodafone, AirtelTigo"},
    {"name": "Greece", "flag": "🇬🇷", "operators": "Cosmote, Vodafone, Nova"},
    {"name": "Grenada", "flag": "🇬🇩", "operators": "Flow, Digicel"},
    {"name": "Guatemala", "flag": "🇬🇹", "operators": "Claro, Tigo"},
    {"name": "Guinea", "flag": "🇬🇳", "operators": "Orange, MTN, Cellcom"},
    {"name": "Guinea-Bissau", "flag": "🇬🇼", "operators": "MTN, Orange"},
    {"name": "Guyana", "flag": "🇬🇾", "operators": "GTT, Digicel"},
    {"name": "Haiti", "flag": "🇭🇹", "operators": "Natcom, Digicel"},
    {"name": "Honduras", "flag": "🇭🇳", "operators": "Tigo, Claro"},
    {"name": "Hong Kong", "flag": "🇭🇰", "operators": "CSL, 3, SmarTone"},
    {"name": "Hungary", "flag": "🇭🇺", "operators": "Magyar Telekom, Telenor, Vodafone"},
    {"name": "Iceland", "flag": "🇮🇸", "operators": "Síminn, Vodafone, Nova"},
    {"name": "India", "flag": "🇮🇳", "operators": "Jio, Airtel, Vi"},
    {"name": "Indonesia", "flag": "🇮🇩", "operators": "Telkomsel, Indosat, XL Axiata"},
    {"name": "Iran", "flag": "🇮🇷", "operators": "MCI, Irancell, Rightel"},
    {"name": "Iraq", "flag": "🇮🇶", "operators": "Zain, Asiacell, Korek"},
    {"name": "Ireland", "flag": "🇮🇪", "operators": "Vodafone, Three, Eir"},
    {"name": "Israel", "flag": "🇮🇱", "operators": "Cellcom, Pelephone, Partner"},
    {"name": "Italy", "flag": "🇮🇹", "operators": "TIM, Vodafone, WindTre, Iliad"},
    {"name": "Jamaica", "flag": "🇯🇲", "operators": "Digicel, Flow"},
    {"name": "Japan", "flag": "🇯🇵", "operators": "NTT Docomo, KDDI, SoftBank, Rakuten"},
    {"name": "Jordan", "flag": "🇯🇴", "operators": "Orange, Zain, Umniah"},
    {"name": "Kazakhstan", "flag": "🇰🇿", "operators": "Kcell, Beeline, Tele2"},
    {"name": "Kenya", "flag": "🇰🇪", "operators": "Safaricom, Airtel, Telkom"},
    {"name": "Kiribati", "flag": "🇰🇮", "operators": "Telecom Kiribati"},
    {"name": "Kuwait", "flag": "🇰🇼", "operators": "Zain, Ooredoo, STC"},
    {"name": "Kyrgyzstan", "flag": "🇰🇬", "operators": "Beeline, MegaCom, O!"},
    {"name": "Laos", "flag": "🇱🇦", "operators": "Lao Telecom, Unitel, ETL"},
    {"name": "Latvia", "flag": "🇱🇻", "operators": "LMT, Tele2, Bite"},
    {"name": "Lebanon", "flag": "🇱🇧", "operators": "Alfa, Touch"},
    {"name": "Lesotho", "flag": "🇱🇸", "operators": "Vodacom, Econet"},
    {"name": "Liberia", "flag": "🇱🇷", "operators": "Orange, MTN"},
    {"name": "Libya", "flag": "🇱🇾", "operators": "LTT, Almadar, Libyana"},
    {"name": "Liechtenstein", "flag": "🇱🇮", "operators": "Telecom Liechtenstein, Salt"},
    {"name": "Lithuania", "flag": "🇱🇹", "operators": "Telia, Tele2, Bite"},
    {"name": "Luxembourg", "flag": "🇱🇺", "operators": "POST, Orange, Tango"},
    {"name": "Madagascar", "flag": "🇲🇬", "operators": "Orange, Telma, Airtel"},
    {"name": "Malawi", "flag": "🇲🇼", "operators": "Airtel, TNM"},
    {"name": "Malaysia", "flag": "🇲🇾", "operators": "Maxis, Celcom, Digi, U Mobile"},
    {"name": "Maldives", "flag": "🇲🇻", "operators": "Dhiraagu, Ooredoo"},
    {"name": "Mali", "flag": "🇲🇱", "operators": "Orange, Malitel"},
    {"name": "Malta", "flag": "🇲🇹", "operators": "GO, Melita, Epic"},
    {"name": "Marshall Islands", "flag": "🇲🇭", "operators": "NTA"},
    {"name": "Mauritania", "flag": "🇲🇷", "operators": "Mauritel, Chinguitel, Mattel"},
    {"name": "Mauritius", "flag": "🇲🇺", "operators": "My.T, Emtel, Chili"},
    {"name": "Mexico", "flag": "🇲🇽", "operators": "Telcel, AT&T, Movistar"},
    {"name": "Micronesia", "flag": "🇫🇲", "operators": "FSM Telecom"},
    {"name": "Moldova", "flag": "🇲🇩", "operators": "Orange, Moldcell, Unite"},
    {"name": "Monaco", "flag": "🇲🇨", "operators": "Monaco Telecom"},
    {"name": "Mongolia", "flag": "🇲🇳", "operators": "Mobicom, Unitel, Skytel"},
    {"name": "Montenegro", "flag": "🇲🇪", "operators": "Telekom, Telenor, M-tel"},
    {"name": "Morocco", "flag": "🇲🇦", "operators": "Maroc Telecom, Orange, Inwi"},
    {"name": "Mozambique", "flag": "🇲🇿", "operators": "Vodacom, Movitel"},
    {"name": "Myanmar", "flag": "🇲🇲", "operators": "MPT, Ooredoo, Telenor/Atom, Mytel"},
    {"name": "Namibia", "flag": "🇳🇦", "operators": "MTC, Telecom Namibia"},
    {"name": "Nauru", "flag": "🇳🇷", "operators": "Digicel"},
    {"name": "Nepal", "flag": "🇳🇵", "operators": "Nepal Telecom, Ncell"},
    {"name": "Netherlands", "flag": "🇳🇱", "operators": "KPN, Vodafone, T-Mobile"},
    {"name": "New Zealand", "flag": "🇳🇿", "operators": "Spark, Vodafone, 2degrees"},
    {"name": "Nicaragua", "flag": "🇳🇮", "operators": "Claro, Tigo"},
    {"name": "Niger", "flag": "🇳🇪", "operators": "Airtel, Moov"},
    {"name": "Nigeria", "flag": "🇳🇬", "operators": "MTN, Airtel, Glo, 9mobile"},
    {"name": "North Korea", "flag": "🇰🇵", "operators": "Koryolink"},
    {"name": "North Macedonia", "flag": "🇲🇰", "operators": "Telekom, A1"},
    {"name": "Norway", "flag": "🇳🇴", "operators": "Telenor, Telia, Ice"},
    {"name": "Oman", "flag": "🇴🇲", "operators": "Omantel, Ooredoo, Vodafone"},
    {"name": "Pakistan", "flag": "🇵🇰", "operators": "Jazz, Zong, Telenor, Ufone"},
    {"name": "Palau", "flag": "🇵🇼", "operators": "PNCC"},
    {"name": "Palestine", "flag": "🇵🇸", "operators": "Jawwal, Ooredoo"},
    {"name": "Panama", "flag": "🇵🇦", "operators": "Cable & Wireless, Tigo, Claro"},
    {"name": "Papua New Guinea", "flag": "🇵🇬", "operators": "Digicel, bmobile"},
    {"name": "Paraguay", "flag": "🇵🇾", "operators": "Tigo, Claro, Personal"},
    {"name": "Peru", "flag": "🇵🇪", "operators": "Claro, Movistar, Entel, Bitel"},
    {"name": "Philippines", "flag": "🇵🇭", "operators": "Globe, Smart, Dito"},
    {"name": "Poland", "flag": "🇵🇱", "operators": "Orange, Play, T-Mobile, Plus"},
    {"name": "Portugal", "flag": "🇵🇹", "operators": "MEO, NOS, Vodafone"},
    {"name": "Qatar", "flag": "🇶🇦", "operators": "Ooredoo, Vodafone"},
    {"name": "Romania", "flag": "🇷🇴", "operators": "Orange, Vodafone, Digi, Telekom"},
    {"name": "Russia", "flag": "🇷🇺", "operators": "MTS, Beeline, Megafon, Tele2"},
    {"name": "Rwanda", "flag": "🇷🇼", "operators": "MTN, Airtel"},
    {"name": "Saint Kitts and Nevis", "flag": "🇰🇳", "operators": "Flow, Digicel"},
    {"name": "Saint Lucia", "flag": "🇱🇨", "operators": "Flow, Digicel"},
    {"name": "Samoa", "flag": "🇼🇸", "operators": "Vodafone, Digicel"},
    {"name": "San Marino", "flag": "🇸🇲", "operators": "TIM, San Marino Telecom"},
    {"name": "Sao Tome and Principe", "flag": "🇸🇹", "operators": "CSTmóvel"},
    {"name": "Saudi Arabia", "flag": "🇸🇦", "operators": "STC, Mobily, Zain"},
    {"name": "Senegal", "flag": "🇸🇳", "operators": "Orange, Free, Expresso"},
    {"name": "Serbia", "flag": "🇷🇸", "operators": "Telekom Srbija, Yettel, A1"},
    {"name": "Seychelles", "flag": "🇸🇨", "operators": "Airtel, Cable & Wireless"},
    {"name": "Sierra Leone", "flag": "🇸🇱", "operators": "Orange, Africell"},
    {"name": "Singapore", "flag": "🇸🇬", "operators": "Singtel, StarHub, M1, SIMBA"},
    {"name": "Slovakia", "flag": "🇸🇰", "operators": "Orange, Telekom, O2, 4ka"},
    {"name": "Slovenia", "flag": "🇸🇮", "operators": "Telekom Slovenije, A1, Telemach"},
    {"name": "Solomon Islands", "flag": "🇸🇧", "operators": "Our Telekom, Bintang"},
    {"name": "Somalia", "flag": "🇸🇴", "operators": "Hormuud, Somtel"},
    {"name": "South Africa", "flag": "🇿🇦", "operators": "Vodacom, MTN, Cell C, Telkom"},
    {"name": "South Korea", "flag": "🇰🇷", "operators": "SK Telecom, KT, LG Uplus"},
    {"name": "South Sudan", "flag": "🇸🇸", "operators": "MTN, Zain"},
    {"name": "Spain", "flag": "🇪🇸", "operators": "Movistar, Vodafone, Orange, Yoigo"},
    {"name": "Sri Lanka", "flag": "🇱🇰", "operators": "Dialog, Mobitel, Hutch"},
    {"name": "Sudan", "flag": "🇸🇩", "operators": "Zain, MTN, Sudani"},
    {"name": "Suriname", "flag": "🇸🇷", "operators": "Telesur, Digicel"},
    {"name": "Sweden", "flag": "🇸🇪", "operators": "Telia, Telenor, Tele2, Tre"},
    {"name": "Switzerland", "flag": "🇨🇭", "operators": "Swisscom, Sunrise, Salt"},
    {"name": "Syria", "flag": "🇸🇾", "operators": "Syriatel, MTN"},
    {"name": "Taiwan", "flag": "🇹🇼", "operators": "Chunghwa Telecom, Taiwan Mobile, FarEasTone"},
    {"name": "Tajikistan", "flag": "🇹🇯", "operators": "Tcell, Beeline, Megafon"},
    {"name": "Tanzania", "flag": "🇹🇿", "operators": "Vodacom, Airtel, Tigo, Halotel"},
    {"name": "Thailand", "flag": "🇹🇭", "operators": "AIS, True Move H, DTAC"},
    {"name": "Timor-Leste", "flag": "🇹🇱", "operators": "Telemor, Timor Telecom, Telkomcel"},
    {"name": "Togo", "flag": "🇹🇬", "operators": "Togocel, Moov"},
    {"name": "Tonga", "flag": "🇹🇴", "operators": "Digicel, Tones"},
    {"name": "Trinidad and Tobago", "flag": "🇹🇹", "operators": "TSTT, Digicel"},
    {"name": "Tunisia", "flag": "🇹🇳", "operators": "Ooredoo, Orange, Tunisie Telecom"},
    {"name": "Turkey", "flag": "🇹🇷", "operators": "Turkcell, Vodafone, Türk Telekom"},
    {"name": "Turkmenistan", "flag": "🇹🇲", "operators": "TM Cell"},
    {"name": "Tuvalu", "flag": "🇹🇻", "operators": "Tuvalu Telecom"},
    {"name": "Uganda", "flag": "🇺🇬", "operators": "MTN, Airtel"},
    {"name": "Ukraine", "flag": "🇺🇦", "operators": "Kyivstar, Vodafone, lifecell"},
    {"name": "United Arab Emirates", "flag": "🇦🇪", "operators": "Etisalat (e&), du, Virgin Mobile"},
    {"name": "United Kingdom", "flag": "🇬🇧", "operators": "EE, Vodafone, O2, Three"},
    {"name": "United States", "flag": "🇺🇸", "operators": "Verizon, AT&T, T-Mobile"},
    {"name": "Uruguay", "flag": "🇺🇾", "operators": "Antel, Movistar, Claro"},
    {"name": "Uzbekistan", "flag": "🇺🇿", "operators": "Ucell, Beeline, Uzmobile, UMS"},
    {"name": "Vanuatu", "flag": "🇻🇺", "operators": "Digicel, Vodafone"},
    {"name": "Vatican City", "flag": "🇻🇦", "operators": "Vatican Telecom"},
    {"name": "Venezuela", "flag": "🇻🇪", "operators": "Movistar, Digicel, Movilnet"},
    {"name": "Vietnam", "flag": "🇻🇳", "operators": "Viettel, Vinaphone, Mobifone"},
    {"name": "Yemen", "flag": "🇾🇪", "operators": "You, Sabafon, Yemen Mobile"},
    {"name": "Zambia", "flag": "🇿🇲", "operators": "Airtel, MTN, Zamtel"},
    {"name": "Zimbabwe", "flag": "🇿🇼", "operators": "Econet, NetOne, Telecel"}
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

@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    uid = event.sender_id
    if is_banned(uid): return
    
    try:
        user_entity = await event.sender
        u_name = user_entity.first_name if user_entity else "مستخدم"
        u_uname = f"@{user_entity.username}" if user_entity and user_entity.username else "بدون معرف"
        notif_text = f"🚨 <b>إشعار دخول مستخدم جديد للبوت!</b>\n\n• الاسم: {u_name}\n• المعرف: {u_uname}\n• الآيدي: <code>{uid}</code>\n• الوقت: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        await client.send_message(DEV_ID, notif_text, parse_mode='html')
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
        except:
            pass

    current_lang = get_user_lang(uid)
    if not current_lang:
        btn = [
            [Button.inline("🇸🇦 العربية", b'set_lang_ar'), Button.inline("🇬🇧 English", b'set_lang_en')]
        ]
        await event.reply(
            "<blockquote>⧺︰ <b>Welcome to Aura eSIM Elite! اختر لغتك المفضلة / Please select your language:</b></blockquote>",
            buttons=btn, parse_mode='html'
        )
        return

    text, btn = main_menu(uid)
    await event.reply(text, buttons=btn, parse_mode='html')

@client.on(events.CallbackQuery)
async def callback(event):
    uid = event.sender_id
    if is_banned(uid): return
    data = event.data.decode()
    lang = get_user_lang(uid) or 'ar'
    t = LANGS.get(lang, LANGS['ar'])
    
    if data.startswith('set_lang_'):
        await event.answer()
        new_l = data.split('_')[2]
        set_user_lang(uid, new_l)
        new_t = LANGS.get(new_l, LANGS['ar'])
        await event.answer(new_t['lang_changed'], alert=True)
        text, btn = main_menu(uid)
        await event.edit(text, buttons=btn, parse_mode='html')
        return

    if data == 'main':
        await event.answer()
        text, btn = main_menu(uid)
        await event.edit(text, buttons=btn, parse_mode='html')

    elif data == 'change_language':
        await event.answer()
        btn = [
            [Button.inline("🇸🇦 العربية", b'set_lang_ar'), Button.inline("🇬🇧 English", b'set_lang_en')],
            [Button.inline(t['back'], b'main')]
        ]
        await event.edit("<blockquote>⧺︰ <b>اختر لغتك / Select language:</b></blockquote>", buttons=btn, parse_mode='html')

    # قسم الأفراد (يعرض الأقسام المفعلة والظاهرة فقط)
    elif data == 'personal_section':
        await event.answer()
        cats = cur.execute("SELECT slug, name_ar, name_en FROM categories WHERE slug NOT LIKE 'dealer_%' AND is_visible=1").fetchall()
        btn = []
        for slug, nar, nen in cats:
            lbl = nar if lang == 'ar' else nen
            btn.append([Button.inline(lbl, f'open_cat_{slug}'.encode())])
        btn.append([Button.inline(t['back'], b'main')])
        await event.edit(f"<blockquote>⧺︰ <b>{t['btn_personal']}</b></blockquote>", buttons=btn, parse_mode='html')

    elif data.startswith('open_cat_'):
        await event.answer()
        cat = data.replace('open_cat_', '')
        plans = cur.execute("SELECT id, name, price_usd, months, minutes FROM esims WHERE category=? ORDER BY months ASC", (cat,)).fetchall()
        btn = []
        for pid, name, price, m, mins in plans:
            min_str = f" ({mins} دقيقة)" if mins > 0 else ""
            btn.append([Button.inline(f"{name}{min_str} - ${price:.0f}", f'show_plan_{pid}_1'.encode())])
        
        back_btn = b'personal_section' if not cat.startswith('dealer_') else b'dealer_section'
        btn.append([Button.inline(t['back'], back_btn)])
        
        cat_info = cur.execute("SELECT name_ar, name_en FROM categories WHERE slug=?", (cat,)).fetchone()
        title_cat = (cat_info[0] if lang == 'ar' else cat_info[1]) if cat_info else cat
        policy = WARRANTY_POLICY_TEXT.get(lang, WARRANTY_POLICY_TEXT['ar'])
        select_dur = "اختر المدة المطلوبة:" if lang == 'ar' else "Select desired duration:"
        await event.edit(f"<blockquote>⧺︰ <b>{title_cat}</b></blockquote>\n\n{policy}\n\n> ⧺︰ <b>{select_dur}</b>", buttons=btn, parse_mode='html')

    # ========================================================
    # إظهار تفاصيل الشريحة والكميات والخصم 10%
    # ========================================================
    elif data.startswith('show_plan_'):
        await event.answer()
        parts = data.split('_')
        pid = int(parts[2])
        qty = int(parts[3]) if len(parts) > 3 else 1
        if qty < 1: qty = 1
        if qty > 50: qty = 50

        plan = cur.execute("SELECT id, name, price_usd, minutes, months, stock, category, is_dealer, description FROM esims WHERE id=?", (pid,)).fetchone()
        if not plan: 
            return await event.answer("الباقة غير متوفرة", alert=True)

        esim_id, name, unit_price, mins, months, stock, cat, is_dealer, desc = plan

        api_row = cur.execute("SELECT id FROM dealer_api_keys WHERE user_id=?", (uid,)).fetchone()
        has_api = api_row is not None
        if has_api and is_dealer:
            unit_price *= 0.5

        subtotal = unit_price * qty
        discount_percent = 10 if qty > 1 else 0
        discount_amount = subtotal * (discount_percent / 100.0)
        final_price = subtotal - discount_amount

        SessionManager.set(uid, f'checkout_{uid}', {
            'esim_id': esim_id,
            'qty': qty,
            'unit_price': unit_price,
            'final_price': final_price,
            'name': name,
            'is_dealer': is_dealer
        })

        mins_text = f"\n⧺︰ <b>دقائق الاتصال:</b> <code>{mins} دقيقة اتصال رسمية</code>" if mins > 0 else "\n⧺︰ <b>النوع:</b> بيانات إنترنت فائقة السرعة بدون استخدام عادل"
        discount_badge = f"\n⧺︰ <b>خصم الكميات الإضافي (10%):</b> <code>-${discount_amount:.2f}</code> (وفرت {discount_percent}%)" if discount_percent > 0 else ""

        info_text = f"""<blockquote>⧺︰ <b>تفاصيل الباقة: {name}</b>
⧺︰ <b>المدة:</b> <code>{months} شهر</code>{mins_text}
⧺︰ <b>سعر الشريحة الواحدة:</b> <code>${unit_price:.2f}</code>
⧺︰ <b>المواصفات:</b> {desc}
⧺︰ <b>المخزون المتوفر:</b> <code>{stock} شريحة</code></blockquote>

<blockquote>⧺︰ <b>الكمية المحددة للشراء:</b> <code>{qty} شرائح</code>{discount_badge}
⧺︰ <b>المبلغ الإجمالي المطلوب:</b> <code>${final_price:.2f}</code>
⧺︰ <i>خصم 10% تلقائي مطبق على مشتريات أكثر من شريحة!</i></blockquote>"""

        btn = [
            [
                Button.inline("➖ تقليل", f'show_plan_{pid}_{qty-1}'.encode()),
                Button.inline(f"الكمية: [{qty}]", b'noop'),
                Button.inline("➕ زيادة", f'show_plan_{pid}_{qty+1}'.encode())
            ],
            [
                Button.inline("1 شريحة", f'show_plan_{pid}_1'.encode()),
                Button.inline("2 (خصم 10%)", f'show_plan_{pid}_2'.encode()),
                Button.inline("5 (خصم 10%)", f'show_plan_{pid}_5'.encode())
            ],
            [Button.inline(f"⚡ شراء فوري من المحفظة (${final_price:.2f})", f'pay_wallet_now_{pid}'.encode())],
            [Button.inline(t['pay_binance'], f'show_order_payments_{pid}'.encode())],
            [Button.inline(t['add_to_cart'], f'add_cart_now_{pid}_{qty}'.encode())]
        ]
        back_dest = f'open_cat_{cat}'.encode()
        btn.append([Button.inline(t['back'], back_dest)])

        try:
            await event.edit(info_text, buttons=btn, parse_mode='html')
        except errors.MessageNotModifiedError:
            pass

    elif data == 'noop':
        await event.answer("استخدم أزرار + و - لتعديل الكمية", alert=False)

    elif data.startswith('add_cart_now_'):
        await event.answer()
        parts = data.split('_')
        pid = int(parts[3])
        qty = int(parts[4])
        sess = SessionManager.get(uid, f'checkout_{uid}')
        price = sess['final_price'] if sess else 20.0
        cur.execute("INSERT INTO cart (user_id, esim_id, scope, price) VALUES (?, ?, ?, ?)", (uid, pid, f"Qty: {qty}", price))
        conn.commit()
        await event.answer("تمت الإضافة إلى سلة المشتريات بنجاح!", alert=True)

    elif data.startswith('pay_wallet_now_'):
        await event.answer()
        pid = int(data.split('_')[3])
        sess = SessionManager.get(uid, f'checkout_{uid}')
        if not sess or sess['esim_id'] != pid:
            return await event.answer("انتهت الجلسة", alert=True)

        final_price = sess['final_price']
        qty = sess['qty']
        name = sess['name']

        if uid not in wallet_locks:
            wallet_locks[uid] = asyncio.Lock()

        async with wallet_locks[uid]:
            bal = get_wallet_balance(uid)
            if bal < final_price:
                btn = [
                    [Button.inline("شحن المحفظة الآن", b'charge_wallet')],
                    [Button.inline(t['back'], b'main')]
                ]
                return await event.edit(f"<blockquote>⧺︰ <b>رصيدك غير كافي!</b>\nالرصيد المتاح: <code>${bal:.2f}</code> | المطلوب: <code>${final_price:.2f}</code></blockquote>", buttons=btn, parse_mode='html')

            order_id = f"AURA{secrets.token_hex(4).upper()}"
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
            update_wallet(uid, -final_price, 'purchase', f"شراء {qty}x {name}")
            cur.execute("INSERT INTO orders VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                        (order_id, uid, pid, qty, final_price/qty, final_price, None, 'paid', sess['is_dealer'], 1, now_str, now_str))
            cur.execute("UPDATE esims SET stock = stock - ? WHERE id=?", (qty, pid))
            conn.commit()
            await check_low_stock_and_alert(pid)

        SessionManager.remove(uid, f'checkout_{uid}')

        if qty > 1:
            lpa_list = f"أكواد الشرائح المشتراة (طلب #{order_id}) - عدد {qty} شرائح:\n" + "\n".join([f"شريحة {i+1}: {DEFAULT_LPA}" for i in range(qty)])
            bio = io.BytesIO(lpa_list.encode('utf-8'))
            bio.name = f"Aura_eSIMs_{order_id}.txt"
            bio.seek(0)
            success_text = f"""<blockquote>🎉 <b>تم الشراء بنجاح مع تطبيق خصم 10%!</b>
• <b>معرف الطلب:</b> <code>{order_id}</code>
• <b>الباقة:</b> {name}
• <b>العدد:</b> {qty} شرائح
• <b>المبلغ المخصوم:</b> <code>${final_price:.2f}</code>
تم إرفاق ملف أكواد التفعيل الموحدة أدناه:</blockquote>"""
            await event.reply(success_text, file=bio, parse_mode='html')
        else:
            success_single = f"""<blockquote>🎉 <b>تم الشراء بنجاح تام!</b>
• <b>معرف الطلب:</b> <code>{order_id}</code>
• <b>الباقة:</b> {name}
• <b>المبلغ المخصوم:</b> <code>${final_price:.2f}</code>

• <b>كود التفعيل الفوري (LPA):</b>
<code>{DEFAULT_LPA}</code>

• <b>امسح الباركود المرفق لتفعيل الشريحة مباشرة.</b></blockquote>"""
            await event.reply(success_single, file=DEFAULT_BARCODE, parse_mode='html')

        text, btn = main_menu(uid)
        await event.respond("القائمة الرئيسية:", buttons=btn)

    elif data == 'dealer_section':
        await event.answer()
        api_row = cur.execute("SELECT api_key FROM dealer_api_keys WHERE user_id=?", (uid,)).fetchone()
        cats = cur.execute("SELECT slug, name_ar, name_en FROM categories WHERE slug LIKE 'dealer_%' AND is_visible=1").fetchall()
        btn = []
        for slug, nar, nen in cats:
            lbl = nar if lang == 'ar' else nen
            btn.append([Button.inline(lbl, f'open_cat_{slug}'.encode())])
        
        if not api_row:
            btn.append([Button.inline(t['btn_dealer_api'], b'buy_api_sub_menu')])
        else:
            btn.append([Button.inline("عرض تفاصيل مفتاح الـ API", b'view_api_key_info')])
        btn.append([Button.inline(t['back'], b'main')])
        await event.edit(f"<blockquote>⧺︰ <b>{t['dealer_title']}</b></blockquote>", buttons=btn, parse_mode='html')

    elif data == 'buy_api_sub_menu':
        await event.answer()
        api_row = cur.execute("SELECT api_key FROM dealer_api_keys WHERE user_id=?", (uid,)).fetchone()
        if api_row:
            return await event.answer("لديك اشتراك API مفعل مسبقاً!", alert=True)
        btn = [
            [Button.inline("شراء تفعيل API الآن مقابل $100", b'confirm_buy_api_sub')],
            [Button.inline(t['back'], b'dealer_section')]
        ]
        desc_sub = "🔌 <b>اشتراك وتفعيل نظام الـ API للتجار:</b>\n\n• تكلفة التفعيل لمرة واحدة: <b>$100</b>\n• المميزات: خصم دائم <b>50%</b> على كافة خدمات ومخزون البوت + مفتاح API رسمي."
        await event.edit(desc_sub, buttons=btn, parse_mode='html')

    elif data == 'confirm_buy_api_sub':
        await event.answer()
        balance = get_wallet_balance(uid)
        if balance < 100.0:
            return await event.answer(t['insufficient_balance'], alert=True)
        update_wallet(uid, -100.0, 'api_subscription', 'شراء تفعيل نظام API للتجار')
        api_key = f"AURA_API_{secrets.token_hex(16).upper()}"
        cur.execute("INSERT OR REPLACE INTO dealer_api_keys (user_id, api_key, created_date) VALUES (?, ?, ?)", 
                    (uid, api_key, datetime.now().strftime("%Y-%m-%d %H:%M")))
        conn.commit()
        success_txt = f"🎉 <b>تم تفعيل اشتراك الـ API بنجاح:</b>\n\n<code>{api_key}</code>\n\nتم تطبيق خصم 50% على جميع طلبات الجملة."
        btn = [[Button.inline(t['back'], b'main')]]
        await event.edit(success_txt, buttons=btn, parse_mode='html')

    elif data == 'view_api_key_info':
        await event.answer()
        api_row = cur.execute("SELECT api_key FROM dealer_api_keys WHERE user_id=?", (uid,)).fetchone()
        if not api_row: return await event.answer("ليس لديك اشتراك API", alert=True)
        info_msg = f"🔌 <b>مفتاح الـ API الخاص بك:</b>\n<code>{api_row[0]}</code>\n\nتستفيد الآن من خصم 50% على باقات الجملة."
        btn = [[Button.inline(t['back'], b'dealer_section')]]
        await event.edit(info_msg, buttons=btn, parse_mode='html')

    elif data == 'wallet':
        await event.answer()
        balance = get_wallet_balance(uid)
        bot_me = await client.get_me()
        ref_link = f"https://t.me/{bot_me.username}?start=ref{uid}"
        text = f"{t['wallet_title']}\n\n<blockquote>⧺︰ <b>{t['current_balance']}:</b> <code>${balance:.2f}</code></blockquote>\n\n<blockquote>⧺︰ <b>رابط الإحالة الخاص بك:</b>\n<code>{ref_link}</code></blockquote>"
        btn = [
            [Button.inline(t['charge_wallet_btn'], b'charge_wallet')],
            [Button.inline(t['btn_transactions'], b'wallet_transactions')],
            [Button.inline(t['btn_verify_payment'], b'verify_payment_menu')],
            [Button.inline(t['back'], b'main')]
        ]
        await event.edit(text, buttons=btn, parse_mode='html')

    elif data == 'charge_wallet':
        await event.answer()
        SessionManager.set(uid, f'charge_amount_prompt_{uid}', True)
        await event.edit(t['charge_prompt'], buttons=[[Button.inline(t['back'], b'wallet')]], parse_mode='html')

    elif data == 'wallet_transactions':
        await event.answer()
        txs = cur.execute("SELECT type, amount, balance_after, description, date FROM wallet_transactions WHERE user_id=? ORDER BY id DESC LIMIT 10", (uid,)).fetchall()
        if not txs:
            return await event.edit("<blockquote>📜 لا توجد حركات مالية مسجلة في محفظتك حتى الآن.</blockquote>", buttons=[[Button.inline(t['back'], b'wallet')]], parse_mode='html')
        tx_text = "<blockquote>📜 سجل آخر المعاملات المالية في محفظتك:</blockquote>\n\n"
        for t_type, amt, b_after, desc, date in txs:
            sign = "+" if amt > 0 else ""
            tx_text += f"• <b>{desc}</b>\n  ↳ المبلغ: <code>{sign}${amt:.2f}</code> | الرصيد بعد: <code>${b_after:.2f}</code>\n  ↳ التاريخ: {date}\n───────────────────\n"
        btn = [[Button.inline(t['back'], b'wallet')]]
        await event.edit(tx_text, buttons=btn, parse_mode='html')

    elif data == 'view_cart':
        await event.answer()
        items = cur.execute("SELECT c.id, e.name, c.scope, c.price FROM cart c JOIN esims e ON c.esim_id=e.id WHERE c.user_id=?", (uid,)).fetchall()
        if not items:
            return await event.edit("<blockquote>سلة المشتريات فارغة تماماً.</blockquote>", buttons=[[Button.inline(t['back'], b'main')]], parse_mode='html')
        total_cart = sum(i[3] for i in items)
        cart_text = "<blockquote>محتويات سلة المشتريات:</blockquote>\n\n"
        btn = []
        for cid, name, sc, pr in items:
            cart_text += f"• <b>{name}</b> ({sc}) - <code>${pr:.2f}</code>\n"
            btn.append([Button.inline(f"حذف: {name}", f"cart_del_{cid}".encode())])
        cart_text += f"\n> ⧺︰ <b>الإجمالي:</b> <code>${total_cart:.2f}</code>"
        btn.append([Button.inline(f"دفع السلة من المحفظة (${total_cart:.2f})", b'cart_checkout')])
        btn.append([Button.inline(t['back'], b'main')])
        await event.edit(cart_text, buttons=btn, parse_mode='html')

    elif data.startswith('cart_del_'):
        await event.answer()
        cid = int(data.split('_')[2])
        cur.execute("DELETE FROM cart WHERE id=? AND user_id=?", (cid, uid))
        conn.commit()
        await callback(event)

    elif data == 'cart_checkout':
        await event.answer()
        items = cur.execute("SELECT c.esim_id, c.price, e.name FROM cart c JOIN esims e ON c.esim_id=e.id WHERE c.user_id=?", (uid,)).fetchall()
        if not items: return await event.answer("السلة فارغة", alert=True)
        total_price = sum(item[1] for item in items)
        if uid not in wallet_locks:
            wallet_locks[uid] = asyncio.Lock()
        async with wallet_locks[uid]:
            bal = get_wallet_balance(uid)
            if bal < total_price:
                return await event.answer(t['insufficient_balance'], alert=True)
            order_id = f"AURA{secrets.token_hex(4).upper()}"
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
            update_wallet(uid, -total_price, 'purchase', f"شراء سلة مشتريات {order_id}")
            for eid, pr, nm in items:
                cur.execute("INSERT INTO orders VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                            (f"{order_id}_{eid}", uid, eid, 1, pr, pr, None, 'paid', 0, 1, now_str, now_str))
                cur.execute("UPDATE esims SET stock=stock-1 WHERE id=?", (eid,))
            cur.execute("DELETE FROM cart WHERE user_id=?", (uid,))
            conn.commit()
        await event.reply(f"<blockquote>🎉 <b>تم دفع السلة بنجاح!</b>\nكود التفعيل (LPA):\n<code>{DEFAULT_LPA}</code></blockquote>", file=DEFAULT_BARCODE, parse_mode='html')
        text, btn = main_menu(uid)
        await event.respond("الرئيسية:", buttons=btn)

    elif data == 'my_orders':
        await event.answer()
        orders = cur.execute("SELECT o.order_id, e.name, o.quantity, o.total_usd, o.created_date FROM orders o JOIN esims e ON o.esim_id=e.id WHERE o.user_id=? AND o.status='paid' ORDER BY o.created_date DESC LIMIT 10", (uid,)).fetchall()
        if not orders: return await event.edit(t['no_orders'], buttons=[[Button.inline(t['back'], b'main')]], parse_mode='html')
        text = f"{t['my_orders_title']}\n\n"
        btn = []
        for order_id, name, qty, total, date in orders:
            text += f"• <b>{qty}x {name}</b> ({date}) | ${total:.2f}\n"
            btn.append([Button.inline(f"تفاصيل الطلب: {order_id}", f"reload_{order_id}".encode())])
        btn.append([Button.inline(t['back'], b'main')])
        await event.edit(text, buttons=btn, parse_mode='html')

    elif data.startswith('reload_'):
        await event.answer()
        oid = data.replace('reload_', '')
        await event.reply(f"<blockquote>تفاصيل الطلب [{oid}]:\nكود LPA الموحد:\n<code>{DEFAULT_LPA}</code></blockquote>", file=DEFAULT_BARCODE, parse_mode='html')

    elif data == 'countries_list':
        await event.answer()
        c_text = "".join([f"⧺︰ {c['flag']} <b>{c['name']}</b> - {c['operators']}\n" for c in COUNTRIES_DATA])
        btn = [[Button.inline(t['back'], b'main')]]
        await event.edit(t['countries_header'].replace("COUNTRIES_COUNT", str(len(COUNTRIES_DATA))) + c_text, buttons=btn, parse_mode='html')

    elif data == 'verify_payment_menu':
        await event.answer()
        SessionManager.set(uid, f'verify_payment_{uid}', True)
        await event.edit(t['verify_prompt'], buttons=[[Button.inline(t['back'], b'wallet')]], parse_mode='html')

    elif data == 'support_ticket':
        await event.answer()
        SessionManager.set(uid, f'support_ticket_{uid}', True)
        await event.edit(t['support_prompt'], buttons=[[Button.inline(t['back'], b'main')]], parse_mode='html')

    elif data.startswith('show_order_payments_'):
        await event.answer()
        pid = int(data.split('_')[3])
        sess = SessionManager.get(uid, f'checkout_{uid}')
        price = sess['final_price'] if sess else 20.0
        networks = cur.execute("SELECT network_name, address, binance_id FROM binance_networks").fetchall()
        details_text = f"<blockquote>⧺︰ <b>بوابة الدفع الشاملة</b>\nالمبلغ المطلوب: <code>${price:.2f}</code></blockquote>\n\n"
        for idx, (n_name, n_addr, n_id) in enumerate(networks, 1):
            details_text += f"<b>{idx}. {n_name}</b>\n"
            if n_id: details_text += f"• <code>ID:</code> <code>{n_id}</code>\n"
            if n_addr: details_text += f"• <code>Address:</code> <code>{n_addr}</code>\n"
            details_text += "───────────────────\n"
        btn = [
            [Button.inline(t['btn_verify_now'], b'verify_payment_menu')],
            [Button.inline(t['back'], f'show_plan_{pid}_{sess["qty"] if sess else 1}'.encode())]
        ]
        await event.edit(details_text, buttons=btn, parse_mode='html')

    # ========================================================
    # 7. لوحة تحكم الأدمن الشاملة والمطورة
    # ========================================================
    elif data == 'admin_panel' and is_admin(uid):
        await event.answer()
        total_sales = cur.execute("SELECT COUNT(*) FROM orders WHERE status='paid'").fetchone()[0]
        total_balance = cur.execute("SELECT SUM(balance) FROM wallets").fetchone()[0] or 0
        total_esims = cur.execute("SELECT SUM(stock) FROM esims").fetchone()[0] or 0
        total_users = cur.execute("SELECT COUNT(*) FROM users_settings").fetchone()[0] or 0
        btn = [
            [Button.inline("📂 إدارة الأقسام (إضافة/حذف/إخفاء)", b'adm_cats_mgr')],
            [Button.inline("📦 إدارة وتصفير الشرائح الفردية", b'adm_plans_mgr')],
            [Button.inline("➕ إضافة شريحة جديدة لقسم", b'adm_plan_add_start')],
            [Button.inline("💳 إدارة طرق وشبكات الدفع", b'adm_pay_mgr')],
            [Button.inline("💰 شحن رصيد لعميل", b'admin_add_balance'), Button.inline("📉 خصم رصيد", b'admin_sub_balance')],
            [Button.inline("تصفير رصيد عميل", b'admin_zero_balance'), Button.inline("إضافة مخزون عام", b'admin_add_stock')],
            [Button.inline("حظر / فك حظر", b'admin_manage_bans'), Button.inline("إذاعة عامة", b'admin_broadcast_msg')],
            [Button.inline(t['back'], b'main')]
        ]
        await event.edit(
            f"{t['admin_panel_title']}\n\n"
            f"<blockquote>⧺︰ <b>إجمالي المستخدمين:</b> <code>{total_users}</code></blockquote>\n"
            f"<blockquote>⧺︰ <b>{t['stats_sales']}:</b> <code>{total_sales}</code></blockquote>\n"
            f"<blockquote>⧺︰ <b>{t['stats_wallets']}:</b> <code>${total_balance:.2f}</code></blockquote>\n"
            f"<blockquote>⧺︰ <b>{t['stats_esims']}:</b> <code>{total_esims}</code></blockquote>",
            buttons=btn, parse_mode='html'
        )

    # ------------------ إدارة الأقسام ------------------
    elif data == 'adm_cats_mgr' and is_admin(uid):
        await event.answer()
        cats = cur.execute("SELECT slug, name_ar, is_visible FROM categories").fetchall()
        txt = "<blockquote>📂 <b>إدارة الأقسام (إخفاء / إظهار / حذف / إضافة):</b></blockquote>\n\n"
        btn = []
        for slug, nar, vis in cats:
            status_icon = "👁️ ظاهر" if vis == 1 else "🙈 مخفي"
            btn.append([Button.inline(f"{nar} ({status_icon})", f"adm_cat_det_{slug}".encode())])
        
        btn.append([Button.inline("➕ إضافة قسم جديد", b'adm_cat_add')])
        btn.append([Button.inline(t['back'], b'admin_panel')])
        await event.edit(txt, buttons=btn, parse_mode='html')

    elif data.startswith('adm_cat_det_') and is_admin(uid):
        await event.answer()
        slug = data.replace('adm_cat_det_', '')
        cat = cur.execute("SELECT name_ar, is_visible FROM categories WHERE slug=?", (slug,)).fetchone()
        if not cat: return
        nar, vis = cat
        toggle_label = "إخفاء القسم عن المستخدمين" if vis == 1 else "إظهار القسم للمستخدمين"
        btn = [
            [Button.inline(toggle_label, f"adm_cat_toggle_{slug}".encode())],
            [Button.inline("🗑️ حذف القسم مع شرائحه", f"adm_cat_delete_{slug}".encode())],
            [Button.inline(t['back'], b'adm_cats_mgr')]
        ]
        await event.edit(f"<blockquote>📂 <b>إدارة القسم: {nar}</b>\nالحالة الحالية: <b>{'ظاهر' if vis==1 else 'مخفي'}</b></blockquote>", buttons=btn, parse_mode='html')

    elif data.startswith('adm_cat_toggle_') and is_admin(uid):
        await event.answer()
        slug = data.replace('adm_cat_toggle_', '')
        cur.execute("UPDATE categories SET is_visible = CASE WHEN is_visible=1 THEN 0 ELSE 1 END WHERE slug=?", (slug,))
        conn.commit()
        await event.answer("تم تبديل حالة القسم بنجاح!", alert=True)
        event.data = f"adm_cat_det_{slug}".encode()
        await callback(event)

    elif data.startswith('adm_cat_delete_') and is_admin(uid):
        await event.answer()
        slug = data.replace('adm_cat_delete_', '')
        cur.execute("DELETE FROM categories WHERE slug=?", (slug,))
        cur.execute("DELETE FROM esims WHERE category=?", (slug,))
        conn.commit()
        await event.answer("تم حذف القسم وكافة شرائحه بنجاح!", alert=True)
        event.data = b'adm_cats_mgr'
        await callback(event)

    elif data == 'adm_cat_add' and is_admin(uid):
        await event.answer()
        SessionManager.set(uid, f'adm_new_cat_{uid}', True)
        await event.edit("أرسل بيانات القسم الجديد بالصيغة:\n<code>المعرف(slug) | اسم القسم بالعربي | Name in English</code>\n\nمثال:\n<code>zain | باقات زين الدولية | Zain Plans</code>", buttons=[[Button.inline(t['back'], b'adm_cats_mgr')]], parse_mode='html')

    # ------------------ إضافة شريحة جديدة ------------------
    elif data == 'adm_plan_add_start' and is_admin(uid):
        await event.answer()
        cats = cur.execute("SELECT slug, name_ar FROM categories").fetchall()
        cats_list_str = "\n".join([f"• <code>{s}</code> ({n})" for s, n in cats])
        SessionManager.set(uid, f'adm_add_plan_input_{uid}', True)
        msg_input = f"""<blockquote>➕ <b>إضافة شريحة جديدة لقسم معين:</b>
الأقسام المتاحة حالياً:
{cats_list_str}

أرسل البيانات بسطر واحد بالصيغة التالية:
<code>المعرف(slug) | اسم الشريحة | السعر | الدقائق | الشهور | المخزون | جملة(1 أو 0) | الوصف</code>

مثال:
<code>vodafone | باقة الصيف 50GB | 25 | 1000 | 1 | 500 | 0 | باقة مميزة للمسافرين</code></blockquote>"""
        await event.edit(msg_input, buttons=[[Button.inline(t['back'], b'admin_panel')]], parse_mode='html')

    # ------------------ إدارة وتصفير الشرائح الفردية ------------------
    elif data == 'adm_plans_mgr' and is_admin(uid):
        await event.answer()
        plans = cur.execute("SELECT id, name, price_usd, stock FROM esims LIMIT 25").fetchall()
        txt = "<blockquote>📦 <b>إدارة الشرائح والمخزون الفردي:</b>\nاختر شريحة لتصفيرها أو تعديل سعرها ومخزونها:</blockquote>\n\n"
        btn = []
        for pid, name, pr, st in plans:
            btn.append([Button.inline(f"{name} | ${pr:.0f} | متبقي: {st}", f"adm_plan_det_{pid}".encode())])
        
        btn.append([Button.inline(t['back'], b'admin_panel')])
        await event.edit(txt, buttons=btn, parse_mode='html')

    elif data.startswith('adm_plan_det_') and is_admin(uid):
        await event.answer()
        pid = int(data.split('_')[3])
        plan = cur.execute("SELECT id, name, price_usd, stock, minutes, months FROM esims WHERE id=?", (pid,)).fetchone()
        if not plan: return
        esim_id, name, pr, st, mins, mo = plan
        SessionManager.set(uid, f'target_plan_id_{uid}', pid)
        
        info = f"""<blockquote>📦 <b>إدارة الشريحة: {name}</b>
• <b>المدة:</b> <code>{mo} شهر</code>
• <b>الدقائق:</b> <code>{mins} دقيقة</code>
• <b>السعر:</b> <code>${pr:.2f}</code>
• <b>المخزون الحالي:</b> <code>{st} قطعة</code></blockquote>"""

        btn = [
            [Button.inline("🚫 تصفير مخزون الشريحة (نفاد المخزون)", f"adm_plan_zero_{pid}".encode())],
            [Button.inline("✏️ تعديل السعر", b'adm_edit_plan_price'), Button.inline("📦 تعبئة المخزون", b'adm_edit_plan_stock')],
            [Button.inline("🗑️ حذف هذه الشريحة نهائياً", f"adm_plan_delete_{pid}".encode())],
            [Button.inline(t['back'], b'adm_plans_mgr')]
        ]
        await event.edit(info, buttons=btn, parse_mode='html')

    elif data.startswith('adm_plan_zero_') and is_admin(uid):
        await event.answer()
        pid = int(data.split('_')[3])
        cur.execute("UPDATE esims SET stock = 0 WHERE id=?", (pid,))
        conn.commit()
        await event.answer("تم تصفير مخزون الشريحة وأصبحت غير متاحة للشراء!", alert=True)
        event.data = f"adm_plan_det_{pid}".encode()
        await callback(event)

    elif data.startswith('adm_plan_delete_') and is_admin(uid):
        await event.answer()
        pid = int(data.split('_')[3])
        cur.execute("DELETE FROM esims WHERE id=?", (pid,))
        conn.commit()
        await event.answer("تم حذف الشريحة نهائياً!", alert=True)
        event.data = b'adm_plans_mgr'
        await callback(event)

    elif data == 'adm_edit_plan_price' and is_admin(uid):
        await event.answer()
        SessionManager.set(uid, f'action_plan_price_{uid}', True)
        await event.edit("أرسل السعر الجديد بالدولار لهذه الشريحة (مثال: <code>25.5</code>):", buttons=[[Button.inline(t['back'], b'adm_plans_mgr')]], parse_mode='html')

    elif data == 'adm_edit_plan_stock' and is_admin(uid):
        await event.answer()
        SessionManager.set(uid, f'action_plan_stock_{uid}', True)
        await event.edit("أرسل كمية المخزون الجديدة للشريحة (مثال: <code>100</code>):", buttons=[[Button.inline(t['back'], b'adm_plans_mgr')]], parse_mode='html')

    # ------------------ إدارة طرق وشبكات الدفع ------------------
    elif data == 'adm_pay_mgr' and is_admin(uid):
        await event.answer()
        nets = cur.execute("SELECT network_key, network_name, address, binance_id FROM binance_networks").fetchall()
        txt = "<blockquote>💳 <b>إدارة طرق وعناوين وشبكات الدفع:</b>\nاختر وسيلة لتعديلها أو حذفها، أو أضف وسيلة جديدة:</blockquote>\n\n"
        btn = []
        for k, name, addr, bid in nets:
            val = bid if bid else (addr[:12] + "...")
            btn.append([Button.inline(f"{name} ({val})", f"adm_pay_det_{k}".encode())])
        
        btn.append([Button.inline("➕ إضافة شبكة/وسيلة دفع جديدة", b'adm_pay_add')])
        btn.append([Button.inline(t['back'], b'admin_panel')])
        await event.edit(txt, buttons=btn, parse_mode='html')

    elif data.startswith('adm_pay_det_') and is_admin(uid):
        await event.answer()
        key = data.replace('adm_pay_det_', '')
        net = cur.execute("SELECT network_key, network_name, address, binance_id FROM binance_networks WHERE network_key=?", (key,)).fetchone()
        if not net: return
        k, name, addr, bid = net
        SessionManager.set(uid, f'target_pay_key_{uid}', k)
        info = f"""<blockquote>💳 <b>تعديل طريقة الدفع:</b>
• الاسم: <b>{name}</b>
• العنوان: <code>{addr if addr else 'غير محدد'}</code>
• ID / Pay ID: <code>{bid if bid else 'غير محدد'}</code></blockquote>"""
        btn = [
            [Button.inline("تعديل العنوان", b'adm_pay_set_addr'), Button.inline("تعديل الـ ID", b'adm_pay_set_id')],
            [Button.inline("🗑️ حذف وسيلة الدفع", f"adm_pay_delete_{k}".encode())],
            [Button.inline(t['back'], b'adm_pay_mgr')]
        ]
        await event.edit(info, buttons=btn, parse_mode='html')

    elif data.startswith('adm_pay_delete_') and is_admin(uid):
        await event.answer()
        key = data.replace('adm_pay_delete_', '')
        cur.execute("DELETE FROM binance_networks WHERE network_key=?", (key,))
        conn.commit()
        await event.answer("تم حذف وسيلة الدفع بنجاح!", alert=True)
        event.data = b'adm_pay_mgr'
        await callback(event)

    elif data == 'adm_pay_set_addr' and is_admin(uid):
        await event.answer()
        SessionManager.set(uid, f'adm_pay_set_addr_{uid}', True)
        await event.edit("أرسل العنوان الجديد (Wallet Address):", buttons=[[Button.inline(t['back'], b'adm_pay_mgr')]], parse_mode='html')

    elif data == 'adm_pay_set_id' and is_admin(uid):
        await event.answer()
        SessionManager.set(uid, f'adm_pay_set_id_{uid}', True)
        await event.edit("أرسل الـ ID الجديد (Binance/Pay ID):", buttons=[[Button.inline(t['back'], b'adm_pay_mgr')]], parse_mode='html')

    elif data == 'adm_pay_add' and is_admin(uid):
        await event.answer()
        SessionManager.set(uid, f'adm_new_pay_{uid}', True)
        await event.edit("أرسل وسيلة الدفع الجديدة بالصيغة:\n<code>اسم الشبكة | العنوان أو المحفظة | ID المنصة (اختياري)</code>\n\nمثال:\n<code>USDT (Polygon) | 0x334c55fe51757ac... | </code>", buttons=[[Button.inline(t['back'], b'adm_pay_mgr')]], parse_mode='html')

    # ------------------ الرصيد والمخزون والإذاعة ------------------
    elif data == 'admin_add_balance' and is_admin(uid):
        await event.answer()
        SessionManager.set(uid, f'add_balance_{uid}', True)
        await event.edit("أرسل آيدي العميل ثم المبلغ (مثال: <code>123456789 50</code>):", buttons=[[Button.inline(t['back'], b'admin_panel')]], parse_mode='html')

    elif data == 'admin_sub_balance' and is_admin(uid):
        await event.answer()
        SessionManager.set(uid, f'sub_balance_{uid}', True)
        await event.edit("أرسل آيدي العميل ثم المبلغ (مثال: <code>123456789 20</code>):", buttons=[[Button.inline(t['back'], b'admin_panel')]], parse_mode='html')

    elif data == 'admin_zero_balance' and is_admin(uid):
        await event.answer()
        SessionManager.set(uid, f'zero_balance_{uid}', True)
        await event.edit("أرسل آيدي العميل لتصفير محفظته:", buttons=[[Button.inline(t['back'], b'admin_panel')]], parse_mode='html')

    elif data == 'admin_add_stock' and is_admin(uid):
        await event.answer()
        SessionManager.set(uid, f'add_stock_{uid}', True)
        await event.edit("أرسل الكمية المراد إضافتها لجميع الشرائح:", buttons=[[Button.inline(t['back'], b'admin_panel')]], parse_mode='html')

    elif data == 'admin_manage_bans' and is_admin(uid):
        await event.answer()
        SessionManager.set(uid, f'manage_bans_{uid}', True)
        await event.edit("أرسل آيدي المستخدم لحظر / فك حظره:", buttons=[[Button.inline(t['back'], b'admin_panel')]], parse_mode='html')

    elif data == 'admin_broadcast_msg' and is_admin(uid):
        await event.answer()
        SessionManager.set(uid, f'broadcast_{uid}', True)
        await event.edit("أرسل الرسالة المراد إذاعتها لجميع المستخدمين:", buttons=[[Button.inline(t['back'], b'admin_panel')]], parse_mode='html')

    elif data.startswith('admin_approve_dep_') and is_admin(uid):
        await event.answer()
        parts = data.split('_')
        target_uid = int(parts[3])
        dep_amount = float(parts[4])
        update_wallet(target_uid, dep_amount, 'admin_deposit', f"شحن إيصال مقبول بقيمة ${dep_amount}")
        try:
            await client.send_message(target_uid, f"<blockquote>✅ <b>تم قبول إيصال الدفع وإضافة ${dep_amount:.2f} إلى محفظتك!</b></blockquote>", parse_mode='html')
        except: pass
        await event.edit(f"تم قبول الطلب وشحن ${dep_amount:.2f} للمستخدم {target_uid}.", buttons=[[Button.inline("لوحة التحكم", b'admin_panel')]], parse_mode='html')

    elif data.startswith('admin_reject_dep_') and is_admin(uid):
        await event.answer()
        parts = data.split('_')
        target_uid = int(parts[3])
        try:
            await client.send_message(target_uid, "<blockquote>❌ <b>عذراً، تم رفض إيصال الدفع. يرجى التواصل مع الدعم.</b></blockquote>", parse_mode='html')
        except: pass
        await event.edit("تم رفض الإيصال وإبلاغ المستخدم.", buttons=[[Button.inline("لوحة التحكم", b'admin_panel')]], parse_mode='html')

# ==========================================
# 8. معالجة الرسائل والمدخلات
# ==========================================
@client.on(events.NewMessage)
async def handler(event):
    uid = event.sender_id
    if is_banned(uid) or (event.text and event.text.startswith('/')): return

    now = time.time()
    if uid in user_rate_limits and now - user_rate_limits[uid] < 0.3:
        return
    user_rate_limits[uid] = now

    text = event.text.strip() if event.text else ""
    lang = get_user_lang(uid) or 'ar'
    t = LANGS.get(lang, LANGS['ar'])

    # شحن المحفظة
    if SessionManager.has(uid, f'charge_amount_prompt_{uid}'):
        SessionManager.remove(uid, f'charge_amount_prompt_{uid}')
        try:
            amount = float(text)
            if amount < 20:
                await event.reply(t['min_charge_err'], parse_mode='html')
                SessionManager.set(uid, f'charge_amount_prompt_{uid}', True)
                return
            SessionManager.set(uid, f'charging_amount_{uid}', amount)
            networks = cur.execute("SELECT network_name, address, binance_id FROM binance_networks").fetchall()
            details_text = t['show_all_payments_title'].replace("$amount", str(amount)) + "\n\n"
            for idx, (n_name, n_addr, n_id) in enumerate(networks, 1):
                details_text += f"<b>{idx}. {n_name}</b>\n"
                if n_id: details_text += f"• <code>ID:</code> <code>{n_id}</code>\n"
                if n_addr: details_text += f"• <code>Address:</code> <code>{n_addr}</code>\n"
                details_text += "───────────────────\n"
            details_text += t['show_all_payments_footer']
            btn = [
                [Button.inline(t['btn_verify_now'], b'verify_payment_menu')],
                [Button.inline(t['back'], b'wallet')]
            ]
            await event.reply(details_text, buttons=btn, parse_mode='html')
        except:
            await event.reply(t['invalid_number_err'], parse_mode='html')
            SessionManager.set(uid, f'charge_amount_prompt_{uid}', True)
        return

    elif SessionManager.has(uid, f'verify_payment_{uid}'):
        SessionManager.remove(uid, f'verify_payment_{uid}')
        await event.reply(t['verify_sent'], buttons=[[Button.inline(t['back'], b'wallet')]], parse_mode='html')
        u = await event.sender
        uname = f"@{u.username}" if u and u.username else "بدون معرف"
        fname = u.first_name if u else "مستخدم"
        dep_amt = SessionManager.pop(uid, f'charging_amount_{uid}') or 20.0
        admin_msg = f"""<blockquote>🚨 <b>طلب تحقق من إيصال دفع!</b>
• <b>العميل:</b> {fname} ({uname})
• <b>الآيدي:</b> <code>{uid}</code>
• <b>المبلغ المطلوب:</b> <code>${dep_amt:.2f}</code>
• <b>البيان:</b> {text if text else 'صورة مرفقة'}</blockquote>"""
        admin_btns = [
            [Button.inline("قبول وشحن الرصيد", f"admin_approve_dep_{uid}_{dep_amt}".encode()),
             Button.inline("رفض الإيصال", f"admin_reject_dep_{uid}".encode())]
        ]
        if event.media:
            await client.send_file(DEV_ID, event.media, caption=admin_msg, buttons=admin_btns, parse_mode='html')
        else:
            await client.send_message(DEV_ID, admin_msg, buttons=admin_btns, parse_mode='html')
        return

    elif SessionManager.has(uid, f'support_ticket_{uid}'):
        SessionManager.remove(uid, f'support_ticket_{uid}')
        await event.reply(t['support_sent'], buttons=[[Button.inline(t['back'], b'main')]], parse_mode='html')
        await client.send_message(DEV_ID, f"<blockquote>💬 <b>تذكرة دعم من المستخدم:</b> <code>{uid}</code>\n\n{text}</blockquote>", parse_mode='html')
        return

    # أوامر الأدمن: إضافة شريحة جديدة
    elif SessionManager.has(uid, f'adm_add_plan_input_{uid}') and is_admin(uid):
        SessionManager.remove(uid, f'adm_add_plan_input_{uid}')
        try:
            parts = [x.strip() for x in text.split('|')]
            cat, name, price, mins, months, stock, is_dlr, desc = parts
            code_key = f"{cat}_{secrets.token_hex(3)}"
            cur.execute('''INSERT INTO esims 
                (category, name, code_key, price_usd, minutes, months, stock, min_qty, is_dealer, description)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (cat, name, code_key, float(price), int(mins), int(months), int(stock), 1, int(is_dlr), desc))
            conn.commit()
            await event.reply(f"✅ تمت إضافة الشريحة <b>{name}</b> بنجاح إلى القسم <code>{cat}</code>!", buttons=[[Button.inline("إدارة الشرائح", b'adm_plans_mgr')]], parse_mode='html')
        except Exception as e:
            await event.reply(f"❌ خطأ أثناء الإضافة، تأكد من الصيغة: {e}")

    # أوامر الأدمن: إضافة قسم جديد
    elif SessionManager.has(uid, f'adm_new_cat_{uid}') and is_admin(uid):
        SessionManager.remove(uid, f'adm_new_cat_{uid}')
        try:
            slug, nar, nen = [x.strip() for x in text.split('|')]
            cur.execute("INSERT OR REPLACE INTO categories (slug, name_ar, name_en, is_visible) VALUES (?, ?, ?, 1)", (slug, nar, nen))
            conn.commit()
            await event.reply(f"✅ تمت إضافة القسم <b>{nar}</b> بنجاح!", buttons=[[Button.inline("إدارة الأقسام", b'adm_cats_mgr')]], parse_mode='html')
        except Exception as e:
            await event.reply(f"❌ خطأ بالصيغة: {e}")

    # أوامر الأدمن: تعديل سعر شريحة
    elif SessionManager.has(uid, f'action_plan_price_{uid}') and is_admin(uid):
        SessionManager.remove(uid, f'action_plan_price_{uid}')
        pid = SessionManager.get(uid, f'target_plan_id_{uid}')
        try:
            pr = float(text)
            cur.execute("UPDATE esims SET price_usd=? WHERE id=?", (pr, pid))
            conn.commit()
            await event.reply(f"✅ تم تحديث السعر إلى <b>${pr:.2f}</b> بنجاح!", buttons=[[Button.inline("لوحة الشرائح", b'adm_plans_mgr')]], parse_mode='html')
        except:
            await event.reply("يرجى إرسال رقم صحيح.")

    # أوامر الأدمن: تعديل مخزون شريحة
    elif SessionManager.has(uid, f'action_plan_stock_{uid}') and is_admin(uid):
        SessionManager.remove(uid, f'action_plan_stock_{uid}')
        pid = SessionManager.get(uid, f'target_plan_id_{uid}')
        try:
            st = int(text)
            cur.execute("UPDATE esims SET stock=? WHERE id=?", (st, pid))
            conn.commit()
            await event.reply(f"✅ تم تحديث المخزون إلى <b>{st}</b> قطعة بنجاح!", buttons=[[Button.inline("لوحة الشرائح", b'adm_plans_mgr')]], parse_mode='html')
        except:
            await event.reply("يرجى إرسال رقم صحيح.")

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
            await event.reply(f"✅ تمت إضافة وسيلة الدفع <b>{name}</b> بنجاح!", buttons=[[Button.inline("إدارة طرق الدفع", b'adm_pay_mgr')]], parse_mode='html')
        except Exception as e:
            await event.reply(f"❌ خطأ: {e}")

    elif SessionManager.has(uid, f'adm_pay_set_addr_{uid}') and is_admin(uid):
        SessionManager.remove(uid, f'adm_pay_set_addr_{uid}')
        k = SessionManager.get(uid, f'target_pay_key_{uid}')
        cur.execute("UPDATE binance_networks SET address=? WHERE network_key=?", (text, k))
        conn.commit()
        await event.reply("✅ تم تحديث العنوان بنجاح!", buttons=[[Button.inline("إدارة طرق الدفع", b'adm_pay_mgr')]], parse_mode='html')

    elif SessionManager.has(uid, f'adm_pay_set_id_{uid}') and is_admin(uid):
        SessionManager.remove(uid, f'adm_pay_set_id_{uid}')
        k = SessionManager.get(uid, f'target_pay_key_{uid}')
        cur.execute("UPDATE binance_networks SET binance_id=? WHERE network_key=?", (text, k))
        conn.commit()
        await event.reply("✅ تم تحديث الـ ID بنجاح!", buttons=[[Button.inline("إدارة طرق الدفع", b'adm_pay_mgr')]], parse_mode='html')

    # الرصيد والمخزون والإذاعة
    elif SessionManager.has(uid, f'add_balance_{uid}') and is_admin(uid):
        SessionManager.remove(uid, f'add_balance_{uid}')
        try:
            target_uid, amt = text.split()
            update_wallet(int(target_uid), float(amt), 'admin_deposit', "إضافة رصيد بواسطة الأدمن")
            await event.reply(f"تمت إضافة ${float(amt):.2f} إلى محفظة {target_uid}.", buttons=[[Button.inline("لوحة التحكم", b'admin_panel')]])
            try: await client.send_message(int(target_uid), f"تمت إضافة مبلغ ${float(amt):.2f} إلى محفظتك!")
            except: pass
        except: await event.reply("صيغة خاطئة (مثال: 123456789 50)")

    elif SessionManager.has(uid, f'sub_balance_{uid}') and is_admin(uid):
        SessionManager.remove(uid, f'sub_balance_{uid}')
        try:
            target_uid, amt = text.split()
            update_wallet(int(target_uid), -float(amt), 'admin_withdraw', "خصم رصيد بواسطة الأدمن")
            await event.reply(f"تم خصم ${float(amt):.2f} من محفظة {target_uid}.", buttons=[[Button.inline("لوحة التحكم", b'admin_panel')]])
        except: await event.reply("صيغة خاطئة (مثال: 123456789 20)")

    elif SessionManager.has(uid, f'zero_balance_{uid}') and is_admin(uid):
        SessionManager.remove(uid, f'zero_balance_{uid}')
        try:
            target_uid = int(text)
            bal = get_wallet_balance(target_uid)
            if bal > 0: update_wallet(target_uid, -bal, 'admin_zero', "تصفير الرصيد")
            await event.reply(f"تم تصفير رصيد المستخدم {target_uid}.", buttons=[[Button.inline("لوحة التحكم", b'admin_panel')]])
        except: await event.reply("أرسل آيدي صحيح")

    elif SessionManager.has(uid, f'add_stock_{uid}') and is_admin(uid):
        SessionManager.remove(uid, f'add_stock_{uid}')
        try:
            cur.execute("UPDATE esims SET stock = stock + ?", (int(text),))
            conn.commit()
            await event.reply(f"تمت إضافة {text} إلى المخزون بنجاح.", buttons=[[Button.inline("لوحة التحكم", b'admin_panel')]])
        except: await event.reply("أرسل رقماً صحيحاً")

    elif SessionManager.has(uid, f'manage_bans_{uid}') and is_admin(uid):
        SessionManager.remove(uid, f'manage_bans_{uid}')
        try:
            tid = int(text)
            if is_banned(tid):
                cur.execute("DELETE FROM bans WHERE user_id=?", (tid,))
                ban_cache.pop(tid, None)
                msg = f"تم فك حظر المستخدم {tid}."
            else:
                cur.execute("INSERT OR REPLACE INTO bans (user_id) VALUES (?)", (tid,))
                ban_cache[tid] = True
                msg = f"تم حظر المستخدم {tid}."
            conn.commit()
            await event.reply(msg, buttons=[[Button.inline("لوحة التحكم", b'admin_panel')]])
        except: await event.reply("أرسل آيدي صحيح")

    elif SessionManager.has(uid, f'broadcast_{uid}') and is_admin(uid):
        SessionManager.remove(uid, f'broadcast_{uid}')
        users = cur.execute("SELECT user_id FROM users_settings").fetchall()
        succ, fail = 0, 0
        status_msg = await event.reply("جاري الإذاعة...")
        for (u_id,) in users:
            try:
                await client.send_message(u_id, f"<blockquote>📢 <b>إعلان رسمي من Aura eSIM:</b>\n\n{text}</blockquote>", parse_mode='html')
                succ += 1
                await asyncio.sleep(0.04)
            except errors.FloodWaitError as e:
                await asyncio.sleep(e.seconds)
                try:
                    await client.send_message(u_id, f"<blockquote>📢 <b>إعلان رسمي من Aura eSIM:</b>\n\n{text}</blockquote>", parse_mode='html')
                    succ += 1
                except: fail += 1
            except: fail += 1
        await status_msg.edit(f"تمت الإذاعة بنجاح.\n- نجاح: {succ}\n- فشل: {fail}")

# ==========================================
# 9. نقطة البداية
# ==========================================
async def main():
    await client.start(bot_token=BOT_TOKEN)
    logger.info("Aura eSIM Elite Bot running smoothly with dynamic admin controls.")
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
