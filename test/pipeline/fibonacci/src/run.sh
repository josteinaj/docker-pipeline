#!/bin/bash

NUMBER="`cat /mnt/input/number.txt | head -n 1`"

f1=0
f2=1
while [ $f1 -lt $NUMBER ]; do
    echo "$f1" > "/mnt/output/$f1.txt"
    fn=$((f1+f2))
    f1=$f2
    f2=$fn
done

echo "success" > /mnt/status/status.txt
