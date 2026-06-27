# SPDX-FileCopyrightText: 2026 Odysseas Kalaitsidis
# SPDX-License-Identifier: MIT

import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from semantic_version import Version

from spdx_tools.spdx3.model.spdx_document import SpdxDocument
from spdx_tools.spdx3.model.creation_info import CreationInfo
from spdx_tools.spdx3.model.organization import Organization
from spdx_tools.spdx3.model.software.package import Package
from spdx_tools.spdx3.model.external_identifier import ExternalIdentifier, ExternalIdentifierType
from spdx_tools.spdx3.model.profile_identifier import ProfileIdentifierType
from spdx_tools.spdx3.payload import Payload
from spdx_tools.spdx3.writer.json_ld.json_ld_writer import write_payload

def export_to_spdx3(findings: List[Dict[str, Any]], output_path: str):
    """
    Exports verification findings to SPDX 3.0 JSON-LD format using spdx-tools models.
    """
    # 1. Setup Creator and CreationInfo
    creator = Organization(
        spdx_id="http://example.org/spdx/org-swhid-poc",
        name="SWHID-POC",
        creation_info=None # Element base class requires this but Organization handles it
    )
    
    creation_info = CreationInfo(
        created=datetime.now(),
        created_by=[creator.spdx_id],
        spec_version=Version("3.0.0"),
        profile=[ProfileIdentifierType.CORE, ProfileIdentifierType.SOFTWARE]
    )
    
    # Update creator with its own creation_info if needed (spdx-tools model quirk)
    # Actually, in this model, elements need creation_info
    creator = Organization(
        spdx_id=creator.spdx_id,
        name=creator.name,
        creation_info=creation_info
    )

    elements = {creator.spdx_id: creator}
    package_ids = []

    for i, f in enumerate(findings):
        purl = f.get("purl")
        if not purl:
            continue
            
        safe_purl = purl.replace(":", "-").replace("/", "-").replace("@", "-")
        package_id = f"http://example.org/spdx/pkg-{safe_purl}-{i}"
        
        # External Identifiers
        external_identifiers = [
            ExternalIdentifier(
                external_identifier_type=ExternalIdentifierType.PURL,
                identifier=purl
            )
        ]
        
        if f.get("swhid"):
            external_identifiers.append(
                ExternalIdentifier(
                    external_identifier_type=ExternalIdentifierType.SWHID,
                    identifier=f["swhid"]
                )
            )

        # Package
        pkg = Package(
            spdx_id=package_id,
            creation_info=creation_info,
            name=f.get("name", purl),
            package_version=f.get("version", ""),
            content_identifier=f.get("swhid"),
            external_identifier=external_identifiers
        )
        elements[package_id] = pkg
        package_ids.append(package_id)


    # 3. Create Document
    doc_id = "http://example.org/spdx/doc-1"
    doc = SpdxDocument(
        spdx_id=doc_id,
        creation_info=creation_info,
        name="SWHID Verification Report",
        element=list(elements.keys()),
        root_element=package_ids
    )
    elements[doc_id] = doc

    # 4. Write Payload
    payload = Payload(spdx_id_map=elements)
    write_payload(payload, output_path)

    return output_path
