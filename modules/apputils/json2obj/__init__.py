#  Licensed to the Apache Software Foundation (ASF) under one or more
#  contributor license agreements.  See the NOTICE file distributed with
#  this work for additional information regarding copyright ownership.
#  The ASF licenses this file to You under the Apache License, Version 2.0
#  (the "License"); you may not use this file except in compliance with
#  the License.  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#
#  Github: https://github.com/hapylestat/apputils
#
#
import json
from types import FunctionType
from typing import get_type_hints, get_args, ClassVar, Dict


class SerializableObject(object):
  """
   SerializableObject is a basic class, which providing Object to Dict, Dict to Object conversion with
   basic fields validation.

   For example we have such dictionary:

   my_dict = {
     name: "Amy",
     age: 18
   }

   and we want to convert this to the object with populated object fields by key:value pairs from dict.
   For that we need to declare object view and describe there expected fields:

   class PersonView(SerializableObject):
     name = None
     age = None

    Instead of None, we can assign another values, they would be used as default if  data dict will not contain
     such fields.  Now it's time for conversion:

    person = PersonView(serialized_obj=my_dict)


    As second way to initialize view, view fields could be directly passed as constructor arguments:

    person = PersonView(name=name, age=16)

  """

  """
  Any error in de-serialization will trigger ValueError exception
  """
  __strict__: bool = True

  """
  Group an json key by the string.endswith pattern.

  Example JSON:
  {
    'a_url': 'xxxxxxx',
    'b_url': 'yyyyyyy'
  }

  Example class:
   class MyObject(SerializableObject):
     __mapping__ = {
      'uris' : '_url'
     }

  Resulting object:

  MyObject = {
    uris: {
     'a_url': 'xxxxxx',
     'b_url': 'yyyyyy'
    }
  }

  """
  __mapping__: Dict = {}

  """
  Alias json key to proper PyObject field name.

  For example:
   'a:b' -> 'a_b"

   class MyObject(SerializableObject):
     __aliases__ = {
       'existing_field': 'json_key',
       'a_b' : 'a:b'
     }
  """
  __aliases__: Dict = {}

  def __init__(self, serialized_obj: str or dict or object or None = None, **kwargs):
    self.__error__ = []

    if isinstance(serialized_obj, type(self)):
      import copy
      self.__dict__ = copy.deepcopy(serialized_obj.__dict__)
      self.__annotations__ = copy.deepcopy(serialized_obj.__annotations__)
      return

    if isinstance(serialized_obj, str):
      # ToDo: inject class decode via object_hook/object_pairs_hook with provided schema
      serialized_obj = json.loads(serialized_obj)

    assert type(serialized_obj) is dict or serialized_obj is None

    if len(kwargs) > 0:
      if serialized_obj:
        serialized_obj.update(kwargs)
      else:
        serialized_obj = kwargs

    if serialized_obj is None:
      return

    self.__deserialize(serialized_obj)

  def __handle_errors(self, clazz: ClassVar, d: dict, missing_definitions, missing_annotations):
    for miss_def in missing_definitions:
      v = d[miss_def]
      self.__error__.append(f"{clazz.__name__} class doesn't contain property '{miss_def}: {type(v).__name__}' (value sample:{v})")

    for miss_ann in missing_annotations:
      self.__error__.append(f"{clazz.__name__} class doesn't contain type annotation in the definition '{miss_ann}'")

    if not self.__error__:
      return

    end_line = "\n- "
    raise ValueError(f"""
A number of errors happen:
--------------------------
- {end_line.join(self.__error__)}
""")

  def __deserialize_transform(self, property_value, schema):
    is_generic = '__origin__' in schema.__dict__
    _type = schema.__dict__['__origin__'] if is_generic else schema
    schema_args = list(get_args(schema)) if is_generic else [] if _type is list else [schema]
    schema_len = len(schema_args)
    property_type = schema_args[0] if schema_args else None

    if property_type in (int, float, complex) and isinstance(property_value, str) and property_value == "":
      property_value = 0  # this is really weird fix for bad written API

    if property_type and property_value is not None and not isinstance(property_value, _type) \
      and not (issubclass(property_type, SerializableObject) and isinstance(property_value, dict)):

      self.__error__.append(
        "Conflicting type in schema and data for object '{}', expecting '{}' but got '{}' (value: {})".format(
          self.__class__.__name__,
          property_type.__name__,
          type(property_value).__name__,
          property_value
        ))
      return None

    if _type is list:
      return [property_type(i) for i in property_value] if property_type else property_value
    elif _type is dict:
      return {k: self.__deserialize_transform(v, schema_args[1] if schema_len == 2 else type(v)) for k, v in property_value.items()}
    else:
      return _type(property_value) if _type and property_value is not None else property_value

  def __deserialize(self, d: dict):
    self.__error__ = []
    clazz = self.__class__
    exclude_types = (FunctionType, property, classmethod, staticmethod)
    properties = {k: v for k, v in clazz.__dict__.items() if not k.startswith("__") and not isinstance(v, exclude_types)}
    annotations = get_type_hints(clazz)

    for property_name, schema in annotations.items():
      if property_name.startswith("__"):
        continue

      try:
        # the way to map properties like "a-b" to python fields
        resolved_prop = self.__aliases__[property_name]
      except KeyError:
        resolved_prop = property_name

      if resolved_prop not in d:  # Property didn't come with data, setting default value
        self.__setattr__(property_name, properties[property_name])
        continue

      property_value = d[resolved_prop]
      self.__setattr__(property_name, self.__deserialize_transform(property_value, schema))

    missing_definitions = set(d.keys()) - set(annotations.keys()) - set(self.__aliases__.values())
    if self.__mapping__:
      for definition, pattern in self.__mapping__.items():
        ret = {}
        for unknown_def in missing_definitions:
          if unknown_def.endswith(pattern):
            ret[unknown_def] = d[unknown_def]
        if ret:
          self.__setattr__(definition, ret)
          missing_definitions = set(missing_definitions) - set(ret.keys())

    if self.__strict__:
      missing_annotations = set(properties.keys()) - set(annotations.keys())
      self.__handle_errors(clazz, d, missing_definitions, missing_annotations)

  def __serialize_transform(self, item):
    _type = type(item)

    if _type is list:
      return [self.__serialize_transform(i) for i in item]
    elif _type is dict:
      return {k: self.__serialize_transform(v) for k, v in item.items() if v is not None}
    else:
      return self.__serialize_transform(item.serialize()) if issubclass(_type, SerializableObject) else _type(item)

  def serialize(self) -> dict:
    # first of all we need to move defaults from class
    all_properties = dict(self.__class__.__dict__)
    all_properties.update(dict(self.__dict__))
    _filter_properties = list(self.__aliases__.keys()) + list(self.__mapping__.keys())

    properties: Dict = {k: v for k, v in all_properties.items()
                        if not k.startswith("__")                                     # filter hidden properties
                        and not isinstance(v, (FunctionType, property, classmethod))  # ignore functions
                        and k not in _filter_properties                               # exclude "special cases"
                        }

    if self.__aliases__:
      properties.update({a: all_properties[p] for p, a in self.__aliases__.items() if p in all_properties})

    if self.__mapping__:
      for k in self.__mapping__.keys():
        if k in all_properties and isinstance(all_properties[k], dict):
          properties.update(all_properties[k])

    return self.__serialize_transform(properties)

  def to_json(self) -> str:
    # ToDo: inject class encode via object_hook/object_pairs_hook with provided schema
    return json.dumps(self.serialize())
