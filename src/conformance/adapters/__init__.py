"""One adapter per tool. Order here is the order of the report's tool table."""

from .base import Adapter, Context, Probe
from .cloud_native import CloudNative
from .copc import Copc
from .docs import Docs
from .gpio import Gpio
from .hosting import Hosting
from .parquet_footer import ParquetFooter
from .pmtiles import Pmtiles
from .portolan_cli import PortolanCli
from .rashid import Rashid
from .rio_cogeo import RioCogeo
from .stac_check import StacCheck
from .stac_validator import StacValidator
from .zarr import Zarr

ALL_ADAPTERS: list[type[Adapter]] = [
    Rashid,
    PortolanCli,
    StacValidator,
    StacCheck,
    Gpio,
    ParquetFooter,
    RioCogeo,
    Pmtiles,
    Zarr,
    Copc,
    CloudNative,
    Hosting,
    Docs,
]

__all__ = ["ALL_ADAPTERS", "Adapter", "Context", "Probe"]
