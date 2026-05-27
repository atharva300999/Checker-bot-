from flask import Flask, jsonify
import threading
import os
from datetime import datetime

app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({
        "status": "online",
        "message": "Crunchyroll Checker Bot is running!",
        "time": datetime.now().isoformat(),
        "admins": [6820734853, 6347503861]
    })

@app.route('/health')
def health():
    return jsonify({"status": "healthy"})

def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def start():
    thread = threading.Thread(target=run)
    thread.daemon = True
    thread.start()
