while true; do DEV=$(ioreg -p IOUSB -w0 | sed 's/[^o]*o //; s/@.*$//' | grep -v '^Root.*'); echo $DEV > usb.txt; sleep 1; done
