
# Helper functions included by various */Build scripts.

function copy_and_check() {
  src="$1"
  dest="$2"
  perms="$3"
  if [[ ! -r "$src" ]]; then echo "copy_and_check source not found: $src"; exit 8; fi
  /bin/cp -Lpruv $src $dest
  if [[ -d "$src" ]]; then dest="$dest/$(basename $src)"; fi
  /usr/bin/diff -qr $src $dest || { echo "FAILED:  $src -> $dest; aborting."; exit 9; }
  if [[ "$perms" != "" ]]; then chmod -R $perms $dest; fi
  echo "OK: $src -> $dest"
}
