#!/bin/bash
# usage: next.sh NN  (finish previous, launch NN)
sleep 5
pkill -f naver-whale; sleep 1
cd /workspace/whale/mint/out
for f in *.hwp.pdf *.hwpx.pdf; do [ -e "$f" ] && mv "$f" "${f%%.*}.pdf"; done
f=$(ls /workspace/whale/mint/in/$1.hwp* | head -1)
nohup /usr/bin/naver-whale --new-window --user-data-dir=/workspace/whale/profile file://$f >/dev/null 2>&1 &
sleep 58
ls /workspace/whale/mint/out | tr '\n' ' '
