# Bashou: a pet that lives in the top-right corner of your terminal and grows as you learn bash.
# Load it from ~/.bashrc:  source ~/Bashou/bashou.bash

[[ $- == *i* && -t 1 ]] || return 0

# A git copy hands over to the apt or dnf package once it's installed. Otherwise a ~/.bashrc line that
# `bashou update` couldn't rewrite keeps loading this copy, which dnf never updates (user report, 0.6.2).
_bashou_pkg=${BASHOU_PACKAGE_LOADER:-/usr/share/bashou/bashou.bash}
if [[ -z $BASHOU_KEEP_CLONE && -r $_bashou_pkg && $(readlink -f "$_bashou_pkg") != "$(readlink -f "${BASH_SOURCE[0]}")" ]]; then
  unset _bashou_pkg
  # shellcheck source=bashou.bash
  source "${BASHOU_PACKAGE_LOADER:-/usr/share/bashou/bashou.bash}"
  return
fi
unset _bashou_pkg

BASHOU_DIR=$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")
_bashou_data=${BASHOU_DATA:-$HOME/.local/share/bashou}
_bashou_events=$_bashou_data/events.$$
_bashou_erase=${BASHOU_CACHE:-$HOME/.cache/bashou}/erase.$$
_bashou_height=${BASHOU_CACHE:-$HOME/.cache/bashou}/height.$$
_bashou_room=${BASHOU_CACHE:-$HOME/.cache/bashou}/room.$$
_bashou_fight=${BASHOU_CACHE:-$HOME/.cache/bashou}/fight.$$
# One pet for all your terminals: this file holds the PID of the shell it lives in. The other shells are
# guests: no pet drawn there, their commands go to guest.<pid> and the pet counts them too.
_bashou_home=${BASHOU_CACHE:-$HOME/.cache/bashou}/pet
_bashou_guest=
# The events file holds what you type, for your pet: yours only, whatever the umask (older versions
# made the folders 755, readable by other accounts where home folders are).
(umask 077; mkdir -p "$_bashou_data" "${_bashou_erase%/*}"; : >> "$_bashou_events") 2>/dev/null
for _bashou_dir in "$_bashou_data" "${_bashou_erase%/*}"; do
  [[ ${_bashou_dir##*/} == bashou && -O $_bashou_dir ]] && chmod 700 "$_bashou_dir" 2>/dev/null
done
unset _bashou_dir
_bashou_restarts=0

# Log each new history entry as "status<TAB>history line". No fork: builtins only.
# $HISTCMD only moves when a command is added, so empty Enters are not counted.
_bashou_log() {
  local status=$? last=$_
  # The pet's terminal closed: it moves into this one.
  if [[ -n $_bashou_guest ]] && ! _bashou_elsewhere && _bashou_claim; then
    bashou on
  fi
  # `bashou here` in another terminal took the pet: this one becomes a guest (its pet took its drawing down).
  if [[ -n $BASHOU_PID ]] && _bashou_elsewhere; then
    kill "$BASHOU_PID" 2>/dev/null
    BASHOU_PID=
    _bashou_guest=1
    _bashou_events=$_bashou_data/guest.$$
  fi
  # The Honey badger got bored and picked a fight (bashou/fight.py): the arena opens, no need to ask.
  if [[ -n $BASHOU_PID && -e $_bashou_fight ]]; then
    rm -f "$_bashou_fight"
    python3 "$BASHOU_DIR/launch.py" bashou.fight badger
  fi
  if [[ -n $BASHOU_PID ]]; then
    _bashou_make_room
  fi
  # No cursor reports from this terminal: at least `clear` puts the prompt back under the pet.
  [[ -n $BASHOU_PID && $_bashou_dsr == off && ( $last == clear || $last == reset ) ]] && _bashou_below
  if [[ ( -n $BASHOU_PID || -n $_bashou_guest ) && -n $_bashou_hc && $HISTCMD != "$_bashou_hc" ]]; then
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

# True when the pet lives in another shell that is still open. Builtins only: guests check at each prompt.
_bashou_elsewhere() {
  local pid
  [[ -r $_bashou_home ]] && IFS= read -r pid < "$_bashou_home"
  [[ -n $pid && $pid != "$$" ]] && kill -0 "$pid" 2>/dev/null
}

# Take the pet's home for this shell, unless another shell took it first: two terminals opened at the
# same moment (a tmux session coming back) must not both start one. noclobber makes the write atomic.
_bashou_claim() {
  local taken=1
  [[ $- == *C* ]] || { set -C; taken=; }
  { echo "$$" > "$_bashou_home"; } 2>/dev/null ||
    { ! _bashou_elsewhere && rm -f "$_bashou_home" && { echo "$$" > "$_bashou_home"; } 2>/dev/null; }
  local ok=$?
  [[ -n $taken ]] || set +C
  return "$ok"
}

# shellcheck source=bashou/room.bash
source "$BASHOU_DIR/bashou/room.bash"

# Ctrl+L too: clear the screen like readline does, then start below the pet (readline redraws the line).
# Not in a guest terminal: no pet there, so no empty rows at the top.
_bashou_clear() {
  printf '\e[H\e[2J'
  [[ -n $BASHOU_PID ]] && _bashou_below
}
bind -x '"\C-l": _bashou_clear' 2>/dev/null

# Erase the pet before a command runs, so it never scrolls with the output.
_bashou_ps0() {
  local seq
  [[ -n $BASHOU_PID ]] || return
  rm -f "$_bashou_room"                              # the pet waits for the next prompt's room
  _bashou_close_room && return
  [[ -r $_bashou_erase ]] || return
  IFS= read -rd '' seq < "$_bashou_erase"
  printf '%s' "$seq"
}

bashou() {
  case $1 in
    off)
      _bashou_guest=
      [[ -n $BASHOU_PID ]] || return 0
      _bashou_ps0
      kill "$BASHOU_PID" 2>/dev/null
      BASHOU_PID=
      ;;
    on)
      [[ -z $BASHOU_PID ]] || return 0
      _bashou_guest=
      _bashou_events=$_bashou_data/events.$$
      echo "$$" >| "$_bashou_home" 2>/dev/null       # guests' commands now come to this pet
      echo 0 > "$_bashou_room" 2>/dev/null           # this loader makes room: the pet waits for it
      # SIGUSR1 ignored until Python installs its handler (the default action would kill it).
      { (trap '' USR1; exec python3 "$BASHOU_DIR/launch.py" bashou.companion "$$") </dev/null 2>/dev/null & } 2>/dev/null
      BASHOU_PID=$!
      disown "$BASHOU_PID"
      ;;
    here)
      # Move the pet to this terminal. The old one sees it at its next prompt and becomes a guest.
      if [[ -n $BASHOU_PID ]]; then
        python3 "$BASHOU_DIR/launch.py" bashou here already
      else
        bashou on && python3 "$BASHOU_DIR/launch.py" bashou here moved
      fi
      ;;
    *) python3 "$BASHOU_DIR/launch.py" bashou "$@" ;;
  esac
}

# Tab completion. Static lists (no Python on Tab); tests/test_completion.py keeps them in sync.
_bashou_commands="help level pets achievements fight arena talk learn lesson project spot share evolve swap stats start config update version adventure reset on off here"
_bashou_pets="bat frog turtle mushroom slime sofa octopus dragon fox owl mole snake ghost spider ant axolotl gremlin snail beaver squirrel pigeon hedgehog bee whale meerkat leopard duck spark packet landscape chameleon"
_bashou_languages="en fr"
_bashou_dev="unlock-all stage stage-all level threat restore"
_bashou_challenges="line_moth column_crab jumble_sprite last_word_wisp flag_phantom typo_troll clutter_critter glob_goblin core_counter stderr_stalker space_sprite shebang_shade rename_rat pattern_pixie group_gremlin padlock_pest bloat_blob tar_tortoise unit_imp header_hound commit_crowd branch_bramble conflict_chimera first_line_imp needle_gnat field_wasp dust_bunny verse_viper peak_harpy grep_hydra awk_golem find_wraith uniq_swarm sed_serpent ps_phantom pipe_eel colon_cobra semicolon_slug list_leech dict_djinn loop_lich ouroboros json_jinn base64_banshee percent_poltergeist injection_imp token_trickster leak_lurker fencepost_fiend stack_specter overflow_ogre linker_lynx warning_wraith segfault_salamander breakpoint_beetle mut_marmot const_condor shadow_shade byte_basilisk version_vole candidate_crow stowaway_stoat autoremove_adder release_raven hitchhiker_hare census_centipede mirror_mimic repo_revenant enabled_ettin indent_imp stage_specter secret_sprite needs_newt manual_mole query_quokka table_troll insert_imp update_urchin join_jackal upsert_unicorn plaintext_pixie cipher_crow forger_ferret vault_vole cleartext_cricket negation_gnome coin_wraith loopback_lurker address_adder subnet_sprite route_raven resolver_rook six_serpent handshake_heron refused_revenant nxdomain_nixie established_ettin"
_bashou_security="1 2 3 4 5 6"
_bashou_projects="photos pdf budget backup logs pomodoro energy contacts todo netwatch menu papers"
_bashou_lessons="list command_line help computer paths files editor reading wildcards variables logic streams quotes grep regex pipes text_tools awk_sed find users permissions disk archives processes scripts substitution loops network git packages repos services compilation gcc_use stack_heap pointers debugger py_start py_flow py_names py_data rust_vars sql_select sql_write sql_join keys pass pipeline ip_addr ipv6 dns dns_tools tcp net_debug"

_bashou_complete() {
  local cur=${COMP_WORDS[COMP_CWORD]} words
  case "$COMP_CWORD:${COMP_WORDS[1]}:${COMP_WORDS[2]}" in
    1:*)              words=$_bashou_commands ;;
    2:swap:*)         words="starter $_bashou_pets" ;;
    2:config:*)       words="list bubble updates size talk quiet editor language skills" ;;
    2:update:*)       words="--version" ;;
    3:config:size)    words="small large default" ;;
    3:config:editor)  words="nano vi default" ;;
    2:arena:*)        words="fight security" ;;
    3:arena:security) words=$_bashou_security ;;
    2:lesson:*)       words=$_bashou_lessons ;;
    2:project:*)      words="start next hint back" ;;
    3:project:start)  words="python shell c rust" ;;
    4:project:start)  words=$_bashou_projects ;;
    3:config:bubble)  words="default" ;;
    3:config:talk)    words="off default" ;;
    3:config:quiet)   words="default" ;;
    3:config:updates) words="on off default" ;;
    3:config:language) words="$_bashou_languages" ;;
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
trap 'bashou off; _bashou_elsewhere || rm -f "$_bashou_home"' EXIT

# First time: choose a starter (builtins only to check, Python only for the picker).
_bashou_ready() {
  local s
  [[ -r $_bashou_data/state.json ]] && IFS= read -rd '' s < "$_bashou_data/state.json"
  [[ $s == *'"language": "'* ]] && [[ $s == *'"starter": "'* || $s == *'"cat"'* ]]
}
if _bashou_ready || bashou start; then
  if _bashou_claim; then
    bashou on                                        # the first prompt makes room for it
  else
    _bashou_guest=1                                  # the pet lives in another terminal
    _bashou_events=$_bashou_data/guest.$$
  fi
fi
