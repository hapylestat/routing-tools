
from apputils.net.curl import curl
from apputils.core.config.main import Configuration
from models import Networks
import sys


RIPE_BGP_STATUS_URL = "https://stat.ripe.net/data/bgp-state/data.json?resource={}"


class DisplayOptions(object):
    IPV4 = "ipv4"
    IPV6 = "ipv6"
    NETS = "nets"


def fetch_ripe_info(as_list):
    """
    Downloading metadata from RIPE

    :type as_list list[str]
    :rtype dict|None
    """
    if not isinstance(as_list, (list, set)):
        return None

    r = curl(RIPE_BGP_STATUS_URL.format(",".join(as_list)))
    if r.code == 200:
        return r.from_json()

    return None


def filter_ipv4(l):
    """
    :type l list[str]
    :rtype list
    """
    if not isinstance(l, (list, set)):
        return None

    return [i for i in l if "." in l]


def filter_ipv6(l):
    """
    :type l list[str]
    :rtype list
    """
    if not isinstance(l, (list, set)):
        return None

    return [i for i in l if ":" in l]


def generate_exclude_lists(nets, include_optional=True, make_query=True):
    """
    :type nets Networks
    :type include_optional bool
    :type make_query bool
    """
    as_list = []
    nets_list = []

    net_names = []
    prefixes_ipv4 = []
    prefixes_ipv6 = []

    for net in nets.items:
        if not include_optional and net.optional:
            continue

        net_names.append(net.name)
        as_list.extend(net.as_list)
        nets_list.extend(net.nets)

    nets = fetch_ripe_info(as_list) if make_query else None

    if not nets:
        return net_names, None, None

    for item in nets["data"]["bgp_state"]:
        if ":" in item["target_prefix"] and item["target_prefix"] not in prefixes_ipv6:
            prefixes_ipv6.append(item["target_prefix"])

        if "." in item["target_prefix"] and item["target_prefix"] not in prefixes_ipv4:
            prefixes_ipv4.append(item["target_prefix"])

    prefixes_ipv4.extend(filter_ipv4(nets_list))
    prefixes_ipv6.extend(filter_ipv6(nets_list))

    return net_names, prefixes_ipv4, prefixes_ipv6


def main():
    conf = Configuration()
    nets = Networks(serialized_obj=conf.get_module_config("networks"))

    option = conf.get("default")
    inc_optional_nets = conf.get("optional", default="true", check_type=str) == "true"

    if len(option) == 0 or option[0] == DisplayOptions.IPV4:
        display_mode = DisplayOptions.IPV4
    elif len(option) > 0 and option[0] == DisplayOptions.IPV6:
        display_mode = DisplayOptions.IPV6
    elif len(option) > 0 and option[0] == DisplayOptions.NETS:
        display_mode = DisplayOptions.NETS
    else:
        print("Please use: {}, {}, {} to display respective information with --optional argument\
 to chose if optional networks need to be displayed".format(
            DisplayOptions.NETS,
            DisplayOptions.IPV4,
            DisplayOptions.IPV6))
        sys.exit(-1)

    net_names, prefixes_ipv4, prefixes_ipv6 = generate_exclude_lists(nets,
                                                                     include_optional=inc_optional_nets,
                                                                     make_query=display_mode != DisplayOptions.NETS)

    if not prefixes_ipv4 and display_mode != DisplayOptions.NETS:
        print("[ERR] List is empty or error occurs!")
        sys.exit(-1)

    if display_mode == DisplayOptions.IPV4:
        print("\n".join(prefixes_ipv4))
    elif display_mode == DisplayOptions.IPV6:
        print("\n".join(prefixes_ipv6))
    elif display_mode == DisplayOptions.NETS:
        print("\n".join(net_names))


if __name__ == '__main__':
    main()
