# keep_alive.py
from flask import Flask
import threading
import os

app = Flask('')

@app.route('/')
def home():
    return "Bot is alive!"

def keep_alive():
    port = int(os.environ.get("PORT", 8080))
    thread = threading.Thread(target=lambda: app.run(host='0.0.0.0', port=port))
    thread.daemon = True
    thread.start()
    print(f"[KeepAlive] Running on port {port}")