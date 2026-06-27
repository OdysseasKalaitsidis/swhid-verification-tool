# SPDX-FileCopyrightText: 2026 Odysseas Kalaitsidis
# SPDX-License-Identifier: MIT

import pytest
from swhid_tool.purl_parser import parse_purl

def test_parse_valid_purls():
    # PyPI
    ecosystem, name, version, qualifiers = parse_purl("pkg:pypi/requests@2.31.0")
    assert ecosystem == "pypi"
    assert name == "requests"
    assert version == "2.31.0"
    assert not qualifiers

    # Cargo
    ecosystem, name, version, qualifiers = parse_purl("pkg:cargo/serde@1.0.203")
    assert ecosystem == "cargo"
    assert name == "serde"
    assert version == "1.0.203"
    assert not qualifiers

    # Maven with namespace
    ecosystem, name, version, qualifiers = parse_purl("pkg:maven/com.fasterxml.jackson.core/jackson-databind@2.17.0")
    assert ecosystem == "maven"
    assert name == "com.fasterxml.jackson.core:jackson-databind"
    assert version == "2.17.0"
    assert not qualifiers

def test_parse_purl_with_qualifiers():
    ecosystem, name, version, qualifiers = parse_purl("pkg:cargo/libc@0.2.155?registry=https://github.com/rust-lang/crates.io-index")
    assert ecosystem == "cargo"
    assert name == "libc"
    assert version == "0.2.155"
    assert qualifiers == {"registry": "https://github.com/rust-lang/crates.io-index"}

def test_parse_invalid_purl():
    with pytest.raises(ValueError):
        parse_purl("invalid_purl_string")

def test_parse_purl_without_version():
    ecosystem, name, version, qualifiers = parse_purl("pkg:pypi/requests")
    assert ecosystem == "pypi"
    assert name == "requests"
    assert version is None
