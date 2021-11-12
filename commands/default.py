import os
import sys
import json

from typing import List
from models import Networks

from modules.apputils.discovery import CommandMetaInfo

__module__ = CommandMetaInfo("default", "Shows the detailed information about requested VMs")
__args__ = __module__.arg_builder \
  .add_default_argument("display_mode", str, "") \
  .add_argument("nets", list, "Networks to apply changes", default=[]) \
  .add_argument("optional", bool,"", default=True) \
  .add_argument("formatter", str, "", default="")

from modules.routing import DisplayOptions, generate_exclude_lists, networks_printer


def __init__(root_path: str, nets: List[str], formatter: str, optional: bool, display_mode: str):
  __networks_file = os.path.join(root_path, "conf", "networks.json")
  try:
    with open(__networks_file, "r") as fp:
      nets_to_proccess = Networks(serialized_obj=json.load(fp))
  except FileNotFoundError:
    raise FileNotFoundError(f"Network definition profile not found: {__networks_file}")

  inc_optional_nets = optional

  if not display_mode or display_mode not in (DisplayOptions.IPV4, DisplayOptions.IPV6, DisplayOptions.NETS):
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


  filtered_nets = [net for net in nets_to_proccess.items if net.name in nets] if nets else nets_to_proccess.items

  if display_mode == DisplayOptions.NETS:
    print("\n".join([net.name for net in filtered_nets]))
  else:
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