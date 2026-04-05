import os

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8500256065:AAHqhuzaTUEf46ukU33OKYv-QhoQpyFCb5s")
PORT      = int(os.environ.get("PORT", 3000))
PROXY_URL = os.environ.get("PROXY_URL", f"http://localhost:{PORT}")
MONGO_URI = os.environ.get("MONGO_URI", "")
CLEANUP_INTERVAL = 300

# ── Admin List ─────────────────────────────────────────────────────────────────
# Add Telegram user IDs of admins here (integers, not usernames)
# To find your ID: message @userinfobot on Telegram
# You can add up to 10-15 admins easily
ADMIN_IDS = [
    8255018518,   # Admin 1 — replace with real Telegram user ID
    6811587584,   # Admin 2 — replace with real Telegram user ID
    # 111111111, # Admin 3  <- remove # to activate
    # 222222222, # Admin 4
    # 333333333, # Admin 5
    # 444444444, # Admin 6
    # 555555555, # Admin 7
    # 666666666, # Admin 8
    # 777777777, # Admin 9
    # 888888888, # Admin 10
]

# Admin contact shown to non-admin users
ADMIN_CONTACT = "@C4DX1"

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is not set!")
if not MONGO_URI:
    raise ValueError("MONGO_URI is not set!")
