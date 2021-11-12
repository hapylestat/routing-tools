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

from collections import OrderedDict
from typing import Dict, Callable, List, get_origin, Optional


class CommandArgumentException(Exception):
  pass


class NoCommandException(Exception):
  def __init__(self, command_name: str or None, message: str):
    super(NoCommandException, self).__init__(message)
    self.__command_name = command_name

  @property
  def command_name(self):
    return self.__command_name


class NotImplementedCommandException(Exception):
  pass


class CommandArgumentItem(object):
  name = None
  value_type = None
  item_help = None
  default = None

  def __init__(self, name: str, value_type: type, item_help: str, default: object = None, alias: str = None):
    self.name = name
    self.value_type = value_type
    self.item_help = item_help
    self.default = default
    self.alias = alias

  @property
  def has_default(self):
    return self.default is not None


class CommandArgumentsBuilder:
  def __init__(self):
    self._args: Dict[str, CommandArgumentItem] = {}
    self._alias_args: Dict[str, CommandArgumentItem] = {}
    self._default_args: Dict[str, CommandArgumentItem] = OrderedDict()
    self.__allowed_default_types = [int, str, float, list]
    self.__allowed_types = self.__allowed_default_types + [bool]
    self.__is_default_arg_flag_used = False

  def add_argument(self, name: str, value_type: type, item_help: str, default: object = None, alias: str = None):
    """
    :arg name name of the argument as it would be used in __init__ function
    :arg value_type python type of the value
    :arg item_help description of element, why it needed anf what it doing
    :arg default default value for the argument. If it is not None, argument is considered as Optional
    :arg alias if set, the name of the argument in console. Otherwise would be taken the same as name

    :rtype CommandArgumentsBuilder
    """
    origin = get_origin(value_type)
    if origin is not None:
      value_type = origin

    if value_type and value_type not in self.__allowed_types:
      raise CommandArgumentException(f"Named argument couldn't have {value_type.__name__} type")

    if default is not None and not isinstance(default, value_type):
      raise CommandArgumentException(f"Invalid default type for argument ({name})")

    if value_type is bool and default is None:
      default = False

    if alias is None:
      alias = name

    self._args.update({
      name: CommandArgumentItem(name, value_type, item_help, default, alias)
    })

    self._alias_args.update({
      alias: CommandArgumentItem(name, value_type, item_help, default, alias)
    })
    return self

  def merge(self, builder):
    """
    :type builder CommandArgumentsBuilder
    """
    self._alias_args.update(builder._alias_args)
    self._args.update(builder._args)
    self._default_args.update(builder._default_args)

  @property
  def arguments(self) -> Dict[str, CommandArgumentItem]:
    return self._args

  @property
  def arguments_by_alias(self) -> Dict[str, CommandArgumentItem]:
    return self._alias_args

  @property
  def default_arguments(self) -> Dict[str, CommandArgumentItem]:
    return self._default_args

  @property
  def all_arguments(self) -> Dict[str, CommandArgumentItem]:
    return {**self._default_args, **self._alias_args}

  def add_default_argument(self, name: str, value_type: type, item_help: str, default: object = None):
    """
    :rtype CommandArgumentsBuilder
    """
    origin = get_origin(value_type)
    if origin is not None:
      value_type = origin

    if value_type not in self.__allowed_default_types:
      raise CommandArgumentException(f"Positional(default) argument could not have {value_type.__name__} type")

    if self.__is_default_arg_flag_used and default is None:
      raise CommandArgumentException(
        f"After defining first default Positional argument, rest should have default value too ({value_type.__name__})")
    elif default is not None:
      self.__is_default_arg_flag_used = True

      if not isinstance(default, value_type):
        raise CommandArgumentException("Invalid default type for argument".format(name))

    self._default_args.update({name: CommandArgumentItem(name, value_type, item_help, default=default)})
    return self

  @property
  def has_optional_default_argument(self) -> bool:
    return self.__is_default_arg_flag_used

  def get_default_argument(self, index: int) -> CommandArgumentItem:
    return list(self._default_args.values())[index]


class CommandMetaInfo(object):
  def __init__(self,
               name: str,
               item_help: str = "",
               default_sub_command: str = "",
               exec_with_child: bool = False,
               **kwargs):
    """
    :arg name Name of the command
    :arg item_help Help description of the command
    :arg default_sub_command In case if command have sub-commands, name of sub-command to execute on requesting base command
    :arg exec_with_child execute base command first, then sub-command. Valid to make command-wide checks.
    """
    self._name = name
    self._arguments = CommandArgumentsBuilder()
    self._help = item_help
    self._kwargs = kwargs
    self._default_sub_command = default_sub_command
    self._exec_with_child = exec_with_child

  @property
  def options(self) -> dict:
    return self._kwargs

  @property
  def name(self) -> str:
    return self._name

  @property
  def help(self) -> str:
    return self._help

  @property
  def default_sub_command(self) -> str:
    return self._default_sub_command

  @property
  def exec_with_child(self) -> bool:
    """
    Execute base command first, then sub-command. Valid to make command-wide checks

    Base command would be feeded with same commands as sub-command with disabled meta-info check
    """
    return self._exec_with_child

  @property
  def arguments(self) -> dict:
    return self._arguments.arguments

  @property
  def default_arguments(self):
    return self._arguments.default_arguments

  @property
  def arg_builder(self) -> CommandArgumentsBuilder:
    return self._arguments

  @classmethod
  def __convert_value_to_type(cls, value: str, _type: type):
    if _type is list and isinstance(value, str):
      return value.split(",")
    elif _type is bool and len(value) == 0:
      return True
    else:
      return _type(value)

  def transform_default_arguments(self, argv: list, fail_on_unknown: bool = False) -> dict:
    parsed_arguments_dict = {}
    default_arguments = list(self._arguments.default_arguments.values())
    expected_length = len(default_arguments)
    real_length = len(argv)

    default_args_count = len([item for item in default_arguments if item.default])

    if real_length == 0 and expected_length == 0:
      return parsed_arguments_dict
    elif not self._arguments.has_optional_default_argument \
      and (not argv or expected_length != real_length) \
      or (fail_on_unknown and real_length > expected_length):

      raise CommandArgumentException(f"Command require {expected_length} positional argument(s), found {real_length}")
    elif self._arguments.has_optional_default_argument and argv \
      and real_length < expected_length - default_args_count \
      or (fail_on_unknown and real_length > expected_length):

      raise CommandArgumentException(
        f"Command require {expected_length} or {expected_length - default_args_count} positional argument(s),"
        f" found {real_length}")

    for index in range(0, expected_length):
      arg_meta: CommandArgumentItem = default_arguments[index]
      try:
        arg = argv[index]
      except IndexError:
        arg = arg_meta.default

      try:
        if arg_meta.value_type:
          arg = self.__convert_value_to_type(arg, arg_meta.value_type)

        parsed_arguments_dict[arg_meta.name] = arg
      except (TypeError, ValueError):
        raise CommandArgumentException(
          f"Invalid argument type - expected {arg_meta.value_type.__name__}, got {type(arg).__name__}")

    return parsed_arguments_dict

  def transform_arguments(self, kwargs: dict, kwargs_injected: set, fail_on_unknown: bool = False):
    parsed_arguments_dict = {}
    arguments = self._arguments.arguments_by_alias

    if fail_on_unknown:
      unknown_commands = set(kwargs.keys()) - set(arguments.keys()) - kwargs_injected
      if unknown_commands:
        raise CommandArgumentException(f"Command contains unknown arguments  \"{', '.join(unknown_commands)}\"")

    for arg_name in arguments:
      if arg_name in kwargs_injected:
        continue

      arg_meta: CommandArgumentItem = arguments[arg_name]
      try:
        if arg_meta.value_type:
          arg = self.__convert_value_to_type(kwargs[arg_name], arg_meta.value_type)
        else:
          arg = kwargs[arg_name]
      except KeyError:
        if arg_meta.default is None:
          raise CommandArgumentException(f"Command require \"{arg_name}\" argument to be set")

        arg = arg_meta.default

      parsed_arguments_dict[arg_meta.name] = arg
    return parsed_arguments_dict


class CommandModule(object):
  def __init__(self, meta_info: CommandMetaInfo, classpath: str, import_name: str, entry_point: Callable, parent=None):
    """
    :type parent CommandModule
    """
    self.__name = meta_info.name
    self.__classpath = classpath
    self.__import_name = import_name
    self.__meta_info = meta_info
    self.__entry_point: Callable = entry_point
    self.__args = None
    self.__sub_commands: Dict[str, CommandModule] = {}
    self.__parent = parent

    if parent:
      self.__meta_info.arg_builder.merge(parent.__meta_info.arg_builder)

  def set_argument(self, args: list, kwargs: dict, injected_args: set = None,
                   fail_on_unknown=False,
                   skip_transform: bool = False):
    """

    :arg args list of default arguments
    :arg kwargs: list of kwargs
    :arg injected_args: list of added argumants
    :arg fail_on_unknown:  option to throw exception if unknown argument found
    :arg skip_transform:  skip argument transformation according to command meta. Usefull if the command is not
                          the last in the execution chain

    """
    if not injected_args:
      injected_args = set()

    if not skip_transform:
      args = self.__meta_info.transform_default_arguments(args, fail_on_unknown=fail_on_unknown)
      args.update(self.__meta_info.transform_arguments(kwargs, injected_args, fail_on_unknown=fail_on_unknown))

      f_args = self.entry_point_args

      if len(f_args) - len(set(f_args) & injected_args) != len(set(args.keys()) & set(f_args)):
        raise CommandArgumentException("Function \"{}\" from module {} doesn't implement all arguments in the"
                                       " signature or implements unknown definition".format(
                                        self.__entry_point.__name__, self.__classpath
                                       ))
    else:
      args = {
        '_': args
      }
      args.update(kwargs)
    self.__args = args

  def add_subcommand(self, cmds):
    """
    :type cmds List[CommandModule] or CommandModule
    """
    if not isinstance(cmds, list):
      cmds = [cmds]

    for cmd in cmds:
      if cmd.name in self.__sub_commands:
        continue

      self.__sub_commands[cmd.name] = cmd

  @property
  def parent(self):
    return self.__parent

  @property
  def subcommands(self):
    """
    :rtype List[CommandModule]
    """
    return list(self.__sub_commands.values())

  @property
  def subcommand_names(self) -> List[str]:
    return list(self.__sub_commands.keys())

  def get_subcommand(self, name: str):
    """
    :rtype CommandModule
    """
    return self.__sub_commands[name]

  @property
  def import_name(self):
    return self.__import_name

  @property
  def name(self) -> str:
    return self.__name

  @property
  def classpath(self) -> str:
    return self.__classpath

  @property
  def meta_info(self) -> CommandMetaInfo:
    return self.__meta_info

  @property
  def entry_point_args(self) -> tuple:
    return self.__entry_point.__code__.co_varnames[:self.__entry_point.__code__.co_argcount]

  def filter_injected_arguments(self, injected_arguments: dict = None) -> dict or None:
    if not injected_arguments:
      return None

    args = set(self.entry_point_args) & set(injected_arguments.keys())

    return {k: v for k, v in injected_arguments.items() if k in args}

  def __get_args(self, args: dict, injected_args: dict = None) -> dict:
    injected_args = self.filter_injected_arguments(injected_args)
    all_args = dict()
    if injected_args:
      all_args.update(injected_args)
    all_args.update(args)

    return all_args

  def execute(self,  injected_args: dict = None):
    self.__entry_point(**self.__get_args(self.__args, injected_args))

  async def execute_async(self, injected_args: dict = None):
    await self.__entry_point(**self.__get_args(self.__args, injected_args))

  def __str__(self):
    return f"Module: {self.__import_name}, Meta: {self.meta_info.name}, Sub Commands: {len(self.__sub_commands)}"


class CommandModules(object):
  class CommandListView(object):
    def __init__(self, lst: list):
      self._l = lst
      self._i = 0
      self._len = len(lst)

    def __next__(self):
      if self._i < self._len:
        try:
          return self._l[self._i]
        finally:
          self._i += 1
      else:
        raise StopIteration()

  def __init__(self, entry_point: str):
    self.__modules: Dict[str, CommandModule] = {}
    self.__entry_point = entry_point
    self.__required_module_fields = {"__module__", entry_point}
    self.__req_module_fields_count = len(self.__required_module_fields)

  def __getitem__(self, item: str) -> CommandModule:
    try:
      return self.__modules[item]
    except KeyError:
      raise NoCommandException(item, f"No such command '{item}' found, unable to continue")

  def __len__(self):
    return len(self.__modules)

  def __contains__(self, item: str):
    return item in self.__modules

  def __iter__(self) -> CommandListView:
    return CommandModules.CommandListView(list(self.__modules.values()))

  @property
  def commands(self):
    return list(self.__modules.keys())

  def get_command_by_meta_name(self, name: str) -> Optional[CommandModule]:
    for cmd in self.__modules.values():
      if cmd.meta_info.name == name:
        return cmd

    return None

  def __create_command(self, classpath: str, cmd_filename: str,
                       parent: CommandModule = None) -> Optional[CommandModule]:

    m = __import__(f"{classpath}.{cmd_filename}", fromlist=classpath)
    m_dict = m.__dict__
    meta_info = m_dict["__module__"]
    if not isinstance(meta_info, CommandMetaInfo):
      return

    if self.__req_module_fields_count == len(self.__required_module_fields & set(m_dict.keys())):
      return CommandModule(
        classpath=m.__name__,
        import_name=cmd_filename,
        meta_info=meta_info,
        entry_point=m_dict[self.__entry_point],
        parent=parent
      )

    return None

  def add(self, classpath: str, command_filename: str, sub_commands: List[str] = ()):
    # if command is an directory, we need to import <command>\__init__.py instead of folder
    import_name = f"{command_filename}.__init__" if sub_commands else command_filename
    command_module: CommandModule = self.__create_command(classpath, import_name)  # [base_command]

    if command_module.name in self.commands:
      prev_command: CommandModule = self.get_command_by_meta_name(command_module.meta_info.name)
      if prev_command is None:
        raise ValueError(f"Conflicting command definition for '{command_filename}'")
      raise ValueError(f"""
Conflicting command definitions detected:
=========================================
 Import 1 classpath: {prev_command.classpath} -> {prev_command.import_name} : #{prev_command.meta_info.name}
 Import 2 classpath: {command_module.classpath} -> {command_module.import_name} : #{command_module.meta_info.name}
""")

    if sub_commands:
      _sub_commands = []
      for sub_command in sub_commands:
        _class_path = f"{classpath}.{command_filename}"
        _command_obj: Optional[CommandModule] = None
        if isinstance(sub_command, tuple):  # [base_command] {sub_command} {sub_sub_command}
          _name, _subcmds = sub_command
          _command_obj = self.__create_command(_class_path, f"{_name}.__init__", command_module)
          _command_obj.add_subcommand([
            self.__create_command(f"{_class_path}.{_name}", _subcmd, _command_obj)
            for _subcmd in _subcmds
          ])
        else:  # [base_command] {sub_command}
          _command_obj = self.__create_command(_class_path, sub_command, command_module)

        _sub_commands.append(_command_obj)

      command_module.add_subcommand(_sub_commands)

    self.__modules[command_module.meta_info.name] = command_module

  def inject(self, module: CommandModule):
    if not module:
      return
    self.__modules[module.meta_info.name] = module
