#!/bin/bash
# usage: mine.sh mNN
pkill -f 'user-data-dir=/workspace/whale/profile_m' ; sleep 1
cd /workspace/whale/mint2/out
for f in *.hwp.pdf *.hwpx.pdf; do [ -e "$f" ] && mv "$f" "${f%%.*}.pdf"; done
f=$(ls /workspace/whale/mint2/in/$1.hwp* | head -1)
nohup /usr/bin/naver-whale --new-window --user-data-dir=/workspace/whale/profile_m file://$f >/dev/null 2>&1 &
sleep 26
ls /workspace/whale/mint2/out | tail -2 | tr '\n' ' '
