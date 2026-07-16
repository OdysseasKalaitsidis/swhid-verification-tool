# SWHID Verification Dataset — Findings Report

*Generated on 2026-07-16 09:39 UTC*

## Executive Summary

This report documents the results of computing and verifying Software Heritage
Identifiers (SWHIDs) for **300 packages** across **6 package
ecosystems**. The dataset covers the most popular packages from PyPI, npm,
Crates.io, Go Modules, Maven Central, and NuGet.

## Overall Results

| Status | Count | Percentage | Meaning |
| :--- | ---: | ---: | :--- |
| ✅ **Verified** | 191 | 63.7% | Exact SWHID match confirmed in SWH archive |
| 🟡 **Inferred** | 43 | 14.3% | Repository archived, but specific version tag not found |
| 🟠 **Partial** | 51 | 17.0% | Local SWHID computed, not yet confirmed in archive |
| 🔴 **Error/Failed** | 15 | 5.0% | Resolution failed (network, missing data, unsupported) |
| **Total** | **300** | **100%** | |

## Per-Ecosystem Breakdown

| Ecosystem | Total | ✅ Verified | 🟡 Inferred | 🟠 Partial | 🔴 Error | Verification Rate |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| **PyPI** | 50 | 50 | 0 | 0 | 0 | 100% |
| **npm** | 50 | 50 | 0 | 0 | 0 | 100% |
| **Crates.io** | 50 | 0 | 0 | 50 | 0 | 0% |
| **Go Modules** | 50 | 37 | 0 | 0 | 13 | 74% |
| **Maven Central** | 50 | 4 | 43 | 1 | 2 | 8% |
| **NuGet** | 50 | 50 | 0 | 0 | 0 | 100% |

## Strategy Distribution

Which verification strategy succeeded for resolved packages:

| Strategy | Count | Description |
| :--- | ---: | :--- |
| **A** | 28 | Attestation-based (e.g., Sigstore/PEP 740 commit SHA extraction) |
| **B** | 137 | Metadata-based (repository URL + version tag matching in SWH snapshot) |
| **C** | 22 | File-level (download artifact, normalize, compute directory SWHID) |
| **N/A** | 113 | No strategy succeeded |

## Key Finding: The Registry-VCS Gap

The most significant finding from this dataset is that **package registry artifacts
are structurally different from VCS (git) repository snapshots**. This creates a
fundamental obstacle to PURL→SWHID mapping:

1. **PyPI**: sdist tarballs contain `PKG-INFO`, `setup.cfg`, and other metadata files
   that don't exist in the git repository.
2. **Cargo**: Crates.io adds `.cargo_vcs_info.json` and replaces `Cargo.toml` with a
   normalized version (the original is saved as `Cargo.toml.orig`).
3. **Maven**: JAR files contain compiled bytecode and manifest files absent from source.
4. **npm**: Tarballs include auto-generated files and normalized `package.json`.
5. **NuGet**: `.nupkg` files include `.nuspec`, content-type XML, and relationship metadata.

This means a **naive SWHID computation on a registry artifact will never match
the SWHID of the same code archived in Software Heritage from git**. Ecosystem-specific
normalization strategies are required to bridge this gap.

## Methodology

For each package, the tool applies a cascade of verification strategies in
descending order of confidence:

1. **Strategy A (Attestation)**: Extract cryptographic commit SHAs from Sigstore/PEP 740
   attestations, then verify the `swh:1:rev:` SWHID exists in the archive.
2. **Strategy B (Metadata + Tag Matching)**: Extract the source repository URL from
   registry metadata, check if SWH has archived it, and match version tags in the
   archived snapshot to find the exact revision.
3. **Strategy C (File-Level)**: Download the artifact, normalize it (strip registry
   additions), compute a `swh:1:dir:` SWHID, and check if it exists in SWH.

## Verified Packages

| Package | SWHID | Strategy |
| :--- | :--- | :--- |
| `pkg:pypi/boto3@1.43.49` | `swh:1:dir:37919af86effb6ed857a0058d0c19bbb6171287b` | C |
| `pkg:pypi/packaging@26.2` | `swh:1:rev:9bfe549d54c8e83441f00860e0d3cdd63b865e26` | A |
| `pkg:pypi/urllib3@2.7.0` | `swh:1:rev:9a950b92d999f906b6020bb2d1076ee56cddd5d2` | A |
| `pkg:pypi/certifi@2026.6.17` | `swh:1:rev:d0ac52f3d93a514224197c7efb66c41b1beae5d1` | A |
| `pkg:pypi/idna@3.18` | `swh:1:rev:f39ea903ba49eb5a0b2c6723c9a929b41ed4a0f1` | A |
| `pkg:pypi/requests@2.34.2` | `swh:1:rev:6e83187b8feb273ed4c6cdab5efd8d54901dfab3` | A |
| `pkg:pypi/typing-extensions@4.16.0` | `swh:1:rev:f29cd28d8ed7642cafb1d18daf5aa41be6a5c0aa` | A |
| `pkg:pypi/charset-normalizer@3.4.9` | `swh:1:rev:cc6840753f17f00dea4e339ce37507747217e916` | A |
| `pkg:pypi/botocore@1.43.49` | `swh:1:dir:43c1568464f0ea17c08422888b729ec0da448259` | C |
| `pkg:pypi/setuptools@83.0.0` | `swh:1:dir:591ac487624a08e9b80726a5aa418ca381c46e11` | C |
| `pkg:pypi/cryptography@49.0.0` | `swh:1:rev:e300bbe2f1bec75e5ee7e0ab7b196958831b3db6` | A |
| `pkg:pypi/aiobotocore@3.7.0` | `swh:1:rev:4013f139e197d1613b649a7d9eae0b62f98cef9b` | A |
| `pkg:pypi/pygments@2.20.0` | `swh:1:dir:c24396e4bb3ea974091ca8ff6159da1fab4d469a` | C |
| `pkg:pypi/pluggy@1.6.0` | `swh:1:rev:fd08ab5f811a9b2fa9124ae8cbbd393221151e2c` | A |
| `pkg:pypi/python-dateutil@2.9.0.post0` | `swh:1:dir:19f309b83402019b13f082ab6127c2d284258d0a` | C |
| `pkg:pypi/six@1.17.0` | `swh:1:dir:e843f002004836aa974760068a0592b6d77dca9d` | C |
| `pkg:pypi/pyyaml@6.0.3` | `swh:1:dir:586a31253655b335b033fa67e2af219cdb8bc0c3` | C |
| `pkg:pypi/numpy@2.5.1` | `swh:1:rev:115e239fad506b454702f615b542105f97299754` | A |
| `pkg:pypi/cffi@2.1.0` | `swh:1:dir:b41abc3bc5a064811b8a573f9358d9988c283461` | C |
| `pkg:pypi/pydantic@2.13.4` | `swh:1:rev:cf67d4b3193c3fe43ede18612ed62785eee11382` | A |
| `pkg:pypi/pytest@9.1.1` | `swh:1:rev:cf470ec0bf7eb89cd97dd56df4859eae5db46447` | A |
| `pkg:pypi/click@8.4.2` | `swh:1:rev:b2e30a175449cfda909ee4fbf4a29a6a071cad53` | A |
| `pkg:pypi/pycparser@3.0` | `swh:1:dir:8162e2217220173ccafd5bd4b9eeb49d5312e367` | C |
| `pkg:pypi/iniconfig@2.3.0` | `swh:1:rev:7faed13ae50bad7c5da3f5782f254a8a7736bb84` | A |
| `pkg:pypi/grpcio-status@1.82.1` | `swh:1:dir:796b309053629d595d99b73a69bf5a27ecfc48a0` | C |
| `pkg:pypi/pydantic-core@2.47.0` | `swh:1:dir:9db552c2f06c373859e41e27ee373fd89b8cfc16` | C |
| `pkg:pypi/anyio@4.14.2` | `swh:1:rev:c384f99687c64c59ed8a11c3a0f11a2d57daff71` | A |
| `pkg:pypi/s3transfer@0.19.1` | `swh:1:dir:de301816d271ee75992272c5e44093ab05164ec2` | C |
| `pkg:pypi/attrs@26.1.0` | `swh:1:rev:7bfc49e9b22d5ba25b6e429524c3d49fee27cb36` | A |
| `pkg:pypi/protobuf@7.35.1` | `swh:1:dir:da2bdd98ce6d573c03d5590689316da23a71de5f` | C |
| `pkg:pypi/h11@0.16.0` | `swh:1:dir:6290b4fea1e2b39548361bce35e9fe6ef1f5d160` | C |
| `pkg:pypi/fsspec@2026.6.0` | `swh:1:dir:8f29b618b486ad4cfe1f85eabd1d5e4d60934125` | C |
| `pkg:pypi/annotated-types@0.7.0` | `swh:1:dir:1fc3d737075ba081c7264555ce6abcb5ad8f6fd6` | C |
| `pkg:pypi/pandas@3.0.3` | `swh:1:rev:72f2fea91530b5abb3cf2100cb22d84e504695c0` | A |
| `pkg:pypi/s3fs@2026.6.0` | `swh:1:dir:ecd7a2ae142a6ecf0498557dd7f686d9ae248f13` | C |
| `pkg:pypi/markupsafe@3.0.3` | `swh:1:rev:297fc8e356e6836a62087949245d09a28e9f1b13` | A |
| `pkg:pypi/httpx@0.28.1` | `swh:1:dir:c60bb5d45e5b5785b7dcd7f1f6f80cdd963e425a` | C |
| `pkg:pypi/httpcore@1.0.9` | `swh:1:dir:2e37d2f4c0b2b80aad48be3dd55299eb083d8764` | C |
| `pkg:pypi/platformdirs@4.10.0` | `swh:1:rev:078bc61171e1a0cfbb3f210ff0fd30795a359664` | A |
| `pkg:pypi/typing-inspection@0.4.2` | `swh:1:rev:8db011350942f33ac4b5d7db60d4d9ea83ab480f` | A |
| `pkg:pypi/jinja2@3.1.6` | `swh:1:rev:15206881c006c79667fe5154fe80c01c65410679` | A |
| `pkg:pypi/python-dotenv@1.2.2` | `swh:1:rev:36004e0e34be7665ff2b11a8a4005144f76f176d` | A |
| `pkg:pypi/pip@26.1.2` | `swh:1:rev:31d7d168953668aad85154d6121879d07fbeac27` | A |
| `pkg:pypi/filelock@3.30.0` | `swh:1:rev:1b094069044a3f2a39173ae841eb22b274833ff9` | A |
| `pkg:pypi/pathspec@1.1.1` | `swh:1:rev:ecf71a99ca739479d450b9830f43416ea0c519c7` | A |
| `pkg:pypi/pyjwt@2.13.0` | `swh:1:rev:7144e4534c34810f4525dc4578a32addd8212cff` | A |
| `pkg:pypi/litellm@1.92.0` | `swh:1:dir:17bc4d5183e70b2b9f2cc5c48e1355c9b29b8a02` | C |
| `pkg:pypi/aiohttp@3.14.1` | `swh:1:rev:9c35d03aa5fecd294510196e07f176f1a2e7fa33` | A |
| `pkg:pypi/rich@15.0.0` | `swh:1:dir:74a1fbb26c744f54d4aa3b18dbb354c0d48cd62e` | C |
| `pkg:pypi/jmespath@1.1.0` | `swh:1:dir:4707b99549c937a40304461dc47113cf813c5e3a` | C |
| `pkg:npm/lodash@4.18.1` | `swh:1:dir:bc9f374aca1463aba17f41c0e43a889020e39a53` | B |
| `pkg:npm/chalk@5.6.2` | `swh:1:dir:f4a4d48b46b69f5ef9488e2dfbdcabba7c151bcf` | B |
| `pkg:npm/react@19.2.7` | `swh:1:dir:76e3ff0a32582da0b3a387d6399f7b49e4da3766` | B |
| `pkg:npm/express@5.2.1` | `swh:1:dir:e34b0a188c9788483fdd0e8bd4bf0754a6c789b7` | B |
| `pkg:npm/commander@15.0.0` | `swh:1:dir:b56f28ac5940bedad711a84a06ce08bd2df9b155` | B |
| `pkg:npm/moment@2.30.1` | `swh:1:dir:1fa8660b7b021912c12255f662d421470871adb0` | B |
| `pkg:npm/debug@4.4.3` | `swh:1:dir:36f14d19ac67cab45b1de78cbdee960fb78b38fe` | B |
| `pkg:npm/async@3.2.6` | `swh:1:dir:f01b03a4ab83e661a3d5a5fb0646e8575e490d5a` | B |
| `pkg:npm/bluebird@3.7.2` | `swh:1:dir:894b0e4dda05072f77ee777601cc8d9779327196` | B |
| `pkg:npm/request@2.88.2` | `swh:1:dir:5cfa99939d46cbfeba44490c453e5b12bec8578e` | B |
| `pkg:npm/underscore@1.13.8` | `swh:1:dir:711c037f8260be344ca2eea2227abfa66fa182bc` | B |
| `pkg:npm/uuid@14.0.1` | `swh:1:dir:5c3978645f57efdd4759927706fb7a647cc08026` | B |
| `pkg:npm/axios@1.18.1` | `swh:1:dir:1df870b4126d3b8821cb37e444348d30a4fc184d` | B |
| `pkg:npm/glob@13.0.6` | `swh:1:dir:1754c307f01a7f7793cd3327f9882a28d87c55a2` | B |
| `pkg:npm/mkdirp@3.0.1` | `swh:1:dir:3a60d3ee462e0483fc81e4c24ecc63b6afa40950` | B |
| `pkg:npm/minimist@1.2.8` | `swh:1:dir:c61a58ccc3002d1fa2d8854d6783aecf86dc0565` | B |
| `pkg:npm/semver@7.8.5` | `swh:1:dir:b3dad436463f171df2f6de973c3c9f7e245ff5c8` | B |
| `pkg:npm/colors@1.4.0` | `swh:1:dir:35e3048093e1ea9cb11d50a9370eb5cae226950e` | B |
| `pkg:npm/body-parser@2.3.0` | `swh:1:dir:4dc124b334a5af113bc88a8d45b348aafcdfc019` | B |
| `pkg:npm/through2@5.0.5` | `swh:1:dir:f24ce2229220f73a2f313664c2579b45dcc647fb` | B |
| `pkg:npm/yargs@18.0.0` | `swh:1:dir:b58eb14ac1a0fce9885441e5c639ee34b675a799` | B |
| `pkg:npm/fs-extra@11.3.6` | `swh:1:dir:af0c6540a6cd01b56d713da654084fdac619dba4` | B |
| `pkg:npm/inquirer@14.0.2` | `swh:1:dir:90415b7a7c02d54ace96efff22f89847f7cd4d4d` | B |
| `pkg:npm/webpack@5.108.4` | `swh:1:dir:5a892268cde802870e2a17b6660d70090ea30c83` | B |
| `pkg:npm/prop-types@15.8.1` | `swh:1:dir:c62bd8ec5657b52dde18577a218167cf7a6e2169` | B |
| `pkg:npm/rxjs@7.8.2` | `swh:1:dir:dc10bd8d2a24e2283b29cf66424cf9359fefda6d` | B |
| `pkg:npm/tslib@2.8.1` | `swh:1:dir:bf34c0ce4a3a0b594830750ea5e3189ee512741d` | B |
| `pkg:npm/core-js@3.49.0` | `swh:1:dir:77f3c1a646805327c62b65c8c43e393b87965e55` | B |
| `pkg:npm/classnames@2.5.1` | `swh:1:dir:d9b37f4f26e0b363f59a515a4f6eb56033e60b78` | B |
| `pkg:npm/jquery@4.0.0` | `swh:1:dir:39da88c5104b8b8c570abe104edfeeefb6a0e1a9` | B |
| `pkg:npm/ws@8.21.1` | `swh:1:dir:c1879cdd73c374e026a79fcf0fbbe91e7e54939e` | B |
| `pkg:npm/cheerio@1.2.0` | `swh:1:dir:78f1652dcf42e3b6ee0db2dcec1c187a7c8610bc` | B |
| `pkg:npm/rimraf@6.1.3` | `swh:1:dir:aa9d30738689835d90cd99d1c0954d0a889d3638` | B |
| `pkg:npm/dotenv@17.4.2` | `swh:1:dir:e31e54609e4a08943282582376d8da62195a557f` | B |
| `pkg:npm/eslint@10.7.0` | `swh:1:dir:a7b36380164af48dc35073e2ca074e3ec789557c` | B |
| `pkg:npm/prettier@3.9.5` | `swh:1:dir:7e42b78ed56e7b4fa4d62c3fd334365b902f095d` | B |
| `pkg:npm/typescript@7.0.2` | `swh:1:dir:3428cd50c725565a935932020c175af17fce43d7` | B |
| `pkg:npm/mocha@11.7.6` | `swh:1:dir:23a9884599da3dbc9d2aa1cfd1b777feb31d7990` | B |
| `pkg:npm/jest@30.4.2` | `swh:1:dir:5917417e9c4721f027d2a4ec060751617469ba14` | B |
| `pkg:npm/babel-core@6.26.3` | `swh:1:dir:82244068437b4dc7ad6f0c41a37059b93ed4c5e4` | B |
| `pkg:npm/ora@9.4.1` | `swh:1:dir:14ab880c1081b1d490c7e893581de7cba260a531` | B |
| `pkg:npm/execa@9.6.1` | `swh:1:dir:031af022b0adaadbbf15744273d68735a12d108f` | B |
| `pkg:npm/nano@11.0.6` | `swh:1:dir:5c0713e388a74eb918af4d86a7f9809bc4d0f6af` | B |
| `pkg:npm/passport@0.7.0` | `swh:1:dir:e4ed8f3a5d46f6c3d89e0d9d5cdb86fee71bc9f8` | B |
| `pkg:npm/mongoose@9.7.4` | `swh:1:dir:0262231aeadbe24b9778c2d15c0c0aac2429099e` | B |
| `pkg:npm/redis@6.1.0` | `swh:1:dir:61531b6e5b6963a60602391b777db3b9517b1e75` | B |
| `pkg:npm/pg@8.22.0` | `swh:1:dir:10bb8bf7a1cb9008bf694b44b49d9b2456641d67` | B |
| `pkg:npm/mysql2@3.23.0` | `swh:1:dir:848903e3d1d896e8b8cfc68e488e865afee054af` | B |
| `pkg:npm/socket.io@4.8.3` | `swh:1:dir:32dcbc8d7bfa2212a8e66a8f7e70b2d5964fff04` | B |
| `pkg:npm/cors@2.8.6` | `swh:1:dir:f9b7fa70774128bd1566efebed7d67b7c78394ad` | B |
| `pkg:golang/github.com/gin-gonic/gin@v1.9.0` | `swh:1:dir:5836ecd2f6866038f6d2481acdbe80b401861e25` | B |
| `pkg:golang/github.com/sirupsen/logrus@v1.9.3` | `swh:1:dir:c12a219d47e40b7ec9ec0d2fe415b6b5dee02ee6` | B |
| `pkg:golang/golang.org/x/text@v0.14.0` | `swh:1:dir:d072db728aedc21566b6765e7c7076d694c32ef4` | B |
| `pkg:golang/github.com/spf13/cobra@v1.8.0` | `swh:1:dir:db27fbf14d40d1f841102990f3550b4c28b9768b` | B |
| `pkg:golang/github.com/stretchr/testify@v1.9.0` | `swh:1:dir:6e4269731b71bb42a2ac8f6621c0ae54799a7abb` | B |
| `pkg:golang/github.com/gorilla/mux@v1.8.1` | `swh:1:dir:f8d5a04a419e836156cccec093412c42f489405b` | B |
| `pkg:golang/github.com/spf13/viper@v1.18.2` | `swh:1:dir:4d43133d15109446bcd666a1aab94fe17a4da03a` | B |
| `pkg:golang/google.golang.org/grpc@v1.62.1` | `swh:1:dir:fa99f0c874e21d192fd33c5bd6866e453706f945` | B |
| `pkg:golang/github.com/prometheus/client_golang@v1.19.0` | `swh:1:dir:e79e400022468a14ae80ec08635e32ab1dc4827b` | B |
| `pkg:golang/github.com/stretchr/objx@v0.5.2` | `swh:1:dir:9f76c065f3e4292bbc25b7e750b53eab3c1a14b5` | B |
| `pkg:golang/go.uber.org/zap@v1.27.0` | `swh:1:dir:e0f2deffdb5d3c090dd020c3dcf7f939febe6610` | B |
| `pkg:golang/github.com/golang/protobuf@v1.5.4` | `swh:1:dir:64084f2998fc3246f47d720109049f91add93c26` | B |
| `pkg:golang/github.com/google/uuid@v1.6.0` | `swh:1:dir:cc4703efbb8a436cb8cfe07d9f7740dae03090dc` | B |
| `pkg:golang/github.com/pkg/errors@v0.9.1` | `swh:1:dir:dd0db94cf1cb171e0b1524b376294d8b1d4c7abb` | B |
| `pkg:golang/github.com/fatih/color@v1.16.0` | `swh:1:dir:55cd5f0568678ba7cd4c670f371b095241590878` | B |
| `pkg:golang/github.com/mitchellh/mapstructure@v1.5.0` | `swh:1:dir:fbdff7fea2e719bc1ab8aa88414d5788075e0ac6` | B |
| `pkg:golang/github.com/aws/aws-sdk-go@v1.51.6` | `swh:1:dir:51411f59eb5656d9ac2131c9a1ba144264fb3ec8` | B |
| `pkg:golang/github.com/hashicorp/consul@v1.18.1` | `swh:1:dir:a44f82074a41ec098f8421278b0c8dbafa649814` | B |
| `pkg:golang/github.com/lib/pq@v1.10.9` | `swh:1:dir:b57c900d0a8daf9f6fd4cf5e104fb3c64b92c6c0` | B |
| `pkg:golang/github.com/go-sql-driver/mysql@v1.8.1` | `swh:1:dir:95921b72dbbeda0013fece7c82a1b87b0d5df514` | B |
| `pkg:golang/github.com/gorilla/websocket@v1.5.1` | `swh:1:dir:7fd1e4cc484b3b18292dd0e1371a472946627cd2` | B |
| `pkg:golang/golang.org/x/crypto@v0.21.0` | `swh:1:dir:c78fba02e71033faf8d6ef46dad83a1d33e3a82d` | B |
| `pkg:golang/golang.org/x/net@v0.22.0` | `swh:1:dir:2d2d3d4c88f7565fbdc8c7e6409a9792ff22d5ce` | B |
| `pkg:golang/golang.org/x/sys@v0.18.0` | `swh:1:dir:da276610e791f12cff7647b0714a03062bc7a706` | B |
| `pkg:golang/golang.org/x/tools@v0.19.0` | `swh:1:dir:b4cc10afd43eaa258b7cb24700ca8927db947ad9` | B |
| `pkg:golang/github.com/rs/zerolog@v1.32.0` | `swh:1:dir:e7a2a2b344ecd522f37d7c7d5cbf11e7cdf7cc59` | B |
| `pkg:golang/github.com/nats-io/nats.go@v1.34.0` | `swh:1:dir:ceb0c4fa9df33ec59226b72977bb41cecce2412f` | B |
| `pkg:golang/github.com/tidwall/gjson@v1.17.1` | `swh:1:dir:935d71b1e3fc4ce2409bff13e0b39937ee7461a6` | B |
| `pkg:golang/github.com/gin-contrib/cors@v1.6.0` | `swh:1:dir:9d1a0d0a1d08e264cc07b8fd785bb23ce75a881f` | B |
| `pkg:golang/github.com/go-kit/kit@v0.13.0` | `swh:1:dir:7a600926279d870c7e1667f771351faa9a40558e` | B |
| `pkg:golang/github.com/gogo/protobuf@v1.3.2` | `swh:1:dir:cf2bc48b35233d539280e14243976674590faec5` | B |
| `pkg:golang/github.com/hashicorp/go-hclog@v1.6.2` | `swh:1:dir:4b94e9e3dcb34a4fa413ed06a3cb11adfc61e71f` | B |
| `pkg:golang/github.com/joho/godotenv@v1.5.1` | `swh:1:dir:df09f0777e3d2c56543897e1f3d0dfc775e95666` | B |
| `pkg:golang/github.com/DATA-DOG/go-sqlmock@v1.5.2` | `swh:1:dir:af0bc28f9c28f37a8bd0921d57971c6a730d16a1` | B |
| `pkg:golang/github.com/uber-go/fx@v1.21.0` | `swh:1:dir:79705861e9c4ccd06ac3ab5ac2d61c53b4da845a` | B |
| `pkg:golang/github.com/shopspring/decimal@v1.3.1` | `swh:1:dir:2e813fb75787cdf0e881261857833a7d142b1d6c` | B |
| `pkg:golang/github.com/jmoiron/sqlx@v1.3.5` | `swh:1:dir:f774a6e36b612fb93f591972699de76b46e1f6b7` | B |
| `pkg:maven/com.fasterxml.jackson.core/jackson-databind@2.17.0` | `swh:1:cnt:8f92a35d1b18d9e28afb948ba0e143e8553b50a1` | N/A |
| `pkg:maven/com.fasterxml.jackson.core/jackson-core@2.17.0` | `swh:1:cnt:888fb8b9581020cfbd653b010c4f9fd0295a2350` | N/A |
| `pkg:maven/com.zaxxer/HikariCP@5.1.0` | `swh:1:cnt:dd7142a690e28a2e6f78ca4d87263fec961b8b01` | N/A |
| `pkg:maven/javax.servlet/javax.servlet-api@4.0.1` | `swh:1:cnt:2140916e713e0ec66c93dcef71ea767c436091f0` | N/A |
| `pkg:nuget/Newtonsoft.Json@13.0.4` | `swh:1:dir:96556403304e16c9624e425c6f116d1196bcfc20` | B |
| `pkg:nuget/System.Text.Json@10.0.10` | `swh:1:dir:49f77368f8c5d56fc4218b06f04e6472fd31ea1f` | B |
| `pkg:nuget/Serilog@4.4.0` | `swh:1:dir:d46679d55cd0f44244b4801a5423632c28898721` | B |
| `pkg:nuget/AutoMapper@16.2.0` | `swh:1:dir:2e905f59dc882afc29fc807005ee2e6b351c29e5` | B |
| `pkg:nuget/FluentValidation@12.1.1` | `swh:1:dir:52d8db109b352b71f73b297f029c3b2cf1f1404f` | B |
| `pkg:nuget/Dapper@2.1.79` | `swh:1:dir:7a83e66478c042c6a7fb40a9ffbbf0ca17711bf5` | B |
| `pkg:nuget/MediatR@14.2.0` | `swh:1:dir:3e25e5c96b8da579378ee0f2f6d652b4cbc2224a` | B |
| `pkg:nuget/Polly@8.7.0` | `swh:1:dir:4c808de4c94dabd2cb8853e3ba6f42b1eddee9ae` | B |
| `pkg:nuget/Swashbuckle.AspNetCore@10.2.3` | `swh:1:dir:23cbf7516c495c473b808e8372cbc906ebcd3510` | B |
| `pkg:nuget/xunit@2.9.3` | `swh:1:dir:62854c12b96f50f3f27ee3dd9b7b1d6316652635` | B |
| `pkg:nuget/NUnit@4.6.1` | `swh:1:dir:7d09403210ad93aeab1027363cb634095ee8b318` | B |
| `pkg:nuget/Moq@4.20.72` | `swh:1:dir:ab5c2eea1699fbbfa261d4b22abe5765116c80a7` | B |
| `pkg:nuget/FluentAssertions@8.10.0` | `swh:1:dir:9c0f59fc05246b4945d56ffa9a731b480bb06758` | B |
| `pkg:nuget/Bogus@35.6.5` | `swh:1:dir:731355629d83f5c0e1d0183679540002c8890d1a` | B |
| `pkg:nuget/Humanizer.Core@3.0.10` | `swh:1:dir:431692e181aec79ba6ae5dbff78ccc28c55b3b76` | B |
| `pkg:nuget/CsvHelper@33.1.0` | `swh:1:dir:712e5853af99b70ba1170d27394689889f6e24ea` | B |
| `pkg:nuget/RestSharp@114.0.0` | `swh:1:dir:0eb44c13d2d08e756d86108e3783a468568ce339` | B |
| `pkg:nuget/MailKit@4.17.0` | `swh:1:dir:f4185ef4029da26a89f9fd12d3bbb019fcc78473` | B |
| `pkg:nuget/HtmlAgilityPack@1.12.4` | `swh:1:dir:4149efbc26e35caa6ab0e9841529350107ded6c7` | B |
| `pkg:nuget/Npgsql@10.0.3` | `swh:1:dir:b8fc919e72164a9474a2c738e6628f2950429ee1` | B |
| `pkg:nuget/StackExchange.Redis@3.0.17` | `swh:1:dir:955e2cf94876b6da20ae62bfdef987288488c097` | B |
| `pkg:nuget/MongoDB.Driver@3.10.0` | `swh:1:dir:7a3f2b15d5e8fd2523412dbbac7e3f7dee958281` | B |
| `pkg:nuget/EntityFramework@6.5.2` | `swh:1:dir:b1a65aeaaf8a233109da2052d9cc2896aa999959` | B |
| `pkg:nuget/Microsoft.EntityFrameworkCore@10.0.10` | `swh:1:dir:cb19449f09be69034b3da7e0156e04668d8bc4a5` | B |
| `pkg:nuget/Hangfire.Core@1.8.23` | `swh:1:dir:99cdec2095c97e82d50ccd51b4b492836ef474bc` | B |
| `pkg:nuget/MassTransit@9.1.2` | `swh:1:dir:1380658af4bc6da55a97c98732f1f5a07ad48776` | B |
| `pkg:nuget/NLog@6.1.4` | `swh:1:dir:9d73c7f373d807833a53b4367eafe3c85e29c18a` | B |
| `pkg:nuget/log4net@3.3.2` | `swh:1:dir:acc8b4c238cced9e75c77084597c2387692a2f9b` | B |
| `pkg:nuget/Autofac@9.3.1` | `swh:1:dir:6baf547bb51f9918df85accd25a6a24fe990f272` | B |
| `pkg:nuget/Grpc.Net.Client@2.80.0` | `swh:1:dir:54d449e00768f6939f41582fbd6f2d757b3509a2` | B |
| `pkg:nuget/protobuf-net@3.2.56` | `swh:1:dir:417defa4d063f22baac5aa65c1e4558e8fdc24af` | B |
| `pkg:nuget/MessagePack@3.1.8` | `swh:1:dir:eebc6deca359e398295c6728710351d42ac7e9b4` | B |
| `pkg:nuget/BenchmarkDotNet@0.15.8` | `swh:1:dir:5445d6501bfd30d5f993639b216194c5e40c431d` | B |
| `pkg:nuget/Shouldly@4.3.0` | `swh:1:dir:a99cfa35e80b3c9cb6eb5cf0fe8dbae50d2d457d` | B |
| `pkg:nuget/AngleSharp@1.5.2` | `swh:1:dir:2d3cbded8f2767e034385443478fd3f331f40d34` | B |
| `pkg:nuget/SixLabors.ImageSharp@4.0.0` | `swh:1:dir:ea1a6cb7d0461ab87b60c1cd0a5fd1b1eca641da` | B |
| `pkg:nuget/SkiaSharp@4.150.1` | `swh:1:dir:1f053a9630e742d8e7a4cc0dcf480dacfbe9ae96` | B |
| `pkg:nuget/Markdig@1.3.2` | `swh:1:dir:ef7335e43b1802e2c1ac24d5bb425e49a869d26f` | B |
| `pkg:nuget/YamlDotNet@18.1.0` | `swh:1:dir:b9ffdad5c09288d55172432f9aba9ec4c0abf35e` | B |
| `pkg:nuget/Jint@4.13.0` | `swh:1:dir:b90e7595e638a586fca00c58db365c78231f37a7` | B |
| `pkg:nuget/MiniProfiler.AspNetCore.Mvc@4.5.4` | `swh:1:dir:30bcc34dea2764972e9f4918624779ce08dec560` | B |
| `pkg:nuget/AWSSDK.Core@4.0.100.5` | `swh:1:dir:8b0926a57f7f4d8df25465cc9a2482e0c31bc5cb` | B |
| `pkg:nuget/Azure.Storage.Blobs@12.29.1` | `swh:1:dir:60844fc15452cd23e57ed5e1ed890908b88894bd` | B |
| `pkg:nuget/Google.Cloud.Storage.V1@4.15.0` | `swh:1:dir:b3fad3bfd82ce6bd72d945b049aa9440bc70ede2` | B |
| `pkg:nuget/NSwag.AspNetCore@14.7.1` | `swh:1:dir:76a76b76856fe92c3d86eea128fcaf5002510637` | B |
| `pkg:nuget/Scrutor@7.0.0` | `swh:1:dir:25e0ee1d9867016e6c1b2b196e21bbc897da0b15` | B |
| `pkg:nuget/Mapster@10.0.11` | `swh:1:dir:e18a72c034e6fd9f1568dced405e7b27467e48e9` | B |
| `pkg:nuget/Refit@13.1.0` | `swh:1:dir:59bd0a79b15461e07e39422d66980d147b4403b7` | B |
| `pkg:nuget/LazyCache@2.4.0` | `swh:1:dir:89ddd9afbebe35a722bd37e9e1c86556b3dec997` | B |
| `pkg:nuget/EFCore.BulkExtensions@10.0.1` | `swh:1:dir:60a6e9ce826a43ebd298df8131d6f74a50984603` | B |

## Error Summary

| Package | Reason |
| :--- | :--- |
| `pkg:golang/github.com/go-chi/chi@v5.0.12` | Could not download zip from Go Proxy: 404 |
| `pkg:golang/github.com/go-redis/redis@v8.11.5` | Could not download zip from Go Proxy: 404 |
| `pkg:golang/github.com/docker/docker@v25.0.5` | Could not download zip from Go Proxy: 404 |
| `pkg:golang/github.com/jackc/pgx@v5.5.5` | Could not download zip from Go Proxy: 404 |
| `pkg:golang/github.com/labstack/echo@v4.11.4` | Could not download zip from Go Proxy: 404 |
| `pkg:golang/github.com/go-playground/validator@v10.19.0` | Could not download zip from Go Proxy: 404 |
| `pkg:golang/github.com/patrickmn/go-cache@v2.1.0` | Could not download zip from Go Proxy: 404 |
| `pkg:golang/github.com/dgrijalva/jwt-go@v3.2.0` | Could not download zip from Go Proxy: 404 |
| `pkg:golang/github.com/gofiber/fiber@v2.52.2` | Could not download zip from Go Proxy: 404 |
| `pkg:golang/github.com/pelletier/go-toml@v2.1.1` | Could not download zip from Go Proxy: 404 |
| `pkg:golang/github.com/cespare/xxhash@v2.2.0` | Could not download zip from Go Proxy: 404 |
| `pkg:golang/github.com/golang-migrate/migrate@v4.17.0` | Could not download zip from Go Proxy: 404 |
| `pkg:golang/github.com/grpc-ecosystem/grpc-gateway@v2.19.1` | Could not download zip from Go Proxy: 404 |
| `pkg:maven/io.netty/netty-all@4.1.108.Final` | No sources.jar found |
| `pkg:maven/org.hibernate/hibernate-core@6.4.4.Final` | No sources.jar found |

## Reproducibility

To reproduce this dataset:

```bash
# Clone and setup
git clone https://github.com/OdysseasKalaitsidis/SWHID_POC
cd SWHID_POC && pip install -e .

# Optional: set SWH API token for higher rate limits
export SWH_AUTH_TOKEN=your_token_here

# Generate the dataset
python3 scripts/generate_full_dataset.py
```

---

*This dataset was generated by the [SWHID Verification Tool](https://github.com/OdysseasKalaitsidis/SWHID_POC).*
