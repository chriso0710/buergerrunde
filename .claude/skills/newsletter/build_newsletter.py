#!/usr/bin/env python3
"""
Bürgerrunde-Newsletter als Brevo-Entwurf bauen.

Vorlage – anpassen und ausführen (python3 build_newsletter.py):
  - SUBJECT, PREVIEW, blocks[] und INTRO/OUTRO befüllen
  - CAMPAIGN_ID = None  -> POST (neuer Draft)
  - CAMPAIGN_ID = 28    -> PUT  (bestehenden Draft aktualisieren)

Key kommt aus os.environ (mise lädt .env). NIE $BREVO_API in die Shell schreiben.
Immer Draft: kein scheduledAt. Versand macht der Vorstand in Brevo.
"""
import os, json, urllib.request, urllib.error

API  = os.environ["BREVO_API"]
BASE = "https://buergerrunde.heuweiler.net"

# ----- Kampagne -----
CAMPAIGN_ID = None  # None = neu anlegen (POST); Zahl = aktualisieren (PUT)
NAME    = "Newsletter <Monat Jahr>"
SUBJECT = "<Thema 1>; <Thema 2>; <Thema 3>"   # Semikolon-Liste aller Themen
PREVIEW = "<kurzer Vorschautext>"
LIST_ID = 3         # 3 = "Bürgerrunde komplett" (echt), 2 = Test
SENDER  = {"name": "Bürgerrunde Heuweiler", "email": "vorstand@heuweiler.net"}

# ----- Design-Tokens (aus alten Newslettern) -----
ACCENT, PAGE_BG, CARD_BG = "#f74d36", "#eff2f7", "#ffffff"
TEXT, HEAD, MUTED = "#3b3f44", "#1f2d3d", "#8a8f96"
FONT = "arial,helvetica,sans-serif"
LOGO = f"{BASE}/assets/images/br_logo_email.png"  # aus SVG gerendert; KEIN .svg im Mail-img

INTRO = ("Liebe Heuweilemer:innen,<br>hier sind unsere aktuellen Themen und Termine. "
         "Viel Freude beim Lesen!")
OUTRO = ("Und nicht vergessen: Unser <strong>Feierabend-Treff</strong> findet weiterhin "
         "einmal im Monat im Caf&eacute; IZ statt &ndash; offen f&uuml;r alle.")

# ----- Inhaltsblöcke (je Post: Bild, Titel, URL, Teaser, CTA) -----
blocks = [
    {
        "img":   f"{BASE}/assets/images/<pfad>.jpg",
        "title": "<Post-Titel>",
        "url":   f"{BASE}/<slug>/",          # Permalink /:title/
        "text":  "<2-3 Sätze Teaser mit Datum, Uhrzeit, Ort.>",
        "cta":   "Mehr lesen",
    },
]

# ----- HTML-Bausteine -----
def button(url, label):
    return f"""
      <table role="presentation" cellspacing="0" cellpadding="0" border="0" style="margin:4px 0 0 0;">
        <tr><td align="center" bgcolor="{ACCENT}" style="background-color:{ACCENT};border-radius:4px;">
          <a href="{url}" target="_blank" style="display:inline-block;padding:12px 26px;font-family:{FONT};font-size:16px;font-weight:bold;color:#ffffff;text-decoration:none;line-height:1.15;">{label}</a>
        </td></tr>
      </table>"""

def block_html(b):
    return f"""
    <tr><td style="padding:0 24px;">
      <a href="{b['url']}" target="_blank" style="text-decoration:none;">
        <img src="{b['img']}" width="552" alt="" style="width:100%;max-width:552px;height:auto;border-radius:6px;display:block;border:0;" />
      </a>
    </td></tr>
    <tr><td style="padding:18px 24px 6px 24px;">
      <h2 style="margin:0;font-size:24px;line-height:1.25;color:{HEAD};font-family:{FONT};font-weight:bold;">
        <a href="{b['url']}" target="_blank" style="color:{HEAD};text-decoration:none;">{b['title']}</a>
      </h2>
    </td></tr>
    <tr><td style="padding:6px 24px 12px 24px;">
      <p style="margin:0;font-size:16px;line-height:1.6;color:{TEXT};font-family:{FONT};">{b['text']}</p>
    </td></tr>
    <tr><td style="padding:0 24px 26px 24px;">{button(b['url'], b['cta'])}</td></tr>
    <tr><td style="padding:0 24px 26px 24px;"><hr style="border:0;border-top:1px solid #e2e6ec;margin:0;" /></td></tr>
    """

def build_html():
    blocks_html = "".join(block_html(b) for b in blocks)
    return f"""<!DOCTYPE html>
<html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:{PAGE_BG};">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{PAGE_BG};">
<tr><td align="center" style="padding:24px 12px;">
  <table role="presentation" width="600" cellpadding="0" cellspacing="0" style="width:600px;max-width:600px;background:{CARD_BG};border-radius:8px;overflow:hidden;">
    <tr><td style="padding:32px 24px 12px 24px;text-align:center;">
      <img src="{LOGO}" width="140" alt="B&uuml;rgerrunde Heuweiler" style="width:140px;max-width:45%;height:auto;display:inline-block;border:0;" />
      <div style="font-size:16px;color:{ACCENT};font-family:{FONT};margin-top:14px;font-weight:bold;">Neues aus dem Dorf</div>
    </td></tr>
    <tr><td style="padding:14px 24px 18px 24px;">
      <p style="margin:0;font-size:16px;line-height:1.6;color:{TEXT};font-family:{FONT};">{INTRO}</p>
    </td></tr>
    <tr><td style="padding:0 24px 24px 24px;"><hr style="border:0;border-top:1px solid #e2e6ec;margin:0;" /></td></tr>
    {blocks_html}
    <tr><td style="padding:18px 24px 22px 24px;">
      <p style="margin:0;font-size:16px;line-height:1.6;color:{TEXT};font-family:{FONT};">{OUTRO}</p>
    </td></tr>
    <tr><td style="padding:22px 24px 30px 24px;background:{PAGE_BG};text-align:center;">
      <p style="margin:0 0 10px 0;font-size:14px;line-height:1.7;color:{MUTED};font-family:{FONT};">
        <a href="{{{{ mirror }}}}" target="_blank" style="color:{ACCENT};text-decoration:underline;">Im Browser &ouml;ffnen</a> |
        <a href="{{{{ unsubscribe }}}}" target="_blank" style="color:{ACCENT};text-decoration:underline;">Newsletter abbestellen</a><br>
        <a href="{BASE}/imprint" target="_blank" style="color:{ACCENT};text-decoration:underline;">Impressum</a> |
        <a href="{BASE}/privacy" target="_blank" style="color:{ACCENT};text-decoration:underline;">Datenschutz</a>
      </p>
      <p style="margin:0;font-size:13px;line-height:1.6;color:{MUTED};font-family:{FONT};">
        B&uuml;rgerrunde Heuweiler e.V.<br>Diese E-Mail wurde an {{{{ contact.EMAIL }}}} gesendet.
      </p>
    </td></tr>
  </table>
</td></tr>
</table>
</body></html>"""

def api(method, path, payload=None):
    req = urllib.request.Request(
        f"https://api.brevo.com/v3{path}",
        data=json.dumps(payload).encode() if payload is not None else None,
        headers={"api-key": API, "content-type": "application/json", "accept": "application/json"},
        method=method)
    try:
        r = urllib.request.urlopen(req)
        body = r.read().decode()
        return r.status, (json.loads(body) if body.strip() else None)
    except urllib.error.HTTPError as e:
        print("ERROR", e.code, e.read().decode()); raise

if __name__ == "__main__":
    html = build_html()
    if CAMPAIGN_ID is None:
        payload = {"name": NAME, "subject": SUBJECT, "sender": SENDER,
                   "htmlContent": html, "recipients": {"listIds": [LIST_ID]},
                   "previewText": PREVIEW, "inlineImageActivation": False}
        status, data = api("POST", "/emailCampaigns", payload)
        print("Angelegt:", status, data)  # {"id": <neu>}
    else:
        payload = {"htmlContent": html, "sender": SENDER, "subject": SUBJECT,
                   "name": NAME, "previewText": PREVIEW}
        status, _ = api("PUT", f"/emailCampaigns/{CAMPAIGN_ID}", payload)
        print("Aktualisiert:", status, "Kampagne", CAMPAIGN_ID)
