

# For logging the recovery:

#   1. curl -X POST kill
#   2. start a timer  
#     # a. 2 sec time delay for the network
#     # b. 3 sec time delay for the keep alive
#   3. start a loop:
#         target
#         for each gate
#           curl -X GET '..'
#           numofworms
#       if target == numofoworms
#       stop the timer

#       10s

#Get the target size and the size of worms to kill
if [ $# -lt 2 ]; then
    echo "Usage: sh log_recovery.sh {target} {number of worms to kill}"
    exit 
fi

#Get the host and port of the worm gates
LINE=1
while read -r NODE
  do

    GATES[LINE-1]=$NODE
    arrIN=(${NODE//:/ })
    GATES_PORT[LINE-1]=${arrIN[1]}

    ((LINE++))
done < "./wormgates"

# for j in "${!GATES[@]}"; do
#   echo "${GATES[j]}"
#   echo "${GATES_PORT[j]}"
# done 


#Kill the worms segments
i=0
while [ $i -lt $2 ]
  do
    curl -X POST 'http://'"${GATES[i]}"'/kill_worms'
    echo 'http://'"${GATES[i]}"'/kill_worms'
    ((i++))
  done

#Start the timer
start=$(date +%s)
echo "start: $start"

#Keep checking the number of worm segments in each gate and sum them up
#Break the loop if the total worm segments is bigger than the target size
NUM_SEGMENTS=0
while [ $NUM_SEGMENTS -lt $1 ]
  do
    NUM_SEGMENTS=0
    for k in "${!GATES[@]}"; do
      POLL_URL='http://'"${GATES[k]}"'/info'
      response=$(curl -s -w "%{http_code}" $POLL_URL)
      content=$(sed '$ d' <<< "$response") 
      # echo "content:$content"
      numsegments=$(curl -s $POLL_URL | python3 -c "import sys, json; print(json.load(sys.stdin)['numsegments'])")
      # echo "numsegments: $numsegments"
      NUM_SEGMENTS=$((NUM_SEGMENTS + numsegments))
    done 
    # echo "NUM_SEGMENTS: $NUM_SEGMENTS"
  done

#Stop the timer
end=$(date +%s)
echo "end: $end"
#Calculate the time used
seconds=$(echo "$end - $start" | bc)
echo $seconds' sec'
