"""felab — the shared toolkit every lesson imports.

    from felab import add_target_args, resolve, client, banner   # where to send requests
    from felab import stream_once, astream_once, percentile, user # how to time them
    from felab import record, table                               # where the numbers go
"""
from .measure import Sample, astream_once, percentile, stream_once, user
from .results import record, table
from .targets import TARGETS, Target, add_target_args, banner, client, resolve

__all__ = ["Sample", "astream_once", "percentile", "stream_once", "user", "record", "table",
           "TARGETS", "Target", "add_target_args", "banner", "client", "resolve"]
