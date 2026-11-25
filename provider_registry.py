from p_base import BaseProvider, TestResult
from p_dgdnetwork import DgdNetworkProvider
from p_mknetwork import MkNetworkProvider
from p_network4 import Network4Provider
from p_voltx import VoltxProvider

PROVIDERS: dict = {
    p.slug: p
    for p in (VoltxProvider(), DgdNetworkProvider(), MkNetworkProvider(), Network4Provider())
}

__all__ = ["PROVIDERS", "BaseProvider", "TestResult"]
