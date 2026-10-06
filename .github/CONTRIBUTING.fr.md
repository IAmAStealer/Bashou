# Contribuer

*[English](CONTRIBUTING.md)*

Les idées, les signalements de bugs, le pixel art, les traductions, les questions et les défis de sécurité
sont les bienvenus. Tu peux écrire en français ou en anglais, dans les tickets comme dans les pull requests.

La plupart des contributions ne demandent pas de code : tu modifies un fichier JSON (ou tu dessines des PNG)
et tu lances une vérification. Les guides détaillés sont en anglais.

| Tu veux… | Tu modifies | Guide |
|---|---|---|
| Traduire le jeu | `bashou/locales/<langue>.json` | [translations.md](../doc/contributing/translations.md) |
| Traduire les questions d'aventure | `bashou/adventure/questions/<langue>/<sujet>.json` | [translations.md](../doc/contributing/translations.md) |
| Écrire ou corriger une leçon | `bashou/lesson/en/<id>.json` | [lessons.md](../doc/contributing/lessons.md) |
| Ajouter des questions d'aventure | `bashou/adventure/questions/en/<sujet>.json` | [questions.md](../doc/contributing/questions.md) |
| Améliorer le pixel art d'un compagnon | `bashou/pets/<compagnon>.json` | [pixel-art.md](../doc/contributing/pixel-art.md) |
| Dessiner de plus grands compagnons à la main (16/32/64 px, sans code, sans IA) | `art/<compagnon>/<taille>/<pose>.png` | [pixel-art.md](../doc/contributing/pixel-art.md) |
| Écrire un défi de sécurité | Python (une petite fonction de préparation) | [security-challenges.md](../doc/contributing/security-challenges.md) |
| Empaqueter les versions (apt, dnf) | `tools/package.py`, `.github/workflows/packages.yml` | [packaging.md](../doc/contributing/packaging.md) |

Traduire avec un agent IA : voir [doc/agents/translation.md](../doc/agents/translation.md).

Bugs et idées : [ouvre un ticket](https://github.com/IAmAStealer/Bashou/issues/new/choose) et choisis un
formulaire. Il y en a en français : *Signaler un bug (en français)* et *Proposer une idée (en français)*.
Pas à l'aise avec le JSON ? Les formulaires *Adventure question* et *Lesson* marchent aussi. Les problèmes de
sécurité passent par le [signalement privé](https://github.com/IAmAStealer/Bashou/security/advisories/new),
jamais par un ticket public, parce qu'un ticket est lu par tout le monde avant d'être corrigé.

Tout ce que tu envoies doit être à toi (pas de copies de jeux, de CTF ou d'autres projets), et est partagé
sous la licence MIT du projet. Avant une pull request, lance `python3 -m unittest`.

**Travailler avec une IA est bienvenu** (Bashou lui-même est construit ainsi, voir
[comment tout a commencé](../doc/STORY.md)), avec une exception : le **dossier `art/` et les grands sprites**
(`bashou/pets/large/`) sont pour les humains, dessinés à la main, sans IA. `art/` ne demande pas de
programmation : dessine des fichiers PNG, dépose-les dans une pull request, et on les transforme en fichiers
du jeu. Les sprites qui vont directement dans le jeu (`bashou/pets/<compagnon>.json`, 17 × 12) peuvent être
dessinés avec une IA et sont relus à la main. Les nouveaux compagnons sont bienvenus aussi, et au mieux en
**ensemble complet** : le compagnon et ses succès, un combat avec ses indices, une leçon qui cite le combat, et
des questions d'aventure (voir [curriculum.md](../doc/contributing/curriculum.md)). Quel que soit l'outil, tu
es responsable de ce que tu envoies : relis-le, teste-le et vérifie les faits.

Tout le monde suit le [code de conduite](CODE_OF_CONDUCT.md) : gentil et patient, les débutants d'abord.
