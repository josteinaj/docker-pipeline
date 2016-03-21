#!/bin/bash

CONTAINER_ID="`cat /proc/self/cgroup | grep "/docker/" | head -n 1 | sed 's/.*\///g'`"

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd $DIR

exec $DIR/run.py "$1" "$CONTAINER_ID" "${@:2}"
