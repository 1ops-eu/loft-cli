from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("loft-cli-core")
except PackageNotFoundError:
    __version__ = "unknown"
