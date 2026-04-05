import time, threading, logging, re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters,
)
import config, db
from proxy import app as flask_app

logging.basicConfig(format="%(asctime)s | %(levelname)s | %(message)s", level=logging.INFO)
log = logging.getLogger(__name__)

# ── State ──────────────────────────────────────────────────────────────────────
_state = {}
def set_state(cid, s): _state[cid] = s
def get_state(cid):    return _state.get(cid)
def clear_state(cid):  _state.pop(cid, None)

# ── Admin Check ────────────────────────────────────────────────────────────────
def is_admin(user_id: int) -> bool:
    return user_id in config.ADMIN_IDS

async def reject_non_admin(update: Update):
    await update.message.reply_text(
        "🚫 *Access Denied*\n\n"
        "You are not an admin, so you cannot use this bot.\n"
        f"Please contact the admin: {config.ADMIN_CONTACT}",
        parse_mode="Markdown",
    )

# ── Helpers ────────────────────────────────────────────────────────────────────
def parse_expiry(text):
    text = text.strip().lower()
    units = {"m": 60, "h": 3600, "d": 86400}
    if len(text) < 2 or text[-1] not in units:
        return None
    try:
        val = int(text[:-1])
        return time.time() + val * units[text[-1]] if val > 0 else None
    except:
        return None

def time_left(exp):
    diff = exp - time.time()
    if diff <= 0: return "❌ Expired"
    h, m = int(diff // 3600), int((diff % 3600) // 60)
    return f"{h}h {m}m remaining" if h else f"{m}m remaining"

# ── /start ─────────────────────────────────────────────────────────────────────
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return await reject_non_admin(update)
    clear_state(update.effective_chat.id)
    await update.message.reply_text(
        "👋 *TempAPI Bot*\n\n"
        "Give any API URL — you will get a temporary link.\n"
        "When time runs out → link expires automatically ✅\n\n"
        "━━━━━━━━━━━━━━━\n"
        "🔑 /newkey — Create a new temp link\n"
        "📋 /mykeys — View your keys\n"
        "🗑 /deletekey — Delete a key\n"
        "ℹ️ /help — Help\n"
        "━━━━━━━━━━━━━━━",
        parse_mode="Markdown",
    )

# ── /help ──────────────────────────────────────────────────────────────────────
async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return await reject_non_admin(update)
    await update.message.reply_text(
        "*How to use:*\n\n"
        "1️⃣  Type /newkey\n"
        "2️⃣  Send your original API URL\n"
        "3️⃣  Set your credit name\n"
        "4️⃣  Set expiry time\n"
        "5️⃣  Get your temp link!\n\n"
        "*Example:*\n"
        "Original URL:\n"
        "`https://example-api.com/data?key=YOUR_KEY&phone={phone}`\n\n"
        "You will get a temp link:\n"
        f"`{config.PROXY_URL}/tapi-xxxx`\n\n"
        "How to use it:\n"
        f"`{config.PROXY_URL}/tapi-xxxx?phone=919876543210`\n\n"
        "_(Works exactly like the original URL — but your key is hidden)_\n\n"
        "*Expiry formats:*\n"
        "`30m`  `2h`  `1d`  `7d`",
        parse_mode="Markdown",
    )

# ── /newkey — Step 1: Ask for URL ──────────────────────────────────────────────
async def cmd_newkey(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return await reject_non_admin(update)
    cid = update.effective_chat.id
    clear_state(cid)
    set_state(cid, {"step": "url"})
    await update.message.reply_text(
        "🔗 *Step 1/3 — Original API URL*\n\n"
        "Send your original API URL.\n\n"
        "*Example:*\n"
        "`https://example-api.com/data?key=YOUR_KEY&phone={phone}`\n\n"
        "_(Include all parameters correctly)_",
        parse_mode="Markdown",
    )

# ── /mykeys ────────────────────────────────────────────────────────────────────
async def cmd_mykeys(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return await reject_non_admin(update)
    keys = db.get_user_keys(update.effective_chat.id)
    if not keys:
        return await update.message.reply_text("No keys found. Create one with /newkey.")
    for k in keys:
        temp_link = f"{config.PROXY_URL}/{k['temp_key']}"
        await update.message.reply_text(
            f"🔑 *Temp Key*\n"
            f"Status: {time_left(k['expires_at'])}\n"
            f"Calls: {k['used_calls']}\n"
            f"Credit: `{k.get('credit_name', 'N/A')}`\n\n"
            f"*Temp Link:*\n`{temp_link}`\n\n"
            f"*Original URL:*\n`{k['original_url']}`",
            parse_mode="Markdown",
        )

# ── /deletekey ─────────────────────────────────────────────────────────────────
async def cmd_deletekey(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return await reject_non_admin(update)
    cid  = update.effective_chat.id
    keys = [k for k in db.get_user_keys(cid) if time.time() <= k["expires_at"]]
    if not keys:
        return await update.message.reply_text("No active keys found.")
    buttons = [[InlineKeyboardButton(
        f"🗑 {k['temp_key'][:16]}... — {time_left(k['expires_at'])}",
        callback_data=f"del_{k['_id']}"
    )] for k in keys]
    await update.message.reply_text("Which key do you want to delete?",
        reply_markup=InlineKeyboardMarkup(buttons))

async def cb_delete(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if not is_admin(q.from_user.id):
        return await q.edit_message_text("🚫 Access Denied. You are not an admin.")
    ok = db.delete_key(q.message.chat.id, q.data.replace("del_", ""))
    await q.edit_message_text("✅ Key deleted!" if ok else "❌ Key not found.")

# ── Message handler — 3-step wizard ───────────────────────────────────────────
async def on_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return await reject_non_admin(update)

    cid   = update.effective_chat.id
    state = get_state(cid)
    if not state:
        return await update.message.reply_text("Type /newkey to create a new key.")
    text = (update.message.text or "").strip()

    # ── Step 1 — URL ──
    if state["step"] == "url":
        if not text.startswith("http"):
            return await update.message.reply_text("❌ URL must start with http:// or https://")

        # Detect @username style credential: e.g. key=@CYBER
        credit_match = re.search(r'(\w+)=@([\w]+)', text)
        if credit_match:
            param_name = credit_match.group(1)
            at_value   = credit_match.group(2)
            state["original_url"] = text
            state["credit_param"] = param_name
            state["credit_at"]    = at_value
            state["step"] = "api_cred"
            return await update.message.reply_text(
                f"🔐 *Credential Detected*\n\n"
                f"Your URL has `{param_name}=@{at_value}`\n\n"
                f"What value should replace `@{at_value}`?\n"
                f"_(Send your actual API key / credential)_",
                parse_mode="Markdown",
            )

        state["original_url"] = text
        state["step"] = "credit"
        return await update.message.reply_text(
            "✏️ *Step 2/3 — Your Credit Name*\n\n"
            "What name should appear as `credit` in the API response?\n\n"
            "*Example:* `@YourName` or `My API Service`\n\n"
            "_(This replaces any existing branding/credit in the original API response)_",
            parse_mode="Markdown",
        )

    # ── Step 1b — API credential replacement ──
    if state["step"] == "api_cred":
        real_value = text
        param_name = state["credit_param"]
        at_value   = state["credit_at"]
        state["original_url"] = state["original_url"].replace(
            f"{param_name}=@{at_value}",
            f"{param_name}={real_value}"
        )
        state.pop("credit_param", None)
        state.pop("credit_at", None)
        state["step"] = "credit"
        return await update.message.reply_text(
            "✅ API credential saved!\n\n"
            "✏️ *Step 2/3 — Your Credit Name*\n\n"
            "What name should appear as `credit` in the API response?\n\n"
            "*Example:* `@YourName` or `My API Service`\n\n"
            "_(This replaces any existing branding/credit in the original API response)_",
            parse_mode="Markdown",
        )

    # ── Step 2 — Credit name ──
    if state["step"] == "credit":
        state["credit_name"] = text
        state["step"] = "expiry"
        return await update.message.reply_text(
            f"✅ Credit set to: `{text}`\n\n"
            "⏰ *Step 3/3 — Expiry Time*\n\n"
            "`30m` = 30 minutes\n"
            "`2h`  = 2 hours\n"
            "`1d`  = 1 day\n"
            "`7d`  = 7 days",
            parse_mode="Markdown",
        )

    # ── Step 3 — Expiry → Done ──
    if state["step"] == "expiry":
        expires_at = parse_expiry(text)
        if not expires_at:
            return await update.message.reply_text("❌ Wrong format. Example: 30m / 2h / 1d / 7d")

        key = db.create_key(
            user_id      = cid,
            original_url = state["original_url"],
            expires_at   = expires_at,
            credit_name  = state.get("credit_name", "@TempAPI"),
        )
        clear_state(cid)

        temp_link = f"{config.PROXY_URL}/{key['temp_key']}"

        placeholders = re.findall(r'\{(\w+)\}', state["original_url"])
        example = temp_link
        if placeholders:
            example_params = "&".join(f"{p}=VALUE" for p in placeholders)
            example = f"{temp_link}?{example_params}"

        await update.message.reply_text(
            f"✅ *Temp API Link Ready!*\n\n"
            f"⏰ Expiry: *{time_left(expires_at)}*\n"
            f"🏷 Credit: `{key['credit_name']}`\n\n"
            f"━━━━━━━━━━━━━━━\n"
            f"🔗 *Temp Link:*\n`{temp_link}`\n\n"
            f"*Usage example:*\n`{example}`\n\n"
            f"*Original URL:*\n`{state['original_url']}`\n"
            f"━━━━━━━━━━━━━━━\n"
            f"✅ Works on Chrome, curl, Postman — everywhere\n"
            f"⚠️ Share only this temp link — your original URL stays safe",
            parse_mode="Markdown",
        )

# ── Background ─────────────────────────────────────────────────────────────────
def _flask():
    flask_app.run(host="0.0.0.0", port=config.PORT, threaded=True)

def _cleanup():
    while True:
        time.sleep(config.CLEANUP_INTERVAL)
        db.cleanup_expired()

# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    threading.Thread(target=_flask, daemon=True).start()
    threading.Thread(target=_cleanup, daemon=True).start()

    app = Application.builder().token(config.BOT_TOKEN).build()
    app.add_handler(CommandHandler("start",     cmd_start))
    app.add_handler(CommandHandler("help",      cmd_help))
    app.add_handler(CommandHandler("newkey",    cmd_newkey))
    app.add_handler(CommandHandler("mykeys",    cmd_mykeys))
    app.add_handler(CommandHandler("deletekey", cmd_deletekey))
    app.add_handler(CallbackQueryHandler(cb_delete, pattern=r"^del_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))

    log.info("🤖 Bot is running...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
