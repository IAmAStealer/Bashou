# Packages only, sourced by /etc/profile.d/bashou.sh before ~/.bashrc runs. At the first prompt, once
# ~/.bashrc is done:
# - nothing loaded Bashou: the package's loader starts the pet, on by default for every user but root.
#   `bashou off` writes ~/.local/share/bashou/off and new terminals skip it, until `bashou on`.
# - ~/.bashrc still loads an old git copy, which apt and dnf never update (user report: no `bashou share`
#   with 0.6.2 installed): the copy's pet stops and the package's loader takes over. BASHOU_KEEP_CLONE=1
#   keeps the copy.

_bashou_handover() {
  local status=$? package=${BASHOU_PACKAGE_DIR:-/usr/share/bashou}
  PROMPT_COMMAND=${PROMPT_COMMAND//_bashou_handover;/}
  PROMPT_COMMAND=${PROMPT_COMMAND//;_bashou_handover/}
  PROMPT_COMMAND=${PROMPT_COMMAND//_bashou_handover/}
  unset -f _bashou_handover
  if [[ -z ${BASHOU_DIR:-} && $EUID != 0 && -r $package/bashou.bash
        && ! -e ${BASHOU_DATA:-$HOME/.local/share/bashou}/off ]]; then
    _bashou_auto=1
    # shellcheck source=bashou.bash
    source "$package/bashou.bash"
  elif [[ -n ${BASHOU_DIR:-} && -z ${BASHOU_KEEP_CLONE:-} && $BASHOU_DIR != "$package" && -r $package/bashou.bash ]]; then
    bashou off
    # shellcheck source=bashou.bash
    source "$package/bashou.bash"
  fi
  return "$status"
}
PROMPT_COMMAND="_bashou_handover${PROMPT_COMMAND:+;$PROMPT_COMMAND}"
