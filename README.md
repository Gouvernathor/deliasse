# deliasse

Ce repo est basé sur [Deliasse-demons](https://framagit.org/parlement-ouvert/deliasse-daemons).
Il permet de capter les données des amendements déposés sur Eliasse à l'assemblée nationale et dans ses commissions.

Les nouvelles fonctionnalités par rapport au repo original sont :
1. Le rafraîchissement périodique infini, pour actualiser en continu les informations collectées, est maintenant optionnel, et désactivé par défaut. Elles étaient justifiées par le caractère de daemon du projet originel, mais on peut maintenant l'utiliser pour simplement constituer une base de données sans la mettre à jour en continu.
2. Paramétrage des organes à considérer par ligne de commande. Au lieu de surveiller à la fois la séance publique et toutes les commissions, on peut ne surveiller qu'un sous-ensemble de celles-ci.
3. Conversion du code au modèle orienté-objet. Il en découle une simplification de la lecture du code et de ce à quoi correspond chaque fonction, en évitant par exemple d'utiliser des dictionnaires partout.

## Usage

```cli
py aspire.py [-v] [-t=TARGET_DIR] [-l=LEGI] [-r] [-o=ORGANES]
```
* `-v` ou `--verbose` active le mode verbeux, et affiche plus d'informations sur la sortie standard.
* `-t` ou `--target_dir` change le répertoire où seront écrites les données. Par défaut, il s'agit sur dossier `./out`, qui est créé si il n'existait pas.
* `-l` ou `--legislature` change le numéro de la législature considérée. Par défaut, c'est la législature actuelle au moment où ce code est écrit, donc la XVIème.
* `-r` ou `--refresh` active le rafraîchissement infini de la base de données.
* `-o` ou `--organes` fournit une liste d'organes à considérer, au lieu de considérer la séance publique de l'assemblée et toutes les commissions. Il accepte une liste de codes de commissions (séparés par des virgules), qui peuvent être trouvés dans le fichier `organes.json` créé après une première requête. Ils sont de la forme `AN` pour la séance publique, ou `CION_X` ou `CION-X` pour les commissions.
