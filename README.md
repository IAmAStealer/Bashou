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
```

## Uninstall

```bash
sed -i '/\.bashou\/bashou\.bash/d' ~/.bashrc && rm -rf ~/.bashou
```

Your progress stays in `~/.local/share/bashou` (delete it too to forget everything).

## More

The [guide](doc/GUIDE.md) explains pets, achievements, fights and translations.
[How it started](doc/STORY.md): fully vibecoded for testing, a single Rust binary is the goal.

MIT license.
