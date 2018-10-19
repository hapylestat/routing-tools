#!/bin/bash

MYDIR=$(dirname ${BASH_SOURCE[0]})
APP=uablock  # used for ipset table name
MYTABLE=160
MYFWMARK=0xaf


do_custom_route(){
 local IF_DEV=$1
 local ifIP=$2
 local rules=$3

 ping -c 1 -n -W 1 ${ifIP} 1>/dev/null 2>&1
 if [ $? -ne 0 ]; then
   echo "Router ping test failed...aborting"
   exit 1
 fi

 echo "My Router IP: ${ifIP}"

 ipset create ${APP} hash:net 1>/dev/null 2>&1
 if [ $? -eq 0 ]; then
  echo "Getting sub-nets list for ${rules}..."
  local ROUTES=`python ${MYDIR}/main.py --nets=${rules}`

  echo  "Publishing networks to storage..."
  for r in ${ROUTES}; do
    ipset add ${APP} ${r}
  done
 else
  echo "Using cached routes (run rt.sh reset to update cache) ..".
 fi

 iptables -t mangle -A PREROUTING -m set --match-set ${APP} dst -j MARK --set-mark ${MYFWMARK}
 iptables -t mangle -A OUTPUT -m set --match-set ${APP} dst -j MARK --set-mark ${MYFWMARK}

 ip rule add fwmark ${MYFWMARK} table ${MYTABLE}
 ip route add default via ${ifIP} table ${MYTABLE} prio 100



 # allow async routes to work properly
 echo 2 >  /proc/sys/net/ipv4/conf/${IF_DEV}/rp_filter
}


do_route(){
 local IF_DEV=$1
 local ifIP=$2
 
 ping -c 1 -n -W 1 ${ifIP} 1>/dev/null 2>&1
 if [ $? -ne 0 ]; then
   echo "Router ping test failed...aborting"
   exit 1
 fi
 
 echo "My Router IP: ${ifIP}" 

 ipset create ${APP} hash:net 1>/dev/null 2>&1
 if [ $? -eq 0 ]; then 
  echo "Getting sub-nets list..."
  local ROUTES=`python ${MYDIR}/main.py`
  
  echo  "Publishing networks to storage..."
  for r in ${ROUTES}; do
    ipset add ${APP} ${r}
  done
 else
  echo "Using cached routes (run rt.sh reset to update cache) ..".
 fi
  
 iptables -t mangle -A PREROUTING -m set --match-set ${APP} dst -j MARK --set-mark ${MYFWMARK}
 iptables -t mangle -A OUTPUT -m set --match-set ${APP} dst -j MARK --set-mark ${MYFWMARK}
 
 ip rule add fwmark ${MYFWMARK} table ${MYTABLE}
 ip route add default via ${ifIP} table ${MYTABLE} prio 100
 
 
 
 # allow async routes to work properly 
 echo 2 >  /proc/sys/net/ipv4/conf/${IF_DEV}/rp_filter
 
}

do_unroute(){
 echo "Removing routes..."
 local IF_DEV=$1
 local ifIP=$2
 
 ping -c 1 -n -W 1 ${ifIP} 1>/dev/null 2>&1
 if [ $? -ne 0 ]; then
   echo "Router ping test failed...aborting"
   exit 1
 fi

 ip rule del fwmark ${MYFWMARK} table ${MYTABLE} 1>/dev/null 2>&1
 ip route del prio 100 via ${ifIP} table ${MYTABLE} 1>/dev/null 2>&1
 ip route del default table ${MYTABLE} prio 100
  
 iptables -t mangle -D PREROUTING -m set --match-set ${APP} dst -j MARK --set-mark ${MYFWMARK} 1>/dev/null 2>&1
 iptables -t mangle -D OUTPUT -m set --match-set ${APP} dst -j MARK --set-mark ${MYFWMARK} 1>/dev/null 2>&1
}

do_reset_cache(){
 echo "Removing cached routes.."
 ipset destroy ${APP} 1>/dev/null 2>&1
}



case $1 in
  start)
   if [ -z $2 ] || [ -z $3 ]; then
     echo "Please provide interface name and routing gw ip(remote point) as argument"
     exit 1
   fi
   
   do_route $2 $3
  ;;
  part-start)
   if [ -z $2 ] || [ -z $3 ] || [ -z $4 ]; then
     echo "Please provide interface name,  routing gw ip(remote point) and rule list to apply as argument"
     exit 1
   fi

   do_custom_route $2 $3 "$4"
  ;;
  stop)
   if [ -z $2 ] || [ -z $3 ]; then
     echo "Please provide interface name and routing gw ip(remote point) as argument"
     exit 1
   fi

   do_unroute $2 $3
  ;;
  reset)
   if [ -z $2 ] || [ -z $3 ]; then
     echo "Please provide interface name and routing gw ip(remote point) as argument"
     exit 1
   fi

   do_unroute $2 $3
   do_reset_cache
  ;;
  *)
  echo "rt.sh start|part-start|stop|reset  <Route if device name> <Route GW ip addr> [rule name for part-start]"
  ;;
esac