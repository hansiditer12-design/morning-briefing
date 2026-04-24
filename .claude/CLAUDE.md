# CLAUDE.md – Morning Briefing

## Zweck

Tägliches, passwortgeschütztes HTML-Briefing für Florian.
Wird werktags um 6:45 Europe/Berlin durch einen scheduled Remote Agent erzeugt und gepusht.

## Struktur

- `templates/briefing-template.html` — HTML-Gerüst mit Markern `{{DATUM}}`, `{{WETTER_BLOCK}}` etc.
- `assets/style.css` — Styling (Light/Dark, druckfreundlich)
- `scripts/publish-briefing.py` — verschlüsselt, archiviert, committet, pusht
- `archiv/` — alte Briefings als `YYYY-MM-DD.html`
- `index.html` — aktuelles Briefing (verschlüsselt, GitHub Pages)
- `index.raw.html` — unverschlüsselte Zwischendatei (durch .gitignore ausgeschlossen)

## Ablauf (Remote Agent)

1. Recherche: WebSearch/WebFetch für alle Sektionen + Wetter.
2. `templates/briefing-template.html` laden, Marker ersetzen.
3. Ergebnis als `index.raw.html` schreiben.
4. `python scripts/publish-briefing.py` ausführen.

## Vorbedingungen des Skripts

- `BRIEFING_PASSWORD` (ENV) — Passwort für staticrypt
- `GITHUB_TOKEN` (ENV) — PAT mit contents:write auf dieses Repo
- Node.js verfügbar (für `npx --yes staticrypt`)

## Nichts manuell editieren

`index.html` und alle Dateien in `archiv/` werden automatisch generiert.
