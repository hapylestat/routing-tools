from modules.apputils.discovery import CommandsDiscovery

discovery = CommandsDiscovery(__file__, __name__).collect()
