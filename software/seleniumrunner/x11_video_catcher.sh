#!/bin/sh
# scan running process and run ffmpeg
# for write video of xvfb session
while true; do
  while ! [ -f "${ffmpeg_bin}" ] ; do
    ffmpeg_bin=$(find ~ -path */bin/ffmpeg -type f)
    echo ${ffmpeg_bin}
    [ -f "${ffmpeg_bin}" ] && break
    sleep 10
  done
  ps -u $(id -u) -o pid= | \
    while read pid; do
      display=""
      resolution=""
      test -d /proc/$pid || continue
      cat /proc/$pid/cmdline | tr '\0' '\n' | head -n1 | grep /bin/Xvfb\$ > /dev/null 2> /dev/null || continue
      for line in $(cat /proc/$pid/cmdline | tr '\0' '\n' 2> /dev/null); do
        if echo ${line} | grep -o ':[0-9]*' > /dev/null ; then
          display="${line}"
        fi
        if echo ${line} | grep -o '[0-9]*x[0-9]*x[0-9]*' > /dev/null ; then
          resolution="${line%x*}"
        fi
      done
      if [ -n "${display}" ] && [ -n "${resolution}" ]; then
        firefox_pid=""
        for f_pid in $(ps -u $(id -u) -o pid=); do
          test -d /proc/${f_pid} || continue
          cat /proc/${f_pid}/cmdline | tr '\0' '\n' | head -n1 | grep ./firefox\$ > /dev/null 2> /dev/null || continue
          cat /proc/${f_pid}/environ | tr '\0' '\n' | grep ^DISPLAY=${display}\$ > /dev/null 2> /dev/null || continue
          firefox_pid="$f_pid"
          break;
        done
        if [ -z "${firefox_pid}" ]; then
          continue
        fi
        filename="output${firefox_pid}.webm"
        test -f ${filename} && continue
        echo "xvfb ${pid} ${display} ${resolution}"
        echo "firefox ${firefox_pid}"
        export DISPLAY=${display}
        "${ffmpeg_bin}" -loglevel error -r 30 -s ${resolution} -f x11grab -i ${display}.0 \
            -vf unpremultiply=inplace=1 \
            -c:v libvpx-vp9 -lossless 1 \
            -f webm ${filename} &
        ffmpeg_pid=$!
        sleep 5
        if ! test -f ${filename} ;then
          kill ${ffmpeg_pid}
          continue
        fi
        echo run ffmpeg ${ffmpeg_pid}

        while true; do
          if ! [ -d "/proc/${firefox_pid}" ]; then
            echo "kill ffmpeg $ffmpeg_pid"
            kill ${ffmpeg_pid}
            exit
          fi
          sleep 0.2
        done &

      fi
    done
  sleep 1
done
