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

from distutils.cmd import Command
from distutils.dir_util import copy_tree
from shutil import copyfile


class AppUtilsCommand(Command):
  description = "Manage AppUtils libs integration to the application"
  user_options = []
  _apputils_git = "https://github.com/hapylestat/apputils.git"
  _requirements_file = "apputils-requirements.txt"
  _name = "apputils"

  def initialize_options(self) -> None:
    pass

  def finalize_options(self) -> None:
    pass

  def run(self):
    import os
    current_path = os.path.dirname(__file__)
    git_path = f"{current_path}{os.sep}build{os.sep}external-libs"
    repo_path = f"{git_path}{os.sep}{self._name}"
    git_rel_path = f"src{os.sep}modules{os.sep}{self._name}"

    print("Looking for requirements....")

    if not os.path.exists(f"{current_path}{os.sep}{self._requirements_file}"):
      print(f"Error!!! No {self._requirements_file} found at {current_path}")
      return

    with open(f"{current_path}{os.sep}{self._requirements_file}", "r") as f:
      modules = [line.strip("\n").strip() for line in f.readlines() if line and not line.startswith("#")]
      rel_modules_install_path = f"{modules[:1][0]}{os.sep}{self._name}"
      modules = modules[1:]

    if not modules:
      print("Error!!! No modules to be integrated")
      return

    print(f"Modules to integrate: {', '.join(modules)}")

    if os.path.exists(repo_path):
      print("Trying to update existing repository....")
      cur_dir = os.path.abspath(".")
      os.chdir(repo_path)
      try:
        os.system("git reset --hard HEAD")
        os.system("git pull")
      finally:
        os.chdir(cur_dir)
    else:
      print(f"Creating directory for checkout {git_path}")
      os.makedirs(git_path, exist_ok=True)
      os.system(f"git clone {self._apputils_git} {repo_path}")

    git_modules_path = os.path.join(repo_path, git_rel_path)
    if not os.path.exists(git_modules_path):
      print(f"Unable to access modules location: {git_modules_path}")

    print("Verifying modules availability:")
    git_available_modules = os.listdir(git_modules_path)
    for module in modules:
      if module in git_available_modules:
        print(f"  {module} ... OK")
      else:
        print(f"  {module} ... NO FOUND")
        return

    old_modules_path = os.path.abspath(os.path.join(current_path, rel_modules_install_path))
    if not os.path.exists(old_modules_path):
      print(f"Preparing modules folder '{old_modules_path}' ...")
      os.makedirs(old_modules_path)

    old_installed_modules = set(os.listdir(old_modules_path)) & set(modules)
    print("Removing old installed modules:")
    for module in old_installed_modules:
      print(f"  Removing old module {module} ....")

    print("Installing requested modules:")
    if not os.path.exists(os.path.join(old_modules_path, "__init__.py")):
      copyfile(os.path.join(git_modules_path, "__init__.py"), os.path.join(old_modules_path, "__init__.py"))

    for module in modules:
      copy_from_path = os.path.join(git_modules_path, module)
      copy_to_path = os.path.join(old_modules_path, module)
      print(f"  {module}...", end="")
      try:
        copy_tree(copy_from_path, copy_to_path, verbose=0)
        print("OK")
      except Exception as e:
        print("FAIL")
        raise e
