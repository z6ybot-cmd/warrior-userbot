import os
import io
import time
import secrets
import asyncio
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv
import aiosqlite
from telethon import TelegramClient, events, Button, errors

# ==========================================
# 1. إعداد السجلات والبيئة
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

DB_NAME = "esim_market.db"

# الشريحة الموحدة لجميع الطلبات
DEFAULT_LPA = "LPA:1$hfy.prod.ondemandconnectivity.com$FA1BEB0FB081104C79BAD7E29424A4101C6BD12873E8733BD856AFF7A7B6DECC"
DEFAULT_BARCODE = f"https://api.qrserver.com/v1/create-qr-code/?data={DEFAULT_LPA}&size=500x500"

# ==========================================
# 2. القواميس والسياسات
# ==========================================
LANGS = {
    'ar': {
        'welcome': """<blockquote>⧺︰ <b>أهلاً بك في البوابـة الرقمية الفاخرة لـ Aura eSIM Elite</b></blockquote>
<blockquote>⧺︰ <b>نقدم لك أحدث حلول الاتصالات والإنترنت الرقمي العالمي بأعلى معايير الجودة</b></blockquote>
<blockquote>⧺︰ <b>تفعيل فوري، آمن، ومباشر عبر QR Code أو التخطي اليدوي بضغطة زر</b></blockquote>
<blockquote>⧺︰ <b>سرعات فائقة بلا حدود وبدون سياسة استخدام عادل</b></blockquote>
<blockquote>⧺︰ <b>فريق دعم فني متواجد ومستعد لخدمتك على مدار الساعة</b></blockquote>
<blockquote>⧺︰ <b>اختر القسم المناسب لك من القائمة أدناه للبدء بكل سهولة</b></blockquote>""",
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
        'btn_lang': "تغيير اللغة / Language",
        'back': "رجوع",
        'admin_panel_title': "<blockquote>⧺︰ <b>لوحة التحكم الذكية والمطورة لإدارة متجر Aura eSIM</b></blockquote>",
        'insufficient_balance': "<blockquote>⧺︰ <b>رصيدك غير كافٍ لإتمام هذه العملية! يرجى شحن محفظتك أولاً.</b></blockquote>",
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
        'btn_verify_now': "التحقق من الدفع وإرسال الإيصال الآن",
        'prev_page': "السابق",
        'next_page': "التالي"
    },
    'en': {
        'welcome': """<blockquote>⧺︰ <b>Welcome to Aura eSIM Elite Gateway</b></blockquote>
<blockquote>⧺︰ <b>Providing next-gen global connectivity solutions</b></blockquote>
<blockquote>⧺︰ <b>Instant & secure QR Code or manual activation</b></blockquote>
<blockquote>⧺︰ <b>Ultra-fast speeds without throttling</b></blockquote>
<blockquote>⧺︰ <b>24/7 dedicated professional support</b></blockquote>
<blockquote>⧺︰ <b>Select a category below to get started</b></blockquote>""",
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
        'insufficient_balance': "<blockquote>⧺︰ <b>Insufficient balance! Please charge your wallet first to purchase.</b></blockquote>",
        'wallet_title': "<blockquote>⧺︰ <b>Your Personal Wallet</b></blockquote>",
        'current_balance': "Current Balance",
        'charge_wallet_btn': "Charge Wallet (Available Payment Methods)",
        'charge_prompt': "<blockquote>⧺︰ <b>Charge Wallet via Crypto Networks & IDs</b></blockquote>\n\n> ⧺︰ <b>Send deposit amount in USD (Minimum $20):</b>",
        'min_charge_err': "<blockquote>⧺︰ <b>⚠️ Minimum deposit amount is $20</b></blockquote>",
        'invalid_number_err': "<blockquote>⧺︰ <b>⚠️ Please send a valid positive number.</b></blockquote>",
        'my_orders_title': "<blockquote>⧺︰ <b>Your Completed Orders (Click any order to reload activation barcode or manual setup)</b></blockquote>",
        'no_orders': "<blockquote>⧺︰ <b>You have no previous orders yet.</b></blockquote>",
        'dealer_title': "<blockquote>⧺︰ <b>Dealers & API Section (50% OFF All Services)</b></blockquote>\n\n> ⧺︰ <b>Choose option below:</b>",
        'verify_prompt': "<blockquote>⧺︰ <b>Automatic Payment Verification</b></blockquote>\n\n> ⧺︰ <b>Send your transaction ID (TxID) or screenshot for instant verification:</b>",
        'verify_sent': "<blockquote>⧺︰ <b>Your receipt has been received successfully. Processing and crediting balance!</b></blockquote>",
        'support_prompt': "<blockquote>⧺︰ <b>Direct Support Ticket System</b></blockquote>\n\n> ⧺︰ <b>Send your message or inquiry now:</b>",
        'support_sent': "<blockquote>⧺︰ <b>Your support ticket has been sent successfully. We will reply soon!</b></blockquote>",
        'btn_verify_now': "Verify Payment Now & Send Receipt",
        'prev_page': "Previous",
        'next_page': "Next"
    }
}

WARRANTY_POLICY_TEXT = {
    'ar': """<blockquote>⧺︰ <b>سياسات ومميزات الشرائح حسب المزود (Aura eSIM Elite):</b>
⧺︰ <b>شرائح هولافلاي (Holafly): إنترنت لا محدود بالكامل وبدون أي سياسة استخدام عادل (True Unlimited Data).</b>
⧺︰ <b>شرائح مايا (Maya): تخضع لسياسة الاستخدام العادل (5 جيجا يومياً بسرعة فائقة 5G، ثم إنترنت لا محدود بسرعات مخفضة).</b>
⧺︰ <b>شرائح فودافون (Vodafone): إنترنت فائق السرعة مع دقائق اتصال محلية ودولية.</b>
⧺︰ <b>ملاحظة: باقات Maya وباقات Holafly مخصصة للإنترنت فقط بدون رقم اتصال.</b></blockquote>

<blockquote>⧺︰ <b>باقة الضمان الذهبي والدعم الفني:</b>
⧺︰ <b>ضمان شامل ومستمر: دعم فني متخصص على مدار الساعة.</b>
⧺︰ <b>سياسة تعويض فورية وآمنة: حقوقك محفوظة بتمديد الفترة أو شريحة بديلة فوراً.</b>
⧺︰ <b>ضمان التخزين المرن (3 أشهر): احتفظ بالشريحة وفعلها خلال 3 أشهر من الشراء.</b></blockquote>""",
    'en': """<blockquote>⧺︰ <b>eSIM Policies & Features by Provider:</b>
⧺︰ <b>Holafly Plans: True unlimited data with ZERO Fair Usage Policy (FUP).</b>
⧺︰ <b>Maya Plans: Subject to Fair Usage Policy (5 GB daily at ultra-fast speed, then unlimited data).</b>
⧺︰ <b>Vodafone Plans: Ultra-fast internet with local & international calling minutes.</b>
⧺︰ <b>Note: Maya and Holafly plans are data-only, no phone number.</b></blockquote>

<blockquote>⧺︰ <b>Golden Warranty & Support Package:</b>
⧺︰ <b>Comprehensive Warranty: 24/7 dedicated professional support.</b>
⧺︰ <b>Instant Compensation Policy: Protected with replacement or extension.</b>
⧺︰ <b>Flexible Storage Warranty (3 Months): Activate within 3 months.</b></blockquote>"""
}

# ==========================================
# 3. إدارة الجلسات والكاش
# ==========================================
user_states = {}
lang_cache = {}
admin_cache = {}
ban_cache = {}
wallet_locks = {}
user_rate_limits = {}

def set_session(uid, key, value, duration_minutes=60):
    user_states[(uid, key)] = {
        'value': value,
        'expires': datetime.now() + timedelta(minutes=duration_minutes)
    }

def get_session(uid, key):
    entry = user_states.get((uid, key))
    if not entry:
        return None
    if datetime.now() > entry['expires']:
        user_states.pop((uid, key), None)
        return None
    return entry['value']

def clear_session(uid, key):
    user_states.pop((uid, key), None)

client = TelegramClient('esim_market', API_ID, API_HASH)

# ==========================================
# 4. إعداد قاعدة البيانات وتثبيت الجداول
# ==========================================
async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("PRAGMA journal_mode=WAL;")
        await db.execute("PRAGMA synchronous=NORMAL;")

        # جدول الباقات الكامل
        await db.execute('''CREATE TABLE IF NOT EXISTS esims (
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

        # جدول المحافظ
        await db.execute('''CREATE TABLE IF NOT EXISTS wallets (
            user_id INTEGER PRIMARY KEY,
            balance REAL DEFAULT 0,
            total_deposited REAL DEFAULT 0,
            created_date TEXT
        )''')

        # جدول المعاملات
        await db.execute('''CREATE TABLE IF NOT EXISTS wallet_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            type TEXT,
            amount REAL,
            balance_after REAL,
            description TEXT,
            date TEXT
        )''')

        # جدول طلبات الإيداع المالي للتحقق
        await db.execute('''CREATE TABLE IF NOT EXISTS deposit_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount REAL,
            tx_data TEXT,
            status TEXT DEFAULT 'pending',
            date TEXT
        )''')

        # جدول الطلبات المكتملة
        await db.execute('''CREATE TABLE IF NOT EXISTS orders (
            order_id TEXT PRIMARY KEY,
            user_id INTEGER,
            esim_id INTEGER,
            quantity INTEGER,
            price_usd REAL,
            total_usd REAL,
            lpa_code TEXT,
            status TEXT,
            is_dealer INTEGER DEFAULT 0,
            created_date TEXT
        )''')

        # سلة المشتريات
        await db.execute('''CREATE TABLE IF NOT EXISTS cart (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            esim_id INTEGER,
            scope TEXT,
            price REAL
        )''')

        # إعدادات المستخدمين
        await db.execute('''CREATE TABLE IF NOT EXISTS users_settings (
            user_id INTEGER PRIMARY KEY,
            lang TEXT DEFAULT 'ar',
            referred_by INTEGER,
            is_dealer_tier INTEGER DEFAULT 0
        )''')

        # مفاتيح التجار API
        await db.execute('''CREATE TABLE IF NOT EXISTS dealer_api_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE,
            api_key TEXT UNIQUE,
            created_date TEXT
        )''')

        # المشرفين والمحظورين
        await db.execute('''CREATE TABLE IF NOT EXISTS admins (user_id INTEGER PRIMARY KEY)''')
        await db.execute('''CREATE TABLE IF NOT EXISTS bans (user_id INTEGER PRIMARY KEY)''')
        await db.execute('''CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)''')

        # جدول طرق وشبكات الدفع القابل للإدارة بالكامل من الأدمن
        await db.execute('''CREATE TABLE IF NOT EXISTS payment_networks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            network_key TEXT UNIQUE,
            network_name TEXT,
            address TEXT,
            binance_id TEXT,
            is_active INTEGER DEFAULT 1
        )''')

        if DEV_ID:
            await db.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (DEV_ID,))

        # ملء شبكات الدفع الأولية
        default_nets = [
            ('bybit_id', 'Bybit ID / Pay ID', '', '159349409'),
            ('binance_id', 'Binance ID / Pay ID', '', '159349409'),
            ('usdt_trc20', 'USDT (TRC20)', 'TM5SqP85qKa9pait6DkqCPDcr3hDNJmDGd', ''),
            ('usdt_bep20', 'USDT (BEP20 / BSC)', '0x334c55fe51757ac79a3d290523298bd5d327df64', ''),
            ('ltc', 'Litecoin (LTC)', 'LRbz7QkKmQ9ASjkAuJSD5eYbziApzidZ9b', '')
        ]
        for k, n, a, b_id in default_nets:
            await db.execute('''INSERT OR IGNORE INTO payment_networks 
                (network_key, network_name, address, binance_id) VALUES (?, ?, ?, ?)''', (k, n, a, b_id))

        # ملء الباقات الكاملة (1، 3، 6، 12 شهر لجميع المزودين وباقات الجملة)
        full_plans = [
            # Vodafone
            ('vodafone', 'Vodafone Unlimited 1 Month', 'vf_1m', 20.0, 850, 1, 5000, 1, 0, 'بيانات لا محدودة + 850 دقيقة اتصال'),
            ('vodafone', 'Vodafone Unlimited 3 Months', 'vf_3m', 35.0, 2500, 3, 5000, 1, 0, 'بيانات لا محدودة + 2500 دقيقة اتصال'),
            ('vodafone', 'Vodafone Unlimited 6 Months', 'vf_6m', 60.0, 5000, 6, 5000, 1, 0, 'بيانات لا محدودة + 5000 دقيقة اتصال'),
            ('vodafone', 'Vodafone Unlimited 12 Months', 'vf_12m', 80.0, 10000, 12, 5000, 1, 0, 'بيانات لا محدودة + 10000 دقيقة اتصال'),
            # Holafly
            ('holafly', 'Holafly Unlimited 1 Month', 'hf_1m', 15.0, 0, 1, 5000, 1, 0, 'هولافلاي إنترنت لا محدود بالكامل - بدون استخدام عادل'),
            ('holafly', 'Holafly Unlimited 3 Months', 'hf_3m', 30.0, 0, 3, 5000, 1, 0, 'هولافلاي إنترنت لا محدود بالكامل - بدون استخدام عادل'),
            ('holafly', 'Holafly Unlimited 6 Months', 'hf_6m', 50.0, 0, 6, 5000, 1, 0, 'هولافلاي إنترنت لا محدود بالكامل - بدون استخدام عادل'),
            ('holafly', 'Holafly Unlimited 12 Months', 'hf_12m', 70.0, 0, 12, 5000, 1, 0, 'هولافلاي إنترنت لا محدود بالكامل - بدون استخدام عادل'),
            # Maya
            ('maya', 'Maya Unlimited 1 Month', 'maya_1m', 12.0, 0, 1, 5000, 1, 0, 'مايا بيانات لا محدودة - تخضع للاستخدام العادل 5 جيجا يومياً'),
            ('maya', 'Maya Unlimited 3 Months', 'maya_3m', 25.0, 0, 3, 5000, 1, 0, 'مايا بيانات لا محدودة - تخضع للاستخدام العادل 5 جيجا يومياً'),
            ('maya', 'Maya Unlimited 6 Months', 'maya_6m', 45.0, 0, 6, 5000, 1, 0, 'مايا بيانات لا محدودة - تخضع للاستخدام العادل 5 جيجا يومياً'),
            ('maya', 'Maya Unlimited 12 Months', 'maya_12m', 65.0, 0, 12, 5000, 1, 0, 'مايا بيانات لا محدودة - تخضع للاستخدام العادل 5 جيجا يومياً'),
            # Wholesale (Dealers 10x)
            ('dealer_hf', 'Holafly 10 شرائح - 1 شهر', 'dealer_hf_1m', 100.0, 0, 1, 5000, 10, 1, 'عرض 10 شرائح هولافلاي لمدة 1 شهر'),
            ('dealer_hf', 'Holafly 10 شرائح - 3 أشهر', 'dealer_hf_3m', 130.0, 0, 3, 5000, 10, 1, 'عرض 10 شرائح هولافلاي لمدة 3 أشهر'),
            ('dealer_hf', 'Holafly 10 شرائح - 6 أشهر', 'dealer_hf_6m', 150.0, 0, 6, 5000, 10, 1, 'عرض 10 شرائح هولافلاي لمدة 6 أشهر'),
            ('dealer_hf', 'Holafly 10 شرائح - 12 شهر', 'dealer_hf_12m', 180.0, 0, 12, 5000, 10, 1, 'عرض 10 شرائح هولافلاي لمدة 12 شهر'),
            ('dealer_vf', 'Vodafone 10 شرائح - 1 شهر', 'dealer_vf_1m', 120.0, 850, 1, 5000, 10, 1, 'عرض 10 شرائح فودافون لمدة 1 شهر'),
            ('dealer_vf', 'Vodafone 10 شرائح - 3 أشهر', 'dealer_vf_3m', 150.0, 2500, 3, 5000, 10, 1, 'عرض 10 شرائح فودافون لمدة 3 أشهر'),
            ('dealer_vf', 'Vodafone 10 شرائح - 6 أشهر', 'dealer_vf_6m', 170.0, 5000, 6, 5000, 10, 1, 'عرض 10 شرائح فودافون لمدة 6 أشهر'),
            ('dealer_vf', 'Vodafone 10 شرائح - 12 شهر', 'dealer_vf_12m', 220.0, 10000, 12, 5000, 10, 1, 'عرض 10 شرائح فودافون لمدة 12 شهر'),
            ('dealer_maya', 'Maya 10 شرائح - 1 شهر', 'dealer_maya_1m', 90.0, 0, 1, 5000, 10, 1, 'عرض 10 شرائح مايا لمدة 1 شهر'),
            ('dealer_maya', 'Maya 10 شرائح - 3 أشهر', 'dealer_maya_3m', 120.0, 0, 3, 5000, 10, 1, 'عرض 10 شرائح مايا لمدة 3 أشهر'),
            ('dealer_maya', 'Maya 10 شرائح - 6 أشهر', 'dealer_maya_6m', 140.0, 0, 6, 5000, 10, 1, 'عرض 10 شرائح مايا لمدة 6 أشهر'),
            ('dealer_maya', 'Maya 10 شرائح - 12 شهر', 'dealer_maya_12m', 160.0, 0, 12, 5000, 10, 1, 'عرض 10 شرائح مايا لمدة 12 شهر')
        ]
        for row in full_plans:
            await db.execute('''INSERT OR IGNORE INTO esims 
                (category, name, code_key, price_usd, minutes, months, stock, min_qty, is_dealer, description)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', row)

        await db.commit()

# ==========================================
# 5. دوال المساعدة وقواعد البيانات
# ==========================================
async def is_admin(uid):
    if uid == DEV_ID: return True
    if uid in admin_cache: return admin_cache[uid]
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT user_id FROM admins WHERE user_id=?", (uid,)) as cur:
            res = (await cur.fetchone()) is not None
            admin_cache[uid] = res
            return res

async def is_banned(uid):
    if uid in ban_cache: return ban_cache[uid]
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT user_id FROM bans WHERE user_id=?", (uid,)) as cur:
            res = (await cur.fetchone()) is not None
            ban_cache[uid] = res
            return res

async def get_user_lang(uid):
    if uid in lang_cache: return lang_cache[uid]
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT lang FROM users_settings WHERE user_id=?", (uid,)) as cur:
            row = await cur.fetchone()
            lang = row[0] if row else 'ar'
            lang_cache[uid] = lang
            return lang

async def set_user_lang(uid, lang):
    lang_cache[uid] = lang
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("INSERT OR REPLACE INTO users_settings (user_id, lang) VALUES (?, ?)", (uid, lang))
        await db.commit()

async def get_wallet_balance(uid):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT balance FROM wallets WHERE user_id=?", (uid,)) as cur:
            row = await cur.fetchone()
            return row[0] if row else 0.0

async def update_wallet(uid, amount, tx_type, desc):
    async with aiosqlite.connect(DB_NAME) as db:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        await db.execute("INSERT OR IGNORE INTO wallets (user_id, balance, total_deposited, created_date) VALUES (?, 0, 0, ?)", (uid, now_str))
        await db.execute("UPDATE wallets SET balance = balance + ? WHERE user_id = ?", (amount, uid))
        if amount > 0:
            await db.execute("UPDATE wallets SET total_deposited = total_deposited + ? WHERE user_id = ?", (amount, uid))

        async with db.execute("SELECT balance FROM wallets WHERE user_id=?", (uid,)) as cur:
            new_bal = (await cur.fetchone())[0]

        await db.execute('''INSERT INTO wallet_transactions 
            (user_id, type, amount, balance_after, description, date) 
            VALUES (?, ?, ?, ?, ?, ?)''', (uid, tx_type, amount, new_bal, desc, now_str))
        await db.commit()
        return new_bal

async def get_payment_details_text(amount):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT network_name, address, binance_id FROM payment_networks WHERE is_active=1") as cur:
            nets = await cur.fetchall()

    text = f"<blockquote>💳 <b>بوابة الدفع الشاملة لمتجر Aura eSIM</b>\n💰 <b>المبلغ المطلوب تحويله:</b> <code>${amount:.2f}</code></blockquote>\n\n"
    text += "<blockquote>⧺︰ <b>إليك كافة عناوين ومعرفات الدفع المتاحة حالياً للتحويل:</b></blockquote>\n\n"
    for idx, (name, addr, b_id) in enumerate(nets, 1):
        text += f"<b>{idx}. {name}</b>\n"
        if b_id:
            text += f"• <code>ID / Pay ID:</code> <code>{b_id}</code>\n"
        if addr:
            text += f"• <code>Address:</code> <code>{addr}</code>\n"
        text += "───────────────────\n"
    text += "\n> ⧺︰ <b>قم بالتحويل عبر إحدى الطرق أعلاه، ثم اضغط على زر التحقق أدناه لتأكيد طلبك.</b>"
    return text

async def build_main_menu(uid):
    lang = await get_user_lang(uid)
    t = LANGS.get(lang, LANGS['ar'])
    bal = await get_wallet_balance(uid)

    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT id FROM dealer_api_keys WHERE user_id=?", (uid,)) as cur:
            has_api = (await cur.fetchone()) is not None

    btn = [
        [Button.inline(t['btn_personal'], b'personal_section')],
        [Button.inline(t['btn_dealer'], b'dealer_section')],
    ]
    if not has_api:
        btn.append([Button.inline(t['btn_dealer_api'], b'buy_api_sub_menu')])

    btn.extend([
        [Button.inline(t['btn_cart'], b'view_cart'), Button.inline(f"{t['btn_wallet']} : ${bal:.2f}", b'wallet')],
        [Button.inline(t['btn_orders'], b'my_orders'), Button.inline(t['btn_support'], b'support_ticket')],
        [Button.inline(t['btn_lang'], b'change_language')]
    ])
    if await is_admin(uid):
        btn.append([Button.inline(t['btn_admin'], b'admin_panel')])

    return t['welcome'], btn

# ==========================================
# 6. معالجات الأحداث والأزرار
# ==========================================
@client.on(events.NewMessage(pattern='/start'))
async def on_start(event):
    uid = event.sender_id
    if await is_banned(uid): return

    now = time.time()
    if uid in user_rate_limits and now - user_rate_limits[uid] < 0.6:
        return
    user_rate_limits[uid] = now

    # إشعار الدخول للمطور
    try:
        u = await event.sender
        uname = f"@{u.username}" if u and u.username else "بدون معرف"
        fname = u.first_name if u else "مستخدم"
        notif = f"🚨 <b>دخول مستخدم جديد للبوت!</b>\n\n• الاسم: {fname}\n• اليوزر: {uname}\n• الآيدي: <code>{uid}</code>\n• الوقت: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        await client.send_message(DEV_ID, notif, parse_mode='html')
    except: pass

    # نظام الإحالة (Referral)
    args = event.text.split()
    if len(args) > 1 and args[1].startswith('ref'):
        try:
            ref_id = int(args[1].replace('ref', ''))
            if ref_id != uid:
                async with aiosqlite.connect(DB_NAME) as db:
                    async with db.execute("SELECT referred_by FROM users_settings WHERE user_id=?", (uid,)) as cur:
                        existing = await cur.fetchone()
                    if not existing or not existing[0]:
                        await db.execute("INSERT OR REPLACE INTO users_settings (user_id, referred_by) VALUES (?, ?)", (uid, ref_id))
                        await db.commit()
        except: pass

    text, btn = await build_main_menu(uid)
    await event.reply(text, buttons=btn, parse_mode='html')

@client.on(events.CallbackQuery)
async def on_callback(event):
    uid = event.sender_id
    if await is_banned(uid): return

    now = time.time()
    if uid in user_rate_limits and now - user_rate_limits[uid] < 0.5:
        return
    user_rate_limits[uid] = now

    data = event.data.decode()
    lang = await get_user_lang(uid)
    t = LANGS.get(lang, LANGS['ar'])

    # ------------------ الملاحة واللغات ------------------
    if data == 'main':
        text, btn = await build_main_menu(uid)
        await event.edit(text, buttons=btn, parse_mode='html')

    elif data == 'change_language':
        btn = [
            [Button.inline("🇸🇦 العربية", b'set_lang_ar'), Button.inline("🇬🇧 English", b'set_lang_en')],
            [Button.inline(t['back'], b'main')]
        ]
        await event.edit("<blockquote>⧺︰ <b>اختر لغتك / Select language:</b></blockquote>", buttons=btn, parse_mode='html')

    elif data.startswith('set_lang_'):
        new_lang = data.split('_')[2]
        await set_user_lang(uid, new_lang)
        text, btn = await build_main_menu(uid)
        await event.edit(text, buttons=btn, parse_mode='html')

    # ------------------ قسم الأفراد ------------------
    elif data == 'personal_section':
        btn = [
            [Button.inline(t['btn_vodafone'], b'cat_vodafone')],
            [Button.inline(t['btn_holafly'], b'cat_holafly')],
            [Button.inline(t['btn_maya'], b'cat_maya')],
            [Button.inline(t['back'], b'main')]
        ]
        await event.edit(f"<blockquote>⧺︰ <b>{t['btn_personal']}</b></blockquote>", buttons=btn, parse_mode='html')

    elif data in ['cat_vodafone', 'cat_holafly', 'cat_maya']:
        cat = data.replace('cat_', '')
        async with aiosqlite.connect(DB_NAME) as db:
            async with db.execute("SELECT id, name, price_usd, months, minutes FROM esims WHERE category=? AND is_dealer=0 ORDER BY months ASC", (cat,)) as cur:
                plans = await cur.fetchall()

        btn = []
        for pid, name, price, m, mins in plans:
            m_label = 'شهر' if lang == 'ar' else 'M'
            btn.append([Button.inline(f"{name} ({m} {m_label}) - ${price:.0f}", f'show_plan_{pid}'.encode())])
        btn.append([Button.inline(t['back'], b'personal_section')])

        policy = WARRANTY_POLICY_TEXT.get(lang, WARRANTY_POLICY_TEXT['ar'])
        title_map = {'vodafone': t['btn_vodafone'], 'holafly': t['btn_holafly'], 'maya': t['btn_maya']}
        await event.edit(f"<blockquote>⧺︰ <b>{title_map[cat]}</b></blockquote>\n\n{policy}\n\n> ⧺︰ <b>اختر المدة المناسبة لك:</b>", buttons=btn, parse_mode='html')

    elif data.startswith('show_plan_'):
        pid = int(data.split('_')[2])
        async with aiosqlite.connect(DB_NAME) as db:
            async with db.execute("SELECT id, name, price_usd, minutes, months, stock, description, category FROM esims WHERE id=?", (pid,)) as cur:
                plan = await cur.fetchone()

        if not plan: return
        esim_id, name, price, mins, months, stock, desc, cat = plan
        set_session(uid, f'checkout_{uid}', {'esim_id': esim_id, 'price': price, 'name': name, 'qty': 1, 'is_dealer': 0})

        info = f"""<blockquote>⧺︰ <b>تفاصيل الباقة: {name}</b>
⧺︰ <b>المدة الزمنية:</b> <code>{months} شهر</code>
⧺︰ <b>السعر:</b> <code>${price:.2f}</code>
⧺︰ <b>المواصفات:</b> {desc}
⧺︰ <b>المخزون المتوفر:</b> <code>{stock} قطعة</code>
⧺︰ <b>كود التفعيل:</b> تفعيل فوري موحد (LPA) أو باركود</blockquote>"""

        btn = [
            [Button.inline(f"⚡ شراء مباشر من المحفظة (${price:.2f})", f'pay_wallet_{pid}'.encode())],
            [Button.inline("💳 الدفع عبر العملات الرقمية", f'pay_crypto_{pid}'.encode())],
            [Button.inline(t['add_to_cart'], f'add_to_cart_{pid}'.encode())],
            [Button.inline(t['back'], f'cat_{cat}'.encode())]
        ]
        await event.edit(info, buttons=btn, parse_mode='html')

    # ------------------ الشراء الفوري والمحفظة ------------------
    elif data.startswith('pay_wallet_'):
        pid = int(data.split('_')[2])
        sess = get_session(uid, f'checkout_{uid}')
        if not sess or sess['esim_id'] != pid:
            return await event.answer("انتهت الجلسة، أعد المحاولة", alert=True)

        price = sess['price']
        qty = sess['qty']
        name = sess['name']

        if uid not in wallet_locks:
            wallet_locks[uid] = asyncio.Lock()

        async with wallet_locks[uid]:
            bal = await get_wallet_balance(uid)
            if bal < price:
                btn = [
                    [Button.inline(t['charge_wallet_btn'], b'charge_wallet')],
                    [Button.inline(t['back'], b'main')]
                ]
                return await event.edit(f"{t['insufficient_balance']}\n<blockquote>رصيدك الحالي: <code>${bal:.2f}</code> | المطلوب: <code>${price:.2f}</code></blockquote>", buttons=btn, parse_mode='html')

            order_id = f"AURA{secrets.token_hex(4).upper()}"
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

            async with aiosqlite.connect(DB_NAME) as db:
                await db.execute('''INSERT INTO orders 
                    (order_id, user_id, esim_id, quantity, price_usd, total_usd, lpa_code, status, is_dealer, created_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 'paid', ?, ?)''',
                    (order_id, uid, pid, qty, price/qty, price, DEFAULT_LPA, sess['is_dealer'], now_str))
                await db.execute("UPDATE esims SET stock = stock - ? WHERE id=?", (qty, pid))
                await db.commit()

            await update_wallet(uid, -price, 'purchase', f"شراء {qty}x {name}")

        clear_session(uid, f'checkout_{uid}')

        success_msg = f"""<blockquote>🎉 <b>تم الشراء بنجاح تام!</b>
• <b>معرف الطلب:</b> <code>{order_id}</code>
• <b>الباقة:</b> {name}
• <b>المبلغ المخصوم:</b> <code>${price:.2f}</code>

• <b>كود التفعيل الفوري (LPA):</b>
<code>{DEFAULT_LPA}</code>

• <b>أو امسح الباركود المرفق لتفعيل الشريحة مباشرة.</b></blockquote>"""

        await event.reply(success_msg, file=DEFAULT_BARCODE, parse_mode='html')
        text, btn = await build_main_menu(uid)
        await event.respond("الرئيسية:", buttons=btn)

    elif data.startswith('pay_crypto_'):
        pid = int(data.split('_')[2])
        sess = get_session(uid, f'checkout_{uid}')
        if not sess: return await event.answer("انتهت الجلسة", alert=True)

        price = sess['price']
        set_session(uid, f'charging_amount_{uid}', price)
        details = await get_payment_details_text(price)
        btn = [
            [Button.inline(t['btn_verify_now'], b'verify_payment_menu')],
            [Button.inline(t['back'], f'show_plan_{pid}'.encode())]
        ]
        await event.edit(details, buttons=btn, parse_mode='html')

    # ------------------ سلة المشتريات ------------------
    elif data.startswith('add_to_cart_'):
        pid = int(data.split('_')[3])
        async with aiosqlite.connect(DB_NAME) as db:
            async with db.execute("SELECT price_usd FROM esims WHERE id=?", (pid,)) as cur:
                row = await cur.fetchone()
            if row:
                await db.execute("INSERT INTO cart (user_id, esim_id, scope, price) VALUES (?, ?, 'Global', ?)", (uid, pid, row[0]))
                await db.commit()
        await event.answer("تمت الإضافة إلى سلة المشتريات بنجاح!", alert=True)

    elif data == 'view_cart':
        async with aiosqlite.connect(DB_NAME) as db:
            async with db.execute('''SELECT c.id, e.name, c.price FROM cart c 
                                     JOIN esims e ON c.esim_id=e.id WHERE c.user_id=?''', (uid,)) as cur:
                items = await cur.fetchall()

        if not items:
            return await event.edit("<blockquote>🛒 <b>سلة المشتريات فارغة تماماً.</b></blockquote>", buttons=[[Button.inline(t['back'], b'main')]], parse_mode='html')

        total = sum(i[2] for i in items)
        cart_txt = "<blockquote>🛒 <b>محتويات سلة المشتريات الخاصة بك:</b></blockquote>\n\n"
        btn = []
        for cid, name, pr in items:
            cart_txt += f"• <b>{name}</b> - <code>${pr:.2f}</code>\n"
            btn.append([Button.inline(f"❌ حذف: {name}", f"cart_del_{cid}".encode())])

        cart_txt += f"\n> ⧺︰ <b>الإجمالي المطلوب:</b> <code>${total:.2f}</code>"
        btn.append([Button.inline(f"💳 دفع السلة من المحفظة (${total:.2f})", b'cart_pay_all')])
        btn.append([Button.inline(t['back'], b'main')])
        await event.edit(cart_txt, buttons=btn, parse_mode='html')

    elif data.startswith('cart_del_'):
        cid = int(data.split('_')[2])
        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute("DELETE FROM cart WHERE id=? AND user_id=?", (cid, uid))
            await db.commit()
        await on_callback(event)

    elif data == 'cart_pay_all':
        async with aiosqlite.connect(DB_NAME) as db:
            async with db.execute("SELECT c.esim_id, c.price, e.name FROM cart c JOIN esims e ON c.esim_id=e.id WHERE c.user_id=?", (uid,)) as cur:
                items = await cur.fetchall()

        if not items: return await event.answer("السلة فارغة", alert=True)
        total = sum(i[1] for i in items)

        if uid not in wallet_locks:
            wallet_locks[uid] = asyncio.Lock()

        async with wallet_locks[uid]:
            bal = await get_wallet_balance(uid)
            if bal < total:
                return await event.answer(t['insufficient_balance'], alert=True)

            order_id = f"CART{secrets.token_hex(4).upper()}"
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

            async with aiosqlite.connect(DB_NAME) as db:
                for eid, pr, nm in items:
                    await db.execute('''INSERT INTO orders 
                        (order_id, user_id, esim_id, quantity, price_usd, total_usd, lpa_code, status, is_dealer, created_date)
                        VALUES (?, ?, ?, 1, ?, ?, ?, 'paid', 0, ?)''',
                        (f"{order_id}_{eid}", uid, eid, pr, pr, DEFAULT_LPA, now_str))
                    await db.execute("UPDATE esims SET stock = stock - 1 WHERE id=?", (eid,))
                await db.execute("DELETE FROM cart WHERE user_id=?", (uid,))
                await db.commit()

            await update_wallet(uid, -total, 'purchase', f"شراء سلة مشتريات {order_id}")

        await event.reply(f"<blockquote>🎉 <b>تم دفع السلة بنجاح ({len(items)} باقات)!</b>\nكود التفعيل الموحد (LPA):\n<code>{DEFAULT_LPA}</code></blockquote>", file=DEFAULT_BARCODE, parse_mode='html')
        text, btn = await build_main_menu(uid)
        await event.respond("الرئيسية:", buttons=btn)

    # ------------------ قسم التجار والموزعين ------------------
    elif data == 'dealer_section':
        btn = [
            [Button.inline(t['btn_dealer_vf'], b'dealer_list_vf')],
            [Button.inline(t['btn_dealer_hf'], b'dealer_list_hf')],
            [Button.inline(t['btn_dealer_maya'], b'dealer_list_maya')],
            [Button.inline(t['btn_dealer_api'], b'buy_api_sub_menu')],
            [Button.inline(t['back'], b'main')]
        ]
        await event.edit(f"<blockquote>⧺︰ <b>{t['dealer_title']}</b></blockquote>", buttons=btn, parse_mode='html')

    elif data.startswith('dealer_list_'):
        cat_key = "dealer_" + data.split('_')[2]
        async with aiosqlite.connect(DB_NAME) as db:
            async with db.execute("SELECT id, name, price_usd, months FROM esims WHERE category=? ORDER BY months ASC", (cat_key,)) as cur:
                plans = await cur.fetchall()

        async with aiosqlite.connect(DB_NAME) as db:
            async with db.execute("SELECT id FROM dealer_api_keys WHERE user_id=?", (uid,)) as cur:
                has_api = (await cur.fetchone()) is not None

        discount = 0.5 if has_api else 1.0
        btn = []
        for pid, name, price, m in plans:
            final_p = price * discount
            btn.append([Button.inline(f"{name} (${final_p:.0f})", f'show_plan_{pid}'.encode())])
        btn.append([Button.inline(t['back'], b'dealer_section')])
        await event.edit("<blockquote>💼 <b>باقات الجملة 10 شرائح (خصم 50% لمشتركي الـ API):</b></blockquote>", buttons=btn, parse_mode='html')

    elif data == 'buy_api_sub_menu':
        async with aiosqlite.connect(DB_NAME) as db:
            async with db.execute("SELECT api_key FROM dealer_api_keys WHERE user_id=?", (uid,)) as cur:
                row = await cur.fetchone()

        if row:
            return await event.edit(f"<blockquote>🔌 <b>مفتاح API الخاص بك مفعّل مسبقاً:</b>\n<code>{row[0]}</code>\n\nتستفيد الآن من خصم 50% الدائم على كافة الباقات.</blockquote>", buttons=[[Button.inline(t['back'], b'dealer_section')]], parse_mode='html')

        btn = [
            [Button.inline("⚡ تفعيل API فوراً بـ $100 من المحفظة", b'confirm_buy_api')],
            [Button.inline(t['back'], b'dealer_section')]
        ]
        await event.edit("<blockquote>🔌 <b>اشتراك وتفعيل نظام الـ API للتجار:</b>\n\n• التكلفة: <b>$100</b> لمرة واحدة مدى الحياة.\n• المميزات: خصم 50% دائم على جميع الباقات وسحب الخدمات برمجياً.</blockquote>", buttons=btn, parse_mode='html')

    elif data == 'confirm_buy_api':
        if uid not in wallet_locks:
            wallet_locks[uid] = asyncio.Lock()

        async with wallet_locks[uid]:
            bal = await get_wallet_balance(uid)
            if bal < 100.0:
                return await event.answer(t['insufficient_balance'], alert=True)

            api_key = f"AURA_API_{secrets.token_hex(16).upper()}"
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
            async with aiosqlite.connect(DB_NAME) as db:
                await db.execute("INSERT OR REPLACE INTO dealer_api_keys (user_id, api_key, created_date) VALUES (?, ?, ?)", (uid, api_key, now_str))
                await db.commit()

            await update_wallet(uid, -100.0, 'api_subscription', "شراء وتفعيل نظام الـ API")

        await event.edit(f"<blockquote>🎉 <b>تم تفعيل مفتاح API الخاص بك بنجاح!</b>\n\n<code>{api_key}</code>\n\nتم تطبيق خصم 50% على حسابك.</blockquote>", buttons=[[Button.inline(t['back'], b'dealer_section')]], parse_mode='html')

    # ------------------ المحفظة والمعاملات ------------------
    elif data == 'wallet':
        bal = await get_wallet_balance(uid)
        bot_user = (await client.get_me()).username
        ref_link = f"https://t.me/{bot_user}?start=ref{uid}"
        text = f"{t['wallet_title']}\n\n<blockquote>⧺︰ <b>{t['current_balance']}:</b> <code>${bal:.2f}</code></blockquote>\n\n<blockquote>🔗 <b>رابط الإحالة الخاص بك:</b>\n<code>{ref_link}</code></blockquote>"
        btn = [
            [Button.inline(t['charge_wallet_btn'], b'charge_wallet')],
            [Button.inline(t['btn_transactions'], b'wallet_transactions')],
            [Button.inline(t['btn_verify_payment'], b'verify_payment_menu')],
            [Button.inline(t['back'], b'main')]
        ]
        await event.edit(text, buttons=btn, parse_mode='html')

    elif data == 'wallet_transactions':
        async with aiosqlite.connect(DB_NAME) as db:
            async with db.execute("SELECT type, amount, balance_after, description, date FROM wallet_transactions WHERE user_id=? ORDER BY id DESC LIMIT 8", (uid,)) as cur:
                txs = await cur.fetchall()

        if not txs:
            return await event.edit("<blockquote>📜 <b>لا توجد حركات مالية مسجلة في محفظتك حتى الآن.</b></blockquote>", buttons=[[Button.inline(t['back'], b'wallet')]], parse_mode='html')

        txt = "<blockquote>📜 <b>سجل آخر الحركات المالية في محفظتك:</b></blockquote>\n\n"
        for tp, amt, ba, desc, dt in txs:
            s = "+" if amt > 0 else ""
            txt += f"• <b>{desc}</b>\n  المبلغ: <code>{s}${amt:.2f}</code> | الرصيد بعد: <code>${ba:.2f}</code>\n  التاريخ: <code>{dt}</code>\n─────────────────\n"
        await event.edit(txt, buttons=[[Button.inline(t['back'], b'wallet')]], parse_mode='html')

    elif data == 'charge_wallet':
        set_session(uid, 'action', 'waiting_deposit_amount')
        await event.edit(t['charge_prompt'], buttons=[[Button.inline(t['back'], b'wallet')]], parse_mode='html')

    elif data == 'verify_payment_menu':
        set_session(uid, 'action', 'waiting_receipt')
        await event.edit(t['verify_prompt'], buttons=[[Button.inline(t['back'], b'wallet')]], parse_mode='html')

    elif data == 'support_ticket':
        set_session(uid, 'action', 'waiting_support')
        await event.edit(t['support_prompt'], buttons=[[Button.inline(t['back'], b'main')]], parse_mode='html')

    elif data == 'my_orders':
        async with aiosqlite.connect(DB_NAME) as db:
            async with db.execute('''SELECT o.order_id, e.name, o.quantity, o.total_usd, o.created_date 
                                     FROM orders o JOIN esims e ON o.esim_id=e.id 
                                     WHERE o.user_id=? ORDER BY o.created_date DESC LIMIT 6''', (uid,)) as cur:
                orders = await cur.fetchall()

        if not orders:
            return await event.edit(t['no_orders'], buttons=[[Button.inline(t['back'], b'main')]], parse_mode='html')

        txt = f"{t['my_orders_title']}\n\n"
        btn = []
        for oid, nm, q, tot, dt in orders:
            txt += f"• <b>{q}x {nm}</b> | <code>${tot:.2f}</code> ({dt})\n"
            btn.append([Button.inline(f"تفاصيل الطلب: {oid}", f"reload_{oid}".encode())])
        btn.append([Button.inline(t['back'], b'main')])
        await event.edit(txt, buttons=btn, parse_mode='html')

    elif data.startswith('reload_'):
        oid = data.replace('reload_', '')
        reloaded = f"<blockquote>⧺︰ <b>تفاصيل الطلب المكتمل:</b>\n• معرف الطلب: <code>{oid}</code>\n\n• كود LPA الافتراضي الموحد:\n<code>{DEFAULT_LPA}</code></blockquote>"
        await event.reply(reloaded, file=DEFAULT_BARCODE, parse_mode='html')

    # ==========================================
    # 7. لوحة تحكم الأدمن الشاملة (مع إدارة طرق الدفع)
    # ==========================================
    elif data == 'admin_panel' and await is_admin(uid):
        async with aiosqlite.connect(DB_NAME) as db:
            sales = (await (await db.execute("SELECT COUNT(*) FROM orders WHERE status='paid'")).fetchone())[0]
            revenue = (await (await db.execute("SELECT SUM(total_usd) FROM orders WHERE status='paid'")).fetchone())[0] or 0.0
            wallets = (await (await db.execute("SELECT SUM(balance) FROM wallets")).fetchone())[0] or 0.0
            users = (await (await db.execute("SELECT COUNT(*) FROM users_settings")).fetchone())[0]

        adm_txt = f"""{t['admin_panel_title']}

<blockquote>⧺︰ <b>إجمالي المستخدمين:</b> <code>{users}</code>
⧺︰ <b>الطلبات المكتملة:</b> <code>{sales}</code>
⧺︰ <b>صافي المبيعات:</b> <code>${revenue:.2f}</code>
⧺︰ <b>إجمالي أرصدة المحافظ:</b> <code>${wallets:.2f}</code></blockquote>"""

        btn = [
            [Button.inline("💳 إدارة طرق وشبكات الدفع", b'adm_manage_payments')],
            [Button.inline("📦 إدارة الباقات والأسعار", b'adm_manage_plans')],
            [Button.inline("💰 شحن رصيد", b'adm_add_bal'), Button.inline("📉 خصم رصيد", b'adm_sub_bal')],
            [Button.inline("🚫 حظر / فك حظر", b'adm_ban_user'), Button.inline("📢 إذاعة عامة", b'adm_broadcast')],
            [Button.inline(t['back'], b'main')]
        ]
        await event.edit(adm_txt, buttons=btn, parse_mode='html')

    # إدارة طرق الدفع بالكامل من البوت
    elif data == 'adm_manage_payments' and await is_admin(uid):
        async with aiosqlite.connect(DB_NAME) as db:
            async with db.execute("SELECT id, network_name, address, binance_id FROM payment_networks") as cur:
                nets = await cur.fetchall()

        txt = "<blockquote>💳 <b>إدارة طرق وعناوين الدفع:</b>\nاختر طريقة لتعديلها أو حذفها، أو أضف طريقة جديدة:</blockquote>\n\n"
        btn = []
        for nid, name, addr, bid in nets:
            val = bid if bid else addr[:15] + "..."
            btn.append([Button.inline(f"⚙️ {name} ({val})", f"edit_pay_{nid}".encode())])

        btn.append([Button.inline("➕ إضافة طريقة دفع جديدة", b'adm_add_payment_net')])
        btn.append([Button.inline(t['back'], b'admin_panel')])
        await event.edit(txt, buttons=btn, parse_mode='html')

    elif data == 'adm_add_payment_net' and await is_admin(uid):
        set_session(uid, 'action', 'adm_new_pay_flow')
        await event.edit("<blockquote>➕ <b>أرسل بيانات طريقة الدفع الجديدة بسطر واحد بالصيغة:</b>\n\n<code>اسم الشبكة | العنوان أو المحفظة | ID المنصة (اختياري)</code>\n\n<b>مثال 1:</b>\n<code>USDT (Arbitrum) | 0x334c55fe51757ac... | </code>\n<b>مثال 2:</b>\n<code>RedotPay ID | | 18274920</code></blockquote>", buttons=[[Button.inline(t['back'], b'adm_manage_payments')]], parse_mode='html')

    elif data.startswith('edit_pay_') and await is_admin(uid):
        nid = int(data.split('_')[2])
        async with aiosqlite.connect(DB_NAME) as db:
            async with db.execute("SELECT network_name, address, binance_id FROM payment_networks WHERE id=?", (nid,)) as cur:
                net = await cur.fetchone()

        if not net: return
        set_session(uid, 'target_pay_id', nid)
        info = f"""<blockquote>💳 <b>تعديل طريقة الدفع:</b>
• الاسم: <b>{net[0]}</b>
• العنوان: <code>{net[1]}</code>
• ID: <code>{net[2]}</code></blockquote>"""
        btn = [
            [Button.inline("تعديل العنوان", b'adm_change_pay_addr'), Button.inline("تعديل ID", b'adm_change_pay_id')],
            [Button.inline("🗑️ حذف هذه الطريقة نهائياً", b'adm_del_pay_confirm')],
            [Button.inline(t['back'], b'adm_manage_payments')]
        ]
        await event.edit(info, buttons=btn, parse_mode='html')

    elif data == 'adm_change_pay_addr' and await is_admin(uid):
        set_session(uid, 'action', 'adm_set_pay_addr')
        await event.edit("<blockquote>أرسل العنوان الجديد (Address):</blockquote>", buttons=[[Button.inline(t['back'], b'adm_manage_payments')]], parse_mode='html')

    elif data == 'adm_change_pay_id' and await is_admin(uid):
        set_session(uid, 'action', 'adm_set_pay_id')
        await event.edit("<blockquote>أرسل الـ ID الجديد (Pay ID):</blockquote>", buttons=[[Button.inline(t['back'], b'adm_manage_payments')]], parse_mode='html')

    elif data == 'adm_del_pay_confirm' and await is_admin(uid):
        nid = get_session(uid, 'target_pay_id')
        if nid:
            async with aiosqlite.connect(DB_NAME) as db:
                await db.execute("DELETE FROM payment_networks WHERE id=?", (nid,))
                await db.commit()
            await event.answer("تم حذف طريقة الدفع بنجاح", alert=True)
        await on_callback(event)

    # تعديل الباقات والمخزون
    elif data == 'adm_manage_plans' and await is_admin(uid):
        async with aiosqlite.connect(DB_NAME) as db:
            async with db.execute("SELECT id, name, price_usd, stock FROM esims LIMIT 15") as cur:
                plans = await cur.fetchall()

        btn = []
        for pid, name, pr, st in plans:
            btn.append([Button.inline(f"{name} | ${pr:.0f} | مخزون: {st}", f"adm_edit_plan_{pid}".encode())])
        btn.append([Button.inline(t['back'], b'admin_panel')])
        await event.edit("<blockquote>📦 <b>اختر باقة لتعديل سعرها أو مخزونها:</b></blockquote>", buttons=btn, parse_mode='html')

    elif data.startswith('adm_edit_plan_') and await is_admin(uid):
        pid = int(data.split('_')[3])
        set_session(uid, 'target_plan_id', pid)
        async with aiosqlite.connect(DB_NAME) as db:
            async with db.execute("SELECT name, price_usd, stock FROM esims WHERE id=?", (pid,)) as cur:
                row = await cur.fetchone()

        btn = [
            [Button.inline("تعديل السعر", b'adm_set_plan_price'), Button.inline("تعديل المخزون", b'adm_set_plan_stock')],
            [Button.inline(t['back'], b'adm_manage_plans')]
        ]
        await event.edit(f"<blockquote>الباقة: <b>{row[0]}</b>\n• السعر: <code>${row[1]:.2f}</code>\n• المخزون: <code>{row[2]}</code></blockquote>", buttons=btn, parse_mode='html')

    elif data == 'adm_set_plan_price' and await is_admin(uid):
        set_session(uid, 'action', 'adm_set_plan_price_val')
        await event.edit("<blockquote>أرسل السعر الجديد بالدولار:</blockquote>", buttons=[[Button.inline(t['back'], b'adm_manage_plans')]], parse_mode='html')

    elif data == 'adm_set_plan_stock' and await is_admin(uid):
        set_session(uid, 'action', 'adm_set_plan_stock_val')
        await event.edit("<blockquote>أرسل كمية المخزون الجديدة:</blockquote>", buttons=[[Button.inline(t['back'], b'adm_manage_plans')]], parse_mode='html')

    # الرصيد والحظر والإذاعة
    elif data == 'adm_add_bal' and await is_admin(uid):
        set_session(uid, 'action', 'adm_add_bal_flow')
        await event.edit("<blockquote>أرسل آيدي العميل ثم المبلغ (مثال: <code>123456789 50</code>):</blockquote>", buttons=[[Button.inline(t['back'], b'admin_panel')]], parse_mode='html')

    elif data == 'adm_sub_bal' and await is_admin(uid):
        set_session(uid, 'action', 'adm_sub_bal_flow')
        await event.edit("<blockquote>أرسل آيدي العميل ثم المبلغ المراد خصمه (مثال: <code>123456789 20</code>):</blockquote>", buttons=[[Button.inline(t['back'], b'admin_panel')]], parse_mode='html')

    elif data == 'adm_ban_user' and await is_admin(uid):
        set_session(uid, 'action', 'adm_ban_user_flow')
        await event.edit("<blockquote>أرسل آيدي المستخدم لتبديل حالة الحظر (حظر / فك حظر):</blockquote>", buttons=[[Button.inline(t['back'], b'admin_panel')]], parse_mode='html')

    elif data == 'adm_broadcast' and await is_admin(uid):
        set_session(uid, 'action', 'adm_broadcast_flow')
        await event.edit("<blockquote>📢 <b>أرسل الرسالة المراد إذاعتها لجميع المستخدمين:</b></blockquote>", buttons=[[Button.inline(t['back'], b'admin_panel')]], parse_mode='html')

    # قبول / رفض الشحن
    elif data.startswith('approve_dep_') and await is_admin(uid):
        dep_id = int(data.split('_')[2])
        async with aiosqlite.connect(DB_NAME) as db:
            async with db.execute("SELECT user_id, amount, status FROM deposit_requests WHERE id=?", (dep_id,)) as cur:
                row = await cur.fetchone()
                if not row or row[2] != 'pending':
                    return await event.answer("تمت معالجة الطلب مسبقاً!", alert=True)

                target_uid, amt, _ = row
                await db.execute("UPDATE deposit_requests SET status='approved' WHERE id=?", (dep_id,))
                await db.commit()

        await update_wallet(target_uid, amt, 'deposit', f"إيداع منصات مقبول #{dep_id}")
        try:
            await client.send_message(target_uid, f"<blockquote>✅ <b>تم قبول إيصال الدفع وإضافة ${amt:.2f} إلى محفظتك بنجاح!</b></blockquote>", parse_mode='html')
        except: pass
        await event.edit(f"<blockquote>✅ <b>تم قبول إيداع ${amt:.2f} وشحنها للمستخدم <code>{target_uid}</code>.</b></blockquote>", parse_mode='html')

    elif data.startswith('reject_dep_') and await is_admin(uid):
        dep_id = int(data.split('_')[2])
        async with aiosqlite.connect(DB_NAME) as db:
            async with db.execute("SELECT user_id, status FROM deposit_requests WHERE id=?", (dep_id,)) as cur:
                row = await cur.fetchone()
                if not row or row[1] != 'pending':
                    return await event.answer("تمت معالجة الطلب مسبقاً", alert=True)
                target_uid = row[0]
                await db.execute("UPDATE deposit_requests SET status='rejected' WHERE id=?", (dep_id,))
                await db.commit()

        try:
            await client.send_message(target_uid, "<blockquote>❌ <b>عذراً، تم رفض إيصال الدفع. يرجى مراجعة الدعم.</b></blockquote>", parse_mode='html')
        except: pass
        await event.edit(f"<blockquote>❌ <b>تم رفض الإيصال #{dep_id}.</b></blockquote>", parse_mode='html')

# ==========================================
# 8. معالجة النصوص والمدخلات
# ==========================================
@client.on(events.NewMessage)
async def on_message(event):
    uid = event.sender_id
    if await is_banned(uid) or event.text.startswith('/'): return

    action = get_session(uid, 'action')
    if not action: return

    text = event.text.strip() if event.text else ""

    if action == 'waiting_deposit_amount':
        try:
            amt = float(text)
            if amt < 20:
                return await event.reply("<blockquote>⚠️ <b>الحد الأدنى للشحن هو $20.</b></blockquote>", parse_mode='html')
            set_session(uid, f'charging_amount_{uid}', amt)
            clear_session(uid, 'action')
            details = await get_payment_details_text(amt)
            btn = [
                [Button.inline("التحقق من الدفع وإرسال الإيصال الآن", b'verify_payment_menu')],
                [Button.inline("رجوع", b'wallet')]
            ]
            await event.reply(details, buttons=btn, parse_mode='html')
        except ValueError:
            await event.reply("<blockquote>⚠️ <b>يرجى إدخال رقم صحيح وموجب.</b></blockquote>", parse_mode='html')

    elif action == 'waiting_receipt':
        amt = get_session(uid, f'charging_amount_{uid}') or 20.0
        clear_session(uid, 'action')
        clear_session(uid, f'charging_amount_{uid}')

        tx_info = text if text else "صورة إيصال مرفقة"
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

        async with aiosqlite.connect(DB_NAME) as db:
            cur = await db.execute("INSERT INTO deposit_requests (user_id, amount, tx_data, date) VALUES (?, ?, ?, ?)",
                                   (uid, amt, tx_info, now_str))
            dep_id = cur.lastrowid
            await db.commit()

        await event.reply("<blockquote>✅ <b>تم استلام الإيصال بنجاح وجاري مراجعته من قبل الإدارة فوراً.</b></blockquote>", parse_mode='html')

        adm_msg = f"""<blockquote>🚨 <b>طلب تحقق من دفع جديد (#{dep_id})!</b>
• <b>العميل:</b> <code>{uid}</code>
• <b>المبلغ المطلوب:</b> <code>${amt:.2f}</code>
• <b>البيان:</b> {tx_info}</blockquote>"""

        adm_btns = [
            [Button.inline("✅ قبول وشحن الرصيد", f"approve_dep_{dep_id}".encode()),
             Button.inline("❌ رفض الإيصال", f"reject_dep_{dep_id}".encode())]
        ]
        if event.media:
            await client.send_file(DEV_ID, event.media, caption=adm_msg, buttons=adm_btns, parse_mode='html')
        else:
            await client.send_message(DEV_ID, adm_msg, buttons=adm_btns, parse_mode='html')

    elif action == 'waiting_support':
        clear_session(uid, 'action')
        await event.reply("<blockquote>✅ <b>تم إرسال تذكرتك بنجاح، سنرد عليك في أقرب وقت.</b></blockquote>", parse_mode='html')
        await client.send_message(DEV_ID, f"<blockquote>💬 <b>تذكرة دعم من المستخدم:</b> <code>{uid}</code>\n\n{text}</blockquote>", parse_mode='html')

    # مدخلات إدارة طرق الدفع من الأدمن
    elif action == 'adm_new_pay_flow' and await is_admin(uid):
        clear_session(uid, 'action')
        try:
            parts = [x.strip() for x in text.split('|')]
            name = parts[0]
            addr = parts[1] if len(parts) > 1 else ""
            bid = parts[2] if len(parts) > 2 else ""
            k = f"net_{secrets.token_hex(4)}"
            async with aiosqlite.connect(DB_NAME) as db:
                await db.execute("INSERT INTO payment_networks (network_key, network_name, address, binance_id) VALUES (?, ?, ?, ?)", (k, name, addr, bid))
                await db.commit()
            await event.reply(f"<blockquote>✅ <b>تمت إضافة طريقة الدفع الجديدة ({name}) بنجاح!</b></blockquote>", parse_mode='html')
        except Exception as e:
            await event.reply(f"❌ خطأ في الإضافة: {e}")

    elif action == 'adm_set_pay_addr' and await is_admin(uid):
        clear_session(uid, 'action')
        nid = get_session(uid, 'target_pay_id')
        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute("UPDATE payment_networks SET address=? WHERE id=?", (text, nid))
            await db.commit()
        await event.reply("<blockquote>✅ <b>تم تحديث العنوان بنجاح!</b></blockquote>", parse_mode='html')

    elif action == 'adm_set_pay_id' and await is_admin(uid):
        clear_session(uid, 'action')
        nid = get_session(uid, 'target_pay_id')
        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute("UPDATE payment_networks SET binance_id=? WHERE id=?", (text, nid))
            await db.commit()
        await event.reply("<blockquote>✅ <b>تم تحديث الـ ID بنجاح!</b></blockquote>", parse_mode='html')

    elif action == 'adm_set_plan_price_val' and await is_admin(uid):
        clear_session(uid, 'action')
        pid = get_session(uid, 'target_plan_id')
        try:
            p = float(text)
            async with aiosqlite.connect(DB_NAME) as db:
                await db.execute("UPDATE esims SET price_usd=? WHERE id=?", (p, pid))
                await db.commit()
            await event.reply(f"<blockquote>✅ <b>تم تحديث السعر إلى ${p:.2f}</b></blockquote>", parse_mode='html')
        except: await event.reply("رقم غير صحيح")

    elif action == 'adm_set_plan_stock_val' and await is_admin(uid):
        clear_session(uid, 'action')
        pid = get_session(uid, 'target_plan_id')
        try:
            s = int(text)
            async with aiosqlite.connect(DB_NAME) as db:
                await db.execute("UPDATE esims SET stock=? WHERE id=?", (s, pid))
                await db.commit()
            await event.reply(f"<blockquote>✅ <b>تم تحديث المخزون إلى {s} قطع</b></blockquote>", parse_mode='html')
        except: await event.reply("رقم غير صحيح")

    elif action == 'adm_add_bal_flow' and await is_admin(uid):
        clear_session(uid, 'action')
        try:
            target_uid, amt = text.split()
            await update_wallet(int(target_uid), float(amt), 'admin_deposit', "شحن يدوي بواسطة الإدارة")
            await event.reply(f"<blockquote>✅ <b>تمت إضافة ${float(amt):.2f} إلى محفظة <code>{target_uid}</code>.</b></blockquote>", parse_mode='html')
            try:
                await client.send_message(int(target_uid), f"<blockquote>💰 <b>تمت إضافة ${float(amt):.2f} إلى محفظتك من قبل الإدارة!</b></blockquote>", parse_mode='html')
            except: pass
        except: await event.reply("الصيغة: ID AMOUNT")

    elif action == 'adm_sub_bal_flow' and await is_admin(uid):
        clear_session(uid, 'action')
        try:
            target_uid, amt = text.split()
            await update_wallet(int(target_uid), -float(amt), 'admin_withdraw', "خصم يدوي بواسطة الإدارة")
            await event.reply(f"<blockquote>✅ <b>تم خصم ${float(amt):.2f} من محفظة <code>{target_uid}</code>.</b></blockquote>", parse_mode='html')
        except: await event.reply("الصيغة: ID AMOUNT")

    elif action == 'adm_ban_user_flow' and await is_admin(uid):
        clear_session(uid, 'action')
        try:
            target_uid = int(text)
            if target_uid == DEV_ID: return
            if await is_banned(target_uid):
                async with aiosqlite.connect(DB_NAME) as db:
                    await db.execute("DELETE FROM bans WHERE user_id=?", (target_uid,))
                    await db.commit()
                ban_cache.pop(target_uid, None)
                await event.reply(f"<blockquote>✅ <b>تم فك حظر المستخدم <code>{target_uid}</code>.</b></blockquote>", parse_mode='html')
            else:
                async with aiosqlite.connect(DB_NAME) as db:
                    await db.execute("INSERT OR REPLACE INTO bans (user_id) VALUES (?)", (target_uid,))
                    await db.commit()
                ban_cache[target_uid] = True
                await event.reply(f"<blockquote>🚫 <b>تم حظر المستخدم <code>{target_uid}</code> بنجاح.</b></blockquote>", parse_mode='html')
        except: await event.reply("آيدي غير صالح")

    elif action == 'adm_broadcast_flow' and await is_admin(uid):
        clear_session(uid, 'action')
        status = await event.reply("<blockquote>⏳ <b>جاري إرسال الإذاعة بأمان...</b></blockquote>", parse_mode='html')
        async with aiosqlite.connect(DB_NAME) as db:
            async with db.execute("SELECT user_id FROM users_settings") as cur:
                users = await cur.fetchall()

        succ, fail = 0, 0
        for (u,) in users:
            try:
                await client.send_message(u, f"<blockquote>📢 <b>إعلان رسمي من Aura eSIM:</b>\n\n{text}</blockquote>", parse_mode='html')
                succ += 1
                await asyncio.sleep(0.05)
            except errors.FloodWaitError as e:
                await asyncio.sleep(e.seconds)
                try:
                    await client.send_message(u, f"<blockquote>📢 <b>إعلان رسمي من Aura eSIM:</b>\n\n{text}</blockquote>", parse_mode='html')
                    succ += 1
                except: fail += 1
            except: fail += 1

        await status.edit(f"<blockquote>📢 <b>اكتملت الإذاعة:</b>\n• نجاح: <code>{succ}</code>\n• فشل: <code>{fail}</code></blockquote>", parse_mode='html')

# ==========================================
# 9. التشغيل
# ==========================================
async def main():
    await init_db()
    await client.start(bot_token=BOT_TOKEN)
    logger.info("Aura eSIM Elite Bot fully upgraded with dynamic admin payment controls & unified LPA.")
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
