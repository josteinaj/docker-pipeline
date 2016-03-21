#!/bin/bash
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd $DIR

if [ "$1" = "test" ]; then
    PIPELINE_DIR="$DIR/test/pipeline"
fi
if [ "$PIPELINE_DIR" = "" ]; then
    echo "PIPELINE_DIR not set"
    exit 1
fi

docker build . >/dev/null
BUILDID="`docker build . | grep "." | tail -n 1 | sed 's/.* //'`"
echo
echo
#set -x
docker run \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -v $DIR/test/pipeline:/mnt/pipeline:ro \
    -v $DIR/test/config:/mnt/config:ro \
    "$BUILDID" "$PIPELINE_DIR" "$@"
