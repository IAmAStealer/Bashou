# Install Bashou

**English** · [Français](INSTALL.fr.md)

On Debian, Ubuntu, Rocky, Alma, RHEL or Fedora, use the signed repositories: see the [README](README.md#install). This page is for everything else.

## Any other Linux, with git

Clone the code and load it from your `~/.bashrc` (also the way to follow the code as it's written):

```bash
git clone https://github.com/IAmAStealer/Bashou.git ~/.bashou && echo 'source ~/.bashou/bashou.bash' >> ~/.bashrc && source ~/.bashrc
```

You need bash and python3. Most Linux systems already have them.

## zsh

Your terminal runs zsh? Bashou works there too: fights then happen in zsh, and the lessons say where zsh
reads a line differently. Bashou adds itself to `~/.zshrc` the first time it starts in bash, and says so.
Only zsh on this machine? Load `bashou.zsh` from your `~/.zshrc`:

```bash
echo 'source ~/.bashou/bashou.zsh' >> ~/.zshrc && source ~/.zshrc
```

## macOS

With [Homebrew](https://brew.sh): Bashou runs in zsh, the Mac's own shell.

```bash
brew install iamastealer/bashou/bashou
bashou on
```

The first line adds Bashou's tap (a small repository with the recipe brew follows) and installs it. The
second one adds one line to your `~/.zshrc`, so the pet comes in every new terminal. `brew upgrade` updates
it with your other tools; `bashou update` reminds you of that.
On a Mac, the questions and lessons are about macOS: Linux-only ones (systemd, apt, dnf, `ip`, `ss`) are left
out. Do you also work on Linux servers? `bashou config os both` brings them back.
macOS's own bash is too old for Bashou (it needs 4.4): use zsh, or a newer bash (`brew install bash`).
Used the test installer (`install-macos.sh`)? Remove the line `source ~/.bashou/bashou.zsh` from your
`~/.zshrc` and the `~/.bashou` folder first. Your pets and progress stay: they live in `~/.local/share/bashou`.

## From git to the repositories

Installed with git on Debian or Red Hat, and want the repository instead? Run `bashou update --packages`.
It shows every command it will run, asks you, then moves you over. Your pets and progress are kept.

## Uninstall

Installed with git:

```bash
sed -i '/\.bashou\/bashou\.bash/d' ~/.bashrc; sed -i '/\.bashou\/bashou\.zsh/d' ~/.zshrc 2>/dev/null; rm -rf ~/.bashou
```

Installed with Homebrew: `brew uninstall bashou`, then remove the `bashou.zsh` line from `~/.zshrc`.

Your progress stays in `~/.local/share/bashou` (delete it too to forget everything).
