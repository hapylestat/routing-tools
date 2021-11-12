#!/bin/bash

MYDIR=$(dirname ${BASH_SOURCE[0]})

if [ -z $2 ]; then
 echo "Please set profile name to use"
 exit 1
fi

. $MYDIR/conf/profiles/$2

APP=${APP:-}  # used for ipset table name
MYTABLE=${MYTABLE:-}
MYFWMARK=${MYFWMARK:-}
DEV=${DEV:-}
IPROUTE=${IPROUTE:-}

create_ipset_restore() {
  local rules=$1
  if [ -z ${rules} ]; then 
    local ROUTES=`python ${MYDIR}/main.py ipv4`
  else 
    local ROUTES=`python ${MYDIR}/main.py ipv4 --nets="${rules}"`
  fi

  for r in ${ROUTES}; do
   echo "add ${APP} ${r}\n"
  done
}


do_custom_route(){
 local rules=$1

 ping -c 1 -n -W 1 ${IPROUTE} 1>/dev/null 2>&1
 if [ $? -ne 0 ]; then
   echo "Router ping test failed...aborting"
   exit 1
 fi

 echo "My Router IP: ${IPROUTE}/${DEV}"

 ipset create ${APP} hash:net 1>/dev/null 2>&1

 echo "Getting sub-nets list for ${rules} and publishing them to the storage..."
 echo -e $(create_ipset_restore ${rules}) | ipset restore -!

 iptables -t mangle -A PREROUTING -m set --match-set ${APP} dst -j MARK --set-mark ${MYFWMARK}
 iptables -t mangle -A OUTPUT -m set --match-set ${APP} dst -j MARK --set-mark ${MYFWMARK}

 ip rule add fwmark ${MYFWMARK} table ${MYTABLE}
 ip route add default via ${IPROUTE} dev ${DEV} table ${MYTABLE} prio 100


 # allow async routes to work properly
 echo 2 >  /proc/sys/net/ipv4/conf/${DEV}/rp_filter
}


do_route(){
 
 ping -c 1 -n -W 1 ${IPROUTE} 1>/dev/null 2>&1
 if [ $? -ne 0 ]; then
   echo "Router ping test failed...aborting"
   exit 1
 fi
 
 echo "My Router IP: ${IPROUTE}" 

 ipset create ${APP} hash:net 1>/dev/null 2>&1
 if [ $? -eq 0 ]; then 
  echo "Getting sub-nets list and publishing routes to the storage..."
  echo -e $(create_ipset_restore) | ipset restore -!
 else
  echo "Using cached routes (run rt.sh reset to update cache) ..".
 fi
  
 iptables -t mangle -A PREROUTING -m set --match-set ${APP} dst -j MARK --set-mark ${MYFWMARK}
 iptables -t mangle -A OUTPUT -m set --match-set ${APP} dst -j MARK --set-mark ${MYFWMARK}
 
 ip rule add fwmark ${MYFWMARK} table ${MYTABLE}
 ip route add default via ${IPROUTE} table ${MYTABLE} prio 100
 
 
 
 # allow async routes to work properly 
 echo 2 >  /proc/sys/net/ipv4/conf/${DEV}/rp_filter
 
}

do_unroute(){
 echo "Removing routes..."
 
 ping -c 1 -n -W 1 ${IPROUTE} 1>/dev/null 2>&1
 if [ $? -ne 0 ]; then
   echo "Router ping test failed...aborting"
   exit 1
 fi

 iptables -t mangle -D PREROUTING -m set --match-set ${APP} dst -j MARK --set-mark ${MYFWMARK} 1>/dev/null 2>&1
 iptables -t mangle -D OUTPUT -m set --match-set ${APP} dst -j MARK --set-mark ${MYFWMARK} 1>/dev/null 2>&1

 ip rule del fwmark ${MYFWMARK} table ${MYTABLE} 1>/dev/null 2>&1
 ip route del prio 100 via ${IPROUTE} table ${MYTABLE} 1>/dev/null 2>&1
 ip route del default table ${MYTABLE} prio 100
}

do_reset_cache(){
 echo "Removing cached routes.."
 ipset destroy ${APP} 1>/dev/null 2>&1
}



case $1 in
  start)
   do_route
  ;;
  update)
   if [ -z $3 ]; then
     echo "please provide rule list to apply as argument"
     exit 1
   fi

   do_custom_route "$3"
  ;;
  stop)
   do_unroute
  ;;
  reset)
   do_unroute
   do_reset_cache
  ;;
  *)
  echo "rt.sh start|update|stop|reset  <profile name> [rule name]"
  ;;
esac