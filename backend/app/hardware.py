"""Read-only local hardware snapshot; no administrative/WMI access required."""

import ctypes
import os
import platform
import shutil
from pathlib import Path


def snapshot():
    result = {
        "os": platform.platform(),
        "logical_cpus": os.cpu_count(),
        "storage_free_gib": round(shutil.disk_usage(Path(__file__).resolve()).free / 2**30, 2),
    }
    if os.name == "nt":
        import winreg

        class Memory(ctypes.Structure):
            _fields_ = [("length", ctypes.c_ulong), ("load", ctypes.c_ulong)] + [
                (name, ctypes.c_ulonglong)
                for name in (
                    "total_phys",
                    "avail_phys",
                    "total_page",
                    "avail_page",
                    "total_virtual",
                    "avail_virtual",
                    "avail_extended",
                )
            ]

        memory = Memory()
        memory.length = ctypes.sizeof(memory)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(memory)):
            result.update(
                ram_gib=round(memory.total_phys / 2**30, 2),
                available_ram_gib=round(memory.avail_phys / 2**30, 2),
                memory_load_percent=memory.load,
            )
        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0"
        ) as key:
            result["cpu"] = winreg.QueryValueEx(key, "ProcessorNameString")[0].strip()
    return result
