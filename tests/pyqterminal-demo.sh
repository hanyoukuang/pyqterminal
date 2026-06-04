#!/usr/bin/env bash
# pyqterminal ANSI art demo — showcases terminal rendering capabilities
# Usage: bash ~/pyqterminal-demo.sh
#   or:  bash ~/pyqterminal-demo.sh | pyqterminal --display

ESC=$'\x1b'
RESET="${ESC}[0m"
BOLD="${ESC}[1m"
DIM="${ESC}[2m"
ITALIC="${ESC}[3m"
UNDERLINE="${ESC}[4m"
BLINK="${ESC}[5m"
REVERSE="${ESC}[7m"
HIDDEN="${ESC}[8m"
STRIKE="${ESC}[9m"
DOUBLE_UL="${ESC}[21m"

# ── Clear & header ──
clear

# ── pyqterminal logo ──
C1="${ESC}[38;5;51m"   # cyan bright
C2="${ESC}[38;5;45m"   # cyan medium
C3="${ESC}[38;5;39m"   # cyan dark
C4="${ESC}[38;5;220m"  # gold
C5="${ESC}[38;5;214m"  # orange
C6="${ESC}[38;5;202m"  # red-orange
C7="${ESC}[38;5;82m"   # green
C8="${ESC}[38;5;213m"  # pink

# ASCII border (single-width on ALL terminals — no CJK ambiguity)
BORDER_W=106
TOP="${BOLD}${C1}+$(printf '=%.0s' $(seq 1 $BORDER_W))+${RESET}"
BOT="${BOLD}${C1}+$(printf '=%.0s' $(seq 1 $BORDER_W))+${RESET}"
EMPTY="${BOLD}${C1}|${RESET}$(printf ' %.0s' $(seq 1 $BORDER_W))${BOLD}${C1}|${RESET}"
SIDE="${BOLD}${C1}|${RESET}"

# Each logo line: concatenated halves (no split)
L1="${C1}${BOLD}█████╗ ${C4}██╗   ██╗ ${C5}██████╗ ${C7}████████╗${C8}███████╗${C2}██████╗ ${C3}███╗   ███╗${C6}██╗███╗   ██╗${C1}█████╗ ${C4}██╗${RESET}"
L2="${C1}${BOLD}██╔══██╗${C4}╚██╗ ██╔╝ ${C5}██╔══██╗${C7}╚══██╔══╝${C8}██╔════╝${C2}██╔══██╗${C3}████╗ ████║${C6}██║████╗  ██║${C1}██╔══██╗${C4}██║${RESET}"
L3="${C1}${BOLD}███████║${C4} ╚████╔╝  ${C5}██████╔╝${C7}   ██║   ${C8}█████╗  ${C2}██████╔╝${C3}██╔████╔██║${C6}██║██╔██╗ ██║${C1}███████║${C4}██║${RESET}"
L4="${C1}${BOLD}██╔══██║${C4}  ╚██╔╝   ${C5}██╔═══╝ ${C7}   ██║   ${C8}██╔══╝  ${C2}██╔══██╗${C3}██║╚██╔╝██║${C6}██║██║╚██╗██║${C1}██╔══██║${C4}╚██╗${RESET}"
L5="${C1}${BOLD}██║  ██║${C4}   ██║    ${C5}██║     ${C7}   ██║   ${C8}███████╗${C2}██║  ██║${C3}██║ ╚═╝ ██║${C6}██║██║ ╚████║${C1}██║  ██║${C4} ╚██╗${RESET}"
L6="${C1}${BOLD}╚═╝  ╚═╝${C4}   ╚═╝    ${C5}╚═╝     ${C7}   ╚═╝   ${C8}╚══════╝${C2}╚═╝  ╚═╝${C3}╚═╝     ╚═╝${C6}╚═╝╚═╝  ╚═══╝${C1}╚═╝  ╚═╝${C4}  ╚═╝${RESET}"

# Print centered: box width = | + BORDER_W spaces + | = BORDER_W + 2
BOX_COLS=$((BORDER_W + 2))
PAD=$(( ( $(tput cols 2>/dev/null || echo 120) - BOX_COLS ) / 2 ))
[[ $PAD -lt 0 ]] && PAD=0
PADSTR=$(printf "%${PAD}s" "")

echo
echo
echo
echo "${PADSTR}${TOP}"
echo "${PADSTR}${EMPTY}"
echo "${PADSTR}${SIDE}  ${L1}  ${SIDE}"
echo "${PADSTR}${SIDE}  ${L2}  ${SIDE}"
echo "${PADSTR}${SIDE}  ${L3}  ${SIDE}"
echo "${PADSTR}${SIDE}  ${L4}  ${SIDE}"
echo "${PADSTR}${SIDE}  ${L5}  ${SIDE}"
echo "${PADSTR}${SIDE}  ${L6}  ${SIDE}"
echo "${PADSTR}${EMPTY}"
echo "${PADSTR}${BOT}"
echo
echo
printf "%$((PAD + 41))s" ""
echo "${DIM}Python frontend · Rust backend${RESET}"
echo
echo
echo

# ── Feature indicators ──
GAP="    "

echo
echo
printf "%15s" ""
echo "${BOLD}${UNDERLINE}SGR Rendering${RESET}"

echo
printf "%15s" ""
echo -n "${BOLD}Bold${RESET}${GAP}"
echo -n "${DIM}Dim${RESET}${GAP}"
echo -n "${ITALIC}Italic${RESET}${GAP}"
echo -n "${UNDERLINE}Underline${RESET}${GAP}"
echo -n "${BLINK}Blink${RESET}${GAP}"
echo -n "${REVERSE} Reverse Video ${RESET}${GAP}"
echo -n "${STRIKE}Strikethrough${RESET}${GAP}"
echo    "${HIDDEN}(Hidden text)${RESET}"

echo
printf "%15s" ""
echo "${BOLD}${UNDERLINE}Underline Styles${RESET}"

echo
printf "%15s" ""
echo -n "${ESC}[4mStraight${RESET}${GAP}"
echo -n "${ESC}[4:1mSingle${RESET}${GAP}"
echo -n "${ESC}[4:2mDouble${RESET}${GAP}"
echo -n "${ESC}[4:3mCurly${RESET}${GAP}"
echo -n "${ESC}[4:4mDotted${RESET}${GAP}"
echo    "${ESC}[4:5mDashed${RESET}"

echo
printf "%15s" ""
echo "${BOLD}${UNDERLINE}True Color (24-bit)${RESET}"

echo
printf "%15s" ""
for i in 0 2 4 6 8 10 12 14 16 18 20 22 24; do
    r=$((255 - i * 10))
    g=$((i * 10))
    b=$((128))
    printf "${ESC}[38;2;%d;%d;%dm███${RESET}" $r $g $b
done
echo

echo
printf "%15s" ""
echo "${BOLD}${UNDERLINE}256 Color Palette${RESET}"

echo
printf "%15s" ""
for i in $(seq 0 15); do
    printf "${ESC}[48;5;%dm ${ESC}[38;5;%dm%3d${RESET} " $i $i $i
done
echo
printf "%15s" ""
for i in $(seq 16 51); do
    printf "${ESC}[48;5;%dm  ${RESET}" $i
done
echo

echo
printf "%15s" ""
echo "${BOLD}${UNDERLINE}Wide Characters (CJK)${RESET}"

echo
printf "%15s" ""
echo "English: The quick brown fox jumps over the lazy dog."
printf "%15s" ""
echo "日本語: 色は匂へど 散りぬるを 我が世誰ぞ 常ならむ"
printf "%15s" ""
echo "中文:  人生到处知何似 应似飞鸿踏雪泥 泥上偶然留指爪 鸿飞那复计东西"
printf "%15s" ""
echo "한국어: 동해물과 백두산이 마르고 닳도록 하느님이 보우하사 우리나라 만세"

echo
printf "%15s" ""
echo "${BOLD}${UNDERLINE}Nerd Font Icons${RESET}"

echo
printf "%15s" ""
echo "   git branch   master   commit   folder   code   terminal"
printf "%15s" ""
echo "   close   lightbulb   check   warning   attention   clock"
printf "%15s" ""
echo "   rust   node   python   docker   github"
printf "%15s" ""
echo "    >_ prompt   lightning   branch   modified   vim"

echo
printf "%15s" ""
echo "${BOLD}${UNDERLINE}Box Drawing${RESET}"

echo
printf "%15s" ""
echo "┌────┬────┐   ╔════╦════╗   ╭────┬────╮"
printf "%15s" ""
echo "│  ✓ │  ✗ │   ║ OK ║ NG ║   │  + │  - │"
printf "%15s" ""
echo "├────┼────┤   ╠════╬════╣   ├────┼────┤"
printf "%15s" ""
echo "│  A │  B │   ║  C ║  D ║   │  E │  F │"
printf "%15s" ""
echo "└────┴────┘   ╚════╩════╝   ╰────┴────╯"

echo
echo
printf "%15s" ""
echo "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
printf "%15s" ""
echo "${DIM}pyqterminal ${ESC}[38;5;51m0.1.1${RESET}${DIM} — Powered by Rust ${BOLD}vte${RESET}${DIM} + PySide6 QPainter${RESET}"
echo
echo
