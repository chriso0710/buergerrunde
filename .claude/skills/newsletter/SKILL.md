---
name: newsletter
description: >-
  Erstellt oder aktualisiert einen Bürgerrunde-Heuweiler-Newsletter als Brevo-Entwurf.
  Nutzen, wenn der User einen Newsletter bauen, aktualisieren, Posts sammeln, den Stil
  der alten Newsletter treffen, Kontakte zur Liste hinzufügen oder Brevo-Kampagnen
  auslesen möchte. Deckt Brevo-API (Kampagnen, Listen, Kontakte), Design-Tokens,
  CTA-Buttons, Logo und Footer ab.
---

# Bürgerrunde-Newsletter (Brevo)

Baut Newsletter für die Bürgerrunde Heuweiler als **Entwurf** in Brevo. Niemals selbst versenden – der Vorstand prüft und sendet in Brevo.

## Grundregeln (wichtig)

1. **API-Calls immer über `python3`**, nie `curl` mit Shell-Variablen. Sobald `$BREVO_API` o. ä. in der Kommandozeile steht, meldet Claude Code „contains simple expansion"/„command substitution" und fragt nach. In Python `os.environ["BREVO_API"]` lesen → kein Prompt. Der Key liegt dank `mise.toml` (`[env] _.file=".env"`) automatisch in jeder Shell.
2. **Immer als Draft anlegen** – kein `scheduledAt` setzen. Ohne `scheduledAt` bleibt die Kampagne `draft` und wird nicht versendet.
3. **IP-Whitelist:** Brevo blockt neue IPs. Bei Fehler `unauthorised IP`/`unauthorized` muss der User die genannte IP unter https://app.brevo.com/security/authorised_ips freigeben.

## Brevo-API-Cheatsheet

Endpoint-Basis `https://api.brevo.com/v3`, Header `api-key: <BREVO_API>`, `accept: application/json`.

| Zweck | Methode + Pfad |
|---|---|
| Kampagnen auflisten | `GET /emailCampaigns?limit=15&sort=desc` |
| Kampagne inkl. `htmlContent` | `GET /emailCampaigns/{id}` |
| Kampagne (Draft) anlegen | `POST /emailCampaigns` |
| Kampagne aktualisieren | `PUT /emailCampaigns/{id}` (HTTP 204) |
| Kontaktlisten | `GET /contacts/lists` |
| Kontakt anlegen/zu Liste | `POST /contacts` `{email, listIds:[3], updateEnabled:true}` |
| Account prüfen | `GET /account` |

**Feste Werte im Konto:**
- **Empfängerliste (echt):** `id 3` = „Bürgerrunde komplett" (~370–410 Kontakte). `id 2` = „Test".
- **Absender:** `id 2` = `vorstand@heuweiler.net`. Beim Anlegen/Update **Name explizit mitgeben**, sonst zeigt Brevo `[DEFAULT_FROM_NAME]`:
  `"sender": {"name": "Bürgerrunde Heuweiler", "email": "vorstand@heuweiler.net"}`

## Content zusammenstellen

1. **Letzten Versand finden:** `GET /emailCampaigns` → jüngste Kampagne mit `status: sent` und ihr `sentDate`.
2. **Neue Posts finden:** `_posts/YYYY/*.md` mit Datum (aus Dateiname) **nach** dem letzten Versanddatum.
3. **Auswählen:** kommende Termine (zeitkritisch zuerst), aktuelle News, Evergreens. **Vergangene Termine weglassen** (heutiges Datum beachten!). Rückblicke nur, wenn relevant.
4. **Pro Post ein Block:** Bild → Überschrift → 2–3 Sätze Teaser → CTA-Button „Mehr lesen".
5. **Betreffzeile** = Semikolon-Liste aller Themen (Stil der alten Newsletter), z. B.
   `Fahrrad-Schraubkurs am 23.7.; Bürgerbus mit neuem Fahrplan; Dorfflohmarkt am 19.9.; …`
6. **Post-URL:** Permalink ist `/:title/` → `https://buergerrunde.heuweiler.net/<slug>/` (Slug = Dateiname ohne Datum/Endung). Vor Nutzung mit HEAD auf 200 prüfen.
7. **Bilder:** absolute URLs von der Live-Site (`image:`-Frontmatter des Posts, Domain davor). Immer auf HTTP 200 prüfen.

**Tonalität:** Du/Ihr, warm, einladend („Kommt vorbei", „Wir freuen uns"). Immer konkret mit **Datum, Uhrzeit, Ort** (meist Café IZ). Themenwelt: Naturschutz, Energie, Kultur, Mobilität, Gemeinschaft.

## Design-Tokens (aus den alten Newslettern kalibriert)

| Element | Wert |
|---|---|
| Akzent / Buttons / Links | `#f74d36` (Orange-Rot) |
| Seiten-Hintergrund | `#eff2f7` |
| Inhaltsfläche | `#ffffff` |
| Fließtext | `#3b3f44`, 16px, line-height 1.6 |
| Überschriften | `#1f2d3d`, 24px bold (Haupttitel 32px) |
| Footer / dezent | `#8a8f96`, 13–14px |
| Schrift | `arial,helvetica,sans-serif` |
| Breite | 600px zentriert, Blöcke 24px seitliches Padding |

**CTA-Buttons:** echte Tabellen-Buttons, `bgcolor=#f74d36`, `border-radius:4px`, weiße 16px-Bold-Schrift, Padding `12px 26px`. Keine reinen Text-Links.

**Logo:** `https://buergerrunde.heuweiler.net/assets/images/br_logo_email.png` (aus `br_logo.svg` gerendert, transparent). Rund, zentriert, ~140px.
⚠️ **Kein SVG im E-Mail-`<img>`** – Gmail/Outlook/Webmail zeigen SVG nicht. Bei Logo-Änderung neu aus SVG rendern:
`rsvg-convert -w 1000 assets/images/br_logo.svg -o assets/images/br_logo_email.png`, committen, pushen, auf Live-200 warten.

**Footer (Pflicht, Vorbild = alte Newsletter):**
- `Im Browser öffnen` → `{{ mirror }}` | `Newsletter abbestellen` → `{{ unsubscribe }}`
- `Impressum` → `/imprint` | `Datenschutz` → `/privacy`
- „Bürgerrunde Heuweiler e.V." + „Diese E-Mail wurde an {{ contact.EMAIL }} gesendet."
- Der `{{ unsubscribe }}`-Link ist zwingend (DSGVO/Brevo). Merge-Tags `{{ }}` literal ins HTML.

## Build-Script

`build_newsletter.py` in diesem Skill-Ordner ist eine anpassbare Vorlage: `blocks`-Liste füllen, `SUBJECT` setzen, `CAMPAIGN_ID` leer lassen (→ `POST`, neuer Draft) oder auf eine ID setzen (→ `PUT`, bestehenden Draft aktualisieren). Danach in Brevo Vorschau/Test-Mail prüfen.

Nach dem Anlegen: Kampagne-ID nennen und Link `https://app.brevo.com/marketing-campaigns/classic/edit/<id>` geben.
