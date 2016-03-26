#!/bin/bash

cp -r /mnt/input/* /mnt/output/

if [ $# -gt 0 ]; then
    echo "$1" > /mnt/status/status.txt
fi