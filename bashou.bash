# Bashou: a pet that lives in the top-right corner of your terminal and grows as you learn bash.
# Load it from ~/.bashrc:  source ~/Bashou/bashou.bash

[[ $- == *i* && -t 1 ]] || return 0

BASHOU_DIR=$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")
_bashou_data=${BASHOU_DATA:-$HOME/.local/share/bashou}
_bashou_events=$_bashou_data/events.$$
_bashou_erase=${BASHOU_CACHE:-$HOME/.cache/bashou}/erase.$$
mkdir -p "$_bashou_data"

# Log each new history entry as "status<TAB>history line". No fork: builtins only.
# $HISTCMD only moves when a command is added, so empty Enters are not counted.
_bashou_log() {
  local status=$?
  if [[ -n $BASHOU_PID && -n $_bashou_hc && $HISTCMD != "$_bashou_hc" ]]; then
    printf '%s\t' "$status" >> "$_bashou_events"
    HISTTIMEFORMAT= history 1 >> "$_bashou_events"
  fi
  _bashou_hc=$HISTCMD
  return "$status"
}

# Erase the pet before a command runs, so it never scrolls with the output.
_bashou_ps0() {
  local seq
  [[ -n $BASHOU_PID && -r $_bashou_erase ]] || return
  IFS= read -rd '' seq < "$_bashou_erase"
  printf '%s' "$seq"
}

bashou() {
  case $1 in
    off)
      [[ -n $BASHOU_PID ]] || return 0
      _bashou_ps0
      kill "$BASHOU_PID" 2>/dev/null
      BASHOU_PID=
      ;;
    on)
      [[ -z $BASHOU_PID ]] || return 0
      { PYTHONPATH=$BASHOU_DIR python3 -m bashou.companion "$$" </dev/null 2>/dev/null & } 2>/dev/null
      BASHOU_PID=$!
      disown "$BASHOU_PID"
      ;;
    *) PYTHONPATH=$BASHOU_DIR python3 -m bashou "$@" ;;
  esac
}

# Tab completion. Static lists (no Python on Tab); tests/test_completion.py keeps them in sync.
_bashou_commands="level pets achievements fight talk swap stats dev on off"
_bashou_pets="cat frog turtle mushroom slime sofa octopus dragon fox owl mole snake ghost spider ant axolotl"
_bashou_dev="unlock-all stage stage-all threat restore"
_bashou_challenges="grep_hydra awk_golem find_wraith uniq_swarm sed_serpent ps_phantom"

_bashou_complete() {
  local cur=${COMP_WORDS[COMP_CWORD]} words
  case "$COMP_CWORD:${COMP_WORDS[1]}:${COMP_WORDS[2]}" in
    1:*)              words=$_bashou_commands ;;
    2:swap:*)         words=$_bashou_pets ;;
    2:dev:*)          words=$_bashou_dev ;;
    3:dev:stage)      words=$_bashou_pets ;;
    3:dev:stage-all)  words="1 2 3" ;;
    3:dev:threat)     words=$_bashou_challenges ;;
    4:dev:stage)      words="1 2 3" ;;
  esac
  COMPREPLY=($(compgen -W "$words" -- "$cur"))
}
complete -F _bashou_complete bashou

[[ ${PROMPT_COMMAND[0]} == _bashou_log* ]] || PROMPT_COMMAND="_bashou_log${PROMPT_COMMAND:+;$PROMPT_COMMAND}"
[[ $PS0 == *_bashou_ps0* ]] || PS0='$(_bashou_ps0)'"$PS0"
trap 'bashou off' EXIT
bashou on
