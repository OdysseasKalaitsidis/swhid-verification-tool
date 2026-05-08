import time
import json
import os
from typing import List, Dict, Any
from shwid_tool.manager import SWHIDManager
from rich.progress import Progress

class BatchProcessor:
    def __init__(self, manager: SWHIDManager, cache_dir: str = "cache"):
        self.manager = manager
        self.cache_dir = cache_dir
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)

    def process_purls(self, purls: List[str]) -> List[Dict[str, Any]]:
        results = []
        with Progress() as progress:
            task = progress.add_task("[cyan]Processing PURLs...", total=len(purls))
            
            for purl in purls:
                # Check cache
                cache_file = os.path.join(self.cache_dir, f"{purl.replace(':', '_').replace('/', '_')}.json")
                if os.path.exists(cache_file):
                    with open(cache_file, "r") as f:
                        results.append(json.load(f))
                    progress.update(task, advance=1)
                    continue

                # Process with backoff
                retries = 0
                max_retries = 5
                while retries < max_retries:
                    try:
                        result = self.manager.resolve(purl)
                        
                        # Trigger Save Code Now if not verified but repo is known
                        if result.get("status") in ["Partial", "Inferred"] and "repo_url" in result:
                            progress.console.print(f"[blue]Triggering Save Code Now for {result['repo_url']}...[/blue]")
                            save_result = self.manager.swh.trigger_save_code_now(result["repo_url"])
                            result["save_code_now"] = save_result
                            
                        results.append(result)
                        # Save to cache
                        with open(cache_file, "w") as f:
                            json.dump(result, f)
                        break
                    except Exception as e:
                        if "429" in str(e): # Rate limited
                            wait_time = (2 ** retries) * 10
                            progress.console.print(f"[yellow]Rate limited. Waiting {wait_time}s...[/yellow]")
                            time.sleep(wait_time)
                            retries += 1
                        else:
                            progress.console.print(f"[red]Error processing {purl}: {str(e)}[/red]")
                            results.append({"purl": purl, "status": "Error", "reason": str(e)})
                            break
                
                progress.update(task, advance=1)
                # Small delay to be polite
                time.sleep(0.5)
        
        return results
