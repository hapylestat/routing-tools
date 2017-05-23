
from apputils.net.curl import curl


AS_LIST = {
    "vk": [
        "AS47542", "AS47541", "AS28709"
    ],
    "mail.ru games": [
        "AS21051"
    ],
    "mail.ru base": {
        "AS47764"
    }
}


prefixes_ipv4 = []
prefixes_ipv6 = []

for net_name, as_list in AS_LIST.items():
    nets = curl("https://stat.ripe.net/data/bgp-state/data.json?resource={}".format(",".join(as_list))).from_json()

    for item in nets["data"]["bgp_state"]:
        if ":" in item["target_prefix"] and item["target_prefix"] not in prefixes_ipv6:
            prefixes_ipv6.append(item["target_prefix"])

        if "." in item["target_prefix"] and item["target_prefix"] not in prefixes_ipv4:
            prefixes_ipv4.append(item["target_prefix"])

print("\n".join(prefixes_ipv4))
print("\n".join(prefixes_ipv6))
