# SPDX-FileCopyrightText: 2026 Odysseas Kalaitsidis
# SPDX-License-Identifier: MIT

"""
Generates a comprehensive SWHID verification dataset.

Fetches the top 50 most popular packages from each of the 6 supported
ecosystems (PyPI, npm, Cargo, Go, Maven, NuGet) and resolves them to
verified SWHIDs. Outputs a CSV, an SPDX 3.0 JSON-LD manifest, and a
detailed Markdown findings report.

Usage:
    python3 scripts/generate_full_dataset.py [--token YOUR_SWH_TOKEN]
"""

import os
import sys
import csv
import shutil
import argparse
import requests
import datetime
from typing import List, Dict, Any, Tuple

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from swhid_tool.manager import SWHIDManager
from swhid_tool.batch_processor import BatchProcessor
from swhid_tool.spdx_exporter import export_to_spdx3

PACKAGES_PER_ECOSYSTEM = 50
OUTPUT_DIR = "dataset"
CACHE_DIR = "cache"


# ---------------------------------------------------------------------------
# Registry fetchers — each returns a list of PURL strings
# ---------------------------------------------------------------------------

def fetch_pypi_top(n: int) -> List[str]:
    """Fetch top PyPI packages from the hugovk/top-pypi-packages dataset."""
    print(f"  📦 Fetching top {n} PyPI packages...")
    url = "https://hugovk.github.io/top-pypi-packages/top-pypi-packages-30-days.min.json"
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    rows = resp.json()["rows"][:n]
    
    purls = []
    for row in rows:
        name = row["project"]
        # Get latest version from PyPI JSON API
        try:
            info = requests.get(f"https://pypi.org/pypi/{name}/json", timeout=15).json()
            version = info["info"]["version"]
            purls.append(f"pkg:pypi/{name}@{version}")
        except Exception as e:
            print(f"    ⚠ Skipping {name}: {e}")
    return purls


def fetch_npm_top(n: int) -> List[str]:
    """Fetch top npm packages using the npm registry API."""
    print(f"  📦 Fetching top {n} npm packages...")
    # Use a curated list of the most depended-upon npm packages
    # (npm doesn't have a simple "top by downloads" public API endpoint)
    top_npm = [
        "lodash", "chalk", "react", "express", "commander", "moment", "debug",
        "async", "bluebird", "request", "underscore", "uuid", "axios", "glob",
        "mkdirp", "minimist", "semver", "colors", "body-parser", "through2",
        "yargs", "fs-extra", "inquirer", "webpack", "prop-types", "rxjs",
        "tslib", "core-js", "classnames", "jquery", "ws", "cheerio",
        "rimraf", "dotenv", "eslint", "prettier", "typescript", "mocha",
        "jest", "babel-core", "ora", "execa", "nano", "passport",
        "mongoose", "redis", "pg", "mysql2", "socket.io", "cors",
        "helmet", "morgan", "multer", "jsonwebtoken", "bcrypt",
        "nodemailer", "sharp", "pino", "fastify", "koa",
    ]
    
    purls = []
    for name in top_npm[:n]:
        try:
            resp = requests.get(f"https://registry.npmjs.org/{name}/latest", timeout=15)
            resp.raise_for_status()
            version = resp.json()["version"]
            purls.append(f"pkg:npm/{name}@{version}")
        except Exception as e:
            print(f"    ⚠ Skipping {name}: {e}")
    return purls


def fetch_cargo_top(n: int) -> List[str]:
    """Fetch top Cargo crates from crates.io sorted by downloads."""
    print(f"  📦 Fetching top {n} Cargo crates...")
    purls = []
    page = 1
    per_page = min(n, 100)
    
    while len(purls) < n:
        url = f"https://crates.io/api/v1/crates?page={page}&per_page={per_page}&sort=downloads"
        resp = requests.get(url, headers={"User-Agent": "SWHID-Dataset-Builder/1.0"}, timeout=15)
        resp.raise_for_status()
        crates = resp.json()["crates"]
        if not crates:
            break
        for c in crates:
            if len(purls) >= n:
                break
            purls.append(f"pkg:cargo/{c['id']}@{c['newest_version']}")
        page += 1
    return purls


def fetch_golang_top(n: int) -> List[str]:
    """Curated list of the most popular Go modules."""
    print(f"  📦 Fetching top {n} Go modules...")
    # Go doesn't have a public "top by downloads" API, so we use a curated list
    # of the most-imported modules from the Go ecosystem
    top_go = [
        ("github.com/gin-gonic/gin", "v1.9.0"),
        ("github.com/sirupsen/logrus", "v1.9.3"),
        ("golang.org/x/text", "v0.14.0"),
        ("github.com/spf13/cobra", "v1.8.0"),
        ("github.com/stretchr/testify", "v1.9.0"),
        ("github.com/gorilla/mux", "v1.8.1"),
        ("github.com/go-chi/chi", "v5.0.12"),
        ("github.com/spf13/viper", "v1.18.2"),
        ("google.golang.org/grpc", "v1.62.1"),
        ("github.com/prometheus/client_golang", "v1.19.0"),
        ("github.com/go-redis/redis", "v8.11.5"),
        ("github.com/stretchr/objx", "v0.5.2"),
        ("go.uber.org/zap", "v1.27.0"),
        ("github.com/golang/protobuf", "v1.5.4"),
        ("github.com/google/uuid", "v1.6.0"),
        ("github.com/pkg/errors", "v0.9.1"),
        ("github.com/fatih/color", "v1.16.0"),
        ("github.com/mitchellh/mapstructure", "v1.5.0"),
        ("github.com/aws/aws-sdk-go", "v1.51.6"),
        ("github.com/hashicorp/consul", "v1.18.1"),
        ("github.com/docker/docker", "v25.0.5"),
        ("github.com/lib/pq", "v1.10.9"),
        ("github.com/jackc/pgx", "v5.5.5"),
        ("github.com/go-sql-driver/mysql", "v1.8.1"),
        ("github.com/gorilla/websocket", "v1.5.1"),
        ("github.com/labstack/echo", "v4.11.4"),
        ("golang.org/x/crypto", "v0.21.0"),
        ("golang.org/x/net", "v0.22.0"),
        ("golang.org/x/sys", "v0.18.0"),
        ("golang.org/x/tools", "v0.19.0"),
        ("github.com/go-playground/validator", "v10.19.0"),
        ("github.com/rs/zerolog", "v1.32.0"),
        ("github.com/nats-io/nats.go", "v1.34.0"),
        ("github.com/tidwall/gjson", "v1.17.1"),
        ("github.com/patrickmn/go-cache", "v2.1.0"),
        ("github.com/dgrijalva/jwt-go", "v3.2.0"),
        ("github.com/gofiber/fiber", "v2.52.2"),
        ("github.com/gin-contrib/cors", "v1.6.0"),
        ("github.com/go-kit/kit", "v0.13.0"),
        ("github.com/gogo/protobuf", "v1.3.2"),
        ("github.com/pelletier/go-toml", "v2.1.1"),
        ("github.com/hashicorp/go-hclog", "v1.6.2"),
        ("github.com/joho/godotenv", "v1.5.1"),
        ("github.com/DATA-DOG/go-sqlmock", "v1.5.2"),
        ("github.com/cespare/xxhash", "v2.2.0"),
        ("github.com/golang-migrate/migrate", "v4.17.0"),
        ("github.com/grpc-ecosystem/grpc-gateway", "v2.19.1"),
        ("github.com/uber-go/fx", "v1.21.0"),
        ("github.com/shopspring/decimal", "v1.3.1"),
        ("github.com/jmoiron/sqlx", "v1.3.5"),
    ]
    
    purls = []
    for mod, ver in top_go[:n]:
        purls.append(f"pkg:golang/{mod}@{ver}")
    return purls


def fetch_maven_top(n: int) -> List[str]:
    """Curated list of the most popular Maven Central artifacts."""
    print(f"  📦 Fetching top {n} Maven artifacts...")
    # Maven Central doesn't have a simple "top downloads" API,
    # so we use the most popular artifacts by usage
    top_maven = [
        ("junit", "junit", "4.13.2"),
        ("org.slf4j", "slf4j-api", "2.0.13"),
        ("org.apache.commons", "commons-lang3", "3.14.0"),
        ("com.fasterxml.jackson.core", "jackson-databind", "2.17.0"),
        ("org.mockito", "mockito-core", "5.11.0"),
        ("com.google.guava", "guava", "33.1.0-jre"),
        ("org.apache.logging.log4j", "log4j-core", "2.23.1"),
        ("org.apache.httpcomponents", "httpclient", "4.5.14"),
        ("com.google.code.gson", "gson", "2.10.1"),
        ("org.projectlombok", "lombok", "1.18.32"),
        ("org.apache.commons", "commons-collections4", "4.4"),
        ("commons-io", "commons-io", "2.16.0"),
        ("org.springframework", "spring-core", "6.1.5"),
        ("org.springframework", "spring-context", "6.1.5"),
        ("org.springframework.boot", "spring-boot", "3.2.4"),
        ("ch.qos.logback", "logback-classic", "1.5.3"),
        ("org.apache.commons", "commons-text", "1.12.0"),
        ("com.fasterxml.jackson.core", "jackson-core", "2.17.0"),
        ("org.yaml", "snakeyaml", "2.2"),
        ("commons-codec", "commons-codec", "1.17.0"),
        ("org.assertj", "assertj-core", "3.25.3"),
        ("org.jetbrains.kotlin", "kotlin-stdlib", "1.9.23"),
        ("org.apache.maven", "maven-core", "3.9.6"),
        ("com.squareup.okhttp3", "okhttp", "4.12.0"),
        ("io.netty", "netty-all", "4.1.108.Final"),
        ("org.testng", "testng", "7.10.1"),
        ("com.h2database", "h2", "2.2.224"),
        ("org.postgresql", "postgresql", "42.7.3"),
        ("com.mysql", "mysql-connector-j", "8.3.0"),
        ("org.apache.kafka", "kafka-clients", "3.7.0"),
        ("io.micrometer", "micrometer-core", "1.12.4"),
        ("org.hibernate", "hibernate-core", "6.4.4.Final"),
        ("com.zaxxer", "HikariCP", "5.1.0"),
        ("com.amazonaws", "aws-java-sdk-core", "1.12.688"),
        ("io.grpc", "grpc-core", "1.63.0"),
        ("org.apache.commons", "commons-math3", "3.6.1"),
        ("org.bouncycastle", "bcprov-jdk18on", "1.77"),
        ("javax.servlet", "javax.servlet-api", "4.0.1"),
        ("org.json", "json", "20240303"),
        ("com.google.protobuf", "protobuf-java", "4.26.0"),
        ("io.swagger.core.v3", "swagger-core", "2.2.21"),
        ("org.apache.poi", "poi", "5.2.5"),
        ("org.flywaydb", "flyway-core", "10.10.0"),
        ("com.google.errorprone", "error_prone_core", "2.26.1"),
        ("io.jsonwebtoken", "jjwt-api", "0.12.5"),
        ("org.mapstruct", "mapstruct", "1.5.5.Final"),
        ("com.google.inject", "guice", "7.0.0"),
        ("org.eclipse.jetty", "jetty-server", "12.0.7"),
        ("io.vertx", "vertx-core", "4.5.7"),
        ("org.apache.camel", "camel-core", "4.5.0"),
    ]

    purls = []
    for group, artifact, version in top_maven[:n]:
        purls.append(f"pkg:maven/{group}/{artifact}@{version}")
    return purls


def fetch_nuget_top(n: int) -> List[str]:
    """Fetch top NuGet packages from the NuGet catalog."""
    print(f"  📦 Fetching top {n} NuGet packages...")
    # Use NuGet search API sorted by totalDownloads
    top_nuget = [
        "Newtonsoft.Json", "System.Text.Json", "Serilog", "AutoMapper",
        "FluentValidation", "Dapper", "MediatR", "Polly",
        "Swashbuckle.AspNetCore", "xunit", "NUnit", "Moq",
        "FluentAssertions", "Bogus", "Humanizer.Core", "CsvHelper",
        "RestSharp", "MailKit", "HtmlAgilityPack", "Npgsql",
        "StackExchange.Redis", "MongoDB.Driver", "EntityFramework",
        "Microsoft.EntityFrameworkCore", "Hangfire.Core",
        "MassTransit", "NLog", "log4net", "Autofac",
        "Grpc.Net.Client", "protobuf-net", "MessagePack",
        "BenchmarkDotNet", "Shouldly", "AngleSharp",
        "SixLabors.ImageSharp", "SkiaSharp", "Markdig",
        "YamlDotNet", "Jint", "MiniProfiler.AspNetCore.Mvc",
        "AWSSDK.Core", "Azure.Storage.Blobs", "Google.Cloud.Storage.V1",
        "NSwag.AspNetCore", "Scrutor", "Mapster", "Refit",
        "LazyCache", "EFCore.BulkExtensions",
    ]

    purls = []
    for name in top_nuget[:n]:
        try:
            url = f"https://api.nuget.org/v3-flatcontainer/{name.lower()}/index.json"
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            versions = resp.json()["versions"]
            # Get latest stable version (no pre-release)
            stable = [v for v in versions if "-" not in v]
            version = stable[-1] if stable else versions[-1]
            purls.append(f"pkg:nuget/{name}@{version}")
        except Exception as e:
            print(f"    ⚠ Skipping {name}: {e}")
    return purls


# ---------------------------------------------------------------------------
# Output generators
# ---------------------------------------------------------------------------

def write_csv(findings: List[Dict[str, Any]], path: str) -> None:
    """Write findings to a CSV file for analysis."""
    fieldnames = [
        "purl", "ecosystem", "name", "version", "status", "confidence",
        "swhid", "strategy", "repo_url", "tag_matched",
        "commit_sha", "reason", "timestamp"
    ]
    
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for finding in findings:
            purl = finding.get("purl", "")
            # Parse ecosystem/name/version from PURL
            parts = purl.split("/", 1)
            ecosystem = parts[0].replace("pkg:", "") if parts else ""
            name_ver = parts[1] if len(parts) > 1 else ""
            if "@" in name_ver:
                name, version = name_ver.rsplit("@", 1)
            else:
                name, version = name_ver, ""
            
            writer.writerow({
                "purl": purl,
                "ecosystem": ecosystem,
                "name": name,
                "version": version,
                "status": finding.get("status", ""),
                "confidence": finding.get("confidence", finding.get("status", "")),
                "swhid": finding.get("swhid", ""),
                "strategy": finding.get("strategy", ""),
                "repo_url": finding.get("repo_url", ""),
                "tag_matched": finding.get("tag_matched", ""),
                "commit_sha": finding.get("commit_sha", ""),
                "reason": finding.get("reason", ""),
                "timestamp": timestamp,
            })


def write_findings_report(
    findings: List[Dict[str, Any]],
    ecosystem_purls: Dict[str, List[str]],
    path: str
) -> None:
    """Write a detailed Markdown findings report."""
    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    total = len(findings)
    
    # Global stats
    verified = sum(1 for f in findings if f.get("status") == "Verified")
    inferred = sum(1 for f in findings if f.get("status") == "Inferred")
    partial = sum(1 for f in findings if f.get("status") == "Partial")
    errors = total - verified - inferred - partial
    
    # Per-ecosystem stats
    eco_stats: Dict[str, Dict[str, int]] = {}
    for f in findings:
        purl = f.get("purl", "")
        eco = purl.split("/")[0].replace("pkg:", "") if "/" in purl else "unknown"
        if eco not in eco_stats:
            eco_stats[eco] = {"total": 0, "verified": 0, "inferred": 0, "partial": 0, "error": 0}
        eco_stats[eco]["total"] += 1
        status = f.get("status", "Error")
        if status == "Verified":
            eco_stats[eco]["verified"] += 1
        elif status == "Inferred":
            eco_stats[eco]["inferred"] += 1
        elif status == "Partial":
            eco_stats[eco]["partial"] += 1
        else:
            eco_stats[eco]["error"] += 1
    
    # Strategy usage
    strategy_counts: Dict[str, int] = {}
    for f in findings:
        s = f.get("strategy", "N/A")
        strategy_counts[s] = strategy_counts.get(s, 0) + 1
    
    def pct(c: float) -> str:
        return f"{c/total*100:.1f}%" if total else "0%"
    
    # Build report
    md = []
    md.append("# SWHID Verification Dataset — Findings Report")
    md.append(f"\n*Generated on {timestamp}*\n")
    
    md.append("## Executive Summary\n")
    md.append("This report documents the results of computing and verifying Software Heritage")
    md.append(f"Identifiers (SWHIDs) for **{total} packages** across **{len(eco_stats)} package")
    md.append("ecosystems**. The dataset covers the most popular packages from PyPI, npm,")
    md.append("Crates.io, Go Modules, Maven Central, and NuGet.\n")
    
    md.append("## Overall Results\n")
    md.append("| Status | Count | Percentage | Meaning |")
    md.append("| :--- | ---: | ---: | :--- |")
    md.append(f"| ✅ **Verified** | {verified} | {pct(verified)} | Exact SWHID match confirmed in SWH archive |")
    md.append(f"| 🟡 **Inferred** | {inferred} | {pct(inferred)} | Repository archived, but specific version tag not found |")
    md.append(f"| 🟠 **Partial** | {partial} | {pct(partial)} | Local SWHID computed, not yet confirmed in archive |")
    md.append(f"| 🔴 **Error/Failed** | {errors} | {pct(errors)} | Resolution failed (network, missing data, unsupported) |")
    md.append(f"| **Total** | **{total}** | **100%** | |")
    md.append("")
    
    md.append("## Per-Ecosystem Breakdown\n")
    md.append("| Ecosystem | Total | ✅ Verified | 🟡 Inferred | 🟠 Partial | 🔴 Error | Verification Rate |")
    md.append("| :--- | ---: | ---: | ---: | ---: | ---: | ---: |")
    eco_names = {"pypi": "PyPI", "npm": "npm", "cargo": "Crates.io", "golang": "Go Modules", "maven": "Maven Central", "nuget": "NuGet"}
    for eco in ["pypi", "npm", "cargo", "golang", "maven", "nuget"]:
        s = eco_stats.get(eco, {"total": 0, "verified": 0, "inferred": 0, "partial": 0, "error": 0})
        t = s["total"]
        vr = f"{s['verified']/t*100:.0f}%" if t else "N/A"
        md.append(f"| **{eco_names.get(eco, eco)}** | {t} | {s['verified']} | {s['inferred']} | {s['partial']} | {s['error']} | {vr} |")
    md.append("")
    
    md.append("## Strategy Distribution\n")
    md.append("Which verification strategy succeeded for resolved packages:\n")
    md.append("| Strategy | Count | Description |")
    md.append("| :--- | ---: | :--- |")
    strat_desc = {
        "A": "Attestation-based (e.g., Sigstore/PEP 740 commit SHA extraction)",
        "B": "Metadata-based (repository URL + version tag matching in SWH snapshot)",
        "C": "File-level (download artifact, normalize, compute directory SWHID)",
        "N/A": "No strategy succeeded",
    }
    for s_key in ["A", "B", "C", "N/A"]:
        if s_key in strategy_counts:
            md.append(f"| **{s_key}** | {strategy_counts[s_key]} | {strat_desc.get(s_key, '')} |")
    # Any other strategies
    for s_key, cnt in sorted(strategy_counts.items()):
        if s_key not in ["A", "B", "C", "N/A"]:
            md.append(f"| **{s_key}** | {cnt} | |")
    md.append("")
    
    md.append("## Key Finding: The Registry-VCS Gap\n")
    md.append("The most significant finding from this dataset is that **package registry artifacts")
    md.append("are structurally different from VCS (git) repository snapshots**. This creates a")
    md.append("fundamental obstacle to PURL→SWHID mapping:\n")
    md.append("1. **PyPI**: sdist tarballs contain `PKG-INFO`, `setup.cfg`, and other metadata files")
    md.append("   that don't exist in the git repository.")
    md.append("2. **Cargo**: Crates.io adds `.cargo_vcs_info.json` and replaces `Cargo.toml` with a")
    md.append("   normalized version (the original is saved as `Cargo.toml.orig`).")
    md.append("3. **Maven**: JAR files contain compiled bytecode and manifest files absent from source.")
    md.append("4. **npm**: Tarballs include auto-generated files and normalized `package.json`.")
    md.append("5. **NuGet**: `.nupkg` files include `.nuspec`, content-type XML, and relationship metadata.\n")
    md.append("This means a **naive SWHID computation on a registry artifact will never match")
    md.append("the SWHID of the same code archived in Software Heritage from git**. Ecosystem-specific")
    md.append("normalization strategies are required to bridge this gap.\n")
    
    md.append("## Methodology\n")
    md.append("For each package, the tool applies a cascade of verification strategies in")
    md.append("descending order of confidence:\n")
    md.append("1. **Strategy A (Attestation)**: Extract cryptographic commit SHAs from Sigstore/PEP 740")
    md.append("   attestations, then verify the `swh:1:rev:` SWHID exists in the archive.")
    md.append("2. **Strategy B (Metadata + Tag Matching)**: Extract the source repository URL from")
    md.append("   registry metadata, check if SWH has archived it, and match version tags in the")
    md.append("   archived snapshot to find the exact revision.")
    md.append("3. **Strategy C (File-Level)**: Download the artifact, normalize it (strip registry")
    md.append("   additions), compute a `swh:1:dir:` SWHID, and check if it exists in SWH.\n")
    
    md.append("## Verified Packages\n")
    verified_list = [f for f in findings if f.get("status") == "Verified"]
    if verified_list:
        md.append("| Package | SWHID | Strategy |")
        md.append("| :--- | :--- | :--- |")
        for f in verified_list:
            swhid = f.get("swhid", "N/A")
            md.append(f"| `{f.get('purl', '')}` | `{swhid}` | {f.get('strategy', 'N/A')} |")
    else:
        md.append("*No packages achieved full Verified status in this run.*")
    md.append("")
    
    md.append("## Error Summary\n")
    error_list = [f for f in findings if f.get("status") not in ["Verified", "Inferred", "Partial"]]
    if error_list:
        md.append("| Package | Reason |")
        md.append("| :--- | :--- |")
        for f in error_list:
            reason = f.get("reason", "Unknown error")
            if len(reason) > 120:
                reason = reason[:117] + "..."
            md.append(f"| `{f.get('purl', '')}` | {reason} |")
    else:
        md.append("*No errors encountered.*")
    md.append("")
    
    md.append("## Reproducibility\n")
    md.append("To reproduce this dataset:\n")
    md.append("```bash")
    md.append("# Clone and setup")
    md.append("git clone https://github.com/OdysseasKalaitsidis/SWHID_POC")
    md.append("cd SWHID_POC && pip install -e .")
    md.append("")
    md.append("# Optional: set SWH API token for higher rate limits")
    md.append("export SWH_AUTH_TOKEN=your_token_here")
    md.append("")
    md.append("# Generate the dataset")
    md.append("python3 scripts/generate_full_dataset.py")
    md.append("```\n")
    
    md.append("---\n")
    md.append("*This dataset was generated by the [SWHID Verification Tool](https://github.com/OdysseasKalaitsidis/SWHID_POC).*\n")
    
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(md))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Generate comprehensive SWHID dataset")
    parser.add_argument("--token", help="Software Heritage API token")
    parser.add_argument("--per-ecosystem", type=int, default=PACKAGES_PER_ECOSYSTEM,
                        help=f"Number of packages per ecosystem (default: {PACKAGES_PER_ECOSYSTEM})")
    parser.add_argument("--no-clear-cache", action="store_true",
                        help="Don't clear the cache before running")
    args = parser.parse_args()
    
    n = args.per_ecosystem
    
    print("=" * 70)
    print("  SWHID Verification Dataset Generator")
    print(f"  Target: {n} packages × 6 ecosystems = {n * 6} packages")
    print("=" * 70)
    
    # Clear stale cache unless told not to
    if not args.no_clear_cache and os.path.exists(CACHE_DIR):
        print(f"\n🗑️  Clearing stale cache at {CACHE_DIR}/...")
        shutil.rmtree(CACHE_DIR)
    
    # Step 1: Fetch top packages from each ecosystem
    print("\n📡 Step 1: Fetching top packages from registries...\n")
    ecosystem_purls: Dict[str, List[str]] = {}
    
    fetchers: List[Tuple[str, Any]] = [
        ("pypi", fetch_pypi_top),
        ("npm", fetch_npm_top),
        ("cargo", fetch_cargo_top),
        ("golang", fetch_golang_top),
        ("maven", fetch_maven_top),
        ("nuget", fetch_nuget_top),
    ]
    
    all_purls: List[str] = []
    for eco_name, fetcher in fetchers:
        try:
            purls = fetcher(n)
            ecosystem_purls[eco_name] = purls
            all_purls.extend(purls)
            print(f"    ✅ {eco_name}: {len(purls)} packages\n")
        except Exception as e:
            print(f"    ❌ {eco_name}: Failed to fetch ({e})\n")
            ecosystem_purls[eco_name] = []
    
    print(f"\n📊 Total packages to resolve: {len(all_purls)}")
    
    # Step 2: Resolve all PURLs through the SWHID verification pipeline
    print("\n🔬 Step 2: Resolving PURLs to SWHIDs...\n")
    manager = SWHIDManager(auth_token=args.token)
    processor = BatchProcessor(manager, cache_dir=CACHE_DIR)
    
    findings = processor.process_purls(all_purls)
    
    # Step 3: Generate outputs
    print("\n📝 Step 3: Generating outputs...\n")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # CSV
    csv_path = os.path.join(OUTPUT_DIR, "swhid_dataset.csv")
    write_csv(findings, csv_path)
    print(f"  ✅ CSV:             {csv_path}")
    
    # SPDX 3.0 JSON-LD
    spdx_path = os.path.join(OUTPUT_DIR, "full_manifest.jsonld")
    export_to_spdx3(findings, spdx_path)
    print(f"  ✅ SPDX 3.0 JSON-LD: {spdx_path}")
    
    # Findings report
    report_path = os.path.join(OUTPUT_DIR, "findings_report.md")
    write_findings_report(findings, ecosystem_purls, report_path)
    print(f"  ✅ Findings Report:  {report_path}")
    
    # Update dataset README
    total = len(findings)
    verified = sum(1 for f in findings if f.get("status") == "Verified")
    inferred = sum(1 for f in findings if f.get("status") == "Inferred")
    partial = sum(1 for f in findings if f.get("status") == "Partial")
    errors = total - verified - inferred - partial
    
    def pct(c: float) -> str:
        return f"{c/total*100:.1f}%" if total else "0%"
    
    readme_path = os.path.join(OUTPUT_DIR, "README.md")
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(f"""# SWHID Verification Dataset
 
This directory contains the comprehensive SWHID verification dataset mapping
{total} of the most popular packages across 6 ecosystems to their SWHIDs.
 
## Files
 
| File | Description |
| :--- | :--- |
| `swhid_dataset.csv` | Full dataset in CSV format for analysis |
| `full_manifest.jsonld` | SPDX 3.0 JSON-LD manifest with all verified mappings |
| `findings_report.md` | Detailed findings report with per-ecosystem analysis |
| `showcase_manifest.jsonld` | Original 25-package showcase manifest |
 
## Dataset Statistics
 
| Metric | Count | Percentage |
| :--- | ---: | ---: |
| **Total Packages** | {total} | 100% |
| **Verified (High Confidence)** | {verified} | {pct(verified)} |
| **Inferred (Medium Confidence)** | {inferred} | {pct(inferred)} |
| **Partial (Low Confidence)** | {partial} | {pct(partial)} |
| **Errors/Failed** | {errors} | {pct(errors)} |
 
*Generated on {datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")} by `scripts/generate_full_dataset.py`.*
""")
    print(f"  ✅ Dataset README:   {readme_path}")
    
    # Summary
    print("\n" + "=" * 70)
    print("  ✅ Dataset generation complete!")
    print(f"  Total: {total} | Verified: {verified} | Inferred: {inferred} | Partial: {partial} | Errors: {errors}")
    print("=" * 70)


if __name__ == "__main__":
    main()
