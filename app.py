import os
from flask import Flask, render_template_string, request, redirect, url_for, session, send_file
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'super_secret_master_key_change_this'

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['ALLOWED_EXTENSIONS'] = {'pdf', 'png', 'jpg', 'jpeg', 'docx'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            shop_name TEXT NOT NULL,
            upi_id TEXT DEFAULT 'shop@upi',
            role TEXT NOT NULL, 
            is_locked INTEGER DEFAULT 0,
            is_paid INTEGER DEFAULT 0
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id INTEGER,
            filename TEXT NOT NULL,
            filepath TEXT NOT NULL,
            color_mode TEXT,
            side_mode TEXT,
            pages INTEGER,
            copies INTEGER,
            total_price INTEGER,
            pay_method TEXT,
            payment_status TEXT DEFAULT 'Pending',
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(owner_id) REFERENCES users(id)
        )
    ''')
    
    conn.commit()
    
    cursor.execute("SELECT * FROM users WHERE role = 'admin'")
    admin_user = cursor.fetchone()
    
    new_admin_user = 'VS119'
    new_admin_pass = generate_password_hash('Vs@787800')
    
    if not admin_user:
        cursor.execute("INSERT INTO users (username, password, shop_name, role, is_locked, is_paid) VALUES (?, ?, ?, 'admin', 0, 1)",
                       (new_admin_user, new_admin_pass, 'Master Admin Panel'))
        conn.commit()
    else:
        cursor.execute("UPDATE users SET username = ?, password = ? WHERE role = 'admin'", 
                       (new_admin_user, new_admin_pass))
        conn.commit()
    
    conn.close()

init_db()

@app.route('/')
def home():
    return '''
        <!DOCTYPE html>
        <html lang="hi">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Pragya Kendra Print Kiosk Platform</title>
            <style>
                body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f0f2f5; text-align: center; padding: 40px 20px; margin: 0; }
                .card { background: white; max-width: 450px; margin: 0 auto; padding: 30px; border-radius: 16px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); text-align: left; }
                h1 { color: #1a1a1a; font-size: 24px; text-align: center; margin-bottom: 5px; }
                p.sub { color: #666; font-size: 14px; text-align: center; margin-bottom: 25px; }
                .btn { display: block; width: 100%; box-sizing: border-box; text-align: center; margin: 12px 0; padding: 12px; background: #0066ff; color: white; text-decoration: none; border-radius: 8px; font-weight: 600; font-size: 16px; transition: 0.2s; }
                .btn:hover { background: #0052cc; }
                .btn.admin { background: #dc3545; }
                .btn.admin:hover { background: #c82333; }
            </style>
        </head>
        <body>
            <div class="card">
                <h1>🖨️ Pragya Kendra Print</h1>
                <p class="sub">Digital Self-Service Kiosk SaaS</p>
                <a href="/login" class="btn">Shop Owner Login</a>
                <a href="/register" class="btn" style="background: #28a745;">Self Register (Paid ID)</a>
                <hr style="border: 0; border-top: 1px solid #eee; margin: 20px 0;">
                <a href="/login" class="btn admin">Master Admin Login</a>
            </div>
        </body>
        </html>
    '''

@app.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])
        shop_name = request.form['shop_name']
        upi_id = request.form['upi_id']
        
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO users (username, password, shop_name, upi_id, role, is_locked, is_paid) VALUES (?, ?, ?, ?, 'owner', 0, 0)",
                           (username, password, shop_name, upi_id))
            conn.commit()
            conn.close()
            return redirect(url_for('payment_gateway', uname=username))
        except sqlite3.IntegrityError:
            error = "Username already exists! Choose another."
            conn.close()
            
    err_html = f'<p class="error">{error}</p>' if error else ''
    return f'''
        <!DOCTYPE html>
        <html lang="hi">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Register - Pragya Kendra</title>
            <style>
                body {{ font-family: 'Segoe UI', sans-serif; background: #f0f2f5; padding: 30px 15px; margin: 0; }}
                .form-card {{ background: white; max-width: 420px; margin: 0 auto; padding: 25px; border-radius: 16px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); }}
                h2 {{ color: #333; text-align: center; margin-top: 0; }}
                label {{ font-weight: 600; color: #444; font-size: 14px; display: block; margin-top: 15px; }}
                input {{ width: 100%; padding: 10px; margin-top: 5px; border: 1px solid #ccc; border-radius: 8px; box-sizing: border-box; font-size: 15px; }}
                button {{ width: 100%; margin-top: 20px; padding: 12px; background: #28a745; color: white; border: none; border-radius: 8px; font-size: 16px; font-weight: bold; cursor: pointer; }}
                .back {{ display: block; text-align: center; margin-top: 15px; color: #0066ff; text-decoration: none; font-size: 14px; }}
                .error {{ color: red; text-align: center; font-size: 14px; }}
            </style>
        </head>
        <body>
            <div class="form-card">
                <h2>📝 नया प्रज्ञा केंद्र रजिस्टर करें</h2>
                {err_html}
                <form method="POST">
                    <label>दुकान का नाम (Shop Name):</label>
                    <input type="text" name="shop_name" required>
                    <label>दुकान की UPI ID:</label>
                    <input type="text" name="upi_id" placeholder="jaise: dukaan@ybl" required>
                    <label>यूजरनेम:</label>
                    <input type="text" name="username" required>
                    <label>पासवर्ड:</label>
                    <input type="password" name="password" required>
                    <button type="submit">रजिस्टर करें & पेमेंट आगे बढ़ाएं</button>
                </form>
                <a href="/" class="back">← होम पेज पर वापस जाएं</a>
            </div>
        </body>
        </html>
    '''

@app.route('/payment-gateway/<uname>', methods=['GET', 'POST'])
def payment_gateway(uname):
    if request.method == 'POST':
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET is_paid = 1 WHERE username = ?", (uname,))
        conn.commit()
        conn.close()
        return redirect(url_for('login'))
        
    return f'''
        <!DOCTYPE html>
        <html lang="hi">
        <head>
            <meta charset="UTF-8">
            <title>Activation Payment</title>
            <style>
                body {{ font-family: 'Segoe UI', sans-serif; background: #f0f2f5; text-align: center; padding: 40px; }}
                .card {{ background: white; max-width: 400px; margin: 0 auto; padding: 30px; border-radius: 16px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); }}
                .btn {{ display: inline-block; margin-top: 20px; padding: 12px 25px; background: #28a745; color: white; border-radius: 8px; text-decoration: none; font-weight: bold; cursor: pointer; border: none; }}
            </style>
        </head>
        <body>
            <div class="card">
                <h2>💳 सॉफ्टवेयर एक्टिवेशन फीस</h2>
                <p>अपनी दुकान की ID एक्टिवेट करने के लिए ₹99 का ऑनलाइन भुगतान करें:</p>
                <img src="https://api.qrserver.com/v1/create-qr-code/?size=160x160&data=upi://pay?pa=admin@upi&pn=PlatformAdmin&am=99&cu=INR" alt="Admin QR" style="border-radius: 8px; border: 1px solid #ddd; margin: 15px 0;">
                <p style="font-size: 13px; color: #666;">पेमेंट पूरा होने के बाद नीचे दिए गए बटन पर क्लिक करें:</p>
                <form method="POST">
                    <button type="submit" class="btn">✅ मैंने पेमेंट कर दिया है (Activate ID)</button>
                </form>
            </div>
        </body>
        </html>
    '''

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id, password, role, is_locked, shop_name, is_paid FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        conn.close()
        
        if user and check_password_hash(user[1], password):
            if user[3] == 1:
                error = "आपका अकाउंट लॉक कर दिया गया है।"
            elif user[2] == 'owner' and user[5] == 0:
                return redirect(url_for('payment_gateway', uname=username))
            else:
                session['user_id'] = user[0]
                session['role'] = user[2]
                session['shop_name'] = user[4]
                
                if user[2] == 'admin':
                    return redirect(url_for('super_admin'))
                else:
                    return redirect(url_for('dashboard'))
        else:
            error = "गलत यूजरनेम या पासवर्ड!"
            
    err_html = f'<p class="error">{error}</p>' if error else ''
    return f'''
        <!DOCTYPE html>
        <html lang="hi">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Login - Kiosk System</title>
            <style>
                body {{ font-family: 'Segoe UI', sans-serif; background: #f0f2f5; padding: 40px 15px; margin: 0; }}
                .form-card {{ background: white; max-width: 400px; margin: 0 auto; padding: 25px; border-radius: 16px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); }}
                h2 {{ color: #333; text-align: center; margin-top: 0; }}
                label {{ font-weight: 600; color: #444; font-size: 14px; display: block; margin-top: 15px;
