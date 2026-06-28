# SPDX-FileCopyrightText: 2026 Odysseas Kalaitsidis
# SPDX-License-Identifier: MIT

import requests
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

OSV_API_URL = "https://api.osv.dev/v1/querybatch"

class OSVClient:
    """
    Client for querying the Open Source Vulnerability (OSV.dev) database.
    """
    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "SWHID-Verification-Tool/1.0 (GSoC 2026)"})

    def query_vulnerabilities(self, commits: List[str]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Queries OSV.dev for vulnerabilities matching a list of commit SHAs.
        Returns a mapping of commit_sha -> list of vulnerability dicts.
        """
        if not commits:
            return {}

        # OSV querybatch allows up to 1000 queries per request
        queries = [{"commit": commit} for commit in commits]
        payload = {"queries": queries}

        try:
            response = self.session.post(OSV_API_URL, json=payload, timeout=30)
            if response.status_code == 200:
                results = response.json().get("results", [])
                mapping = {}
                for commit, res in zip(commits, results):
                    vulns = res.get("vulns", [])
                    if vulns:
                        mapping[commit] = vulns
                return mapping
            else:
                logger.error(f"OSV API returned status code {response.status_code}: {response.text}")
        except Exception as e:
            logger.error(f"Error querying OSV API: {e}")

        return {}
