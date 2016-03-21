#!/bin/bash

NUMBER="`cat /mnt/input/number.txt | head -n 1`"
RESULT="`echo $(($NUMBER * $NUMBER))`"

echo $RESULT > /mnt/output/number.txt

echo "success" > /mnt/status/status.txt
