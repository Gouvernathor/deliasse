# deliasse

Ce repo est basé sur [Deliasse-demons](https://framagit.org/parlement-ouvert/deliasse-daemons).
Il permet de capter les données des amendements déposés sur Eliasse à l'assemblée nationale et dans ses commissions.

Les nouvelles fonctionnalités par rapport au repo original sont :
1. Le rafraîchissement périodique infini, pour actualiser en continu les informations collectées, est maintenant optionnel, et désactivé par défaut. Elles étaient justifiées par le caractère de daemon du projet originel, mais on peut maintenant l'utiliser pour simplement constituer une base de données sans la mettre à jour en continu.
2. Paramétrage des organes à considérer par ligne de commande. Au lieu de surveiller à la fois la séance publique et toutes les commissions, on peut ne surveiller qu'un sous-ensemble de celles-ci.
3. Conversion du code au modèle orienté-objet. Il en découle une simplification de la lecture du code et de ce à quoi correspond chaque fonction, en évitant par exemple d'utiliser des dictionnaires partout.
