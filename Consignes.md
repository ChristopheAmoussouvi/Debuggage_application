Débugger une application
Assigné
fr

F
Bertrand Fournel
créé : 04/10/25
L'objectif est d’identifier une anomalie dans le code de l’application. Après analyse, il s’agit d’expliquer clairement la cause de l’erreur, puis de proposer et d’appliquer un correctif minimal garantissant la stabilité du service. La résolution du problème doit être documenté de manière détaillée : préciser la nature du bug, son origine dans le flux de traitement, et la solution mise en œuvre pour y remédier. Afin d’éviter que ce type d’incident ne se reproduise, l’objectif est de mettre en place un ensemble simple de tests automatisés dans le cadre d'un déploiement CI/CD fictif, en s’appuyant sur GitHub Actions. Ces tests doivent permettre de détecter toute régression ou anomalie lors des futures mises à jour du code Flask.
Référentiels
\[2023] Certification RNCP Développeur.se en intelligence artificielle
Contexte du projet
En tant que développeur, résoudre les incidents techniques en apportant les modifications nécessaires au code de l’application et en documentant les solutions pour en garantir le fonctionnement opérationnel.

Surveiller une application , en mobilisant des techniques de monitorage et de journalisation, dans le respect des normes de gestion des donnée personnelles en vigueur,

Modalités pédagogiques
Travail individuel

Modalités d'évaluation
Restitution écrite et oral et évaluation devant un jury
Livrables
Livrable E5 (environ 5 pages + annexes et appendices pour prouver)
Critères de performance
Critères du référentiel :

C20 :

* La documentation liste les métriques et les seuils et valeurs d’alerte pour chaque métrique à risque.
* La documentation explicite les arguments en faveur des choix techniques pour l’outillage du monitorage de l’application.
* Les outils (collecteurs, journalisation, agrégateurs, filtres, dashboard, etc.) sont installés et opérationnels à minima en environnement local.
* Les règles de journalisation sont intégrées aux sources de l’application, en fonction des métriques à surveiller.
* Les alertes sont configurées et en état de marche, en fonction des seuils préalablement définis.

C21 :

* La ou les causes du problème sont identifiées correctement.
* Le problème est reproduit en environnement de développement.
* La procédure de débogage du code est documentée depuis l’outil de de suivi.
* La solution documentée explicite chaque étape de la résolution et de son implémentation.
* La solution est versionnée dans le dépôt Git du projet d’application (par exemple avec une merge request)
  Assignation



proposition de plan de rédaction : 



# Surveillance et résolution d’incidents E5

1 L’incident technique (C21)  
1.1 Analyse de l’incident  
1.2 Résolution de l’incident  
1.3 Tests automatisés pour éviter la régression  
1.4 Journalisation et monitoring

2 Feedback Loop (C20)  
2.1 Principes  
2.2 Modélisation base de données

3 Conclusion (C20, C21)



