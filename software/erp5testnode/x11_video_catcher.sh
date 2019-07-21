#!/bin/sh
# scan running process and run ffmpeg
# for write video of xvfb session
ffmpeg_bin=$(find ~ -path */bin/ffmpeg -type f)
xvfb_bin=$(find ~ -path */bin/Xvfb -type f)
echo ${ffmpeg_bin}
echo ${xvfb_bin}
while true; do
  ps -u $(id -u) -o pid= | \
    while read pid; do
      display=""
      screen=""
      filename="output$pid.mpeg"
      test -d /proc/$pid || continue
      cat /proc/$pid/cmdline | tr '\0' ' ' | grep ^${xvfb_bin} > /dev/null 2> /dev/null || continue
      test -f ${filename} && continue
      for line in $(cat /proc/$pid/cmdline | tr '\0' '\n' 2> /dev/null); do
        if echo ${line} | grep -o ':[0-9]*' > /dev/null ; then
          display="${line}"
        fi
        if echo ${line} | grep -o '[0-9]*x[0-9]*x[0-9]*' > /dev/null ; then
          screen="${line%x*}"
        fi
      done
      echo $display $screen
      if [ -n "${display}" ] && [ -n "${screen}" ]; then
        export DISPLAY=${display}
        "${ffmpeg_bin}" -loglevel error -r 30 -s ${screen} -f x11grab -i ${display}.0 \
            -vcodec libx264 -preset ultrafast -tune zerolatency -maxrate 750k \
            -f mpegts ${filename} &
        ffmpeg_pid=$!
        sleep 5
        if ! test -f ${filename} ;then
          kill ${ffmpeg_pid}
          continue
        fi
        echo run ffmpeg $ffmpeg_pid

        while true; do
          if ! test -d /proc/$pid ; then
            echo kill ffmpeg $ffmpeg_pid
            kill $ffmpeg_pid
            exit
          fi
          sleep 1
        done &

      fi
    done
  sleep 1
done
