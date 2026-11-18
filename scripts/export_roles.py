#!/usr/bin/env python3
"""Exporte les rôles intégrés Azure RBAC et Entra ID vers data/*.json.

Prérequis : une session `az login` active (dans GitHub Actions : azure/login en OIDC).
- Azure RBAC : rôle Reader sur la portée indiquée par ROLES_SCOPE (ex. un groupe
  de ressources vide dédié). Lister les définitions de rôles ne demande pas plus.
- Entra ID : permission d'application Microsoft Graph RoleManagement.Read.Directory.

Les fichiers ne sont réécrits que si la liste des rôles a changé, pour éviter
des commits inutiles. Un résumé des ajouts et retraits est écrit dans le
résumé du job GitHub Actions.
"""
import datetime
import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
GRAPH = "https://graph.microsoft.com/beta/roleManagement/directory/roleDefinitions"


def az(*args):
    res = subprocess.run(["az", *args, "-o", "json"], capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(res.stderr.strip())
    return json.loads(res.stdout)


def uniq(items):
    return sorted(set(items), key=str.lower)


def azure_roles():
    scope = os.environ.get("ROLES_SCOPE")
    args = ["role", "definition", "list", "--query", "[?roleType=='BuiltInRole']"]
    if scope:
        args += ["--scope", scope]
    raw = az(*args)
    roles = []
    for r in raw:
        perms = r.get("permissions") or []
        pick = lambda k: uniq(x for p in perms for x in (p.get(k) or []))
        roles.append({
            "id": r["name"],
            "name": r["roleName"],
            "description": (r.get("description") or "").strip(),
            "actions": pick("actions"),
            "notActions": pick("notActions"),
            "dataActions": pick("dataActions"),
            "notDataActions": pick("notDataActions"),
        })
    return sorted(roles, key=lambda x: x["name"].lower())


def entra_roles():
    token = az("account", "get-access-token", "--resource-type", "ms-graph")["accessToken"]
    url, raw = GRAPH, []
    while url:
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            page = json.load(resp)
        raw.extend(page.get("value", []))
        url = page.get("@odata.nextLink")
    roles = []
    for r in raw:
        if not r.get("isBuiltIn"):
            continue
        perms = r.get("rolePermissions") or []
        roles.append({
            "id": r.get("templateId") or r["id"],
            "name": r["displayName"],
            "description": (r.get("description") or "").strip(),
            "isPrivileged": r.get("isPrivileged"),
            "actions": uniq(a for p in perms for a in (p.get("allowedResourceActions") or [])),
        })
    return sorted(roles, key=lambda x: x["name"].lower())


def save(kind, roles, summary):
    path = DATA / f"{kind}-roles.json"
    old = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"roles": []}
    if old.get("roles") == roles:
        summary.append(f"- **{kind}** : {len(roles)} rôles, aucun changement")
        return
    old_names = {r["name"] for r in old.get("roles", [])}
    new_names = {r["name"] for r in roles}
    added, removed = sorted(new_names - old_names), sorted(old_names - new_names)
    payload = {
        "generatedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "count": len(roles),
        "roles": roles,
    }
    DATA.mkdir(exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    summary.append(f"- **{kind}** : {len(roles)} rôles, mis à jour")
    if added:
        summary.append(f"  - Ajoutés ({len(added)}) : " + ", ".join(added))
    if removed:
        summary.append(f"  - Retirés ({len(removed)}) : " + ", ".join(removed))
    if old_names and not added and not removed:
        summary.append("  - Permissions ou descriptions modifiées")


def main():
    summary, failed = ["## Rôles intégrés"], False
    for kind, fn in (("azure", azure_roles), ("entra", entra_roles)):
        try:
            save(kind, fn(), summary)
        except Exception as exc:  # on continue pour l'autre source
            failed = True
            print(f"::error::Export {kind} impossible : {exc}")
            summary.append(f"- **{kind}** : échec ({exc})")
    text = "\n".join(summary)
    print(text)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write(text + "\n")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
