# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Projekt

Jekyll-basierte Community-Website für die Bürgerrunde Heuweiler e.V. Gehostet auf Netlify unter https://buergerrunde.heuweiler.net. Sprache: Deutsch.

## Befehle

```bash
# Entwicklung
bundle exec jekyll serve --livereload    # Dev-Server auf localhost:4000

# Build
bundle exec jekyll build                 # Lokaler Build
JEKYLL_ENV=production bundle exec jekyll build  # Produktions-Build (Netlify)

# Locations (OpenAI-basierte Generierung)
rake locations:generate                  # Bis zu 10 Locations aus orte_heuweiler.txt generieren
rake locations:test['Ortsname']          # Einzelne Location testen
rake locations:list                      # Verfügbare Orte anzeigen
rake locations:geocode                   # Koordinaten via Nominatim aktualisieren

# Bildverarbeitung
rake images:optimize                     # JPGs >800px verkleinern
rake images:convert_heic_to_jpg          # HEIC zu JPG konvertieren
```

## Systemvoraussetzungen

- Ruby 3.2.x (exakt 3.2.9, siehe `.ruby-version`)
- Bundler (`bundle install`)
- ImageMagick (für `mini_magick` / Bildverarbeitung)
- `.env`-Datei mit `OPENAI_API_KEY` für Location-Generierung

## Architektur

**Content-Typen:**
- `_posts/YYYY/` — Blogbeiträge (~200), organisiert nach Jahr
- `_locations/` — AI-generierte Ortsbeschreibungen (~107), eigene Jekyll-Collection
- `_pages/` — Statische Seiten (About, Kontakt, Events, Datenschutz etc.)

**Layout-Hierarchie:** `default.html` (Bootstrap 4 Basis) → `post.html`, `page.html`, `locations.html`, `map.html`, Archive-Layouts

**Plugins:**
- `_plugins/german_date_filter.rb` — Deutsche Datumsformatierung
- `_plugins/liquid_frozen_string_patch.rb` — Frozen-String-Kompatibilität

**AI-Location-Pipeline:** `lib/location_generator.rb` liest Ortsnamen aus `orte_heuweiler.txt`, generiert via OpenAI strukturierte Markdown-Dateien mit YAML-Frontmatter (Koordinaten, Kategorien, Beschreibung) nach `_locations/`.

## SEO-Konfiguration

- Location-Seiten sind bewusst von Google-Index und Sitemap ausgeschlossen (`noindex,nofollow` in `_config.yml` defaults + `robots.txt`)
- `jekyll-seo-tag` für Meta-Tags, `jekyll-sitemap` für Sitemap
- Google Search Console Verifizierung via `googleXXX.html`

## Deployment

Netlify baut automatisch bei Push auf `master`. Konfiguration in `netlify.toml`. Netlify Image CDN liefert responsive Bilder für `/assets/images/locations/`.

## Konventionen

- Commit-Messages: Conventional Commits (`feat:`, `fix:`, `chore:`)
- Post-Frontmatter: `layout`, `author`, `category`, `tags`, optional `toc`, `rating`, `search`
- Kategorien definiert in `_data/categories.yml`
