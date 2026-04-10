from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("loft-cli-core")
except PackageNotFoundError:
    __version__ = "unknown"
