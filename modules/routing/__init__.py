
import itertools

from netaddr import IPNetwork
from lookup import QueryMethod, WhoisQuery, fetch_ripe_info, nslookup


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


def networks_printer(networks, formatter, sys=None):
  if formatter:
    counter = itertools.count(1)
    for net_str in networks:
      net_parsed = IPNetwork(net_str)
      try:
        print(formatter.format(
          net=net_parsed.network,
          cidr=net_parsed.prefixlen,
          mask=net_parsed.netmask,
          count=next(counter)
        ))
      except KeyError as e:
        print(f"Wrong formatter key '{e}'. 'net', 'cidr', 'mask', 'count' are supported")
        sys.exit(-1)
  else:
    print("\n".join(networks))