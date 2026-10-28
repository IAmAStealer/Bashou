# Bashou for zsh: a pet that lives in the top-right corner of your terminal and grows as you learn the shell.
# Load it from ~/.zshrc:  source ~/Bashou/bashou.zsh
# This is bashou.bash for zsh (0.9.0): the comments there explain the why, these say what differs.

[[ -o interactive && -t 1 ]] || return 0

# Everything below runs with zsh's own options, whatever the player's .zshrc set (ksharrays,
# noclobber…) and even when the package's profile.d sources it from `emulate sh`: functions defined
# under `emulate zsh -c` keep zsh's options each time they run.
if [[ -z $_bashou_sticky ]]; then
  _bashou_sticky=${(%):-%x}
  emulate zsh -c 'source "$_bashou_sticky"'
  unset _bashou_sticky
  return
fi

# A git copy hands over to the apt or dnf package once it's installed.
_bashou_pkg=${BASHOU_PACKAGE_LOADER:-/usr/share/bashou/bashou.zsh}
if [[ -z $BASHOU_KEEP_CLONE && -r $_bashou_pkg && ${_bashou_pkg:A} != ${_bashou_sticky:A} ]]; then
  _bashou_sticky=${_bashou_pkg:A}
  unset _bashou_pkg
  source "$_bashou_sticky"
  return
fi
unset _bashou_pkg

BASHOU_DIR=${_bashou_sticky:A:h}
[[ $BASHOU_DIR == */Cellar/bashou/*/libexec ]] && BASHOU_DIR=${BASHOU_DIR%/Cellar/bashou/*}/opt/bashou/libexec
_bashou_py=python3                                   # Homebrew runs its own python (libexec/python, a link)
[[ -x $BASHOU_DIR/python ]] && _bashou_py=$BASHOU_DIR/python
export BASHOU_SHELL=zsh                              # the arena and `bashou on` follow your shell
_bashou_data=${BASHOU_DATA:-$HOME/.local/share/bashou}
_bashou_events=$_bashou_data/events.$$
_bashou_erase=${BASHOU_CACHE:-$HOME/.cache/bashou}/erase.$$
_bashou_height=${BASHOU_CACHE:-$HOME/.cache/bashou}/height.$$
_bashou_room=${BASHOU_CACHE:-$HOME/.cache/bashou}/room.$$
_bashou_fight=${BASHOU_CACHE:-$HOME/.cache/bashou}/fight.$$
_bashou_home=${BASHOU_CACHE:-$HOME/.cache/bashou}/pet
_bashou_guest=
_bashou_off=$_bashou_data/off
(umask 077; mkdir -p "$_bashou_data" "${_bashou_erase%/*}"; : >> "$_bashou_events") 2>/dev/null
for _bashou_dir in "$_bashou_data" "${_bashou_erase%/*}"; do
  [[ ${_bashou_dir:t} == bashou && -O $_bashou_dir ]] && chmod 700 "$_bashou_dir" 2>/dev/null
done
unset _bashou_dir
_bashou_restarts=0
_bashou_cmd=

# The command line, as typed, before it runs (zsh calls no preexec for an empty line: not counted).
# Lines starting with a space stay private, like they stay out of the history.
_bashou_preexec() {
  [[ $1 == ' '* ]] && _bashou_cmd= || _bashou_cmd=$1
  _bashou_ps0
}

# Each prompt: log the last command as "status<TAB>    1  command", the layout of bash's `history 1`
# that analyze.parse_log reads.
_bashou_precmd() {
  local st=$? cmd=$_bashou_cmd
  _bashou_cmd=
  if [[ -n $_bashou_guest && ( -z $_bashou_auto || ! -e $_bashou_off ) ]] && ! _bashou_elsewhere && _bashou_claim; then
    _bashou_on
  fi
  if [[ -n $BASHOU_PID ]] && _bashou_elsewhere; then
    kill "$BASHOU_PID" 2>/dev/null
    BASHOU_PID=
    _bashou_guest=1
    _bashou_events=$_bashou_data/guest.$$
  fi
  if [[ -n $BASHOU_PID && -e $_bashou_fight ]]; then
    rm -f "$_bashou_fight"
    "$_bashou_py" "$BASHOU_DIR/launch.py" bashou.fight badger
  fi
  if [[ -n $BASHOU_PID ]]; then
    _bashou_make_room
  fi
  [[ -n $BASHOU_PID && $_bashou_dsr == off && ${cmd%% *} == (clear|reset) ]] && _bashou_below
  if [[ ( -n $BASHOU_PID || -n $_bashou_guest ) && -n $cmd ]]; then
    printf '%s\t    1  %s\n' "$st" "$cmd" >> "$_bashou_events"
  fi
  if [[ -n $BASHOU_PID ]] && ! kill -USR1 "$BASHOU_PID" 2>/dev/null && (( _bashou_restarts++ < 3 )); then
    BASHOU_PID=
    _bashou_on
  fi
  # compinit may come after this file in ~/.zshrc: complete `bashou` as soon as it's there.
  if [[ -z $_bashou_completes ]] && (( $+functions[compdef] )); then
    compdef _bashou bashou
    _bashou_completes=1
  fi
  return $st
}

_bashou_elsewhere() {
  local pid
  [[ -r $_bashou_home ]] && IFS= read -r pid < "$_bashou_home"
  [[ -n $pid && $pid != $$ ]] && kill -0 "$pid" 2>/dev/null
}

# Take the pet's home for this shell, unless another shell took it first (noclobber makes it atomic).
_bashou_claim() {
  setopt local_options no_clobber
  { echo $$ > "$_bashou_home" } 2>/dev/null ||
    { ! _bashou_elsewhere && rm -f "$_bashou_home" && { echo $$ > "$_bashou_home" } 2>/dev/null }
}

source "$BASHOU_DIR/bashou/room.zsh"

# Ctrl+L: clear like zle does, then start below the pet (not in a guest terminal: no pet there).
_bashou_clear() {
  printf '\e[H\e[2J'
  [[ -n $BASHOU_PID ]] && _bashou_below
  zle reset-prompt
}
zle -N _bashou_clear
for _bashou_map in emacs viins vicmd; do
  bindkey -M $_bashou_map '^L' _bashou_clear
done
unset _bashou_map

# Erase the pet before a command runs, so it never scrolls with the output.
_bashou_ps0() {
  local seq
  [[ -n $BASHOU_PID ]] || return
  rm -f "$_bashou_room"
  _bashou_close_room && return
  [[ -r $_bashou_erase ]] || return
  seq=$(<"$_bashou_erase")
  printf '%s' "$seq"
}

_bashou_off() {
  _bashou_guest=
  [[ -n $BASHOU_PID ]] || return 0
  _bashou_ps0
  kill "$BASHOU_PID" 2>/dev/null
  BASHOU_PID=
}

_bashou_on() {
  [[ -z $BASHOU_PID ]] || return 0
  _bashou_guest=
  _bashou_events=$_bashou_data/events.$$
  echo $$ >| "$_bashou_home" 2>/dev/null
  echo 0 >| "$_bashou_room" 2>/dev/null
  # Its own process group (Ctrl+C mustn't reach it), no job message, SIGUSR1 ignored until Python handles it.
  setopt local_options no_notify
  { (trap '' USR1; exec "$_bashou_py" "$BASHOU_DIR/launch.py" bashou.companion $$) </dev/null 2>/dev/null &! } 2>/dev/null
  BASHOU_PID=$!
}

bashou() {
  case $1 in
    off)
      _bashou_off
      if [[ -n $_bashou_auto && ! -e $_bashou_off ]] && : >| "$_bashou_off" 2>/dev/null; then
        "$_bashou_py" "$BASHOU_DIR/launch.py" bashou off saved
      else
        "$_bashou_py" "$BASHOU_DIR/launch.py" bashou off hidden
      fi
      ;;
    on)
      # Always say what happened (owner: `bashou on` didn't reply when the pet was already there).
      rm -f "$_bashou_off"
      if [[ -n $BASHOU_PID ]]; then
        "$_bashou_py" "$BASHOU_DIR/launch.py" bashou on already
      elif [[ -n $_bashou_guest ]] && _bashou_elsewhere; then
        "$_bashou_py" "$BASHOU_DIR/launch.py" bashou on guest
      else
        _bashou_ready || bashou start || return 1
        _bashou_on
        "$_bashou_py" "$BASHOU_DIR/launch.py" bashou on back
      fi
      ;;
    here)
      if [[ -n $BASHOU_PID ]]; then
        "$_bashou_py" "$BASHOU_DIR/launch.py" bashou here already
      else
        rm -f "$_bashou_off"
        { _bashou_ready || bashou start; } && _bashou_on && "$_bashou_py" "$BASHOU_DIR/launch.py" bashou here moved
      fi
      ;;
    *) "$_bashou_py" "$BASHOU_DIR/launch.py" bashou "$@" ;;
  esac
}

# Tab completion: the same static lists as bashou.bash (tests/test_completion.py keeps them equal).
_bashou_commands="help level pets achievements fight arena talk learn lesson project spot share evolve swap stats start config update version changelog export import adventure reset on off here"
_bashou_pets="bat frog turtle mushroom slime sofa octopus dragon fox owl mole snake ghost spider ant axolotl gremlin snail beaver squirrel pigeon hedgehog bee whale meerkat leopard duck spark packet landscape chameleon seal"
_bashou_languages="en fr"
_bashou_dev="unlock-all stage stage-all level threat restore"
_bashou_challenges="line_moth column_crab jumble_sprite last_word_wisp flag_phantom typo_troll clutter_critter glob_goblin core_counter stderr_stalker space_sprite shebang_shade rename_rat pattern_pixie group_gremlin padlock_pest bloat_blob tar_tortoise unit_imp header_hound commit_crowd branch_bramble conflict_chimera revert_revenant first_line_imp needle_gnat field_wasp dust_bunny verse_viper peak_harpy grep_hydra awk_golem find_wraith uniq_swarm sed_serpent ps_phantom pipe_eel colon_cobra semicolon_slug list_leech dict_djinn except_eel loop_lich ouroboros json_jinn base64_banshee percent_poltergeist injection_imp token_trickster leak_lurker fencepost_fiend stack_specter overflow_ogre linker_lynx warning_wraith segfault_salamander breakpoint_beetle mut_marmot const_condor shadow_shade byte_basilisk borrow_badger vector_viper version_vole candidate_crow stowaway_stoat autoremove_adder release_raven hitchhiker_hare census_centipede mirror_mimic repo_revenant enabled_ettin indent_imp stage_specter secret_sprite needs_newt manual_mole query_quokka table_troll insert_imp update_urchin null_newt join_jackal upsert_unicorn plaintext_pixie cipher_crow forger_ferret vault_vole cleartext_cricket negation_gnome coin_wraith loopback_lurker address_adder subnet_sprite route_raven resolver_rook six_serpent handshake_heron refused_revenant nxdomain_nixie established_ettin key_kraken drop_dragon index_imp dash_demon nomatch_nymph newline_nixie stdin_siren masked_mole errexit_eel echo_echidna trap_troll expiry_elk san_salamander key_kobold chain_chameleon insecure_iguana request_raccoon pathlen_panther impostor_ibex config_cobra revoked_reindeer"
_bashou_security="1 2 3 4 5 6"
_bashou_projects="photos pdf budget backup logs pomodoro energy contacts todo netwatch menu papers"
_bashou_lessons="list command_line help computer paths files editor reading wildcards variables bash_zsh logic streams quotes grep regex pipes text_tools awk_sed find users permissions disk archives processes scripts substitution loops prompt_script script_errors script_files script_data script_cleanup network git packages repos services compilation gcc_use stack_heap pointers debugger py_start py_flow py_errors py_names py_data rust_vars rust_own sql_select sql_write sql_null sql_join keys pass pipeline ip_addr ipv6 dns dns_tools tcp ssh firewall net_debug certs certs_tools certs_admin certs_ca certs_cnf certs_revoke ai_context ai_plan"

# The words that can come next: $@ is the command line up to the cursor (the last word is being typed).
# Sets reply to the candidates starting with it, in the lists' order.
_bashou_words() {
  local cword=$(( $# - 1 )) cur=${@[-1]} words
  case "$cword:$2:$3" in
    1:*)              words=$_bashou_commands ;;
    2:swap:*)         words="starter $_bashou_pets" ;;
    2:config:*)       words="list bubble updates size talk quiet editor os language skills" ;;
    2:update:*)       words="--version" ;;
    2:export:*)       words="--full" ;;
    3:config:size)    words="small large default" ;;
    3:config:editor)  words="nano vi default" ;;
    3:config:os)      words="linux macos both default" ;;
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
  reply=( ${(M)${=words}:#${~${(b)cur}}*} )
}
_bashou_words_end=   # tests/test_completion.py reads the lists and _bashou_words up to this line

_bashou() {
  local -a reply
  _bashou_words "${(@)words[1,CURRENT]}"
  compadd -a reply
}

# Without compinit (a bare ~/.zshrc, like the one zsh writes at first start), zsh's older completion,
# compctl, still works: it asks this function for the words, zsh keeps those that fit what's typed.
_bashou_compctl() {
  local -a args
  local n
  read -cA args
  read -cn n
  (( n > $#args )) && args+=("")
  _bashou_words "${(@)args[1,n]}"
}
compctl -K _bashou_compctl bashou

precmd_functions=(_bashou_precmd ${precmd_functions:#_bashou_precmd})
preexec_functions=(_bashou_preexec ${preexec_functions:#_bashou_preexec})
_bashou_exit() {
  _bashou_dsr=${_bashou_dsr/on}
  _bashou_off
  _bashou_elsewhere || rm -f "$_bashou_home"
}
zshexit_functions=(${zshexit_functions:#_bashou_exit} _bashou_exit)

_bashou_ready() {
  local s
  [[ -r $_bashou_data/state.json ]] && s=$(<"$_bashou_data/state.json")
  [[ $s == *'"language": "'* ]] && [[ $s == *'"starter": "'* || $s == *'"cat"'* ]]
}
if _bashou_ready || BASHOU_AUTO=$_bashou_auto bashou start; then
  # bash gets its line in ~/.bashrc too, once.
  [[ -e $_bashou_data/setup.bash ]] || (( ! $+commands[bash] )) || "$_bashou_py" "$BASHOU_DIR/launch.py" bashou on bash
  if _bashou_claim; then
    _bashou_on
  else
    _bashou_guest=1
    _bashou_events=$_bashou_data/guest.$$
  fi
elif [[ -n $_bashou_auto && -t 0 ]]; then
  : >| "$_bashou_off" 2>/dev/null
fi
