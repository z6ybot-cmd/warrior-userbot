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
from telethon import TelegramClient, events, Button

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
DEV_ID = 1902742467

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

DEFAULT_PLANS = [
    ('vodafone', 'Vodafone Unlimited 1 Month', 'vf_1m', 20.0, 850, 1, 0, 1, 0, 'بيانات لا محدودة + 850 دقيقة اتصال'),
    ('vodafone', 'Vodafone Unlimited 3 Months', 'vf_3m', 35.0, 2500, 3, 0, 1, 0, 'بيانات لا محدودة + 2500 دقيقة اتصال'),
    ('vodafone', 'Vodafone Unlimited 6 Months', 'vf_6m', 60.0, 5000, 6, 5000, 1, 0, 'بيانات لا محدودة + 5000 دقيقة اتصال'),
    ('vodafone', 'Vodafone Unlimited 12 Months', 'vf_12m', 80.0, 10000, 12, 5000, 1, 0, 'بيانات لا محدودة + 10000 دقيقة اتصال'),
    
    ('holafly', 'Holafly Unlimited 1 Month', 'hf_1m', 15.0, 0, 1, 0, 1, 0, 'هولافلاي إنترنت لا محدود بالكامل - بدون استخدام عادل'),
    ('holafly', 'Holafly Unlimited 3 Months', 'hf_3m', 30.0, 0, 3, 0, 1, 0, 'هولافلاي إنترنت لا محدود بالكامل - بدون استخدام عادل'),
    ('holafly', 'Holafly Unlimited 6 Months', 'hf_6m', 50.0, 0, 6, 0, 1, 0, 'هولافلاي إنترنت لا محدود بالكامل - بدون استخدام عادل'),
    ('holafly', 'Holafly Unlimited 12 Months', 'hf_12m', 70.0, 0, 12, 5000, 1, 0, 'هولافلاي إنترنت لا محدود بالكامل - بدون استخدام عادل'),

    ('maya', 'Maya Unlimited 1 Month', 'maya_1m', 12.0, 0, 1, 0, 1, 0, 'مايا بيانات لا محدودة - تخضع للاستخدام العادل 5 جيجا يومياً'),
    ('maya', 'Maya Unlimited 3 Months', 'maya_3m', 25.0, 0, 3, 0, 1, 0, 'مايا بيانات لا محدودة - تخضع للاستخدام العادل 5 جيجا يومياً'),

    ('dealer', 'Holafly 10 شرائح - 1 شهر', 'dealer_hf_1m', 100.0, 0, 1, 0, 10, 1, 'عرض 10 شرائح هولافلاي لمدة 1 شهر'),
    ('dealer', 'Holafly 10 شرائح - 3 أشهر', 'dealer_hf_3m', 130.0, 0, 3, 0, 10, 1, 'عرض 10 شرائح هولافلاي لمدة 3 أشهر'),
    ('dealer', 'Holafly 10 شرائح - 6 أشهر', 'dealer_hf_6m', 150.0, 0, 6, 0, 10, 1, 'عرض 10 شرائح هولافلاي لمدة 6 أشهر'),
    ('dealer', 'Holafly 10 شرائح - 12 شهر', 'dealer_hf_12m', 180.0, 0, 12, 5000, 10, 1, 'عرض 10 شرائح هولافلاي لمدة 12 شهر'),
    
    ('dealer', 'Vodafone 10 شرائح - 1 شهر', 'dealer_vf_1m', 120.0, 850, 1, 0, 10, 1, 'عرض 10 شرائح فودافون لمدة 1 شهر'),
    ('dealer', 'Vodafone 10 شرائح - 3 أشهر', 'dealer_vf_3m', 150.0, 2500, 3, 0, 10, 1, 'عرض 10 شرائح فودافون لمدة 3 أشهر'),
    ('dealer', 'Vodafone 10 شرائح - 6 أشهر', 'dealer_vf_6m', 170.0, 5000, 6, 5000, 10, 1, 'عرض 10 شرائح فودافون لمدة 6 أشهر'),
    ('dealer', 'Vodafone 10 شرائح - 12 شهر', 'dealer_vf_12m', 220.0, 10000, 12, 5000, 10, 1, 'عرض 10 شرائح فودافون لمدة 12 شهر'),

    ('dealer', 'Maya 10 شرائح - 1 شهر', 'dealer_maya_1m', 90.0, 0, 1, 0, 10, 1, 'عرض 10 شرائح مايا لمدة 1 شهر'),
    ('dealer', 'Maya 10 شرائح - 3 أشهر', 'dealer_maya_3m', 120.0, 0, 3, 0, 10, 1, 'عرض 10 شرائح مايا لمدة 3 أشهر'),
]

for cat, name, code, price, mins, months, stock, min_q, is_dlr, desc in DEFAULT_PLANS:
    cur.execute('''INSERT OR IGNORE INTO esims 
        (category, name, code_key, price_usd, minutes, months, stock, min_qty, is_dealer, description)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', 
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


async def get_channel_entity(channel_str):
    try:
        entity = await client.get_entity(channel_str)
        return entity
    except Exception as e:
        logger.error(f"Error getting channel entity {channel_str}: {e}")
        return channel_str

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

    forced_channels = get_forced_subs()
    if forced_channels:
        missing_subs = []
        for ch in forced_channels:
            try:
                await client.get_permissions(ch, uid)
            except:
                missing_subs.append(ch)
        
        if missing_subs:
            sub_text = "عذراً، يجب عليك الاشتراك في القنوات التالية للمتابعة:" if current_lang == 'ar' else "Sorry, you must subscribe to the following channels to continue:"
            sub_btns = []
            for ch in missing_subs:
                clean_ch = ch.replace('@', '')
                sub_btns.append([Button.url(f"اشتراك في {ch}", f"https://t.me/{clean_ch}")])
            sub_btns.append([Button.inline("تحقق من الاشتراك", b'main')])
            await event.reply(
                f"<blockquote>⧺︰ <b>{sub_text}</b>\n" + "\n".join(missing_subs) + "</blockquote>",
                buttons=sub_btns, parse_mode='html'
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
        new_l = data.split('_')[2]
        set_user_lang(uid, new_l)
        new_t = LANGS.get(new_l, LANGS['ar'])
        await event.answer(new_t['lang_changed'], alert=True)
        text, btn = main_menu(uid)
        await event.edit(text, buttons=btn, parse_mode='html')
        return

    if data == 'main':
        text, btn = main_menu(uid)
        await event.edit(text, buttons=btn, parse_mode='html')

    elif data == 'change_language':
        btn = [
            [Button.inline("🇸🇦 العربية", b'set_lang_ar'), Button.inline("🇬🇧 English", b'set_lang_en')],
            [Button.inline(t['back'], b'main')]
        ]
        await event.edit("<blockquote>⧺︰ <b>اختر لغتك / Select language:</b></blockquote>", buttons=btn, parse_mode='html')

    elif data == 'personal_section':
        btn = [
            [Button.inline(t['btn_vodafone'], b'cat_vodafone')],
            [Button.inline(t['btn_holafly'], b'cat_holafly')],
            [Button.inline(t['back'], b'main')]
        ]
        await event.edit(f"<blockquote>⧺︰ <b>{t['btn_personal']}</b></blockquote>", buttons=btn, parse_mode='html')

    elif data == 'dealer_section':
        api_row = cur.execute("SELECT api_key FROM dealer_api_keys WHERE user_id=?", (uid,)).fetchone()
        btn = [
            [Button.inline(t['btn_dealer_hf'], b'dealer_hf_list')],
            [Button.inline(t['btn_dealer_vf'], b'dealer_vf_list')],
        ]
        if not api_row:
            btn.append([Button.inline(t['btn_dealer_api'], b'buy_api_sub_menu')])
        else:
            btn.append([Button.inline("عرض تفاصيل مفتاح الـ API", b'view_api_key_info')])
        btn.append([Button.inline(t['back'], b'main')])
        await event.edit(f"<blockquote>⧺︰ <b>{t['dealer_title']}</b></blockquote>", buttons=btn, parse_mode='html')

    elif data == 'buy_api_sub_menu':
        api_row = cur.execute("SELECT api_key FROM dealer_api_keys WHERE user_id=?", (uid,)).fetchone()
        if api_row:
            already_sub = "لديك اشتراك API مفعل مسبقاً!" if lang=='ar' else "You already have an active API subscription!"
            return await event.answer(already_sub, alert=True)
        
        btn = [
            [Button.inline("شراء تفعيل API الآن مقابل $100", b'confirm_buy_api_sub')],
            [Button.inline(t['back'], b'dealer_section')]
        ]
        desc_sub = "🔌 <b>اشتراك وتفعيل نظام الـ API للتجار:</b>\n\n• تكلفة التفعيل لمرة واحدة: <b>$100</b>\n• المميزات: خصم دائم <b>50%</b> على كافة خدمات ومخزون البوت + مفتاح API رسمي لسحب الخدمات تلقائياً." if lang=='ar' else "🔌 <b>Dealer API Subscription:</b>\n\n• Cost: <b>$100</b>\n• Benefits: Permanent <b>50% OFF</b> + Official API Key."
        await event.edit(desc_sub, buttons=btn, parse_mode='html')

    elif data == 'confirm_buy_api_sub':
        balance = get_wallet_balance(uid)
        if balance < 100.0:
            return await event.answer(t['insufficient_balance'], alert=True)
        
        update_wallet(uid, -100.0, 'api_subscription', 'شراء تفعيل نظام API للتجار مع خصم 50%')
        api_key = f"AURA_API_{secrets.token_hex(16).upper()}"
        cur.execute("INSERT OR REPLACE INTO dealer_api_keys (user_id, api_key, created_date) VALUES (?, ?, ?)", 
                    (uid, api_key, datetime.now().strftime("%Y-%m-%d %H:%M")))
        conn.commit()
        
        success_txt = f"🎉 <b>مبروك! تم تفعيل اشتراك الـ API بنجاح وإليك مفتاحك الخاص:</b>\n\n<code>{api_key}</code>\n\nتم تطبيق خصم 50% على جميع طلباتك ومخزونك." if lang=='ar' else f"🎉 <b>Success! API subscription activated:</b>\n\n<code>{api_key}</code>"
        btn = [[Button.inline(t['back'], b'main')]]
        await event.edit(success_txt, buttons=btn, parse_mode='html')

    elif data == 'view_api_key_info':
        api_row = cur.execute("SELECT api_key FROM dealer_api_keys WHERE user_id=?", (uid,)).fetchone()
        if not api_row:
            return await event.answer("ليس لديك اشتراك API", alert=True)
        api_key_str = api_row[0]
        info_msg = f"🔌 <b>مفتاح الـ API الخاص بك:</b>\n<code>{api_key_str}</code>\n\nيمكنك استخدام هذا المفتاح في ترويسة الطلبات (Authorization Header) لسحب الخدمات تلقائياً بخصم 50%." if lang=='ar' else f"🔌 <b>Your API Key:</b>\n<code>{api_key_str}</code>"
        btn = [[Button.inline(t['back'], b'dealer_section')]]
        await event.edit(info_msg, buttons=btn, parse_mode='html')

    elif data == 'support_ticket':
        SessionManager.set(uid, f'support_ticket_{uid}', True)
        await event.edit(t['support_prompt'], buttons=[[Button.inline(t['back'], b'main')]], parse_mode='html')

    elif data == 'verify_payment_menu':
        SessionManager.set(uid, f'verify_payment_{uid}', True)
        await event.edit(t['verify_prompt'], buttons=[[Button.inline(t['back'], b'wallet')]], parse_mode='html')

    elif data.startswith('admin_reply_'):
        if not is_admin(uid): return
        target_uid = int(data.split('_')[2])
        SessionManager.set(uid, f'admin_reply_user_{uid}', target_uid)
        reply_prompt = f"<blockquote>⧺︰ <b>أرسل الرد للعميل (User ID: {target_uid}):</b></blockquote>" if lang == 'ar' else f"<blockquote>⧺︰ <b>Send reply to client (User ID: {target_uid}):</b></blockquote>"
        await event.edit(reply_prompt, parse_mode='html')

    elif data == 'admin_panel':
        if not is_admin(uid):
            no_auth = "غير مصرح لك" if lang == 'ar' else "Unauthorized"
            return await event.answer(no_auth, alert=True)

        total_sales = cur.execute("SELECT COUNT(*) FROM orders WHERE status='paid'").fetchone()[0]
        total_balance = cur.execute("SELECT SUM(balance) FROM wallets").fetchone()[0] or 0
        total_esims = cur.execute("SELECT SUM(stock) FROM esims").fetchone()[0] or 0
        total_users = cur.execute("SELECT COUNT(*) FROM users_settings").fetchone()[0] or 0

        btn = [
            [Button.inline("إضافة رصيد لعميل" if lang == 'ar' else "Add Balance", b'admin_add_balance'), Button.inline("خصم رصيد" if lang == 'ar' else "Deduct Balance", b'admin_sub_balance')],
            [Button.inline("تصفير رصيد عميل" if lang == 'ar' else "Zero Balance", b'admin_zero_balance')],
            [Button.inline("إضافة مخزون للأقسام" if lang == 'ar' else "Add Stock", b'admin_add_stock'), Button.inline("عرض الإحصائيات" if lang == 'ar' else "Statistics", b'admin_stats_details')],
            [Button.inline("تصدير نسخة احتياطية" if lang == 'ar' else "Export Backup", b'admin_export_backup'), Button.inline("استيراد نسخة احتياطية" if lang == 'ar' else "Import Backup", b'admin_import_backup')],
            [Button.inline("إدارة شرائح معينة" if lang == 'ar' else "Manage Sections", b'admin_manage_sections')],
            [Button.inline("تطوير الاشتراك الإجباري" if lang == 'ar' else "Forced Sub", b'admin_manage_forced_full')],
            [Button.inline("حظر / فك حظر" if lang == 'ar' else "Ban / Unban", b'admin_manage_bans'), Button.inline("إدارة الأدمنية" if lang == 'ar' else "Manage Admins", b'admin_manage_admins')],
            [Button.inline("إذاعة عامة" if lang == 'ar' else "Broadcast", b'admin_broadcast_msg')],
            [Button.inline(t['back'], b'main')]
        ]
        users_label = "إجمالي المستخدمين:" if lang == 'ar' else "Total Users:"
        await event.edit(
            f"{t['admin_panel_title']}\n\n"
            f"<blockquote>⧺︰ <b>{users_label}</b> <code>{total_users}</code></blockquote>\n"
            f"<blockquote>⧺︰ <b>{t['stats_sales']}:</b> <code>{total_sales}</code></blockquote>\n"
            f"<blockquote>⧺︰ <b>{t['stats_wallets']}:</b> <code>${total_balance:.2f}</code></blockquote>\n"
            f"<blockquote>⧺︰ <b>{t['stats_esims']}:</b> <code>${total_esims}</code></blockquote>",
            buttons=btn, parse_mode='html'
        )

    elif data == 'admin_export_backup' and is_admin(uid):
        db_path = 'esim_market.db'
        if os.path.exists(db_path):
            await event.reply("📁 <b>إليك النسخة الاحتياطية لقاعدة البيانات كاملة:</b>", file=db_path, parse_mode='html')
        else:
            await event.answer("ملف القاعدة غير موجود", alert=True)
        return

    elif data == 'admin_import_backup' and is_admin(uid):
        SessionManager.set(uid, f'admin_import_db_{uid}', True)
        await event.edit("📁 <b>أرسل الآن ملف قاعدة البيانات (.db) الجديد لاستبدال النسخة الحالية واستيرادها:</b>", buttons=[[Button.inline(t['back'], b'admin_panel')]], parse_mode='html')
        return

    elif data == 'admin_manage_sections' and is_admin(uid):
        sections = cur.execute("SELECT DISTINCT category FROM esims").fetchall()
        btn = []
        for (sec,) in sections:
            btn.append([Button.inline(f"إظهار/حذف قسم: {sec}", f"admin_sec_toggle_{sec}".encode())])
        btn.append([Button.inline("➕ إضافة قسم جديد", b'admin_sec_add')])
        btn.append([Button.inline(t['back'], b'admin_panel')])
        await event.edit("📂 <b>إدارة الأقسام (إظهار وحذف وتعديل الأقسام):</b>", buttons=btn, parse_mode='html')

    elif data.startswith('admin_sec_toggle_') and is_admin(uid):
        sec_name = data.replace('admin_sec_toggle_', '')
        btn = [
            [Button.inline("🗑️ حذف هذا القسم بالكامل ومحتوياته", f"admin_sec_delete_{sec_name}".encode())],
            [Button.inline("👁️‍🗨️ عرض محتويات القسم", f"admin_sec_view_{sec_name}".encode())],
            [Button.inline(t['back'], b'admin_manage_sections')]
        ]
        await event.edit(f"📂 <b>إدارة القسم: {sec_name}</b>", buttons=btn, parse_mode='html')

    elif data.startswith('admin_sec_delete_') and is_admin(uid):
        sec_name = data.replace('admin_sec_delete_', '')
        cur.execute("DELETE FROM esims WHERE category=?", (sec_name,))
        conn.commit()
        await event.answer(f"تم حذف القسم {sec_name} بنجاح", alert=True)
        await callback(event) # Refresh

    elif data == 'admin_manage_forced_full' and is_admin(uid):
        channels = get_forced_subs()
        btn = []
        for ch in channels:
            btn.append([Button.inline(f"🗑️ حذف القناة: {ch}", f"admin_del_forced_{ch}".encode())])
        btn.append([Button.inline("➕ إضافة قناة اشتراك إجباري جديدة", b'admin_add_forced')])
        btn.append([Button.inline(t['back'], b'admin_panel')])
        await event.edit("📢 <b>إدارة قنوات الاشتراك الإجباري الكاملة:</b>\n\nالقنوات الحالية:\n" + ("\n".join(channels) if channels else "لا توجد قنوات مسجلة"), buttons=btn, parse_mode='html')

    elif data == 'admin_add_forced' and is_admin(uid):
        SessionManager.set(uid, f'admin_add_forced_chan_{uid}', True)
        await event.edit("📢 <b>أرسل معرف القناة المراد إضافتها (مثال: @ChannelUsername أو معرف رقمي):</b>", buttons=[[Button.inline(t['back'], b'admin_panel')]], parse_mode='html')
        return

    elif data.startswith('admin_del_forced_') and is_admin(uid):
        ch_to_del = data.replace('admin_del_forced_', '')
        remove_forced_sub(ch_to_del)
        await event.answer("تم حذف القناة بنجاح", alert=True)
        # Refresh panel
        await callback(event)

    elif data == 'admin_stats_details' and is_admin(uid):
        paid_revenue = cur.execute("SELECT SUM(total_usd) FROM orders WHERE status='paid'").fetchone()[0] or 0
        back_admin = "رجوع لوحة التحكم" if lang == 'ar' else "Back to Admin Panel"
        rev_label = "تقرير أرباح وإحصائيات متجر Aura eSIM Elite الدقيقة:" if lang == 'ar' else "Aura eSIM Elite Earnings Report:"
        net_rev = "صافي إيرادات المبيعات:" if lang == 'ar' else "Net Sales Revenue:"
        btn = [[Button.inline(back_admin, b'admin_panel')]]
        await event.edit(f"<blockquote>⧺︰ <b>{rev_label}</b></blockquote>\n\n> ⧺︰ {net_rev} <code>${paid_revenue:.2f}</code>", buttons=btn, parse_mode='html')

    elif data == 'admin_broadcast_msg' and is_admin(uid):
        bc_title = "إذاعة عامة" if lang == 'ar' else "General Broadcast"
        bc_prompt = "أرسل الرسالة المراد اذاعتها لجميع المستخدمين:" if lang == 'ar' else "Send the message you want to broadcast to all users:"
        await event.edit(f"<blockquote>⧺︰ <b>{bc_title}</b>\n> ⧺︰ <b>{bc_prompt}</b></blockquote>", buttons=[[Button.inline(t['back'], b'admin_panel')]], parse_mode='html')
        SessionManager.set(uid, f'broadcast_{uid}', True)

    elif data == 'admin_add_balance' and is_admin(uid):
        title = "إضافة رصيد لعميل" if lang == 'ar' else "Add Balance to Client"
        prompt = "أرسل آيدي العميل ثم المبلغ (مثال: 123456789 50):" if lang == 'ar' else "Send client ID then amount (e.g. 123456789 50):"
        await event.edit(f"<blockquote>⧺︰ <b>{title}</b>\n> ⧺︰ <b>{prompt}</b></blockquote>", buttons=[[Button.inline(t['back'], b'admin_panel')]], parse_mode='html')
        SessionManager.set(uid, f'add_balance_{uid}', True)

    elif data == 'admin_sub_balance' and is_admin(uid):
        title = "خصم رصيد من عميل" if lang == 'ar' else "Deduct Balance from Client"
        prompt = "أرسل آيدي العميل ثم المبلغ (مثال: 123456789 20):" if lang == 'ar' else "Send client ID then amount (e.g. 123456789 20):"
        await event.edit(f"<blockquote>⧺︰ <b>{title}</b>\n> ⧺︰ <b>{prompt}</b></blockquote>", buttons=[[Button.inline(t['back'], b'admin_panel')]], parse_mode='html')
        SessionManager.set(uid, f'sub_balance_{uid}', True)

    elif data == 'admin_zero_balance' and is_admin(uid):
        title = "تصفير رصيد عميل" if lang == 'ar' else "Zero Client Balance"
        prompt = "أرسل آيدي العميل المراد تصفير محفظته:" if lang == 'ar' else "Send client ID to zero their wallet:"
        await event.edit(f"<blockquote>⧺︰ <b>{title}</b>\n> ⧺︰ <b>{prompt}</b></blockquote>", buttons=[[Button.inline(t['back'], b'admin_panel')]], parse_mode='html')
        SessionManager.set(uid, f'zero_balance_{uid}', True)

    elif data == 'admin_add_stock' and is_admin(uid):
        title = "إضافة مخزون عام" if lang == 'ar' else "Add General Stock"
        prompt = "أرسل الكمية المراد إضافتها:" if lang == 'ar' else "Send quantity to add:"
        await event.edit(f"<blockquote>⧺︰ <b>{title}</b>\n> ⧺︰ <b>{prompt}</b></blockquote>", buttons=[[Button.inline(t['back'], b'admin_panel')]], parse_mode='html')
        SessionManager.set(uid, f'add_stock_{uid}', True)

    elif data == 'admin_manage_bans' and is_admin(uid):
        title = "إدارة الحظر" if lang == 'ar' else "Manage Bans"
        prompt = "أرسل آيدي المستخدم لتعطيل/تفعيل الحظر:" if lang == 'ar' else "Send user ID to ban/unban:"
        await event.edit(f"<blockquote>⧺︰ <b>{title}</b>\n> ⧺︰ <b>{prompt}</b></blockquote>", buttons=[[Button.inline(t['back'], b'admin_panel')]], parse_mode='html')
        SessionManager.set(uid, f'manage_bans_{uid}', True)

    elif data == 'admin_manage_admins' and is_admin(uid):
        title = "إدارة الأدمنية" if lang == 'ar' else "Manage Admins"
        prompt = "أرسل آيدي المستخدم لرفعه/تنزيله:" if lang == 'ar' else "Send user ID to promote/demote:"
        await event.edit(f"<blockquote>⧺︰ <b>{title}</b>\n> ⧺︰ <b>{prompt}</b></blockquote>", buttons=[[Button.inline(t['back'], b'admin_panel')]], parse_mode='html')
        SessionManager.set(uid, f'manage_admins_{uid}', True)

    elif data == 'wallet':
        balance = get_wallet_balance(uid)
        bot_me = await client.get_me()
        ref_link = f"https://t.me/{bot_me.username}?start=ref{uid}"
        ref_label = "رابط الإحالة الخاص بك (احصل على رصيد لمحفظتك فور إتمام المدعو أول عملية شراء):" if lang == 'ar' else "Your Referral Link:"
        text = f"{t['wallet_title']}\n\n<blockquote>⧺︰ <b>{t['current_balance']}:</b> <code>${balance:.2f}</code></blockquote>\n\n<blockquote>⧺︰ <b>{ref_label}</b>\n<code>{ref_link}</code></blockquote>"
        btn = [
            [Button.inline(t['charge_wallet_btn'], b'charge_wallet')],
            [Button.inline(t['btn_transactions'], b'wallet_transactions')],
            [Button.inline(t['btn_verify_payment'], b'verify_payment_menu')],
            [Button.inline(t['back'], b'main')]
        ]
        await event.edit(text, buttons=btn, parse_mode='html')

    elif data == 'wallet_transactions':
        txs = cur.execute("SELECT type, amount, balance_after, description, date FROM wallet_transactions WHERE user_id=? ORDER BY id DESC LIMIT 10", (uid,)).fetchall()
        if not txs:
            empty_tx = "📜 لا توجد حركات مالية مسجلة في محفظتك حتى الآن." if lang == 'ar' else "📜 No transactions recorded yet."
            return await event.edit(f"<blockquote>⧺︰ <b>{empty_tx}</b></blockquote>", buttons=[[Button.inline(t['back'], b'wallet')]], parse_mode='html')
        
        tx_title = "📜 سجل آخر الحركات المعاملات المالية في محفظتك:" if lang == 'ar' else "📜 Recent Wallet Transactions:"
        tx_text = f"<blockquote>⧺︰ <b>{tx_title}</b></blockquote>\n\n"
        for t_type, amt, b_after, desc, date in txs:
            sign = "+" if amt > 0 else ""
            tx_text += f"• <b>{desc}</b>\n  ↳ المبلغ: <code>{sign}${amt:.2f}</code> | الرصيد بعد: <code>${b_after:.2f}</code>\n  ↳ التاريخ: {date}\n───────────────────\n"
        
        btn = [[Button.inline(t['back'], b'wallet')]]
        await event.edit(tx_text, buttons=btn, parse_mode='html')

    elif data == 'charge_wallet':
        SessionManager.set(uid, f'charge_amount_prompt_{uid}', True)
        await event.edit(t['charge_prompt'], buttons=[[Button.inline(t['back'], b'wallet')]], parse_mode='html')

    elif data.startswith('show_all_payments_'):
        parts = data.split('_')
        amount = parts[3]
        SessionManager.set(uid, f'charging_amount_{uid}', float(amount))
        networks = cur.execute("SELECT network_name, address, binance_id FROM binance_networks").fetchall()
        details_text = t['show_all_payments_title'].replace("$amount", amount) + "\n\n"
        for idx, (n_name, n_addr, n_id) in enumerate(networks, 1):
            details_text += f"<b>{idx}. {n_name}</b>\n"
            if n_id and n_id != '':
                details_text += f"• <code>ID / Pay ID:</code> <code>{n_id}</code>\n"
            if n_addr and n_addr != '':
                details_text += f"• <code>Address:</code> <code>{n_addr}</code>\n"
            details_text += "───────────────────\n"
        details_text += t['show_all_payments_footer']
        btn = [
            [Button.inline(t['btn_verify_now'], b'verify_payment_menu')],
            [Button.inline(t['back'], b'wallet')]
        ]
        await event.edit(details_text, buttons=btn, parse_mode='html')

    elif data.startswith('show_order_payments_'):
        parts = data.split('_')
        order_id = parts[3]
        session = SessionManager.get(uid, f'buy_{uid}')
        if not session: 
            expired_msg = "انتهت الجلسة" if lang == 'ar' else "Session expired"
            return await event.answer(expired_msg, alert=True)
        price = session['price']
        networks = cur.execute("SELECT network_name, address, binance_id FROM binance_networks").fetchall()
        gateway_title = f"Comprehensive Payment Gateway for Order: {order_id}" if lang == 'en' else f"بوابة الدفع الشاملة لطلبك: {order_id}"
        total_req = f"Total amount required:" if lang == 'en' else f"المبلغ الإجمالي المطلوب:"
        all_methods = f"Here are all available payment methods, IDs, and addresses:" if lang == 'en' else f"إليك كافة طرق الدفع والمعرفات والعناوين المتاحة للتحويل:"
        transfer_notice = f"Transfer the amount (${price:.2f}), then click the verify button below to send your receipt or transaction ID." if lang == 'en' else f"قم بالتحويل بمبلغ (${price:.2f}), ثم انقر على زر التحقق أدناه لإرسال الإيصال أو معرف المعاملة."

        details_text = f"<blockquote>⧺︰ <b>{gateway_title}</b>\n"
        details_text += f"⧺︰ <b>{total_req}</b> <code>${price:.2f}</code></blockquote>\n\n"
        details_text += f"<blockquote>⧺︰ <b>{all_methods}</b></blockquote>\n\n"
        for idx, (n_name, n_addr, n_id) in enumerate(networks, 1):
            details_text += f"<b>{idx}. {n_name}</b>\n"
            if n_id and n_id != '':
                details_text += f"• <code>ID / Pay ID:</code> <code>{n_id}</code>\n"
            if n_addr and n_addr != '':
                details_text += f"• <code>Address:</code> <code>{n_addr}</code>\n"
            details_text += "───────────────────\n"
        details_text += f"\n> ⧺︰ <b>{transfer_notice}</b>"
        btn = [
            [Button.inline(t['btn_verify_now'], b'verify_payment_menu')],
            [Button.inline(t['back'], b'main')]
        ]
        await event.edit(details_text, buttons=btn, parse_mode='html')

    elif data == 'cat_vodafone':
        plans = cur.execute("SELECT id, name, price_usd, months, minutes FROM esims WHERE category='vodafone' AND is_dealer=0 ORDER BY months ASC").fetchall()
        btn = []
        for pid, name, price, m, mins in plans:
            btn.append([Button.inline(f"Vodafone - {m} {'Months' if lang=='en' else 'شهر'} (${price:.0f})", f'show_plan_{pid}'.encode())])
        btn.append([Button.inline(t['back'], b'personal_section')])
        policy = WARRANTY_POLICY_TEXT.get(lang, WARRANTY_POLICY_TEXT['ar'])
        select_dur = "اختر المدة المطلوبة (1، 3، 6، أو 12 شهر):" if lang == 'ar' else "Select desired duration:"
        await event.edit(f"<blockquote>⧺︰ <b>{t['btn_vodafone']}</b></blockquote>\n\n{policy}\n\n> ⧺︰ <b>{select_dur}</b>", buttons=btn, parse_mode='html')

    elif data == 'cat_holafly':
        plans = cur.execute("SELECT id, name, price_usd, months, minutes FROM esims WHERE category='holafly' AND is_dealer=0 ORDER BY months ASC").fetchall()
        btn = []
        for pid, name, price, m, mins in plans:
            btn.append([Button.inline(f"Holafly - {m} {'Months' if lang=='en' else 'شهر'} (${price:.0f})", f'show_plan_{pid}'.encode())])
        btn.append([Button.inline(t['back'], b'personal_section')])
        policy = WARRANTY_POLICY_TEXT.get(lang, WARRANTY_POLICY_TEXT['ar'])
        select_dur = "اختر المدة المطلوبة (1، 3، 6، أو 12 شهر):" if lang == 'ar' else "Select desired duration:"
        await event.edit(f"<blockquote>⧺︰ <b>{t['btn_holafly']}</b></blockquote>\n\n{policy}\n\n> ⧺︰ <b>{select_dur}</b>", buttons=btn, parse_mode='html')

    elif data.startswith('show_plan_'):
        pid = int(data.split('_')[2])
        plan = cur.execute("SELECT id, name, price_usd, minutes, months, stock, category FROM esims WHERE id=?", (pid,)).fetchone()
        if not plan: 
            not_avail = "الباقة غير متوفرة" if lang == 'ar' else "Plan not available"
            return await event.answer(not_avail, alert=True)
        esim_id, name, price, mins, months, stock, cat = plan
        back_target = 'cat_vodafone' if cat == 'vodafone' else 'cat_holafly'
        
        SessionManager.set(uid, f'plan_choice_{uid}', esim_id)

        btn = [
            [Button.inline(t['type_global'], f'plan_type_global_{esim_id}'.encode())],
            [Button.inline(t['type_country'], f'plan_type_country_{esim_id}_0'.encode())],
            [Button.inline(t['back'], back_target.encode())]
        ]
        policy = WARRANTY_POLICY_TEXT.get(lang, WARRANTY_POLICY_TEXT['ar'])
        price_label = "السعر:" if lang == 'ar' else "Price:"
        dur_label = "المدة:" if lang == 'ar' else "Duration:"
        months_str = "شهر / أشهر" if lang == 'ar' else "month(s)"
        await event.edit(f"<blockquote>⧺︰ <b>{name}</b>\n⧺︰ {price_label} ${price:.0f}\n⧺︰ {dur_label} {months} {months_str}</blockquote>\n\n{t['select_type']}\n\n{policy}", buttons=btn, parse_mode='html')

    elif data.startswith('plan_type_global_'):
        esim_id = int(data.split('_')[3])
        plan = cur.execute("SELECT name, price_usd FROM esims WHERE id=?", (esim_id,)).fetchone()
        price = plan[1]
        SessionManager.set(uid, f'pending_checkout_{uid}', {'esim_id': esim_id, 'price': price, 'qty': 1, 'is_dealer': 0, 'scope': 'Global'})

        pay_direct = "الدفع مباشرة" if lang == 'ar' else "Pay Directly"
        add_cart_btn = t['add_to_cart']
        confirm_title = "تأكيد الباقة" if lang == 'ar' else "Plan Confirmation"
        coverage_label = "نطاق التغطية:" if lang == 'ar' else "Coverage Scope:"
        total_label = "السعر الإجمالي:" if lang == 'ar' else "Total Price:"

        btn = [
            [Button.inline(pay_direct, f'proceed_pay_{esim_id}_0'.encode())],
            [Button.inline(add_cart_btn, f'add_cart_item_{esim_id}_Global_{price}'.encode())],
            [Button.inline(t['back'], b'main')]
        ]
        await event.edit(f"<blockquote>⧺︰ <b>{confirm_title}</b>\n⧺︰ {coverage_label} <b>Global Plan / باقة عالمية</b>\n⧺︰ {total_label} <code>${price:.2f}</code></blockquote>", buttons=btn, parse_mode='html')

    elif data.startswith('proceed_pay_'):
        parts = data.split('_')
        esim_id = int(parts[2])
        session_data = SessionManager.get(uid, f'pending_checkout_{uid}')
        if not session_data: 
            expired_msg = "انتهت الجلسة" if lang == 'ar' else "Session expired"
            return await event.answer(expired_msg, alert=True)
        final_price = session_data['price']
        order_id = f"AURA{secrets.token_hex(4).upper()}"
        SessionManager.set(uid, f'buy_{uid}', {'esim_id': esim_id, 'order_id': order_id, 'price': final_price, 'qty': session_data['qty'], 'is_dealer': session_data['is_dealer'], 'scope': session_data['scope']})

        final_total = "الإجمالي النهائي:" if lang == 'ar' else "Final Total:"
        btn = [
            [Button.inline(t['pay_wallet'], f'pay_wallet_{order_id}'.encode())],
            [Button.inline(t['pay_binance'], f'show_order_payments_{order_id}'.encode())],
            [Button.inline(t['back'], b'main')]
        ]
        await event.edit(f"<blockquote>⧺︰ <b>{t['confirm_buy']}</b>\n⧺︰ {final_total} <code>${final_price:.2f}</code></blockquote>", buttons=btn, parse_mode='html')

    elif data.startswith('plan_type_country_'):
        parts = data.split('_')
        esim_id = int(parts[3])
        page = int(parts[4])
        per_page = 10
        start, end = page * per_page, (page + 1) * per_page
        countries_page = COUNTRIES_DATA[start:end]
        total_pages = (len(COUNTRIES_DATA) + per_page - 1) // per_page

        btn = [
            [Button.inline(t['search_country_btn'], f'search_country_start_{esim_id}'.encode())]
        ]
        for c in countries_page:
            btn.append([Button.inline(f"{c['flag']} {c['name']}", f"sel_country_{esim_id}_{c['name']}".encode())])
        
        nav = []
        if page > 0: nav.append(Button.inline(t['prev_page'], f"plan_type_country_{esim_id}_{page-1}".encode()))
        if page < total_pages - 1: nav.append(Button.inline(t['next_page'], f"plan_type_country_{esim_id}_{page+1}".encode()))
        if nav: btn.append(nav)
        btn.append([Button.inline(t['back'], f'show_plan_{esim_id}'.encode())])
        await event.edit(f"<blockquote>⧺︰ <b>{t['select_country_prompt']}</b></blockquote>", buttons=btn, parse_mode='html')

    elif data.startswith('search_country_start_'):
        esim_id = int(data.split('_')[3])
        SessionManager.set(uid, f'search_country_{uid}', esim_id)
        await event.edit(f"<blockquote>⧺︰ <b>{t['search_prompt']}</b></blockquote>", buttons=[[Button.inline(t['back'], f'plan_type_country_{esim_id}_0'.encode())]], parse_mode='html')

    elif data.startswith('sel_country_'):
        parts = data.split('_')
        esim_id = int(parts[2])
        country_name = parts[3]
        plan = cur.execute("SELECT name, price_usd FROM esims WHERE id=?", (esim_id,)).fetchone()
        price = plan[1]
        SessionManager.set(uid, f'pending_checkout_{uid}', {'esim_id': esim_id, 'price': price, 'qty': 1, 'is_dealer': 0, 'scope': country_name})

        pay_direct_btn = "الدفع مباشرة" if lang == 'ar' else "Pay Directly"
        add_cart_btn = t['add_to_cart']
        sel_country_label = "الدولة المختارة:" if lang == 'ar' else "Selected Country:"
        base_price_label = "السعر الأساسي:" if lang == 'ar' else "Base Price:"

        btn = [
            [Button.inline(pay_direct_btn, f'proceed_pay_{esim_id}_0'.encode())],
            [Button.inline(add_cart_btn, f'add_cart_item_{esim_id}_{country_name}_{price}'.encode())],
            [Button.inline(t['back'], b'main')]
        ]
        await event.edit(f"<blockquote>⧺︰ <b>{sel_country_label}</b> <b>{country_name}</b>\n⧺︰ {base_price_label} <code>${price:.2f}</code></blockquote>", buttons=btn, parse_mode='html')

    elif data.startswith('add_cart_item_'):
        parts = data.split('_')
        esim_id = int(parts[3])
        scope = parts[4]
        price = float(parts[5])
        cur.execute("INSERT INTO cart (user_id, esim_id, scope, price) VALUES (?, ?, ?, ?)", (uid, esim_id, scope, price))
        conn.commit()
        added_msg = "تم إضافة المنتج إلى السلة بنجاح!" if lang == 'ar' else "Item successfully added to cart!"
        await event.answer(added_msg, alert=True)

    elif data == 'view_cart':
        items = cur.execute("SELECT c.id, e.name, c.scope, c.price FROM cart c JOIN esims e ON c.esim_id=e.id WHERE c.user_id=?", (uid,)).fetchall()
        if not items:
            empty_msg = "سلة المشتريات فارغة تماماً." if lang == 'ar' else "Your shopping cart is empty."
            return await event.edit(f"<blockquote>⧺︰ <b>{empty_msg}</b></blockquote>", buttons=[[Button.inline(t['back'], b'main')]], parse_mode='html')
        
        cart_title = "محتويات سلة المشتريات الخاصة بك:" if lang == 'ar' else "Your Shopping Cart Items:"
        cart_text = f"<blockquote>⧺︰ <b>{cart_title}</b></blockquote>\n\n"
        total_cart_price = 0
        btn = []
        for cid, name, scope, price in items:
            cart_text += f"• <b>{name}</b> ({scope}) - <code>${price:.2f}</code>\n"
            total_cart_price += price
            del_text = "حذف" if lang == 'ar' else "Remove"
            btn.append([Button.inline(f"{del_text}: {name} ({scope})", f"cart_del_{cid}".encode())])
        
        tot_label = "الإجمالي:" if lang == 'ar' else "Total Price:"
        cart_text += f"\n> ⧺︰ <b>{tot_label}</b> <code>${total_cart_price:.2f}</code>"
        checkout_cart_btn = "إتمام الدفع لكافة محتويات السلة" if lang == 'ar' else "Proceed Cart Checkout"
        btn.append([Button.inline(checkout_cart_btn, b'cart_checkout')])
        btn.append([Button.inline(t['back'], b'main')])
        await event.edit(cart_text, buttons=btn, parse_mode='html')

    elif data.startswith('cart_del_'):
        cid = int(data.split('_')[2])
        cur.execute("DELETE FROM cart WHERE id=? AND user_id=?", (cid, uid))
        conn.commit()
        await callback(event)
        return

    elif data == 'cart_checkout':
        items = cur.execute("SELECT c.esim_id, c.scope, c.price, e.name FROM cart c JOIN esims e ON c.esim_id=e.id WHERE c.user_id=?", (uid,)).fetchall()
        if not items:
            return await event.answer("السلة فارغة", alert=True)
        total_price = sum(item[2] for item in items)
        order_id = f"AURA{secrets.token_hex(4).upper()}"
        SessionManager.set(uid, f'cart_buy_{uid}', {'items': items, 'total': total_price, 'order_id': order_id})
        confirm_title = "تأكيد طلب السلة" if lang == 'ar' else "Cart Order Confirmation"
        tot_label = "المبلغ الإجمالي للباقات:" if lang == 'ar' else "Total Cart Amount:"
        btn = [
            [Button.inline(t['pay_wallet'], f'cart_pay_wallet_{order_id}'.encode())],
            [Button.inline(t['pay_binance'], f'cart_show_payments_{order_id}'.encode())],
            [Button.inline(t['back'], b'view_cart')]
        ]
        await event.edit(f"<blockquote>⧺︰ <b>{confirm_title}</b>\n⧺︰ {tot_label} <code>${total_price:.2f}</code></blockquote>", buttons=btn, parse_mode='html')

    elif data.startswith('cart_show_payments_'):
        order_id = data.split('_')[3]
        session = SessionManager.get(uid, f'cart_buy_{uid}')
        if not session: return await event.answer("انتهت الجلسة", alert=True)
        price = session['total']
        networks = cur.execute("SELECT network_name, address, binance_id FROM binance_networks").fetchall()
        details_text = f"<blockquote>⧺︰ <b>بوابة الدفع الشاملة للسلة: {order_id}</b>\nالإجمالي المطلوب: <code>${price:.2f}</code></blockquote>\n\n"
        for idx, (n_name, n_addr, n_id) in enumerate(networks, 1):
            details_text += f"<b>{idx}. {n_name}</b>\n"
            if n_id: details_text += f"• <code>ID:</code> <code>{n_id}</code>\n"
            if n_addr: details_text += f"• <code>Address:</code> <code>{n_addr}</code>\n"
            details_text += "───────────────────\n"
        btn = [[Button.inline(t['btn_verify_now'], b'verify_payment_menu')], [Button.inline(t['back'], b'view_cart')]]
        await event.edit(details_text, buttons=btn, parse_mode='html')

    elif data.startswith('cart_pay_wallet_'):
        order_id = data.split('_')[3]
        session = SessionManager.get(uid, f'cart_buy_{uid}')
        if not session: return await event.answer("انتهت الجلسة", alert=True)
        total_price = session['total']
        if uid not in wallet_locks:
            wallet_locks[uid] = asyncio.Lock()
        async with wallet_locks[uid]:
            balance = get_wallet_balance(uid)
            if balance < total_price:
                return await event.answer(t['insufficient_balance'], alert=True)
            update_wallet(uid, -total_price, 'purchase', f"شراء سلة مشتريات {order_id}")
            all_codes_text = f"تفاصيل شرائح سلة المشتريات (طلب: {order_id}) - تفعيل فوري باركود أو تخطي يدوي:\n" if lang == 'ar' else f"Cart eSIM Details (Order: {order_id}):\n"
            for esim_id, scope, price, name in session['items']:
                sub_order_id = f"AURA{secrets.token_hex(4).upper()}"
                cur.execute("INSERT INTO orders VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", 
                            (sub_order_id, uid, esim_id, 1, price, price, None, 'paid', 0, 1, datetime.now().strftime("%Y-%m-%d %H:%M"), datetime.now().strftime("%Y-%m-%d %H:%M")))
                cur.execute("UPDATE esims SET stock=stock-1 WHERE id=?", (esim_id,))
                await check_low_stock_and_alert(esim_id)
                all_codes_text += f"\n• {name} ({scope}):\n`{DEFAULT_LPA}`\n"
            cur.execute("DELETE FROM cart WHERE user_id=?", (uid,))
            conn.commit()

        SessionManager.remove(uid, f'cart_buy_{uid}')
        bio = io.BytesIO(all_codes_text.encode('utf-8'))
        bio.name = f"Aura_Cart_Codes_{order_id}.txt"
        bio.seek(0)
        success_cart_msg = "<blockquote>⧺︰ <b>تم دفع وإنجاز طلب السلة بنجاح! الشريحة تدعم التفعيل الفوري بباركود أو تخطي يدوي. تم إرسال ملف أكواد التفعيل أدناه:</b></blockquote>" if lang == 'ar' else "<blockquote>⧺︰ <b>Cart order successfully paid and processed! File sent below:</b></blockquote>"
        await event.edit(success_cart_msg, file=bio, parse_mode='html')

    elif data.startswith('reload_order_'):
        sub_order_id = data.split('_')[2]
        order_row = cur.execute("SELECT o.quantity, o.total_usd, o.created_date, e.name FROM orders o JOIN esims e ON o.esim_id=e.id WHERE o.order_id=? AND o.user_id=?", (sub_order_id, uid)).fetchone()
        if not order_row:
            return await event.answer("الطلب غير موجود أو غير متاح", alert=True)
        qty, total, date, name = order_row
        reloaded_text = f"تفاصيل الطلب [{sub_order_id}]:\n• المنتج: {name}\n• الكمية: {qty}\n• التاريخ: {date}\n• تفعيل فوري بباركود أو تخطي يدوي (LPA):\n`{DEFAULT_LPA}`"
        
        btn = [
            [Button.inline(t['back'], b'my_orders')]
        ]
        await event.edit(f"<blockquote>⧺︰ <b>إعادة تحميل تفاصيل وأكواد الطلب (باركود أو تخطي يدوي):</b></blockquote>\n\n{reloaded_text}", buttons=btn, parse_mode='html')

    elif data == 'countries_list' or data.startswith('countries_page_'):
        page = int(data.split('_')[2]) if data.startswith('countries_page_') else 0
        per_page = 40
        start, end = page * per_page, (page + 1) * per_page
        countries_page = COUNTRIES_DATA[start:end]
        total_pages = (len(COUNTRIES_DATA) + per_page - 1) // per_page
        c_text = "".join([f"⧺︰ {c['flag']} <b>{c['name']}</b> - {c['operators']}\n" for c in countries_page])
        btn = [
            [Button.inline(t['search_country_btn'], b'main_search_country')]
        ]
        nav = []
        if page > 0: nav.append(Button.inline(t['prev_page'], f"countries_page_{page-1}".encode()))
        if page < total_pages - 1: nav.append(Button.inline(t['next_page'], f"countries_page_{page+1}".encode()))
        if nav: btn.append(nav)
        btn.append([Button.inline(t['back'], b'main')])
        countries_title = t['countries_header'].replace("COUNTRIES_COUNT", str(len(COUNTRIES_DATA)))
        await event.edit(countries_title + c_text, buttons=btn, parse_mode='html')

    elif data == 'main_search_country':
        SessionManager.set(uid, f'search_country_{uid}', 'general')
        await event.edit(f"<blockquote>⧺︰ <b>{t['search_prompt']}</b></blockquote>", buttons=[[Button.inline(t['back'], b'countries_list')]], parse_mode='html')

    elif data == 'dealer_hf_list':
        plans = cur.execute("SELECT id, name, price_usd, months FROM esims WHERE category='dealer' AND code_key LIKE 'dealer_hf_%' ORDER BY months ASC").fetchall()
        btn = []
        api_chk = cur.execute("SELECT id FROM dealer_api_keys WHERE user_id=?", (uid,)).fetchone()
        discount_mult = 0.5 if api_chk else 1.0
        for pid, name, price, m in plans:
            final_p = price * discount_mult
            btn.append([Button.inline(f"Holafly 10 شرائح - {m} {'Months' if lang=='en' else 'شهر'} (${final_p:.0f})", f'buy_dealer_bundle_id_{pid}_{final_p}'.encode())])
        btn.append([Button.inline(t['back'], b'dealer_section')])
        header_hf = "عروض Holafly لجملة 10 شرائح (1، 3، 6، 12 شهر)" if lang=='ar' else "Holafly Wholesale Offers (1, 3, 6, 12M)"
        await event.edit(f"<blockquote>⧺︰ <b>{header_hf}</b></blockquote>", buttons=btn, parse_mode='html')

    elif data == 'dealer_vf_list':
        plans = cur.execute("SELECT id, name, price_usd, months FROM esims WHERE category='dealer' AND code_key LIKE 'dealer_vf_%' ORDER BY months ASC").fetchall()
        btn = []
        api_chk = cur.execute("SELECT id FROM dealer_api_keys WHERE user_id=?", (uid,)).fetchone()
        discount_mult = 0.5 if api_chk else 1.0
        for pid, name, price, m in plans:
            final_p = price * discount_mult
            btn.append([Button.inline(f"Vodafone 10 شرائح - {m} {'Months' if lang=='en' else 'شهر'} (${final_p:.0f})", f'buy_dealer_bundle_id_{pid}_{final_p}'.encode())])
        btn.append([Button.inline(t['back'], b'dealer_section')])
        header_vf = "عروض Vodafone لجملة 10 شرائح (1، 3، 6، 12 شهر)" if lang=='ar' else "Vodafone Wholesale Offers (1, 3, 6, 12M)"
        await event.edit(f"<blockquote>⧺︰ <b>{header_vf}</b></blockquote>", buttons=btn, parse_mode='html')

    elif data.startswith('buy_dealer_bundle_id_'):
        parts = data.split('_')
        pid = int(parts[4])
        price = float(parts[5])
        plan = cur.execute("SELECT name FROM esims WHERE id=?", (pid,)).fetchone()
        order_id = f"AURA{secrets.token_hex(4).upper()}"
        SessionManager.set(uid, f'buy_{uid}', {'esim_id': pid, 'order_id': order_id, 'price': price, 'qty': 10, 'is_dealer': 1, 'scope': 'Wholesale 10 eSIMs'})

        btn = [
            [Button.inline(t['pay_wallet'], f'pay_wallet_{order_id}'.encode())],
            [Button.inline(t['pay_binance'], f'show_order_payments_{order_id}'.encode())],
            [Button.inline(t['back'], b'dealer_section')]
        ]
        await event.edit(f"<blockquote>⧺︰ <b>{t['confirm_buy']}</b>\n• الباقة: {plan[0]}\n• الإجمالي: <code>${price:.2f}</code></blockquote>", buttons=btn, parse_mode='html')

    elif data.startswith('pay_wallet_'):
        order_id = data.split('_')[2]
        session = SessionManager.get(uid, f'buy_{uid}')
        if not session: 
            expired_msg = "انتهت الجلسة" if lang == 'ar' else "Session expired"
            return await event.answer(expired_msg, alert=True)
        price = session['price']
        qty = session['qty']
        esim_id = session['esim_id']
        if uid not in wallet_locks:
            wallet_locks[uid] = asyncio.Lock()
        async with wallet_locks[uid]:
            balance = get_wallet_balance(uid)
            if balance < price:
                charge_wallet_btn_text = "شحن المحفظة الآن" if lang == 'ar' else "Charge Wallet Now"
                current_bal_label = "رصيدك الحالي:" if lang == 'ar' else "Current Balance:"
                required_label = "المطلوب:" if lang == 'ar' else "Required:"
                btn = [
                    [Button.inline(charge_wallet_btn_text, b'charge_wallet')],
                    [Button.inline(t['back'], b'main')]
                ]
                await event.edit(f"<blockquote>⧺︰ <b>{t['insufficient_balance']}</b>\n⧺︰ {current_bal_label} <code>${balance:.2f}</code> | {required_label} <code>${price:.2f}</code></blockquote>", buttons=btn, parse_mode='html')
                return

            esim = cur.execute("SELECT name FROM esims WHERE id=?", (esim_id,)).fetchone()
            desc_purchase = f"شراء {qty}x {esim[0]}" if lang == 'ar' else f"Purchase {qty}x {esim[0]}"
            update_wallet(uid, -price, 'purchase', desc_purchase)
            cur.execute("INSERT INTO orders VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", (order_id, uid, esim_id, qty, price/qty, price, None, 'paid', session['is_dealer'], 1, datetime.now().strftime("%Y-%m-%d %H:%M"), datetime.now().strftime("%Y-%m-%d %H:%M")))
            cur.execute("UPDATE esims SET stock=stock-? WHERE id=?", (qty, esim_id))
            conn.commit()
            await check_low_stock_and_alert(esim_id)

        SessionManager.remove(uid, f'buy_{uid}')

        if qty > 1:
            lpa_list_text = f"تفاصيل طلبك ({qty} شرائح - تفعيل فوري باركود أو تخطي يدوي):\n" + "\n".join([f"شريحة {i+1}: {DEFAULT_LPA}" for i in range(qty)]) if lang == 'ar' else f"Order Details ({qty} eSIMs):\n" + "\n".join([f"eSIM {i+1}: {DEFAULT_LPA}" for i in range(qty)])
            bio = io.BytesIO(lpa_list_text.encode('utf-8'))
            bio.name = f"Aura_eSIM_Codes_{order_id}.txt"
            bio.seek(0)
            success_multi_text = "<blockquote>⧺︰ <b>تم الشراء بنجاح!</b>\nتم إرسال ملف يحتوي على كافة أكواد التفعيل الخاصة بـ {qty} شرائح (باركود أو تخطي يدوي) أدناه:</blockquote>" if lang == 'ar' else "<blockquote>⧺︰ <b>Successfully purchased!</b>\nA file containing all activation codes for {qty} eSIMs has been sent below:</blockquote>"
            await event.edit(success_multi_text, file=bio, parse_mode='html')
        else:
            success_single_text = f"<blockquote>⧺︰ <b>تم الشراء بنجاح!</b>\n<b>تفعيل فوري باركود أو تخطي يدوي (LPA):</b>\n<code>{DEFAULT_LPA}</code></blockquote>" if lang == 'ar' else f"<blockquote>⧺︰ <b>Successfully purchased!</b>\n<b>Activation Code (LPA):</b>\n<code>{DEFAULT_LPA}</code></blockquote>"
            await event.edit(success_single_text, file=DEFAULT_BARCODE, parse_mode='html')

    elif data == 'my_orders':
        orders = cur.execute("SELECT o.order_id, e.name, o.quantity, o.total_usd, o.created_date FROM orders o JOIN esims e ON o.esim_id=e.id WHERE o.user_id=? AND o.status='paid' ORDER BY o.created_date DESC LIMIT 10", (uid,)).fetchall()
        if not orders: return await event.edit(t['no_orders'], buttons=[[Button.inline(t['back'], b'main')]], parse_mode='html')
        text = f"{t['my_orders_title']}\n\n"
        btn = []
        for order_id, name, qty, total, date in orders:
            text += f"• <b>{qty}x {name}</b> ({date}) | ${total:.2f}\n"
            btn.append([Button.inline(f"تفاصيل الطلب: {order_id}", f"reload_order_{order_id}".encode())])
        btn.append([Button.inline(t['back'], b'main')])
        await event.edit(text, buttons=btn, parse_mode='html')

    elif data.startswith('admin_approve_dep_'):
        if not is_admin(uid): return
        parts = data.split('_')
        target_uid = int(parts[3])
        dep_amount = float(parts[4]) if len(parts) > 4 else 20.0
        try:
            admin_dep_desc = f"شحن عبر إيصال منصات مقبول بقيمة ${dep_amount}" if lang == 'ar' else f"Deposit via approved platform receipt of ${dep_amount}"
            update_wallet(target_uid, dep_amount, 'admin_deposit', admin_dep_desc)
            client_approved_msg = f"<blockquote>⧺︰ <b>تم قبول إيصال الدفع والشحن الخاص بك بنجاح وإضافة ${dep_amount:.2f} إلى محفظتك!</b></blockquote>" if lang == 'ar' else f"<blockquote>⧺︰ <b>Your payment receipt and deposit have been successfully accepted and ${dep_amount:.2f} added to your wallet!</b></blockquote>"
            admin_approved_notice = f"<blockquote>⧺︰ <b>تم قبول الطلب وشحن رصيد العميل بقيمة ${dep_amount:.2f} بنجاح.</b></blockquote>" if lang == 'ar' else f"<blockquote>⧺︰ <b>Request accepted and client wallet credited with ${dep_amount:.2f} successfully.</b></blockquote>"
            panel_btn_text = "لوحة التحكم" if lang == 'ar' else "Admin Panel"
            await client.send_message(target_uid, client_approved_msg, parse_mode='html')
            await event.edit(admin_approved_notice, buttons=[[Button.inline(panel_btn_text, b'admin_panel')]], parse_mode='html')
        except Exception as e:
            await event.edit(f"❌ Error: {e}")

    elif data.startswith('admin_reject_dep_'):
        if not is_admin(uid): return
        parts = data.split('_')
        target_uid = int(parts[3]) if len(parts) > 3 else int(data.split('_')[3])
        try:
            client_rejected_msg = "<blockquote>⧺︰ <b>عذراً، تم رفض إيصال الدفع الخاص بك أو لم يتم التحقق منه. يرجى مراجعة الدعم.</b></blockquote>" if lang == 'ar' else "<blockquote>⧺︰ <b>Sorry, your payment receipt was rejected or could not be verified. Please contact support.</b></blockquote>"
            admin_rejected_notice = "<blockquote>⧺︰ <b>تم رفض الطلب وإبلاغ المستخدم.</b></blockquote>" if lang == 'ar' else "<blockquote>⧺︰ <b>Request rejected and user notified.</b></blockquote>"
            panel_btn_text = "لوحة التحكم" if lang == 'ar' else "Admin Panel"
            await client.send_message(target_uid, client_rejected_msg, parse_mode='html')
            await event.edit(admin_rejected_notice, buttons=[[Button.inline(panel_btn_text, b'admin_panel')]], parse_mode='html')
        except Exception as e:
            await event.edit(f"❌ Error: {e}")

@client.on(events.NewMessage)
async def handler(event):
    uid = event.sender_id
    if is_banned(uid): return
    
    now = time.time()
    if uid in user_rate_limits and now - user_rate_limits[uid] < 0.8:
        return
    user_rate_limits[uid] = now

    text = event.text.strip() if event.text else ""
    lang = get_user_lang(uid) or 'ar'
    t = LANGS.get(lang, LANGS['ar'])

    if SessionManager.has(uid, f'admin_import_db_{uid}'):
        SessionManager.remove(uid, f'admin_import_db_{uid}')
        panel_btn_text = "لوحة التحكم" if lang == 'ar' else "Admin Panel"
        if event.media:
            try:
                await event.download_media(file='esim_market.db')
                await event.reply("✅ <b>تم استيراد قاعدة البيانات واستبدالها بنجاح تام!</b>", buttons=[[Button.inline(panel_btn_text, b'admin_panel')]], parse_mode='html')
            except Exception as e:
                await event.reply(f"❌ خطأ أثناء الاستيراد: {e}", buttons=[[Button.inline(panel_btn_text, b'admin_panel')]], parse_mode='html')
        else:
            await event.reply("❌ لم يتم إرسال ملف بصيغة صحيحة.", buttons=[[Button.inline(panel_btn_text, b'admin_panel')]], parse_mode='html')
        return

    if SessionManager.has(uid, f'admin_add_forced_chan_{uid}'):
        SessionManager.remove(uid, f'admin_add_forced_chan_{uid}')
        panel_btn_text = "لوحة التحكم" if lang == 'ar' else "Admin Panel"
        add_forced_sub(text)
        await event.reply(f"✅ <b>تمت إضافة القناة {text} بنجاح إلى قنوات الاشتراك الإجباري!</b>", buttons=[[Button.inline(panel_btn_text, b'admin_panel')]], parse_mode='html')
        return

    if SessionManager.has(uid, f'zero_balance_{uid}'):
        SessionManager.remove(uid, f'zero_balance_{uid}')
        panel_btn_text = "لوحة التحكم" if lang == 'ar' else "Admin Panel"
        try:
            target_uid = int(text)
            current_bal = get_wallet_balance(target_uid)
            if current_bal > 0:
                admin_zero_desc = "تصفير الرصيد بواسطة الأدمن" if lang == 'ar' else "Balance zeroed by admin"
                update_wallet(target_uid, -current_bal, 'admin_zero', admin_zero_desc)
            success_zero = f"<blockquote>⧺︰ <b>تم تصفير رصيد المستخدم {target_uid} بنجاح وأصبح $0.00</b></blockquote>" if lang == 'ar' else f"<blockquote>⧺︰ <b>User {target_uid} balance successfully zeroed to $0.00</b></blockquote>"
            await event.reply(success_zero, buttons=[[Button.inline(panel_btn_text, b'admin_panel')]], parse_mode='html')
        except:
            err_zero = "<blockquote>⧺︰ <b>صيغة خاطئة. أرسل آيدي صحيح (مثال: 123456789)</b></blockquote>" if lang == 'ar' else "<blockquote>⧺︰ <b>Invalid format. Send a valid ID (e.g. 123456789)</b></blockquote>"
            await event.reply(err_zero, buttons=[[Button.inline(panel_btn_text, b'admin_panel')]], parse_mode='html')
        return

    if SessionManager.has(uid, f'add_balance_{uid}'):
        SessionManager.remove(uid, f'add_balance_{uid}')
        panel_btn_text = "لوحة التحكم" if lang == 'ar' else "Admin Panel"
        try:
            parts = text.split()
            target_uid = int(parts[0])
            amount = float(parts[1])
            admin_add_desc = "إضافة رصيد بواسطة الأدمن" if lang == 'ar' else "Balance added by admin"
            update_wallet(target_uid, amount, 'admin_deposit', admin_add_desc)
            success_add = f"<blockquote>⧺︰ <b>تم إضافة ${amount:.2f} بنجاح إلى محفظة المستخدم {target_uid}</b></blockquote>" if lang == 'ar' else f"<blockquote>⧺︰ <b>Successfully added ${amount:.2f} to user {target_uid} wallet</b></blockquote>"
            await event.reply(success_add, buttons=[[Button.inline(panel_btn_text, b'admin_panel')]], parse_mode='html')
            try:
                client_add_msg = f"<blockquote>⧺︰ <b>تمت إضافة مبلغ ${amount:.2f} إلى محفظتك من قبل الإدارة!</b></blockquote>" if lang == 'ar' else f"<blockquote>⧺︰ <b>Admin added ${amount:.2f} to your wallet!</b></blockquote>"
                await client.send_message(target_uid, client_add_msg, parse_mode='html')
            except:
                pass
        except:
            err_add = "<blockquote>⧺︰ <b>صيغة خاطئة. مثال: <code>123456789 50</code></b></blockquote>" if lang == 'ar' else "<blockquote>⧺︰ <b>Invalid format. Example: <code>123456789 50</code></b></blockquote>"
            await event.reply(err_add, buttons=[[Button.inline(panel_btn_text, b'admin_panel')]], parse_mode='html')
        return

    if SessionManager.has(uid, f'sub_balance_{uid}'):
        SessionManager.remove(uid, f'sub_balance_{uid}')
        panel_btn_text = "لوحة التحكم" if lang == 'ar' else "Admin Panel"
        try:
            parts = text.split()
            target_uid = int(parts[0])
            amount = float(parts[1])
            admin_sub_desc = "خصم رصيد بواسطة الأدمن" if lang == 'ar' else "Balance deducted by admin"
            update_wallet(target_uid, -amount, 'admin_withdraw', admin_sub_desc)
            success_sub = f"<blockquote>⧺︰ <b>تم خصم ${amount:.2f} بنجاح من محفظة المستخدم {target_uid}</b></blockquote>" if lang == 'ar' else f"<blockquote>⧺︰ <b>Successfully deducted ${amount:.2f} from user {target_uid} wallet</b></blockquote>"
            await event.reply(success_sub, buttons=[[Button.inline(panel_btn_text, b'admin_panel')]], parse_mode='html')
            try:
                client_sub_msg = f"<blockquote>⧺︰ <b>تم خصم مبلغ ${amount:.2f} من محفظتك من قبل الإدارة.</b></blockquote>" if lang == 'ar' else f"<blockquote>⧺︰ <b>Admin deducted ${amount:.2f} from your wallet.</b></blockquote>"
                await client.send_message(target_uid, client_sub_msg, parse_mode='html')
            except:
                pass
        except:
            err_sub = "<blockquote>⧺︰ <b>صيغة خاطئة. مثال: <code>123456789 20</code></b></blockquote>" if lang == 'ar' else "<blockquote>⧺︰ <b>Invalid format. Example: <code>123456789 20</code></b></blockquote>"
            await event.reply(err_sub, buttons=[[Button.inline(panel_btn_text, b'admin_panel')]], parse_mode='html')
        return

    if SessionManager.has(uid, f'charge_amount_prompt_{uid}'):
        SessionManager.remove(uid, f'charge_amount_prompt_{uid}')
        try:
            amount = float(text)
            if amount < 20:
                await event.reply(t['min_charge_err'], parse_mode='html')
                SessionManager.set(uid, f'charge_amount_prompt_{uid}', True)
                return
            SessionManager.set(uid, f'charging_amount_{uid}', amount)
            show_all_btn_text = "عرض كافة طرق وعناوين الدفع برِسالة واحدة" if lang == 'ar' else "Show All Payment Methods & Addresses"
            deposit_label = "المبلغ المراد إيداعه:" if lang == 'ar' else "Amount to deposit:"
            click_prompt = "انقر أدناه لعرض كافة شبكات وعناوين الدفع دفعة واحدة:" if lang == 'ar' else "Click below to view all payment networks and addresses at once:"
            btn = [
                [Button.inline(show_all_btn_text, f'show_all_payments_{amount}'.encode())],
                [Button.inline(t['back'], b'wallet')]
            ]
            await event.reply(f"<blockquote>⧺︰ <b>{deposit_label} <code>${amount:.2f}</code></b></blockquote>\n\n> ⧺︰ <b>{click_prompt}</b>", buttons=btn, parse_mode='html')
        except:
            await event.reply(t['invalid_number_err'], parse_mode='html')
            SessionManager.set(uid, f'charge_amount_prompt_{uid}', True)
        return

    if SessionManager.has(uid, f'verify_payment_{uid}'):
        SessionManager.remove(uid, f'verify_payment_{uid}')
        await event.reply(t['verify_sent'], buttons=[[Button.inline(t['back'], b'wallet')]], parse_mode='html')
        user_entity = await client.get_entity(uid)
        username = f"@{user_entity.username}" if user_entity.username else ("بدون معرف" if lang=='ar' else "No username")
        full_name = user_entity.first_name or ("مستخدم" if lang=='ar' else "User")
        dep_amt = SessionManager.pop(uid, f'charging_amount_{uid}') or 20.0
        admin_msg = (
            f"<blockquote>⧺︰ <b>طلب تحقق آلي من الدفع!</b>\n"
            f"⧺︰ 👤 <b>اسم العميل:</b> {full_name}\n"
            f"⧺︰ 🆔 <b>الايدي:</b> <code>{uid}</code>\n"
            f"⧺︰ 🔗 <b>اليوزر:</b> {username}\n"
            f"⧺︰ 💰 <b>المبلغ المراد شحنه:</b> <code>${dep_amt:.2f}</code>\n"
            f"⧺︰ 💬 <b>معرف المعاملة / السكرين:</b> {text if text else 'صورة إيصال الدفع'}</blockquote>"
        )
        admin_buttons = [
            [
                Button.inline("قبول الدفع وشحن الرصيد", f"admin_approve_dep_{uid}_{dep_amt}".encode()),
                Button.inline("رفض الإيصال", f"admin_reject_dep_{uid}".encode())
            ]
        ]
        try:
            if event.media:
                await client.send_file(DEV_ID, event.media, caption=admin_msg, buttons=admin_buttons, parse_mode='html')
            else:
                await client.send_message(DEV_ID, admin_msg, buttons=admin_buttons, parse_mode='html')
        except Exception as e:
            logger.error(f"Verify payment send error: {e}")
        return

    if SessionManager.has(uid, f'support_ticket_{uid}'):
        SessionManager.remove(uid, f'support_ticket_{uid}')
        await event.reply(t['support_sent'], buttons=[[Button.inline(t['back'], b'main')]], parse_mode='html')
        try:
            user_entity = await client.get_entity(uid)
            username = f"@{user_entity.username}" if user_entity.username else ("بدون معرف" if lang=='ar' else "No username")
            full_name = user_entity.first_name or ("مستخدم" if lang=='ar' else "User")
            admin_msg = (
                f"<blockquote>⧺︰ <b>تذكرة دعم فني جديدة!</b>\n"
                f"⧺︰ 👤 <b>العميل:</b> {full_name}\n"
                f"⧺︰ 🆔 <b>الايدي:</b> <code>{uid}</code>\n"
                f"⧺︰ 🔗 <b>اليوزر:</b> {username}\n"
                f"⧺︰ 💬 <b>الرسالة:</b> {text}</blockquote>"
            )
            await client.send_message(
                DEV_ID,
                admin_msg,
                buttons=[[Button.inline("رد على العميل", f"admin_reply_{uid}".encode())]],
                parse_mode='html'
            )
        except Exception as e:
            logger.error(f"Support ticket send error: {e}")
        return

    if SessionManager.has(uid, f'admin_reply_user_{uid}'):
        target_uid = SessionManager.pop(uid, f'admin_reply_user_{uid}')
        try:
            reply_body = f"<blockquote>⧺︰ <b>رد من دعم فني Aura eSIM:</b>\n\n{text}</blockquote>" if lang == 'ar' else f"<blockquote>⧺︰ <b>Reply from Aura eSIM Support:</b>\n\n{text}</blockquote>"
            await client.send_message(target_uid, reply_body, parse_mode='html')
            success_reply = f"<blockquote>⧺︰ <b>تم إرسال الرد بنجاح إلى العميل {target_uid}</b></blockquote>" if lang == 'ar' else f"<blockquote>⧺︰ <b>Reply successfully sent to client {target_uid}</b></blockquote>"
            await event.reply(success_reply, parse_mode='html')
        except Exception as e:
            await event.reply(f"❌ Failed to send: {e}")
        return

    if SessionManager.has(uid, f'search_country_{uid}'):
        target_mode = SessionManager.pop(uid, f'search_country_{uid}')
        query_clean = text.lower().strip()
        matched_country = None
        if query_clean in COUNTRY_ALIASES:
            mapped_name = COUNTRY_ALIASES[query_clean]
            for c in COUNTRIES_DATA:
                if c['name'].lower() == mapped_name.lower():
                    matched_country = c
                    break
        else:
            for c in COUNTRIES_DATA:
                if query_clean in c['name'].lower() or c['name'].lower() in query_clean:
                    matched_country = c
                    break
        
        if matched_country:
            result_msg = f"<blockquote>⧺︰ <b>الدولة {matched_country['name']} {matched_country['flag']} مدعومة بالكامل في متجرنا Aura eSIM (تفعيل باركود أو تخطي يدوي)</b>\n> ⧺︰ 📡 <b>Networks:</b> {matched_country['operators']}</blockquote>" if lang == 'ar' else f"<blockquote>⧺︰ <b>Country {matched_country['name']} {matched_country['flag']} is fully supported in our Aura eSIM store</b>\n> ⧺︰ 📡 <b>Networks:</b> {matched_country['operators']}</blockquote>"
            back_btn = Button.inline(t['back'], b'countries_list' if target_mode == 'general' else f'plan_type_country_{target_mode}_0'.encode())
            await event.reply(result_msg, buttons=[[back_btn]], parse_mode='html')
        else:
            result_msg = f"<blockquote>⧺︰ <b>الدولة '{text}' مدعومة ضمن الباقات العالمية المتاحة في متجرنا (تفعيل باركود أو تخطي يدوي).</b></blockquote>" if lang == 'ar' else f"<blockquote>⧺︰ <b>The country '{text}' is supported via our global plans.</b></blockquote>"
            back_btn = Button.inline(t['back'], b'countries_list' if target_mode == 'general' else f'plan_type_country_{target_mode}_0'.encode())
            await event.reply(result_msg, buttons=[[back_btn]], parse_mode='html')
        return

    if SessionManager.has(uid, f'broadcast_{uid}'):
        SessionManager.remove(uid, f'broadcast_{uid}')
        users = cur.execute("SELECT user_id FROM users_settings").fetchall()
        success, failed = 0, 0
        status_init = "جاري بدء الإذاعة عبر متجر Aura eSIM..." if lang == 'ar' else "Starting broadcast via Aura eSIM store..."
        status_msg = await event.reply(f"<blockquote>⧺︰ <b>{status_init}</b></blockquote>")
        for (u_id,) in users:
            try:
                bc_msg = f"<blockquote>⧺︰ <b>إعلان رسمي من Aura eSIM:</b>\n\n{text}</blockquote>" if lang == 'ar' else f"<blockquote>⧺︰ <b>Official Announcement from Aura eSIM:</b>\n\n{text}</blockquote>"
                await client.send_message(u_id, bc_msg, parse_mode='html')
                success += 1
                await asyncio.sleep(0.04)
            except: failed += 1
        done_msg = f"<blockquote>⧺︰ <b>تمت الإذاعة بنجاح.\n- نجاح: {success}\n- فشل: {failed}</b></blockquote>" if lang == 'ar' else f"<blockquote>⧺︰ <b>Broadcast completed successfully.\n- Success: {success}\n- Failed: {failed}</b></blockquote>"
        await status_msg.edit(done_msg)
        return

    if SessionManager.has(uid, f'add_stock_{uid}'):
        SessionManager.remove(uid, f'add_stock_{uid}')
        panel_btn_text = "لوحة التحكم" if lang == 'ar' else "Admin Panel"
        try:
            cur.execute("UPDATE esims SET stock = stock + ?", (int(text),))
            conn.commit()
            success_stock = "<blockquote>⧺︰ <b>تمت إضافة المخزون بنجاح لشرايح Aura eSIM.</b></blockquote>" if lang == 'ar' else "<blockquote>⧺︰ <b>Stock successfully added for Aura eSIMs.</b></blockquote>"
            await event.reply(success_stock, buttons=[[Button.inline(panel_btn_text, b'admin_panel')]], parse_mode='html')
        except: 
            err_stock = "<blockquote>⧺︰ <b>صيغة خاطئة</b></blockquote>" if lang == 'ar' else "<blockquote>⧺︰ <b>Invalid format</b></blockquote>"
            await event.reply(err_stock, parse_mode='html')
        return

    if SessionManager.has(uid, f'manage_bans_{uid}'):
        SessionManager.remove(uid, f'manage_bans_{uid}')
        panel_btn_text = "لوحة التحكم" if lang == 'ar' else "Admin Panel"
        try:
            tid = int(text)
            if is_banned(tid):
                cur.execute("DELETE FROM bans WHERE user_id=?", (tid,))
                if tid in ban_cache: del ban_cache[tid]
                msg = f"<blockquote>⧺︰ <b>تم فك الحظر عن المستخدم {tid}</b></blockquote>" if lang == 'ar' else f"<blockquote>⧺︰ <b>User {tid} unbanned</b></blockquote>"
            else:
                cur.execute("INSERT OR REPLACE INTO bans (user_id) VALUES (?)", (tid,))
                ban_cache[tid] = True
                msg = f"<blockquote>⧺︰ <b>تم حظر المستخدم {tid} من متجر Aura eSIM</b></blockquote>" if lang == 'ar' else f"<blockquote>⧺︰ <b>User {tid} banned from Aura eSIM</b></blockquote>"
            conn.commit()
            await event.reply(msg, buttons=[[Button.inline(panel_btn_text, b'admin_panel')]], parse_mode='html')
        except: 
            err_ban = "<blockquote>⧺︰ <b>صيغة خاطئة</b></blockquote>" if lang == 'ar' else "<blockquote>⧺︰ <b>Invalid format</b></blockquote>"
            await event.reply(err_ban, parse_mode='html')
        return

    if SessionManager.has(uid, f'manage_admins_{uid}'):
        SessionManager.remove(uid, f'manage_admins_{uid}')
        panel_btn_text = "لوحة التحكم" if lang == 'ar' else "Admin Panel"
        try:
            tid = int(text)
            if tid == DEV_ID: return
            row = cur.execute("SELECT user_id FROM admins WHERE user_id=?", (tid,)).fetchone()
            if row:
                cur.execute("DELETE FROM admins WHERE user_id=?", (tid,))
                if tid in admin_cache: del admin_cache[tid]
                msg = f"<blockquote>⧺︰ <b>تم تنزيل الأدمن {tid}</b></blockquote>" if lang == 'ar' else f"<blockquote>⧺︰ <b>Admin {tid} demoted</b></blockquote>"
            else:
                cur.execute("INSERT OR REPLACE INTO admins (user_id) VALUES (?)", (tid,))
                admin_cache[tid] = True
                msg = f"<blockquote>⧺︰ <b>تم رفع الأدمن الجديد {tid} في Aura eSIM</b></blockquote>" if lang == 'ar' else f"<blockquote>⧺︰ <b>New admin {tid} promoted in Aura eSIM</b></blockquote>"
            conn.commit()
            await event.reply(msg, buttons=[[Button.inline(panel_btn_text, b'admin_panel')]], parse_mode='html')
        except: 
            err_admin = "<blockquote>⧺︰ <b>صيغة خاطئة</b></blockquote>" if lang == 'ar' else "<blockquote>⧺︰ <b>Invalid format</b></blockquote>"
            await event.reply(err_admin, parse_mode='html')
        return

async def main():
    await client.start(bot_token=BOT_TOKEN)
    logger.info("Aura eSIM Elite Bot - WEB SERVER, PHONE COMPATIBILITY & ALL EMOJIS REMOVED SUCCESSFULLY")
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
