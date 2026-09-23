# Bashou: a pet that lives in the top-right corner of your terminal and grows as you learn bash.
# Load it from ~/.bashrc:  source ~/Bashou/bashou.bash

[[ $- == *i* && -t 1 ]] || return 0

BASHOU_DIR=$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")
_bashou_data=${BASHOU_DATA:-$HOME/.local/share/bashou}
_bashou_events=$_bashou_data/events.$$
_bashou_erase=${BASHOU_CACHE:-$HOME/.cache/bashou}/erase.$$
_bashou_height=${BASHOU_CACHE:-$HOME/.cache/bashou}/height.$$
mkdir -p "$_bashou_data"
_bashou_restarts=0

# Log each new history entry as "status<TAB>history line". No fork: builtins only.
# $HISTCMD only moves when a command is added, so empty Enters are not counted.
_bashou_log() {
  local status=$? last=$_
  # `clear` put the prompt back on the top line, under the pet.
  [[ $last == clear || $last == reset ]] && _bashou_below
  if [[ -n $BASHOU_PID && -n $_bashou_hc && $HISTCMD != "$_bashou_hc" ]]; then
    printf '%s\t' "$status" >> "$_bashou_events"
    HISTTIMEFORMAT='' history 1 >> "$_bashou_events"
  fi
  _bashou_hc=$HISTCMD
  # Poke the pet so it redraws now (PS0 erased it). If it died, bring it back (3 tries max).
  if [[ -n $BASHOU_PID ]] && ! kill -USR1 "$BASHOU_PID" 2>/dev/null && (( _bashou_restarts++ < 3 )); then
    BASHOU_PID=
    bashou on
  fi
  return "$status"
}

# The pet is drawn over the top lines of the screen: move the prompt down past it, or the first
# commands' output would hide under the pet. Cursor down doesn't scroll: on a full screen it does
# nothing. (Asking the terminal where the cursor is could swallow keys typed at that moment.)
_bashou_below() {
  local lines=6
  [[ -r $_bashou_height ]] && IFS= read -r lines < "$_bashou_height"
  printf '\e[%dB' "$lines"
}

# Ctrl+L too: clear the screen like readline does, then start below the pet (readline redraws the line).
_bashou_clear() {
  printf '\e[H\e[2J'
  _bashou_below
}
bind -x '"\C-l": _bashou_clear' 2>/dev/null

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
      # SIGUSR1 ignored until Python installs its handler (the default action would kill it).
      { (trap '' USR1; exec python3 "$BASHOU_DIR/launch.py" bashou.companion "$$") </dev/null 2>/dev/null & } 2>/dev/null
      BASHOU_PID=$!
      disown "$BASHOU_PID"
      ;;
    *) python3 "$BASHOU_DIR/launch.py" bashou "$@" ;;
  esac
}

# Tab completion. Static lists (no Python on Tab); tests/test_completion.py keeps them in sync.
_bashou_commands="level pets achievements fight talk learn explain evolve swap stats start language skills config setup update version security adventure reset dev on off"
_bashou_pets="bat frog turtle mushroom slime sofa octopus dragon fox owl mole snake ghost spider ant axolotl gremlin snail beaver squirrel pigeon hedgehog bee whale meerkat"
_bashou_dev="unlock-all stage stage-all level threat restore"
_bashou_challenges="line_moth column_crab jumble_sprite last_word_wisp first_line_imp needle_gnat field_wasp dust_bunny verse_viper peak_harpy grep_hydra awk_golem find_wraith uniq_swarm sed_serpent ps_phantom pipe_eel colon_cobra semicolon_slug list_leech dict_djinn loop_lich ouroboros json_jinn base64_banshee percent_poltergeist injection_imp token_trickster leak_lurker fencepost_fiend stack_specter overflow_ogre mut_marmot const_condor shadow_shade byte_basilisk version_vole candidate_crow stowaway_stoat autoremove_adder release_raven hitchhiker_hare census_centipede mirror_mimic repo_revenant enabled_ettin"
_bashou_security="1 2 3 4 5 6"

_bashou_complete() {
  local cur=${COMP_WORDS[COMP_CWORD]} words
  case "$COMP_CWORD:${COMP_WORDS[1]}:${COMP_WORDS[2]}" in
    1:*)              words=$_bashou_commands ;;
    2:swap:*)         words="starter $_bashou_pets" ;;
    2:config:*)       words="bubble updates size talk quiet" ;;
    2:update:*)       words="--version" ;;
    2:explain:*)      words="python rust c" ;;
    3:explain:rust)   words="mut shadowing const integers" ;;
    3:explain:python) words="list dict loop recursion json url base64 subprocess" ;;
    3:explain:c)      words="malloc array string recursion asan" ;;
    3:config:size)    words="small large default" ;;
    2:security:*)     words=$_bashou_security ;;
    3:config:bubble)  words="default" ;;
    3:config:talk)    words="off default" ;;
    3:config:quiet)   words="default" ;;
    3:config:updates) words="on off default" ;;
    2:dev:*)          words=$_bashou_dev ;;
    3:dev:stage)      words=$_bashou_pets ;;
    3:dev:stage-all)  words="1 2 3" ;;
    3:dev:level)      words="1 2 3 4 5 6 7 8 9" ;;
    3:dev:threat)     words=$_bashou_challenges ;;
    4:dev:stage)      words="1 2 3" ;;
  esac
  mapfile -t COMPREPLY < <(compgen -W "$words" -- "$cur")
}
complete -F _bashou_complete bashou

[[ ${PROMPT_COMMAND[0]} == _bashou_log* ]] || PROMPT_COMMAND="_bashou_log${PROMPT_COMMAND:+;$PROMPT_COMMAND}"
# shellcheck disable=SC2016  # expanded later, by bash, each time PS0 is shown
[[ $PS0 == *_bashou_ps0* ]] || PS0='$(_bashou_ps0)'"$PS0"
trap 'bashou off' EXIT

# First time: choose a starter (builtins only to check, Python only for the picker).
_bashou_ready() {
  local s
  [[ -r $_bashou_data/state.json ]] && IFS= read -rd '' s < "$_bashou_data/state.json"
  [[ $s == *'"language": "'* ]] && [[ $s == *'"starter": "'* || $s == *'"cat"'* ]]
}
if _bashou_ready || bashou start; then
  _bashou_below
  bashou on
fi
