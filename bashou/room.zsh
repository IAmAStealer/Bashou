# Room at the top of the screen, zsh's copy of room.bash (read that one for the why). Sourced by bashou.zsh
# and the zsh arena (fight.ZSH_RC), with _bashou_height, _bashou_room and _bashou_erase set before.
# Differences: keys typed ahead are found with zselect (zsh's `read -t 0` would eat a line), and files are
# written with >| (the player's NO_CLOBBER mustn't stop them).

zmodload zsh/zselect 2>/dev/null

_bashou_below() {
  local lines=7
  [[ -r $_bashou_height ]] && IFS= read -r lines < "$_bashou_height"
  printf '\e[%dB' "$lines"
}

_bashou_dsr=
_bashou_gap=0
_bashou_first=1
_bashou_where() {   # the cursor's row and column, and the screen's last row: "row col bottom"
  local row col bottom skip wait=2
  [[ $_bashou_dsr == off ]] && return 1
  zselect -t 0 -r 0 2>/dev/null && return 1          # keys typed ahead: asking would eat them
  [[ $_bashou_dsr == on ]] && wait=10
  printf '\e[6n\e7\e[9999;9999H\e[6n\e8' > /dev/tty
  if ! IFS='[;' read -rs -t $wait -d R skip row col < /dev/tty \
     || ! IFS='[;' read -rs -t $wait -d R skip bottom skip < /dev/tty \
     || [[ ! $row$col$bottom =~ '^[0-9]+$' ]]; then
    _bashou_dsr=off                                  # no answer: this terminal doesn't do it
    return 1
  fi
  _bashou_dsr=on
  _bashou_at="$row $col $bottom"
}

_bashou_hide() {    # no room this time: the pet isn't drawn, and nothing may blank its cells
  echo 0 >| "$_bashou_room"
  rm -f "$_bashou_erase"
}

_bashou_make_room() {
  local lines=7 row col bottom scroll nl=
  # An empty Enter runs no preexec: the last room is still there, the pet in it. Delete it first.
  (( _bashou_gap )) && [[ -e $_bashou_room ]] && _bashou_close_room
  _bashou_gap=0
  [[ -r $_bashou_height ]] && IFS= read -r lines < "$_bashou_height"
  if ! _bashou_where; then
    if [[ $_bashou_dsr == off ]]; then
      (( _bashou_first )) && _bashou_below           # as before: below the pet at the start,
      _bashou_first=0
      echo 1 >| "$_bashou_room"                      # and drawn over the text after that
    else
      _bashou_hide
    fi
    return
  fi
  _bashou_first=0
  read -r row col bottom <<< "$_bashou_at"
  if (( bottom < lines + 8 )); then                  # too short a screen to give the pet its rows
    _bashou_hide
    return
  fi
  # Keep 2 free rows under the prompt: Enter on a one-line command must not scroll the screen.
  scroll=$(( row + lines + 2 - bottom ))
  (( scroll < 0 )) && scroll=0
  (( scroll )) && nl=${(pl:scroll::\n:)}
  printf '\e[%d;1H%s\e[H\e[%dL\e[%d;%dH' "$bottom" "$nl" "$lines" $(( row - scroll + lines )) "$col" > /dev/tty
  _bashou_gap=$lines
  echo 1 >| "$_bashou_room"
}

# When a command starts (preexec): delete the empty top rows (the pet goes with them) and follow the
# command line up. Not if the screen scrolled. Fails when there was nothing to delete.
_bashou_close_room() {
  local row col bottom
  (( _bashou_gap )) && _bashou_where || return 1
  read -r row col bottom <<< "$_bashou_at"
  (( row < bottom && row > _bashou_gap )) || return 1
  printf '\e[H\e[%dM\e[%d;%dH' "$_bashou_gap" $(( row - _bashou_gap )) "$col" > /dev/tty
}
