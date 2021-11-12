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

from typing import List

from . import CommandMetaInfo, CommandModule,CommandLineOptions, CommandModules


def __generate_help(command: CommandModule) -> str:
  pass

START_SPACING: str = " " * 5

def format_help_description(description: str, max_arg_len: int) -> str:
  if "\n" not in description:
    return description
  description_lines = description.split("\n")
  new_description: List[str] = [description_lines[0]]
  new_description += [f"{START_SPACING}{' ' * (max_arg_len + 3)}{line}" for line in description_lines[1:]]
  return "\n".join(new_description)


def generate_command_help(fn_spacing:str, command: CommandModule, show_subcommands:bool = True) -> str:
  endl = "\n"
  meta: CommandMetaInfo = command.meta_info
  _spacing =" " * len(fn_spacing)
  if not meta:
    return ""

  args = []
  arg_details = []
  sub_command_details = []
  filename_prefix = "▪" if show_subcommands else "-"
  subcommands = f"[{'|'.join(command.subcommand_names)}]" if command.subcommand_names and show_subcommands else ""

  try:
    max_arg_len: int = len(max(meta.arg_builder.all_arguments.keys(), key=len))
  except ValueError:
    max_arg_len: int = 0

  for key, value in meta.arg_builder.default_arguments.items():
    additional_spacing = " " * (max_arg_len - len(key))
    default_str = f"(Default: {value.default})" if value.default else ""
    args.append(f"[{key}]" if value.has_default else key)
    arg_details.append(f"{_spacing} {key}{additional_spacing} - {format_help_description(value.item_help, max_arg_len)} {default_str}")

  for key, value in meta.arg_builder.arguments_by_alias.items():
    additional_spacing = " " * (max_arg_len - len(key))
    default_str = f"(Default: {value.default})" if value.default else ""
    args.append(f"[--{key}]" if value.has_default else f"--{key}")
    arg_details.append(f"{_spacing} {key}{additional_spacing} - {format_help_description(value.item_help, max_arg_len)} {default_str}")

  return """
{filename} {cmd} {subcommands} {args}
{cmd_help}{arg_details}
        """.format(
   filename=_spacing[:-1] + filename_prefix,
   cmd=command.name,
   cmd_help=f"{_spacing} {meta.help}",
   subcommands=subcommands,
   args=" ".join(args),
   arg_details=  f"{endl*2}{endl.join(arg_details)}" if arg_details else ""
 )


def generate_help(modules: CommandModules, options: CommandLineOptions, subcommand: str = "", subcmd_cmd: str = ""):
  filename = options.filename
  end_line = "\n"
  help_str = f"Usage:{end_line}"

  command_list = modules.commands if not subcommand else [subcommand]

  for command in command_list:
    cmd = modules[command]
    cmd_meta: CommandMetaInfo = cmd.meta_info
    subcommands = f"[{'|'.join(cmd.subcommand_names)}]" if cmd.subcommand_names else ""

    if not cmd_meta:
      continue

    help_str += f"""
{filename} {cmd.name} {subcommands}
{START_SPACING}{cmd.meta_info.help}
"""
    help_str += generate_command_help(filename, cmd, show_subcommands=False)

    subcommands = [cmd.get_subcommand(subcmd_cmd)] if subcmd_cmd and subcmd_cmd in cmd.subcommand_names else cmd.subcommands

    for sub in subcommands:
      help_str += generate_command_help(" " * len(filename), sub)
      if not sub.subcommands:
        continue

      for subsub in sub.subcommands:
        help_str += generate_command_help(" " * len(filename) + " " * len(sub.name), subsub, show_subcommands=False)

  return help_str
