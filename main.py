from __future__ import print_function

import os
import commands

__app_name__ = "router-tools"
__app_version__ = "v0.0"
__my_root_dir__ = os.path.dirname(__file__)
__properties_file__ = "conf.json"


def main():
  commands.discovery.start_application(
    default_command="default",
    kwargs={
      "root_path": __my_root_dir__
    }
  )


if __name__ == '__main__':
  main()
