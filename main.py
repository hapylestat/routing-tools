
from apputils.net.curl import curl
from apputils.core.config.main import Configuration
from models import Networks

conf = Configuration()
nets = Networks(serialized_obj=conf.get_module_config("networks"))

prefixes_ipv4 = []
prefixes_ipv6 = []

as_list = []

for net in nets.items:
    as_list.extend(net.as_list)

nets = curl("https://stat.ripe.net/data/bgp-state/data.json?resource={}".format(",".join(as_list))).from_json()

for item in nets["data"]["bgp_state"]:
    if ":" in item["target_prefix"] and item["target_prefix"] not in prefixes_ipv6:
        prefixes_ipv6.append(item["target_prefix"])

    if "." in item["target_prefix"] and item["target_prefix"] not in prefixes_ipv4:
        prefixes_ipv4.append(item["target_prefix"])

print("\n".join(prefixes_ipv4))
print("\n".join(prefixes_ipv6))
