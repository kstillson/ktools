#!/bin/bash

refdir="$(echo $1)"
shift

subst="$1"
shift

if [[ $# == 0 ]]; then exit 0; fi

ok_count=0
tmp=$(mktemp)
for f in "$@"; do
    if [[ "$subst" != "" ]]; then f=$(echo "$f" | sed -e "$subst"); fi
    diff -sq "${refdir}/$f" "$f" >&/dev/null
    if [[ "$?" == 0 ]]; then
	ok_count=$((ok_count+1))
    else
	out="${refdir}/$f"
	if [[ ! -f "$out" ]]; then out="$out		( missing )"; fi
	echo "$out" >> $tmp
    fi
done

ref_plus=$(dirname $f)
if [[ "$ref_plus" != "." ]]; then
    refdir="${refdir}/${ref_plus}"
fi


if [[ -s $tmp ]]; then
  echo "${refdir}: ${ok_count} matched;  $(wc -l $tmp | cut -f1 -d' ') mismatches:"
  sed -e 's/^/	/' < $tmp
else
  echo "${refdir}: ${ok_count} matched"
fi

rm $tmp
exit 0

