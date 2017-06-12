#!/bin/bash

MYDIR=$(dirname ${BASH_SOURCE[0]})

echo "Getting sub-nets list..."
ROUTES=`python $MYDIR/main.py`
GATE=2.3.2.1


do_route(){
 echo "Adding routes..."
 for r in $ROUTES; do
   if [[ $r == *"/32"* ]]; then
     route add -host $r gw $GATE 1>/dev/null 2>&1
   else
     route add -net $r gw $GATE 1>/dev/null 2>&1
   fi
 done

}

do_unroute(){
  echo "Removing routes..."
 for r in $ROUTES; do
   if [[ $r == *"/32"* ]]; then
     route del -host $r gw $GATE 1>/dev/null 2>&1
   else
     route del -net $r gw $GATE 1>/dev/null 2>&1
   fi
 done
}



case $1 in
  start)
   do_route
  ;;
  stop)
   do_unroute 
  ;;
  *)
  echo Use start or stop as arguments
  ;;
esac