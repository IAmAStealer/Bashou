# Bashou

[English](README.md) · **Français**

[![CI](https://github.com/IAmAStealer/Bashou/actions/workflows/ci.yml/badge.svg)](https://github.com/IAmAStealer/Bashou/actions/workflows/ci.yml)
[![CodeQL](https://github.com/IAmAStealer/Bashou/actions/workflows/codeql.yml/badge.svg)](https://github.com/IAmAStealer/Bashou/actions/workflows/codeql.yml)
[![OpenSSF Scorecard](https://api.securityscorecards.dev/projects/github.com/IAmAStealer/Bashou/badge)](https://scorecard.dev/viewer/?uri=github.com/IAmAStealer/Bashou)
[![Release](https://img.shields.io/github/v/release/IAmAStealer/Bashou)](https://github.com/IAmAStealer/Bashou/releases/latest)
[![Licence : MIT](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

Apprends les commandes Linux et les scripts bash gratuitement, dans ton propre terminal.

Un petit compagnon en pixel art vit dans le coin de ton terminal. Il grandit pendant que tu apprends la ligne
de commande. Commence par bash. Ensuite, choisis : Linux, systemd, les paquets, gpg et pass, SQL, la CI/CD,
Python, C ou Rust. Lance des commandes, essaie de nouveaux outils, et rencontre de nouveaux compagnons en chemin.

Le jeu est traduit en français : `bashou config language fr`.

![Une petite poussière d'étoile en pixel art dans le coin du terminal, avec une astuce dans sa bulle, au-dessus
d'une explication `bashou learn` d'une commande tar](doc/img/prompt.svg)

## Installer

Bashou a ses propres dépôts signés : installe-le une fois, et il se met à jour avec le reste de ton système.

**Debian, Ubuntu** (apt) :

```bash
sudo mkdir -p -m 755 /etc/apt/keyrings
sudo curl -fsSLo /etc/apt/keyrings/bashou.asc https://iamastealer.github.io/Bashou/bashou.asc
printf '%s\n' 'Types: deb' 'URIs: https://iamastealer.github.io/Bashou/deb/' 'Suites: ./' \
  'Signed-By: /etc/apt/keyrings/bashou.asc' | sudo tee /etc/apt/sources.list.d/bashou.sources
sudo apt update && sudo apt install bashou
```

**Rocky, Alma, RHEL, Fedora** (dnf) :

```bash
sudo curl -fsSLo /etc/yum.repos.d/bashou.repo https://iamastealer.github.io/Bashou/bashou.repo
sudo dnf install bashou
```

Ouvre un nouveau terminal : ton compagnon est là. Chaque utilisateur a le sien, sauf root.
`bashou off` le cache, aussi dans les nouveaux terminaux. `bashou on` le fait revenir.
Pas de compagnon sur Debian ou Ubuntu ? Lance `bashou on` une fois : ça ajoute une ligne à ton `~/.bashrc`.
Les mises à jour arrivent avec `apt upgrade` ou `dnf upgrade`.

**Tout autre Linux**, ou pour suivre le code au fur et à mesure, avec git :

```bash
git clone https://github.com/IAmAStealer/Bashou.git ~/.bashou && echo 'source ~/.bashou/bashou.bash' >> ~/.bashrc && source ~/.bashrc
```

Il te faut bash et python3. La plupart des Linux les ont déjà.

## Quoi de neuf

**0.8.5**
- **Encore des secrets** : un nouveau compagnon secret, deux amis cachés de plus, et un indice pour le plus féroce.

**0.8.4**
- **Des amis secrets** se cachent dans Bashou et autour. Les curieux les trouveront.

**0.8.3**
- **Bashou parle français** sur le web : un README en français, une page d'accueil en français, et des
  formulaires en français pour signaler un bug ou proposer une idée.
- **Actif dès l'installation** : avec `apt` ou `dnf`, ouvre un nouveau terminal et ton compagnon est là.
  `bashou off` le garde éteint jusqu'à `bashou on`.
- Le Pigeonneau a un nouveau look.

**0.8.2**
- **Ton compagnon de départ grandit plus loin** : quatre nouvelles formes pour chaque lignée, jusqu'à l'Univers,
  l'Arbre-monde et un Caillou chéri.
- **`bashou spot`** : des hachages de mots de passe, des jetons CSRF et des chaînes OAuth2 à reconnaître.
- Un deuxième compagnon secret, pour ceux qui aiment la bagarre.

**0.8.1**
- **`bashou share`** : ta carte montre maintenant ton meilleur score à `bashou spot` et tes compagnons rares :
  ceux que tu as fait grandir jusqu'à leur dernière forme, et les plus durs à rencontrer.

**0.8.0**
- **`bashou project`** : 13 vrais projets à construire en Python, Shell, C ou Rust, une petite étape à la fois,
  et un nouveau compagnon, le Paysage, qui passe d'une colline à une ville au fil de tes projets.
- **`bashou spot`** : une IPv6, un hachage, du base64, un JWT, une ligne de Rust ? Dis ce qu'est la chaîne, le
  plus vite possible, en 25 secondes. Un nouveau compagnon arrive avec : le Caméléon, jusqu'à l'Aigle.
- **`bashou here`** amène ton compagnon dans le terminal où tu tapes.
- Une nouvelle leçon sur la substitution de commande, `$( )` : les guillemets, les codes de retour, et les mots
  de passe de `pass` dans les scripts.

Tous les changements, version par version (en anglais) : [CHANGELOG.md](CHANGELOG.md).

## Apprendre le terminal sans demander à une IA

Bashou t'apprend dans ton vrai terminal, pendant que tu travailles. Il marche hors ligne : pas de compte, pas
de modèle d'IA, pas de jetons dépensés pour savoir ce que fait une commande. Il ne te gêne pas : un seul
compagnon pour tous tes terminaux, et il ne dessine jamais par-dessus ton texte.

- **`bashou learn <commande>`** démonte une commande et explique chaque morceau : la commande, chaque option,
  les arguments, les pipes et les redirections (71 commandes, de `ls` à `tar`, `awk`, `gpg` et `kubectl`).
  Sans commande, il explique la dernière que ton compagnon t'a suggérée.
- **Ton compagnon donne des astuces** en chemin (Ctrl+R, `cd -`, `du -sh *`…) et repère les outils que tu
  n'as pas encore essayés.
- **171 succès** récompensent de vraies compétences : un pipe de 3 commandes, `find -exec`, `sed -i`,
  `git bisect`, `tar -tf`…
- **Des menaces** apparaissent de temps en temps. `bashou fight` ouvre un shell bac à sable où tu les bats avec
  le bon outil : `grep` contre l'Hydre des logs, `awk` contre le Golem comptable. Ça commence par les premiers
  pas (une option à trouver dans `--help`, une faute à corriger dans ton éditeur, des fichiers à ranger) et ça
  monte jusqu'aux droits Linux, aux services et aux conflits de fusion git. Une commande réussie avec le bon
  outil touche l'ennemi ; les autres te coûtent un cœur. Les combats de code te donnent un petit fichier Python
  ou C cassé à réparer (un `;` oublié, une boucle sans fin, une fuite de mémoire, une injection shell) ; les
  combats de paquets interrogent ta propre machine avec `apt`, `dpkg` ou `rpm`, ou te font réparer un fichier
  de dépôt ; les combats CI/CD te donnent un fichier GitHub Actions ou GitLab CI à réparer ; les combats SQL
  te donnent une base SQLite à interroger et à réparer. Les combats de secrets apprennent `gpg` et `pass`, avec
  leur propre clé et leur propre coffre d'entraînement : les tiens ne sont jamais touchés. Les combats réseau
  lisent tes adresses et tes routes avec `ip`, trouvent un service avec `ss`, et lisent des captures avec
  `tcpdump -r` ; rien ne sort de ta machine.
  Les combats gagnés reviennent après 1, 7 et 30 jours (répétition espacée), pour que ce que tu as appris reste.
- **`bashou lesson`** : la bibliothèque de la Chouette sage. Des leçons avec des dessins qui se complètent page
  après page (la pile et le tas, où va la sortie, les permissions, `$( )`…), sur un parcours : chacune s'ouvre
  quand tu as réussi les précédentes, en gagnant un combat ou un succès. Ton éditeur, c'est toi qui le
  choisis, nano ou vi.
- **`bashou project`** : tu veux pratiquer un langage mais tu ne sais pas *quoi* programmer ? 13 vrais projets
  en Python, Shell, C et Rust, du très facile au difficile : fusionner des PDF, trier tes photos par date, un
  script de sauvegarde, un minuteur Pomodoro… Une petite étape à la fois : chaque étape dit quoi faire et
  quand c'est fini, jamais comment, avec un indice si tu bloques.
- **`bashou spot`** : un jeu rapide. Une chaîne apparaît : une adresse IPv6, une MAC, un hachage, du base64, un
  JWT, une regex, une ligne de Python ou de SQL… Dis ce que c'est avec les flèches, de plus en plus vite, en
  25 secondes.
- **`bashou arena`** : viens te battre quand tu veux. Un combat chronométré, ou une enquête de sécurité sans
  chrono (un fichier caché, une porte dérobée dans cron, un binaire SUID).
- **`bashou adventure`** : une balade à travers 12 thèmes (logique de code, bash, Linux, systemd, Python, Rust,
  C, Debian, Rocky Linux, CI/CD, SQL, réseaux) avec 379 questions sur ce qui tourne mal et ce qu'il faut
  vérifier en premier, des boss, et des coffres qui s'ouvrent avec de vraies commandes.

![bashou fight : une Planète et ses cœurs face à l'Hydre des logs, la tâche dans une bulle, et le shell de
l'arène en dessous](doc/img/duel.svg)

## Découvre les compagnons

Choisis un compagnon de départ : Poussière, Graine ou Caillou. Il grandit jusqu'au niveau 20 et change de
forme en chemin. Ce qu'il devient, c'est à toi de le découvrir.

31 autres compagnons se cachent dans ton terminal. Chacun vient de ce qu'il représente : une Gouttelette après
tes 10 premières commandes, un codeur de nuit pour tes premiers programmes, un champignon pour tes propres
scripts, d'autres pour un nouvel outil assez utilisé, un long pipe, un combat perdu ou gagné, une balade dans
l'aventure… Le tableau des compagnons ne montre que leur silhouette tant que tu ne les as pas rencontrés.

![Les trois compagnons de départ, Poussière, Graine et Caillou, puis trois des premiers compagnons à
rencontrer](doc/img/pets.svg)

## Montre ton compagnon

**`bashou share`** affiche un QR code dans ton terminal. Scanne-le, et ton téléphone dessine une bannière de ton
compagnon, de sa famille et de ta progression, avec un bouton pour l'envoyer sur Signal, WhatsApp ou ailleurs.
La première fois, il te demande un pseudo à afficher à la place de ton vrai nom.

Avant le QR code, Bashou liste exactement ce que contient la carte : pas de commandes, de fichiers, de noms
de machines ni de dates. La progression voyage dans le lien, après le `#`, une partie que les navigateurs
n'envoient jamais à un serveur.

## Tes données restent sur ta machine

Bashou ne collecte rien. Pas de compte, pas de télémétrie, pas de statistiques, pas de pub : **tu n'es pas le
produit.** Il lit tes commandes seulement pour compter les outils et les constructions, garde ces compteurs dans
`~/.local/share/bashou`, et ne les envoie jamais nulle part. La seule chose qu'il demande à internet, c'est si
une nouvelle version est sortie (une fois par jour ; `bashou config updates off` l'arrête, et avec apt ou dnf
c'est ton gestionnaire de paquets qui s'en occupe).

Bashou est un petit projet perso, fait avec des jetons d'IA en trop par quelqu'un qui aime enseigner et aider
les gens. Il n'y a rien à vendre.

## Utiliser

```bash
bashou                       # voir comment va ton compagnon
bashou -h                    # toutes les commandes
bashou here                  # amener ton compagnon dans ce terminal
bashou config language fr    # le jeu en français
bashou update                # prendre la nouvelle version (apt ou dnf pour les paquets)
```

## Désinstaller

Installé en paquet : `sudo apt remove bashou` ou `sudo dnf remove bashou`, puis enlève la ligne
`source /usr/share/bashou/bashou.bash` de `~/.bashrc` si tu l'avais ajoutée.

Installé avec git :

```bash
sed -i '/\.bashou\/bashou\.bash/d' ~/.bashrc && rm -rf ~/.bashou
```

Ta progression reste dans `~/.local/share/bashou` (supprime-le aussi pour tout oublier).

## Plus

Le [guide](doc/GUIDE.md) (en anglais) explique les compagnons, les succès, les combats et les traductions.
Un bug, une idée ? [Signale un bug](https://github.com/IAmAStealer/Bashou/issues/new?template=6-bug-fr.yml)
ou [propose une idée](https://github.com/IAmAStealer/Bashou/issues/new?template=7-idea-fr.yml).
Envie d'aider ? Pixel art, leçons, défis de sécurité et questions d'aventure sont les bienvenus :
[contribuer](.github/CONTRIBUTING.fr.md).

Licence MIT.
