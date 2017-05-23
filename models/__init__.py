
from apputils.types.config import ConfigObject


class NetworkItem(ConfigObject):
    name = None
    as_list = []


class Networks(ConfigObject):
    items = [NetworkItem]
