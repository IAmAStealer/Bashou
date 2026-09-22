# Bashou

A little pixel-art pet that lives in the corner of your terminal and grows while you learn bash.
Run commands, try new tools, and collect new pets along the way.

## Install

Copy this line into your terminal:

```bash
git clone https://github.com/IAmAStealer/Bashou.git ~/.bashou && echo 'source ~/.bashou/bashou.bash' >> ~/.bashrc && source ~/.bashrc
```

You need bash and python3 (already there on most Linux systems).

## Use

```bash
bashou          # see how your pet is doing
bashou -h       # all commands
bashou update   # get the new version (your pet tells you when there is one)
```

## Uninstall

```bash
sed -i '/\.bashou\/bashou\.bash/d' ~/.bashrc && rm -rf ~/.bashou
```

Your progress stays in `~/.local/share/bashou` (delete it too to forget everything).

## More

The [guide](doc/GUIDE.md) explains pets, achievements, fights and translations.
Want to help? Pixel art, security challenges and adventure questions are welcome: [contributing](.github/CONTRIBUTING.md).
[How it started](doc/STORY.md): made with AI for responsible use (learning, so you can do it too); the Rust version is written by hand.

MIT license.
