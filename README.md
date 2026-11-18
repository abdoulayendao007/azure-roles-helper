# Choisir le bon rôle Azure et Entra ID

Assistant web pour choisir le rôle **Azure RBAC** ou **Entra ID** au moindre privilège, comprendre ce qu'il permet (et ne permet pas) et copier la commande d'attribution.

**Site :** https://abdoulayendao007.github.io/azure-roles-helper/
**Version de développement :** https://abdoulayendao007.github.io/azure-roles-helper/dev/

## Branches

- `dev` : développement et tests, publiée sous `/dev/` avec un bandeau orange
- `main` : production, publiée à la racine. On y fusionne `dev` par Pull Request une fois validé.

Le workflow `deploy-pages.yml` publie les deux branches à chaque push. La source GitHub Pages doit être réglée sur **GitHub Actions**.

## Fonctionnalités

- **Assistant** en 3 étapes : domaine, besoin, recommandation avec alternatives. Côté Entra ID, les 212 tâches et leurs rôles au moindre privilège proviennent directement de la page Microsoft [Least privileged roles by task](https://learn.microsoft.com/fr-fr/entra/identity/role-based-access-control/delegate-by-task), synchronisée chaque semaine
- **Catalogue** commenté de 46 rôles courants, filtrable par type et niveau de risque
- **Comparateur** de 3 rôles côte à côte
- **Tous les rôles** : l'ensemble des rôles intégrés Azure RBAC et Entra ID, mis à jour chaque semaine, avec une recherche **« Quels rôles accordent cette permission ? »** (prend en compte les `*` et les NotActions, résultats triés du plus restreint au plus large)
- **Azure RBAC vs Entra ID** : les différences et les bonnes pratiques
- **Commandes générées** : Azure CLI, Azure PowerShell, Microsoft Graph PowerShell

## Structure

```
index.html                          Page unique (HTML, CSS, JS sans dépendance)
data/azure-roles.json               Export des rôles intégrés Azure RBAC (généré)
data/entra-roles.json               Export des rôles intégrés Entra ID (généré)
data/entra-tasks.json               Tâches et rôles au moindre privilège selon Microsoft (généré)
scripts/export_roles.py             Export des rôles (Azure CLI + Microsoft Graph)
scripts/export_tasks.py             Export des tâches Microsoft (dépôt public MicrosoftDocs/entra-docs)
.github/workflows/update-roles.yml  Workflow hebdomadaire (lundi) + lancement manuel
.github/workflows/deploy-pages.yml  Publication de main (racine) et dev (/dev/)
```

## Configuration de la mise à jour automatique

Le workflow se connecte à Azure en **OIDC (identité fédérée)** : aucun secret client n'est stocké dans GitHub. L'identité n'a besoin que de droits en lecture, limités à un groupe de ressources vide.

> Utiliser un tenant et un abonnement de lab ou personnels, jamais ceux d'un client.

### 1. Créer l'identité (Azure CLI, Cloud Shell Bash)

```bash
REPO="abdoulayendao007/azure-roles-helper"

# Inscription d'application + principal de service
APP_ID=$(az ad app create --display-name "gh-azure-roles-helper" --query appId -o tsv)
az ad sp create --id "$APP_ID"

# Identité fédérée : seule la branche main de ce dépôt peut obtenir un jeton.
# GitHub inclut désormais les ID numériques du propriétaire et du dépôt dans le subject :
#   repo:<owner>@<owner-id>/<repo>@<repo-id>:ref:refs/heads/main
# Le subject exact apparaît dans l'erreur AADSTS700213 du premier lancement si besoin.
SUBJECT="repo:abdoulayendao007@276451228/azure-roles-helper@1462095922:ref:refs/heads/main"
az ad app federated-credential create --id "$APP_ID" --parameters "{
  \"name\": \"github-main\",
  \"issuer\": \"https://token.actions.githubusercontent.com\",
  \"subject\": \"${SUBJECT}\",
  \"audiences\": [\"api://AzureADTokenExchange\"]
}"

# Azure RBAC : Reader uniquement sur un groupe de ressources vide dédié.
# Lister les définitions de rôles fonctionne à cette portée : le robot ne voit aucune autre ressource.
SUB_ID=$(az account show --query id -o tsv)
az group create --name rg-azure-roles-helper --location canadacentral
az lock create --name ne-pas-supprimer --lock-type CanNotDelete --resource-group rg-azure-roles-helper
SP_OID=$(az ad sp show --id "$APP_ID" --query id -o tsv)
az role assignment create --assignee-object-id "$SP_OID" --assignee-principal-type ServicePrincipal \
  --role "Reader" --scope "/subscriptions/$SUB_ID/resourceGroups/rg-azure-roles-helper"

# Entra ID : permission d'application Graph RoleManagement.Read.Directory
GRAPH_APP="00000003-0000-0000-c000-000000000000"
PERM_ID=$(az ad sp show --id "$GRAPH_APP" --query "appRoles[?value=='RoleManagement.Read.Directory'].id" -o tsv)
az ad app permission add --id "$APP_ID" --api "$GRAPH_APP" --api-permissions "${PERM_ID}=Role"
az ad app permission admin-consent --id "$APP_ID"

# Valeurs à copier dans GitHub
echo "AZURE_CLIENT_ID=$APP_ID"
echo "AZURE_TENANT_ID=$(az account show --query tenantId -o tsv)"
echo "AZURE_SUBSCRIPTION_ID=$SUB_ID"
```

Le consentement administrateur nécessite un rôle comme Privileged Role Administrator ou Administrateur général.

### 2. Ajouter les secrets dans GitHub

Dépôt → **Settings → Secrets and variables → Actions → New repository secret** :

| Nom | Valeur |
|---|---|
| `AZURE_CLIENT_ID` | ID de l'application |
| `AZURE_TENANT_ID` | ID du tenant |
| `AZURE_SUBSCRIPTION_ID` | ID de l'abonnement |

### 3. Lancer le premier export

**Actions → Mise à jour des rôles intégrés → Run workflow**. Le résumé du job liste les rôles ajoutés ou retirés. Ensuite, le workflow tourne chaque lundi et ne commit que s'il y a un changement.

## Utilisation locale

```bash
python3 -m http.server 8000
# puis http://localhost:8000
```

Ouvrir `index.html` directement fonctionne aussi, sauf l'onglet « Tous les rôles » qui a besoin d'un serveur pour charger les JSON.

## Ajouter un rôle au guide commenté

Ajouter une entrée dans le tableau `ROLES` de `index.html`, puis éventuellement un besoin dans `NEEDS`. L'onglet « Tous les rôles » signale automatiquement si un rôle du guide a été renommé ou retiré de l'export officiel.

## Sources

- [Rôles intégrés Azure](https://learn.microsoft.com/fr-fr/azure/role-based-access-control/built-in-roles)
- [Rôles intégrés Entra ID](https://learn.microsoft.com/fr-fr/entra/identity/role-based-access-control/permissions-reference)

## Auteur

Conçu et maintenu par **Abdoulaye Ndao**, développé avec l'aide de Claude (Anthropic).

> Projet pédagogique. Toujours vérifier les permissions sur la documentation officielle avant une attribution en production.
