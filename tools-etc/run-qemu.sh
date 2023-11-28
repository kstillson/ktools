#!/bin/bash

: 'qemu virtual machine launcher

$1 can be any of:
  a full pathname of an img to mount
  a filename in $DEFAULT_DIR (defined below or passed in)
  a partial filename in $DEFAULT_DIR, multiple matches resolved interactively
  a directory name, where *.img will be interactively selected
  "-" to skip auto-creating params wrt image to launch
  "+" to create a new image in $DEFAULT_DIR
  not provided, which will interactively select from *.img in $DEFAULT_DIR

$2 can be "-" to skip the editing phase (see below).

This launcher will create a script contining a best-effort qemu launch command
line, and then pass it to $EDITOR for customization tweaking.  The generated
script has a bunch of advice on various alternatives.

Once editing is complete, the generated+edited script is launched.
To abort that launch, delete all the contents when in the editor.

Once qmeu exits, this script will ask what you want to do with the generated
script, e.g. delete it, refine it, or save it as a new script in the same
directory as this script.
'

# ---------- control constants (can be overriden by incoming environment)

DEFAULT_DIR="${DEFAULT_DIR:-/mnt/data/qemu}"   # default location of qemu image files
SCRIPT_DIR=${SCRIPT_DIR:-$(dirname $0)}        # location for saved scripts


# ---------- select image

img="$1"
shift

if [[ "$1" == "-" ]]; then skipedit="1"; shift; else skipedit="0"; fi

if   [[ -f "$img" ]]; then      echo "using image: $img"
elif [[ "$img" == "-" ]]; then  echo "skipping image."
elif [[ -f "${DEFAULT_DIR}/$img" ]]; then
    img="${DEFAULT_DIR}/$img";  echo "using image: $img"
elif [[ -d "$img" ]]; then
    select tmp in ${img}/*.qcow2; do img=$tmp; break; done
elif [[ "$img" == "+" ]]; then
    read -p "name for new image: " img
    if [[ "$img" == "" ]]; then echo "aborted"; exit 3; fi
    if [[ ! "$img" == "/"* ]]; then img="${DEFAULT_DIR}/$img"; fi
    read -p "type (default qcow2): " type
    if [[ "$type" == "" ]]; then type="qcow2"; fi
    read -p "size (default 8G): " size
    if [[ "$size" == "" ]]; then size="8G"; fi
    if [[ ! "$img" == *"."* ]]; then img="${img}.${type}"; fi
    echo "qemu-img create $img -f $type $size"
    qemu-img create $img -f $type $size
    if [[ "$?" != "0" ]]; then echo "that didn't seem to work :-("; exit 4; fi    
elif [[ -d $DEFAULT_DIR ]]; then
    export COLUMNS=1
    imgs=$(ls -1 ${DEFAULT_DIR}/*${img}*.qcow2 | fgrep -v baseline)
    select tmp in $imgs; do img=$tmp; break; done
fi

if [[ -f "$img" ]]; then
    image="-drive file=${img}"
elif [[ "$img" == "-" ]]; then
    image=""
else
    echo "dont know which disk image to use. give me a hint as first param or '-' to skip"
    exit 2
fi


# ---------- construct proposed cli

tmpfile=$(mktemp /tmp/run-qemu-XXXXXXXXX)
cat >$tmpfile <<EOF
#!/bin/bash

qemu-system-x86_64 ${image} $@ \\
  -boot menu=on \\
  -cpu host \\
  -enable-kvm \\
  -m 8192 \\
  -machine type=q35,accel=kvm \\
  -name qemu1 \\
  -net user,hostfwd=tcp::2223-:22 -net nic \\
  -smp 4,sockets=1,cores=1,threads=4 \\
  -virtfs local,path=/home/ken/tmp/9p,mount_tag=tag1,security_model=none,multidevs=remap 

# Some other common possibilities:
# -bios /usr/share/ovmf/OVMF.fd \\                                               # UEFI
# -cdrom /home/ken/mnt/share/sw/bootable/{}.iso \\                               # bootable ISO
# -net nic,model=virtio,macaddr=52:54:00:00:00:01 -net bridge,br=virtbr0 \\      # bridged net IF
# -usb -usbdevice disk:/dev/... \\                                               # USB passthrough
# -drive file={}.img,if=none,id=flashdisk -device usb-storage,drive=flashdisk \\ # USB imagefile
# -vga virtio -display gtk,gl=on \\

# To establish a bridge network:
#  brctl addbr virtbr0; brctl addif virtbr0 enp5s0; ip addr add 192.168.0.20/24 dev virtbr0;
#    ip link set virtbr0 up; iptables -I FORWARD -m physdev --physdev-is-bridged -j ACCEPT
#  (perm problems?  check /etc/qemu/bridge.conf for "allow virtbr0",
#                     and chmod u+s /usr/lib/qemu/qemu-bridge-helper)

EOF

# ---------- edit conf file

LOOP=1
while [[ "$LOOP" == "1" ]]; do

LOOP=0

if [[ "$skipedit" != "1" ]]; then
    ${EDITOR} $tmpfile
    if [[ "$?" != "0" ]]; then echo "edit failed; leaving tmpfile in place: $tmpfile"; exit 1; fi
    if [[ ! -s "$tmpfile" ]]; then echo "aborted."; rm "$tmpfile"; exit 2; fi
fi

# ---------- launch conf file

cat <<EOF

To mount shared dir from inside Linux, use:
modprobe 9pnet_virtio; mount -t 9p -o trans=virtio tag1 /mnt

launching...

EOF

. $tmpfile
status=$?

# ---------- cleanup

echo "qemu exit status: $status"
echo ""
echo "what to do with the launch script? "
read -p "(e) to edit again, (x) to delete, or a name for ${SCRIPT_DIR}:" sel
echo ""

if [[ "$sel" == "e" ]]; then
    LOOP=1
    echo "trying again..."

elif [[ "$sel" == "x" ]]; then
    echo "rm $tmpfile"
    rm $tmpfile

elif [[ "$sel" == "" ]]; then
    echo "leaving launch script in place: $tmpfile"

else
    dest="${SCRIPT_DIR}/${sel}"
    mv "$tmpfile" "$dest"
    chmod +x "$dest"
    echo "created: $dest"
fi

done   # see LOOP

if [[ "$status" == "0" ]]; then echo "ok bye"
else echo "exiting with qemu exit status (${status})..."
fi
exit $status
