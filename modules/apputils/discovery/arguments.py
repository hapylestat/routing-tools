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

from typing import List


class CommandLineOptions(object):

  def __init__(self, *argv: List[str]):
    self.__argv = argv if argv else sys.argv[1:]
    self.__file_path = os.path.abspath(sys.argv[0])
    self.__filename = os.path.basename(self.__file_path)
    self.__directory = os.path.dirname(self.__file_path)
    self.__args = []
    self.__kwargs = {}

    self._parse_command_line()

  def _parse_command_line(self):
    curr_command = None

    def parse_full_command(_command):
      if "=" in curr_command:
        _cmd, _, val = curr_command.partition("=")
        self.__kwargs[_cmd] = val
        _command = None

      return _command

    for cmd in self.__argv:
      if curr_command and (cmd.startswith("--") or cmd.startswith("-")):
        self.kwargs[curr_command] = ""
        curr_command = None

      if cmd.startswith("--"):
        curr_command = cmd[2:]
        if "=" in curr_command:
          curr_command = parse_full_command(curr_command)
        continue
      elif cmd.startswith("-"):
        curr_command = cmd[1:]
        continue

      if curr_command:
        self.__kwargs[curr_command] = cmd
        curr_command = None
        continue
      else:
        self.__args.append(cmd)

    if curr_command:
      self.kwargs[curr_command] = ""

  @property
  def filename(self):
    return self.__filename

  @property
  def directory(self):
    return self.__directory

  @property
  def argv(self):
    return self.__argv

  @property
  def args(self):
    return self.__args

  @property
  def kwargs(self):
    return self.__kwargs
