#!/usr/bin/env python3
"""
bb-alert: avisa por Telegram (mensaje + llamada) cuando aparece un programa
publico nuevo en HackerOne, Bugcrowd, YesWeHack (e Intigriti opcional).

Fuente de datos: https://github.com/arkadiyt/bounty-targets-data
(se actualiza cada ~30 min con todos los programas publicos).

Estado: seen.json guarda las claves de todos los programas ya vistos.
Solo crece (nunca se borra nada), asi que si la fuente falla un dia y luego
vuelven a aparecer los mismos programas, no se re-alerta.

Variables de entorno:
  DATA_DIR           carpeta con los *_data.json (por defecto ./btd/data)
  STATE_FILE         fichero de estado (por defecto ./seen.json)
  PLATFORMS          lista separada por comas (por defecto hackerone,bugcrowd,yeswehack)
  ONLY_BOUNTY        "1" = ignorar VDPs sin recompensa (por defecto "0")
  H1_SUPPRESS_MATURE "1" = no alertar de programas H1 con historial de reportes,
                     es decir re-listados del directorio, no lanzamientos reales
                     (por defecto "1"); se absorben en seen.json igualmente
  TG_BOT_TOKEN       token del bot de Telegram (mensaje con detalles y enlaces)
  TG_CHAT_ID         tu chat_id de Telegram
  CALLMEBOT_USER     tu @usuario de Telegram (o telefono +34...) para la llamada
  CALL_LANG          voz de la llamada (por defecto es-ES-Standard-A)
  NTFY_TOPIC         tema secreto de ntfy.sh para la alarma en el movil
  DRY_RUN            "1" = no envia nada, solo imprime
"""
import json
import os
import sys
import urllib.parse
import urllib.request

DATA_DIR = os.environ.get("DATA_DIR", "btd/data")
STATE_FILE = os.environ.get("STATE_FILE", "seen.json")
PLATFORMS = [p.strip() for p in os.environ.get("PLATFORMS", "hackerone,bugcrowd,yeswehack").split(",") if p.strip()]
ONLY_BOUNTY = os.environ.get("ONLY_BOUNTY", "0") == "1"
DRY_RUN = os.environ.get("DRY_RUN", "0") == "1"
# "1" = no alertar de programas H1 que ya tienen historial de reportes
# (re-listados del directorio, no lanzamientos reales). Los absorbe en seen.
H1_SUPPRESS_MATURE = os.environ.get("H1_SUPPRESS_MATURE", "1") == "1"

# Si una plataforma devuelve menos de este % de los programas ya conocidos,
# asumimos que el scraper de la fuente ha fallado y no la procesamos.
MIN_RATIO = 0.5


def _norm(name, key, url, bounty, max_reward, mature=False):
    return {"name": (name or "").strip(), "key": key, "url": url, "bounty": bounty,
            "max": max_reward, "mature": mature}


def parse_hackerone(d):
    out = []
    for p in d:
        if p.get("submission_state") != "open":
            continue
        # La fuente no trae fecha de lanzamiento. Pero un programa recien
        # lanzado no tiene historial de gestion de reportes: si ya ha
        # respondido o resuelto algun reporte, NO es nuevo (es un re-listado
        # del directorio de H1). Esto filtra falsos positivos tipo Rocket.Chat.
        mature = (p.get("average_time_to_first_program_response") is not None
                  or p.get("average_time_to_report_resolved") is not None)
        out.append(_norm(p["name"], f"h1:{p['handle']}", p["url"],
                         bool(p.get("offers_bounties")), None, mature=mature))
    return out


def parse_bugcrowd(d):
    out = []
    for p in d:
        mp = p.get("max_payout") or 0
        out.append(_norm(p["name"], f"bc:{urllib.parse.urlparse(p['url']).path.rstrip('/')}", p["url"], mp > 0,
                         f"${mp:,}" if mp else None))
    return out


def parse_yeswehack(d):
    out = []
    for p in d:
        if not p.get("public") or p.get("disabled"):
            continue
        mb = p.get("max_bounty") or 0
        out.append(_norm(p["name"], f"ywh:{p['id']}", f"https://yeswehack.com/programs/{p['id']}", mb > 0,
                         f"{mb:,}€" if mb else None))
    return out


def parse_intigriti(d):
    out = []
    for p in d:
        if p.get("status") != "open" or p.get("confidentiality_level") != "public":
            continue
        mb = (p.get("max_bounty") or {}).get("value") or 0
        cur = (p.get("max_bounty") or {}).get("currency", "")
        out.append(_norm(p["name"], f"iti:{p['id']}", p["url"], mb > 0, f"{mb:,} {cur}" if mb else None))
    return out


PARSERS = {
    "hackerone": ("HackerOne", parse_hackerone),
    "bugcrowd": ("Bugcrowd", parse_bugcrowd),
    "yeswehack": ("YesWeHack", parse_yeswehack),
    "intigriti": ("Intigriti", parse_intigriti),
}


def load_state():
    if not os.path.exists(STATE_FILE):
        return None
    with open(STATE_FILE) as f:
        return json.load(f)


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=1, sort_keys=True)
        f.write("\n")


def http_get(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": "bb-alert/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.read().decode("utf-8", "replace")


def send_telegram(text):
    token, chat = os.environ.get("TG_BOT_TOKEN"), os.environ.get("TG_CHAT_ID")
    if not token or not chat:
        print("[i] TG_BOT_TOKEN/TG_CHAT_ID no configurados, salto el mensaje")
        return
    data = urllib.parse.urlencode({
        "chat_id": chat, "text": text, "parse_mode": "HTML", "disable_web_page_preview": "true",
    }).encode()
    req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=data)
    with urllib.request.urlopen(req, timeout=30) as r:
        print(f"[+] Telegram mensaje: HTTP {r.status}")


def send_call(text):
    user = os.environ.get("CALLMEBOT_USER")
    if not user:
        print("[i] CALLMEBOT_USER no configurado, salto la llamada")
        return
    q = urllib.parse.urlencode({
        "user": user, "text": text, "lang": os.environ.get("CALL_LANG", "es-ES-Standard-A"),
    })
    try:
        status, body = http_get(f"https://api.callmebot.com/start.php?{q}", timeout=60)
        print(f"[+] CallMeBot llamada: HTTP {status} {body[:200]!r}")
    except Exception as e:  # no tumbar el job si la llamada falla
        print(f"[!] CallMeBot fallo: {e}")


def send_ntfy(title, body, click_url=None):
    """Alarma en el movil via la app ntfy (prioridad maxima)."""
    topic = os.environ.get("NTFY_TOPIC")
    if not topic:
        print("[i] NTFY_TOPIC no configurado, salto ntfy")
        return
    params = {"title": title, "priority": "5", "tags": "rotating_light"}
    if click_url:
        params["click"] = click_url
    url = f"https://ntfy.sh/{topic}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, data=body.encode("utf-8"))
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            print(f"[+] ntfy: HTTP {r.status}")
    except Exception as e:
        print(f"[!] ntfy fallo: {e}")


def html_escape(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def main():
    state = load_state()
    first_run = state is None
    state = state or {}
    new = []

    for plat in PLATFORMS:
        if plat not in PARSERS:
            print(f"[!] Plataforma desconocida: {plat}")
            continue
        label, parser = PARSERS[plat]
        path = os.path.join(DATA_DIR, f"{plat}_data.json")
        try:
            with open(path) as f:
                programs = parser(json.load(f))
        except Exception as e:
            print(f"[!] No pude leer {path}: {e}")
            continue

        seen = set(state.get(plat, []))
        if seen and len(programs) < MIN_RATIO * len(seen):
            print(f"[!] {label}: solo {len(programs)} programas vs {len(seen)} conocidos, posible fallo de la fuente; salto")
            continue

        suppressed = 0
        for p in programs:
            if p["key"] in seen:
                continue
            seen.add(p["key"])  # absorbido en estado: no se re-evalua nunca mas
            if H1_SUPPRESS_MATURE and p.get("mature"):
                suppressed += 1  # tiene historial -> no es un lanzamiento real
                continue
            if ONLY_BOUNTY and not p["bounty"]:
                continue
            p["platform"] = label
            new.append(p)
        state[plat] = sorted(seen)
        extra = f", {suppressed} descartados por historial (no nuevos de verdad)" if suppressed else ""
        print(f"[i] {label}: {len(programs)} programas, {len(seen)} conocidos{extra}")

    save_state(state)

    if first_run:
        print("[i] Primera ejecucion: estado inicializado, no se envian alertas")
        return 0
    if not new:
        print("[i] Sin programas nuevos")
        return 0

    lines = [f"🚨 <b>{len(new)} programa(s) nuevo(s)</b>"]
    for p in new:
        tag = "💰 Bounty" + (f" hasta {p['max']}" if p["max"] else "") if p["bounty"] else "🛡️ VDP"
        lines.append(f"\n<b>{html_escape(p['name'])}</b> · {p['platform']}\n{tag}\n{p['url']}")
    msg = "\n".join(lines)

    if len(new) == 1:
        p = new[0]
        call_text = f"Nuevo programa en {p['platform']}: {p['name']}"
    else:
        plats = sorted({p["platform"] for p in new})
        call_text = f"Hay {len(new)} programas nuevos en {', '.join(plats)}"

    print(msg)
    print(f"[call] {call_text}")
    if DRY_RUN:
        return 0
    # Primero el mensaje (con enlaces), luego la llamada para despertarte.
    try:
        send_telegram(msg[:4000])
    except Exception as e:
        print(f"[!] Telegram fallo: {e}")
    ntfy_body = "\n".join(f"{p['name']} ({p['platform']}) {p['url']}" for p in new)
    send_ntfy(call_text, ntfy_body[:3500], new[0]["url"] if len(new) == 1 else None)
    send_call(call_text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
