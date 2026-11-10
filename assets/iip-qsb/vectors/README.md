# IIP-65 test vectors

`vectors.json` holds the test vectors of IIP-65 for `ParamsV1`
(`G_VERIFY = 150,000`). `qsb_vectors.py` generates it with the Python standard
library only, independently of the reference implementation (iotex-core PR
#5059), whose tests assert the same values.

```sh
python3 -I qsb_vectors.py > vectors.json
```

| Section | IIP | Contents | Asserted in the reference implementation by |
|---|---|---|---|
| `qsbDomain` | §7 | `qsbDomain` of mainnet and testnet from chain ID and genesis hash | `TestDomainVectors` (`ioctl/qsb`) |
| `transcripts` | §7 | A full UNSTAKE CALL and BIND ACCEPT; for a ROTATE, `callHash = SHA-512(CALL)`, the SHA-256 of its ACCEPT, and the incoming key's `guardKeyID` | `TestTranscriptVectors` |
| `canonicalSize` | §8 | `len(C(m))`, intrinsic gas, and SHA-256 of `C(m)` for BIND, every op, `sponsor`, a 2^28 anchor height, and an empty `newGuard` | `TestCanonicalVectors` |
| `kdf` | §12 | `QSB-KDF-v1` output keying material for a fixed seed and for the BIP-39 test mnemonic with and without a passphrase, with the resulting public keys | `TestDeriveQSBKeyVectors` |

All inputs are written next to the values in `vectors.json`. The public keys
in `kdf` come from FIPS 205 key generation over the output keying material,
which the standard library cannot run. The script checks that each starts with
its `PK.seed`, `okm[48:72]`.

Every vector uses the mainnet domain unless it says otherwise. The intrinsic
gas follows `G_BASE + G_BYTE·size + k·G_VERIFY`; `--g-verify` regenerates the
gas values for another parameter version.
