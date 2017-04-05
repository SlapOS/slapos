#!{{ dash }}
{{ browser }} '{{ url }}' &
pid=$!
sleep {{ timeout }}
kill -15 $pid
