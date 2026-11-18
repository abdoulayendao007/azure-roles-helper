#!/usr/bin/env python3
"""Exporte les noms et descriptions FRANÇAISES des rôles intégrés, publiés par Microsoft
sur Microsoft Learn, vers data/descriptions-fr.json.

Sources (traductions de Microsoft) :
- Azure RBAC : tableau récapitulatif de la page « Rôles intégrés Azure » (colonnes Rôle, Description, ID)
- Entra ID   : tableau « Tous les rôles » de la page « Rôles intégrés Microsoft Entra » (colonnes Rôle, Description, ID de modèle)

Chaque description est associée à son rôle par l'ID, jamais par le nom.
Aucune authentification nécessaire. Le fichier n'est réécrit que si le contenu a changé.
"""
import datetime
import json
import os
import re
import sys
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

SOURCES = {
    "azure": "https://learn.microsoft.com/fr-fr/azure/role-based-access-control/built-in-roles",
    "entra": "https://learn.microsoft.com/fr-fr/entra/identity/role-based-access-control/permissions-reference",
}
MIN_ROWS = {"azure": 400, "entra": 80}  # garde-fou : en dessous, la page a probablement changé de structure
OUT = Path(__file__).resolve().parent.parent / "data" / "descriptions-fr.json"
GUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)


class Tables(HTMLParser):
    """Récupère le texte de chaque cellule de chaque ligne de tableau."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows, self.row, self.cell = [], None, None

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self.row = []
        elif tag in ("td", "th") and self.row is not None:
            self.cell = []
        elif tag == "br" and self.cell is not None:
            self.cell.append(" ")

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self.cell is not None and self.row is not None:
            self.row.append(re.sub(r"\s+", " ", "".join(self.cell)).strip())
            self.cell = None
        elif tag == "tr" and self.row is not None:
            if self.row:
                self.rows.append(self.row)
            self.row = None

    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data)


def parse(html):
    """Retourne {id: {"name": ..., "description": ...}} pour les lignes Rôle | Description | ID."""
    p = Tables()
    p.feed(html)
    out = {}
    for row in p.rows:
        if len(row) < 3:
            continue
        rid = row[-1].strip().lower()
        if not GUID.match(rid):
            continue
        name, desc = row[0].strip(), row[-2].strip()
        if name and desc and rid not in out:
            out[rid] = {"name": name, "description": desc}
    return out


def fetch(url):
    req = urllib.request.Request(url, headers={
        "Accept-Language": "fr-FR,fr;q=0.9",
        "User-Agent": "azure-roles-helper (https://github.com/abdoulayendao007/azure-roles-helper)",
    })
    with urllib.request.urlopen(req, timeout=90) as resp:
        return resp.read().decode("utf-8", errors="replace")


def main():
    old = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    result, lines, failed = {}, ["## Descriptions françaises (Microsoft Learn)"], False
    for kind, url in SOURCES.items():
        try:
            rows = parse(fetch(url))
            if len(rows) < MIN_ROWS[kind]:
                raise RuntimeError(f"seulement {len(rows)} lignes trouvées, structure de page inattendue")
            result[kind] = dict(sorted(rows.items()))
            lines.append(f"- **{kind}** : {len(rows)} rôles")
        except Exception as exc:
            failed = True
            print(f"::warning::Descriptions françaises {kind} : {exc}")
            lines.append(f"- **{kind}** : échec ({exc}), données précédentes conservées")
            if old.get(kind):
                result[kind] = old[kind]
    if result and any(result.get(k) != old.get(k) for k in SOURCES):
        OUT.parent.mkdir(exist_ok=True)
        OUT.write_text(json.dumps({
            "generatedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
            "sources": SOURCES,
            **result,
        }, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        lines.append("- Fichier mis à jour")
    else:
        lines.append("- Aucun changement")
    text = "\n".join(lines)
    print(text)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write(text + "\n")
    sys.exit(1 if failed and not result else 0)


if __name__ == "__main__":
    main()
