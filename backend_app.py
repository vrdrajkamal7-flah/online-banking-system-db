from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import smtplib
import random
import time
import os
import re
import socket
import json
from email.message import EmailMessage

# The frontend HTML file (index.html) should sit in the SAME folder as this
# backend_app.py file when you deploy both together as one service.
FRONTEND_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="")
# CORS is still enabled here in case you ever split the frontend out again,
# but when both are served from this same Flask app you don't need it —
# same-origin requests never hit CORS rules at all.
CORS(app)

SMTP_EMAIL = os.environ.get("SMTP_EMAIL")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD")

# Demo/server memory store. For production, use a database or Redis.
otp_storage = {}

OTP_VALID_SECONDS = 30
MAX_RESENDS = 5
COOLDOWN_AFTER_LIMIT = 24 * 60 * 60


def valid_email(email):
    return bool(re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", str(email or "").strip()))


def email_domain_has_mx(email):
    """Best-effort domain check. It cannot prove an individual mailbox exists."""
    domain = email.rsplit("@", 1)[1].lower()
    try:
        import dns.resolver
        answers = dns.resolver.resolve(domain, "MX", lifetime=5)
        return len(list(answers)) > 0
    except Exception:
        try:
            socket.gethostbyname(domain)
            return True
        except Exception:
            return False


def smtp_recipient_check(email):
    """Best-effort SMTP mailbox check. Some providers intentionally hide mailbox status."""
    domain = email.rsplit("@", 1)[1].lower()
    hosts = []
    try:
        import dns.resolver
        answers = dns.resolver.resolve(domain, "MX", lifetime=5)
        hosts = [str(r.exchange).rstrip(".") for r in sorted(answers, key=lambda x: x.preference)]
    except Exception:
        hosts = []

    if not hosts:
        return False

    for host in hosts[:3]:
        try:
            with smtplib.SMTP(host, 25, timeout=8) as server:
                server.ehlo_or_helo_if_needed()
                code, _ = server.mail(SMTP_EMAIL)
                if code >= 400:
                    continue
                code, _ = server.rcpt(email)
                if code in (250, 251):
                    return True
                if code in (550, 551, 552, 553):
                    return False
        except Exception:
            continue
    return None


def email_appears_valid(email):
    """Return True/False/None. None means the provider did not expose mailbox status."""
    if not email_domain_has_mx(email):
        return False
    return smtp_recipient_check(email)


def generate_otp():
    return f"{random.SystemRandom().randint(0, 999999):06d}"


def send_email_otp(receiver_email, otp):
    message = EmailMessage()
    message["Subject"] = "Your Online Banking System OTP"
    message["From"] = SMTP_EMAIL
    message["To"] = receiver_email
    message.set_content(
        f"Your OTP is {otp}\n\n"
        f"This OTP is valid for {OTP_VALID_SECONDS} seconds.\n\n"
        "If you did not request this OTP, please ignore this email.\n"
    )

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(SMTP_EMAIL, SMTP_PASSWORD)
        server.send_message(message)


@app.get("/")
def home():
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_path):
        return send_from_directory(FRONTEND_DIR, "index.html")
    return "Gmail OTP Backend Running (index.html not found next to backend_app.py)"


@app.get("/health")
def health():
    return jsonify({"ok": True, "service": "gmail-otp", "smtp_configured": bool(SMTP_EMAIL and SMTP_PASSWORD)})


@app.post("/send-otp")
def send_otp():
    data = request.get_json(silent=True) or {}
    email = str(data.get("email") or "").strip().lower()
    is_resend = bool(data.get("resend", False))

    if not valid_email(email):
        return jsonify({"success": False, "message": "Invalid Email ID."}), 400

    mailbox_check = email_appears_valid(email)
    if mailbox_check is False:
        return jsonify({"success": False, "message": "Invalid Email ID."}), 400

    now = time.time()
    record = otp_storage.get(email)

    if record and now < record.get("locked_until", 0):
        hours = max(1, int((record["locked_until"] - now) / 3600))
        return jsonify({
            "success": False,
            "message": f"You have reached the limit try after 24 hours"
        }), 429

    if record and record.get("locked_until", 0) and now >= record["locked_until"]:
        record = None
        otp_storage.pop(email, None)

    if is_resend:
        if not record:
            return jsonify({"success": False, "message": "OTP session not found. Click Send OTP to Gmail."}), 400
        if record.get("locked_until", 0) and now < record["locked_until"]:
            return jsonify({"success": False, "message": "You have reached the limit try after 24 hours"}), 429
        if record.get("resend_count", 0) >= MAX_RESENDS:
            record["locked_until"] = now + COOLDOWN_AFTER_LIMIT
            return jsonify({"success": False, "message": "You have reached the limit try after 24 hours"}), 429
        resend_count = record.get("resend_count", 0) + 1
        window_started = record.get("window_started", now)
    else:
        if record:
            window_started = record.get("window_started", now)
            if now - window_started < COOLDOWN_AFTER_LIMIT and record.get("resend_count", 0) >= MAX_RESENDS:
                return jsonify({"success": False, "message": "You have reached the limit try after 24 hours"}), 429
            if now - window_started >= COOLDOWN_AFTER_LIMIT:
                resend_count = 0
                window_started = now
            else:
                resend_count = record.get("resend_count", 0)
        else:
            resend_count = 0
            window_started = now

    otp = generate_otp()
    record = {
        "otp": otp,
        "expires": now + OTP_VALID_SECONDS,
        "resend_count": resend_count,
        "window_started": window_started,
        "locked_until": 0,
    }
    otp_storage[email] = record

    try:
        send_email_otp(email, otp)
        return jsonify({
            "success": True,
            "message": "OTP sent successfully",
            "expires_in": OTP_VALID_SECONDS,
            "resend_count": resend_count,
            "max_resends": MAX_RESENDS,
        })
    except smtplib.SMTPAuthenticationError:
        otp_storage.pop(email, None)
        print("Email error: Gmail SMTP authentication failed")
        return jsonify({"success": False, "message": "Gmail SMTP authentication failed. Use a Gmail App Password and check SMTP_EMAIL/SMTP_PASSWORD on the backend."}), 500
    except (smtplib.SMTPException, OSError) as exc:
        otp_storage.pop(email, None)
        print("Email error:", repr(exc))
        return jsonify({"success": False, "message": "Gmail could not send the OTP. Check SMTP_EMAIL, Gmail App Password, and backend logs."}), 500
    except Exception as exc:
        otp_storage.pop(email, None)
        print("Email error:", repr(exc))
        return jsonify({"success": False, "message": "Unexpected backend error while sending OTP. Check backend logs."}), 500


@app.post("/verify-otp")
def verify_otp():
    data = request.get_json(silent=True) or {}
    email = str(data.get("email") or "").strip().lower()
    entered_otp = str(data.get("otp") or "").strip()

    if not valid_email(email):
        return jsonify({"success": False, "message": "Invalid email ID."}), 400
    if not re.fullmatch(r"\d{6}", entered_otp):
        return jsonify({"success": False, "message": "OTP must contain 6 digits."}), 400

    record = otp_storage.get(email)
    if not record:
        return jsonify({"success": False, "message": "OTP not found. Click Resend OTP."}), 400

    now = time.time()
    if now > record["expires"]:
        # Keep resend_count so the 5-resend limit cannot be bypassed by expiration.
        return jsonify({"success": False, "message": "Invalid OTP. OTP expired after 30 seconds. Click Resend OTP."}), 400

    if entered_otp != record["otp"]:
        return jsonify({"success": False, "message": "Invalid OTP"}), 400

    del otp_storage[email]
    return jsonify({"success": True, "message": "OTP verified successfully"})



# ---------------- ORACLE DATABASE ----------------
try:
    import oracledb
except ImportError:
    oracledb = None

ORACLE_USER = os.environ.get('ORACLE_USER')
ORACLE_PASSWORD = os.environ.get('ORACLE_PASSWORD')
ORACLE_DSN = os.environ.get('ORACLE_DSN', 'localhost:1521/XEPDB1')

def oracle_configured():
    return bool(oracledb and ORACLE_USER and ORACLE_PASSWORD and ORACLE_DSN)

def oracle_connection():
    if not oracle_configured():
        raise RuntimeError('Oracle is not configured. Set ORACLE_USER, ORACLE_PASSWORD and ORACLE_DSN.')
    return oracledb.connect(user=ORACLE_USER, password=ORACLE_PASSWORD, dsn=ORACLE_DSN)

def state_payload(data):
    return {'nextAccountNumber':data.get('nextAccountNumber',[]),'accounts':data.get('accounts',[]),'users':data.get('users',[]),'transactions':data.get('transactions',[]),'kycRequests':data.get('kycRequests',[])}

@app.get('/api/db-test')
def db_test():
    try:
        with oracle_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('select 1 from dual'); cur.fetchone()
        return jsonify({'ok':True,'database':'Oracle','connected':True})
    except Exception as exc:
        return jsonify({'ok':False,'database':'Oracle','connected':False,'message':str(exc)}),500

@app.get('/api/state')
def get_state():
    try:
        with oracle_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('select state_json from ob_state where state_id=1')
                row=cur.fetchone()
                if not row: return jsonify({'ok':True,'state':None})
                value=row[0].read() if hasattr(row[0],'read') else row[0]
                return jsonify({'ok':True,'state':json.loads(value)})
    except Exception as exc:
        return jsonify({'ok':False,'message':str(exc)}),500

def save_normalized(cur,data):
    cur.execute('delete from ob_transactions'); cur.execute('delete from ob_kyc'); cur.execute('delete from ob_accounts'); cur.execute('delete from ob_users')
    for u in data.get('users',[]):
        cur.execute("insert into ob_users(email,mobile,password_text,kyc_status) values(:1,:2,:3,:4)",[str(u.get('email','')).lower(),str(u.get('mobile','')),str(u.get('password','')),str(u.get('kycStatus','not-started'))])
    for a in data.get('accounts',[]):
        try: bank_code=['IND','SBI','AXIS','HDFC','IDFC','ICICI'][int(a.get('bank',0))]
        except Exception: bank_code=str(a.get('bank',''))
        cur.execute("insert into ob_accounts(account_number,user_email,name,company_name,mobile,email,pin_text,balance,bank_code,account_type,blocked,kyc_status) values(:1,:2,:3,:4,:5,:6,:7,:8,:9,:10,:11,:12)",[str(a.get('acn','')),'',str(a.get('name','')),str(a.get('companyName','')),str(a.get('mobile','')),str(a.get('email','')),str(a.get('pin','')),float(a.get('bal',0) or 0),bank_code,str(a.get('accountType','self')),int(bool(a.get('blocked',0))),str(a.get('kycStatus','not-started'))])
    for t in data.get('transactions',[]):
        cur.execute("insert into ob_transactions(sender_account,receiver_account,amount,tx_date,tx_time) values(:1,:2,:3,:4,:5)",[str(t.get('sender','')),str(t.get('receiver','')),float(t.get('amount',0) or 0),str(t.get('date','')),str(t.get('time',''))])
    for k in data.get('kycRequests',[]):
        try: bank_code=['IND','SBI','AXIS','HDFC','IDFC','ICICI'][int(k.get('bank',0))]
        except Exception: bank_code=str(k.get('bank',''))
        sub=k.get('submittedAt') or {}
        cur.execute("insert into ob_kyc(mobile,bank_code,status,submitted_date,submitted_time) values(:1,:2,:3,:4,:5)",[str(k.get('mobile','')),bank_code,str(k.get('status','pending')),str(sub.get('date','')),str(sub.get('time',''))])

@app.post('/api/state')
def put_state():
    data=state_payload(request.get_json(silent=True) or {})
    try:
        raw=json.dumps(data,separators=(',',':'))
        with oracle_connection() as conn:
            with conn.cursor() as cur:
                save_normalized(cur,data)
                cur.execute('delete from ob_state where state_id=1')
                cur.execute('insert into ob_state(state_id,state_json,updated_at) values(1,:1,systimestamp)',[raw])
            conn.commit()
        return jsonify({'ok':True})
    except Exception as exc:
        return jsonify({'ok':False,'message':str(exc)}),500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=False)
