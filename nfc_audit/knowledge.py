"""Base de connaissance normative (vectorisée dans ChromaDB).

Les textes sont des synthèses en français destinées à la démonstration ; ils ne
remplacent pas les référentiels officiels. La référence COBAC est reprise telle
que fournie dans le dossier de conception : à faire valider par la Conformité.
"""

NORMS = [
    dict(
        id="COBAC-12", framework="COBAC", source="COBAC R-2016/04",
        article="Art. 12 – Contrôle des accès",
        content=("Les établissements de crédit doivent garantir une séparation stricte des fonctions et "
                 "assurer une traçabilité intégrale des accès aux systèmes d'information. Tout accès "
                 "privilégié (compte administrateur) doit faire l'objet d'une autorisation préalable "
                 "nominative et d'une revue mensuelle."),
        tags="accès privilège administrateur autorisation revue séparation fonctions traçabilité compte base de données modification",
    ),
    dict(
        id="ISO-A5.18", framework="ISO", source="ISO/IEC 27001:2022",
        article="A.5.18 – Droits d'accès",
        content=("Les droits d'accès aux informations et aux actifs associés sont attribués, revus, modifiés "
                 "et retirés conformément à la politique d'accès. Les droits sont supprimés au départ d'une "
                 "personne ou ajustés lors d'un changement de poste ; les comptes inactifs ne sont pas "
                 "réactivés sans demande approuvée (équivalent de A.9.2.6 dans la version 2013)."),
        tags="droits accès compte inactif réactivation départ désactivation création suppression approbation",
    ),
    dict(
        id="ISO-A8.2", framework="ISO", source="ISO/IEC 27001:2022",
        article="A.8.2 – Droits d'accès privilégiés",
        content=("L'attribution et l'utilisation des droits d'accès privilégiés sont restreintes et gérées : "
                 "autorisation formelle, revue régulière, comptes d'administration dédiés et traçables."),
        tags="privilège administrateur admin dba groupe élévation compte à privilèges",
    ),
    dict(
        id="ISO-A8.15", framework="ISO", source="ISO/IEC 27001:2022",
        article="A.8.15 – Journalisation",
        content=("Les journaux enregistrant les activités, exceptions, défaillances et autres événements "
                 "pertinents sont produits, protégés, conservés et analysés, notamment pour les actions "
                 "privilégiées, les accès et les modifications."),
        tags="journalisation logs événements revue traçabilité audit connexion",
    ),
    dict(
        id="ISO-A8.16", framework="ISO", source="ISO/IEC 27001:2022",
        article="A.8.16 – Activités de surveillance",
        content=("Les réseaux, systèmes et applications sont surveillés pour détecter les comportements "
                 "anormaux (rafales d'échecs d'authentification, connexions inhabituelles) et déclencher une "
                 "réponse appropriée."),
        tags="surveillance détection échec authentification connexion brute force anomalie",
    ),
    dict(
        id="ISO-A8.32", framework="ISO", source="ISO/IEC 27001:2022",
        article="A.8.32 – Gestion des changements",
        content=("Les changements apportés aux moyens de traitement de l'information et aux systèmes "
                 "d'information sont soumis à des procédures formelles de gestion des changements."),
        tags="changement production base de données alter drop update ticket rfc modification",
    ),
    dict(
        id="COBIT-DSS05.04", framework="COBIT", source="COBIT 2019",
        article="DSS05.04 – Gérer l'identité des utilisateurs et les accès logiques",
        content=("Gérer les demandes d'accès, la distribution des droits et la révocation de manière "
                 "centralisée, en cohérence avec les processus de gestion des demandes ITIL et avec la "
                 "validation des responsables métier."),
        tags="accès identité droits demande validation révocation compte privilège",
    ),
    dict(
        id="COBIT-BAI06", framework="COBIT", source="COBIT 2019",
        article="BAI06 – Gérer les changements IT",
        content=("Tous les changements (urgents, normaux, standards) sont enregistrés, évalués, autorisés "
                 "avant leur mise en œuvre puis revus après déploiement."),
        tags="changement autorisation production base de données modification urgence",
    ),
    dict(
        id="COBIT-DSS05.07", framework="COBIT", source="COBIT 2019",
        article="DSS05.07 – Superviser l'infrastructure et les événements de sécurité",
        content=("Surveiller l'infrastructure pour détecter les événements liés à la sécurité et gérer les "
                 "vulnérabilités, avec analyse et escalade des anomalies."),
        tags="supervision événements sécurité détection connexion échec anomalie",
    ),
    dict(
        id="ITIL-CHG", framework="ITIL", source="ITIL v4",
        article="Change Enablement & Service Validation",
        content=("Toute modification de configuration, attribution de privilège ou intervention sur une base "
                 "de données critique doit être corrélée à un ticket de changement (RFC) approuvé dans l'outil "
                 "ITSM."),
        tags="changement ticket rfc itsm approuvé configuration privilège base de données",
    ),
    dict(
        id="ITIL-INC", framework="ITIL", source="ITIL v4",
        article="Incident Management",
        content=("Les événements de sécurité détectés (connexions suspectes, compromission présumée) donnent "
                 "lieu à un incident enregistré, priorisé, traité puis clos avec analyse de cause."),
        tags="incident sécurité connexion suspecte échec compromission réponse",
    ),
]

NORMS_BY_ID = {n["id"]: n for n in NORMS}
