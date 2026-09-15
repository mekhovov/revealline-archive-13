# RevealLine archive 13

This repository preserves the original **v0.54.0** game at
`https://mekhovov.github.io/revealline-archive-13/releases/v0.54.0/site/game/`.
The frozen source is `1af33851e93ee95110de20cc73622ed43d85a4da`; `source-lock.json`
pins its original tag object, ZIP, manifest, release record and checksum.

The workflow downloads the original GitHub Release ZIP. It uses the existing
bounded extractor pinned to source commit `0594b60136db000c9d6c87527c7885c2c51a2562`,
verifies the whole ZIP and every member's CRC, size and SHA256, and preserves the
original worker and assets. No game source is rebuilt, no release/tag is moved,
and no previously allocated archive changes.

`expected-inventory.json` contains every canonical body, including hidden build
metadata, original manifest/checksum and release record. Two independent reads
must match all 652 files / 312,209,411 bytes before Pages upload. The artifact
stays below the existing 800,000,000-byte archive budget. The downloadable ZIP
remains on the original GitHub Release.

A successful workflow establishes extraction, artifact integrity and deployment;
public full-body verification and actual browser/offline acceptance are recorded
separately before the main publishing controller admits this route. This repository
does not select the main site's current game.

Focused local checks require Python 3.11 or newer:

```sh
python3 -m unittest discover -s tools -p 'test_*.py' -v
```
