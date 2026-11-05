# Ce que tu peux faire

[English](COMMANDS.md) · **Français**

| Commande | Ce qu'elle fait |
|---|---|
| `bashou learn <commande>` | Démonte une commande et explique chaque morceau : options, arguments, pipes, redirections (88 commandes, de `ls` à `tar`, `awk`, `gpg` et `kubectl`) |
| *(ton compagnon)* | Donne des astuces en chemin (Ctrl+R, `cd -`, `du -sh *`…) et repère les outils que tu n'as pas encore essayés |
| *(succès)* | **304 succès** récompensent de vraies compétences : un pipe de 3 commandes, `find -exec`, `sed -i`, `git bisect`… |
| `bashou fight` | Des menaces apparaissent de temps en temps : bats-les dans un shell bac à sable avec le bon outil, `grep` contre l'Hydre des logs, `awk` contre le Golem comptable |
| `bashou lesson` | La bibliothèque de la Chouette sage : des leçons avec des dessins qui se complètent page après page, sur un parcours qui s'ouvre quand tu réussis |
| `bashou project` | 13 vrais projets en Python, Shell, C et Rust (fusionner des PDF, trier des photos, un script de sauvegarde…), un petit pas à la fois |
| `bashou spot` | Jeu rapide : une IPv6, un hash, du base64, un JWT… dis ce que c'est, de plus en plus vite |
| `bashou arena` | Un combat chronométré, ou une enquête de sécurité (un fichier caché, une porte dérobée dans cron, un binaire SUID) |
| `bashou adventure` | Une balade à travers 13 thèmes avec 503 questions sur ce qui tourne mal et ce qu'il faut vérifier en premier, des boss et des coffres |
| `bashou share` | Un QR code : ton téléphone dessine une bannière de ton compagnon et de ta progression, à envoyer où tu veux |

## Combats

Une commande réussie avec le bon outil touche l'ennemi. Seule une mauvaise réponse à `answer` coûte un cœur : essaie autant que tu veux.

| Combat | Ce que tu fais |
|---|---|
| Code | Répare un petit fichier Python, C ou Rust cassé |
| Scripts | Répare un script bash ; il doit ensuite tenir sur les fichiers piégés de Bashou |
| Paquets | Interroge ta machine avec `apt`, `dpkg` ou `rpm`, ou répare un fichier de dépôt |
| CI/CD | Répare un fichier GitHub Actions ou GitLab CI |
| SQL | Interroge et répare une base SQLite |
| Secrets | Entraîne-toi à `gpg` et `pass` avec leur propre clé et leur propre coffre, jamais les tiens |
| Réseau | Lis les adresses, les services et des captures ; rien ne sort de ta machine |

Les combats gagnés reviennent après 1, 7 et 30 jours, pour que ce que tu as appris reste.
Dans un combat, `lesson` ouvre la leçon qui l'explique.

## Joue sur deux ordinateurs

```bash
bashou export                           # écrit bashou-save-DATE.txt ici
bashou import bashou-save-DATE.txt      # sur l'autre ordinateur, même version de Bashou
```

Pour chaque chose, Bashou garde le meilleur des deux ordinateurs. Le fichier ne contient ni commandes, ni compteurs d'outils, ni dates ;
`bashou export --full` emporte tout.

## Tes données restent sur ta machine

Bashou ne collecte rien : pas de compte, pas de télémétrie, pas de pub.

- Il lit tes commandes seulement pour compter les outils, et garde ces compteurs dans `~/.local/share/bashou`.
- Il demande seulement à internet si une nouvelle version est sortie, une fois par jour. `bashou config updates off` l'arrête ; avec apt ou dnf, il ne demande jamais.

Bashou est un petit projet perso, fait avec des jetons d'IA en trop par quelqu'un qui aime enseigner. Il n'y a rien à vendre.

`bashou share` montre ce que contient la bannière avant le QR code : pas de commandes, de fichiers, de noms de machines ni de dates.
