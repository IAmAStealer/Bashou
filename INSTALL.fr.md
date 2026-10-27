# Installer Bashou

[English](INSTALL.md) · **Français**

Sur Debian, Ubuntu, Rocky, Alma, RHEL ou Fedora, prends les dépôts signés : voir le [README](README.fr.md#installer). Cette page est pour tout le reste.

## Tout autre Linux, avec git

Clone le code et charge-le depuis ton `~/.bashrc` (aussi le moyen de suivre le code au fur et à mesure) :

```bash
git clone https://github.com/IAmAStealer/Bashou.git ~/.bashou && echo 'source ~/.bashou/bashou.bash' >> ~/.bashrc && source ~/.bashrc
```

Il te faut bash et python3. La plupart des Linux les ont déjà.

## zsh

Ton terminal tourne avec zsh ? Bashou y marche aussi : les combats se passent alors dans zsh, et les leçons
disent où zsh lit une ligne autrement. Bashou s'ajoute à `~/.zshrc` la première fois qu'il démarre dans bash,
et le dit. Seulement zsh sur cette machine ? Charge `bashou.zsh` depuis ton `~/.zshrc` :

```bash
echo 'source ~/.bashou/bashou.zsh' >> ~/.zshrc && source ~/.zshrc
```

## macOS

Avec [Homebrew](https://brew.sh) : Bashou tourne dans zsh, le shell du Mac.

```bash
brew install iamastealer/bashou/bashou
bashou on
```

La première ligne ajoute le tap de Bashou (un petit dépôt avec la recette que suit brew) et l'installe. La
deuxième ajoute une ligne à ton `~/.zshrc`, pour que ton compagnon vienne dans chaque nouveau terminal.
`brew upgrade` le met à jour avec tes autres outils ; `bashou update` te le rappelle.
Sur un Mac, les questions et les leçons parlent de macOS : celles propres à Linux (systemd, apt, dnf, `ip`,
`ss`) sont mises de côté. Tu travailles aussi sur des serveurs Linux ? `bashou config os both` les ramène.
Le bash fourni avec macOS est trop vieux pour Bashou (il faut la 4.4) : utilise zsh, ou un bash récent
(`brew install bash`).
Tu as utilisé l'installeur de test (`install-macos.sh`) ? Retire d'abord la ligne `source ~/.bashou/bashou.zsh`
de ton `~/.zshrc` et le dossier `~/.bashou`. Tes compagnons et ta progression restent : ils sont dans
`~/.local/share/bashou`.

## De git aux dépôts

Installé avec git sur Debian ou Red Hat, et tu veux le dépôt à la place ? Lance `bashou update --packages`.
Il montre chaque commande qu'il va lancer, te demande, puis fait le passage. Tes compagnons et ta progression sont gardés.

## Désinstaller

Installé avec git :

```bash
sed -i '/\.bashou\/bashou\.bash/d' ~/.bashrc; sed -i '/\.bashou\/bashou\.zsh/d' ~/.zshrc 2>/dev/null; rm -rf ~/.bashou
```

Installé avec Homebrew : `brew uninstall bashou`, puis enlève la ligne `bashou.zsh` de `~/.zshrc`.

Ta progression reste dans `~/.local/share/bashou` (supprime-le aussi pour tout oublier).
