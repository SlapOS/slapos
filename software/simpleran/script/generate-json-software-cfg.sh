#!/bin/bash
DIR=$(dirname $(realpath $0))
cd $DIR/..

JSON_LIST="/tmp/json-list-$(date +%s)"

for f in $(find . -type f -name "*.json" | cut -c 3-) ; do
  python3 -c "import json ; f = open('$f', 'r') ; '\$schema' in json.load(f) and print('$f')"
done >> $JSON_LIST
ls -1 software*.cfg.json >> $JSON_LIST

gen() {
  echo "Add in $1"
  echo ; echo

  for f in $(cat $JSON_LIST | sort) ; do
    $2
  done

  echo ; echo
}

buildout() {
  cat <<- EOF
[$f]
filename = $f
md5sum = XXX
EOF
}

software_parts() {
  echo "  $f"
}

software_section() {
  cat <<- EOF
[$f]
<= download-json-base
EOF
}

gen buildout.hash.cfg buildout
gen "software.cfg parts+=" software_parts
gen "software.cfg" software_section

rm -f $JSON_LIST
