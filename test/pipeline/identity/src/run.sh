#!/bin/bash

if [ "`ls /mnt/input/ | wc -l`" = 0 ]; then
    echo "no input files!"
else
    cp -r /mnt/input/* /mnt/output/
fi

if [ $# -gt 0 ]; then
    echo "$1" > /mnt/status/status.txt
fi