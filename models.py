from typing import List

from modules.apputils.json2obj import SerializableObject


class NetworkItem(SerializableObject):
  name: str = None
  items:List[str] = []
  optional: bool = False


class Networks(SerializableObject):
  items:List[NetworkItem] = []
