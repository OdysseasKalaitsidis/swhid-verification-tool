# SPDX-FileCopyrightText: 2026 Odysseas Kalaitsidis
# SPDX-License-Identifier: MIT

from packageurl import PackageURL
from typing import Optional, Tuple

def parse_purl(purl_str: str) -> Tuple[str, str, str, Optional[str]]:
    """
    Parses a PURL string and returns (ecosystem, name, version, qualifiers).
    """
    purl = PackageURL.from_string(purl_str)
    ecosystem = purl.type
    name = purl.name
    version = purl.version
    
    if purl.namespace:
        name = f"{purl.namespace}:{name}"
        
    return ecosystem, name, version, purl.qualifiers
