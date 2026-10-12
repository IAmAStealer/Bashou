# Packages only: zsh's copy of handover.bash (read that one for the why). Sourced by /etc/profile.d/bashou.sh,
# which zsh reads through its zprofile in `emulate sh`: the hook is defined under `emulate zsh` so it runs
# with zsh's options. At the first prompt, once ~/.zshrc is done, it removes itself and:
# - nothing loaded Bashou: the package's loader starts the pet (not for root, not after `bashou off`);
# - ~/.zshrc loads an old git copy: that pet stops and the package's loader takes over.

emulate zsh -c '
_bashou_handover() {
  local st=$? package=${BASHOU_PACKAGE_DIR:-/usr/share/bashou}
  precmd_functions=(${precmd_functions:#_bashou_handover})
  unfunction _bashou_handover
  if [[ -z ${BASHOU_DIR:-} && $EUID != 0 && -r $package/bashou.zsh
        && ! -e ${BASHOU_DATA:-$HOME/.local/share/bashou}/off ]]; then
    _bashou_auto=1
    source "$package/bashou.zsh"
  elif [[ -n ${BASHOU_DIR:-} && -z ${BASHOU_KEEP_CLONE:-} && $BASHOU_DIR != "$package" && -r $package/bashou.zsh ]]; then
    bashou off
    source "$package/bashou.zsh"
  fi
  return $st
}
'
precmd_functions=(_bashou_handover $precmd_functions)
