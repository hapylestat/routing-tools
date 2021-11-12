#!/usr/bin/env python3

# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import codecs
import os
import sys
import re
from typing import List

# needed due to claims of importing distutils before setuptools
import setuptools
from apputils_setup import AppUtilsCommand
from distutils.command.install import install
from setuptools import find_packages, setup
from wheel.bdist_wheel import bdist_wheel

"""
HOW TO BUILD PROJECT
=====================
From the project root:
  python3 setup.py bdist_wheel [--version=vX.X] [--update-link=link to GitHub API Releases landing]

  Example of update-link: https://api.github.com/repos/hapylestat/openstack_cli/releases

  The output wheel would be available in dist folder
"""

here = os.path.abspath(os.path.dirname(__file__))


def read(*parts):
  # auto-detects file encoding
  with codecs.open(os.path.join(here, *parts), 'r') as fp:
    return fp.read()


def find_tag(tags: str or List[str], *file_paths: str, use_import: bool = False):
  result_list: List[str] = []
  if isinstance(tags, str):
    tags = [tags]

  if use_import:
    import importlib
    _path = ".".join(file_paths)
    if _path.endswith(".py"):
      _path = _path[:-3]
    m = importlib.import_module(_path)

    for t in tags:
      if f"__{t}__" in m.__dict__:
        result_list.append(m.__dict__[f"__{t}__"])
  else:
    tag_file = read(*file_paths)
    for t in tags:
      tag_match = re.search(
        rf"^__{t}__ = ['\"]([^'\"]*)['\"]",
        tag_file,
        re.M,
      )
      if tag_match:
        result_list.append(tag_match.group(1))

  if len(result_list) != len(tags):
    raise RuntimeError(f"Unable to find some tag from the list: {', '.join(tags)}")

  return result_list


def load_requirements():
  data = read("requirements.txt")
  return data.split("\n")


def get_git_hash() -> str:
  base_path = ".git"
  head_path = os.path.join(base_path, "HEAD")
  if not os.path.exists(head_path):
    return "dev-build"
  f = read(head_path)

  if ":" not in f:   # in case of tag, HEAD would contains de-attached tree with commit ID
    return f.strip()

  _, _, ref_path = f.partition(":")

  ref_path = os.path.join(base_path, ref_path.strip())
  if not os.path.exists(ref_path):
    return "dev-build"

  f = read(ref_path)
  return f.strip()


app_name, app_version, prop_file = find_tag(
  ["app_name", "app_version", "properties_file"],
  "main.py",
  use_import=False
)
git_hash = get_git_hash()
update_link = ""

for arg in sys.argv:
  if "--version" in arg:
    _, _, app_version = arg.partition("=")
    break


class MyWheel(bdist_wheel):
  user_options = install.user_options + [
    ('update-link=', None, "Specify path to releases GITHUB API"),
    ('version=', None, "Application version in format 'vX.X'")
  ]

  def initialize_options(self) -> None:
    bdist_wheel.initialize_options(self)
    self.update_link = None
    self.version = None

  def finalize_options(self) -> None:
    bdist_wheel.finalize_options(self)

  def run(self):
    global update_link, app_version
    if self.update_link is not None:
      update_link = self.update_link

    if self.version is not None:
      app_version = self.version
    bdist_wheel.run(self)


class MyInstall(install):

  def run(self):
    install.run(self)
    if "install_data" in self.__dict__:
      import json
      out_dir, _, _ = self.install_data.rpartition("-")
      os.makedirs(out_dir, exist_ok=True)
      with open(os.path.join(out_dir, prop_file), "w+") as f:
        data = {
          "app_name": app_name,
          "app_version": app_version,
          "commit_hash": git_hash,
          "update_src": update_link
        }
        json.dump(data, f)
    else:
      raise RuntimeError("Unable to locate data directory")


setup(
  name=app_name,
  version=app_version,
  description="OpenStack VM orchestrator",
  long_description="OpenStack VM orchestrator",
  license='ASF',
  classifiers=[
    "Programming Language :: Python",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.7",
    "Programming Language :: Python :: 3.8",
  ],
  author='hapylestat@apache.org',
  package_dir={"": "src"},
  packages=find_packages(
    where="src",
    exclude=["contrib", "docs", "tests*", "tasks"],
  ),
  cmdclass={
    "install": MyInstall,
    "bdist_wheel": MyWheel,
    "apputils": AppUtilsCommand
  },
  install_requires=load_requirements(),
  entry_points={
    "console_scripts": [
      "osvm=openstack_cli.core:main_entry",
      ],
  },
  zip_safe=True,
  python_requires='>=3.7'
)
