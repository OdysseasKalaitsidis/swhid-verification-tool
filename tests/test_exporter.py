from shwid_tool.spdx_exporter import export_to_spdx3
import os

def test_exporter():
    findings = [
        {
            "purl": "pkg:pypi/six@1.17.0",
            "name": "six",
            "version": "1.17.0",
            "swhid": "swh:1:dir:8ff44f081d43176474b267de5451f2c2e88089d0",
            "strategy": "B"
        }
    ]
    output = "findings/test_spdx3_v2.jsonld"
    if not os.path.exists("findings"): os.makedirs("findings")
    
    print(f"Exporting to {output}...")
    export_to_spdx3(findings, output)
    print("Export successful.")

if __name__ == "__main__":
    try:
        test_exporter()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
