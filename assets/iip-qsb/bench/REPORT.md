# SLH-DSA guard key spike

## Result

**Choose the SHA2 family for a native Go consensus verifier.** On the measured Apple M3 Pro, SHA2 verification was about 4.0–5.2× faster than the matching SHAKE set. SHA2 also signed and generated keys faster in every tested pair. Choose the security level separately: SHA2-128s if category 1 is acceptable, or SHA2-192s if category 3 is required. The `192f` variants sign faster but have 35,664-byte signatures and slower verification than `192s`, so they are a poor fit when verification and transaction size matter most.

These are **darwin/arm64 measurements**, not a linux/amd64 gas calibration. SHA-2 can use CPU SHA instructions or optimized implementations on both platforms, with the exact acceleration depending on CPU and Go implementation. SHAKE/Keccak has no comparably general single-stream hardware path in Go. Benchmark the same code on representative linux/amd64 validators before fixing a consensus gas schedule.

## Measurements

Go 1.26.5, darwin/arm64, Apple M3 Pro, CIRCL v1.6.5. One benchmark run per operation; `KeyGen` and deterministic pure `Sign` used `-benchtime=3x`, `Verify` used `-benchtime=200x`, all with `-benchmem -count=1`. The message was `staking bucket guard authorization`, with context `IOTEX-PQ-BUCKET-v1`. Verification used an already generated key and valid signature; its time includes CIRCL signature parsing and `NewMessage`, but excludes key generation, wire decoding, and transaction processing. Key generation includes `crypto/rand` reads. Each operation reports **ns/op (B/op; allocs/op)**.

| Parameter set | Public key bytes | Signature bytes | KeyGen | Sign | Verify / estimated raw gas basis |
|---|---:|---:|---:|---:|---:|
| SHA2-128s | 32 | 7,856 | 17,428,583 (1,152; 9) | 136,760,792 (15,677; 36) | 128,171 (5,962; 26) |
| SHA2-192s | 48 | 16,224 | 25,738,389 (1,552; 9) | 356,778,736 (27,066; 39) | 233,125 (8,562; 29) |
| SHA2-256s | 64 | 29,792 | 16,927,764 (1,648; 9) | 261,299,028 (45,677; 44) | 339,480 (10,698; 34) |
| SHAKE-128s | 32 | 7,856 | 88,797,097 (1,264; 8) | 669,600,167 (15,101; 28) | 661,551 (5,914; 23) |
| SHAKE-192s | 48 | 16,224 | 145,117,333 (1,472; 8) | 1,144,319,931 (25,829; 31) | 1,013,649 (8,162; 26) |
| SHAKE-256s | 64 | 29,792 | 95,047,903 (1,600; 8) | 1,070,285,458 (44,466; 36) | 1,373,672 (10,282; 31) |
| SHA2-192f | 48 | 35,664 | 420,389 (1,216; 9) | 11,631,667 (53,018; 55) | 631,840 (10,610; 45) |
| SHAKE-192f | 48 | 35,664 | 2,031,764 (1,136; 8) | 53,760,708 (51,781; 47) | 2,751,499 (10,210; 42) |

The Verify column is the measured **verify cost per operation** to start a gas estimate. If the chain later chooses a budget of `T` ns per gas, a first conversion is `ceil(verify_ns / T)` gas, followed by calibration against slower supported validators and any key decoding, transaction, and signature byte costs. No gas unit is assumed here.

## Correctness and vectors

`go test -count=1 ./...` passed under Go 1.26.5. For all eight sets, the test covers key generation, deterministic and randomized pure signatures with the non-empty context, verification, repeated deterministic signature equality, and rejection of a changed message, signature, context, or public key. Cross-family tests reinterpret a serialized SHA2 public key as the same-size SHAKE parameter set and confirm rejection, so they exercise the hash-family boundary rather than just a length check.

CIRCL v1.6.5 bundles compressed ACVP prompt/result JSON for FIPS 205 key generation, signature generation, and verification in `sign/slhdsa/testdata`. Its `acvp_test.go` compares against those NIST ACVP vectors. Upstream tests skip the slow `s` vector groups by default unless run with `-long`. This spike's tests are independent round trips and negative cases; they do not rerun CIRCL's upstream vector suite.

## API notes

- `slhdsa.NewMessage(raw)` selects **pure** mode. `PreHash.BuildMessage()` selects pre-hash mode; these are distinct signed messages and must not be mixed.
- `SignDeterministic` and `SignRandomized` both take the context as `[]byte`; it is part of the FIPS 205 message encoding. CIRCL rejects contexts longer than 255 **bytes**. Use one fixed byte string throughout consensus validation.
- `PrivateKey.Sign` uses randomized signing with an empty context and discards `crypto.SignerOpts`; use the direct SLH-DSA functions for this protocol context.
- The serialized public key and signature do not self-identify the parameter set. Consensus data should specify or fix the `slhdsa.ID` before unmarshalling a public key and verifying.

## Reproduction

The installed Go 1.26.5 toolchain in this workspace failed to resolve even standard packages in module mode (`package fmt is not in std`). The measurements above used **that Go 1.26.5 compiler in GOPATH mode** with temporary symlinks under `/tmp/slhdsa-gopath` to the already cached CIRCL v1.6.5, `golang.org/x/crypto` v0.54.0, and `golang.org/x/sys` v0.47.0 source trees. The ordinary module test was also run successfully with the locally cached Go 1.27.2 toolchain; its timings were not used in the table. `go.mod` and `go.sum` now list the transitive dependencies needed by the test import.

Commands used for the reported Go 1.26.5 run (after setting up those GOPATH symlinks):

```sh
GO111MODULE=off GOPATH=/tmp/slhdsa-gopath GOCACHE=/tmp/slhdsa-gocache126 go test -count=1 ./...
GO111MODULE=off GOPATH=/tmp/slhdsa-gopath GOCACHE=/tmp/slhdsa-gocache126 go test -run '^$' -bench 'BenchmarkSLHDSA/.*/(KeyGen|Sign)$' -benchtime=3x -benchmem -count=1 ./...
GO111MODULE=off GOPATH=/tmp/slhdsa-gopath GOCACHE=/tmp/slhdsa-gocache126 go test -run '^$' -bench 'BenchmarkSLHDSA/.*/Verify$' -benchtime=200x -benchmem -count=1 ./...
```
