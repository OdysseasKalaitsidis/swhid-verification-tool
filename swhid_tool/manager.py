# SPDX-FileCopyrightText: 2026 Odysseas Kalaitsidis
# SPDX-License-Identifier: MIT

from typing import Dict, Any
from swhid_tool.purl_parser import parse_purl
from swhid_tool.core import SWHClient
from swhid_tool.strategies.pypi_strategy import PyPIStrategy
from swhid_tool.strategies.cargo_strategy import CargoStrategy
from swhid_tool.strategies.maven_strategy import MavenStrategy

class SWHIDManager:
    def __init__(self, auth_token: str = None):
        self.swh = SWHClient(auth_token)
        self.strategies = {
            "pypi": PyPIStrategy(self.swh),
            "cargo": CargoStrategy(self.swh),
            "maven": MavenStrategy(self.swh),
        }

    def resolve(self, purl_str: str) -> Dict[str, Any]:
        ecosystem, name, version, qualifiers = parse_purl(purl_str)
        strategy = self.strategies.get(ecosystem)
        
        if not strategy:
            raise ValueError(f"Unsupported ecosystem: {ecosystem}")
            
        return strategy.resolve(name, version, qualifiers)
