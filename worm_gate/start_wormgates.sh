#!/bin/bash

# Generates a list of wormgates (HOST:PORT) for the number as input
# Starts wormgates from the list ("wormgates")
# Modified from "wormgates_start.sh (Author: Mike Murphy <michael.j.murphy@uit.no>)" 

if [ $# -lt 1 ]; then
    echo "Usage: sh start_wormgates.sh {number of wormgates}"
    exit 
fi

echo "run $1 wormgates"

/share/apps/ifi/available-nodes.sh | grep compute | shuf | head -n $1 > nodes
shuf -i 49152-65535 -n $1 > ports
paste -d ':' nodes ports > wormgates

WORMGATE="$(readlink -f wormgate.py)"
WORMGATES_LIST="$(readlink -f wormgates)"
OTHER_GATES=""

for n in $(< wormgates)
do
    OTHER_GATES+="$n "
done
echo -n "OTHER_GATES:$OTHER_GATES "

while IFS='' read -r LINE || [[ -n "$LINE" ]]
do
    if [[ "$LINE" =~ ^[a-zA-Z0-9_-]+:[0-9]+$ ]]
    then
        HOST="$(echo "$LINE" | cut -d':' -f1)"
        PORT="$(echo "$LINE" | cut -d':' -f2)"
        echo -n "$HOST:$PORT -- "
        if [[ "$HOST" == "localhost" ]]
        then
            (set -x; "$WORMGATE" -p "$PORT" $* &)
        else
            (set -x; ssh -f "$HOST" "$WORMGATE" -p "$PORT" "$OTHER_GATES")
        fi

    else
        echo "Skipping line that does not match host:port format: $LINE"
    fi
done <"$WORMGATES_LIST"