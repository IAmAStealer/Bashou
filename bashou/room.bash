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
  [[ $lines =~ ^[0-9]+$ ]] || lines=7                  # a number, or printf %d prints an error
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
  local rc
  [[ $_bashou_dsr == off ]] && return 1
  # The whole exchange without canonical mode or echo: a half-typed line then counts as keys waiting
  # (a Mac hides it until Enter, and the second read ate it), and nothing is printed between the reads.
  _bashou_raw=1
  stty -icanon -echo 2>/dev/null < /dev/tty
  _bashou_ask
  rc=$?
  stty icanon echo 2>/dev/null < /dev/tty
  _bashou_raw=
  return "$rc"
}

_bashou_raw=
_bashou_tty_back() {  # Ctrl+C during the questions skipped the stty above: the command would run without echo
  [[ -n $_bashou_raw ]] && stty icanon echo 2>/dev/null < /dev/tty
  _bashou_raw=
}

_bashou_ask() {
  local row col bottom wait=2
  read -t 0 && return 1                              # keys typed ahead: asking would eat them
  # A terminal that answered once will answer again, only late when busy (WSL after a long output):
  # wait for it, or the answer comes after we stopped reading and shows up on the screen (^[[30;120R).
  [[ $_bashou_dsr == on ]] && wait=10
  printf '\e[6n' > /dev/tty                           # one question at a time
  if ! IFS='[;' read -rs -t "$wait" -dR _ row col; then
    _bashou_dsr=off                                  # no answer: this terminal doesn't do it
    return 1
  fi
  read -t 0 && return 1                              # keys typed meanwhile: the second read would eat them
  # (keys typed while the second answer is on its way are still lost: the window is short)
  if ! printf '\e7\e[9999;9999H\e[6n\e8' > /dev/tty || ! IFS='[;' read -rs -t "$wait" -dR _ bottom _ \
     || [[ ! $row$col$bottom =~ ^[0-9]+$ ]]; then
    _bashou_dsr=off
    return 1
  fi
  _bashou_dsr=on
  _bashou_at="$row $col $bottom"
}

_bashou_hide() {    # no room this time: the pet isn't drawn, and nothing may blank its cells
  { echo 0 > "$_bashou_room"; } 2>/dev/null
  rm -f "$_bashou_erase"
}

_bashou_make_room() {
  local lines=7 row col bottom scroll asked='' used='' nl=''
  [[ -r $_bashou_height ]] && IFS= read -r lines < "$_bashou_height"
  [[ $lines =~ ^[0-9]+$ ]] || lines=7                  # a number: (( )) below would run anything else as code
  # An empty Enter runs no PS0 (bash shows it only before a command): the last room is still there,
  # the pet in it. Same size, with its 2 free rows under the prompt: keep it (made again, the whole
  # screen moved up and back down at each Enter: owner, it flickered). Else delete it first, or the new
  # blank rows push it down and it's drawn again above; in one frame with the new room (synchronized
  # output: terminals that don't know it ignore it).
  if (( _bashou_gap )) && [[ -e $_bashou_room ]] && _bashou_where; then
    asked=1
    read -r row col bottom <<< "$_bashou_at"
    IFS= read -r used < "$_bashou_room"                # 0: the pet waits for a new room (`bashou on`)
    [[ $used == 1 ]] && (( lines == _bashou_gap && row + 2 <= bottom )) && return
    printf '\e[?2026h' > /dev/tty
    _bashou_close_room asked
  fi
  _bashou_gap=0
  if [[ -z $asked ]] && ! _bashou_where; then
    if [[ $_bashou_dsr == off ]]; then
      (( _bashou_first )) && _bashou_below           # as before: below the pet at the start,
      _bashou_first=0
      { echo 1 > "$_bashou_room"; } 2>/dev/null       # and drawn over the text after that
    else
      _bashou_hide
    fi
    return
  fi
  _bashou_first=0
  read -r row col bottom <<< "$_bashou_at"
  if (( bottom < lines + 8 )); then                  # too short a screen to give the pet its rows
    _bashou_hide
    printf '\e[?2026l' > /dev/tty
    return
  fi
  # Keep 2 free rows under the prompt: Enter on a one-line command must not scroll the screen.
  scroll=$(( row + lines + 2 - bottom ))
  (( scroll < 0 )) && scroll=0
  (( scroll )) && printf -v nl '%*s' "$scroll" '' && nl=${nl// /$'\n'}
  printf '\e[%d;1H%s\e[H\e[%dL\e[%d;%dH\e[?2026l' "$bottom" "$nl" "$lines" $(( row - scroll + lines )) "$col" > /dev/tty
  _bashou_gap=$lines
  { echo 1 > "$_bashou_room"; } 2>/dev/null
}

# When a command starts (PS0): the command line sits under the empty top rows. Delete them (the pet
# goes with them) and follow it up. Not if the screen scrolled (a long command reached the last row):
# the top rows moved. Fails when there was nothing to delete. `asked`: _bashou_at is fresh, don't ask
# again; it then tells where the cursor went.
_bashou_close_room() {
  local row col bottom
  (( _bashou_gap )) || return 1
  [[ ${1-} == asked ]] || _bashou_where || return 1
  read -r row col bottom <<< "$_bashou_at"
  (( row < bottom && row > _bashou_gap )) || return 1
  printf '\e[H\e[%dM\e[%d;%dH' "$_bashou_gap" $(( row - _bashou_gap )) "$col" > /dev/tty
  _bashou_at="$(( row - _bashou_gap )) $col $bottom"
}
