#!/usr/bin/env bash
# Source: https://github.com/alacritty/alacritty/blob/master/scripts/colors.sh
# License: Apache 2.0
# Tests: all SGR attribute combinations (0-8) × all 8 foregrounds × all 8 backgrounds

for x in {0..8}; do
    for i in {30..37}; do
        for a in {40..47}; do
            echo -ne "\e[$x;$i;$a""m\\\e[$x;$i;$a""m\e[0;37;40m "
        done
        echo
    done
done
echo ""
