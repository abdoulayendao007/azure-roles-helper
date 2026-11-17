# Choisir le bon rôle Azure et Entra ID

Assistant web pour choisir le rôle **Azure RBAC** ou **Entra ID** au moindre privilège, comprendre ce qu'il permet (et ne permet pas) et copier la commande d'attribution.

## Fonctionnalités

- **Assistant** en 3 étapes : domaine, besoin, recommandation avec alternatives
- **Catalogue** filtrable par type et niveau de risque
- **Comparateur** de 3 rôles côte à côte
- **Azure RBAC vs Entra ID** : les différences et les bonnes pratiques
- **Commandes générées** : Azure CLI, Azure PowerShell, Microsoft Graph PowerShell (portée tenant ou unité administrative)

Page HTML unique, sans dépendance ni backend.

## Utilisation locale

Ouvrir `index.html` dans un navigateur.

## Ajouter un rôle

Ajouter une entrée dans le tableau `ROLES` de `index.html`, puis éventuellement un besoin dans `NEEDS`.

## Sources

- [Rôles intégrés Azure](https://learn.microsoft.com/fr-fr/azure/role-based-access-control/built-in-roles)
- [Rôles intégrés Entra ID](https://learn.microsoft.com/fr-fr/entra/identity/role-based-access-control/permissions-reference)

> Projet pédagogique. Toujours vérifier les permissions sur la documentation officielle avant une attribution en production.
