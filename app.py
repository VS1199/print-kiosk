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
    
    # Centers Table
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
    
    # Orders Table with Advanced Tracking (B/W, Color, Pages, Copies, Revenue)
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
            print_status TEXT DEFAULT 'Uploaded',
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(owner_id) REFERENCES users(id)
        )
    ''')
    
    conn.commit()
    
    # Default Super Admin Setup
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
        <div style="font-family:sans-serif; text-align:center; padding:50px; background:#f0f2f5; height:100vh; margin:0;">
            <div style="background:white; max-width:400px; margin:0 auto; padding:30px; border-radius:12px; box-shadow:0 4px 15px rgba(0,0,0,0.1);">
                <h2>🖨️ Smart Pragya Print</h2>
                <p style="color:#666; font-size:14px;">Multi-Center Cloud Printing SaaS</p>
                <br><a href="/login" style="display:block; padding:12px; background:#0066ff; color:#fff; text-decoration:none; border-radius:8px; font-weight:bold;">लॉगिन करें (Shop Owner / Admin)</a>
            </div>
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
                error = "आपका अकाउंट लॉक कर दिया गया है!"
            else:
                session['user_id'] = user[0]
                session['role'] = user[2]
                session['shop_name'] = user[4]
                return redirect(url_for('super_admin' if user[2] == 'admin' else 'dashboard'))
        else:
            error = "गलत यूजरनेम या पासवर्ड!"
            
    return f'''
        <div style="font-family:sans-serif; max-width:400px; margin:50px auto; padding:25px; background:white; border-radius:12px; box-shadow:0 4px 15px rgba(0,0,0,0.1);">
            <h2>🔐 कियोस्क लॉगिन</h2>
            <p style="color:red; font-size:14px;">{error}</p>
            <form method="POST">
                <label>यूजरनेम:</label><br><input type="text" name="username" required style="width:100%; padding:10px; margin:5px 0 15px; border:1px solid #ccc; border-radius:6px; box-sizing:border-box;"><br>
                <label>पासवर्ड:</label><br><input type="password" name="password" required style="width:100%; padding:10px; margin:5px 0 15px; border:1px solid #ccc; border-radius:6px; box-sizing:border-box;"><br>
                <button type="submit" style="width:100%; padding:12px; background:#0066ff; color:#fff; border:none; border-radius:6px; font-weight:bold; cursor:pointer;">लॉगिन करें</button>
            </form>
            <br><a href="/" style="color:#0066ff; text-decoration:none; font-size:14px;">← होम पेज</a>
        </div>
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
    
    # Fetch all orders for this specific center (Tenant Data Isolation)
    cursor.execute("SELECT id, filename, color_mode, side_mode, pages, copies, total_price, pay_method, payment_status, print_status FROM files WHERE owner_id = ? ORDER BY id DESC", (owner_id,))
    files = cursor.fetchall()
    
    # Calculate Analytics / Stats
    total_orders = len(files)
    total_revenue = sum(f[6] for f in files if f[8] == 'Verified')
    bw_pages = sum(f[4] * f[5] for f in files if f[2] == 'bw' and f[8] == 'Verified')
    color_pages = sum(f[4] * f[5] for f in files if f[2] == 'color' and f[8] == 'Verified')
    
    conn.close()
    
    upload_link = request.host_url + f"upload/{owner_id}"
    
    rows = ""
    for f in files:
        status_badge = '<span style="color: #28a745; font-weight: bold;">✓ Approved</span>' if f[8] == 'Verified' else f'<a href="/approve-order/{f[0]}" style="padding:4px 8px; background:#ffc107; color:#000; border-radius:4px; text-decoration:none; font-size:12px; font-weight:bold;">✅ Approve</a>'
        print_action = f'<a href="/print-file/{f[0]}" target="_blank" style="padding:6px 12px; background:#28a745; color:white; border-radius:4px; text-decoration:none; font-size:12px; font-weight:bold;">🖨️ प्रिंट करें</a>' if f[8] == 'Verified' else '<span style="color: #888; font-size: 12px;">Waiting Approval</span>'
        
        rows += f'''
            <tr>
                <td>{f[0]}</td>
                <td>{f[1]}</td>
                <td>{f[2].upper()} | P: {f[4]} | C: {f[5]}</td>
                <td><b>₹{f[6]}</b></td>
                <td>{status_badge}</td>
                <td>{print_action}</td>
            </tr>
        '''

    return f'''
        <div style="font-family:sans-serif; max-width:1100px; margin:20px auto; padding:20px; background:#fff; border-radius:12px; box-shadow:0 4px 15px rgba(0,0,0,0.06);">
            <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:2px solid #eee; padding-bottom:15px; margin-bottom:20px;">
                <h2>🖥️ {shop_name} (डैशबोर्ड)</h2>
                <a href="/logout" style="background:#dc3545; color:white; padding:8px 16px; text-decoration:none; border-radius:6px; font-weight:bold; font-size:14px;">लॉग आउट</a>
            </div>
            
            <!-- Analytics Cards -->
            <div style="display:flex; gap:15px; margin-bottom:20px; flex-wrap:wrap;">
                <div style="background:#f8f9fa; padding:15px; border-radius:8px; flex:1; min-width:200px; border-left:4px solid #0066ff;">
                    <p style="margin:0; color:#666; font-size:13px;">कुल आर्डर्स</p>
                    <h3 style="margin:5px 0 0; color:#333;">{total_orders}</h3>
                </div>
                <div style="background:#f8f9fa; padding:15px; border-radius:8px; flex:1; min-width:200px; border-left:4px solid #28a745;">
                    <p style="margin:0; color:#666; font-size:13px;">कुल कमाई (Revenue)</p>
                    <h3 style="margin:5px 0 0; color:#28a745;">₹{total_revenue}</h3>
                </div>
                <div style="background:#f8f9fa; padding:15px; border-radius:8px; flex:1; min-width:200px; border-left:4px solid #ffc107;">
                    <p style="margin:0; color:#666; font-size:13px;">B/W Pages / Color Pages</p>
                    <h3 style="margin:5px 0 0; color:#333;">{bw_pages} B/W | {color_pages} Color</h3>
                </div>
            </div>

            <h3>💳 UPI ID सेटिंग:</h3>
            <form method="POST" style="margin-bottom:20px;">
                <input type="text" name="upi_id" value="{upi_id}" required style="padding:8px; width:300px; border:1px solid #ccc; border-radius:6px;">
                <button type="submit" name="update_upi" value="1" style="padding:8px 15px; background:#0066ff; color:white; border:none; border-radius:6px; font-weight:bold; cursor:pointer;">अपडेट करें</button>
            </form>

            <h3>📱 ग्राहक अपलोड लिंक (QR Code Link):</h3>
            <input type="text" value="{upload_link}" style="width:450px; padding:8px; border:1px solid #ccc; border-radius:6px;" readonly>
            <p><a href="https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={upload_link}" target="_blank" style="color:#0066ff; font-weight:bold;">🔗 QR कोड देखें</a></p>
            
            <hr style="border:0; border-top:1px solid #eee; margin:20px 0;">
            
            <h3>📥 ग्राहकों के प्रिंट ऑर्डर्स:</h3>
            <table border="1" cellpadding="10" style="width:100%; border-collapse:collapse; font-size:14px; margin-top:10px;">
                <tr style="background:#f1f3f5;"><th>ID</th><th>फाइल का नाम</th><th>सेटिंग्स</th><th>बिल</th><th>स्टेटस</th><th>एक्शन</th></tr>
                {rows if rows else '<tr><td colspan="6" style="text-align:center; color:#777;">अभी तक कोई आर्डर नहीं आया है।</td></tr>'}
            </table>
        </div>
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
    
    msg = ""
    if request.method == 'POST' and 'create_shop' in request.form:
        try:
            cursor.execute("INSERT INTO users (username, password, shop_name, upi_id, role, is_locked, is_paid) VALUES (?, ?, ?, ?, 'owner', 0, 1)",
                           (request.form['username'], generate_password_hash(request.form['password']), request.form['shop_name'], request.form['upi_id']))
            conn.commit()
            msg = "✅ दुकान सफलतापूर्वक बन गई!"
        except:
            msg = "❌ यूजरनेम पहले से मौजूद है!"

    cursor.execute("SELECT id, username, shop_name, is_locked FROM users WHERE role = 'owner'")
    owners = cursor.fetchall()
    conn.close()
    
    owner_rows = ""
    for o in owners:
        owner_rows += f"<tr><td>{o[0]}</td><td><b>{o[2]}</b></td><td>{o[1]}</td><td>{'Locked' if o[3] else 'Active'}</td></tr>"

    return f'''
        <div style="font-family:sans-serif; max-width:950px; margin:30px auto; padding:20px; background:white; border-radius:12px; box-shadow:0 4px 15px rgba(0,0,0,0.06);">
            <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:2px solid #eee; padding-bottom:15px; margin-bottom:20px;">
                <h2>👑 Master Super Admin Control Panel</h2>
                <a href="/logout" style="background:#dc3545; color:white; padding:8px 16px; text-decoration:none; border-radius:6px; font-weight:bold;">लॉग आउट</a>
            </div>
            
            <p style="color:green; font-weight:bold;">{msg}</p>

            <div style="background:#f8f9fa; padding:20px; border-radius:10px; margin-bottom:20px;">
                <h3>➕ नई दुकान (Shopkeeper) की ID बनाएं:</h3>
                <form method="POST">
                    दुकान का नाम: <input type="text" name="shop_name" required style="width:100%; padding:8px; margin:5px 0 10px; border:1px solid #ccc; border-radius:6px;"><br>
                    UPI ID: <input type="text" name="upi_id" required style="width:100%; padding:8px; margin:5px 0 10px; border:1px solid #ccc; border-radius:6px;"><br>
                    यूजरनेम: <input type="text" name="username" required style="width:100%; padding:8px; margin:5px 0 10px; border:1px solid #ccc; border-radius:6px;"><br>
                    पासवर्ड: <input type="password" name="password" required style="width:100%; padding:8px; margin:5px 0 15px; border:1px solid #ccc; border-radius:6px;"><br>
                    <button type="submit" name="create_shop" value="1" style="padding:10px 20px; background:#28a745; color:white; border:none; border-radius:6px; font-weight:bold; cursor:pointer;">दुकान बनाएं</button>
                </form>
            </div>

            <h3>📋 सभी रजिस्टर्ड दुकानें:</h3>
            <table border="1" cellpadding="10" style="width:100%; border-collapse:collapse; font-size:14px; margin-top:10px;">
                <tr style="background:#f1f3f5;"><th>ID</th><th>दुकान का नाम</th><th>यूजरनेम</th><th>स्टेटस</th></tr>
                {owner_rows if owner_rows else '<tr><td colspan="4" style="text-align:center; color:#777;">कोई दुकान नहीं है</td></tr>'}
            </table>
        </div>
    '''

@app.route('/upload/<int:owner_id>', methods=['GET', 'POST'])
def customer_upload(owner_id):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT shop_name, upi_id, is_locked FROM users WHERE id = ? AND role = 'owner'", (owner_id,))
    owner = cursor.fetchone()
    
    if not owner or owner[2] == 1:
        conn.close()
        return "<h2 style='text-align:center; margin-top:50px; font-family:sans-serif;'>⚠️ यह प्रज्ञा केंद्र अकाउंट वर्तमान में बंद या लॉक है।</h2>"
        
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
                    INSERT INTO files (owner_id, filename, filepath, color_mode, side_mode, pages, copies, total_price, pay_method, payment_status, print_status) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Pending', 'Uploaded')
                """, (owner_id, filename, filepath, color_mode, side_mode, pages, copies, total_price, pay_method))
                conn.commit()
                conn.close()
                
                return f'''
                    <div style="font-family:sans-serif; max-width:400px; margin:50px auto; padding:30px; background:white; border-radius:12px; text-align:center; box-shadow:0 4px 15px rgba(0,0,0,0.08);">
                        <h2 style="color:#28a745; margin-top:0;">✅ ऑर्डर सफलतापूर्व जमा हो गया!</h2>
                        <div style="font-size:22px; color:#333; margin:15px 0; background:#f8f9fa; padding:10px; border-radius:8px;">कुल बिल: <b>₹{total_price}</b></div>
                        <p style="color:#555; font-size:14px;">दुकानदार द्वारा अप्रूव होते ही प्रिंट चालू हो जाएगा।</p>
                        <a href="/upload/{owner_id}" style="display:inline-block; margin-top:20px; color:#0066ff; text-decoration:none; font-weight:bold;">← दूसरा डाक्यूमेंट भेजें</a>
                    </div>
                '''

    conn.close()
    
    upi_pay_link = f"upi://pay?pa={upi_id}&pn={shop_name}&cu=INR"
    qr_img_api = f"https://api.qrserver.com/v1/create-qr-code/?size=180x180&data={upi_pay_link}"

    return f'''
        <div style="font-family:sans-serif; max-width:440px; margin:30px auto; padding:25px; background:white; border-radius:16px; box-shadow:0 4px 20px rgba(0,0,0,0.08);">
            <h2 style="text-align:center; margin-top:0;">🖨️ Quick Print Kiosk</h2>
            <p style="text-align:center; color:#666; font-size:13px; margin-top:-10px; margin-bottom:20px;">{shop_name}</p>
            
            <form method="POST" enctype="multipart/form-data">
                <label style="font-weight:600; font-size:14px;">📄 डॉक्यूमेंट चुनें (PDF, Word, Image):</label><br>
                <input type="file" name="file" required style="width:100%; padding:10px; margin:5px 0 15px; border:1px solid #ccc; border-radius:8px; box-sizing:border-box;"><br>
                
                <label style="font-weight:600; font-size:14px;">🎨 प्रिंट का प्रकार:</label><br>
                <select name="color_mode" style="width:100%; padding:10px; margin:5px 0 15px; border:1px solid #ccc; border-radius:8px;">
                    <option value="bw">Black & White (₹5 / पेज)</option>
                    <option value="color">Colour (₹10 / पेज)</option>
                </select><br>
                
                <label style="font-weight:600; font-size:14px;">📄 प्रिंट साइड:</label><br>
                <select name="side_mode" style="width:100%; padding:10px; margin:5px 0 15px; border:1px solid #ccc; border-radius:8px;">
                    <option value="single">Single Side</option>
                    <option value="both">Both Side (Duplex)</option>
                </select><br>
                
                <label style="font-weight:600; font-size:14px;">🔢 पेजों की संख्या:</label><br>
                <input type="number" name="pages" value="1" min="1" required style="width:100%; padding:10px; margin:5px 0 15px; border:1px solid #ccc; border-radius:8px; box-sizing:border-box;"><br>
                
                <label style="font-weight:600; font-size:14px;">📑 कॉपी की संख्या:</label><br>
                <input type="number" name="copies" value="1" min="1" required style="width:100%; padding:10px; margin:5px 0 15px; border:1px solid #ccc; border-radius:8px; box-sizing:border-box;"><br>

                <label style="font-weight:600; font-size:14px;">💳 पेमेंट का तरीका:</label><br>
                <select name="pay_method" id="pay_method" onchange="togglePay()" style="width:100%; padding:10px; margin:5px 0 15px; border:1px solid #ccc; border-radius:8px;">
                    <option value="cash">Cash (काउंटर पर)</option>
                    <option value="upi">UPI / Online Payment</option>
                </select><br>

                <div id="qr_box" style="display:none; text-align:center; background:#f8f9fa; padding:15px; border-radius:8px; margin-bottom:15px;">
                    <p style="margin:0 0 10px; font-size:13px;">UPI ID: <b>{upi_id}</b></p>
                    <img src="{qr_img_api}" width="140" style="border-radius:6px;">
                </div>
                
                <button type="submit" style="width:100%; padding:14px; background:#0066ff; color:white; border:none; border-radius:8px; font-size:16px; font-weight:bold; cursor:pointer;">प्रिंट ऑर्डर भेजें 🚀</button>
            </form>
            <script>
                function togglePay() {{
                    var m = document.getElementById('pay_method').value;
                    document.getElementById('qr_box').style.display = (m === 'upi') ? 'block' : 'none';
                }}
            </script>
        </div>
    '''

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
