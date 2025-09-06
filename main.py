from flask import Flask, request, render_template_string
import requests, json, random, string, time
from threading import Thread, Event

app = Flask(__name__)
app.debug = True

stop_events = {}
threads = {}

# WhatsApp Messaging Function
def send_messages(creds, target, prefix, interval, messages, task_id):
    stop_event = stop_events[task_id]

    whatsapp_token = creds["whatsapp_token"]
    phone_number_id = creds["phone_number_id"]

    url = f"https://graph.facebook.com/v17.0/{phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {whatsapp_token}",
        "Content-Type": "application/json"
    }

    msg_index = 0
    while not stop_event.is_set():
        try:
            msg = f"{prefix} {messages[msg_index]}"

            payload = {
                "messaging_product": "whatsapp",
                "to": target,
                "type": "text",
                "text": {"body": msg}
            }

            r = requests.post(url, headers=headers, json=payload, timeout=10)
            if r.status_code == 200:
                print(f"✅ Sent: {msg}")
            else:
                print(f"❌ Failed {r.status_code}: {r.text}")

        except Exception as e:
            print(f"⚠️ Error: {e}")
            time.sleep(5)

        time.sleep(interval)
        msg_index = (msg_index + 1) % len(messages)


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        # Upload cred.json
        cred_file = request.files.get("credFile")
        if not cred_file:
            return "cred.json required"
        creds = json.loads(cred_file.read().decode())

        # Target phone number
        target = request.form.get("target")
        prefix = request.form.get("prefix", "")
        try:
            interval = int(request.form.get("interval", 5))
        except:
            interval = 5

        # Messages file
        txt_file = request.files.get("txtFile")
        if not txt_file:
            return "Message file required"
        messages = txt_file.read().decode().splitlines()
        messages = [m for m in messages if m.strip()]

        task_id = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
        stop_events[task_id] = Event()
        thread = Thread(target=send_messages, args=(creds, target, prefix, interval, messages, task_id))
        thread.start()

        return f"Task started with ID: {task_id}"

    # Same HTML/CSS as before
    return render_template_string("""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Aarav - WhatsApp Bot</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.0.2/dist/css/bootstrap.min.css" rel="stylesheet">
  <style>
    body { background-color: white; color: black; }
    .container {
      max-width: 400px; min-height: 600px;
      border-radius: 20px; padding: 20px;
      box-shadow: 0 0 15px gray; margin-bottom: 20px;
    }
    .form-control { border: 1px solid black; background:#f9f9f9;
      height: 40px; padding:7px; margin-bottom:20px; border-radius:10px; color:black; }
    .header { text-align:center; padding-bottom:20px; }
    .btn-submit { width:100%; margin-top:10px; }
  </style>
</head>
<body>
  <header class="header mt-4">
    <h2 class="mt-3">WhatsApp Auto Sender by Aarav</h2>
  </header>
  <div class="container text-center">
    <form method="post" enctype="multipart/form-data">
      <div class="mb-3">
        <label class="form-label">Upload cred.json</label>
        <input type="file" class="form-control" name="credFile" required>
      </div>
      <div class="mb-3">
        <label class="form-label">Target Number (with +country code)</label>
        <input type="text" class="form-control" name="target" placeholder="+919876543210" required>
      </div>
      <div class="mb-3">
        <label class="form-label">Prefix</label>
        <input type="text" class="form-control" name="prefix" placeholder="Hello">
      </div>
      <div class="mb-3">
        <label class="form-label">Time Delay (seconds)</label>
        <input type="number" class="form-control" name="interval" value="5">
      </div>
      <div class="mb-3">
        <label class="form-label">Message File (.txt)</label>
        <input type="file" class="form-control" name="txtFile" required>
      </div>
      <button type="submit" class="btn btn-primary btn-submit">Start Messaging</button>
    </form>
  </div>
</body>
</html>
""")


@app.route("/stop", methods=["POST"])
def stop():
    task_id = request.form.get("taskId")
    if task_id in stop_events:
        stop_events[task_id].set()
        return f"Task {task_id} stopped"
    return "Task not found"


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
