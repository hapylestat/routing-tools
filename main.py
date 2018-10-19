from __future__ import print_function

from apputils.core.config.main import Configuration

from lookup import QueryMethod, fetch_ripe_info, nslookup, WhoisQuery
from models import Networks
from netaddr import IPNetwork

import sys
import itertools


class DisplayOptions(object):
  IPV4 = "ipv4"
  IPV6 = "ipv6"
  NETS = "nets"

def is_number(s):
  try:
    float(s)
    return True
  except ValueError:
    pass

  try:
    import unicodedata
    unicodedata.numeric(s)
    return True
  except (TypeError, ValueError):
    pass

  return False


def filter_ipv4(addr_list):
  """
  :type addr_list list[str]
  :rtype list
  """
  if not isinstance(addr_list, list):
    return None

  return [item for item in addr_list if "." in item]


def filter_ipv6(addr6_list):
  """
  :type addr6_list list[str]
  :rtype list
  """
  if not isinstance(addr6_list, list):
    return None

  return [item for item in addr6_list if ":" in item]


def generate_exclude_lists(nets, include_optional=True, make_query=True, method=QueryMethod.radb_whois):
  """
  :type nets Networks
  :type include_optional bool
  :type make_query bool
  :type method QueryMethod
  """
  whois = WhoisQuery()

  as_list = []
  nets_list = []
  net_names = []

  for net in nets.items:
    if not include_optional and net.optional:
      continue

    for item in net.items:
      if item.lower().startswith("as"):
        as_list.append(item)
      elif ":" in item:
        nets_list.append(item)
      elif is_number(item.partition(".")[0]):
        if "/" not in item:
          nets_list.append("{}/32".format(item))
        else:
          nets_list.append(item)
      else:
        nets_list.extend(("{}/32".format(item) for item in nslookup(item)))

    net_names.append(net.name)

  if method == QueryMethod.ripe:
    nets_list.extend(fetch_ripe_info(as_list) if make_query else [])
  elif method == QueryMethod.radb_whois:
    nets_list.extend(whois.subnets_by_asns(as_list))

  return net_names, filter_ipv4(nets_list), filter_ipv6(nets_list)


def networks_printer(networks, formatter):
  if formatter:
    counter = itertools.count(1)
    for net_str in networks:
      net_parsed = IPNetwork(net_str)
      try:
        print(
          formatter.format(net=net_parsed.network, cidr=net_parsed.prefixlen, mask=net_parsed.netmask, count=next(counter))
        )
      except KeyError as e:
        print("Wrong formatter key '{0}'. 'net', 'cidr', 'mask', 'count' are supported".format(e.message))
        sys.exit(-1)
  else:
    print("\n".join(networks))


def main():
  conf = Configuration()
  nets = Networks(serialized_obj=conf.get_module_config("networks"))

  option = conf.get("default")
  inc_optional_nets = conf.get("optional", default="true", check_type=str) == "true"
  formatter = conf.get("formatter", default="", check_type=str)
  nets_to_proccess = conf.get("nets", default="", check_type=str)
  nets_to_proccess = [] if not nets_to_proccess else nets_to_proccess.split(",")

  if len(option) == 0 or option[0] == DisplayOptions.IPV4:
    display_mode = DisplayOptions.IPV4
  elif len(option) > 0 and option[0] == DisplayOptions.IPV6:
    display_mode = DisplayOptions.IPV6
  elif len(option) > 0 and option[0] == DisplayOptions.NETS:
    display_mode = DisplayOptions.NETS
  else:
    print("""Please use: {}, {}, {} to display respective information with --optional argument\
to chose if optional networks need to be displayed.\nAlso you can specify --formatter=\"FORMAT_STR\", to print \
information formatted output.
Formatter string must be in default python format syntax, variables that passed to format call:
* net - network ip
* mask - network mask
* cidr - network mask in cidr notation
* count - route number
""".format(
      DisplayOptions.NETS,
      DisplayOptions.IPV4,
      DisplayOptions.IPV6))
    sys.exit(-1)

  filtered_nets = [] if nets_to_proccess else nets.items
  if nets_to_proccess:
    for net in nets.items:
      if net.name in nets_to_proccess:
        filtered_nets.append(net)

  net_names, prefixes_ipv4, prefixes_ipv6 = generate_exclude_lists(Networks(items=filtered_nets),
                                                                   include_optional=inc_optional_nets,
                                                                   make_query=display_mode != DisplayOptions.NETS)

  if not prefixes_ipv4 and display_mode != DisplayOptions.NETS:
    print("[ERR] List is empty or error occurs!")
    sys.exit(-1)

  if display_mode == DisplayOptions.IPV4:
    networks_printer(prefixes_ipv4, formatter)
  elif display_mode == DisplayOptions.IPV6:
    networks_printer(prefixes_ipv6, formatter)
  elif display_mode == DisplayOptions.NETS:
    print("\n".join(net_names))


if __name__ == '__main__':
  main()
