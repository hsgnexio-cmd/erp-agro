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
| Une nomenclature par article (pas de versions pour l'instant) | Suffisant pour démarrer ; l'historique garde les anciennes valeurs. Les versions datées n'ont pas été faites en phase 6 : voir « Points en suspens ». |
| Taux de perte sur chaque ligne de nomenclature | Exemple de la fiche : bœuf haché −25 % à la cuisson. Quantité brute = nette / (1 − perte). |
| Toutes les règles vérifiées à chaque enregistrement (`ValidatedModel`) | Aucune voie de contournement : API, administration ou script passent par les mêmes contrôles. |
| Historique avec django-simple-history | Règle 12 (audit IFS / BRCGS) : qui, quand, avant/après, pour chaque table du référentiel. |
| Pas de suppression par l'API ; suppression dans l'administration réservée au rôle `admin` | On désactive (« actif ») plutôt que de supprimer. Une donnée utilisée ailleurs est protégée par la base. |
| Saisie dans l'administration Django, écrans React en lecture | Garde la phase à une taille raisonnable. Les opérations quotidiennes (commandes, réceptions, lots, OF, inventaires, ventes) ont ensuite eu leurs écrans React ; le référentiel se saisit toujours dans l'administration. |
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

## Phase 4a – Lots et mouvements

| Décision | Raison |
| --- | --- |
| Phase 4 découpée en 4a (lots, mouvements, FEFO) et 4b (températures, inventaires, alertes) | Deux pull requests plus faciles à relire et à tester. |
| Stock calculé par lot **et** par emplacement, à partir des mouvements | Un lot peut être réparti (ex. 250 kg de crème à l'entrepôt, 150 kg à l'usine NAN). Le champ « emplacement d'entrée » du lot garde seulement l'emplacement de réception. |
| Statuts changés uniquement par `qualite` et `admin` | Règle 6 et section 9 de CLAUDE.md. |
| Passages autorisés : quarantaine → libéré ou bloqué ; libéré → bloqué ; bloqué → libéré ou détruit | On ne revient jamais en quarantaine ; on ne détruit qu'un lot bloqué ; un lot détruit est définitif. |
| Motif obligatoire pour bloquer, débloquer et détruire | Traçabilité des décisions qualité (audit IFS / BRCGS). |
| Journal des changements de statut (`LotStatusChange`), jamais modifié | Qui, quand, ancien et nouveau statut, motif. |
| Un lot périmé ne peut être ni libéré ni débloqué | Un lot reste utilisable le jour même de sa DLC/DDM, plus le lendemain. |
| Destruction = sortie automatique de tout le stock restant | Mouvements de type « destruction », un par emplacement. |
| Transfert = deux mouvements (sortie + entrée) liés par un numéro `TR-AAAA-NNNNN` | Règle 11 ; permis pour tout lot non détruit (on doit pouvoir ranger un lot bloqué). |
| Emplacement à la bonne température obligatoire, au transfert comme à la réception | Chaîne du froid : frais → froid positif, surgelé → froid négatif, sec et emballages → ambiant. Zones de quarantaine `MPE-QUAR-FN` et `MPE-QUAR-AMB` ajoutées. |
| Correction d'une réception par un mouvement inverse, total ou partiel | Règle 11 : l'original n'est jamais modifié ; la correction pointe vers le mouvement corrigé. Un transfert se corrige par un transfert inverse. |
| Le stock ne devient jamais négatif | Contrôlé à chaque transfert et correction ; le lot est verrouillé pendant l'opération. |
| FEFO : lots libérés, non périmés, du site, triés par date de péremption | Règle 4. Les lots sans date (emballages) passent en dernier. Paramètre de DLC minimale prévu pour la règle 5 (phase 7). |
| DLC d'un produit fabriqué = date de fabrication + durée de vie | Règle 3 ; fonction prête pour la phase 6. |

### Droits

| Opération | Rôles |
| --- | --- |
| Libérer, bloquer, débloquer, détruire un lot | `admin`, `qualite` |
| Transférer, corriger une réception | `admin`, `magasinier` |
| Consulter lots, mouvements, état des stocks, FEFO | tous les rôles |

## Phase 4b – Surveillance (températures, inventaires, alertes)

| Décision | Raison |
| --- | --- |
| Limites de température : celles de l'emplacement, sinon celles de sa classe | Froid positif 0 à 4 °C, froid négatif ≤ −18 °C ; relevés facultatifs en ambiant. Les limites sont copiées dans chaque relevé pour l'audit. |
| Un écart bloque tous les lots libérés ou en quarantaine présents dans l'emplacement | Règle 7. Les lots déjà bloqués gardent leur motif d'origine. Une alerte critique est créée à chaque écart. |
| Relevés de température jamais modifiés ni supprimés | Preuve pour les audits IFS / BRCGS. |
| Alerte « relevé manquant » après 24 h sans relevé | Seulement pour une chambre froide qui contient du stock. |
| Vérification quotidienne à 6 h par Celery Beat | Péremption proche (DLC ≤ 3 jours, DDM ≤ 30 jours), DLC dépassée (lot bloqué automatiquement), DDM dépassée (alerte seule), relevés manquants. Commande `verifier_alertes` pour la lancer à la demande. |
| Pas de doublon d'alerte | Une alerte identique encore ouverte (même type, même lot ou emplacement) n'est pas recréée. Exception : chaque écart de température crée sa propre alerte. |
| Alerte jamais supprimée : marquée « traitée » avec un commentaire obligatoire | Qui, quand, ce qui a été fait. |
| Pas d'envoi d'e-mail pour l'instant | Pas de serveur d'envoi ; les alertes sont dans l'application (page Alertes et compteur du menu). |
| Inventaire = photo du stock à l'ouverture, comptage, puis validation | Numéro `INV-AAAA-NNNNN`. Les écarts deviennent des mouvements « ajustement d'inventaire » (règle 11). |
| Emplacements gelés pendant l'inventaire | Aucun mouvement (transfert, réception, correction, destruction) sur le périmètre compté avant la validation ou l'annulation, contrôlé dans le modèle `StockMovement`. Deux inventaires ne se chevauchent pas. |
| Comptage à l'aveugle | La quantité théorique est cachée pendant la saisie ; elle s'affiche à l'étape des écarts, juste avant la validation. |
| Lot trouvé pendant le comptage | Un lot existant peut être ajouté à la feuille s'il est trouvé à un emplacement où le système ne le situait pas. |
| Fichiers `stocks/monitoring.py` et `stocks/inventory.py` | Logique métier de la surveillance et des inventaires, séparée de `stocks/services.py` pour rester lisible. |

### Droits

| Opération | Rôles |
| --- | --- |
| Saisir un relevé de température | `admin`, `qualite`, `magasinier` |
| Traiter une alerte | `admin`, `qualite`, `magasinier` |
| Ouvrir, compter, valider, annuler un inventaire | `admin`, `magasinier` |
| Consulter relevés, inventaires, alertes | tous les rôles |

## Phase 5 – Traçabilité, rappel produit, allergènes

| Décision | Raison |
| --- | --- |
| Fabrication et expédition **minimales** dès la phase 5 (option A) | Sans elles, rien à tracer. `production.services.record_production` et `ventes.services.record_shipment` seront reprises par les phases 6 (ordres de fabrication, rendements) et 7 (commandes EDI, préparation FEFO). |
| La traçabilité est portée par les **mouvements de stock** eux-mêmes | Une consommation pointe vers le lot fabriqué (`produced_lot`), une expédition vers l'entrepôt client (`customer_warehouse`). Une seule source de vérité : stock et traçabilité ne peuvent pas se contredire. |
| Lot fabriqué : numéro `LF-AAMMJJ-NNNN`, DLC calculée, démarre en quarantaine | Règles 2, 3 et 6. Libération par la qualité comme un lot reçu. |
| On ne consomme et n'expédie qu'un lot libéré et non périmé | Règle 6. Le lot est relu et verrouillé au moment de l'opération. |
| On ne consomme que des composants de la nomenclature de l'article fabriqué | Évite les erreurs de saisie qui fausseraient la traçabilité. |
| Expédition : produit MDD uniquement chez son enseigne ; DLC minimale de l'enseigne respectée | Règles 10 et 5, appliquées dès maintenant (peu coûteuses). |
| Traçabilité amont et aval à tous les niveaux, emballages compris | Règle 1. Arbres consultables à l'écran Traçabilité. |
| Rappel en deux temps : simulation (tous les rôles), puis lancement (`qualite`, `admin`) | Le lancement bloque d'un coup tous les lots concernés ayant du stock, avec le motif « Rappel RAP-… ». |
| Photo complète du rappel enregistrée au lancement (`snapshot`) | Preuve pour les autorités et les audits : lots, stocks, livraisons au moment du rappel. Un rappel ne se modifie ni ne se supprime. |
| Liste des clients à prévenir en CSV (séparateur « ; », UTF-8) | S'ouvre directement dans Excel. Pas d'envoi d'e-mail pour l'instant. |
| Calcul de l'impact d'un rappel niveau par niveau, en requêtes groupées | Objectif de la fiche entreprise : rappel complet en 5 minutes maximum. Mesuré : quelques dizaines de millisecondes sur les données de démonstration ; un test échoue au-delà de 2 secondes. |
| Allergènes des semi-finis et produits finis **calculés à chaque consultation** | Règle 8. Toujours à jour : un allergène ajouté sur une matière se répercute immédiatement sur toutes les recettes. L'origine de chaque allergène est affichée. |
| Scénario de référence (crème contaminée) en test automatisé | `qualite/tests/test_tracabilite_et_rappel.py::test_scenario_de_reference_creme_contaminee`, sur les données de démonstration. |

### Droits

| Opération | Rôles |
| --- | --- |
| Consulter la traçabilité, simuler un rappel, voir les allergènes | tous les rôles |
| Lancer un rappel | `admin`, `qualite` |
| Déclarer une fabrication (API) | `admin`, `production` |
| Déclarer une expédition (API) | `admin`, `magasinier` |

## Phase 6 – Production

| Décision | Raison |
| --- | --- |
| 9 lignes de production dans le référentiel (L1 à L9) | Usine, familles et formats acceptés, cadence horaire (fiche entreprise). Saisie : `admin`, `production`. |
| Un produit fini ne passe que sur une ligne compatible | La ligne doit accepter la famille de la recette et le format (ex. lasagnes 1 kg : L3 uniquement). Un semi-fini se prépare en cuisine, sans ligne. |
| Statuts d'OF : planifié → lancé → terminé (ou annulé) | Modifiable seulement planifié ; annulable tant qu'aucune production n'est déclarée. Numéro `OF-AAAA-NNNNN`. |
| Plusieurs déclarations par OF, clôture manuelle | Une déclaration par équipe ; on produit rarement exactement la quantité prévue. |
| Proposition FEFO pré-remplie à la déclaration | Règle 4. Un lot hors FEFO est accepté avec une **justification obligatoire**, enregistrée sur la déclaration et sur le mouvement de consommation. |
| Pas de réservation de stock au lancement | Plus simple ; le contrôle de stock à la déclaration empêche deux OF de consommer la même quantité. |
| Rendement matière = théorique ÷ réel, sur les composants en kg et en litres | Théorique = besoins de la nomenclature, pertes comprises, pour la quantité produite. Les emballages (unités) sont suivis à part. Sous **96 %** (fiche entreprise), l'OF est signalé et une alerte « rendement faible » est créée à la clôture. |
| Lot fabriqué : semi-fini en chambre froide semi-finis de l'usine, produit fini en `PFN-QUAR` | En quarantaine jusqu'à la libération par la qualité (règle 6). |
| Toute nouvelle fabrication passe par un OF | L'API de déclaration directe de la phase 5 est remplacée. Les fabrications de démonstration de la phase 5 restent dans l'historique. |
| Planning de la semaine par ligne | Charge = quantité ÷ cadence ; capacité 15 h / jour (2 équipes de 7 h 30) ; avertissement en cas de surcharge. |
| Ordre « sans allergène → avec allergènes » : avertissement, pas blocage | Signalé quand un OF suit, sur la même ligne le même jour, un OF contenant un allergène qu'il n'a pas : nettoyage renforcé requis. Le responsable de production garde la main. |
| Hors périmètre | Prévisions à 8 semaines, plan hebdomadaire figé à J-2, calcul des besoins d'achat (MRP) : possible phase complémentaire. |

### Droits

| Opération | Rôles |
| --- | --- |
| Créer, modifier, lancer, déclarer, clôturer, annuler un OF | `admin`, `production` |
| Libérer les lots fabriqués | `admin`, `qualite` |
| Consulter OF, planning, rendements | tous les rôles |

## Phase 7a – Commandes clients et EDI

| Décision | Raison |
| --- | --- |
| Phase 7 découpée en 7a (commandes, EDI, tarifs) et 7b (préparation, SSCC, expédition, taux de service, invendables) | Deux pull requests plus faciles à relire et à tester. |
| Tarifs de vente datés par enseigne et par produit fini | Comme les tarifs d'achat ; deux tarifs ne se chevauchent pas ; pas de tarif MDD pour une autre enseigne. Serviront au chiffre d'affaires et à la démarque (phase 8). |
| Heure limite 11 h | Commande reçue avant 11 h : livrable dès J+1 ; après : J+2 au plus tôt. Une date plus proche est refusée (règle de la fiche entreprise). |
| Produits commandables | Produit fini actif ; MDD uniquement par son enseigne (règle 10) ; marque Brévanne uniquement par une enseigne qui la vend. |
| Ligne sans tarif : acceptée, signalée « à valoriser » | On ne refuse pas une commande client à cause d'un oubli interne. |
| Commande : numéro `CC-AAAA-NNNNN`, statuts reçue → en préparation → expédiée (ou annulée) | Annulable seulement à l'état « reçue ». La préparation et l'expédition arrivent en 7b. |
| EDI simulé : message JSON inspiré d'EDIFACT ORDERS | Chaque message est gardé tel quel (audit) puis intégré (commande créée) ou rejeté avec tous les motifs. Un message déjà intégré renvoyé est ignoré comme doublon. |
| Simulation Celery chaque jour de semaine à 9 h 30 | Avant l'heure limite. Une commande par enseigne, assortiment habituel, quantités par colis de 12 ; environ 1 message sur 10 contient une erreur volontaire. Commande `simuler_edi` et bouton « Simuler les commandes du jour ». |
| Saisie manuelle d'une commande | Pour une commande reçue par téléphone ; mêmes contrôles que l'EDI. |
| Hors périmètre | Promotions (annoncées 6 à 8 semaines avant, jusqu'à ×3) : avec la planification avancée. |

### Droits

| Opération | Rôles |
| --- | --- |
| Saisir, annuler une commande ; saisir les tarifs de vente ; simuler ou déposer un message EDI | `admin`, `commercial` |
| Consulter commandes, tarifs, messages EDI | tous les rôles |

## Phase 7b – Préparation, expédition, taux de service, invendables

| Décision | Raison |
| --- | --- |
| Préparation en deux temps : « Préparer » (lots choisis, **sans mouvement**), puis « Expédier » (mouvements, palettes) | Le magasinier prépare au quai, puis charge le camion ; le stock ne bouge qu'au départ réel. Toute la logique est dans `ventes/shipping.py`. |
| Toutes les expéditions partent de la plateforme `PFN` | Fiche entreprise : la plateforme de Nantes expédie vers les entrepôts des enseignes. |
| DLC minimale client calculée **à la date de livraison demandée** | DLC du lot ≥ livraison + durée de vie × % de l'enseigne, arrondi au jour supérieur (lasagnes 14 j, 70 % → livraison + 10 jours). Les lots trop courts ne sont pas proposés et sont refusés, même avec une justification. |
| Proposition FEFO, justification obligatoire hors FEFO | Règle 4, même fonctionnement qu'en production. La justification est gardée sur la ligne préparée. |
| Les quantités déjà préparées (pas encore expédiées) ne sont plus proposées | Deux préparations ne peuvent pas prendre les mêmes barquettes. Ce n'est pas une réservation : rien n'est retenu tant qu'on n'a pas préparé. |
| Pas de surplus, pas de reliquat | On ne prépare jamais plus que commandé ; le manquant est une rupture et la commande est soldée à l'expédition. |
| Un seul bon de livraison en cours par commande ; préparation annulable avant l'expédition | Contrainte en base. L'annulation (motif obligatoire) remet la commande « reçue ». |
| Contrôles refaits à l'expédition | Statut, péremption, stock, DLC minimale : un lot bloqué entre la préparation et le départ empêche l'expédition (il faut annuler et préparer de nouveau). |
| Température obligatoire au chargement ; au-dessus de 4 °C : refus | Règle 7. Les lots préparés sont bloqués, une alerte critique « Température à l'expédition » est créée, le BL est « refusé » et la commande redevient « reçue » (à préparer avec d'autres lots). Exactement 4 °C est accepté. |
| Numéro `BL-AAAA-NNNNN` ; les mouvements d'expédition portent ce numéro | Un document par expédition, retrouvable depuis la fiche lot et la traçabilité. Les expéditions de la phase 5 gardent leur numéro `EXP-`. |
| Palettes de 720 unités (60 colis de 12), remplies dans l'ordre des lignes | Une palette peut mélanger plusieurs produits et lots ; une ligne peut s'étaler sur plusieurs palettes. |
| SSCC GS1 à 18 chiffres : extension `0` + préfixe fictif `3770000` + série (compteur `SSCC`, 9 chiffres) + clé modulo 10 | Norme des étiquettes logistiques ; clé de contrôle vérifiée par un test. Étiquettes imprimables depuis le BL (une par page). |
| Taux de service = livré complet et à l'heure ÷ commandé, par enseigne | « À l'heure » = expédié au plus tard la veille de la livraison (transport J+1). Commandes annulées exclues ; une commande non expédiée mais encore dans les temps est « en cours » (non comptée) ; après, elle compte comme non livrée. Objectif 98,5 %, pénalités seulement signalées. Période par défaut : livraisons de J-29 à J+7. |
| Invendables : produit fini **bloqué ou périmé**, rôle `qualite` / `admin` | Destination obligatoire (don, alimentation animale, destruction) et motif ; tout le stock sort par un mouvement propre (`don`, `alimentation_animale`, `destruction_invendable`) et le lot passe « détruit ». Un lot périmé encore libéré est d'abord bloqué (journal des statuts). Les matières se détruisent par la décision qualité habituelle. |
| Expédition directe de la phase 5 retirée de l'API | Toute expédition passe par une commande client. `record_shipment` reste la fonction qui crée le mouvement (appelée par `ship_order`). |
| Données de démo : 4 commandes à la mesure du stock de la plateforme | Complète et à l'heure (ENS1), rupture (ENS2), en retard (ENS3), refusée à 5,8 °C puis gratin détruit en invendable (ENS4). Les commandes EDI de la démo 7a, faute de stock fabriqué, restent non expédiées : le taux de service de la démo est donc très bas. |

### Droits

| Opération | Rôles |
| --- | --- |
| Préparer, annuler une préparation, expédier | `admin`, `magasinier` |
| Sortir un invendable | `admin`, `qualite` |
| Consulter bons de livraison, palettes, taux de service | tous les rôles |

## Phase 8a – Indicateurs et tableau de bord

| Décision | Raison |
| --- | --- |
| Phase 8 découpée en 8a (historique de démo, vues SQL, API, tableau de bord) et 8b (Power BI, Power Query, utilisateur PostgreSQL en lecture seule) | Deux pull requests plus faciles à relire et à tester. |
| Calculs dans des **vues SQL** PostgreSQL, schéma `bi` (`pilotage/sql/bi_views.sql`, créé par une migration) | Une seule source de vérité : le tableau de bord (via `pilotage/indicators.py`) et Power BI lisent les mêmes vues. Des tests vérifient que les vues donnent les mêmes résultats que les calculs métier en Python (taux de service, rendement). |
| Valorisation : produit fini au **prix de vente moyen en vigueur** des enseignes ; matière et emballage au **prix d'achat en vigueur à la date** (fournisseur du lot, sinon moyenne) ; semi-fini au coût de sa nomenclature | Validé en début de phase. Fonctions SQL `bi.unit_value`, `bi.sale_price`, `bi.purchase_price`, `bi.bom_cost`. |
| Démarque = mouvements `destruction`, `don`, `alimentation_animale`, `destruction_invendable`, divisés par le CA expédié (prix des commandes) | Fiche entreprise : « valeur détruite ou déclassée / CA ». Les ajustements d'inventaire n'en font pas partie. |
| Couvertures en **valeur** et en jours : stock disponible ÷ sorties moyennes par jour (expéditions pour les produits finis, consommations pour les matières) | Additionner des kg, des litres et des unités n'aurait pas de sens. |
| Stock disponible = lots **libérés ou en quarantaine** ; les lots bloqués ne comptent pas | La production de la veille attend sa libération du matin : sans elle, la couverture serait sous-estimée. |
| Stock d'un jour passé : statut retrouvé dans le journal des statuts (`LotStatusChange`) | Vue `bi.fact_stock_daily` : stock de fin de journée par article, site et statut, pour suivre les couvertures semaine par semaine. |
| TRS et fiabilité des prévisions affichés « **non disponibles** » | Validé : l'ERP n'enregistre ni arrêts de ligne ni prévisions ; on n'invente pas de chiffres. Saisie possible dans une phase complémentaire. |
| Délai de traçabilité = **rappel à blanc** mesuré à chaque consultation sur le lot de matière le plus utilisé ; la durée des vrais rappels est gardée dans leur photo (`duration_ms`) | Toujours une mesure récente, même sans rappel sur la période. |
| Filtres : période pour tous ; enseigne pour le taux de service ; site pour le rendement et la couverture matières | Les autres indicateurs ne se découpent pas proprement (le CA et les expéditions sont ceux de la plateforme). Chaque tuile affiche les filtres qu'elle prend en compte. |
| Période par défaut : les 28 derniers jours ; évolution par semaine ISO (S41, S42…) | Quatre semaines d'historique de démonstration. |
| **Historique de démonstration** de 4 semaines (`pilotage/demo_history.py`), rejoué jour par jour avec les fonctions métier, dans `charger_donnees_demo` | Validé : indicateurs réalistes. Toutes les règles s'appliquent (FEFO, DLC client, statuts…). Une commande Django plutôt qu'un script dans `data/` : même outil que le reste de la démo. Option `--sans-historique` pour les tests (le chargement complet prend environ 6 minutes). |
| Horloge simulée pendant l'historique (`simulated_clock`) | Chaque enregistrement porte la date de sa journée. Pour cela, le FEFO ignore les lots créés « dans le futur » (sans effet en usage normal). |
| Incidents volontaires dans l'historique | Panne de ligne (ruptures), transporteur en retard (livraisons hors délai), fuite en cuisson (rendement faible), 3 % de réceptions non conformes (lots laissés bloqués, pour retour fournisseur), invendables donnés ou détruits. |
| Quatre légumes n'avaient qu'un fournisseur non audité (FOU-007) | L'historique les référence aussi chez Maraîchers Nantais (FOU-006, audité), au même prix : on ne commande jamais à un fournisseur non audité. |

| Relancer `charger_donnees_demo` un autre jour ne recrée plus les tarifs déjà présents (achat et vente) | Défaut des phases 3 et 7a : les périodes recalculées depuis « aujourd'hui » chevauchaient les anciennes et le chargement échouait. |
| Tests front-end : attente maximale de 5 s pour qu'un élément apparaisse (au lieu de 1 s) | Le premier affichage d'un fichier de tests dépassait parfois 1 s quand le PC est chargé : échecs aléatoires, sans lien avec le code. |

### Droits

| Opération | Rôles |
| --- | --- |
| Consulter le tableau de bord et l'API des indicateurs | tous les rôles |

## Phase 8b – Power BI, Power Query, export Excel

| Décision | Raison |
| --- | --- |
| Utilisateur PostgreSQL **`powerbi` en lecture seule** : lecture du schéma `bi` uniquement, sessions en lecture seule (`default_transaction_read_only`) | Validé : Power BI et Excel ne voient aucune table de l'application et ne peuvent rien modifier. Testé en se connectant réellement avec cet utilisateur. |
| Création par la commande relançable `creer_utilisateur_bi`, mot de passe `BI_DB_PASSWORD` du `.env` (12 caractères minimum) | Validé : jamais de mot de passe dans le code ni dans une migration. |
| Droits remis automatiquement après chaque `migrate` (`pilotage.bi_access.refresh_grants`) et droits par défaut sur le schéma | Une vue recréée par une migration garde sa lecture pour `powerbi`. |
| Fonctions de valorisation en `SECURITY DEFINER` (migration `0002`) | Elles lisent les tarifs (tables de l'application) avec les droits de l'ERP : `powerbi` peut les appeler sans accès aux tables. |
| Colonne `value` ajoutée à `bi.fact_stock_daily` (migration `0003`) | Les mesures DAX ne peuvent pas appeler une fonction SQL : la vue fournit la valeur du stock, utilisée aussi par le tableau de bord. |
| Une requête Power Query typée par vue (`bi/power-query/*.pq`) et les mesures DAX documentées (`bi/mesures-dax.md`) | Validé : Nicolas construit lui-même le rapport Power BI (formation) et l'enregistre au format projet `.pbip` (texte, suivi par Git) dans `bi/powerbi/`. Un `.pbix` est un binaire qu'on ne peut pas produire de façon fiable par le code. |
| Excel d'abord, Power BI ensuite | Validé : Excel est déjà installé sur le PC de Nicolas. |
| **Export CSV** du tableau de bord (`/api/pilotage/indicators/export/`) : séparateur « ; », UTF-8 avec marque d'ordre, décimales à la virgule | Validé : s'ouvre directement dans Excel, sans connexion à configurer. Même format que la liste des clients d'un rappel. |

### Rapport Power BI (après la 8b)

| Décision | Raison |
| --- | --- |
| Rapport construit par Nicolas dans Power BI Desktop, enregistré au format projet dans `bi/powerbi/indicateurs.pbip` | Format texte (TMDL, JSON) suivi par Git. Vérifié : aucun mot de passe dans les fichiers (les identifiants restent dans le profil Windows). |
| `cache.abf` et `localSettings.json` exclus de Git (`bi/powerbi/.gitignore`) | Recommandation Microsoft : le cache contient une copie des données, les réglages sont propres à chaque PC. À l'ouverture, Power BI relit la base. |
| Détection automatique des relations désactivée dans le rapport | Les vues n'ont pas de clés déclarées : la détection tournait sans fin et proposait de fausses relations (ex. `fact_service.order_id` ↔ `fact_production_yield.order_id`, deux numéros sans rapport). Relations créées à la main, d'après `bi/mesures-dax.md`. |

## Phase 9a – Prévisions de vente

| Décision | Raison |
| --- | --- |
| Phase 9 découpée en 9a (prévisions de vente) et 9b (plan de production figé à J-2, calcul des besoins d'achat / MRP) | Deux pull requests plus faciles à relire et à tester. |
| Nouvelle app `previsions`, logique dans `previsions/forecast.py` | Module à part entière de la planification ; la 9b s'appuiera dessus. |
| On prévoit la **demande** : quantités commandées (commandes non annulées), par semaine de livraison demandée | Validé. Les expéditions sont réduites par les ruptures : prévoir à partir d'elles ferait baisser la prévision à chaque rupture, donc la production. |
| Maille produit fini × enseigne × semaine ISO (lundi → dimanche), horizon S+1 à S+8 | Validé (fiche entreprise : prévisions à 8 semaines). Une semaine est désignée par la date de son lundi. Seuls les couples commandables sont prévus (MDD : son enseigne ; marque : les enseignes qui la vendent). |
| Méthode : moyenne pondérée des 4 dernières semaines (40/30/20/10 %), arrondie au colis de 12 | Validé : simple, refaisable dans Excel. Trop peu d'historique pour une saisonnalité. Une semaine en promotion est divisée par son coefficient ; les semaines antérieures à la première commande du couple ne comptent pas (sinon un nouveau produit serait sous-estimé). |
| Promotions : coefficient de 1,01 à 3 ; refus au-delà de ×3, d'un chevauchement avec une autre promotion du couple, d'un début avant la semaine prochaine | Validé (fiche : jusqu'à ×3). Annonce à moins de 6 semaines : **avertissement** seulement. Annulation avec motif, uniquement avant son début ; historique des modifications (règle 12). |
| Corrections manuelles : quantité qui **remplace** le total calculé, motif obligatoire, jamais modifiées ni supprimées | Validé. La dernière correction l'emporte ; une correction sans quantité rend la main au calcul. Le détail (base, promotion, correction) reste visible. |
| Versions figées `PRV-AAAA-NNNNN` : chaque lundi à 5 h (Celery Beat, une seule automatique par jour) et à la demande | Validé. Une version et ses lignes ne se modifient ni ne se suppriment. Une version ne retient que les promotions et corrections saisies avant elle. |
| Fiabilité à S-1 = 1 − Σ écart absolu (prévu − commandé) ÷ Σ commandé, au couple produit × enseigne, jamais sous 0 % | Validé (fiche : ≥ 80 % à S-1). Version de référence : la dernière figée **avant le lundi** de la semaine (heure de Paris) et qui la couvre. Seules les semaines terminées comptent ; un produit commandé mais non prévu compte en entier dans l'écart. |
| Vues `bi.fact_forecast` et `bi.fact_forecast_accuracy` (migration `pilotage/0004`) | Le tableau de bord et Power BI lisent la même vue ; un test vérifie qu'elle donne les mêmes résultats que le calcul Python. La tuile « Fiabilité des prévisions » est activée (filtres période et enseigne) et ajoutée à l'évolution par semaine et à l'export CSV. |
| Écran React **Prévisions** : grille 8 semaines, correction en cliquant sur une case, promotions, fiabilité par semaine, versions | Saisie par `commercial` et `admin`, consultation pour tous (la production en aura besoin en 9b). Rien ne se saisit dans l'administration : les règles passent par les fonctions métier. |
| Historique de démonstration porté à **6 semaines** (mesuré : ≈ 6 min de chargement, comme avant) | Avec 4 semaines, une seule semaine aurait eu une prévision figée la semaine précédente. Avec 6 : trois semaines mesurables sur les 28 derniers jours. Une promotion ×2 (ENS2, lasagnes Brévanne), annoncée 7 semaines avant, double réellement les commandes et la production de sa semaine. |
| Démo du moment : deux promotions à venir (dont une annoncée tard) et une correction manuelle | Montre l'avertissement et le code couleur de la grille. |
| Test de l'export CSV rendu indépendant de la date du jour | Il utilisait une période fixe (01/10 → 05/11/2026) : à partir du 07/11, les OF de la démo tombaient hors période. |

### Droits

| Opération | Rôles |
| --- | --- |
| Saisir ou annuler une promotion, saisir une correction, figer une version | `admin`, `commercial` |
| Consulter prévisions, promotions, corrections, versions, fiabilité | tous les rôles |

## Conventions techniques transverses

Règles de fonctionnement prises en cours de route, valables pour tous les modules.

| Convention | Où | Raison |
| --- | --- | --- |
| `ValidatedModel` : validation complète (`full_clean`) à chaque enregistrement | `referentiel/models.py` | Les règles s'appliquent quel que soit le chemin (API, administration, script, données de démo). |
| Les opérations relisent et verrouillent le lot (`select_for_update`) | `stocks/services.py`, `production/services.py`, `ventes/services.py` | Statut et stock lus à l'instant de l'opération ; deux personnes ne modifient pas le même lot en même temps. |
| Enregistrements jamais modifiés ni supprimés | `StockMovement`, `LotStatusChange`, `TemperatureReading`, `ProductRecall`, `Alert` (marquée traitée), `ForecastVersion`, `ForecastLine`, `ForecastAdjustment` | Preuves pour les audits IFS / BRCGS (règles 11 et 12). |
| Documents d'opération en lecture seule dans l'administration | `ReadOnlyAdminMixin` (`stocks/admin.py`) | Commandes, réceptions, lots, OF, inventaires, rappels, commandes clients naissent des opérations de l'application, qui appliquent les règles. |
| Numérotation par compteur en base | `referentiel.services.next_document_number`, modèle `DocumentSequence` (aussi pour la série des SSCC et les versions de prévision `PRV-`) | Sans doublon même en accès simultané ; numéro attribué après validation. |
| Droits par rôle | `comptes.permissions.WriteRolesPermission` + `write_roles` sur chaque vue ; `sync_group_permissions` après chaque `migrate` | Lecture pour tous, écriture selon le métier ; mêmes droits dans l'administration. |
| Décimaux renvoyés en texte par l'API (`"4.2000"`) | toutes les API | Aucune perte de précision ; le front-end formate en français (`formatDecimal`, `formatMoney`). |
| Erreurs métier → réponse 400 lisible | `config/exceptions.py` ; côté React `errorMessages` + `ErrorList` | Les messages des règles s'affichent tels quels à l'utilisateur. |
| Connexion par session Django + jeton CSRF | `comptes/views.py`, `DJANGO_CSRF_TRUSTED_ORIGINS` | Sécurité standard ; l'origine du front-end (`localhost:5173`) doit être déclarée de confiance. |
| Données de démonstration : une commande, relançable, dates relatives à aujourd'hui | `charger_donnees_demo` (référentiel → achats → stocks → surveillance → traçabilité → production → ventes → expéditions → prévisions → historique de 6 semaines ; `--sans-historique` dans les tests) | Démo cohérente quel que soit le jour ; chaque module ne recharge rien s'il est déjà présent. |
| Tâches planifiées Celery Beat | `CELERY_BEAT_SCHEDULE` (`config/settings.py`) | 6 h : alertes de stock ; 9 h 30 en semaine : EDI simulé ; lundi 5 h : prévision figée. Commandes `verifier_alertes` et `simuler_edi` pour lancer à la main. |
| Tests | pytest : `conftest.py` racine + un par app ; Vitest : `mockApi`, `renderApp` (`frontend/src/test/utils.tsx`) | Noms de tests en français décrivant la règle vérifiée. |
| Front-end | hook `useApi` (rechargement par paramètre `?v=`), `auth/roles.ts`, `StatusBadge` | Même façon de faire sur tous les écrans. |

## Points en suspens

À traiter dans les prochaines étapes ou dans une phase complémentaire.

| Sujet | Où en est-on | Quand |
| --- | --- | --- |
| Suite de la feuille de route | Phase 9a (prévisions de vente) faite ; 9b (plan figé à J-2, MRP) à suivre ; autres pistes dans ce tableau (TRS…) | 9b, puis à décider avec Nicolas |
| Stock de produits finis de démonstration | Résolu en 8a par l'historique de 4 semaines (11 produits finis). Les commandes EDI de la démo 7a, reçues avant l'historique, restent en partie non livrées : elles pèsent sur le taux de service de la semaine en cours | — |
| Valorisation des ruptures (CA perdu) | La démarque est valorisée (8a) ; les ruptures ne sont comptées qu'en quantités | Si besoin |
| Pénalités des enseignes sous 98,5 % | Seulement signalées (taux de service en rouge) | Si besoin |
| TRS | « Non disponible » : pas de saisie des arrêts de ligne (la fiabilité des prévisions est disponible depuis la 9a) | Phase complémentaire possible |
| Durée du chargement de l'historique de démo (≈ 6 min, 6 semaines depuis la 9a) | Une seule fois ; les tests utilisent `--sans-historique` ou un historique de 4 jours | À optimiser si besoin |
| Planification avancée : plan figé à J-2, calcul des besoins (MRP) | Prévisions à 8 semaines et promotions faites en 9a | Phase 9b |
| Saisonnalité et événements calendaires dans les prévisions | La moyenne pondérée ne connaît que les 4 dernières semaines ; le commercial corrige à la main | Si besoin, quand l'historique sera plus long |
| Versions datées des nomenclatures | Une seule nomenclature par article (l'historique garde les anciennes valeurs) | Phase complémentaire possible |
| « Refus à quai » à la réception | Une ligne non conforme crée un lot bloqué | Si besoin |
| Envoi d'e-mails (alertes, rappels, commandes fournisseurs en PDF) | Pas de serveur d'envoi ; tout est dans l'application | Si besoin |
| Réservation de stock (OF, préparation) | Pas de réservation ; contrôle du stock au moment de l'opération | Si besoin |
| Formulaires React du référentiel | Saisie dans l'administration Django | Si besoin |
| Jours ouvrés et jours fériés | L'heure limite, le planning et l'historique de démo (7 jours sur 7) ne tiennent pas compte des week-ends | Si besoin |
| Durée de la suite de tests back-end (≈ 5 min en local) | Due surtout aux tests qui rechargent toutes les données de démo | À optimiser (données de démo partagées entre tests) |
| Expéditions de démonstration de la phase 5 | Non rattachées à des commandes clients (numéros `EXP-`) : elles ne comptent pas dans le taux de service | À garder en tête en phase 8 |
| Base locale de Nicolas modifiée par les vérifications | Commande CA-2026-00011 et lot de crème bloqué (5,2 °C), lot de lait libéré et transféré, message EDI `ENS4-…-ERR`, commande CC-2026-00019 préparée et expédiée en 7b (BL-2026-00005, 54 lasagnes), compte `test-verif` désactivé | Repartir d'une base neuve si besoin (procédure dans `docs/prochaine-etape.md`) |
