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

cur.execute('''CREATE TABLE IF NOT EXISTS reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    order_id TEXT,
    rating INTEGER,
    comment TEXT,
    date TEXT
)''')

cur.execute('''CREATE TABLE IF NOT EXISTS user_sessions (
    user_id INTEGER PRIMARY KEY,
    state_key TEXT,
    state_data TEXT,
    expires_at TEXT
)''')

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

# تحديث الباقات والدقائق المطلوبة لفودافون (850، 1600، 2300، 3700)
DEFAULT_PLANS = [
    ('vodafone', 'Vodafone Unlimited 1 Month', 'vf_1m', 20.0, 850, 1, 5000, 1, 0, 'بيانات لا محدودة + 850 دقيقة اتصال'),
    ('vodafone', 'Vodafone Unlimited 3 Months', 'vf_3m', 35.0, 1600, 3, 5000, 1, 0, 'بيانات لا محدودة + 1600 دقيقة اتصال'),
    ('vodafone', 'Vodafone Unlimited 6 Months', 'vf_6m', 60.0, 2300, 6, 5000, 1, 0, 'بيانات لا محدودة + 2300 دقيقة اتصال'),
    ('vodafone', 'Vodafone Unlimited 12 Months', 'vf_12m', 80.0, 3700, 12, 5000, 1, 0, 'بيانات لا محدودة + 3700 دقيقة اتصال'),
    
    ('holafly', 'Holafly Unlimited 1 Month', 'hf_1m', 15.0, 0, 1, 5000, 1, 0, 'هولافلاي إنترنت لا محدود بالكامل - بدون استخدام عادل'),
    ('holafly', 'Holafly Unlimited 3 Months', 'hf_3m', 30.0, 0, 3, 5000, 1, 0, 'هولافلاي إنترنت لا محدود بالكامل - بدون استخدام عادل'),
    ('holafly', 'Holafly Unlimited 6 Months', 'hf_6m', 50.0, 0, 6, 5000, 1, 0, 'هولافلاي إنترنت لا محدود بالكامل - بدون استخدام عادل'),
    ('holafly', 'Holafly Unlimited 12 Months', 'hf_12m', 70.0, 0, 12, 5000, 1, 0, 'هولافلاي إنترنت لا محدود بالكامل - بدون استخدام عادل'),

    ('maya', 'Maya Unlimited 1 Month', 'maya_1m', 12.0, 0, 1, 5000, 1, 0, 'مايا بيانات لا محدودة - تخضع للاستخدام العادل 5 جيجا يومياً'),
    ('maya', 'Maya Unlimited 3 Months', 'maya_3m', 25.0, 0, 3, 5000, 1, 0, 'مايا بيانات لا محدودة - تخضع للاستخدام العادل 5 جيجا يومياً'),

    ('dealer', 'Holafly 10 شرائح - 1 شهر', 'dealer_hf_1m', 100.0, 0, 1, 5000, 10, 1, 'عرض 10 شرائح هولافلاي لمدة 1 شهر'),
    ('dealer', 'Holafly 10 شرائح - 3 أشهر', 'dealer_hf_3m', 130.0, 0, 3, 5000, 10, 1, 'عرض 10 شرائح هولافلاي لمدة 3 أشهر'),
    ('dealer', 'Holafly 10 شرائح - 6 أشهر', 'dealer_hf_6m', 150.0, 0, 6, 5000, 10, 1, 'عرض 10 شرائح هولافلاي لمدة 6 أشهر'),
    ('dealer', 'Holafly 10 شرائح - 12 شهر', 'dealer_hf_12m', 180.0, 0, 12, 5000, 10, 1, 'عرض 10 شرائح هولافلاي لمدة 12 شهر'),
    
    ('dealer', 'Vodafone 10 شرائح - 1 شهر', 'dealer_vf_1m', 120.0, 850, 1, 5000, 10, 1, 'عرض 10 شرائح فودافون لمدة 1 شهر (850 دقيقة لكل شريحة)'),
    ('dealer', 'Vodafone 10 شرائح - 3 أشهر', 'dealer_vf_3m', 150.0, 1600, 3, 5000, 10, 1, 'عرض 10 شرائح فودافون لمدة 3 أشهر (1600 دقيقة لكل شريحة)'),
    ('dealer', 'Vodafone 10 شرائح - 6 أشهر', 'dealer_vf_6m', 170.0, 2300, 6, 5000, 10, 1, 'عرض 10 شرائح فودافون لمدة 6 أشهر (2300 دقيقة لكل شريحة)'),
    ('dealer', 'Vodafone 10 شرائح - 12 شهر', 'dealer_vf_12m', 220.0, 3700, 12, 5000, 10, 1, 'عرض 10 شرائح فودافون لمدة 12 شهر (3700 دقيقة لكل شريحة)'),

    ('dealer', 'Maya 10 شرائح - 1 شهر', 'dealer_maya_1m', 90.0, 0, 1, 5000, 10, 1, 'عرض 10 شرائح مايا لمدة 1 شهر'),
    ('dealer', 'Maya 10 شرائح - 3 أشهر', 'dealer_maya_3m', 120.0, 0, 3, 5000, 10, 1, 'عرض 10 شرائح مايا لمدة 3 أشهر'),
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

def get_forced_subs():
    rows = cur.execute("SELECT value FROM settings WHERE key LIKE 'forced_sub_%'").fetchall()
    return [r[0] for r in rows]

def add_forced_sub(channel):
    cur.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (f"forced_sub_{channel}", channel))
    conn.commit()

def remove_forced_sub(channel):
    cur.execute("DELETE FROM settings WHERE value=?", (channel,))
    conn.commit()

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
    {"name": "Algeria", "flag": "🇩🇿", "operators": "Djezzy, Mobilis"},
    {"name": "Bahrain", "flag": "🇧🇭", "operators": "Batelco, Zain, STC"},
    {"name": "Egypt", "flag": "🇪🇬", "operators": "Vodafone, Orange, Etisalat, WE"},
    {"name": "France", "flag": "🇫🇷", "operators": "Orange, SFR, Free, Bouygues"},
    {"name": "Germany", "flag": "🇩🇪", "operators": "T-Mobile, Vodafone, O2"},
    {"name": "Iraq", "flag": "🇮🇶", "operators": "Zain, Asiacell, Korek"},
    {"name": "Italy", "flag": "🇮🇹", "operators": "TIM, Vodafone, WindTre, Iliad"},
    {"name": "Jordan", "flag": "🇯🇴", "operators": "Orange, Zain, Umniah"},
    {"name": "Kuwait", "flag": "🇰🇼", "operators": "Zain, Ooredoo, STC"},
    {"name": "Lebanon", "flag": "🇱🇧", "operators": "Alfa, Touch"},
    {"name": "Libya", "flag": "🇱🇾", "operators": "LTT, Almadar, Libyana"},
    {"name": "Morocco", "flag": "🇲🇦", "operators": "Maroc Telecom, Orange, Inwi"},
    {"name": "Oman", "flag": "🇴🇲", "operators": "Omantel, Ooredoo, Vodafone"},
    {"name": "Palestine", "flag": "🇵🇸", "operators": "Jawwal, Ooredoo"},
    {"name": "Qatar", "flag": "🇶🇦", "operators": "Ooredoo, Vodafone"},
    {"name": "Saudi Arabia", "flag": "🇸🇦", "operators": "STC, Mobily, Zain"},
    {"name": "Spain", "flag": "🇪🇸", "operators": "Movistar, Vodafone, Orange, Yoigo"},
    {"name": "Sudan", "flag": "🇸🇩", "operators": "Zain, MTN, Sudani"},
    {"name": "Syria", "flag": "🇸🇾", "operators": "Syriatel, MTN"},
    {"name": "Tunisia", "flag": "🇹🇳", "operators": "Ooredoo, Orange, Tunisie Telecom"},
    {"name": "Turkey", "flag": "🇹🇷", "operators": "Turkcell, Vodafone, Türk Telekom"},
    {"name": "United Arab Emirates", "flag": "🇦🇪", "operators": "Etisalat (e&), du, Virgin Mobile"},
    {"name": "United Kingdom", "flag": "🇬🇧", "operators": "EE, Vodafone, O2, Three"},
    {"name": "United States", "flag": "🇺🇸", "operators": "Verizon, AT&T, T-Mobile"},
    {"name": "Yemen", "flag": "🇾🇪", "operators": "You, Sabafon, Yemen Mobile"}
]

COUNTRY_ALIASES = {
    'مصر': 'Egypt', 'egypt': 'Egypt',
    'السعودية': 'Saudi Arabia', 'saudi arabia': 'Saudi Arabia', 'ksa': 'Saudi Arabia',
    'الإمارات': 'United Arab Emirates', 'uae': 'United Arab Emirates', 'dubai': 'United Arab Emirates',
    'الكويت': 'Kuwait', 'kuwait': 'Kuwait',
    'قطر': 'Qatar', 'qatar': 'Qatar',
    'البحرين': 'Bahrain', 'bahrain': 'Bahrain',
    'عمان': 'Oman', 'oman': 'Oman',
    'الأردن': 'Jordan', 'jordan': 'Jordan',
    'العراق': 'Iraq', 'iraq': 'Iraq',
    'تركيا': 'Turkey', 'turkey': 'Turkey',
    'أمريكا': 'United States', 'usa': 'United States',
    'بريطانيا': 'United Kingdom', 'uk': 'United Kingdom'
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

    elif data == 'personal_section':
        await event.answer()
        btn = [
            [Button.inline(t['btn_vodafone'], b'cat_vodafone')],
            [Button.inline(t['btn_holafly'], b'cat_holafly')],
            [Button.inline(t['btn_maya'], b'cat_maya')],
            [Button.inline(t['back'], b'main')]
        ]
        await event.edit(f"<blockquote>⧺︰ <b>{t['btn_personal']}</b></blockquote>", buttons=btn, parse_mode='html')

    elif data in ['cat_vodafone', 'cat_holafly', 'cat_maya']:
        await event.answer()
        cat = data.replace('cat_', '')
        plans = cur.execute("SELECT id, name, price_usd, months, minutes FROM esims WHERE category=? AND is_dealer=0 ORDER BY months ASC", (cat,)).fetchall()
        btn = []
        for pid, name, price, m, mins in plans:
            min_str = f" ({mins} دقيقة)" if mins > 0 else ""
            btn.append([Button.inline(f"{name}{min_str} - ${price:.0f}", f'show_plan_{pid}_1'.encode())])
        btn.append([Button.inline(t['back'], b'personal_section')])
        policy = WARRANTY_POLICY_TEXT.get(lang, WARRANTY_POLICY_TEXT['ar'])
        select_dur = "اختر المدة المطلوبة:" if lang == 'ar' else "Select desired duration:"
        title_cat = t[f'btn_{cat}']
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
        back_dest = b'personal_section' if not is_dealer else b'dealer_section'
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
        btn = [
            [Button.inline(t['btn_dealer_vf'], b'dealer_vf_list')],
            [Button.inline(t['btn_dealer_hf'], b'dealer_hf_list')],
            [Button.inline(t['btn_dealer_maya'], b'dealer_maya_list')],
        ]
        if not api_row:
            btn.append([Button.inline(t['btn_dealer_api'], b'buy_api_sub_menu')])
        else:
            btn.append([Button.inline("عرض تفاصيل مفتاح الـ API", b'view_api_key_info')])
        btn.append([Button.inline(t['back'], b'main')])
        await event.edit(f"<blockquote>⧺︰ <b>{t['dealer_title']}</b></blockquote>", buttons=btn, parse_mode='html')

    elif data in ['dealer_vf_list', 'dealer_hf_list', 'dealer_maya_list']:
        await event.answer()
        plans = cur.execute("SELECT id, name, price_usd, months, minutes FROM esims WHERE category='dealer' ORDER BY months ASC").fetchall()
        api_chk = cur.execute("SELECT id FROM dealer_api_keys WHERE user_id=?", (uid,)).fetchone()
        discount_mult = 0.5 if api_chk else 1.0
        btn = []
        for pid, name, price, m, mins in plans:
            final_p = price * discount_mult
            btn.append([Button.inline(f"{name} (${final_p:.0f})", f'show_plan_{pid}_1'.encode())])
        btn.append([Button.inline(t['back'], b'dealer_section')])
        await event.edit("<blockquote>💼 <b>باقات الجملة 10 شرائح (خصم 50% لمشتركي الـ API):</b></blockquote>", buttons=btn, parse_mode='html')

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

    # ==========================================
    # لوحة تحكم الأدمن
    # ==========================================
    elif data == 'admin_panel' and is_admin(uid):
        await event.answer()
        total_sales = cur.execute("SELECT COUNT(*) FROM orders WHERE status='paid'").fetchone()[0]
        total_balance = cur.execute("SELECT SUM(balance) FROM wallets").fetchone()[0] or 0
        total_esims = cur.execute("SELECT SUM(stock) FROM esims").fetchone()[0] or 0
        total_users = cur.execute("SELECT COUNT(*) FROM users_settings").fetchone()[0] or 0
        btn = [
            [Button.inline("إضافة رصيد لعميل", b'admin_add_balance'), Button.inline("خصم رصيد", b'admin_sub_balance')],
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
    if uid in user_rate_limits and now - user_rate_limits[uid] < 0.4:
        return
    user_rate_limits[uid] = now

    text = event.text.strip() if event.text else ""
    lang = get_user_lang(uid) or 'ar'
    t = LANGS.get(lang, LANGS['ar'])

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

    # أوامر الأدمن النصية
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
    logger.info("Aura eSIM Elite Bot running smoothly with quantity selection & 10% discount.")
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
