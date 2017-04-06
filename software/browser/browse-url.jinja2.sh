#!{{ dash }}
{{ browser }} '{{ url }}' &
pid=$!
sleep {{ timeout }}
kill $pid
