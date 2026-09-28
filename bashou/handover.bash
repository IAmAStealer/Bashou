# Packages only, sourced by /etc/profile.d/bashou.sh before ~/.bashrc runs.
# A ~/.bashrc that still loads an old git copy of Bashou keeps running that copy, which apt and dnf never
# update (user report: no `bashou share` with 0.6.2 installed). At the first prompt, once ~/.bashrc is
# done, the copy's pet stops and the package's loader takes over. BASHOU_KEEP_CLONE=1 keeps the copy.

_bashou_handover() {
  local status=$? package=${BASHOU_PACKAGE_DIR:-/usr/share/bashou}
  PROMPT_COMMAND=${PROMPT_COMMAND//_bashou_handover;/}
  PROMPT_COMMAND=${PROMPT_COMMAND//;_bashou_handover/}
  PROMPT_COMMAND=${PROMPT_COMMAND//_bashou_handover/}
  unset -f _bashou_handover
  if [[ -n ${BASHOU_DIR:-} && -z ${BASHOU_KEEP_CLONE:-} && $BASHOU_DIR != "$package" && -r $package/bashou.bash ]]; then
    bashou off
    # shellcheck source=bashou.bash
    source "$package/bashou.bash"
  fi
  return "$status"
}
PROMPT_COMMAND="_bashou_handover${PROMPT_COMMAND:+;$PROMPT_COMMAND}"
