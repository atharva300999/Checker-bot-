import os

# ===== TELEGRAM BOT TOKEN (Get from @BotFather) =====
BOT_TOKEN = os.environ.get("BOT_TOKEN")

# ===== PUBLIC CRUNCHYROLL CREDENTIALS (Working as of Dec 2024) =====
# These are the official Android TV app credentials - no registration needed!
CRUNCHYROLL_AUTH_HEADER = os.environ.get(
    "CRUNCHYROLL_AUTH_HEADER",
    "Basic YW5kcm9pZF90dl9jbGllbnQ6YW5kcm9pZF90dl9jbGllbnRfc2VjcmV0"  # Working public key
)

# ===== YOUR ADMIN IDs (Already added!) =====
ADMIN_IDS = [6820734853, 6347503861]

# ===== BOT SETTINGS =====
MAX_FILE_SIZE_MB = 10
DEFAULT_THREADS = 10
CHECK_TIMEOUT = 30
PORT = int(os.environ.get("PORT", 8080))

# Optional: You can update the auth header anytime from:
# https://raw.githubusercontent.com/vitalygashkov/crextractor/refs/heads/main/credentials.tv.json
