"""Start a Bashou module: python3 launch.py bashou [args], python3 launch.py bashou.companion <pid>…

`python3 -m bashou` would look in the current folder first: a `bashou/` folder there (a clone, a
download, a shared directory) would run instead of this install. A script only looks next to itself.
"""

import runpy
import sys

if __name__ == "__main__":
    runpy.run_module(sys.argv.pop(1), run_name="__main__", alter_sys=True)
