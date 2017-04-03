#!{{ dash }}
{{ browser }} --no-remote '{{ dumps(url) }}'
pid=$$
sleep {{ timeout }}
kill -SIGKILL $pid
