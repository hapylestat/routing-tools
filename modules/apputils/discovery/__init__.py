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

import os
import sys
from typing import List, Iterable, Tuple

from .arguments import CommandLineOptions
from .commands import CommandMetaInfo, NoCommandException, CommandArgumentException, \
  CommandModules, CommandModule, NotImplementedCommandException


class CommandsDiscovery(object):
  def __init__(self,
               discovery_location_path: str,
               module_class_path: str,
               file_pattern: str = "",
               module_main_fname: str = "__init__"):

    self._discovery_location_path = discovery_location_path
    self._module_main_fname = module_main_fname
    self._file_pattern = file_pattern
    self._options: CommandLineOptions = CommandLineOptions()

    if os.path.isfile(self._discovery_location_path):
      self._search_dir = os.path.dirname(os.path.abspath(self._discovery_location_path))
    else:
      self._search_dir = self._discovery_location_path

    self._module_class_path = module_class_path
    self._modules = CommandModules(entry_point=module_main_fname)

  @property
  def search_dir(self) -> str:
    return self._search_dir

  @classmethod
  def __collect_modules(cls, path: str, pattern: str = "") -> Iterable[Tuple[str, str, bool, str]]:
    exclude_list = ("pyc", "__init__.py", "__pycache__")
    for name in os.listdir(path):
      full_name = os.path.join(path, name)
      is_dir = os.path.isdir(full_name)
      if name.endswith(exclude_list):
        continue

      if pattern and not name.endswith(pattern):
        continue

      # command, file/dir name, is_dir, full_name
      yield name.partition(".")[0], name, is_dir, full_name

  def collect(self):
    """
    :rtype CommandsDiscovery
    """
    for command, name, is_dir, full_name in self.__collect_modules(self._search_dir, self._file_pattern):
      if command in self._modules:
        continue

      sub_commands: List[str or Tuple[str, List[str]]] = []
      if is_dir:  # currently supporting only 2 levels of sub-command
        for _command, _name, _is_dir, _full_name in self.__collect_modules(full_name, self._file_pattern):
          if _is_dir:
            _sub = [item[0] for item in self.__collect_modules(_full_name, self._file_pattern) if not item[2]]
            sub_commands.append((_command, _sub))
          else:
            sub_commands.append(_command)
      self._modules.add(self._module_class_path, command, sub_commands)

    return self

  def __inject_help_command(self):
    from .help import generate_help
    meta = CommandMetaInfo("help", "this command")
    meta.arg_builder \
      .add_default_argument("subcommand", str, "name of the command to show help for", default="@") \
      .add_default_argument("subcommand_command", str, "Command name of the subcommand", default="@")

    def _print_help(subcommand: str, subcommand_command: str):
      sys.stdout.write(generate_help(self._modules, self._options, subcommand, subcommand_command))

    self._modules.inject(CommandModule(meta, "discovery", "__internal__", _print_help))

  @property
  def command_name(self) -> str or None:
    return self._options.args[0] if self._options.args else None

  @property
  def command_arguments(self) -> List[str]:
    return self._options.args[1:] if self._options.args else []

  @property
  def kwargs_name(self) -> List[str]:
    return list(self._options.kwargs.keys())

  def _get_command(self, injected_args: dict = None, fail_on_unknown: bool = False) -> List[CommandModule]:
    if not self._options.args:
      raise NoCommandException(None, "No command passed, unable to continue")

    command_chain: List[CommandModule] = []
    command: CommandModule = self._modules[self._options.args[0]]  # [command name]
    command_args = self._options.args[1:]

    # Process all command in sub-command chain [command1] [command2] .. [last command]
    while command_args:
      if command_args[0] not in command.subcommand_names:
        break
      command_name = command_args[0]
      command_args = command_args[1:]

      if command.meta_info.exec_with_child:
        command_chain.append(command)
      command = command.get_subcommand(command_name)

    # Now process the last command "default sub-command" forward if present
    if command.meta_info.default_sub_command and \
      command.meta_info.default_sub_command in command.subcommand_names:

      if command.meta_info.exec_with_child:
        command_chain.append(command)
      command = command.get_subcommand(command.meta_info.default_sub_command)

    command_chain.append(command)
    inj_args = set(injected_args.keys()) if injected_args else set()
    for _command in command_chain:
      _require_transform = True if _command == command else False
      _command.set_argument(command_args, self._options.kwargs, inj_args, fail_on_unknown, not _require_transform)

    return command_chain

  def execute_command(self, injected_args: dict = None):
    try:
      commands = self._get_command(injected_args)
      for command in commands:
        command.execute(injected_args)
    except CommandArgumentException as e:
      raise NoCommandException(None, f"Application arguments exception: {str(e)}\n")

  async def execute_command_async(self, injected_args: dict = None):
    try:
      commands = self._get_command()
      for command in commands:
        await command.execute_async(injected_args)
    except CommandArgumentException as e:
      raise NoCommandException(None, f"Application arguments exception: {str(e)}\n")

  def __get_modules_from_args(self) -> Tuple[str, str]:
    args = self._options.args
    if len(args) == 0:
      return "", ""

    cmd = self._modules.get_command_by_meta_name(args[0])
    if cmd is None:
      return "", ""

    if len(args) == 1 or args[1] not in cmd.subcommand_names:
      return cmd.name, ""

    return cmd.name, args[1]

  def start_application(self, kwargs: dict = None, default_command: str = ""):
    from .help import generate_help

    self.__inject_help_command()
    try:
      cmd_list = self._get_command(injected_args=kwargs, fail_on_unknown=True)
      for command in cmd_list:
        command.execute(injected_args=kwargs)
    except NotImplementedCommandException:
      sys.stdout.write(generate_help(self._modules, self._options, *self.__get_modules_from_args()))
    except NoCommandException as e:
      if default_command:
        _argv = [default_command] + self._options.args + [f"--{k}={v}" for k, v in self._options.kwargs.items()]
        self._options = CommandLineOptions(*_argv)
        self.start_application(kwargs)
        return
      elif e.command_name:
        sys.stdout.write(generate_help(self._modules, self._options))
      else:
        sys.stdout.write("No command provided, use 'help' to check the list of available commands")
    except CommandArgumentException as e:
      sys.stdout.write(f"Application arguments exception: {str(e)}\n")
