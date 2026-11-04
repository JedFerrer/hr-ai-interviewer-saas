"""Untrusted document parser child: hard CPU, memory and parent wall-time bounds."""

import os
import sys


def restrict_resources():
    if os.name != "nt":
        import resource

        resource.setrlimit(resource.RLIMIT_AS, (384 * 1024**2, 384 * 1024**2))
        resource.setrlimit(resource.RLIMIT_CPU, (10, 10))
        return
    import ctypes as c
    from ctypes import wintypes as w

    class Basic(c.Structure):
        _fields_ = [
            ("process_time", c.c_longlong),
            ("job_time", c.c_longlong),
            ("flags", w.DWORD),
            ("min_ws", c.c_size_t),
            ("max_ws", c.c_size_t),
            ("processes", w.DWORD),
            ("affinity", c.c_size_t),
            ("priority", w.DWORD),
            ("scheduling", w.DWORD),
        ]

    class IO(c.Structure):
        _fields_ = [
            (name, c.c_ulonglong)
            for name in (
                "read_ops",
                "write_ops",
                "other_ops",
                "read_bytes",
                "write_bytes",
                "other_bytes",
            )
        ]

    class Extended(c.Structure):
        _fields_ = [
            ("basic", Basic),
            ("io", IO),
            ("process_memory", c.c_size_t),
            ("job_memory", c.c_size_t),
            ("peak_process", c.c_size_t),
            ("peak_job", c.c_size_t),
        ]

    kernel = c.WinDLL("kernel32", use_last_error=True)
    kernel.CreateJobObjectW.restype = w.HANDLE
    kernel.CreateJobObjectW.argtypes = [c.c_void_p, w.LPCWSTR]
    kernel.GetCurrentProcess.restype = w.HANDLE
    kernel.SetInformationJobObject.argtypes = [w.HANDLE, c.c_int, c.c_void_p, w.DWORD]
    kernel.AssignProcessToJobObject.argtypes = [w.HANDLE, w.HANDLE]
    job = kernel.CreateJobObjectW(None, None)
    limits = Extended()
    limits.basic.flags = 0x100 | 0x2  # PROCESS_MEMORY | PROCESS_TIME
    limits.basic.process_time = 10 * 10_000_000
    limits.process_memory = 384 * 1024**2
    if (
        not job
        or not kernel.SetInformationJobObject(job, 9, c.byref(limits), c.sizeof(limits))
        or not kernel.AssignProcessToJobObject(job, kernel.GetCurrentProcess())
    ):
        raise RuntimeError("Cannot establish parser resource limits")
    # Keep handle open until child exit (not a kill-on-close job).


def main():
    restrict_resources()
    import socket

    def deny_network(*args, **kwargs):
        raise RuntimeError("Parser network access is forbidden")

    socket.socket.connect = deny_network
    socket.socket.connect_ex = deny_network
    socket.create_connection = deny_network
    from app.services.resume_service import _extract_docx, _extract_pdf

    data = sys.stdin.buffer.read(10 * 1024**2 + 1)
    if len(data) > 10 * 1024**2:
        raise ValueError("size")
    text = _extract_pdf(data) if sys.argv[1] == ".pdf" else _extract_docx(data)
    if len(text) > 100_000:
        raise ValueError("text limit")
    sys.stdout.buffer.write(text.encode("utf-8"))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        raise SystemExit(1) from exc
