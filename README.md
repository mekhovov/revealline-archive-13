# RevealLine archive 13

This repository preserves the original **v0.54.0 and v0.55.0** games at:

- `https://mekhovov.github.io/revealline-archive-13/releases/v0.54.0/site/game/`
- `https://mekhovov.github.io/revealline-archive-13/releases/v0.55.0/site/game/`

`source-lock.json` v2 declares both original tag objects, source revisions, ZIP
hashes and metadata pins. The v0.54.0 cohort retains all three original metadata
files and all 650 canonical rows from infrastructure `03986d7`. The v0.55.0
cohort is bound to annotated tag `253ed21b6897a0784ba3d8d2b871c952fee90451`,
source `acc9f265b651017fd268ffd8bbe6989bec614c41`, and the original published
metadata committed in main `da4459b706555007468d053a578caa215d08eca3`.
`input-authority.json` records that finite metadata derivation and its limits.

The workflow sequentially downloads the two original GitHub Release ZIPs. It
uses the unchanged bounded extractor pinned to source commit
`0594b60136db000c9d6c87527c7885c2c51a2562`, verifies the whole ZIP and every
member's CRC, size and SHA256, and preserves the original worker and assets.
No game source is rebuilt and no release/tag is moved. All cohort metadata and
Git identities are checked before the first download and again before success.
Each ZIP receipt also has to match its cohort's identities. The extractor removes
its temporary ZIP before processing the next version.

`expected-inventory.json` includes every canonical body, hidden build marker,
original manifest/checksum and release record. It is independently reconstructed
from both pinned metadata cohorts before extraction. Two complete body reads
must then match all **1,303 files / 624,422,286 bytes** before Pages upload, below
the unchanged **800,000,000-byte** artifact cap (175,577,714 bytes spare).
The downloadable ZIPs remain on the original GitHub Releases.

The infrastructure-owned `releases/index.html` sends the frozen games’ Release
explorer action to `https://mekhovov.github.io/revealline/releases/`, with an
explicit visible link as well as refresh. The preceding 1,302-file deployment
passed its exact HTTP inventory, but native browser testing found that this omitted
route returned 404. That byte audit is retained with routing acceptance false.
This added page is included in metadata derivation and both complete artifact
reads; neither original game is rewritten. New hosted/public/native verification
is required before controller admission.

Actual preparation requires **3 GiB free** in both the workflow and CLI. With
sequential extraction the archive plus one temporary ZIP is under 937 MB; Pages
packaging can additionally retain one archive-sized TAR. The 3 GiB floor leaves
room for those outputs and the small source/receipts. This is a hosted guard,
not permission to run a large download on a low-space local machine. The output
must be fresh; failures retain partial private output and available versioned
receipts for diagnosis. A failed cohort cannot emit a combined success receipt,
and a failed build cannot upload or deploy Pages.

A successful workflow establishes extraction, artifact integrity and deployment.
New combined public full-body verification and both-version actual browser
routing acceptance remain separate before main-controller admission. Earlier
v0.54.0 public/offline receipts remain historical and are not broadened by this
append. This repository does not select the main site's current game.

Focused local checks require Python 3.11 or newer and no network or game bodies:

```sh
python3 -m unittest discover -s tools -p 'test_*.py' -v
```

The cohort tests use tiny local Git/metadata fixtures and a local extractor
stand-in to verify ordering, failure isolation, source drift and no overwrite.
They mock only the capacity observation where assembly is exercised; the CLI
has no bypass. The workflow also runs the unchanged pinned extractor's own ZIP
corruption tests before the hosted preparation:

```sh
python3 -m unittest discover -s source/publishing/pages-controller -p 'test_extract_current.py' -v
python3 archive/tools/prepare.py --source source --out "$RUNNER_TEMP/archive13"
python3 archive/tools/verify.py "$RUNNER_TEMP/archive13/artifact"
```
