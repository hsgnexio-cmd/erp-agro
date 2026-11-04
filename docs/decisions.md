# Décisions du projet

Ce document garde la trace des choix faits et de leurs raisons, phase par phase.

## Phase 1 – Fondations

| Décision | Raison |
| --- | --- |
| Python 3.14 (et non 3.15) | 3.15 sortie un mois avant le début du projet ; toutes les bibliothèques ne la déclaraient pas encore. |
| TypeScript 6.0 (et non 7.0) | typescript-eslint ne supportait pas encore TypeScript 7. |
| Rôles = groupes Django | Mécanisme standard de Django, visible et modifiable dans l'administration. |
| Modèle utilisateur personnalisé (`comptes.User`) | Indispensable dès le départ : très difficile à changer ensuite. |
| Le front-end appelle `/api/...` via le proxy de Vite | Même adresse pour le navigateur : pas de configuration CORS. |

## Phase 2 – Référentiel

| Décision | Raison |
| --- | --- |
| Une seule table `Article` pour MP, SF, PF et EM | Les lots, mouvements et nomenclatures pourront pointer vers « un article » quel que soit son type. Les règles propres à chaque type sont vérifiées dans `referentiel/services.py`. |
| Code produit fini généré automatiquement | Évite les erreurs de saisie : `PF-[famille]-[recette]-[marque]-[format]` est calculé à partir des champs. |
| Codes fournisseurs `FOU-001` | Non prévu par CLAUDE.md ; format simple choisi pour la phase 2. |
| Codes entrepôts clients `ENS1-E01` et emplacements `NAN-CF-MP` | Le code commence toujours par l'enseigne ou le site : lisible et vérifié. |
| Type de date (DLC/DDM) porté par la catégorie de matière | Règle 3 : `SEC` et `SUR` en DDM, le frais en DLC. Semi-finis et produits finis toujours en DLC. |
| Allergènes saisis seulement sur les matières premières | Règle 8 : ceux des recettes seront calculés à partir des nomenclatures (phase 5). Seuls `qualite` et `admin` les modifient. |
| Une nomenclature par article (pas de versions pour l'instant) | Suffisant pour démarrer ; l'historique garde les anciennes valeurs. Les versions datées pourront venir en phase 6. |
| Taux de perte sur chaque ligne de nomenclature | Exemple de la fiche : bœuf haché −25 % à la cuisson. Quantité brute = nette / (1 − perte). |
| Toutes les règles vérifiées à chaque enregistrement (`ValidatedModel`) | Aucune voie de contournement : API, administration ou script passent par les mêmes contrôles. |
| Historique avec django-simple-history | Règle 12 (audit IFS / BRCGS) : qui, quand, avant/après, pour chaque table du référentiel. |
| Pas de suppression par l'API ; suppression dans l'administration réservée au rôle `admin` | On désactive (« actif ») plutôt que de supprimer. Une donnée utilisée ailleurs est protégée par la base. |
| Saisie dans l'administration Django, écrans React en lecture | Garde la phase à une taille raisonnable ; les formulaires React viendront plus tard. |
| Lignes de production (L1–L9) reportées en phase 6, prix d'achat en phase 3 | Hors du périmètre du référentiel tel que défini dans CLAUDE.md. |

### Droits de modification

| Données | Rôles autorisés |
| --- | --- |
| Sites, emplacements, familles, catégories | `admin` |
| Articles, recettes, nomenclatures | `admin`, `production`, `qualite` |
| Allergènes des matières | `admin`, `qualite` |
| Fournisseurs et articles fournisseurs | `admin`, `acheteur` |
| Enseignes et entrepôts | `admin`, `commercial` |

Tous les rôles consultent tout. Les droits sont définis dans `backend/referentiel/permissions.py` et appliqués automatiquement aux groupes après chaque `migrate`.

## Phase 3 – Achats et réceptions

| Décision | Raison |
| --- | --- |
| Pas de commande à un fournisseur non audité | La fiche entreprise exige des fournisseurs audités. Le contrôle porte sur les commandes en brouillon. |
| Statuts de commande : brouillon → envoyée → partiellement reçue → soldée (ou annulée) | Une commande n'est modifiable qu'en brouillon ; annulation impossible après une réception. |
| Prix proposé automatiquement d'après le tarif en vigueur à la date de commande | Tarifs datés (`SupplierPrice`) : prix annuels (secs, emballages) ou hebdomadaires (viande, légumes, laitiers, mer). Deux tarifs ne se chevauchent jamais. |
| Quantité minimale de commande par article fournisseur | Emballages MDD : minimums élevés (fiche entreprise). |
| Livraison acceptée jusqu'à la commande + 10 % | Les livraisons au poids ne tombent jamais pile ; au-delà, la réception est refusée. |
| Une ligne non conforme crée quand même un lot, **bloqué** | La marchandise est physiquement là : elle doit être tracée. Le motif est enregistré sur le lot. Le « refus à quai » n'est pas géré pour l'instant. |
| Contrôles à réception automatiques | Température ≤ 4 °C (froid positif) ou ≤ −18 °C (froid négatif) ; produit non périmé ; DLC restante ≥ seuil de la catégorie ; aspect ; documents. |
| DLC restante minimale par catégorie | 60 % pour viandes, produits laitiers, produits de la mer ; 50 % pour légumes frais, surgelés, produits secs. Modifiable dans l'administration. |
| Lot reçu en quarantaine | Règle 6. La libération par la qualité viendra en phase 4. |
| Quantité d'un lot = somme de ses mouvements | Règle 11 : pas de quantité stockée qui pourrait diverger des mouvements. |
| Mouvements de stock impossibles à modifier ou supprimer | Règle 11, appliquée dans le modèle (y compris les opérations groupées). On corrige par un mouvement inverse. |
| Numéros automatiques : `CA-AAAA-NNNNN`, `REC-AAAA-NNNNN`, `LR-AAMMJJ-NNNN` | Compteur en base (`DocumentSequence`) protégé contre les accès simultanés ; le numéro est attribué après validation, donc sans trou. |
| Commandes, réceptions, lots : consultation seule dans l'administration | Ils naissent uniquement des opérations de l'application, qui appliquent toutes les règles. Les tarifs se saisissent dans l'administration. |
| Premiers écrans de saisie dans React | Commandes (création, envoi, annulation) et réception à quai : usage quotidien. |

### Droits

| Opération | Rôles |
| --- | --- |
| Créer, modifier, envoyer, annuler une commande ; saisir les tarifs | `admin`, `acheteur` |
| Enregistrer une réception | `admin`, `magasinier` |
| Consulter commandes, réceptions, lots, mouvements | tous les rôles |
