import asyncio
import datetime
from typing import Dict, List, TypedDict, Union

import discord
import psutil
from redbot.core.utils import AsyncIter
from redbot.core.utils.chat_formatting import box as cf_box
from redbot.core.utils.chat_formatting import humanize_number, humanize_timedelta, pagify
from tabulate import tabulate
from vexcogutils.chat import humanize_bytes

ZERO_WIDTH = "\u200b"


def box(text: str) -> str:
    """Box up text as toml. Will not return more than 1024 chars (embed value limit)"""
    if len(text) > 1010:
        text = list(pagify(text, page_length=1024, shorten_by=12))[0]
        text += "\n..."
    return cf_box(text, "toml")


def up_for() -> float:
    now = datetime.datetime.utcnow().timestamp()
    return now - psutil.boot_time()


def _hum(num: Union[int, float]) -> str:
    """Round a number, then humanize."""
    return humanize_number(round(num))


def finalise_embed(e: discord.Embed) -> discord.Embed:
    """Make embeds look nicer - limit to two columns and set the footer to boot time"""
    # needed because otherwise they are otherwise too squashed together so tabulate doesn't work
    # doesn't look great on mobile but is fully bearable, more than ugly text wrapping

    # oh, don't mention the ugly code please :P
    # it works...
    emb = e.to_dict()
    fields: List[dict] = emb["fields"]
    if len(fields) > 2:  # needs multi rows
        data: List[List[dict]] = []
        temp = []
        for field in fields:
            temp.append(field)
            if len(temp) == 2:
                data.append(temp)
                temp = []
        if len(temp) != 0:  # clear up stragglers
            data.append(temp)

        empty_field = {"inline": True, "name": ZERO_WIDTH, "value": ZERO_WIDTH}
        fields = []
        row: List[dict]
        for row in data:
            while len(row) < 3:
                row.append(empty_field)
            fields.extend(row)

    # else it's 2 or less columns so doesn't need special treatment
    emb["fields"] = fields
    e = discord.Embed.from_dict(emb)

    # and footer is just a nice touch, thanks max for the idea of uptime there
    uptime = humanize_timedelta(seconds=up_for())
    boot_time = datetime.datetime.utcfromtimestamp(psutil.boot_time())
    e.set_footer(text=f"Uptime: {uptime} | Up since:")
    e.timestamp = boot_time

    return e


async def get_cpu() -> Dict[str, str]:
    """Get CPU metrics"""
    psutil.cpu_percent()
    await asyncio.sleep(1)
    percent = psutil.cpu_percent(percpu=True)
    time = psutil.cpu_times()
    freq = psutil.cpu_freq(percpu=True)
    cores = psutil.cpu_count()

    if psutil.LINUX:
        data = {"percent": "", "freq": "", "freq_note": "", "time": ""}
        for i in range(cores):
            data["percent"] += f"[Core {i}] {percent[i]} %\n"
            ghz = round((freq[i].current / 1000), 2)
            data["freq"] += f"[Core {i}] {ghz} GHz\n"
    else:
        data = {"percent": "", "freq": "", "freq_note": " (nominal)", "time": ""}
        for i in range(cores):
            data[
                "percent"
            ] += f"[Core {i}] {percent[i]} % \n"  # keep extra space here, for special case,
            # tabulate removes it
        ghz = round((freq[0].current / 1000), 2)
        data["freq"] = f"{ghz} GHz\n"  # blame windows

    data["time"] += f"[Idle]   {_hum(time.idle)} seconds\n"
    data["time"] += f"[User]   {_hum(time.user)} seconds\n"
    data["time"] += f"[System] {_hum(time.system)} seconds\n"
    data["time"] += f"[Uptime] {_hum(up_for())} seconds\n"

    return data


async def get_mem() -> Dict[str, str]:
    """Get memory metrics"""
    physical = psutil.virtual_memory()
    swap = psutil.swap_memory()

    data = {"physical": "", "swap": ""}

    data["physical"] += f"[Percent]   {physical.percent} %\n"
    data["physical"] += f"[Used]      {humanize_bytes(physical.used, 2)}\n"
    data["physical"] += f"[Available] {humanize_bytes(physical.available, 2)}\n"
    data["physical"] += f"[Total]     {humanize_bytes(physical.total, 2)}\n"

    data["swap"] += f"[Percent]   {swap.percent} %\n"
    data["swap"] += f"[Used]      {humanize_bytes(swap.used, 2)}\n"
    data["swap"] += f"[Available] {humanize_bytes(swap.free, 2)}\n"
    data["swap"] += f"[Total]     {humanize_bytes(swap.total, 2)}\n"

    return data


async def get_sensors(fahrenheit: bool) -> Dict[str, str]:
    """Get metrics from sensors"""
    temp = psutil.sensors_temperatures(fahrenheit)
    fans = psutil.sensors_fans()

    data = {"temp": "", "fans": ""}

    unit = "°F" if fahrenheit else "°C"

    t_data = []
    for t_k, t_v in temp.items():
        for t_item in t_v:
            name = t_item.label or t_k
            t_data.append([f"[{name}]", f"{t_item.current} {unit}"])
    data["temp"] = tabulate(t_data, tablefmt="plain") or "No temperature sensors found"

    f_data = []
    for f_k, f_v in fans.items():
        for f_item in f_v:
            name = f_item.label or f_k
            f_data.append([f"[{name}]", f"{f_item.current} RPM"])
    data["fans"] = tabulate(f_data, tablefmt="plain") or "No fan sensors found"

    return data


async def get_users(embed: bool) -> Dict[str, str]:
    """Get users connected"""
    users = psutil.users()

    e = "`" if embed else ""

    data = {}

    for user in users:
        data[f"{e}{user.name}{e}"] = "[Terminal]  {}\n".format(user.terminal or "Unknown")
        started = datetime.datetime.fromtimestamp(user.started).strftime("%Y-%m-%d at %H:%M:%S")
        data[f"{e}{user.name}{e}"] += f"[Started]   {started}\n"
        if not psutil.WINDOWS:
            data[f"{e}{user.name}{e}"] += f"[PID]       {user.pid}"

    return data


class PartitionData(TypedDict):
    part: psutil._common.sdiskpart
    usage: psutil._common.sdiskusage


async def get_disk(embed: bool) -> Dict[str, str]:
    """Get disk info"""
    partitions = psutil.disk_partitions()
    partition_data: Dict[str, PartitionData] = {}
    # that type hint was a waste of time...

    for partition in partitions:
        try:
            partition_data[partition.device] = {
                "part": partition,
                "usage": psutil.disk_usage(partition.mountpoint),
            }
        except Exception:
            continue

    e = "`" if embed else ""

    data = {}

    for k, v in partition_data.items():
        total_avaliable = (
            f"{humanize_bytes(v['usage'].total)}"
            if v["usage"].total > 1073741824
            else f"{humanize_bytes(v['usage'].total)}"
        )
        data[f"{e}{k}{e}"] = f"[Usage]       {v['usage'].percent} %\n"
        data[f"{e}{k}{e}"] += f"[Total]       {total_avaliable}\n"
        data[f"{e}{k}{e}"] += f"[Filesystem]  {v['part'].fstype}\n"
        data[f"{e}{k}{e}"] += f"[Mount point] {v['part'].mountpoint}\n"

    return data


async def get_proc() -> Dict[str, str]:
    """Get process info"""
    processes = psutil.process_iter(["status", "username"])
    status = {"sleeping": 0, "idle": 0, "running": 0, "stopped": 0}

    async for process in AsyncIter(processes):  # v slow on windows
        try:
            status[process.info["status"]] += 1
        except KeyError:
            continue

    sleeping = status["sleeping"]
    idle = status["idle"]
    running = status["running"]
    stopped = status["stopped"]
    total = sleeping + idle + running + stopped

    data = {"statuses": f"[Running]  {running}\n"}
    if psutil.WINDOWS:
        data["statuses"] += f"[Stopped]  {stopped}\n"
        data["statuses"] += f"[Total]    {total}\n"
    else:
        data["statuses"] += f"[Idle]     {idle}\n"
        data["statuses"] += f"[Sleeping] {sleeping}\n"
        if status["stopped"]:  # want to keep it at 4 rows
            data["statuses"] += f"[Stopped]  {stopped}\n"
        else:
            data["statuses"] += f"[Total]    {total}\n"

    return data


async def get_net() -> Dict[str, str]:
    """Get network stats. May have reset from zero at some point."""
    net = psutil.net_io_counters()

    data = {"counters": ""}
    data["counters"] += f"[Bytes sent]   {humanize_bytes(net.bytes_sent)}\n"
    data["counters"] += f"[Bytes recv]   {humanize_bytes(net.bytes_recv)}\n"
    data["counters"] += f"[Packets sent] {net.packets_sent}\n"
    data["counters"] += f"[Packets recv] {net.packets_recv}\n"

    return data


async def get_uptime() -> Dict[str, str]:
    """Get uptime info"""
    boot_time = datetime.datetime.fromtimestamp(psutil.boot_time())

    friendly_boot_time = boot_time.strftime("%b %d, %H:%M:%S UTC")
    friendly_up_for = humanize_timedelta(timedelta=datetime.datetime.utcnow() - boot_time)

    data = {"uptime": ""}

    data["uptime"] += f"[Boot time] {friendly_boot_time}\n"
    data["uptime"] += f"[Up for]    {friendly_up_for}\n"

    return data