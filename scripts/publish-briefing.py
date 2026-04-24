#!/usr/bin/env python3
"""
Publish-Skript für das Morning Briefing.

Ablauf:
	1. Liest das rohe HTML (index.raw.html im Repo-Root).
	2. Archiviert ein ggf. bestehendes index.html nach archiv/YYYY-MM-DD.html
	   (Datum = mtime der alten Datei).
	3. Verschlüsselt das rohe HTML mit staticrypt (via npx) und schreibt
	   das Ergebnis nach index.html.
	4. Löscht die Rohdatei.
	5. Committet und pusht die Änderungen.

Vorbedingungen:
	- ENV BRIEFING_PASSWORD enthält das Passwort für staticrypt.
	- ENV GITHUB_TOKEN enthält einen PAT mit write-Zugriff auf das Repo
	  (wird verwendet, um die Remote-URL für den Push zu setzen).
	- npx ist verfügbar (Node.js).

Aufruf:
	python scripts/publish-briefing.py [raw_html_path]

Default raw_html_path: index.raw.html im Repo-Root.
"""

import os
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_RAW = REPO_ROOT / "index.raw.html"
FINAL_HTML = REPO_ROOT / "index.html"
ARCHIV_DIR = REPO_ROOT / "archiv"
REPO_URL = "github.com/hansiditer12-design/morning-briefing.git"


def fail(msg: str, code: int = 1) -> None:
	print(f"[publish] FEHLER: {msg}", file=sys.stderr)
	sys.exit(code)


def run(cmd: list[str], check: bool = True, **kwargs) -> subprocess.CompletedProcess:
	print(f"[publish] $ {' '.join(cmd)}")
	return subprocess.run(cmd, check=check, cwd=REPO_ROOT, **kwargs)


def archive_previous() -> None:
	"""Verschiebt ein bestehendes index.html nach archiv/YYYY-MM-DD.html."""
	if not FINAL_HTML.exists():
		print("[publish] kein bestehendes index.html, nichts zu archivieren")
		return
	mtime = datetime.fromtimestamp(FINAL_HTML.stat().st_mtime)
	archive_name = mtime.strftime("%Y-%m-%d") + ".html"
	ARCHIV_DIR.mkdir(parents=True, exist_ok=True)
	target = ARCHIV_DIR / archive_name
	# Falls am gleichen Tag schon archiviert wurde, mit Suffix versehen
	suffix = 1
	while target.exists():
		target = ARCHIV_DIR / f"{mtime.strftime('%Y-%m-%d')}-{suffix}.html"
		suffix += 1
	shutil.move(str(FINAL_HTML), str(target))
	print(f"[publish] altes Briefing archiviert nach {target.relative_to(REPO_ROOT)}")


def encrypt(raw_path: Path, password: str) -> None:
	"""Verschlüsselt raw_path mit staticrypt und schreibt das Ergebnis nach FINAL_HTML."""
	with tempfile.TemporaryDirectory() as tmp:
		tmp_path = Path(tmp)
		# staticrypt -d <dir> -p <pw> --short <input>
		# Ergebnis liegt in <dir> unter gleichem Dateinamen
		cmd = [
			"npx", "--yes", "staticrypt",
			str(raw_path),
			"-p", password,
			"-d", str(tmp_path),
			"--short",
		]
		result = run(cmd, check=False)
		if result.returncode != 0:
			fail(f"staticrypt fehlgeschlagen (exit {result.returncode})")
		produced = tmp_path / raw_path.name
		if not produced.exists():
			# manche staticrypt-Versionen behalten nur Stem und hängen .html an
			alt = tmp_path / (raw_path.stem + ".html")
			if alt.exists():
				produced = alt
			else:
				fail(f"staticrypt hat keine Datei in {tmp_path} erzeugt")
		shutil.move(str(produced), str(FINAL_HTML))
		print(f"[publish] verschlüsselte Datei nach {FINAL_HTML.relative_to(REPO_ROOT)} geschrieben")


def configure_git_remote(token: str) -> None:
	"""Setzt die Remote-URL mit Token, damit Push ohne interaktive Auth funktioniert."""
	url = f"https://x-access-token:{token}@{REPO_URL}"
	run(["git", "remote", "set-url", "origin", url])


def commit_and_push() -> None:
	run(["git", "add", "index.html", "archiv/"])
	# nur committen, wenn es etwas zu committen gibt
	status = subprocess.run(
		["git", "status", "--porcelain"],
		cwd=REPO_ROOT, capture_output=True, text=True, check=True,
	).stdout.strip()
	if not status:
		print("[publish] keine Änderungen zu committen")
		return
	today = datetime.now().strftime("%Y-%m-%d")
	run(["git", "commit", "-m", f"briefing {today}"])
	# Push mit bis zu 3 Retries
	for attempt in range(1, 4):
		result = run(["git", "push", "origin", "main"], check=False)
		if result.returncode == 0:
			return
		print(f"[publish] Push-Versuch {attempt} fehlgeschlagen, retry in 5s")
		time.sleep(5)
	fail("git push nach 3 Versuchen fehlgeschlagen")


def main() -> None:
	raw_path = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else DEFAULT_RAW
	if not raw_path.exists():
		fail(f"raw HTML nicht gefunden: {raw_path}")

	password = os.environ.get("BRIEFING_PASSWORD")
	if not password:
		fail("ENV BRIEFING_PASSWORD nicht gesetzt")

	token = os.environ.get("GITHUB_TOKEN")
	if not token:
		fail("ENV GITHUB_TOKEN nicht gesetzt (PAT mit contents:write)")

	archive_previous()
	encrypt(raw_path, password)
	# Rohdatei entfernen (auch wenn sie durch .gitignore ohnehin nicht gepusht wird)
	try:
		raw_path.unlink()
	except FileNotFoundError:
		pass

	configure_git_remote(token)
	commit_and_push()
	print("[publish] fertig")


if __name__ == "__main__":
	main()
