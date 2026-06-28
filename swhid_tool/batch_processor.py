# SPDX-FileCopyrightText: 2026 Odysseas Kalaitsidis
# SPDX-License-Identifier: MIT

import json
import os
import logging
from typing import List, Dict, Any
from swhid_tool.manager import SWHIDManager
from rich.progress import Progress

logger = logging.getLogger(__name__)

class BatchProcessor:
    def __init__(self, manager: SWHIDManager, cache_dir: str = "cache"):
        self.manager = manager
        self.cache_dir = cache_dir
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)

    def process_purls(self, purls: List[str], trigger_save: bool = False) -> List[Dict[str, Any]]:
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        results = [None] * len(purls)  # type: List[Any]
        purl_to_index = {purl: idx for idx, purl in enumerate(purls)}
        
        # Check cache first
        uncached_purls = []
        for idx, purl in enumerate(purls):
            cache_file = os.path.join(self.cache_dir, f"{purl.replace(':', '_').replace('/', '_')}.json")
            if os.path.exists(cache_file):
                try:
                    with open(cache_file, "r") as f:
                        results[idx] = json.load(f)
                except Exception:
                    uncached_purls.append(purl)
            else:
                uncached_purls.append(purl)

        if not uncached_purls:
            return [r for r in results if r is not None]

        # Parallel processing
        # 5 workers for anonymous, 10 if authenticated
        max_workers = 5
        if self.manager.swh.session.headers.get("Authorization"):
            max_workers = 10

        def resolve_one(purl: str) -> Dict[str, Any]:
            cache_file = os.path.join(self.cache_dir, f"{purl.replace(':', '_').replace('/', '_')}.json")
            try:
                logger.info(f"Resolving {purl}")
                result = self.manager.resolve(purl)
                
                # Trigger Save Code Now if enabled and not verified but repo is known
                if trigger_save and result.get("status") in ["Partial", "Inferred"] and "repo_url" in result:
                    save_result = self.manager.swh.trigger_save_code_now(result["repo_url"])
                    result["save_code_now"] = save_result
                    
                # Save to cache
                with open(cache_file, "w") as f:
                    json.dump(result, f)
                return result
            except Exception as e:
                logger.error(f"Error processing {purl}: {str(e)}")
                return {"purl": purl, "status": "Error", "reason": str(e)}

        with Progress() as progress:
            task = progress.add_task("[cyan]Processing PURLs...", total=len(purls))
            progress.update(task, advance=len(purls) - len(uncached_purls))
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_purl = {executor.submit(resolve_one, purl): purl for purl in uncached_purls}
                
                for future in as_completed(future_to_purl):
                    purl = future_to_purl[future]
                    idx = purl_to_index[purl]
                    try:
                        result = future.result()
                        results[idx] = result
                    except Exception as exc:
                        logger.error(f"{purl} generated an exception: {exc}")
                        results[idx] = {"purl": purl, "status": "Error", "reason": str(exc)}
                    
                    progress.update(task, advance=1)
        
        return [r for r in results if r is not None]

