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

# ==========================================================
# 1. إعداد السجلات والبيئة
# ==========================================================
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

# الشريحة الموحدة لجميع المبيعات
DEFAULT_LPA = "LPA:1$hfy.prod.ondemandconnectivity.com$FA1BEB0FB081104C79BAD7E29424A4101C6BD12873E8733BD856AFF7A7B6DECC"
DEFAULT_BARCODE = f"https://api.qrserver.com/v1/create-qr-code/?data={DEFAULT_LPA}&size=500x500"

# ==========================================================
# 2. نصوص اللغات والتصميم الفاخر
# ==========================================================
LANGS = {
    'ar': {
        'welcome': """<blockquote>⧺︰ <b>البوابـة الرقميـة الفـاخرة | Aura eSIM Elite</b></blockquote>
<blockquote>⧺︰ <b>الحل الموثوق للاتصالات والإنترنت عالي السرعة بدون حدود</b></blockquote>
<blockquote>⧺︰ <b>تفعيل فوري مباشر عبر QR Code أو كود LPA المعتمد بضغطة واحدة</b></blockquote>
<blockquote>⧺︰ <b>ضمان تشغيل متواصل، دعم متخصص، وأمان مالي متكامل</b></blockquote>""",
        'btn_personal': "🌐 قسم الأفراد (باقات الاستخدام الشخصي)",
        'btn_dealer': "💼 قسم الموزعين والتجار (عروض الجملة)",
        'btn_wallet': "💳 المحفظة الرقمية",
        'btn_orders': "📋 سجل طلباتي",
        'btn_support': "💬 الدعم الفني",
        'btn_admin': "⚙️ غرفة التحكم الإدارية",
        'btn_lang': "🌍 اللغة / Language",
        'back': "🔙 رجوع",
        'main_menu': "🏠 القائمة الرئيسية",
        'insufficient_balance': "<blockquote>⚠️ <b>عذراً، رصيد محفظتك غير كافٍ لإتمام عملية الشراء.</b>\nيرجى شحن محفظتك للمتابعة.</blockquote>",
        'wallet_title': "<blockquote>💳 <b>المحفظة الرقمية الموحدة لـ Aura eSIM</b></blockquote>",
        'current_balance': "الرصيد المتاح",
        'charge_wallet_btn': "➕ شحن المحفظة (طرق الدفع)",
        'charge_prompt': "<blockquote>💵 <b>أرسل الآن المبلغ المراد شحنه بالدولار (الحد الأدنى $20):</b></blockquote>",
        'min_charge_err': "<blockquote>⚠️ <b>الحد الأدنى المقبول لعملية الشحن هو $20</b></blockquote>",
        'invalid_number_err': "<blockquote>⚠️ <b>يرجى كتابة رقم صحيح وموجب حصراً.</b></blockquote>",
        'verify_prompt': "<blockquote>🧾 <b>أرسل الآن صورة الإيصال أو معرف المعاملة (TxID):</b></blockquote>",
        'verify_sent': "<blockquote>✅ <b>تم استلام الإيصال بنجاح وجارٍ التحقق منه من قبل الإدارة فوراً.</b></blockquote>",
        'support_prompt': "<blockquote>💬 <b>اكتب استفسارك أو مشكلتك وسيتم تحويلها لفريق الدعم المباشر:</b></blockquote>",
        'support_sent': "<blockquote>✅ <b>تم فتح تذكرة الدعم بنجاح وسيتم إشعارك بالرد قريباً.</b></blockquote>",
        'out_of_stock': "<blockquote>⚠️ <b>عذراً، هذه الباقة نفدت كميتها من المخزون حالياً.</b></blockquote>"
    },
    'en': {
        'welcome': """<blockquote>⧺︰ <b>Aura eSIM Elite | Luxury Digital Gateway</b></blockquote>
<blockquote>⧺︰ <b>Next-gen global connectivity with unlimited speeds</b></blockquote>
<blockquote>⧺︰ <b>Instant activation via QR Code or authorized LPA setup</b></blockquote>
<blockquote>⧺︰ <b>Continuous uptime, dedicated support, and bulletproof security</b></blockquote>""",
        'btn_personal': "🌐 Personal Data Plans",
        'btn_dealer': "💼 Wholesale & Dealers",
        'btn_wallet': "💳 My Wallet",
        'btn_orders': "📋 Order History",
        'btn_support': "💬 Support",
        'btn_admin': "⚙️ Executive Panel",
        'btn_lang': "🌍 Language / اللغة",
        'back': "🔙 Back",
        'main_menu': "🏠 Main Menu",
        'insufficient_balance': "<blockquote>⚠️ <b>Insufficient wallet balance to complete this transaction.</b>\nPlease top up your wallet.</blockquote>",
        'wallet_title': "<blockquote>💳 <b>Aura eSIM Digital Wallet</b></blockquote>",
        'current_balance': "Current Balance",
        'charge_wallet_btn': "➕ Deposit Funds",
        'charge_prompt': "<blockquote>💵 <b>Enter amount in USD (Minimum $20):</b></blockquote>",
        'min_charge_err': "<blockquote>⚠️ <b>Minimum deposit amount is $20</b></blockquote>",
        'invalid_number_err': "<blockquote>⚠️ <b>Please enter a valid positive number.</b></blockquote>",
        'verify_prompt': "<blockquote>🧾 <b>Send receipt screenshot or Transaction ID (TxID):</b></blockquote>",
        'verify_sent': "<blockquote>✅ <b>Receipt received and pending administrative approval.</b></blockquote>",
        'support_prompt': "<blockquote>💬 <b>Send your inquiry and our support team will respond shortly:</b></blockquote>",
        'support_sent': "<blockquote>✅ <b>Support ticket submitted successfully.</b></blockquote>",
        'out_of_stock': "<blockquote>⚠️ <b>This package is currently out of stock.</b></blockquote>"
    }
}

PAYMENT_ADDRESSES = """<blockquote>⧺︰ <b>عناوين ومحافظ الدفع المعتمدة:</b>
• <b>Binance Pay ID:</b> <code>159349409</code>
• <b>USDT (TRC20):</b> <code>TM5SqP85qKa9pait6DkqCPDcr3hDNJmDGd</code>
• <b>USDT (BEP20 / BSC):</b> <code>0x334c55fe51757ac79a3d290523298bd5d327df64</code>
• <b>Litecoin (LTC):</b> <code>LRbz7QkKmQ9ASjkAuJSD5eYbziApzidZ9b</code></blockquote>"""

client = TelegramClient('esim_market', API_ID, API_HASH)

# ==========================================================
# 3. إدارة الذاكرة المؤقتة والحماية من الهجمات (Anti-Flood & Cache)
# ==========================================================
user_states = {}
lang_cache = {}
admin_cache = {}
ban_cache = {}
wallet_locks = {}
user_rate_limits = {}

def set_session(uid, key, value, duration_minutes=30):
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

# ==========================================================
# 4. إدارة قاعدة البيانات وقفل العمليات المتزامنة
# ==========================================================
async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("PRAGMA journal_mode=WAL;")
        await db.execute("PRAGMA synchronous=NORMAL;")

        # جدول الأقسام
        await db.execute('''CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            slug TEXT UNIQUE,
            name_ar TEXT,
            name_en TEXT,
            is_active INTEGER DEFAULT 1
        )''')

        # جدول الباقات
        await db.execute('''CREATE TABLE IF NOT EXISTS packages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_slug TEXT,
            name_ar TEXT,
            name_en TEXT,
            price_usd REAL,
            stock INTEGER DEFAULT 100,
            duration_months INTEGER DEFAULT 1,
            is_active INTEGER DEFAULT 1
        )''')

        # المحافظ
        await db.execute('''CREATE TABLE IF NOT EXISTS wallets (
            user_id INTEGER PRIMARY KEY,
            balance REAL DEFAULT 0,
            total_deposited REAL DEFAULT 0
        )''')

        # العمليات المالية
        await db.execute('''CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            type TEXT,
            amount REAL,
            balance_after REAL,
            description TEXT,
            created_at TEXT
        )''')

        # طلبات الشحن
        await db.execute('''CREATE TABLE IF NOT EXISTS deposit_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount REAL,
            tx_detail TEXT,
            status TEXT DEFAULT 'pending',
            created_at TEXT
        )''')

        # سجل الطلبات
        await db.execute('''CREATE TABLE IF NOT EXISTS orders (
            order_id TEXT PRIMARY KEY,
            user_id INTEGER,
            package_id INTEGER,
            package_name TEXT,
            price_usd REAL,
            lpa_code TEXT,
            created_at TEXT
        )''')

        # إعدادات المستخدمين والحظر والأدمن
        await db.execute('''CREATE TABLE IF NOT EXISTS users_settings (
            user_id INTEGER PRIMARY KEY,
            lang TEXT DEFAULT 'ar'
        )''')
        await db.execute('''CREATE TABLE IF NOT EXISTS admins (user_id INTEGER PRIMARY KEY)''')
        await db.execute('''CREATE TABLE IF NOT EXISTS bans (user_id INTEGER PRIMARY KEY)''')

        if DEV_ID:
            await db.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (DEV_ID,))

        # الأقسام الافتراضية
        default_cats = [
            ('personal', 'قسم الأفراد (Personal)', 'Personal Plans'),
            ('wholesale', 'قسم الجملة (Wholesale)', 'Wholesale Plans')
        ]
        for c in default_cats:
            await db.execute("INSERT OR IGNORE INTO categories (slug, name_ar, name_en) VALUES (?, ?, ?)", c)

        # باقات تجريبية أولية في حال كانت القاعدة فارغة
        async with db.execute("SELECT COUNT(*) FROM packages") as cur:
            if (await cur.fetchone())[0] == 0:
                init_pkgs = [
                    ('personal', 'باقة فودافون شهرية (بيانات + مكالمات)', 'Vodafone 1 Month Unlimited', 20.0, 50, 1),
                    ('personal', 'باقة هولافلاي 3 أشهر (بيانات غير محدودة)', 'Holafly 3 Months Unlimited', 35.0, 50, 3),
                    ('wholesale', 'باقة موزعين - 10 شرائح فودافون شهرية', 'Dealer 10x Vodafone 1 Month', 120.0, 20, 1),
                    ('wholesale', 'باقة موزعين - 10 شرائح هولافلاي شهرية', 'Dealer 10x Holafly 1 Month', 100.0, 20, 1)
                ]
                for p in init_pkgs:
                    await db.execute('''INSERT INTO packages 
                        (category_slug, name_ar, name_en, price_usd, stock, duration_months) 
                        VALUES (?, ?, ?, ?, ?, ?)''', p)

        await db.commit()

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
        await db.execute("INSERT OR IGNORE INTO wallets (user_id, balance, total_deposited) VALUES (?, 0, 0)", (uid,))
        await db.execute("UPDATE wallets SET balance = balance + ? WHERE user_id = ?", (amount, uid))
        if amount > 0:
            await db.execute("UPDATE wallets SET total_deposited = total_deposited + ? WHERE user_id = ?", (amount, uid))

        async with db.execute("SELECT balance FROM wallets WHERE user_id=?", (uid,)) as cur:
            new_bal = (await cur.fetchone())[0]

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        await db.execute('''INSERT INTO transactions 
            (user_id, type, amount, balance_after, description, created_at) 
            VALUES (?, ?, ?, ?, ?, ?)''', (uid, tx_type, amount, new_bal, desc, now_str))
        await db.commit()
        return new_bal

async def build_main_menu(uid):
    lang = await get_user_lang(uid)
    t = LANGS.get(lang, LANGS['ar'])
    bal = await get_wallet_balance(uid)

    btn = [
        [Button.inline(t['btn_personal'], b'cat_personal'), Button.inline(t['btn_dealer'], b'cat_wholesale')],
        [Button.inline(f"{t['btn_wallet']} (${bal:.2f})", b'view_wallet'), Button.inline(t['btn_orders'], b'view_orders')],
        [Button.inline(t['btn_support'], b'req_support'), Button.inline(t['btn_lang'], b'change_lang')]
    ]
    if await is_admin(uid):
        btn.append([Button.inline(t['btn_admin'], b'adm_root')])

    return t['welcome'], btn

# ==========================================================
# 5. معالجات الرسائل والأوامر
# ==========================================================
@client.on(events.NewMessage(pattern='/start'))
async def on_start(event):
    uid = event.sender_id
    if await is_banned(uid): return

    now = time.time()
    if uid in user_rate_limits and now - user_rate_limits[uid] < 0.6:
        return
    user_rate_limits[uid] = now

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

    # ------------------ القائمة واللغة ------------------
    if data == 'main_menu':
        text, btn = await build_main_menu(uid)
        await event.edit(text, buttons=btn, parse_mode='html')

    elif data == 'change_lang':
        btn = [
            [Button.inline("🇸🇦 العربية", b'set_lang_ar'), Button.inline("🇬🇧 English", b'set_lang_en')],
            [Button.inline(t['back'], b'main_menu')]
        ]
        await event.edit("<blockquote>🌍 <b>يرجى اختيار اللغة المفضلة / Select Language:</b></blockquote>", buttons=btn, parse_mode='html')

    elif data in ['set_lang_ar', 'set_lang_en']:
        new_lang = 'ar' if data == 'set_lang_ar' else 'en'
        await set_user_lang(uid, new_lang)
        text, btn = await build_main_menu(uid)
        await event.edit(text, buttons=btn, parse_mode='html')

    # ------------------ استعراض الباقات وشراؤها ------------------
    elif data.startswith('cat_'):
        slug = data.replace('cat_', '')
        async with aiosqlite.connect(DB_NAME) as db:
            async with db.execute("SELECT id, name_ar, name_en, price_usd, stock FROM packages WHERE category_slug=? AND is_active=1", (slug,)) as cur:
                pkgs = await cur.fetchall()

        if not pkgs:
            return await event.edit(f"<blockquote>⚠️ <b>لا توجد باقات متاحة حالياً في هذا القسم.</b></blockquote>", buttons=[[Button.inline(t['back'], b'main_menu')]], parse_mode='html')

        btn = []
        for pid, nar, nen, price, stock in pkgs:
            title = nar if lang == 'ar' else nen
            stock_badge = f"[{stock} متاح]" if stock > 0 else "[نفد]"
            btn.append([Button.inline(f"{title} - ${price:.0f} {stock_badge}", f"view_pkg_{pid}".encode())])

        btn.append([Button.inline(t['back'], b'main_menu')])
        section_title = "قسم الأفراد" if slug == 'personal' else "قسم الجملة والتجار"
        await event.edit(f"<blockquote>🌐 <b>باقات {section_title}:</b>\nاختر الباقة المطلوبة للشراء المباشر:</blockquote>", buttons=btn, parse_mode='html')

    elif data.startswith('view_pkg_'):
        pid = int(data.split('_')[2])
        async with aiosqlite.connect(DB_NAME) as db:
            async with db.execute("SELECT name_ar, name_en, price_usd, stock, duration_months, category_slug FROM packages WHERE id=?", (pid,)) as cur:
                pkg = await cur.fetchone()

        if not pkg:
            return await event.answer(t['out_of_stock'], alert=True)

        nar, nen, price, stock, dur, cat_slug = pkg
        title = nar if lang == 'ar' else nen

        if stock <= 0:
            return await event.answer(t['out_of_stock'], alert=True)

        set_session(uid, 'active_purchase', {'pid': pid, 'price': price, 'title': title})

        desc_text = f"""<blockquote>⧺︰ <b>تفاصيل الباقة: {title}</b>
⧺︰ <b>المدة:</b> <code>{dur} شهر</code>
⧺︰ <b>السعر النهائي:</b> <code>${price:.2f}</code>
⧺︰ <b>المخزون المتاح:</b> <code>{stock} شريحة</code>
⧺︰ <b>نوع التفعيل:</b> فوري وموحد عبر QR Code أو كود الـ LPA</blockquote>"""

        btn = [
            [Button.inline(f"⚡ تأكيد الشراء من المحفظة (${price:.2f})", f"confirm_checkout_{pid}".encode())],
            [Button.inline(t['back'], f"cat_{cat_slug}".encode())]
        ]
        await event.edit(desc_text, buttons=btn, parse_mode='html')

    elif data.startswith('confirm_checkout_'):
        pid = int(data.split('_')[2])
        sess = get_session(uid, 'active_purchase')
        if not sess or sess['pid'] != pid:
            return await event.answer("انتهت صلاحية الجلسة، يرجى المحاولة ثانية.", alert=True)

        price = sess['price']
        title = sess['title']

        # قفل العمليات المتزامنة لمنع الدفع المزدوج (Double Spending Lock)
        if uid not in wallet_locks:
            wallet_locks[uid] = asyncio.Lock()

        async with wallet_locks[uid]:
            bal = await get_wallet_balance(uid)
            if bal < price:
                return await event.answer(t['insufficient_balance'], alert=True)

            async with aiosqlite.connect(DB_NAME) as db:
                async with db.execute("SELECT stock FROM packages WHERE id=?", (pid,)) as cur:
                    current_stock = (await cur.fetchone())[0]

                if current_stock <= 0:
                    return await event.answer(t['out_of_stock'], alert=True)

                # خصم المخزون والرصيد في Transaction موحدة
                await db.execute("UPDATE packages SET stock = stock - 1 WHERE id=?", (pid,))
                order_id = f"AURA{secrets.token_hex(4).upper()}"
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

                await db.execute('''INSERT INTO orders 
                    (order_id, user_id, package_id, package_name, price_usd, lpa_code, created_at) 
                    VALUES (?, ?, ?, ?, ?, ?, ?)''', (order_id, uid, pid, title, price, DEFAULT_LPA, now_str))
                await db.commit()

            await update_wallet(uid, -price, 'purchase', f"شراء {title}")

        clear_session(uid, 'active_purchase')

        success_msg = f"""<blockquote>🎉 <b>تم إنجاز طلب الشراء بنجاح!</b>
⧺︰ <b>معرف الطلب:</b> <code>{order_id}</code>
⧺︰ <b>الباقة:</b> {title}
⧺︰ <b>المبلغ المخصوم:</b> <code>${price:.2f}</code>

⧺︰ <b>كود التفعيل اليدوي (LPA):</b>
<code>{DEFAULT_LPA}</code>

⧺︰ <b>أو استخدم الباركود المرفق لتفعيل الشريحة فوراً من إعدادات الجوال.</b></blockquote>"""

        await event.reply(success_msg, file=DEFAULT_BARCODE, parse_mode='html')
        text, btn = await build_main_menu(uid)
        await event.respond(text, buttons=btn, parse_mode='html')

    # ------------------ المحفظة والشحن ------------------
    elif data == 'view_wallet':
        bal = await get_wallet_balance(uid)
        text = f"{t['wallet_title']}\n\n<blockquote>⧺︰ <b>{t['current_balance']}:</b> <code>${bal:.2f}</code></blockquote>\n\n{PAYMENT_ADDRESSES}"
        btn = [
            [Button.inline(t['charge_wallet_btn'], b'start_deposit')],
            [Button.inline(t['back'], b'main_menu')]
        ]
        await event.edit(text, buttons=btn, parse_mode='html')

    elif data == 'start_deposit':
        set_session(uid, 'prompt', 'deposit_amount')
        await event.edit(t['charge_prompt'], buttons=[[Button.inline(t['back'], b'view_wallet')]], parse_mode='html')

    # ------------------ سجل الطلبات ------------------
    elif data == 'view_orders':
        async with aiosqlite.connect(DB_NAME) as db:
            async with db.execute("SELECT order_id, package_name, price_usd, created_at FROM orders WHERE user_id=? ORDER BY created_at DESC LIMIT 6", (uid,)) as cur:
                orders = await cur.fetchall()

        if not orders:
            return await event.edit("<blockquote>📋 <b>لا توجد طلبات مكتملة في سجلك حتى الآن.</b></blockquote>", buttons=[[Button.inline(t['back'], b'main_menu')]], parse_mode='html')

        orders_text = "<blockquote>📋 <b>سجل آخر طلباتك المكتملة:</b></blockquote>\n\n"
        for oid, pname, pr, dt in orders:
            orders_text += f"• <b>{pname}</b> - <code>${pr:.2f}</code>\n  الطلب: <code>{oid}</code> | التاريخ: <code>{dt}</code>\n  الكود: <code>{DEFAULT_LPA}</code>\n────────────────────\n"

        await event.edit(orders_text, buttons=[[Button.inline(t['back'], b'main_menu')]], parse_mode='html')

    # ------------------ الدعم الفني ------------------
    elif data == 'req_support':
        set_session(uid, 'prompt', 'support_text')
        await event.edit(t['support_prompt'], buttons=[[Button.inline(t['back'], b'main_menu')]], parse_mode='html')

    # ==========================================================
    # 6. لوحة التحكم الإدارية الاحترافية (كاملة الصلاحيات)
    # ==========================================================
    elif data == 'adm_root' and await is_admin(uid):
        async with aiosqlite.connect(DB_NAME) as db:
            users_count = (await (await db.execute("SELECT COUNT(*) FROM users_settings")).fetchone())[0]
            orders_count = (await (await db.execute("SELECT COUNT(*) FROM orders")).fetchone())[0]
            revenue = (await (await db.execute("SELECT SUM(price_usd) FROM orders")).fetchone())[0] or 0.0
            wallets_total = (await (await db.execute("SELECT SUM(balance) FROM wallets")).fetchone())[0] or 0.0

        adm_text = f"""<blockquote>⚙️ <b>لوحة تحكم المشرف التنفيذية المطورة:</b>
• <b>إجمالي المستخدمين:</b> <code>{users_count}</code>
• <b>إجمالي المبيعات:</b> <code>{orders_count} طلب</code>
• <b>صافي الإيرادات:</b> <code>${revenue:.2f}</code>
• <b>أرصدة المحافظ:</b> <code>${wallets_total:.2f}</code></blockquote>"""

        btn = [
            [Button.inline("📦 إدارة المخزون والأسعار", b'adm_manage_packages')],
            [Button.inline("➕ إضافة باقة جديدة", b'adm_add_pkg_start')],
            [Button.inline("💰 شحن / خصم رصيد عميل", b'adm_balance_actions')],
            [Button.inline("📢 إذاعة آمنة للجميع", b'adm_start_broadcast')],
            [Button.inline("🚫 إدارة الحظر", b'adm_ban_manager')],
            [Button.inline(t['back'], b'main_menu')]
        ]
        await event.edit(adm_text, buttons=btn, parse_mode='html')

    # إدارة باقات ومخزون الأقسام
    elif data == 'adm_manage_packages' and await is_admin(uid):
        async with aiosqlite.connect(DB_NAME) as db:
            async with db.execute("SELECT id, name_ar, price_usd, stock FROM packages") as cur:
                pkgs = await cur.fetchall()

        btn = []
        for pid, name, pr, st in pkgs:
            btn.append([Button.inline(f"✏️ {name} | ${pr:.0f} | مخزون: {st}", f"adm_edit_pkg_{pid}".encode())])
        btn.append([Button.inline(t['back'], b'adm_root')])
        await event.edit("<blockquote>📦 <b>اختر الباقة المراد تعديل سعرها أو مخزونها أو حذفها:</b></blockquote>", buttons=btn, parse_mode='html')

    elif data.startswith('adm_edit_pkg_') and await is_admin(uid):
        pid = int(data.split('_')[3])
        async with aiosqlite.connect(DB_NAME) as db:
            async with db.execute("SELECT name_ar, price_usd, stock FROM packages WHERE id=?", (pid,)) as cur:
                p = await cur.fetchone()

        if not p: return
        set_session(uid, 'adm_target_pkg', pid)

        pkg_info = f"""<blockquote>✏️ <b>إدارة الباقة: {p[0]}</b>
• السعر الحالي: <code>${p[1]:.2f}</code>
• المخزون المتوفر: <code>{p[2]}</code> قطعة</blockquote>"""

        btn = [
            [Button.inline("تعديل المخزون", b'adm_set_pkg_stock'), Button.inline("تعديل السعر", b'adm_set_pkg_price')],
            [Button.inline("🗑️ حذف الباقة نهائياً", b'adm_del_pkg_confirm')],
            [Button.inline(t['back'], b'adm_manage_packages')]
        ]
        await event.edit(pkg_info, buttons=btn, parse_mode='html')

    elif data == 'adm_set_pkg_stock' and await is_admin(uid):
        set_session(uid, 'prompt', 'adm_input_stock')
        await event.edit("<blockquote>📦 <b>أرسل الكمية الإجمالية الجديدة للمخزون (رقم صحيح):</b></blockquote>", buttons=[[Button.inline(t['back'], b'adm_manage_packages')]], parse_mode='html')

    elif data == 'adm_set_pkg_price' and await is_admin(uid):
        set_session(uid, 'prompt', 'adm_input_price')
        await event.edit("<blockquote>💵 <b>أرسل السعر الجديد بالدولار (مثال: 25.5):</b></blockquote>", buttons=[[Button.inline(t['back'], b'adm_manage_packages')]], parse_mode='html')

    elif data == 'adm_del_pkg_confirm' and await is_admin(uid):
        pid = get_session(uid, 'adm_target_pkg')
        if pid:
            async with aiosqlite.connect(DB_NAME) as db:
                await db.execute("DELETE FROM packages WHERE id=?", (pid,))
                await db.commit()
            await event.answer("تم حذف الباقة بنجاح", alert=True)
        await on_callback(event)

    # إضافة باقة جديدة
    elif data == 'adm_add_pkg_start' and await is_admin(uid):
        set_session(uid, 'prompt', 'adm_add_pkg_flow')
        await event.edit("<blockquote>➕ <b>لإضافة باقة جديدة أرسل بياناتها بسطر واحد بالصيغة التالية:</b>\n\n<code>القسم(personal/wholesale) | اسم الباقة عربي | Price | Stock | Months</code>\n\n<b>مثال:</b>\n<code>personal | باقة سياحية 15 يوم | 18 | 50 | 1</code></blockquote>", buttons=[[Button.inline(t['back'], b'adm_root')]], parse_mode='html')

    # الرصيد والإذاعة والحظر
    elif data == 'adm_balance_actions' and await is_admin(uid):
        set_session(uid, 'prompt', 'adm_adjust_balance')
        await event.edit("<blockquote>💰 <b>أرسل آيدي العميل ثم المبلغ المراد إضافته (أو رقم سالب للخصم):</b>\n\nمثال لإضافة 50 دولار: <code>123456789 50</code>\nمثال لخصم 20 دولار: <code>123456789 -20</code></blockquote>", buttons=[[Button.inline(t['back'], b'adm_root')]], parse_mode='html')

    elif data == 'adm_start_broadcast' and await is_admin(uid):
        set_session(uid, 'prompt', 'adm_broadcast_text')
        await event.edit("<blockquote>📢 <b>أرسل الرسالة المراد إذاعتها لجميع المشتركين:</b></blockquote>", buttons=[[Button.inline(t['back'], b'adm_root')]], parse_mode='html')

    elif data == 'adm_ban_manager' and await is_admin(uid):
        set_session(uid, 'prompt', 'adm_ban_user_id')
        await event.edit("<blockquote>🚫 <b>أرسل آيدي المستخدم لحظره أو فك حظره فوراً:</b></blockquote>", buttons=[[Button.inline(t['back'], b'adm_root')]], parse_mode='html')

    # تدقيق الإيصالات المالي
    elif data.startswith('approve_dep_') and await is_admin(uid):
        dep_id = int(data.split('_')[2])
        async with aiosqlite.connect(DB_NAME) as db:
            async with db.execute("SELECT user_id, amount, status FROM deposit_requests WHERE id=?", (dep_id,)) as cur:
                row = await cur.fetchone()
                if not row or row[2] != 'pending':
                    return await event.answer("تم اتخاذ إجراء مسبق على هذا الإيصال!", alert=True)

                target_uid, amount, _ = row
                await db.execute("UPDATE deposit_requests SET status='approved' WHERE id=?", (dep_id,))
                await db.commit()

        await update_wallet(target_uid, amount, 'deposit', f"إيداع مؤكد #{dep_id}")
        try:
            await client.send_message(target_uid, f"<blockquote>✅ <b>تم قبول إيصال الدفع وإضافة ${amount:.2f} إلى محفظتك بنجاح!</b></blockquote>", parse_mode='html')
        except: pass
        await event.edit(f"<blockquote>✅ <b>تمت الموافقة وشحن ${amount:.2f} للمستخدم <code>{target_uid}</code> بنجاح.</b></blockquote>", parse_mode='html')

    elif data.startswith('reject_dep_') and await is_admin(uid):
        dep_id = int(data.split('_')[2])
        async with aiosqlite.connect(DB_NAME) as db:
            async with db.execute("SELECT user_id, status FROM deposit_requests WHERE id=?", (dep_id,)) as cur:
                row = await cur.fetchone()
                if not row or row[1] != 'pending':
                    return await event.answer("تمت معالجة الإيصال مسبقاً", alert=True)

                target_uid = row[0]
                await db.execute("UPDATE deposit_requests SET status='rejected' WHERE id=?", (dep_id,))
                await db.commit()

        try:
            await client.send_message(target_uid, "<blockquote>❌ <b>عذراً، تم رفض إيصال الدفع لعدم مطابقته. تواصل مع الدعم للمساعدة.</b></blockquote>", parse_mode='html')
        except: pass
        await event.edit(f"<blockquote>❌ <b>تم رفض الطلب #{dep_id}.</b></blockquote>", parse_mode='html')

# ==========================================================
# 7. معالج الرسائل النصية والمدخلات
# ==========================================================
@client.on(events.NewMessage)
async def on_text(event):
    uid = event.sender_id
    if await is_banned(uid) or event.text.startswith('/'): return

    prompt_action = get_session(uid, 'prompt')
    if not prompt_action: return

    text = event.text.strip() if event.text else ""

    # شحن المحفظة
    if prompt_action == 'deposit_amount':
        try:
            amount = float(text)
            if amount < 20:
                return await event.reply("<blockquote>⚠️ <b>الحد الأدنى للشحن هو $20. يرجى إدخال مبلغ صحيح.</b></blockquote>", parse_mode='html')
            
            set_session(uid, 'pending_deposit_val', amount)
            set_session(uid, 'prompt', 'waiting_receipt')
            dep_msg = f"""<blockquote>💵 <b>المبلغ المطلوب تحويله:</b> <code>${amount:.2f}</code></blockquote>\n\n{PAYMENT_ADDRESSES}\n\n<blockquote>🧾 <b>قم بالتحويل عبر أي طريقة أعلاه ثم أرسل صورة الإيصال أو الـ TxID هنا الآن:</b></blockquote>"""
            await event.reply(dep_msg, parse_mode='html')
        except ValueError:
            await event.reply("<blockquote>⚠️ <b>يرجى إرسال رقم صحيح.</b></blockquote>", parse_mode='html')

    elif prompt_action == 'waiting_receipt':
        amount = get_session(uid, 'pending_deposit_val') or 20.0
        clear_session(uid, 'prompt')
        clear_session(uid, 'pending_deposit_val')

        tx_info = text if text else "صورة إيصال مرفقة"
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

        async with aiosqlite.connect(DB_NAME) as db:
            cur = await db.execute("INSERT INTO deposit_requests (user_id, amount, tx_detail, created_at) VALUES (?, ?, ?, ?)",
                                   (uid, amount, tx_info, now_str))
            dep_id = cur.lastrowid
            await db.commit()

        await event.reply("<blockquote>✅ <b>تم إرسال إيصالك لغرفة العمليات، وسيتم شحن الرصيد آلياً فور المراجعة.</b></blockquote>", parse_mode='html')

        adm_alert = f"""<blockquote>🚨 <b>طلب شحن رصيد جديد (#{dep_id})</b>
• <b>العميل:</b> <code>{uid}</code>
• <b>المبلغ المطلوب:</b> <code>${amount:.2f}</code>
• <b>البيان:</b> {tx_info}</blockquote>"""

        adm_btns = [
            [Button.inline("✅ قبول وشحن الرصيد", f"approve_dep_{dep_id}".encode()),
             Button.inline("❌ رفض الإيصال", f"reject_dep_{dep_id}".encode())]
        ]
        if event.media:
            await client.send_file(DEV_ID, event.media, caption=adm_alert, buttons=adm_btns, parse_mode='html')
        else:
            await client.send_message(DEV_ID, adm_alert, buttons=adm_btns, parse_mode='html')

    # تذاكر الدعم
    elif prompt_action == 'support_text':
        clear_session(uid, 'prompt')
        await event.reply("<blockquote>✅ <b>تم استلام رسالتك وسيتم الرد عليك مباشرة من الدعم.</b></blockquote>", parse_mode='html')
        await client.send_message(DEV_ID, f"<blockquote>💬 <b>رسالة دعم من المستخدم:</b> <code>{uid}</code>\n\n{text}</blockquote>", parse_mode='html')

    # مدخلات لوحة التحكم
    elif prompt_action == 'adm_input_stock' and await is_admin(uid):
        clear_session(uid, 'prompt')
        pid = get_session(uid, 'adm_target_pkg')
        try:
            st = int(text)
            async with aiosqlite.connect(DB_NAME) as db:
                await db.execute("UPDATE packages SET stock=? WHERE id=?", (st, pid))
                await db.commit()
            await event.reply(f"<blockquote>✅ <b>تم تحديث المخزون إلى {st} شريحة بنجاح.</b></blockquote>", parse_mode='html')
        except:
            await event.reply("⚠️ صيغة غير صحيحة.")

    elif prompt_action == 'adm_input_price' and await is_admin(uid):
        clear_session(uid, 'prompt')
        pid = get_session(uid, 'adm_target_pkg')
        try:
            pr = float(text)
            async with aiosqlite.connect(DB_NAME) as db:
                await db.execute("UPDATE packages SET price_usd=? WHERE id=?", (pr, pid))
                await db.commit()
            await event.reply(f"<blockquote>✅ <b>تم تحديث السعر إلى ${pr:.2f} بنجاح.</b></blockquote>", parse_mode='html')
        except:
            await event.reply("⚠️ صيغة غير صحيحة.")

    elif prompt_action == 'adm_add_pkg_flow' and await is_admin(uid):
        clear_session(uid, 'prompt')
        try:
            cat, nar, pr, st, mo = [x.strip() for x in text.split('|')]
            async with aiosqlite.connect(DB_NAME) as db:
                await db.execute('''INSERT INTO packages 
                    (category_slug, name_ar, name_en, price_usd, stock, duration_months) 
                    VALUES (?, ?, ?, ?, ?, ?)''', (cat, nar, nar, float(pr), int(st), int(mo)))
                await db.commit()
            await event.reply("<blockquote>✅ <b>تمت إضافة الباقة الجديدة بنجاح!</b></blockquote>", parse_mode='html')
        except Exception as e:
            await event.reply(f"❌ تعذر إضافة الباقة، تأكد من الصيغة: {e}")

    elif prompt_action == 'adm_adjust_balance' and await is_admin(uid):
        clear_session(uid, 'prompt')
        try:
            target_id, amt = text.split()
            await update_wallet(int(target_id), float(amt), 'admin_adj', "تعديل رصيد بواسطة الإدارة")
            await event.reply(f"<blockquote>✅ <b>تم تعديل رصيد العميل <code>{target_id}</code> بمقدار ${float(amt):.2f}.</b></blockquote>", parse_mode='html')
        except:
            await event.reply("⚠️ صيغة خاطئة. مثال: `123456789 50`")

    elif prompt_action == 'adm_ban_user_id' and await is_admin(uid):
        clear_session(uid, 'prompt')
        try:
            target_id = int(text)
            if target_id == DEV_ID: return
            if await is_banned(target_id):
                async with aiosqlite.connect(DB_NAME) as db:
                    await db.execute("DELETE FROM bans WHERE user_id=?", (target_id,))
                    await db.commit()
                ban_cache.pop(target_id, None)
                await event.reply(f"<blockquote>✅ <b>تم فك حظر المستخدم <code>{target_id}</code>.</b></blockquote>", parse_mode='html')
            else:
                async with aiosqlite.connect(DB_NAME) as db:
                    await db.execute("INSERT OR REPLACE INTO bans (user_id) VALUES (?)", (target_id,))
                    await db.commit()
                ban_cache[target_id] = True
                await event.reply(f"<blockquote>🚫 <b>تم حظر المستخدم <code>{target_id}</code> من البوت.</b></blockquote>", parse_mode='html')
        except:
            await event.reply("⚠️ يرجى إرسال آيدي رقمي صحيح.")

    elif prompt_action == 'adm_broadcast_text' and await is_admin(uid):
        clear_session(uid, 'prompt')
        status = await event.reply("<blockquote>⏳ <b>جارٍ إرسال الإذاعة لجميع المشتركين بأمان...</b></blockquote>", parse_mode='html')

        async with aiosqlite.connect(DB_NAME) as db:
            async with db.execute("SELECT user_id FROM users_settings") as cur:
                users = await cur.fetchall()

        succ, fail = 0, 0
        for (u,) in users:
            try:
                await client.send_message(u, f"<blockquote>📢 <b>إعلان رسمي من إدارة Aura eSIM:</b>\n\n{text}</blockquote>", parse_mode='html')
                succ += 1
                await asyncio.sleep(0.05)
            except errors.FloodWaitError as e:
                await asyncio.sleep(e.seconds)
                try:
                    await client.send_message(u, f"<blockquote>📢 <b>إعلان رسمي من إدارة Aura eSIM:</b>\n\n{text}</blockquote>", parse_mode='html')
                    succ += 1
                except:
                    fail += 1
            except:
                fail += 1

        await status.edit(f"<blockquote>📢 <b>اكتملت الإذاعة بنجاح!</b>\n• نجاح: <code>{succ}</code>\n• فشل: <code>{fail}</code></blockquote>", parse_mode='html')

# ==========================================================
# 8. نقطة التشغيل الرئيسية
# ==========================================================
async def main():
    await init_db()
    await client.start(bot_token=BOT_TOKEN)
    logger.info("Aura eSIM Elite Bot initialized with bulletproof architecture and unified LPA delivery.")
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
