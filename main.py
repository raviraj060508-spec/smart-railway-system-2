from flask import Flask, render_template, request, redirect, session, send_file
import sqlite3, random, os
from werkzeug.security import generate_password_hash, check_password_hash
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet

app = Flask(__name__)
app.secret_key = "secure_key"

DB = "railway.db"

def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("CREATE TABLE IF NOT EXISTS users (username TEXT, password TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS tickets (pnr INTEGER, name TEXT, status TEXT, seat TEXT)")

    conn.commit()
    conn.close()

init_db()

def generate_pnr():
    return random.randint(100000, 999999)

def book_ticket(name):
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM tickets WHERE status='CONFIRMED'")
    confirmed = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM tickets WHERE status='RAC'")
    rac = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM tickets WHERE status='WAITING'")
    waiting = c.fetchone()[0]

    pnr = generate_pnr()

    if confirmed < 2:
        status = "CONFIRMED"
        seat = f"S{confirmed+1}"
    elif rac < 2:
        status = "RAC"
        seat = "RAC"
    elif waiting < 2:
        status = "WAITING"
        seat = "WL"
    else:
        return None

    c.execute("INSERT INTO tickets VALUES (?, ?, ?, ?)", (pnr, name, status, seat))
    conn.commit()
    conn.close()

    return pnr

def cancel_ticket(pnr):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("DELETE FROM tickets WHERE pnr=?", (pnr,))
    conn.commit()
    conn.close()

def get_ticket(pnr):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT * FROM tickets WHERE pnr=?", (pnr,))
    data = c.fetchone()
    conn.close()
    return data

def get_all():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT * FROM tickets")
    data = c.fetchall()
    conn.close()
    return data

def generate_pdf(ticket):
    file = f"/tmp/{ticket[0]}.pdf"
    doc = SimpleDocTemplate(file)
    styles = getSampleStyleSheet()

    content = [
        Paragraph(f"PNR: {ticket[0]}", styles['Normal']),
        Paragraph(f"Name: {ticket[1]}", styles['Normal']),
        Paragraph(f"Status: {ticket[2]}", styles['Normal']),
        Paragraph(f"Seat: {ticket[3]}", styles['Normal']),
    ]

    doc.build(content)
    return file

@app.route("/", methods=["GET","POST"])
def login():
    if request.method == "POST":
        user = request.form["username"]
        pwd = request.form["password"]

        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("SELECT password FROM users WHERE username=?", (user,))
        result = c.fetchone()
        conn.close()

        if result and check_password_hash(result[0], pwd):
            session["user"] = user
            return redirect("/dashboard")
        else:
            return "Invalid Login"

    return render_template("login.html")

@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        user = request.form["username"]
        pwd = generate_password_hash(request.form["password"])

        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("INSERT INTO users VALUES (?,?)", (user,pwd))
        conn.commit()
        conn.close()

        return redirect("/")

    return render_template("register.html")

@app.route("/dashboard", methods=["GET","POST"])
def dashboard():
    if "user" not in session:
        return redirect("/")

    message = ""

    if request.method == "POST":
        action = request.form["action"]

        if action == "book":
            pnr = book_ticket(request.form["name"])
            message = f"PNR Generated: {pnr}" if pnr else "No Tickets Available"

        elif action == "cancel":
            cancel_ticket(int(request.form["pnr"]))
            message = "Ticket Cancelled"

    data = get_all()
    return render_template("dashboard.html", data=data, message=message)

@app.route("/download/<int:pnr>")
def download(pnr):
    ticket = get_ticket(pnr)
    file = generate_pdf(ticket)
    return send_file(file, as_attachment=True)

@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect("/")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
