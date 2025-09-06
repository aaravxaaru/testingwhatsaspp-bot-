# whatsapp_flask_bot.py
# Flask app with two-step UI:
# 1. QR code login page
# 2. After login, redirect to send-message form page
#
# Features:
# - QR shown first; after scanning, the user is redirected to /send_page
# - Send form includes: phone (with country code +1 etc.), prefix, message file upload, time interval
# - Backend reads messages from file and sends them repeatedly at interval
#
# Same warnings: WhatsApp Web automation may violate ToS. For educational/demo purposes only.

from flask import Flask, request, render_template_string, send_file, jsonify, redirect, url_for
from threading import Thread, Event
import time, os, io
import urllib.parse

SESSION_DIR = os.path.join(os.getcwd(), "wa_profile")
STORAGE_STATE = os.path.join(os.getcwd(), "cred.json")
QR_PNG_PATH = os.path.join(os.getcwd(), "latest_qr.png")

app = Flask(__name__)
app.debug = True

class WhatsAppManager:
    def __init__(self):
        self.thread = None
        self.stop_event = Event()
        self.running = False
        self.page = None
        self.context = None
        self.last_qr_bytes = None

    def start(self):
        if self.running:
            return 'already_running'
        self.stop_event.clear()
        self.thread = Thread(target=self._run_playwright, daemon=True)
        self.thread.start()
        return 'started'

    def stop(self):
        self.stop_event.set()
        return 'stopping'

    def _run_playwright(self):
        try:
            from playwright.sync_api import sync_playwright
        except Exception as e:
            print('Playwright import error:', e)
            self.running = False
            return

        self.running = True
        with sync_playwright() as p:
            ctx = p.chromium.launch_persistent_context(SESSION_DIR, headless=False)
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            self.context = ctx
            self.page = page
            page.goto('https://web.whatsapp.com', timeout=0)

            for _ in range(60):
                if self.stop_event.is_set():
                    break
                try:
                    el = page.query_selector('canvas')
                    if el:
                        buf = el.screenshot()
                        self.last_qr_bytes = buf
                        with open(QR_PNG_PATH, 'wb') as f:
                            f.write(buf)
                    if page.query_selector('div[role="textbox"]'):
                        self.last_qr_bytes = None
                        break
                except Exception:
                    pass
                time.sleep(1)

            while not self.stop_event.is_set():
                time.sleep(1)
            ctx.close()
        self.running = False

    def get_qr_bytes(self):
        return self.last_qr_bytes

    def send_message_loop(self, phone, prefix, messages, interval, stop_event):
        if not self.page:
            return
        p = self.page
        for idx, msg in enumerate(messages):
            if stop_event.is_set():
                break
            text = f"{prefix} {msg}"
            wa_url = f"https://web.whatsapp.com/send?phone={phone}&text={urllib.parse.quote_plus(text)}"
            try:
                p.goto(wa_url, timeout=60000)
                time.sleep(3)
                input_el = p.query_selector('div[contenteditable="true"][data-tab]') or p.query_selector('div[role="textbox"]')
                if input_el:
                    input_el.press('Enter')
            except Exception as e:
                print('send error:', e)
            time.sleep(interval)

manager = WhatsAppManager()
stop_events = {}

@app.route('/')
def index():
    return render_template_string('''
    <div style="text-align:center; margin-top:50px;">
      <h3>Step 1: Start WhatsApp Session</h3>
      <form method="post" action="/start">
        <button class="btn btn-primary">Start & Show QR</button>
      </form>
      <p>After scanning QR, you will be redirected to message form.</p>
    </div>
    ''')

@app.route('/start', methods=['POST'])
def start_route():
    manager.start()
    return redirect(url_for('qr_page'))

@app.route('/qr')
def qr_page():
    buf = manager.get_qr_bytes()
    if buf:
        img_tag = '<img src="/qr_img" style="max-width:300px;">'
    else:
        if manager.running:
            return redirect(url_for('send_page'))
        img_tag = '<p>No QR available</p>'
    return f"<div style='text-align:center; margin-top:40px;'><h3>Scan QR Code</h3>{img_tag}<br><a href='/send_page'>Go to Send Page</a></div>"

@app.route('/qr_img')
def qr_img():
    buf = manager.get_qr_bytes()
    if buf:
        return send_file(io.BytesIO(buf), mimetype='image/png')
    return 'no qr', 404

@app.route('/send_page')
def send_page():
    return render_template_string('''
    <div style="max-width:500px; margin:40px auto;">
      <h3>Step 2: Send Messages</h3>
      <form method="post" action="/send" enctype="multipart/form-data">
        <label>Target Phone (+countrycode...)</label>
        <input type="text" name="phone" class="form-control" required>
        <label>Prefix</label>
        <input type="text" name="prefix" class="form-control" required>
        <label>Message File (.txt, one per line)</label>
        <input type="file" name="msgfile" class="form-control" required>
        <label>Interval (seconds)</label>
        <input type="number" name="interval" class="form-control" value="5" required>
        <button type="submit" class="btn btn-success" style="margin-top:10px;">Start Sending</button>
      </form>
    </div>
    ''')

@app.route('/send', methods=['POST'])
def send_route():
    phone = request.form.get('phone','').replace('+','').strip()
    prefix = request.form.get('prefix','')
    interval = int(request.form.get('interval','5'))
    f = request.files['msgfile']
    messages = f.read().decode().splitlines()
    task_id = str(int(time.time()))
    ev = Event()
    stop_events[task_id] = ev
    t = Thread(target=manager.send_message_loop, args=(phone,prefix,messages,interval,ev), daemon=True)
    t.start()
    return f"Started sending with task id {task_id}"
