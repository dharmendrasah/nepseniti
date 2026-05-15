
from dotenv import load_dotenv
import os
from flask import Flask, render_template, request, redirect, session, url_for, flash
import requests
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from groq import Groq
import os

# ============================================
# APP CONFIG
# ============================================

app = Flask(__name__)
load_dotenv()
app.secret_key = "nepseniti-super-secret-key"

# ============================================
# YOUR CREDENTIALS
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

    return {
        "ltp": 0,
        "change": 0
    }

# ============================================
# SEND TELEGRAM MESSAGE
# ============================================

def send_telegram_message(chat_id, message):

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    data = {
        "chat_id": chat_id,
        "text": message
    }

    try:

        response = requests.post(
            url,
            data=data,
            timeout=20
        )

        print("Telegram Response:", response.text)

        return response.json()

    except Exception as e:

        print("Telegram Error:", e)

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

            response = requests.get(
                portfolio_url,
                headers=headers
            )

            portfolio_items = response.json()

            if len(portfolio_items) == 0:
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

                holdings_text += (
                    f"{symbol}: Qty {qty}, "
                    f"Buy Rs.{buy_price}, "
                    f"LTP Rs.{ltp}, "
                    f"P/L Rs.{round(pnl,2)}\n"
                )

            total_pnl = total_current - total_invested

            pnl_percent = 0

            if total_invested > 0:
                pnl_percent = (total_pnl / total_invested) * 100

            # AI PROMPT
            prompt = f"""
            तपाईं नेपाल शेयर बजारका अनुभवी विश्लेषक हुनुहुन्छ।

            तलको पोर्टफोलियोको छोटो दैनिक विश्लेषण नेपाली भाषामा गर्नुहोस्।

            पोर्टफोलियो:

            {holdings_text}

            कुल लगानी: Rs.{round(total_invested,2)}
            हालको मूल्य: Rs.{round(total_current,2)}
            कुल नाफा/नोक्सानी: Rs.{round(total_pnl,2)}

            छोटो, professional, useful analysis दिनुहोस्।

            5-8 लाइन मात्र लेख्नुहोस्।
            """

            # AI GENERATION
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            ai_text = completion.choices[0].message.content

            # FINAL TELEGRAM MESSAGE
            message = f"""
📊 NepseNiti Daily Alert

💰 Portfolio Value: Rs.{round(total_current,2)}

📈 Total P/L: Rs.{round(total_pnl,2)}
📊 Return: {round(pnl_percent,2)}%

━━━━━━━━━━━━━━

🤖 AI Analysis:

{ai_text}

━━━━━━━━━━━━━━

Thank you for using NepseNiti 🇳🇵
"""

            send_telegram_message(chat_id, message)

            print(f"Alert sent to {email}")

        except Exception as e:

            print("Alert Error:", e)

# ============================================
# SCHEDULER
# ============================================

scheduler = BackgroundScheduler()

# 4 PM NST = 15:45 UTC
scheduler.add_job(send_daily_alerts, 'cron', hour=15, minute=45)

scheduler.start()

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

        response = requests.post(
            url,
            headers=headers,
            json=data
        )

        if response.status_code in [200, 201]:

            flash("Account created successfully!", "success")
            return redirect("/login")

        else:
            flash("Signup failed!", "danger")

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

        response = requests.get(
            url,
            headers=headers
        )

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

    gainers = sorted(
        stocks,
        key=lambda x: float(x.get("pc", 0)),
        reverse=True
    )[:5]

    losers = sorted(
        stocks,
        key=lambda x: float(x.get("pc", 0))
    )[:5]

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

        response = requests.post(
            url,
            headers=headers,
            json=data
        )

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
            f"Stock: {symbol}, "
            f"Qty: {qty}, "
            f"Buy Price: {buy_price}, "
            f"LTP: {ltp}\n"
        )

    prompt = f"""
    तपाईं एक अनुभवी नेपाली शेयर बजार विश्लेषक हुनुहुन्छ।

    तलको पोर्टफोलियोको नेपाली भाषामा विश्लेषण गर्नुहोस्।

    {portfolio_text}

    विश्लेषणमा:
    - जोखिम
    - राम्रो पक्ष
    - कमजोर पक्ष
    - दीर्घकालीन सुझाव
    - छोटो निष्कर्ष

    सबै कुरा नेपाली भाषामा लेख्नुहोस्।
    """

    try:

        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        ai_text = completion.choices[0].message.content

    except Exception as e:

        ai_text = f"AI analysis failed: {str(e)}"

    return render_template(
        "analysis.html",
        ai_text=ai_text,
        timestamp=datetime.now()
    )

# ============================================
# NOTIFICATIONS
# ============================================

@app.route("/notifications", methods=["GET", "POST"])
def notifications():

    if "user" not in session:
        return redirect("/login")

    user = session["user"]

    if request.method == "POST":

        chat_id = request.form["chat_id"]

        alerts_enabled = request.form.get("alerts_enabled")

        enabled = alerts_enabled == "on"

        data = {
            "telegram_chat_id": chat_id,
            "alerts_enabled": enabled
        }

        url = f"{SUPABASE_URL}/rest/v1/Users?email=eq.{user['email']}"

        response = requests.patch(
            url,
            headers=headers,
            json=data
        )

        if response.status_code in [200, 204]:

            # UPDATE SESSION USER
            session["user"]["telegram_chat_id"] = chat_id
            session["user"]["alerts_enabled"] = enabled

            flash("Notification settings updated!", "success")

        else:
            flash("Update failed!", "danger")

    return render_template("notifications.html")

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
            "✅ NepseNiti test alert successful!"
        )

        flash("Test message sent!", "success")

    else:
        flash("Please save Telegram Chat ID first!", "danger")

    return redirect("/notifications")

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

    return render_template(
        "admin.html",
        users=users
    )

@app.route("/telegram_test")
def telegram_test():

    send_telegram_message(
        "1493102148",
        "✅ NepseNiti Telegram direct test successful!"
    )

    return "Telegram test sent!"
# ============================================
# MAIN
# ============================================

if __name__ == "__main__":
    app.run(debug=True)
