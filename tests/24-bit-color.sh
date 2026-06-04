#!/usr/bin/env bash
# Source: https://github.com/alacritty/alacritty/blob/master/scripts/24-bit-color.sh
#         (originally from iTerm2 https://github.com/gnachman/iTerm2/blob/master/tests/24-bit-color.sh)
# License: Apache 2.0
# Tests: 24-bit true color gradients (R, G, B ramps + HSV rainbow)

setBackgroundColor()
{
    printf '\x1b[48;2;%s;%s;%sm' $1 $2 $3
}

resetOutput()
{
    echo -en "\x1b[0m\n"
}

# Gives a color $1/255 % along HSV
rainbowColor()
{
    let h=$1/43
    let f=$1-43*$h
    let t=$f*255/43
    let q=255-t

    if [ $h -eq 0 ]; then
        echo "255 $t 0"
    elif [ $h -eq 1 ]; then
        echo "$q 255 0"
    elif [ $h -eq 2 ]; then
        echo "0 255 $t"
    elif [ $h -eq 3 ]; then
        echo "0 $q 255"
    elif [ $h -eq 4 ]; then
        echo "$t 0 255"
    elif [ $h -eq 5 ]; then
        echo "255 0 $q"
    else
        echo "0 0 0"
    fi
}

# Red ramp
for i in `seq 0 127`; do
    setBackgroundColor $i 0 0
    echo -en " "
done
resetOutput
for i in `seq 255 -1 128`; do
    setBackgroundColor $i 0 0
    echo -en " "
done
resetOutput

# Green ramp
for i in `seq 0 127`; do
    setBackgroundColor 0 $i 0
    echo -n " "
done
resetOutput
for i in `seq 255 -1 128`; do
    setBackgroundColor 0 $i 0
    echo -n " "
done
resetOutput

# Blue ramp
for i in `seq 0 127`; do
    setBackgroundColor 0 0 $i
    echo -n " "
done
resetOutput
for i in `seq 255 -1 128`; do
    setBackgroundColor 0 0 $i
    echo -n " "
done
resetOutput

# HSV rainbow
for i in `seq 0 127`; do
    setBackgroundColor `rainbowColor $i`
    echo -n " "
done
resetOutput
for i in `seq 255 -1 128`; do
    setBackgroundColor `rainbowColor $i`
    echo -n " "
done
resetOutput
