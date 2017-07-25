
from apputils.types.config import ConfigObject


class NetworkItem(ConfigObject):
    name = None
    as_list = []
    nets = []
    optional = False


class Networks(ConfigObject):
    items = [NetworkItem]
