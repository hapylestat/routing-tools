
from apputils.types.config import ConfigObject


class NetworkItem(ConfigObject):
  name = None
  items = []
  optional = False


class Networks(ConfigObject):
  items = [NetworkItem]
