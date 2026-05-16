

from dotenv import load_dotenv
import os
from flask import Flask, render_template, request, redirect, session, url_for, flash, jsonify
import requests
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from groq import Groq

# ============================================
# APP CONFIG
# ============================================

app = Flask(__name__)
load_dotenv()
app.secret_key = "nepseniti-super-secret-key"

# ============================================
# CREDENTIALS
# ============================================

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

ADMIN_EMAIL = "admin@nepseniti.com"

# ============================================
# HEADERS
# ============================================

headers = {
    "apikey": SUPABASE_ANON_KEY,
    "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
    "Content-Type": "application/json"
}

# ============================================
# GROQ CLIENT
# ============================================

client = Groq(api_key=GROQ_API_KEY)

SECTOR_MAP = {
    # Commercial Banks
    "NABIL":"Commercial Banks","NBL":"Commercial Banks","NICA":"Commercial Banks",
    "EBL":"Commercial Banks","SBI":"Commercial Banks","SANIMA":"Commercial Banks",
    "MBL":"Commercial Banks","CBL":"Commercial Banks","PRVU":"Commercial Banks",
    "KBL":"Commercial Banks","SRBL":"Commercial Banks","GBIME":"Commercial Banks",
    "HBL":"Commercial Banks","NIMB":"Commercial Banks","NMB":"Commercial Banks",
    "PCBL":"Commercial Banks","SBL":"Commercial Banks","ADBL":"Commercial Banks",
    "CZBIL":"Commercial Banks","LSL":"Commercial Banks","BOKL":"Commercial Banks",
    "MEGA":"Commercial Banks","CCBL":"Commercial Banks","JBNL":"Commercial Banks",
    "NABBC":"Commercial Banks","RBB":"Commercial Banks","NBB":"Commercial Banks",
    "SCB":"Commercial Banks","NIBL":"Commercial Banks","LBBL":"Commercial Banks",
    "GBBL":"Commercial Banks","NIC":"Commercial Banks","CITY":"Commercial Banks",

    # Development Banks
    "CORBL":"Development Bank Limited","SAPDBL":"Development Bank Limited",
    "KSBBL":"Development Bank Limited","SHINE":"Development Bank Limited",
    "SINDU":"Development Bank Limited","SADBL":"Development Bank Limited",
    "EDBL":"Development Bank Limited","MNBBL":"Development Bank Limited",
    "MLBL":"Development Bank Limited","GRDBL":"Development Bank Limited",
    "SBBL":"Development Bank Limited","NWCL":"Development Bank Limited",
    "JBBL":"Development Bank Limited","LBBL":"Development Bank Limited",
    "KRBL":"Development Bank Limited","CEDB":"Development Bank Limited",
    "DALB":"Development Bank Limited","GBBL":"Development Bank Limited",

    # Finance
    "HFIN":"Finance","SIFC":"Finance","UFL":"Finance","GFCL":"Finance",
    "MFIL":"Finance","PFL":"Finance","ICFC":"Finance","CFCL":"Finance",
    "RLFL":"Finance","JFL":"Finance","SFCL":"Finance","BESTL":"Finance",
    "GUFL":"Finance","MPFL":"Finance","BFC":"Finance","PROFL":"Finance",
    "NFS":"Finance","CITY":"Finance","GMFIL":"Finance","CLI":"Finance",

    # Microfinance
    "FMDBL":"Microfinance","ILBS":"Microfinance","CBBL":"Microfinance",
    "MLBSL":"Microfinance","SWBBL":"Microfinance","DDBL":"Microfinance",
    "SKBBL":"Microfinance","SMFBS":"Microfinance","NESDO":"Microfinance",
    "NICLBSL":"Microfinance","KMCDB":"Microfinance","MERO":"Microfinance",
    "NCLBSL":"Microfinance","VLBS":"Microfinance","HLBSL":"Microfinance",
    "SLBBL":"Microfinance","JBLB":"Microfinance","SBBL":"Microfinance",
    "UNLB":"Microfinance","SHLB":"Microfinance","WNLB":"Microfinance",
    "NMBMF":"Microfinance","GMFBS":"Microfinance","MLBBL":"Microfinance",
    "SWMF":"Microfinance","SLBSL":"Microfinance","ACLBSL":"Microfinance",
    "USLB":"Microfinance","DLBS":"Microfinance","LLBS":"Microfinance",
    "GLBSL":"Microfinance","ALBSL":"Microfinance","GILB":"Microfinance",
    "MSLB":"Microfinance","GBLBS":"Microfinance","NMFBS":"Microfinance",
    "SMHL":"Microfinance","SABBL":"Microfinance","KKHC":"Microfinance",
    "ULBSL":"Microfinance","NMLBBL":"Microfinance","NUBL":"Microfinance",

    # Hydropower
    "NHDL":"Hydro Power","NHPC":"Hydro Power","UPPER":"Hydro Power",
    "RIDI":"Hydro Power","AKPL":"Hydro Power","RHPC":"Hydro Power",
    "RADHI":"Hydro Power","SHL":"Hydro Power","UHEWA":"Hydro Power",
    "MAKAR":"Hydro Power","KPCL":"Hydro Power","HPPL":"Hydro Power",
    "PMHPL":"Hydro Power","BPCL":"Hydro Power","GHL":"Hydro Power",
    "API":"Hydro Power","NYADI":"Hydro Power","DHPL":"Hydro Power",
    "DOLTI":"Hydro Power","RKPCL":"Hydro Power","AKJCL":"Hydro Power",
    "CHCL":"Hydro Power","HIDCL":"Hydro Power","HIDCLP":"Hydro Power",
    "SSHL":"Hydro Power","BHL":"Hydro Power","HDHPC":"Hydro Power",
    "AHPC":"Hydro Power","SHPC":"Hydro Power","BARUN":"Hydro Power",
    "SJCL":"Hydro Power","HURJA":"Hydro Power","RFPL":"Hydro Power",
    "DORDI":"Hydro Power","LEC":"Hydro Power","HHL":"Hydro Power",
    "MBJC":"Hydro Power","SPDL":"Hydro Power","TAMOR":"Hydro Power",
    "RLEL":"Hydro Power","TPC":"Hydro Power","UMHL":"Hydro Power",
    "RHGCL":"Hydro Power","GLH":"Hydro Power","BJHL":"Hydro Power",
    "EHPL":"Hydro Power","DHEL":"Hydro Power","SHEL":"Hydro Power",
    "HEI":"Hydro Power","USHEC":"Hydro Power","PMLI":"Hydro Power",
    "PHCL":"Hydro Power","MEHL":"Hydro Power","MHCL":"Hydro Power",
    "MHL":"Hydro Power","MCHL":"Hydro Power","UMRH":"Hydro Power",
    "MKHL":"Hydro Power","SPHL":"Hydro Power","BHPL":"Hydro Power",
    "BHDC":"Hydro Power","BEDC":"Hydro Power","RURU":"Hydro Power",
    "GVL":"Hydro Power","SGHC":"Hydro Power","BNHC":"Hydro Power",
    "MHNL":"Hydro Power","CKHL":"Hydro Power","SKHL":"Hydro Power",
    "SKHEL":"Hydro Power","NHDL":"Hydro Power","TSHL":"Hydro Power",
    "USHL":"Hydro Power","MSHL":"Hydro Power","SMH":"Hydro Power",
    "AVYAN":"Hydro Power","ULHC":"Hydro Power","SOHL":"Hydro Power",
    "SHIVM":"Hydro Power","SMJC":"Hydro Power","SAIL":"Hydro Power",
    "HDL":"Hydro Power","IHL":"Hydro Power","UPCL":"Hydro Power",
    "PPL":"Hydro Power","BHCL":"Hydro Power","FOWAD":"Hydro Power",
    "MKCL":"Hydro Power","MAKAR":"Hydro Power","SIKLES":"Hydro Power",
    "KPCL":"Hydro Power","CGH":"Hydro Power","SAHAS":"Hydro Power",
    "NGPL":"Hydro Power","MANDU":"Hydro Power","VLUCL":"Hydro Power",
    "KDL":"Hydro Power","RLEL":"Hydro Power","SMPDA":"Hydro Power",
    "MKJC":"Hydro Power","MMKJL":"Hydro Power","BGWT":"Hydro Power",
    "HRL":"Hydro Power","BUNGAL":"Hydro Power","MEL":"Hydro Power",

    # Life Insurance
    "NLIC":"Life Insurance","LICN":"Life Insurance","ALICL":"Life Insurance",
    "SLICL":"Life Insurance","SJLIC":"Life Insurance","NLICL":"Life Insurance",
    "SNLI":"Life Insurance","ILI":"Life Insurance","PMLI":"Life Insurance",
    "CLI":"Life Insurance","GILB":"Life Insurance","SRLI":"Life Insurance",
    "NMIC":"Life Insurance","JOSHI":"Life Insurance","AHL":"Life Insurance",
    "HLI":"Life Insurance","MABEL":"Life Insurance","UAIL":"Life Insurance",

    # Non-Life Insurance
    "NICL":"Non-Life Insurance","PICL":"Non-Life Insurance","SICL":"Non-Life Insurance",
    "HGICL":"Non-Life Insurance","RBCL":"Non-Life Insurance","SGIC":"Non-Life Insurance",
    "SPICL":"Non-Life Insurance","PRIN":"Non-Life Insurance","AIL":"Non-Life Insurance",
    "NLG":"Non-Life Insurance","IGI":"Non-Life Insurance","GCIL":"Non-Life Insurance",
    "NRIC":"Non-Life Insurance","SALICO":"Non-Life Insurance","NIL":"Non-Life Insurance",
    "PPCL":"Non-Life Insurance","SANVI":"Non-Life Insurance","SPIL":"Non-Life Insurance",
    "SPC":"Non-Life Insurance","MDB":"Non-Life Insurance","RNLI":"Non-Life Insurance",
    "ALICL":"Non-Life Insurance",

    # Investment
    "CIT":"Investment","NIFRA":"Investment","ENL":"Investment",
    "HIDCL":"Investment","SMB":"Investment",

    # Hotels & Tourism
    "OHL":"Hotels And Tourism","TRH":"Hotels And Tourism","KDL":"Hotels And Tourism",
    "NRN":"Hotels And Tourism","CHDC":"Hotels And Tourism","CITY":"Hotels And Tourism",
    "CGH":"Hotels And Tourism",

    # Manufacturing
    "NTC":"Manufacturing And Processing","UNL":"Manufacturing And Processing",
    "BBC":"Manufacturing And Processing","BNT":"Manufacturing And Processing",
    "RSML":"Manufacturing And Processing","STC":"Manufacturing And Processing",
    "TTL":"Manufacturing And Tourism","OMPL":"Manufacturing And Processing",
    "SBID2090":"Manufacturing And Processing",

    # Tradings
    "SHL":"Tradings","SMB":"Tradings",
}

# ============================================
# TELEGRAM BOT STATE (in-memory)
# Tracks users mid-conversation waiting to send email
# ============================================

waiting_for_email = {}

# ============================================
# GET LIVE NEPSE DATA
# ============================================

def get_market_data():
    try:
        url = "https://merolagani.com/handlers/webrequesthandler.ashx?type=market_summary"
        response = requests.get(url, timeout=20)
        if response.status_code == 200:
            data = response.json()
            stocks  = data.get("turnover", {}).get("detail", [])
            sectors = data.get("sector",   {}).get("detail", [])
            overall = data.get("overall",  {})
            return {"stocks": stocks, "sectors": sectors, "overall": overall}
        return {"stocks": [], "sectors": [], "overall": {}}
    except Exception as e:
        print("Market data error:", e)
        return {"stocks": [], "sectors": [], "overall": {}}


# ============================================
# GET STOCK PRICE
# ============================================

def get_stock_price(symbol):
    market = get_market_data()
    stocks = market["stocks"]
    for stock in stocks:
        if stock.get("s") == symbol.upper():
            ltp    = float(stock.get("lp",  0))
            change = float(stock.get("pc",  0))
            high   = float(stock.get("h",   0))
            low    = float(stock.get("l",   0))
            open_  = float(stock.get("op",  0))
            volume = float(stock.get("q",   0))
            turnover = float(stock.get("t", 0))

            # intraday trend: LTP vs Open
            if open_ > 0:
                intraday_chg = round((ltp - open_) / open_ * 100, 2)
            else:
                intraday_chg = 0

            # volume flag
            avg_vol_threshold = 50000
            volume_flag = "सक्रिय 🔥" if volume >= avg_vol_threshold else "सामान्य"

            return {
                "ltp": ltp, "change": change,
                "high": high, "low": low,
                "open": open_, "volume": volume,
                "turnover": turnover,
                "intraday_chg": intraday_chg,
                "volume_flag": volume_flag,
            }
    return {
        "ltp": 0, "change": 0, "high": 0, "low": 0,
        "open": 0, "volume": 0, "turnover": 0,
        "intraday_chg": 0, "volume_flag": "N/A",
    }


# ============================================
# SEND TELEGRAM MESSAGE
# ============================================

def send_telegram_message(chat_id, message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        response = requests.post(url, data=data, timeout=20)
        print("Telegram Response:", response.text)
        return response.json()
    except Exception as e:
        print("Telegram Error:", e)
        return None

# ============================================
# SET TELEGRAM WEBHOOK
# ============================================

def set_telegram_webhook(app_url):
    webhook_url = f"{app_url}/webhook"
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/setWebhook"
    response = requests.post(url, data={"url": webhook_url})
    print("Webhook set:", response.text)
    return response.json()

# ============================================
# LINK TELEGRAM CHAT ID TO USER IN SUPABASE
# ============================================

def link_telegram_to_user(email, chat_id):
    url = f"{SUPABASE_URL}/rest/v1/Users?email=eq.{email}"
    data = {
        "telegram_chat_id": str(chat_id),
        "alerts_enabled": True
    }
    response = requests.patch(url, headers=headers, json=data)
    return response.status_code in [200, 204]

# ============================================
# CHECK IF EMAIL EXISTS IN SUPABASE
# ============================================

def find_user_by_email(email):
    url = f"{SUPABASE_URL}/rest/v1/Users?email=eq.{email}"
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        users = response.json()
        if len(users) > 0:
            return users[0]
    return None

# ============================================
# GET ALL USERS
# ============================================

def get_all_users():
    url = f"{SUPABASE_URL}/rest/v1/Users"
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    return []

# ============================================
# DAILY ALERT FUNCTION
# ============================================

def send_daily_alerts():
    print("Sending NepseNiti daily alerts...")
    users = get_all_users()

    for user in users:
        try:
            if not user.get("alerts_enabled"):
                continue

            chat_id = user.get("telegram_chat_id")
            if not chat_id:
                continue

            email = user.get("email")

            # FETCH PORTFOLIO
            portfolio_url = f"{SUPABASE_URL}/rest/v1/portfolios?user_name=eq.{email}"
            response = requests.get(portfolio_url, headers=headers)
            portfolio_items = response.json()

            if len(portfolio_items) == 0:
                send_telegram_message(
                    chat_id,
                    f"📊 <b>NepseNiti Daily Alert</b>\n\nनमस्ते {user.get('name', '')}! तपाईंको portfolio खाली छ। Portfolio page मा गएर stocks थप्नुहोस्।\n\n🌐 https://nepseniti.up.railway.app/portfolio"
                )
                continue

            total_invested = 0
            total_current = 0
            holdings_text = ""

            for item in portfolio_items:
                symbol = item["symbol"]
                qty = item["quantity"]
                buy_price = item["buy_price"]
                stock = get_stock_price(symbol)
                ltp = stock["ltp"]
                invested = qty * buy_price
                current = qty * ltp
                pnl = current - invested
                total_invested += invested
                total_current += current
                pnl_emoji = "📈" if pnl >= 0 else "📉"
                holdings_text += (
                    f"{pnl_emoji} {symbol}: {qty} कित्ता, "
                    f"खरिद Rs.{buy_price}, "
                    f"हालको Rs.{ltp}, "
                    f"नाफा/नोक्सान Rs.{round(pnl, 2)}\n"
                )

            total_pnl = total_current - total_invested
            pnl_percent = 0
            if total_invested > 0:
                pnl_percent = (total_pnl / total_invested) * 100

            # AI PROMPT
            prompt = f"""तपाईं नेपाल शेयर बजारका अनुभवी विश्लेषक हुनुहुन्छ।

तलको पोर्टफोलियोको छोटो दैनिक विश्लेषण नेपाली भाषामा गर्नुहोस्।

पोर्टफोलियो:
{holdings_text}

कुल लगानी: Rs.{round(total_invested, 2)}
हालको मूल्य: Rs.{round(total_current, 2)}
कुल नाफा/नोक्सानी: Rs.{round(total_pnl, 2)} ({round(pnl_percent, 2)}%)

छोटो, professional, useful analysis दिनुहोस्। ५-७ लाइन मात्र।"""

            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}]
            )
            ai_text = completion.choices[0].message.content

            pnl_emoji = "📈" if total_pnl >= 0 else "📉"

            message = f"""📊 <b>NepseNiti दैनिक रिपोर्ट</b>
नमस्ते {user.get('name', '')}!

💰 कुल मूल्य: <b>Rs.{round(total_current, 2)}</b>
{pnl_emoji} नाफा/नोक्सान: <b>Rs.{round(total_pnl, 2)} ({round(pnl_percent, 2)}%)</b>

━━━━━━━━━━━━━━
<b>Holdings:</b>
{holdings_text}
━━━━━━━━━━━━━━
🤖 <b>AI विश्लेषण:</b>
{ai_text}

━━━━━━━━━━━━━━
🌐 <a href="https://nepseniti.up.railway.app/dashboard">Dashboard हेर्नुहोस्</a>
NepseNiti 🇳🇵"""

            send_telegram_message(chat_id, message)
            print(f"Alert sent to {email}")

        except Exception as e:
            print("Alert Error:", e)

# ============================================
# SCHEDULER - 4PM NST = 10:15 UTC
# ============================================

scheduler = BackgroundScheduler()
scheduler.add_job(send_daily_alerts, 'cron', hour=10, minute=15)
scheduler.start()

# ============================================
# TELEGRAM WEBHOOK ROUTE
# ============================================

@app.route("/webhook", methods=["POST"])
def webhook():
    global waiting_for_email

    data = request.get_json()

    if not data or "message" not in data:
        return jsonify({"ok": True})

    message = data["message"]
    chat_id = str(message["chat"]["id"])
    text = message.get("text", "").strip()
    first_name = message["chat"].get("first_name", "")

    # USER SENT /start
    if text == "/start":
        waiting_for_email[chat_id] = True
        send_telegram_message(
            chat_id,
            f"🇳🇵 <b>NepseNitiमा स्वागत छ!</b>\n\n"
            f"नमस्ते {first_name}! म तपाईंलाई दैनिक ४ बजे NEPSE portfolio alert पठाउँछु।\n\n"
            f"📧 कृपया आफ्नो NepseNiti <b>email address</b> पठाउनुहोस्:\n\n"
            f"(उदाहरण: yourname@gmail.com)\n\n"
            f"अझै account छैन? यहाँ बनाउनुहोस्:\n"
            f"🌐 https://nepseniti.up.railway.app/signup"
        )
        return jsonify({"ok": True})

    # USER SENT /status
    if text == "/status":
        url = f"{SUPABASE_URL}/rest/v1/Users?telegram_chat_id=eq.{chat_id}"
        response = requests.get(url, headers=headers)
        users = response.json()
        if users:
            user = users[0]
            send_telegram_message(
                chat_id,
                f"✅ <b>Connected!</b>\n\n"
                f"नाम: {user.get('name', '')}\n"
                f"Email: {user.get('email', '')}\n"
                f"Alert: {'Enabled ✅' if user.get('alerts_enabled') else 'Disabled ❌'}\n\n"
                f"दैनिक ४ बजे alert आउँछ।"
            )
        else:
            send_telegram_message(
                chat_id,
                "❌ तपाईंको account link भएको छैन।\n/start पठाएर email दिनुहोस्।"
            )
        return jsonify({"ok": True})

    # USER SENT /stop
    if text == "/stop":
        url = f"{SUPABASE_URL}/rest/v1/Users?telegram_chat_id=eq.{chat_id}"
        requests.patch(url, headers=headers, json={"alerts_enabled": False})
        send_telegram_message(
            chat_id,
            "🔕 Alert बन्द गरियो।\nफेरि सुरु गर्न /start पठाउनुहोस्।"
        )
        waiting_for_email.pop(chat_id, None)
        return jsonify({"ok": True})

    # USER IS IN EMAIL WAITING STATE - they sent their email
    if waiting_for_email.get(chat_id):
        email = text.lower().strip()

        # Basic email validation
        if "@" not in email or "." not in email:
            send_telegram_message(
                chat_id,
                "❌ सही email address पठाउनुहोस्।\nउदाहरण: yourname@gmail.com"
            )
            return jsonify({"ok": True})

        # Find user in Supabase
        user = find_user_by_email(email)

        if user:
            # Link chat_id to user
            success = link_telegram_to_user(email, chat_id)
            if success:
                waiting_for_email.pop(chat_id, None)
                send_telegram_message(
                    chat_id,
                    f"✅ <b>सफलतापूर्वक जोडियो!</b>\n\n"
                    f"नमस्ते {user.get('name', '')}!\n\n"
                    f"तपाईंको account link भयो।\n"
                    f"अब दैनिक <b>४ बजे NST</b> मा portfolio alert आउनेछ।\n\n"
                    f"📊 Portfolio हेर्न: https://nepseniti.up.railway.app/dashboard\n\n"
                    f"Commands:\n"
                    f"/status - आफ्नो status हेर्नुहोस्\n"
                    f"/stop - alert बन्द गर्नुहोस्"
                )
            else:
                send_telegram_message(
                    chat_id,
                    "❌ Error भयो। फेरि /start गर्नुहोस्।"
                )
        else:
            send_telegram_message(
                chat_id,
                f"❌ <b>{email}</b> यो email NepseNiti मा भेटिएन।\n\n"
                f"पहिले account बनाउनुहोस्:\n"
                f"🌐 https://nepseniti.up.railway.app/signup\n\n"
                f"Account बनाएपछि फेरि /start पठाउनुहोस्।"
            )

        return jsonify({"ok": True})

    # DEFAULT - unrecognized message
    send_telegram_message(
        chat_id,
        "नमस्ते! 🇳🇵\n\n"
        "/start - Account जोड्नुहोस्\n"
        "/status - Status हेर्नुहोस्\n"
        "/stop - Alert बन्द गर्नुहोस्"
    )
    return jsonify({"ok": True})

# ============================================
# SET WEBHOOK ON STARTUP
# ============================================

@app.route("/set_webhook")
def set_webhook():
    app_url = "https://nepseniti.up.railway.app"
    result = set_telegram_webhook(app_url)
    return jsonify(result)

# ============================================
# HOME PAGE
# ============================================

@app.route("/")
def home():
    return render_template("index.html")

# ============================================
# SIGNUP
# ============================================

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]

        data = {
            "name": name,
            "email": email,
            "password": password,
            "alerts_enabled": False
        }

        url = f"{SUPABASE_URL}/rest/v1/Users"
        response = requests.post(url, headers=headers, json=data)

        if response.status_code in [200, 201]:
            flash("Account created! Login गर्नुहोस्।", "success")
            return redirect("/login")
        else:
            flash("Signup failed! Email already exists.", "danger")

    return render_template("signup.html")

# ============================================
# LOGIN
# ============================================

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        url = f"{SUPABASE_URL}/rest/v1/Users?email=eq.{email}&password=eq.{password}"
        response = requests.get(url, headers=headers)
        users = response.json()

        if len(users) > 0:
            session["user"] = users[0]
            return redirect("/dashboard")

        flash("Invalid email or password", "danger")

    return render_template("login.html")

# ============================================
# LOGOUT
# ============================================

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ============================================
# DASHBOARD
# ============================================

@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/login")

    user  = session["user"]
    email = user["email"]

    # Refresh user from DB for telegram status
    u_url = f"{SUPABASE_URL}/rest/v1/Users?email=eq.{email}"
    u_resp = requests.get(u_url, headers=headers)
    if u_resp.status_code == 200 and u_resp.json():
        session["user"] = u_resp.json()[0]
        user = session["user"]

    # Portfolio
    p_url  = f"{SUPABASE_URL}/rest/v1/portfolios?user_name=eq.{email}"
    p_resp = requests.get(p_url, headers=headers)
    portfolio = p_resp.json()

    # Market data (one call, reuse)
    market  = get_market_data()
    stocks  = market["stocks"]
    sectors = market["sectors"]
    overall = market["overall"]

    # Build stock lookup dict for speed
    stock_lookup = {s["s"]: s for s in stocks}

    # ── Portfolio holdings ────────────────────────────────────────────────
    total_invested = 0
    total_current  = 0
    holdings = []

    for item in portfolio:
        symbol    = item["symbol"]
        qty       = item["quantity"]
        buy_price = item["buy_price"]
        s = stock_lookup.get(symbol.upper(), {})
        ltp      = float(s.get("lp",  buy_price))
        change   = float(s.get("pc",  0))
        volume   = float(s.get("q",   0))
        open_    = float(s.get("op",  0))
        high     = float(s.get("h",   0))
        low      = float(s.get("l",   0))
        turnover = float(s.get("t",   0))

        intraday_chg = round((ltp - open_) / open_ * 100, 2) if open_ > 0 else 0
        volume_flag  = "🔥" if volume >= 50000 else ""

        invested = qty * buy_price
        current  = qty * ltp
        pnl      = current - invested
        pnl_pct  = (pnl / invested * 100) if invested > 0 else 0

        total_invested += invested
        total_current  += current

        holdings.append({
            "symbol": symbol, "qty": qty,
            "buy_price": buy_price, "ltp": ltp,
            "change": change, "high": high, "low": low,
            "volume": int(volume), "volume_flag": volume_flag,
            "intraday_chg": intraday_chg,
            "invested": invested, "current": current,
            "pnl": pnl, "pnl_pct": pnl_pct,
        })

    total_pnl     = total_current - total_invested
    total_pnl_pct = (total_pnl / total_invested * 100) if total_invested > 0 else 0

    # ── Gainers / Losers ──────────────────────────────────────────────────
    gainers = sorted(stocks, key=lambda x: float(x.get("pc", 0)), reverse=True)[:5]
    losers  = sorted(stocks, key=lambda x: float(x.get("pc", 0)))[:5]

    # ── Sector heat ───────────────────────────────────────────────────────
    total_sector_turnover = sum(float(s.get("t", 0)) for s in sectors)
    sector_heat = []
    for sec in sorted(sectors, key=lambda x: float(x.get("t", 0)), reverse=True)[:8]:
        t = float(sec.get("t", 0))
        pct = round(t / total_sector_turnover * 100, 1) if total_sector_turnover > 0 else 0
        sector_heat.append({
            "name": sec["s"],
            "turnover": t,
            "pct": pct,
        })

    # ── Market overview ───────────────────────────────────────────────────
    market_overview = {
        "total_turnover": float(overall.get("t", 0)),
        "total_volume":   overall.get("q", "0"),
        "total_txn":      overall.get("tn", "0"),
        "stocks_traded":  overall.get("st", "0"),
    }

    return render_template(
        "dashboard.html",
        user=user,
        holdings=holdings,
        total_invested=total_invested,
        total_current=total_current,
        total_pnl=total_pnl,
        total_pnl_pct=total_pnl_pct,
        gainers=gainers,
        losers=losers,
        sector_heat=sector_heat,
        market_overview=market_overview,
    )


# ============================================
# PORTFOLIO
# ============================================

@app.route("/portfolio", methods=["GET", "POST"])
def portfolio():
    if "user" not in session:
        return redirect("/login")

    user = session["user"]
    email = user["email"]

    if request.method == "POST":
        symbol = request.form["symbol"].upper()
        quantity = int(request.form["quantity"])
        buy_price = float(request.form["buy_price"])

        data = {
            "user_name": email,
            "symbol": symbol,
            "quantity": quantity,
            "buy_price": buy_price
        }

        url = f"{SUPABASE_URL}/rest/v1/portfolios"
        response = requests.post(url, headers=headers, json=data)

        if response.status_code in [200, 201]:
            flash("Stock added successfully!", "success")
        else:
            flash("Failed to add stock!", "danger")

        return redirect("/portfolio")

    url = f"{SUPABASE_URL}/rest/v1/portfolios?user_name=eq.{email}"
    response = requests.get(url, headers=headers)
    portfolio_items = response.json()

    portfolio_data = []
    total_invested = 0
    total_current = 0

    for item in portfolio_items:
        symbol = item["symbol"]
        qty = item["quantity"]
        buy_price = item["buy_price"]
        stock = get_stock_price(symbol)
        ltp = stock["ltp"]
        invested = qty * buy_price
        current = qty * ltp
        pnl = current - invested
        pnl_percent = 0
        if invested > 0:
            pnl_percent = (pnl / invested) * 100
        total_invested += invested
        total_current += current
        portfolio_data.append({
            "id": item["id"],
            "symbol": symbol,
            "qty": qty,
            "buy_price": buy_price,
            "ltp": ltp,
            "change": stock["change"],
            "invested": invested,
            "current": current,
            "pnl": pnl,
            "pnl_percent": pnl_percent
        })

    total_pnl = total_current - total_invested

    return render_template(
        "portfolio.html",
        portfolio=portfolio_data,
        total_invested=total_invested,
        total_current=total_current,
        total_pnl=total_pnl
    )

# ============================================
# DELETE STOCK
# ============================================

@app.route("/delete_stock/<int:stock_id>")
def delete_stock(stock_id):
    if "user" not in session:
        return redirect("/login")

    url = f"{SUPABASE_URL}/rest/v1/portfolios?id=eq.{stock_id}"
    requests.delete(url, headers=headers)
    flash("Stock deleted!", "success")
    return redirect("/portfolio")

# ============================================
# AI ANALYSIS
# ============================================

@app.route("/analysis")
def analysis():
    if "user" not in session:
        return redirect("/login")

    user = session["user"]
    email = user["email"]

    url = f"{SUPABASE_URL}/rest/v1/portfolios?user_name=eq.{email}"
    response = requests.get(url, headers=headers)
    portfolio = response.json()

    portfolio_text = ""
    for item in portfolio:
        symbol = item["symbol"]
        qty = item["quantity"]
        buy_price = item["buy_price"]
        stock = get_stock_price(symbol)
        ltp = stock["ltp"]
        portfolio_text += (
            f"Stock: {symbol}, Qty: {qty}, Buy Price: {buy_price}, LTP: {ltp}\n"
        )

    prompt = f"""तपाईं एक अनुभवी नेपाली शेयर बजार विश्लेषक हुनुहुन्छ।

तलको पोर्टफोलियोको नेपाली भाषामा विश्लेषण गर्नुहोस्।

{portfolio_text}

विश्लेषणमा:
- जोखिम
- राम्रो पक्ष
- कमजोर पक्ष
- दीर्घकालीन सुझाव
- छोटो निष्कर्ष

सबै कुरा नेपाली भाषामा लेख्नुहोस्।"""

    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}]
        )
        ai_text = completion.choices[0].message.content
    except Exception as e:
        ai_text = f"AI analysis failed: {str(e)}"

    return render_template("analysis.html", ai_text=ai_text, timestamp=datetime.now())

# ============================================
# NOTIFICATIONS
# ============================================

@app.route("/notifications")
def notifications():
    if "user" not in session:
        return redirect("/login")

    user = session["user"]

    # Refresh user from DB to get latest telegram status
    url = f"{SUPABASE_URL}/rest/v1/Users?email=eq.{user['email']}"
    response = requests.get(url, headers=headers)
    users = response.json()
    if users:
        session["user"] = users[0]
        user = users[0]

    return render_template("notifications.html", user=user)

# ============================================
# TEST TELEGRAM ALERT
# ============================================

@app.route("/test_alert")
def test_alert():
    if "user" not in session:
        return redirect("/login")

    user = session["user"]
    chat_id = user.get("telegram_chat_id")

    if chat_id:
        send_telegram_message(
            chat_id,
            f"✅ <b>NepseNiti Test Alert!</b>\n\nनमस्ते {user.get('name', '')}! तपाईंको Telegram सफलतापूर्वक जोडिएको छ। दैनिक ४ बजे alert आउनेछ। 🇳🇵"
        )
        flash("Test message sent to Telegram!", "success")
    else:
        flash("Telegram जोडिएको छैन। Bot मा /start गर्नुहोस्।", "danger")

    return redirect("/notifications")

# ============================================
# RUN ALERTS MANUALLY (admin use)
# ============================================

@app.route("/run_alerts")
def run_alerts():
    send_daily_alerts()
    return "Daily alerts executed!"

# ============================================
# ADMIN PAGE
# ============================================

@app.route("/admin")
def admin():
    users = get_all_users()
    return render_template("admin.html", users=users)

# ============================================
# MAIN
# ============================================

if __name__ == "__main__":
    app.run(debug=True)

