import json
from datetime import datetime
from typing import Dict, Any, List

def export_to_spdx3(findings: List[Dict[str, Any]], output_path: str):
    """
    Exports verification findings to SPDX 3.0 JSON-LD format.
    """
    spdx_document = {
        "@context": "https://spdx.org/rdf/3.0.0/spdx-context.jsonld",
        "@type": "spdx:SpdxDocument",
        "spdxId": "http://example.org/spdx/doc-1",
        "name": "SWHID Verification Report",
        "creationInfo": {
            "created": datetime.utcnow().isoformat() + "Z",
            "creator": ["Organization: SWHID-POC"]
        },
        "elements": []
    }

    for f in findings:
        package_id = f"http://example.org/spdx/pkg-{f['purl'].replace(':', '-').replace('/', '-')}"
        package = {
            "@type": "spdx:Package",
            "spdxId": package_id,
            "name": f.get("name", f["purl"]),
            "versionInfo": f.get("version", ""),
            "externalIdentifier": [
                {
                    "externalIdentifierType": "purl",
                    "identifier": f["purl"]
                }
            ],
            "contentIdentifier": []
        }

        if "swhid" in f:
            package["contentIdentifier"].append({
                "comment": f"SWHID verified via strategy {f.get('strategy', 'unknown')}",
                "identifier": f["swhid"],
                "identifierType": "swhid"
            })

        spdx_document["elements"].append(package)
        
        # Add relationship
        if "swhid" in f:
            relationship = {
                "@type": "spdx:Relationship",
                "spdxId": f"{package_id}-rel",
                "from": package_id,
                "relationshipType": "hasDistributionArtifact",
                "to": f["swhid"]
            }
            spdx_document["elements"].append(relationship)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(spdx_document, f, indent=2)

    return output_path
