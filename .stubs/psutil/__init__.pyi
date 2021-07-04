# THESE STUBS WERE MADE BY ME BECAUSE AUTO GENERATION
# 1) WILL GENERATE FOR CURRENT OS, NOT ALL OSES
# 2) AUTO GENERATION MAINLY DOESNT HAVE TYPEHINTS

from collections import namedtuple
from typing import Dict, Generator, List, Optional, TypedDict

from ._common import sdiskpart, sdiskusage, snetio, suser

LINUX: bool
WINDOWS: bool

# -------------------------------------------------------------------------------------------------
# these are NOT representive of the actual code as the namedtuped changes based on the os
# this cog uses attributes that are common and used i the cog
# most of these are also in _common or the oses file so :awesome:
scputimes = namedtuple("scputimes", ["user", "idle", "system"])
scpufreq = namedtuple("scpufreq", ["current", "min", "max"])
svmem = namedtuple("svmem", ["total", "available", "percent", "used"])
sswap = namedtuple("sswap", ["total", "used", "free", "percent"])
shwtemp = namedtuple("shwtemp", ["label", "current", "high", "critical"])
sfan = namedtuple("sfan", ["label", "current"])
pmem = namedtuple("pmem", ["rss", "vms"])
pfullmem = namedtuple("pfullmem", ["rss", "vms", "swap"])

class ProcInfo(TypedDict):
    status: str
    username: str

class Process:
    info: ProcInfo
    pid: int
    def oneshot(self): ...
    def memory_info(self) -> pmem: ...
    def memory_full_info(self) -> pfullmem: ...
    def memory_percent(self, memtype: str = None) -> float: ...
    def cpu_percent(self, interval: bool = None) -> float: ...

# -------------------------------------------------------------------------------------------------
# some of these can return others but for this cog will only return one thing due to args used
def cpu_percent(interval: bool = None, percpu: bool = False) -> List[float]: ...
def cpu_times(percpu: bool = False) -> scputimes: ...
def cpu_freq(percpu: bool = False) -> List[scpufreq]: ...
def cpu_count(logical: bool = True) -> int: ...
def boot_time() -> float: ...
def virtual_memory() -> svmem: ...
def swap_memory() -> sswap: ...
def sensors_temperatures(fahrenheit: bool = False) -> Dict[str, List[shwtemp]]: ...
def sensors_fans() -> Dict[str, List[sfan]]: ...
def users() -> List[suser]: ...
def disk_partitions(all: bool = False) -> List[sdiskpart]: ...
def disk_usage(path: str) -> sdiskusage: ...
def process_iter(
    attars: Optional[list] = None, ad_value=None
) -> Generator[Process, Process, Process]: ...
def net_io_counters(permic=..., nowrap=...) -> snetio: ...