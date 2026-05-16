

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
    "NABIL":"Banking","NBL":"Banking","NICA":"Banking","EBL":"Banking",
    "SBI":"Banking","SANIMA":"Banking","MBL":"Banking","CBL":"Banking",
    "PRVU":"Banking","KBL":"Banking","SRBL":"Banking","GBIME":"Banking",
    "HBL":"Banking","NIMB":"Banking","NMB":"Banking","PCBL":"Banking",
    "SBL":"Banking","ADBL":"Banking","CZBIL":"Banking","LSL":"Banking",
    "BOKL":"Banking","MEGA":"Banking","CCBL":"Banking","JBNL":"Banking",
    "NABBC":"Banking","RBB":"Banking","NBB":"Banking",
    # Development Banks
    "FMDBL":"Development Bank","NWCL":"Development Bank","MLBL":"Development Bank",
    "SADBL":"Development Bank","EDBL":"Development Bank","MNBBL":"Development Bank",
    "CORBL":"Development Bank","SAPDBL":"Development Bank","KSBBL":"Development Bank",
    "SHINE":"Development Bank","SINDU":"Development Bank","HAMRO":"Development Bank",
    # Finance
    "HFIN":"Finance","SIFC":"Finance","UFL":"Finance","GFCL":"Finance",
    "MFIL":"Finance","PFL":"Finance","ICFC":"Finance","CFCL":"Finance",
    "RLFL":"Finance","JFL":"Finance","SFCL":"Finance","BESTL":"Finance",
    # Hydropower
    "NHDL":"Hydropower","NHPC":"Hydropower","UPPER":"Hydropower","RIDI":"Hydropower",
    "AKPL":"Hydropower","RHPC":"Hydropower","RADHI":"Hydropower","SHL":"Hydropower",
    "UHEWA":"Hydropower","MAKAR":"Hydropower","KPCL":"Hydropower","HPPL":"Hydropower",
    "PMHPL":"Hydropower","BPCL":"Hydropower","GHL":"Hydropower","API":"Hydropower",
    "NYADI":"Hydropower","DHPL":"Hydropower","DOLTI":"Hydropower","RKPCL":"Hydropower",
    # Insurance
    "NLIC":"Insurance","LICN":"Insurance","ALICL":"Insurance","GILC":"Insurance",
    "SLICL":"Insurance","NICL":"Insurance","PICL":"Insurance","SICL":"Insurance",
    "HGICL":"Insurance","RBCL":"Insurance","SGIC":"Insurance","SPICL":"Insurance",
    "PRIN":"Insurance","AIL":"Insurance","NLG":"Insurance","IGI":"Insurance",
    # Microfinance
    "NCLBSL":"Microfinance","CBBL":"Microfinance","MLBSL":"Microfinance",
    "SWBBL":"Microfinance","ILBS":"Microfinance","DDBL":"Microfinance",
    "SKBBL":"Microfinance","SMFBS":"Microfinance","NESDO":"Microfinance",
    "NICLBSL":"Microfinance","KMCDB":"Microfinance","MERO":"Microfinance",
    # Others
    "NTC":"Telecom","NIFRA":"Infrastructure","CIT":"Investment","NIBL":"Banking",
    "CHCL":"Hydropower","PLIC":"Insurance","VLBS":"Microfinance",
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
            stocks = data.get("turnover", {}).get("detail", [])
            return stocks
        return []
    except Exception as e:
        print("Market data error:", e)
        return []

# ============================================
# GET STOCK PRICE
# ============================================

def get_stock_price(symbol):
    stocks = get_market_data()
    for stock in stocks:
        if stock.get("s") == symbol.upper():
            return {
                "ltp": float(stock.get("lp", 0)),
                "change": float(stock.get("pc", 0)),
                "high": stock.get("h", 0),
                "low": stock.get("l", 0),
                "volume": stock.get("q", 0)
            }
    return {"ltp": 0, "change": 0}

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

    user = session["user"]
    email = user["email"]

    url = f"{SUPABASE_URL}/rest/v1/portfolios?user_name=eq.{email}"
    response = requests.get(url, headers=headers)
    portfolio = response.json()

    total_invested = 0
    total_current = 0
    holdings = []

    for item in portfolio:
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
        holdings.append({
            "symbol": symbol,
            "qty": qty,
            "buy_price": buy_price,
            "ltp": ltp,
            "invested": invested,
            "current": current,
            "pnl": pnl,
            "pnl_percent": pnl_percent,
            "change": stock["change"]
        })

    total_pnl = total_current - total_invested

    stocks = get_market_data()
    gainers = sorted(stocks, key=lambda x: float(x.get("pc", 0)), reverse=True)[:5]
    losers = sorted(stocks, key=lambda x: float(x.get("pc", 0)))[:5]

    return render_template(
        "dashboard.html",
        user=user,
        holdings=holdings,
        total_invested=total_invested,
        total_current=total_current,
        total_pnl=total_pnl,
        gainers=gainers,
        losers=losers
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

    if not portfolio:
        return render_template("analysis.html", ai_text="Portfolio खाली छ। पहिले stocks थप्नुहोस्।", timestamp=datetime.now(), portfolio_data=[])

    # ── Build rich stock context ──────────────────────────────────────────
    portfolio_data = []
    sector_summary = {}
    total_invested = 0
    total_current = 0

    for item in portfolio:
        symbol  = item["symbol"]
        qty     = item["quantity"]
        buy_price = item["buy_price"]
        stock   = get_stock_price(symbol)
        ltp     = stock["ltp"] if stock["ltp"] > 0 else buy_price
        change  = stock["change"]
        invested = qty * buy_price
        current  = qty * ltp
        pnl      = current - invested
        pnl_pct  = (pnl / invested * 100) if invested > 0 else 0
        sector   = SECTOR_MAP.get(symbol.upper(), "Other")

        total_invested += invested
        total_current  += current

        # sector grouping
        if sector not in sector_summary:
            sector_summary[sector] = {"invested": 0, "current": 0, "stocks": []}
        sector_summary[sector]["invested"] += invested
        sector_summary[sector]["current"]  += current
        sector_summary[sector]["stocks"].append(symbol)

        # signal logic
        if pnl_pct >= 20:
            signal = "SELL ✅"
            signal_reason = "२०%+ नाफा भयो — आंशिक मुनाफा लिन सकिन्छ"
        elif pnl_pct <= -15:
            signal = "REVIEW ⚠️"
            signal_reason = "१५%+ घाटा छ — कारण विश्लेषण गर्नुहोस्"
        elif -5 <= pnl_pct <= 5 and change >= 0:
            signal = "HOLD 🟡"
            signal_reason = "स्थिर छ — थप जानकारी हेर्नुहोस्"
        elif change >= 3:
            signal = "HOLD 🟡"
            signal_reason = "आज राम्रो गति छ"
        elif change <= -3:
            signal = "WATCH 👁️"
            signal_reason = "आज घटेको छ — ट्रेन्ड हेर्नुहोस्"
        else:
            signal = "HOLD 🟡"
            signal_reason = "सामान्य अवस्थामा छ"

        portfolio_data.append({
            "symbol":   symbol,
            "qty":      qty,
            "buy_price": buy_price,
            "ltp":      ltp,
            "change":   change,
            "invested": invested,
            "current":  current,
            "pnl":      pnl,
            "pnl_pct":  pnl_pct,
            "sector":   sector,
            "signal":   signal,
            "signal_reason": signal_reason,
        })

    total_pnl = total_current - total_invested
    total_pnl_pct = (total_pnl / total_invested * 100) if total_invested > 0 else 0

    # ── Build sector text for prompt ─────────────────────────────────────
    sector_text = ""
    for sec, data in sector_summary.items():
        sec_pnl = data["current"] - data["invested"]
        sec_pct = (sec_pnl / data["invested"] * 100) if data["invested"] > 0 else 0
        sector_text += f"- {sec}: {', '.join(data['stocks'])} → {'नाफा' if sec_pnl >= 0 else 'घाटा'} Rs.{round(sec_pnl, 0)} ({round(sec_pct, 1)}%)\n"

    # ── Build per-stock text for prompt ──────────────────────────────────
    stock_text = ""
    for p in portfolio_data:
        stock_text += (
            f"• {p['symbol']} ({p['sector']}): {p['qty']} कित्ता, "
            f"खरिद Rs.{p['buy_price']}, LTP Rs.{p['ltp']}, "
            f"आजको परिवर्तन {p['change']}%, "
            f"नाफा/घाटा Rs.{round(p['pnl'],0)} ({round(p['pnl_pct'],1)}%), "
            f"संकेत: {p['signal']}\n"
        )

    # ── Smart Nepali prompt ───────────────────────────────────────────────
    prompt = f"""तपाईं नेपाल शेयर बजारका एक अनुभवी र विश्वसनीय विश्लेषक हुनुहुन्छ। तपाईं सधैं नेपाली भाषामा स्पष्ट, व्यावहारिक र intelligent सुझाव दिनुहुन्छ।

===== पोर्टफोलियो विवरण =====
{stock_text}

===== Sector Analysis =====
{sector_text}

===== कुल अवस्था =====
कुल लगानी: Rs.{round(total_invested, 0)}
हालको मूल्य: Rs.{round(total_current, 0)}
कुल नाफा/घाटा: Rs.{round(total_pnl, 0)} ({round(total_pnl_pct, 1)}%)

===== तपाईंको काम =====
तलका ३ भाग मा नेपाली भाषामा smart analysis दिनुहोस्:

**१. प्रत्येक Stock को निर्णय:**
प्रत्येक stock को लागि एउटा line मा लेख्नुहोस्:
[SYMBOL] → [राख्नुहोस् / बेच्नुहोस् / थप किन्नुहोस् / हेर्नुहोस्] — [१ line मा कारण]

**२. Sector Analysis:**
कुन sector राम्रो छ र कुन कमजोर छ — specific कारण सहित।

**३. Overall Strategy:**
यो पोर्टफोलियोको लागि अहिले के गर्नु पर्छ? — ३-४ वटा concrete action points नेपालीमा।

सबै कुरा नेपाली भाषामा लेख्नुहोस्। Bold headings राख्नुहोस्। Generic कुरा नलेख्नुहोस् — specific stock names र numbers प्रयोग गर्नुहोस्।"""

    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1500,
            temperature=0.7,
        )
        ai_text = completion.choices[0].message.content
    except Exception as e:
        ai_text = f"AI analysis failed: {str(e)}"

    return render_template(
        "analysis.html",
        ai_text=ai_text,
        timestamp=datetime.now(),
        portfolio_data=portfolio_data,
        total_invested=total_invested,
        total_current=total_current,
        total_pnl=total_pnl,
        total_pnl_pct=total_pnl_pct,
    )



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

