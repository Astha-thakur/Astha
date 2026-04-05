import uuid, secrets, time
from pymongo import MongoClient
import config

_db = None

def get_db():
    global _db
    if _db is None:
        _db = MongoClient(config.MONGO_URI)["tempapi_bot"]
    return _db

def _gen():
    return "tapi-" + secrets.token_hex(16)

# ── Key banao ──────────────────────────────────────────────────────────────────
def create_key(user_id, original_url, expires_at, credit_name="@TempAPI"):
    db  = get_db()
    kid = str(uuid.uuid4())
    tmp = _gen()
    doc = {
        "_id":          kid,
        "user_id":      user_id,
        "temp_key":     tmp,
        "original_url": original_url,
        "credit_name":  credit_name,     # user ka custom credit naam
        "expires_at":   expires_at,
        "used_calls":   0,
        "created_at":   time.time(),
    }
    db.keys.insert_one(doc)
    return doc

# ── User ki keys ───────────────────────────────────────────────────────────────
def get_user_keys(user_id):
    return sorted(
        list(get_db().keys.find({"user_id": user_id})),
        key=lambda k: k["created_at"], reverse=True
    )

# ── Temp key se dhundo ─────────────────────────────────────────────────────────
def find_by_temp_key(tmp):
    return get_db().keys.find_one({"temp_key": tmp})

def increment_usage(tmp):
    get_db().keys.update_one({"temp_key": tmp}, {"$inc": {"used_calls": 1}})

def delete_key(user_id, kid):
    res = get_db().keys.delete_one({"_id": kid, "user_id": user_id})
    return res.deleted_count > 0

def cleanup_expired():
    res = get_db().keys.delete_many({"expires_at": {"$lt": time.time()}})
    if res.deleted_count:
        print(f"🧹 {res.deleted_count} expired keys removed")
