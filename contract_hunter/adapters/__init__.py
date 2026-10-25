"""
Contract Hunter Source Adapters
================================
Multi-source ingestion adapters for Hacker News, WeWorkRemotely, Y Combinator, and RemoteOK.
"""

from .hn_adapter import HNAdapter
from .wwr_adapter import WWRAdapter
from .yc_adapter import YCAdapter
from .remoteok_adapter import RemoteOKAdapter

__all__ = ["HNAdapter", "WWRAdapter", "YCAdapter", "RemoteOKAdapter"]
