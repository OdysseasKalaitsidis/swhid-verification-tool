# SPDX-FileCopyrightText: 2026 Odysseas Kalaitsidis
# SPDX-License-Identifier: MIT

import requests
from typing import List, Dict, Any, Optional, cast
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)

OSV_API_URL = "https://api.osv.dev/v1/querybatch"
OSV_VULN_URL = "https://api.osv.dev/v1/vulns"

class OSVClient:
    """
    Client for querying the Open Source Vulnerability (OSV.dev) database.
    """
    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "SWHID-Verification-Tool/1.0 (GSoC 2026)"})

    def _fetch_vuln_details(self, vuln_id: str) -> Optional[Dict[str, Any]]:
        """Fetches full details for a single vulnerability ID."""
        url = f"{OSV_VULN_URL}/{vuln_id}"
        try:
            resp = self.session.get(url, timeout=15)
            if resp.status_code == 200:
                return cast(Dict[str, Any], resp.json())
            else:
                logger.error(f"Failed to fetch details for {vuln_id}: {resp.status_code}")
        except Exception as e:
            logger.error(f"Error fetching details for {vuln_id}: {e}")
        return None

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

    def query_vulnerabilities_hybrid(self, items: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Queries OSV.dev for vulnerabilities using both the PURL and the commit SHA (hybrid).
        Each item in `items` should be a dict containing 'purl' and optionally 'swhid'.
        Returns a mapping of purl -> list of unique vulnerability dicts.
        """
        if not items:
            return {}

        queries = []
        query_map = []  # List of tuples: (index_in_items, query_type)

        for idx, item in enumerate(items):
            purl = item.get("purl")
            swhid = item.get("swhid")
            
            # 1. PURL query
            if purl:
                queries.append({"package": {"purl": purl}})
                query_map.append((idx, "purl"))
                
            # 2. Commit query
            if swhid and swhid.startswith("swh:1:rev:"):
                commit_sha = swhid.split(":")[-1]
                queries.append({"commit": commit_sha})
                query_map.append((idx, "commit"))

        if not queries:
            return {}

        payload = {"queries": queries}
        results_map: Dict[int, Dict[str, Dict[str, Any]]] = {}
        
        try:
            response = self.session.post(OSV_API_URL, json=payload, timeout=30)
            if response.status_code == 200:
                results = response.json().get("results", [])
                
                # Process results and group by item index
                for (item_idx, q_type), res in zip(query_map, results):
                    vulns = res.get("vulns", [])
                    if vulns:
                        if item_idx not in results_map:
                            results_map[item_idx] = {}
                        for v in vulns:
                            v_id = v.get("id")
                            if v_id:
                                # Store by ID to deduplicate if both commit and PURL return the same vulnerability
                                results_map[item_idx][v_id] = v
            else:
                logger.error(f"OSV API returned status code {response.status_code}: {response.text}")
        except Exception as e:
            logger.error(f"Error querying OSV API: {e}")

        # Gather all unique vulnerability IDs that lack a summary
        vulns_to_fetch = set()
        for idx_map in results_map.values():
            for v_id, v in idx_map.items():
                if "summary" not in v or not v["summary"]:
                    vulns_to_fetch.add(v_id)

        # Fetch full details for those vulnerabilities in parallel
        if vulns_to_fetch:
            detailed_vulns = {}
            with ThreadPoolExecutor(max_workers=20) as executor:
                future_to_id = {
                    executor.submit(self._fetch_vuln_details, v_id): v_id 
                    for v_id in vulns_to_fetch
                }
                for future in as_completed(future_to_id):
                    v_id = future_to_id[future]
                    try:
                        details = future.result()
                        if details:
                            detailed_vulns[v_id] = details
                    except Exception as e:
                        logger.error(f"Error retrieving future for {v_id}: {e}")

            # Merge the detailed info back into the results
            for idx_map in results_map.values():
                for v_id in list(idx_map.keys()):
                    if v_id in detailed_vulns:
                        idx_map[v_id].update(detailed_vulns[v_id])

        # Map back to PURLs
        final_mapping = {}
        for idx, item in enumerate(items):
            purl = item.get("purl")
            if purl and idx in results_map:
                final_mapping[purl] = list(results_map[idx].values())

        return final_mapping
