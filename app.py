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
                label {{ font-weight: 600; color: #444; font-size: 14px; display: block; margin-top: 15px; }}
                input {{ width: 100%; padding: 10px; margin-top: 5px; border: 1px solid #ccc; border-radius: 8px; box-sizing: border-box; font-size: 15px; }}
                button {{ width: 100%; margin-top: 20px; padding: 12px; background: #0066ff; color: white; border: none; border-radius: 8px; font-size: 16px; font-weight: bold; cursor: pointer; }}
                .back {{ display: block; text-align: center; margin-top: 15px; color: #0066ff; text-decoration: none; font-size: 14px; }}
                .error {{ color: red; text-align: center; font-size: 14px; }}
            </style>
        </head>
        <body>
            <div class="form-card">
                <h2>🔐 कियोस्क लॉगिन</h2>
                {err_html}
                <form method="POST">
                    <label>यूजरनेम:</label>
                    <input type="text" name="username" required>
                    <label>पासवर्ड:</label>
                    <input type="password" name="password" required>
                    <button type="submit">लॉगिन करें</button>
                </form>
                <a href="/" class="back">← होम पेज पर वापस जाएं</a>
            </div>
        </body>
        </html>
    '''

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user_id' not in session or session['role'] != 'owner':
        return redirect(url_for('login'))
    
    owner_id = session['user_id']
    shop_name = session['shop_name']
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    if request.method == 'POST' and 'update_upi' in request.form:
        new_upi = request.form['upi_id']
        cursor.execute("UPDATE users SET upi_id = ? WHERE id = ?", (new_upi, owner_id))
        conn.commit()
        
    cursor.execute("SELECT upi_id FROM users WHERE id = ?", (owner_id,))
    upi_row = cursor.fetchone()
    upi_id = upi_row[0] if upi_row else 'shop@upi'
    
    cursor.execute("SELECT id, filename, color_mode, side_mode, pages, copies, total_price, pay_method, payment_status, timestamp FROM files WHERE owner_id = ? ORDER BY id DESC", (owner_id,))
    files = cursor.fetchall()
    conn.close()
    
    upload_link = request.host_url + f"upload/{owner_id}"
    
    rows_html = ""
    for f in files:
        status_badge = '<span style="color: #28a745; font-weight: bold;">✓ Approved</span>' if f[8] == 'Verified' else f'<span style="color: #e67e22; font-weight: bold;">⌛ Pending Approval</span><br><a href="/approve-order/{f[0]}" style="display:inline-block; padding:4px 8px; background:#ffc107; color:#000; border-radius:4px; text-decoration:none; font-size:12px; font-weight:bold; margin-top:4px;">✅ Approve Order</a>'
        print_action = f'<a href="/print-file/{f[0]}" target="_blank" style="display:inline-block; padding:6px 12px; background:#28a745; color:white; border-radius:4px; text-decoration:none; font-size:12px; font-weight:bold;">🖨️ प्रिंट करें</a>' if f[8] == 'Verified' else '<span style="color: #888; font-size: 12px;">Waiting Approval</span>'
        
        rows_html += f'''
            <tr>
                <td>{f[0]}</td>
                <td>{f[1]}</td>
                <td>{f[2].upper()} | {f[3].replace('_', ' ').title()} | P: {f[4]} | C: {f[5]}</td>
                <td><b>{f[7].upper()}</b></td>
                <td><b>₹{f[6]}</b></td>
                <td>{status_badge}</td>
                <td>{print_action}</td>
            </tr>
        '''
    if not files:
        rows_html = '<tr><td colspan="7" style="text-align: center; color: #777;">अभी तक कोई आर्डर नहीं आया है।</td></tr>'

    return f'''
        <!DOCTYPE html>
        <html lang="hi">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{shop_name} - Dashboard</title>
            <style>
                body {{ font-family: 'Segoe UI', sans-serif; background: #f8f9fa; padding: 20px; margin: 0; }}
                .container {{ max-width: 1050px; margin: 0 auto; background: white; padding: 25px; border-radius: 16px; box-shadow: 0 4px 20px rgba(0,0,0,0.06); }}
                .header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #eee; padding-bottom: 15px; margin-bottom: 20px; }}
                h2, h3 {{ color: #333; margin-top: 0; }}
                .logout {{ background: #dc3545; color: white; padding: 8px 16px; text-decoration: none; border-radius: 6px; font-weight: bold; font-size: 14px; }}
                input[type="text"] {{ padding: 8px; width: 300px; border: 1px solid #ccc; border-radius: 6px; font-size: 14px; }}
                button {{ padding: 8px 15px; background: #0066ff; color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: bold; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 14px; }}
                th, td {{ border: 1px solid #dee2e6; padding: 10px; text-align: left; }}
                th {{ background: #f1f3f5; color: #333; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>🖥️ {shop_name} (डैशबोर्ड)</h2>
                    <a href="/logout" class="logout">लॉग आउट</a>
                </div>
                
                <h3>💳 दुकान की UPI ID सेटिंग:</h3>
                <form method="POST">
                    <input type="text" name="upi_id" value="{upi_id}" required>
                    <button type="submit" name="update_upi" value="1">अपडेट करें</button>
                </form>
                <hr style="border: 0; border-top: 1px solid #eee; margin: 20px 0;">
                
                <h3>📱 ग्राहक QR कोड और लिंक:</h3>
                <input type="text" value="{upload_link}" style="width: 450px;" readonly>
                <p><a href="https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={upload_link}" target="_blank" style="color: #0066ff; font-weight: bold;">🔗 QR कोड देखें</a></p>
                <hr style="border: 0; border-top: 1px solid #eee; margin: 20px 0;">
                
                <h3>📥 ग्राहकों के प्रिंट ऑर्डर लिस्ट:</h3>
                <table>
                    <tr>
                        <th>ID</th>
                        <th>फाइल का नाम</th>
                        <th>प्रिंट सेटिंग्स</th>
                        <th>मोड</th>
                        <th>कुल बिल</th>
                        <th>स्टेटस</th>
                        <th>प्रिंट / एक्शन</th>
                    </tr>
                    {rows_html}
                </table>
            </div>
        </body>
        </html>
    '''

@app.route('/approve-order/<int:file_id>')
def approve_order(file_id):
    if 'user_id' not in session or session['role'] != 'owner':
        return redirect(url_for('login'))
        
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE files SET payment_status = 'Verified' WHERE id = ? AND owner_id = ?", (file_id, session['user_id']))
    conn.commit()
    conn.close()
    return redirect(url_for('dashboard'))

@app.route('/print-file/<int:file_id>')
def print_file(file_id):
    if 'user_id' not in session or session['role'] != 'owner':
        return redirect(url_for('login'))
        
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT filename, filepath, owner_id, payment_status FROM files WHERE id = ?", (file_id,))
    f = cursor.fetchone()
    conn.close()
    
    if f and f[2] == session['user_id']:
        if f[3] != 'Verified':
            return "<h3>ऑर्डर अभी अप्रूव नहीं हुआ है!</h3>", 403
        
        return f'''
            <!DOCTYPE html>
            <html lang="hi">
            <head>
                <meta charset="UTF-8">
                <title>Print Document - {f[0]}</title>
                <style>
                    body {{ font-family: sans-serif; text-align: center; padding: 40px; background: #f8f9fa; }}
                    .print-box {{ background: white; max-width: 600px; margin: 0 auto; padding: 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }}
                    .btn {{ padding: 12px 25px; background: #0066ff; color: white; border: none; border-radius: 6px; font-size: 16px; font-weight: bold; cursor: pointer; text-decoration: none; display: inline-block; margin: 10px; }}
                    .btn-print {{ background: #28a745; }}
                    @media print {{ .no-print {{ display: none; }} }}
                </style>
            </head>
            <body>
                <div class="print-box">
                    <h2>🖨️ Printer Ready: {f[0]}</h2>
                    <p>प्रिन्टर से प्रिंट निकालने के लिए नीचे दिए गए बटन पर क्लिक करें:</p>
                    <div class="no-print">
                        <button onclick="window.print()" class="btn btn-print">🖨️ Print Now (प्रिंट खोलें)</button>
                        <a href="/download-raw/{file_id}" class="btn">📥 Download File</a>
                    </div>
                </div>
                <script>
                    window.onload = function() {{
                        setTimeout(function() {{ window.print(); }}, 500);
                    }}
                </script>
            </body>
            </html>
        '''
    return "Unauthorized", 403

@app.route('/download-raw/<int:file_id>')
def download_raw(file_id):
    if 'user_id' not in session or session['role'] != 'owner':
        return redirect(url_for('login'))
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT filepath, owner_id FROM files WHERE id = ?", (file_id,))
    f = cursor.fetchone()
    conn.close()
    if f and f[1] == session['user_id']:
        return send_file(f[0], as_attachment=True)
    return "Unauthorized", 403

@app.route('/super-admin', methods=['GET', 'POST'])
def super_admin():
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
        
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    msg = ""
    if request.method == 'POST' and 'create_shop' in request.form:
        s_name = request.form['shop_name']
        s_user = request.form['username']
        s_pass = generate_password_hash(request.form['password'])
        s_upi = request.form['upi_id']
        try:
            cursor.execute("INSERT INTO users (username, password, shop_name, upi_id, role, is_locked, is_paid) VALUES (?, ?, ?, ?, 'owner', 0, 1)",
                           (s_user, s_pass, s_name, s_upi))
            conn.commit()
            msg = "✅ दुकान की ID सफलतापूर्वक बन गई!"
        except sqlite3.IntegrityError:
            msg = "❌ यह यूजरनेम पहले से मौजूद है!"

    cursor.execute("SELECT id, username, shop_name, is_locked, is_paid FROM users WHERE role = 'owner'")
    owners = cursor.fetchall()
    conn.close()
    
    owners_html = ""
    for owner in owners:
        act_status = '<span style="color:green; font-weight: bold;">Paid / Active</span>' if owner[4] == 1 else '<span style="color:orange; font-weight: bold;">Unpaid / Pending</span>'
        lock_status = '<span style="color:red; font-weight: bold;">Locked</span>' if owner[3] == 1 else '<span style="color:green; font-weight: bold;">Active</span>'
        lock_action = f'<a href="/toggle-lock/{owner[0]}" style="color: #28a745; font-weight: bold; text-decoration: none;">🔓 Unlock</a>' if owner[3] == 1 else f'<a href="/toggle-lock/{owner[0]}" style="color: #dc3545; font-weight: bold; text-decoration: none;">🔒 Lock</a>'
        make_free_action = f' | <a href="/make-paid/{owner[0]}" style="color: #28a745; font-weight: bold; text-decoration: none;">✨ Make Active</a>' if owner[4] == 0 else ''
        
        owners_html += f'''
            <tr>
                <td>{owner[0]}</td>
                <td><b>{owner[2]}</b></td>
                <td>{owner[1]}</td>
                <td>{act_status}</td>
                <td>{lock_status}</td>
                <td>{lock_action}{make_free_action}</td>
            </tr>
        '''
    if not owners:
        owners_html = '<tr><td colspan="6" style="text-align: center; color: #777;">अभी कोई दुकान रजिस्टर्ड नहीं है। नीचे दिए गए फॉर्म से नई दुकान जोड़ें।</td></tr>'

    msg_html = f'<p style="background: #e6f4ea; color: #137333; padding: 10px; border-radius: 6px; font-weight: bold;">{msg}</p>' if msg else ''

    return f'''
        <!DOCTYPE html>
        <html lang="hi">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Master Admin Control Panel</title>
            <style>
                body {{ font-family: 'Segoe UI', sans-serif; background: #f0f2f5; padding: 20px; margin: 0; }}
                .container {{ max-width: 950px; margin: 0 auto; background: white; padding: 25px; border-radius: 16px; box-shadow: 0 4px 20px rgba(0,0,0,0.06); }}
                .header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #eee; padding-bottom: 15px; margin-bottom: 20px; }}
                h1 {{ color: #333; font-size: 22px; margin: 0; }}
                .logout {{ background: #dc3545; color: white; padding: 8px 16px; text-decoration: none; border-radius: 6px; font-weight: bold; font-size: 14px; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 14px; }}
                th, td {{ border: 1px solid #dee2e6; padding: 12px; text-align: left; }}
                th {{ background: #f1f3f5; }}
                .form-box {{ background: #f8f9fa; padding: 20px; border-radius: 12px; margin-bottom: 20px; border: 1px solid #e9ecef; }}
                .form-box input {{ padding: 10px; margin: 5px 0 15px 0; width: 100%; box-sizing: border-box; border: 1px solid #ccc; border-radius: 6px; }}
                .form-box button {{ background: #28a745; color: white; border: none; padding: 10px 20px; font-weight: bold; border-radius: 6px; cursor: pointer; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>👑 Master Super Admin Control Panel</h1>
                    <a href="/logout" class="logout">लॉग आउट</a>
                </div>
                
                {msg_html}

                <div class="form-box">
                    <h3>➕ नई दुकान (Shopkeeper) की ID डायरेक्ट बनाएं:</h3>
                    <form method="POST">
                        <label>दुकान का नाम:</label>
                        <input type="text" name="shop_name" placeholder="उदा: प्रज्ञा केंद्र हीहल" required>
                        <label>दुकान की UPI ID:</label>
                        <input type="text" name="upi_id" placeholder="उदा: dukan@okaxis" required>
                        <label>यूजरनेम:</label>
                        <input type="text" name="username" placeholder="उदा: shop123" required>
                        <label>पासवर्ड:</label>
                        <input type="password" name="password" required>
                        <button type="submit" name="create_shop" value="1">दुकान की ID बनाएँ (Free Active)</button>
                    </form>
                </div>

                <h3>📋 सभी प्रज्ञा केंद्र (Shops) की सूची:</h3>
                <table>
                    <tr><th>ID</th><th>दुकान का नाम</th><th>यूजरनेम</th><th>एक्टिवेशन स्टेटस</th><th>लॉक स्टेटस</th><th>एक्शन</th></tr>
                    {owners_html}
                </table>
            </div>
        </body>
        </html>
    '''

@app.route('/make-paid/<int:owner_id>')
def make_paid(owner_id):
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET is_paid = 1 WHERE id = ?", (owner_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('super_admin'))

@app.route('/toggle-lock/<int:owner_id>')
def toggle_lock(owner_id):
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
        
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT is_locked FROM users WHERE id = ?", (owner_id,))
    res = cursor.fetchone()
    if res:
        new_status = 0 if res[0] == 1 else 1
        cursor.execute("UPDATE users SET is_locked = ? WHERE id = ?", (new_status, owner_id))
        conn.commit()
    conn.close()
    return redirect(url_for('super_admin'))

@app.route('/upload/<int:owner_id>', methods=['GET', 'POST'])
def customer_upload(owner_id):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT shop_name, upi_id, is_locked, is_paid FROM users WHERE id = ? AND role = 'owner'", (owner_id,))
    owner = cursor.fetchone()
    
    if not owner or owner[2] == 1:
        conn.close()
        return "<h2 style='text-align:center; margin-top:50px; font-family:sans-serif;'>⚠️ यह प्रज्ञा केंद्र अकाउंट वर्तमान में बंद या लॉक है।</h2>"
    
    if owner[3] == 0:
        conn.close()
        return "<h2 style='text-align:center; margin-top:50px; font-family:sans-serif;'>⚠️ इस दुकान का सब्सक्रिप्शन पेंडिंग है। कृपया दुकानदार से संपर्क करें।</h2>"
        
    shop_name = owner[0]
    upi_id = owner[1]

    if request.method == 'POST':
        if 'file' in request.files:
            file = request.files['file']
            if file and allowed_file(file.filename):
                filename = file.filename
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                
                color_mode = request.form.get('color_mode', 'bw')
                side_mode = request.form.get('side_mode', 'single')
                pages = int(request.form.get('pages', 1))
                copies = int(request.form.get('copies', 1))
                pay_method = request.form.get('pay_method', 'cash')
                
                rate = 10 if color_mode == 'color' else 5
                total_price = rate * pages * copies
                
                cursor.execute("""
                    INSERT INTO files (owner_id, filename, filepath, color_mode, side_mode, pages, copies, total_price, pay_method, payment_status) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Pending')
                """, (owner_id, filename, filepath, color_mode, side_mode, pages, copies, total_price, pay_method))
                conn.commit()
                conn.close()
                
                return f'''
                    <!DOCTYPE html>
                    <html lang="hi">
                    <head>
                        <meta charset="UTF-8">
                        <meta name="viewport" content="width=device-width, initial-scale=1.0">
                        <title>Order Success</title>
                        <style>
                            body {{ font-family: 'Segoe UI', sans-serif; background: #f0f2f5; padding: 40px 20px; text-align: center; }}
                            .card {{ background: white; max-width: 420px; margin: 0 auto; padding: 30px; border-radius: 16px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); }}
                            h2 {{ color: #28a745; margin-top: 0; }}
                            .bill {{ font-size: 22px; color: #333; margin: 15px 0; background: #f8f9fa; padding: 10px; border-radius: 8px; }}
                        </style>
                    </head>
                    <body>
                        <div class="card">
                            <h2>✅ ऑर्डर सफलतापूर्वक जमा हो गया!</h2>
                            <div class="bill">कुल बिल: <b>₹{total_price}</b></div>
                            <p style="color: #555; font-size: 14px;">दुकानदार द्वारा अप्रूव होते ही प्रिंट चालू हो जाएगा।</p>
                            <a href="/upload/{owner_id}" style="display:inline-block; margin-top:20px; color:#0066ff; text-decoration:none; font-weight:bold;">← दूसरा डाक्यूमेंट भेजें</a>
                        </div>
                    </body>
                    </html>
                '''

    conn.close()
    
    upi_pay_link = f"upi://pay?pa={upi_id}&pn={shop_name}&cu=INR"
    qr_img_api = f"https://api.qrserver.com/v1/create-qr-code/?size=180x180&data={upi_pay_link}"

    return f'''
        <!DOCTYPE html>
        <html lang="hi">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Quick Print Kiosk - {shop_name}</title>
            <style>
                body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f0f2f5; padding: 20px 10px; margin: 0; }}
                .kiosk-card {{ background: white; max-width: 440px; margin: 0 auto; padding: 25px; border-radius: 16px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); }}
                h2 {{ color: #1a1a1a; font-size: 22px; text-align: center; margin-top: 0; margin-bottom: 20px; border-bottom: 2px solid #f1f3f5; padding-bottom: 12px; }}
                label {{ font-weight: 600; color: #333; font-size: 14px; display: block; margin-top: 15px; margin-bottom: 5px; }}
                input[type="file"], select, input[type="number"] {{ width: 100%; padding: 10px; border: 1px solid #ced4da; border-radius: 8px; box-sizing: border-box; font-size: 15px; background: #fff; }}
                .submit-btn {{ width: 100%; margin-top: 25px; padding: 14px; background: #0066ff; color: white; border: none; border-radius: 8px; font-size: 16px; font-weight: bold; cursor: pointer; transition: 0.2s; }}
                .submit-btn:hover {{ background: #0052cc; }}
                .note {{ background: #e7f5ff; border-left: 4px solid #339af0; padding: 12px; border-radius: 6px; font-size: 13px; color: #1864ab; margin-top: 20px; line-height: 1.4; }}
                .qr-section {{ text-align: center; margin-top: 25px; background: #f8f9fa; padding: 15px; border-radius: 12px; display: none; }}
                .upi-btn-group {{ display: flex; gap: 8px; justify-content: center; margin-top: 10px; flex-wrap: wrap; }}
                .upi-app-btn {{ background: #5f259f; color: white; padding: 8px 12px; border-radius: 6px; text-decoration: none; font-size: 13px; font-weight: bold; }}
            </style>
            <script>
                function togglePaymentMode() {{
                    var mode = document.getElementById('pay_method').value;
                    var qrSec = document.getElementById('qr_section');
                    if(mode === 'upi') {{
                        qrSec.style.display = 'block';
                    }} else {{
                        qrSec.style.display = 'none';
                    }}
                }}
            </script>
        </head>
        <body>
            <div class="kiosk-card">
                <h2>🖨️ Quick Print Kiosk</h2>
                <p style="text-align: center; color: #666; font-size: 13px; margin-top: -15px; margin-bottom: 20px;">{shop_name}</p>
                
                <form method="POST" enctype="multipart/form-data">
                    <label>📄 डॉक्यूमेंट चुनें (PDF, Word, Image):</label>
                    <input type="file" name="file" required>
                    
                    <label>🎨 प्रिंट का प्रकार:</label>
                    <select name="color_mode">
                        <option value="bw">Black & White (₹5 / पेज)</option>
                        <option value="color">Colour (₹10 / पेज)</option>
                    </select>
                    
                    <label>📄 प्रिंट साइड:</label>
                    <select name="side_mode">
                        <option value="single">Single Side</option>
                        <option value="both">Both Side (Duplex)</option>
                    </select>
                    
                    <label>🔢 पेजों की संख्या:</label>
                    <input type="number" name="pages" value="1" min="1" required>
                    
                    <label>📑 कॉपी की संख्या:</label>
                    <input type="number" name="copies" value="1" min="1" required>

                    <label>💳 पेमेंट का तरीका:</label>
                    <select name="pay_method" id="pay_method" onchange="togglePaymentMode()" required>
                        <option value="cash">Cash (काउंटर पर)</option>
                        <option value="upi">UPI / Online Payment</option>
                    </select>
                    
                    <div class="note">
                        💡 <b>नोट:</b> फाइल सबमिट करने के बाद दुकानदार द्वारा अप्रूव होते ही प्रिंट चालू हो जाएगा।
                    </div>

                    <div class="qr-section" id="qr_section">
                        <p style="margin: 0 0 10px 0; font-size: 14px; font-weight: 600; color: #333;">📱 UPI भुगतान ऐप से पे करें</p>
                        <p style="margin: 0 0 10px 0; font-size: 13px; color: #555;">UPI ID: <b>{upi_id}</b></p>
                        <div class="upi-btn-group">
                            <a href="{upi_pay_link}" class="upi-app-btn" style="background: #5f259f;">PhonePe</a>
                            <a href="{upi_pay_link}" class="upi-app-btn" style="background: #008551;">Google Pay</a>
                            <a href="{upi_pay_link}" class="upi-app-btn" style="background: #00baf2; color: #000;">Paytm</a>
                        </div>
                        <br>
                        <img src="{qr_img_api}" alt="UPI QR Code" style="border-radius: 8px; border: 1px solid #ddd; width: 150px; margin-top: 10px;">
                    </div>
                    
                    <button type="submit" class="submit-btn">प्रिंट ऑर्डर भेजें 🚀</button>
                </form>
            </div>
        </body>
        </html>
    '''

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
