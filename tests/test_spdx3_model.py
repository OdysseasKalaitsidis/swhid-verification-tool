from datetime import datetime
from spdx_tools.spdx3.model.spdx_document import SpdxDocument
from spdx_tools.spdx3.model.creation_info import CreationInfo
from spdx_tools.spdx3.model.organization import Organization
from spdx_tools.spdx3.model.software.package import Package
from spdx_tools.spdx3.model.external_identifier import ExternalIdentifier, ExternalIdentifierType
from spdx_tools.spdx3.model.relationship import Relationship, RelationshipType
from spdx_tools.spdx3.writer.json_ld.json_ld_writer import write_payload

def test_spdx3_creation():
    # 1. Creation Info
    creator = Organization(
        spdx_id="http://example.org/spdx/org-swhid-poc",
        creation_info=None, # Will be set later or omitted in some models
        name="SWHID-POC"
    )
    
    from semantic_version import Version
    from spdx_tools.spdx3.model.profile_identifier import ProfileIdentifierType
    creation_info = CreationInfo(
        created=datetime.now(),
        created_by=[creator.spdx_id],
        spec_version=Version("3.0.0"),
        profile=[ProfileIdentifierType.CORE, ProfileIdentifierType.SOFTWARE]
    )
    
    # 2. Package
    pkg = Package(
        spdx_id="http://example.org/spdx/pkg-six",
        creation_info=creation_info,
        name="six",
        package_version="1.17.0",
        content_identifier="swh:1:dir:8ff44f081d43176474b267de5451f2c2e88089d0"
    )
    
    ext_id = ExternalIdentifier(
        external_identifier_type=ExternalIdentifierType.PURL,
        identifier="pkg:pypi/six@1.17.0"
    )
    pkg.external_identifier = [ext_id]
    
    # 3. Relationship
    rel = Relationship(
        spdx_id="http://example.org/spdx/rel-1",
        creation_info=creation_info,
        from_element=pkg.spdx_id,
        relationship_type=RelationshipType.DISTRIBUTION_ARTIFACT,
        to=[pkg.content_identifier] # Usually relationships are between elements
    )
    
    # 4. Document
    doc = SpdxDocument(
        spdx_id="http://example.org/spdx/doc-1",
        creation_info=creation_info,
        name="Test SPDX 3.0 Document",
        element=[creator.spdx_id, pkg.spdx_id, rel.spdx_id],
        root_element=[pkg.spdx_id]
    )
    
    print("Document created successfully.")
    # try writing to a file
    # write_payload(doc, "test_spdx3.jsonld")

if __name__ == "__main__":
    try:
        test_spdx3_creation()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
