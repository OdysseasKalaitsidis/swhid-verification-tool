# SPDX-FileCopyrightText: 2026 Odysseas Kalaitsidis
# SPDX-License-Identifier: MIT

import subprocess
import sys

def test_cli():
    print("Testing CLI...")
    # Test verify-installation
    subprocess.run([sys.executable, "-m", "swhid_tool.cli", "verify-installation"], check=True)
    
    # Test swhid-map (dry run/error case for now)
    subprocess.run([sys.executable, "-m", "swhid_tool.cli", "swhid-map", "pkg:pypi/six@1.17.0"], check=True)

if __name__ == "__main__":
    test_cli()
