# DecapCMS Setup für Locations

Dieses Verzeichnis enthält die Konfiguration für DecapCMS, um die Locations zu verwalten.

## Aktivierung mit DecapBridge

DecapBridge ist ein moderner Authentication-Service für DecapCMS, der einfacher zu konfigurieren ist als Netlify Identity und mehr Login-Optionen bietet (Google, Microsoft, etc.).

### 1. Site bei DecapBridge erstellen

1. Gehe zu https://decapbridge.com/
2. Erstelle ein Konto oder melde dich an
3. Klicke auf "Create New Site"
4. Gib folgende Informationen ein:
   - **Site Name**: Bürgerrunde Heuweiler
   - **Repository**: chriso0710/buergerrunde
   - **Branch**: master
   - **Site URL**: https://buergerrunde.heuweiler.net

### 2. Site-ID in config.yml eintragen

1. Kopiere die **Site ID** aus dem DecapBridge Dashboard
2. Öffne `admin/config.yml`
3. Ersetze `YOUR_SITE_ID` in der Zeile:
   ```yaml
   identity_url: https://auth.decapbridge.com/sites/YOUR_SITE_ID
   ```
   mit deiner tatsächlichen Site ID

### 3. Benutzer einladen

1. Gehe im DecapBridge Dashboard zu deiner Site
2. Klicke auf "Invite Users" oder "Manage Users"
3. Gib die E-Mail-Adressen der Redakteure ein
4. Die eingeladenen Benutzer erhalten eine E-Mail mit einem Einladungslink

### 4. GitHub Token erstellen

DecapBridge benötigt einen GitHub Personal Access Token:
1. Gehe zu GitHub → Settings → Developer settings → Personal access tokens → Fine-grained tokens
2. Erstelle einen neuen Token mit Repository access: "Only select repositories" → `chriso0710/buergerrunde`
3. Permissions: Contents (Read and write), Pull requests (Read and write)
4. Trage den Token im DecapBridge Dashboard ein

### 5. CMS aufrufen

Nach erfolgreicher Konfiguration ist das CMS unter folgender URL erreichbar:

```
https://buergerrunde.heuweiler.net/admin/
```

Benutzer können sich mit Google, Microsoft oder E-Mail/Passwort anmelden.

## Lokale Entwicklung

Für die lokale Entwicklung kannst du den DecapCMS Proxy Server verwenden:

1. Installiere den Proxy Server:
```bash
npm install -g decap-server
```

2. In `admin/config.yml` kommentiere die Zeile ein:
```yaml
local_backend: true
```

3. Starte den Proxy Server in einem Terminal:
```bash
npx decap-server
```

4. Starte Jekyll in einem anderen Terminal:
```bash
bundle exec jekyll serve
```

5. Öffne: `http://localhost:4000/admin/`

## Konfiguration

Die Konfiguration befindet sich in `admin/config.yml` und umfasst:

- **Backend**: Git Gateway (über DecapBridge)
- **Collections**: Locations in `_locations/`
- **Media**: Bilder werden in `assets/images/locations/` gespeichert

### Verfügbare Felder

- **Titel**: Name des Ortes (Pflichtfeld)
- **Kategorie**: Auswahl aus 12 vordefinierten Kategorien (Pflichtfeld)
- **Beschreibung**: Kurzbeschreibung (Pflichtfeld)
- **Adresse**: Postadresse
- **Koordinaten**: Latitude/Longitude für Karten
- **Website**: URL der offiziellen Website
- **Bild**: Hauptbild mit Upload-Funktion
- **Bildrechte**: Copyright-Vermerk
- **Inhalt**: Detaillierter Markdown-Content

### Kategorien

- Bauernhöfe
- Geschäfte & Gastronomie
- Handwerk & Gewerbe
- Historische Gebäude
- Infrastruktur
- Naturdenkmäler
- Öffentliche Gebäude
- Religiöse Stätten
- Straßen & Wege
- Veranstaltungsorte
- Vereine
- Wohngebiete

## Workflow

1. Nach dem Login sehen Redakteure alle vorhandenen Locations
2. Neue Locations können über den Button "New Location" erstellt werden
3. Änderungen werden direkt in GitHub committed
4. Netlify baut die Site automatisch neu

## Troubleshooting

### "Error loading config.yml"
- Prüfe die Syntax in `admin/config.yml`
- Stelle sicher, dass die Datei korrekt eingerückt ist (YAML-Syntax)
- Vergewissere dich, dass `YOUR_SITE_ID` durch deine tatsächliche Site ID ersetzt wurde

### "Cannot read collections"
- Prüfe, ob die Site-ID korrekt in der config.yml eingetragen ist
- Stelle sicher, dass DecapBridge Zugriff auf dein GitHub Repository hat
- Prüfe, ob der Branch-Name korrekt ist (master)

### Login funktioniert nicht
- Stelle sicher, dass der Benutzer über DecapBridge eingeladen wurde
- Prüfe, ob der Benutzer die Einladungs-E-Mail erhalten und akzeptiert hat
- Lösche Browser-Cache und Cookies
- Versuche einen anderen Login-Provider (Google, Microsoft, E-Mail)

### "Config validation error"
- Öffne die Browser-Konsole (F12) für detaillierte Fehlermeldungen
- Prüfe, ob alle erforderlichen Felder in der config.yml vorhanden sind

## Vorteile von DecapBridge

- **Einfache Einrichtung**: Keine komplexe OAuth-Konfiguration nötig
- **Mehrere Login-Optionen**: Google, Microsoft, E-Mail/Passwort
- **Benutzer-Management**: Einfaches Einladen und Verwalten von Redakteuren
- **Kein Vendor Lock-in**: Funktioniert mit jedem Git-Provider (GitHub, GitLab, etc.)
- **Kostenlos**: Für die meisten Anwendungsfälle kostenlos nutzbar

## Weitere Informationen

- DecapCMS Dokumentation: https://decapcms.org/docs/
- DecapBridge: https://decapbridge.com/
- GitHub Repository: https://github.com/chriso0710/buergerrunde
