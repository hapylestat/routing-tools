import socket
from contextlib import contextmanager

from modules.apputils.curl import curl

RIPE_BGP_STATUS_URL = "https://stat.ripe.net/data/bgp-state/data.json?resource={}"


class QueryMethod(object):
  ripe = 0
  radb_whois = 1


def fetch_ripe_info(as_list):
  """
  Downloading metadata from RIPE

  :type as_list list[str]
  :rtype list
  """
  if not isinstance(as_list, (list, set)):
    return None

  results = []

  r = curl(RIPE_BGP_STATUS_URL.format(",".join(as_list)))
  if r.code == 200:
    nets = r.from_json()
    if not nets:
      return None

    for item in nets["data"]["bgp_state"]:
      results.append(item["target_prefix"])

  return results


class WhoisQuery(object):

  def __init__(self, server="whois.radb.net", port=43):
    self.__whois_server = (server, port)

  def query(self, q):
    """
    :type q str
    """
    _sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
      _sock.connect(self.__whois_server)
      _sock.send(str(q + "\r\n").encode())

      response = b""
      while True:
        data = _sock.recv(4096)
        if not data:
          break

        response += data

      return response.decode()
    finally:
      try:
        _sock.close()
      except:
        pass

    return ""

  def subnets_by_asn(self, asn):
    """
    :type asn str
    :rtype list[str]
    """
    result = []
    q = "-i origin {}".format(asn)
    lines = self.query(q).split("\n")
    for line in lines:
      if line.startswith("route"):
        result.append(line.partition(":")[2].strip())

    return result

  def subnets_by_asns(self, asn_list):
    """
    :type asn_list list
    :rtype list[str]
    """
    results = []
    for asn in asn_list:
      results.extend(self.subnets_by_asn(asn))

    return results


def nslookup(sitename):
  """
  :type sitename str
  """
  try:
    return socket.gethostbyname_ex(sitename)[2]
  except:
    return []
