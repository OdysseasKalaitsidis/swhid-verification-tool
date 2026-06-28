# SPDX-FileCopyrightText: 2026 Odysseas Kalaitsidis
# SPDX-License-Identifier: MIT

from packageurl import PackageURL
from typing import Dict, Tuple

def parse_purl(purl_str: str) -> Tuple[str, str, str, Dict[str, str]]:
    """
    Parses a PURL string and returns (ecosystem, name, version, qualifiers).
    """
    purl = PackageURL.from_string(purl_str)
    ecosystem = purl.type or ""
    name = purl.name or ""
    version = purl.version or ""
    qualifiers = purl.qualifiers or {}
    
    if purl.namespace:
        name = f"{purl.namespace}:{name}"
        
    return ecosystem, name, version, qualifiers
