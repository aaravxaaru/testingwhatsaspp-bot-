from flask import Flask, request, render_template_string
import asyncio
import os
from playwright.async_api import async_playwright

app = Flask(__name__)

# -----------------------
# WhatsApp Messaging Logic
# -----------------------
async def send_whatsapp_message(target, prefix, messages, interval):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(storage_state="session.json")  # ✅ Use saved session
        page = await context.new_page()

        await page.goto("https://web.whatsapp.com")

        for msg in messages:
            try:
                await page.goto(f"https://web.whatsapp.com/send?phone={target}&text={prefix} {msg}")
                await page.wait_for_selector("div[role='textbox']", timeout=20000)
                await page.keyboard.press("Enter")
                print(f"✅ Sent: {msg}")
                await asyncio.sleep(interval)
            except Exception as e:
                print(f"❌ Error sending message: {e}")

        await browser.close()

# -----------------------
# Flask Routes
# -----------------------
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        target = request.form.get("target")
        prefix = request.form.get("prefix", "")
        try:
            interval = int(request.form.get("interval", 5))
        except:
            interval = 5

        txt_file = request.files.get("txtFile")
        if txt_file:
            messages = txt_file.read().decode().splitlines()
        else:
            messages = ["Hello from Render Bot!"]

        asyncio.run(send_whatsapp_message(target, prefix, messages, interval))
        return "✅ Messages sent successfully!"

    return render_template_string("""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>WhatsApp Bot - Render</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.0.2/dist/css/bootstrap.min.css" rel="stylesheet">
  <style>
    body { background:#f8f9fa; }
    .container { max-width:500px; margin-top:50px; padding:20px; border-radius:20px; box-shadow:0 0 15px gray; }
  </style>
</head>
<body>
  <div class="container">
    <h3 class="text-center">WhatsApp Auto Sender</h3>
    <form method="post" enctype="multipart/form-data">
      <div class="mb-3">
        <label class="form-label">Target Number (with country code)</label>
        <input type="text" name="target" class="form-control" placeholder="+919876543210" required>
      </div>
      <div class="mb-3">
        <label class="form-label">Prefix</label>
        <input type="text" name="prefix" class="form-control" placeholder="Hello">
      </div>
      <div class="mb-3">
        <label class="form-label">Message File (.txt)</label>
        <input type="file" name="txtFile" class="form-control" required>
      </div>
      <div class="mb-3">
        <label class="form-label">Interval (seconds)</label>
        <input type="number" name="interval" class="form-control" value="5">
      </div>
      <button class="btn btn-success w-100">Start Messaging</button>
    </form>
  </div>
</body>
</html>
""")

# -----------------------
# Render Port
# -----------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
