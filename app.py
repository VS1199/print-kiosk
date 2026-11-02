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
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (username, password, shop_name, role, is_locked, is_paid) VALUES (?, ?, ?, 'admin', 0, 1)",
                       ('VS119', generate_password_hash('Vs@787800'), 'Master Admin Panel'))
        conn.commit()
    conn.close()

init_db()

@app.route('/')
def home():
    return '''
        <div style="font-family:sans-serif; text-align:center; padding:50px;">
            <h2>🖨️ Pragya Kendra Print Kiosk Platform</h2>
            <br><a href="/login" style="padding:10px 20px; background:#0066ff; color:#fff; text-decoration:none; border-radius:5px;">Login</a>
        </div>
    '''

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = ""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id, password, role, is_locked, shop_name FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        conn.close()
        
        if user and check_password_hash(user[1], password):
            if user[3] == 1:
                error = "अकाउंट लॉक है!"
            else:
                session['user_id'] = user[0]
                session['role'] = user[2]
                session['shop_name'] = user[4]
                return redirect(url_for('super_admin' if user[2] == 'admin' else 'dashboard'))
        else:
            error = "गलत यूजरनेम या पासवर्ड!"
            
    return f'''
        <div style="font-family:sans-serif; max-width:400px; margin:50px auto; padding:20px; border:1px solid #ddd; border-radius:8px;">
            <h2>🔐 लॉगिन करें</h2>
            <p style="color:red;">{error}</p>
            <form method="POST">
                <label>यूजरनेम:</label><br><input type="text" name="username" required style="width:100%; padding:8px; margin:5px 0 15px;"><br>
                <label>पासवर्ड:</label><br><input type="password" name="password" required style="width:100%; padding:8px; margin:5px 0 15px;"><br>
                <button type="submit" style="width:100%; padding:10px; background:#0066ff; color:#fff; border:none; border-radius:5px;">लॉगिन</button>
            </form>
        </div>
    '''

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session or session['role'] != 'owner':
        return redirect(url_for('login'))
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, filename, total_price, payment_status FROM files WHERE owner_id = ? ORDER BY id DESC", (session['user_id'],))
    files = cursor.fetchall()
    conn.close()
    
    rows = ""
    for f in files:
        status = "✓ Approved" if f[3] == 'Verified' else f'<a href="/approve-order/{f[0]}">✅ Approve</a>'
        print_btn = f'<a href="/print-file/{f[0]}" target="_blank">🖨️ प्रिंट करें</a>' if f[3] == 'Verified' else 'Pending'
        rows += f"<tr><td>{f[0]}</td><td>{f[1]}</td><td>₹{f[2]}</td><td>{status}</td><td>{print_btn}</td></tr>"

    return f'''
        <div style="font-family:sans-serif; max-width:800px; margin:30px auto; padding:20px;">
            <h2>🖥️ {session['shop_name']} डैशबोर्ड</h2>
            <a href="/logout" style="color:red; float:right;">लॉग आउट</a>
            <hr>
            <h3>📥 आर्डर लिस्ट:</h3>
            <table border="1" cellpadding="10" style="width:100%; border-collapse:collapse;">
                <tr><th>ID</th><th>फाइल</th><th>मूल्य</th><th>स्टेटस</th><th>एक्शन</th></tr>
                {rows if rows else '<tr><td colspan="5" style="text-align:center;">कोई आर्डर नहीं है</td></tr>'}
            </table>
        </div>
    '''

@app.route('/approve-order/<int:file_id>')
def approve_order(file_id):
    if 'user_id' not in session: return redirect(url_for('login'))
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE files SET payment_status = 'Verified' WHERE id = ? AND owner_id = ?", (file_id, session['user_id']))
    conn.commit()
    conn.close()
    return redirect(url_for('dashboard'))

@app.route('/print-file/<int:file_id>')
def print_file(file_id):
    if 'user_id' not in session: return redirect(url_for('login'))
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT filepath, owner_id FROM files WHERE id = ?", (file_id,))
    f = cursor.fetchone()
    conn.close()
    if f and f[1] == session['user_id']:
        return send_file(f[0], as_attachment=False)
    return "Unauthorized", 403

@app.route('/super-admin', methods=['GET', 'POST'])
def super_admin():
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
        
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    if request.method == 'POST':
        try:
            cursor.execute("INSERT INTO users (username, password, shop_name, upi_id, role, is_locked, is_paid) VALUES (?, ?, ?, ?, 'owner', 0, 1)",
                           (request.form['username'], generate_password_hash(request.form['password']), request.form['shop_name'], request.form['upi_id']))
            conn.commit()
        except: pass

    cursor.execute("SELECT id, username, shop_name, is_locked FROM users WHERE role = 'owner'")
    owners = cursor.fetchall()
    conn.close()
    
    owner_rows = ""
    for o in owners:
        owner_rows += f"<tr><td>{o[0]}</td><td>{o[2]}</td><td>{o[1]}</td><td>{'Locked' if o[3] else 'Active'}</td></tr>"

    return f'''
        <div style="font-family:sans-serif; max-width:900px; margin:30px auto; padding:20px;">
            <h2>👑 Master Super Admin Control Panel</h2>
            <a href="/logout" style="color:red; float:right;">लॉग आउट</a>
            <hr>
            <h3>➕ नई दुकान जोड़ें:</h3>
            <form method="POST" style="background:#f9f9f9; padding:15px; border-radius:8px;">
                दुकान का नाम: <input type="text" name="shop_name" required style="padding:5px; width:100%; margin:5px 0 10px;"><br>
                UPI ID: <input type="text" name="upi_id" required style="padding:5px; width:100%; margin:5px 0 10px;"><br>
                यूजरनेम: <input type="text" name="username" required style="padding:5px; width:100%; margin:5px 0 10px;"><br>
                पासवर्ड: <input type="password" name="password" required style="padding:5px; width:100%; margin:5px 0 10px;"><br>
                <button type="submit" style="padding:8px 15px; background:green; color:#fff; border:none; border-radius:5px;">दुकान बनाएँ</button>
            </form>
            <h3 style="margin-top:30px;">📋 सभी दुकानें:</h3>
            <table border="1" cellpadding="10" style="width:100%; border-collapse:collapse;">
                <tr><th>ID</th><th>दुकान का नाम</th><th>यूजरनेम</th><th>स्टेटस</th></tr>
                {owner_rows if owner_rows else '<tr><td colspan="4" style="text-align:center;">कोई दुकान नहीं है</td></tr>'}
            </table>
        </div>
    '''

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
