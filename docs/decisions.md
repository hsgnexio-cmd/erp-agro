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

## Phase 9b – Plan de production hebdomadaire

| Décision | Raison |
| --- | --- |
| Suite de la phase 9 découpée en 9b (plan de production figé à J-2) et 9c (calcul des besoins d'achat / MRP) | Deux pull requests plus faciles à relire et à tester. |
| Plan de la semaine S+1 calculé, ajusté par la production, puis **figé le samedi à 12 h** (Celery Beat, J-2 avant le lundi) ou plus tôt avec un bouton | Validé (fiche : « plan hebdomadaire figé à J-2 »). Le gel crée un OF planifié par produit et par jour ; un plan figé ne se modifie plus. Trop tard une fois la semaine commencée. Logique dans `production/master_plan.py`. |
| Après le gel, on modifie les **OF** (écran existant) ; l'écart avec le plan figé est affiché | Le plan figé reste la référence ; l'OF est la réalité de l'atelier (quantité modifiée, OF annulé, déplacé, autre ligne). |
| Marque Brévanne sur stock : demande + stock de sécurité − stock projeté au lundi | Validé. Demande = prévision de la semaine (dernière version figée qui la couvre, sinon prévision du moment). Stock projeté = lots libérés ou en quarantaine non périmés + OF à venir avant la semaine − demande prévue d'ici lundi (prévision de la semaine en cours au prorata des jours restants), jamais négatif. |
| Stock de sécurité : nouveau champ de l'article « stock de sécurité (jours de demande) » | Validé. Vide = 1 jour, ou 0,5 jour si la durée de vie est de 10 jours ou moins. Stock de sécurité = demande ÷ 7 × jours, arrondi à l'unité supérieure. |
| MDD à la commande : plus grande valeur entre la prévision et les commandes déjà reçues, **sans stock de sécurité** | Validé. Le stock projeté est aussi déduit, pour ne pas refabriquer un surplus déjà en stock. |
| Quantité arrondie au colis de 12 supérieur, répartie à parts égales du lundi au vendredi (le reste sur les premiers jours), première ligne compatible | Validé (fiche : 5 jours sur 7). La production ajuste quantités et ligne avant le gel ; recalculer efface ces ajustements (confirmation demandée). |
| Charge des lignes affichée (quantité ÷ cadence), surcharge au-delà de 15 h par jour | Même règle que le planning de la phase 6 : avertissement, pas blocage. |
| Semi-finis hors du plan | Ils se préparent en cuisine pour les produits finis ; leurs besoins seront calculés par le MRP (9c). |
| Démo : plan de la semaine prochaine calculé **en brouillon**, après l'historique | Aucun plan n'est rejoué dans l'historique : ses OF « planifiés » resteraient dans le passé et fausseraient les indicateurs. La production peut figer le plan de démo (sinon gel automatique samedi). |

### Droits

| Opération | Rôles |
| --- | --- |
| Calculer, ajuster, figer le plan de production | `admin`, `production` |
| Consulter les plans | tous les rôles |

## Phase 9c – Calcul des besoins (MRP)

| Décision | Raison |
| --- | --- |
| Calcul **à la demande**, rien n'est enregistré (`achats/mrp.py`, `/api/achats/mrp/`) | Toujours à jour (prévisions, plan, stock, commandes). La trace durable est la commande fournisseur créée par l'acheteur. Moins d'une seconde sur la démo. |
| Horizon : semaine en cours + 8 semaines, par semaine | Validé. Les emballages ont 3 à 6 semaines de délai : un horizon plus court les commanderait trop tard. |
| Production prévue : OF planifiés ou lancés (reste à fabriquer), puis plan brouillon de la semaine, sinon prévision de la semaine | Validé. Une semaine au plan figé est couverte par ses OF ; pas de double comptage. |
| Éclatement à tous les niveaux, pertes comprises ; semi-finis diminués de leur stock avant d'être éclatés | Validé. Même calcul que les besoins d'un OF (`production.orders.theoretical_needs`). |
| Besoin net = stock disponible (libéré ou en quarantaine, non périmé) + commandes en cours − besoins bruts cumulés | Validé. Les commandes **brouillon** comptent aussi : sinon, recalculer juste après avoir créé les commandes proposerait les mêmes achats. Une livraison en retard compte dans la semaine en cours. |
| Proposition : fournisseur principal audité (sinon un autre fournisseur audité, le plus rapide) ; date de commande = lundi du besoin (ou aujourd'hui) − délai ; « en retard » si elle est passée | Validé. Jamais de proposition chez un fournisseur non audité. |
| Quantité relevée au minimum de commande ; emballages (unités) arrondis à l'unité supérieure | Validé pour le minimum. L'arrondi évite de proposer 4 337,479 cartons. |
| Une commande **brouillon par fournisseur et par semaine de besoin**, livraison prévue la semaine du besoin (au plus tôt après le délai du fournisseur) | Une commande ne peut avoir qu'une ligne par article : un article commandé pour plusieurs semaines donne plusieurs livraisons, chacune comptée dans la bonne semaine au calcul suivant. Toutes les règles d'achat s'appliquent (audit, tarif, minimum). |
| Écran **Besoins d'achat** : propositions « d'ici 7 jours et en retard » par défaut, filtre fournisseur, quantité modifiable, détail semaine par semaine d'un article | L'acheteur choisit ; il vérifie puis envoie les commandes créées comme d'habitude. |
| Pas de données de démo dédiées | Le calcul s'appuie sur les prévisions, le plan brouillon et le stock de la démo. Exemple visible : étiquette MDD `EM-ETIQ-ENS2` (21 jours de délai, minimum 5 000) en retard et relevée au minimum. |
| Limites connues | Semaine entière d'un coup même pour le frais à DLC courte (l'acheteur peut fractionner) ; les OF de semi-finis déjà prévus ne diminuent pas le besoin en semi-finis des produits finis. |

### Droits

| Opération | Rôles |
| --- | --- |
| Transformer des propositions en commandes brouillon | `admin`, `acheteur` |
| Consulter le calcul des besoins | tous les rôles |

## Phase 10 – Arrêts de ligne et TRS

| Décision | Raison |
| --- | --- |
| Temps d'ouverture = **plages de marche déclarées** (début et fin de chaque passage d'OF sur la ligne, arrêts compris), saisies à la déclaration | Validé. Dans la démo, les lignes ne tournent qu'environ 1 h par jour : un temps d'ouverture fixe de 15 h donnerait un TRS d'environ 5 %, sans signification. |
| TRS = disponibilité × performance × qualité = temps utile ÷ temps requis | Validé (norme NF E60-182). Requis = ouverture − arrêts planifiés ; fonctionnement = requis − arrêts non planifiés ; net = produit ÷ cadence ; utile = bon ÷ cadence. Logique dans `production/oee.py`. |
| Calcul **jour par jour et par ligne**, cumulé ensuite ; temps jamais négatifs | Un arrêt plus long que la marche du jour ne retire pas de temps aux autres jours. Même calcul dans la vue `bi.fact_line_time` (un test le vérifie). Une plage et un arrêt comptent le jour de leur début. |
| Arrêts : ligne, début, fin, cause, OF facultatif, commentaire ; 7 causes ; pas de chevauchement sur une ligne ; ni futur, ni plus de 24 h | Validé. « Maintenance préventive » et « nettoyage planifié » sont planifiés : retirés du temps requis, absents des parts du Pareto. |
| Un arrêt ne se modifie pas : il **s'annule avec un motif**, puis se ressaisit | Validé, comme les autres enregistrements de l'ERP (audit). L'annulation est gardée dans l'historique. |
| Plage de marche **obligatoire dans l'application** pour un produit fini (sur ligne) ; deux OF ne marchent pas en même temps sur une ligne ; 16 h au plus | Validé. Les fonctions métier l'acceptent sans plage pour les anciennes déclarations et les tests (`require_run`). Un semi-fini (cuisine) n'a pas de plage. |
| Rebuts : « quantité rebutée » et motif à la déclaration, hors stock | Validé. Quantité produite = lot + rebut ; quantité bonne = lot. |
| Vues `bi.fact_line_stop` et `bi.fact_line_time` (migration `pilotage/0005`) ; tuile TRS activée (filtres période et site), dans l'évolution par semaine et l'export CSV | Même chemin que les autres indicateurs. |
| Écran **TRS des lignes** : TRS et ses trois taux, tableau par ligne, Pareto des arrêts, saisie et annulation des arrêts | Saisie par `production` et `admin`, consultation pour tous. |
| Démo : plages à partir de 5 h, OF de la journée à la suite ; changements de série (3 à 7 min), micro-arrêts, pannes (8 % des OF), manques matière, cadence réelle à 85–97 % ; 0,3 à 2 % de rebuts | Validé. La panne de ligne de l'historique arrête désormais la production après 30 min (20 % de l'OF fabriqué, 5 h de panne) au lieu d'annuler l'OF : elle pèse sur le TRS et crée toujours des ruptures. Tirages aléatoires séparés, pour ne pas changer le reste de l'historique. |

### Droits

| Opération | Rôles |
| --- | --- |
| Saisir ou annuler un arrêt ; déclarer plage de marche et rebuts | `admin`, `production` |
| Consulter le TRS et les arrêts | tous les rôles |

## Phase 11a – Calendrier : jours ouvrés et jours fériés

| Décision | Raison |
| --- | --- |
| Phase 11 découpée en 11a (calendrier et règles) et 11b (historique de démonstration sur le vrai calendrier) | Deux pull requests plus faciles à relire et à tester. |
| Module `referentiel/calendar.py` : les 11 jours fériés de France calculés chaque année (Pâques par l'algorithme grégorien), sans nouvelle bibliothèque | Validé. Rien à saisir chaque année. |
| **Fermetures exceptionnelles** par site (`SiteClosure` : site, du, au, motif ; pas de chevauchement), saisies dans l'administration par le rôle `admin` | Validé (ponts, inventaire annuel…). Historique des modifications (règle 12). |
| Qui travaille quand : production (NAN, REN) du lundi au vendredi ; expédition PFN, livraisons des enseignes et prise de commande du lundi au samedi ; réception MPE du lundi au vendredi ; jamais un jour férié ni un jour de fermeture du site | Validé. Fiche : production 5 j/7 ; la grande distribution est livrée 6 j/7. |
| Heure limite en jours ouvrés : avant 11 h → prochain jour de livraison ; après → le suivant ; une commande reçue un dimanche ou un jour férié compte comme reçue le jour ouvré suivant au matin | Validé. Exemple : mardi 10/11 avant 11 h → jeudi 12/11 (le 11 est férié). |
| Livraison un dimanche ou un jour férié **refusée**, avec la prochaine date possible dans le message | Validé (commande saisie comme EDI). |
| « Livrée à l'heure » = expédiée au plus tard le **jour d'expédition précédent** la livraison (samedi pour un lundi) ; date enregistrée sur la commande à sa création (`ship_by_date`, remplie aussi pour les commandes existantes par la migration `ventes/0003`) | Validé. La vue `bi.fact_service` lit cette date (migration `pilotage/0006`) : pas de calendrier à recalculer en SQL. Une fermeture saisie après la commande ne change pas sa date limite. |
| Plan de production : quantité répartie sur les jours ouvrés de l'usine de la ligne ; saisie refusée un jour fermé ; charge à 0 h de capacité ce jour-là | Validé. |
| Planning : un OF un jour non ouvré est **accepté avec un avertissement** ; cases grisées | Validé (heures supplémentaires possibles), comme la surcharge. |
| Délais fournisseurs en **jours ouvrés de réception** (MPE) : livraison prévue par défaut d'une commande, date de commande et livraison des propositions MRP | Validé. Un délai de 3 jours commandé un vendredi donne une livraison le mercredi. |
| EDI simulé : rien les jours fériés | Validé. |
| Tests : **calendrier 7 j/7 sans jour férié par défaut** (fixture `seven_day_calendar` du `conftest.py` racine) ; les tests du calendrier portent la marque `@pytest.mark.calendrier` | Les tests des autres règles utilisent des dates relatives (« demain ») : ils auraient échoué chaque veille de week-end ou de jour férié (constaté le 10/11, veille de l'Armistice). |
| Démo (11a) : commandes de l'historique et de la démo des expéditions calées sur le premier jour de livraison possible | Pour que le chargement ne soit jamais refusé. Le rejeu complet sur le vrai calendrier (production du lundi au vendredi, stock avant les week-ends) est l'objet de la 11b. |

### Droits

| Opération | Rôles |
| --- | --- |
| Saisir une fermeture exceptionnelle (administration) | `admin` |
| Consulter le calendrier | tous les rôles |

## Phase 11b – Historique de démonstration sur le vrai calendrier

| Décision | Raison |
| --- | --- |
| Commandes des enseignes du lundi au samedi (jours fériés exclus), pour le prochain jour de livraison ; expédition le jour même à 15 h | Même règles que l'application (11a) : heure limite et livraisons en jours ouvrés. |
| Production du lundi au vendredi seulement ; chaque fabrication couvre les expéditions jusqu'au jour de production suivant (le samedi pour le vendredi, la veille d'un jour férié) | Fiche entreprise : 5 jours sur 7. |
| La qualité **libère à 14 h** la production du matin (historique seulement) | Validé par Nicolas (10/11/2026). Sinon, les livraisons du mardi n'auraient pas de produit frais. Dans l'application, la libération reste une décision manuelle de la qualité. |
| Un produit dont la DLC restante serait trop courte à la livraison **n'est pas commandé** ce jour-là (produits à 8 jours livrés le lundi, piémontaise pour ENS4 à 75 %) | Validé par Nicolas (10/11/2026) : assortiment réaliste plutôt que des ruptures artificielles. Calcul : dernier jour de production avant l'expédition + part minimale de l'enseigne ≤ durée de vie. |
| Pas de stock de sécurité la veille d'un week-end ou d'un jour férié | Il vieillissait pendant la fermeture et finissait donné le lundi : la démarque de la démo montait à 9,8 %. |
| Invendables jugés sur la **prochaine livraison réelle** (calendrier) ; achats de frais sur 4 jours de besoin au plus (au lieu de 6) | Sans production le week-end, la viande achetée pour 6 jours périmait. |
| Incidents (panne, fuite, transporteur en retard) au premier jour ouvré à partir du jour prévu ; première prévision figée seulement après une semaine complète de commandes | Résultats identiques quel que soit le jour du chargement ; une première semaine partielle donnait une fiabilité de 34 %. |
| Résultat mesuré (28 derniers jours, chargement du 10/11/2026) | Démarque 1,49 % ; TRS 75 % ; taux de service 99,5 à 99,7 % sur les semaines complètes ; fiabilité des prévisions 83,5 % sur 3 semaines ; rendement 98,5 %. La couverture produits finis par semaine vaut presque 0 : elle est mesurée le dimanche, quand le stock est expédié et que l'usine ne produit pas. La semaine en cours reste basse (commandes de démonstration des phases 7a et 7b). |

## Équipe de démonstration et comptes par rôle

| Décision | Raison |
| --- | --- |
| On garde les **7 rôles** ; plusieurs personnes par rôle (10 comptes : 2 direction, 1 acheteur, 2 magasiniers, 2 responsables de production, 1 qualité, 2 commerciaux) | Chaque rôle est branché sur les droits de tous les écrans : un nouveau rôle demanderait de redécider ses droits partout. Une entreprise a plusieurs personnes par métier (un responsable de production par usine). |
| Nouveau champ **fonction** sur l'utilisateur (`job_title`), affiché en haut de l'application | Montre qui agit (« Claire · Responsable qualité ») plutôt que le seul nom du rôle. |
| Comptes créés par `charger_donnees_demo` (et `creer_comptes_demo`), relançables : un compte existant n'est jamais modifié | Un visiteur qui teste le projet a tout de suite une équipe ; un mot de passe changé par l'utilisateur n'est pas écrasé. |
| Mot de passe commun **`DEMO_USERS_PASSWORD`** dans le `.env` (8 caractères au moins, sinon aucun compte créé) | Jamais de mot de passe dans le code ; comptes de test uniquement. Le compte administrateur reste créé à part (`createsuperuser`). |

## Accès en lecture selon le rôle (moindre privilège)

| Décision | Raison |
| --- | --- |
| Chaque rôle ne **voit** que les domaines utiles à son métier ; matrice centrale `comptes/access.py` (`READ_AREAS`) | Demande de Nicolas (10/11/2026) : principe du moindre privilège, comme dans un vrai ERP. Remplace la règle « tous les rôles consultent tout » des débuts. |
| Appliquée **par le serveur** (attribut `read_area` des vues, contrôlé par `WriteRolesPermission`) ; le menu, l'accueil et les pages suivent la même matrice (`/api/auth/me/` renvoie les domaines, `auth/roles.ts`) | Cacher un écran ne suffit pas : les données d'un autre domaine sont refusées (403). Un écran hors du rôle affiche « Accès réservé ». |
| Socle commun à tous : référentiel, lots et stocks, traçabilité et rappels | Tout le monde a besoin de l'état des lots ; un rappel produit concerne toute l'entreprise. |
| **Prix masqués** : prix d'achat réservés à achats et direction, prix de vente à ventes et direction ; les autres voient les commandes sans les montants | Le quai réceptionne et expédie sans avoir à connaître les prix. |
| ~~Tableau de bord réservé à la direction~~ → remplacé le 10/11/2026 par le **tableau de bord par rôle** (section suivante) | Chaque métier a aussi besoin de suivre ses indicateurs. |
| `admin` et les superutilisateurs voient tout | Administration et maintenance. |

| Domaine (écrans) | direction | acheteur | magasinier | production | qualite | commercial |
| --- | :-: | :-: | :-: | :-: | :-: | :-: |
| Référentiel (articles, fournisseurs, clients, sites, calendrier) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Lots, stocks, FEFO, températures, inventaires, alertes | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Traçabilité, rappels, allergènes | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Commandes fournisseurs, réceptions | ✅ | ✅ | ✅ | ✅ | ✅ | — |
| Prix d'achat (tarifs, montants des commandes fournisseurs) | ✅ | ✅ | — | — | — | — |
| Besoins d'achat (MRP) | ✅ | ✅ | — | ✅ | — | — |
| Production, planning, plan de production, TRS | ✅ | ✅ | — | ✅ | ✅ | — |
| Commandes clients, EDI, expéditions, taux de service | ✅ | — | ✅ | — | ✅ | ✅ |
| Prix de vente (tarifs, montants des commandes clients) | ✅ | — | — | — | — | ✅ |
| Prévisions de vente | ✅ | ✅ | — | ✅ | — | ✅ |
| Tableau de bord (indicateurs de son métier, export Excel) ; montants en euros | ✅ (tout, avec les euros) | ✅ | ✅ | ✅ | ✅ | ✅ |

## Tableau de bord par rôle

| Décision | Raison |
| --- | --- |
| Tableau de bord ouvert à tous les rôles ; chaque rôle n'y voit que les **indicateurs de son métier** (`DASHBOARD_INDICATORS` de `comptes/access.py`) : qualité → conformité réception, délai de traçabilité, démarque en % ; production → rendement matière, TRS, couverture matières ; achats → couverture matières, conformité réception ; commercial → taux de service, fiabilité des prévisions ; magasinier → taux de service, couverture produits finis | Validé par Nicolas (10/11/2026) : chacun suit ses objectifs au même endroit, sans voir ceux des autres métiers. |
| `admin` et `direction` voient les 9 indicateurs ; un utilisateur à plusieurs rôles voit la réunion de leurs indicateurs | La direction pilote l'ensemble. |
| **Montants en euros réservés à la direction** : pour les autres, la valeur (%, jours) reste, mais le détail en euros (CA, démarque, stocks valorisés) est remplacé par « Calculé en valeur ; montants en euros réservés à la direction » | Même logique que les prix masqués. |
| Filtrage **par le serveur** : l'API, l'évolution par semaine et l'export CSV ne contiennent que les indicateurs du rôle ; les autres ne sont pas calculés (écran plus rapide) | Cacher une tuile à l'écran ne suffirait pas. |
| L'écran n'affiche les filtres site et enseigne que si un indicateur visible en tient compte | Pas de filtre sans effet. |
| Power BI (utilisateur `powerbi`) inchangé : il lit toutes les vues `bi` | Outil de la direction. |

## Relecture générale du code (finition, 10/11/2026)

| Constat | Suite donnée |
| --- | --- |
| Règles métier : aucun mouvement ni lot supprimé (seulement des brouillons), aucune mise à jour en masse (`update()`) qui contournerait l'historique, statut d'un lot modifié en un seul endroit (`stocks/services.py`), `float` seulement dans la génération de la démo | Rien à corriger. |
| `ruff` en mode strict : alertes « injection SQL » de `pilotage/indicators.py` | Fausses alertes : noms de colonnes écrits dans le code, valeurs passées en paramètres. |
| Simplifications possibles (conditions imbriquées, `dict.fromkeys`) | Corrigées ; règles `SIM` et `C4` ajoutées à `ruff` (surveillées par GitHub Actions). Règles `PERF` non retenues : leurs réécritures rendent les boucles moins lisibles pour un gain négligeable. |
| `check --deploy` : réglages HTTPS absents, `DEBUG` actif | Normal pour une application locale de développement ; section « Limites » du README. |
| `npm audit` : 0 faille dans l'application ; faille modérée de `minimatch` dans l'outil de lint seulement | Pas de correction : la seule proposée revient à une ancienne version d'eslint. |

## Accélération des tests (finition, 10/11/2026)

| Décision | Raison |
| --- | --- |
| **pytest-xdist** (`-n auto` dans `pyproject.toml`) : tests répartis sur tous les cœurs, une base de test par processus | Suite complète de 7 min 19 à 2 min 25 sur le PC de Nicolas (16 cœurs) ; plus rapide aussi sur GitHub Actions (4 cœurs). Petite dépendance de développement, sans effet sur l'application. |
| Les bases de test (« test_… ») ne redonnent pas ses droits à l'utilisateur `powerbi` après `migrate` | Power BI ne s'y connecte pas, et 16 bases créées en même temps modifiaient ce rôle commun au serveur (« tuple concurrently updated »). |
| Le test de l'utilisateur Power BI prend un nom de rôle par processus (`powerbi_test_gw0`…) | Un rôle PostgreSQL vaut pour tout le serveur. |
| Pas de chargement partagé des données de démonstration entre tests | Gain de quelques secondes seulement, au prix de tests qui dépendraient les uns des autres. Le temps restant est surtout fixe : création des bases (≈ 20 s) et test de l'historique (≈ 30 s). |

## Publication (finition, 10/11/2026)

| Sujet | Décision | Pourquoi |
| --- | --- | --- |
| Licence | PolyForm Noncommercial 1.0.0 (`LICENSE.md`), avis « Required Notice » au nom de Nicolas | Choix de Nicolas : code lisible et réutilisable pour apprendre, mais pas d'usage commercial sans licence séparée (garder la possibilité de vendre). MIT écartée. |
| Rappel produit dans la démo | Dernier jour de l'historique, 20 h : rappel d'un lot de crème `MP-LAI-CREME35` déjà consommé. Parmi les 12 derniers, on prend celui dont le rappel est le plus parlant : des lots encore en stock à bloquer, puis le plus d'enseignes livrées (`pilotage/demo_history.py`, `_recall`). La première règle (« reçu au moins 6 jours plus tôt ») ne bloquait aucun lot certains jours (lendemain de jour férié) | Le scénario de référence se voit dans la démo (menu Rappels, vue `bi.fact_recall`) ; les produits finis encore en stock sont bloqués, comme dans la réalité. |
| Captures d'écran du README | `docs/captures/`, prises sur une démo neuve (compte de la direction), 1440 × 900 | Montrer l'ERP sans avoir à l'installer. |
| Audit de cohérence avant publication | 16 contrôles sur les données de démo (stock jamais négatif, consommation / expédition seulement si libéré, DLC calculées, DLC minimale enseigne, traçabilité complète, alertes de température, vues `bi`) : tous bons ; 38 écrans ouverts sans erreur | Vérifier les règles métier sur des données réelles, pas seulement dans les tests. |
| Historique Git | Aucun secret : `.env` jamais commité, seuls des mots de passe d'exemple dans `.env.example` et le README | Préalable au passage du dépôt en public. |

## Conventions techniques transverses

Règles de fonctionnement prises en cours de route, valables pour tous les modules.

| Convention | Où | Raison |
| --- | --- | --- |
| `ValidatedModel` : validation complète (`full_clean`) à chaque enregistrement | `referentiel/models.py` | Les règles s'appliquent quel que soit le chemin (API, administration, script, données de démo). |
| Les opérations relisent et verrouillent le lot (`select_for_update`) | `stocks/services.py`, `production/services.py`, `ventes/services.py` | Statut et stock lus à l'instant de l'opération ; deux personnes ne modifient pas le même lot en même temps. |
| Enregistrements jamais modifiés ni supprimés | `StockMovement`, `LotStatusChange`, `TemperatureReading`, `ProductRecall`, `Alert` (marquée traitée), `ForecastVersion`, `ForecastLine`, `ForecastAdjustment`, `LineStop` (annulé avec motif) | Preuves pour les audits IFS / BRCGS (règles 11 et 12). |
| Documents d'opération en lecture seule dans l'administration | `ReadOnlyAdminMixin` (`stocks/admin.py`) | Commandes, réceptions, lots, OF, inventaires, rappels, commandes clients naissent des opérations de l'application, qui appliquent les règles. |
| Numérotation par compteur en base | `referentiel.services.next_document_number`, modèle `DocumentSequence` (aussi pour la série des SSCC et les versions de prévision `PRV-`) | Sans doublon même en accès simultané ; numéro attribué après validation. |
| Droits par rôle | `comptes.permissions.WriteRolesPermission` + `write_roles` sur chaque vue ; `sync_group_permissions` après chaque `migrate` | Lecture pour tous, écriture selon le métier ; mêmes droits dans l'administration. |
| Décimaux renvoyés en texte par l'API (`"4.2000"`) | toutes les API | Aucune perte de précision ; le front-end formate en français (`formatDecimal`, `formatMoney`). |
| Erreurs métier → réponse 400 lisible | `config/exceptions.py` ; côté React `errorMessages` + `ErrorList` | Les messages des règles s'affichent tels quels à l'utilisateur. |
| Connexion par session Django + jeton CSRF | `comptes/views.py`, `DJANGO_CSRF_TRUSTED_ORIGINS` | Sécurité standard ; l'origine du front-end (`localhost:5173`) doit être déclarée de confiance. |
| Données de démonstration : une commande, relançable, dates relatives à aujourd'hui | `charger_donnees_demo` (référentiel → achats → stocks → surveillance → traçabilité → production → ventes → expéditions → prévisions → historique de 6 semaines → plan de production de S+1 (brouillon) ; `--sans-historique` dans les tests) | Démo cohérente quel que soit le jour ; chaque module ne recharge rien s'il est déjà présent. |
| Tâches planifiées Celery Beat | `CELERY_BEAT_SCHEDULE` (`config/settings.py`) | 6 h : alertes de stock ; 9 h 30 en semaine : EDI simulé ; lundi 5 h : prévision figée ; samedi 12 h : plan de production de S+1 figé. Commandes `verifier_alertes` et `simuler_edi` pour lancer à la main. |
| Tests | pytest : `conftest.py` racine + un par app ; Vitest : `mockApi`, `renderApp` (`frontend/src/test/utils.tsx`) | Noms de tests en français décrivant la règle vérifiée. Calendrier 7 j/7 par défaut, vrai calendrier avec `@pytest.mark.calendrier` (phase 11). |
| Front-end | hook `useApi` (rechargement par paramètre `?v=`), `auth/roles.ts`, `StatusBadge` | Même façon de faire sur tous les écrans. |

## Points en suspens

À traiter dans les prochaines étapes ou dans une phase complémentaire.

| Sujet | Où en est-on | Quand |
| --- | --- | --- |
| Suite de la feuille de route | Phases 9 (planification) et 10 (TRS) terminées ; autres pistes dans ce tableau | À décider avec Nicolas |
| Stock de produits finis de démonstration | Résolu en 8a par l'historique de 4 semaines (11 produits finis). Les commandes EDI de la démo 7a, reçues avant l'historique, restent en partie non livrées : elles pèsent sur le taux de service de la semaine en cours | — |
| Valorisation des ruptures (CA perdu) | La démarque est valorisée (8a) ; les ruptures ne sont comptées qu'en quantités | Si besoin |
| Pénalités des enseignes sous 98,5 % | Seulement signalées (taux de service en rouge) | Si besoin |
| Durée du chargement de l'historique de démo (≈ 6 min, 6 semaines depuis la 9a) | Une seule fois ; les tests utilisent `--sans-historique` ou un historique de 4 jours | À optimiser si besoin |
| Saisonnalité et événements calendaires dans les prévisions | La moyenne pondérée ne connaît que les 4 dernières semaines ; le commercial corrige à la main | Si besoin, quand l'historique sera plus long |
| Versions datées des nomenclatures | Une seule nomenclature par article (l'historique garde les anciennes valeurs) | Phase complémentaire possible |
| Facturation et comptabilité (factures, avoirs, TVA, export comptable) | Hors périmètre : l'ERP s'arrête à l'expédition | Indispensable avant tout usage réel |
| Coût de revient des recettes | Prix d'achat et de vente connus, pas de calcul du coût de revient | Si besoin |
| « Refus à quai » à la réception | Une ligne non conforme crée un lot bloqué | Si besoin |
| Envoi d'e-mails (alertes, rappels, commandes fournisseurs en PDF) | Pas de serveur d'envoi ; tout est dans l'application | Si besoin |
| Réservation de stock (OF, préparation) | Pas de réservation ; contrôle du stock au moment de l'opération | Si besoin |
| Formulaires React du référentiel | Saisie dans l'administration Django | Si besoin |
| Durée de la suite de tests back-end | Résolu : ≈ 2 min 30 en parallèle (pytest-xdist, voir « Accélération des tests ») | — |
| Expéditions de démonstration de la phase 5 | Non rattachées à des commandes clients (numéros `EXP-`) : elles ne comptent pas dans le taux de service | À garder en tête en phase 8 |
| Base locale de Nicolas modifiée par les vérifications | Commande CA-2026-00011 et lot de crème bloqué (5,2 °C), lot de lait libéré et transféré, message EDI `ENS4-…-ERR`, commande CC-2026-00019 préparée et expédiée en 7b (BL-2026-00005, 54 lasagnes), compte `test-verif` désactivé | Repartir d'une base neuve si besoin (procédure dans `docs/prochaine-etape.md`) |
