# shellcheck shell=bash
# shellcheck disable=SC2154  # the file paths are set by whoever sources this
# Room at the top of the screen for what Bashou draws there: the pet in your shell (bashou.bash), the
# fight panel in the arena (bashou/fight.py). Set before sourcing: _bashou_height (file: rows to empty),
# _bashou_room (file: 1 when they are empty, 0 when nothing may be drawn), _bashou_erase (file: how to
# erase the drawing).

# The pet is drawn over the top lines of the screen: move the prompt down past it, or the first
# commands' output would hide under the pet. Cursor down doesn't scroll: on a full screen it does
# nothing. (Asking the terminal where the cursor is could swallow keys typed at that moment.)
_bashou_below() {
  local lines=7
  [[ -r $_bashou_height ]] && IFS= read -r lines < "$_bashou_height"
  printf '\e[%dB' "$lines"
}

# The pet and its bubble are drawn over the top rows of the screen. Drawn over text, they hid it, and
# PS0 then blanked those cells: lines were lost for good (owner: `--help` output with holes when
# scrolling up). So before each prompt the top rows are made empty: the lines there go up into the
# scrollback untouched (the screen scrolls), and blank rows are inserted at the top. The rest of the
# screen doesn't move. When a command starts, PS0 deletes these blank rows again, so the scrollback
# never collects them. The terminal tells where the cursor is (ESC[6n); that answer comes on the
# input, so we never ask while keys are waiting there: they would be eaten. Then the pet stays hidden.
_bashou_dsr=
_bashou_gap=0
_bashou_first=1
_bashou_where() {   # the cursor's row and column, and the screen's last row: "row col bottom"
  local row col bottom
  [[ $_bashou_dsr == off ]] && return 1
  read -t 0 && return 1                              # keys typed ahead: asking would eat them
  printf '\e[6n\e7\e[9999;9999H\e[6n\e8' > /dev/tty
  if ! IFS='[;' read -rs -t 2 -dR _ row col || ! IFS='[;' read -rs -t 2 -dR _ bottom _ \
     || [[ ! $row$col$bottom =~ ^[0-9]+$ ]]; then
    _bashou_dsr=off                                  # no answer: this terminal doesn't do it
    return 1
  fi
  _bashou_at="$row $col $bottom"
}

_bashou_hide() {    # no room this time: the pet isn't drawn, and nothing may blank its cells
  echo 0 > "$_bashou_room"
  rm -f "$_bashou_erase"
}

_bashou_make_room() {
  local lines=7 row col bottom scroll nl=
  _bashou_gap=0
  [[ -r $_bashou_height ]] && IFS= read -r lines < "$_bashou_height"
  if ! _bashou_where; then
    if [[ $_bashou_dsr == off ]]; then
      (( _bashou_first )) && _bashou_below           # as before: below the pet at the start,
      _bashou_first=0
      echo 1 > "$_bashou_room"                       # and drawn over the text after that
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
  (( scroll )) && printf -v nl '%*s' "$scroll" '' && nl=${nl// /$'\n'}
  printf '\e[%d;1H%s\e[H\e[%dL\e[%d;%dH' "$bottom" "$nl" "$lines" $(( row - scroll + lines )) "$col" > /dev/tty
  _bashou_gap=$lines
  echo 1 > "$_bashou_room"
}

# When a command starts (PS0): the command line sits under the empty top rows. Delete them (the pet
# goes with them) and follow it up. Not if the screen scrolled (a long command reached the last row):
# the top rows moved. Fails when there was nothing to delete.
_bashou_close_room() {
  local row col bottom
  (( _bashou_gap )) && _bashou_where || return 1
  read -r row col bottom <<< "$_bashou_at"
  (( row < bottom && row > _bashou_gap )) || return 1
  printf '\e[H\e[%dM\e[%d;%dH' "$_bashou_gap" $(( row - _bashou_gap )) "$col" > /dev/tty
}
