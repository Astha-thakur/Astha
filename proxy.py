import time, requests, json, re
from flask import Flask, request, Response, jsonify
import db, config

app = Flask(__name__)

# Fields jo original API ke response se hata dene hain
STRIP_FIELDS = {"branding", "credit", "buy", "api", "powered_by", "credits", "owner", "seller"}

@app.after_request
def cors(r):
    r.headers["Access-Control-Allow-Origin"]  = "*"
    r.headers["Access-Control-Allow-Headers"] = "*"
    r.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    return r

@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "ok", "bot": "TempAPI Bot ✅"})

def clean_json(data: dict, user_credit: str) -> dict:
    """
    - Top-level STRIP_FIELDS hata do
    - Agar koi nested dict mein bhi branding/credit ho, woh bhi hata do
    - End mein user ka credit naam add karo
    """
    def strip_nested(obj):
        if isinstance(obj, dict):
            return {k: strip_nested(v) for k, v in obj.items() if k.lower() not in STRIP_FIELDS}
        if isinstance(obj, list):
            return [strip_nested(i) for i in obj]
        return obj

    cleaned = strip_nested(data)
    # User ka apna credit daalo
    cleaned["credit"] = user_credit
    return cleaned

# ── Main proxy route ───────────────────────────────────────────────────────────
@app.route("/<temp_key>", methods=["GET", "OPTIONS"])
def proxy(temp_key):
    if request.method == "OPTIONS":
        return Response("", status=204)

    # Key validate karo
    key_obj = db.find_by_temp_key(temp_key)

    if not key_obj:
        return jsonify({"error": "Invalid key", "msg": "This temp key does not exist"}), 401

    if time.time() > key_obj["expires_at"]:
        return jsonify({"error": "Key expired", "msg": "This temp key has expired"}), 401

    original_url = key_obj["original_url"]
    user_credit  = key_obj.get("credit_name", "@TempAPI")   # user ka set kiya naam

    # Query params forward karo
    user_params = dict(request.args)

    final_url = original_url
    for param, value in user_params.items():
        final_url = final_url.replace(f"{{{param}}}", value)

    remaining_placeholders = re.findall(r'\{(\w+)\}', final_url)
    extra_params = {k: v for k, v in user_params.items() if k not in remaining_placeholders}

    # Forward karo
    try:
        resp = requests.get(final_url, params=extra_params, timeout=30)
        db.increment_usage(temp_key)

        content_type = resp.headers.get("Content-Type", "")

        # Agar JSON response hai — clean karo aur credit replace karo
        if "json" in content_type or resp.content.strip().startswith(b"{"):
            try:
                data    = resp.json()
                cleaned = clean_json(data, user_credit)
                return Response(
                    json.dumps(cleaned, ensure_ascii=False, indent=2),
                    status=resp.status_code,
                    content_type="application/json; charset=utf-8"
                )
            except Exception:
                pass  # JSON parse fail hua — raw return karo

        # Non-JSON response as-is
        return Response(resp.content, status=resp.status_code, content_type=content_type)

    except requests.exceptions.Timeout:
        return jsonify({"error": "Timeout", "msg": "Original API did not respond"}), 504
    except Exception as e:
        return jsonify({"error": "Proxy error", "detail": str(e)}), 502
