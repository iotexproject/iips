# IIP-65 full-handler benchmarks for `G_VERIFY`

These measurements set `G_VERIFY = 150,000` (§8). The Draft 1 primitive
measurements that gave the provisional value of 30,000 are kept in `draft1/`.

## What is measured

The benchmarks are in the reference implementation, iotex-core PR #5059:

| Benchmark | Package | Measures |
|---|---|---|
| `BenchmarkVerifyOp`, `BenchmarkAuthorizeBind` | `action/protocol/staking/bucketguard` | The signature work of an action: the transcripts are built and every required signature is verified. One and two verifications, the largest op, and two failing cases: a CALL signature over another message, and a valid CALL with an ACCEPT for another CALL. |
| `BenchmarkGuardedBucketOpDecode` | `action` | Decoding an op from the wire, the stateless checks, and pricing. |
| `TestBucketGuardBlockPerf` (`QSB_PERF=1`) | `e2etest` | The full node path. Blocks are filled to the 25 M gas limit with guarded UNSTAKE (one verification), ROTATE (two verifications, about 32.6 KB), and the two failing cases. They go through the action pool, execution on the state database (state reads, verification, state writes, the staking snapshot and its revert, receipts), commit, and block decoding. The time per action is the block's execution time above an empty block's, over the actions in it. Five blocks per scenario; medians are reported. |

On amd64, `GODEBUG=cpu.sha=off` runs the same binary without the SHA
extensions. Go's `crypto/sha256`, which the SLH-DSA-SHA2 verifier (CIRCL
v1.6.5) uses, honours it. The `x/sys/cpu` warning it prints does not affect
the standard library.

## Results

Execution time per action in the full node path (`TestBucketGuardBlockPerf`):

| Platform | UNSTAKE (1 verification) | ROTATE (2 verifications) | Failing CALL | Failing ACCEPT |
|---|---:|---:|---:|---:|
| linux/amd64, AMD Ryzen 5 3600, SHA extensions | 0.70 ms | 1.21 ms | 0.66 ms | 1.14 ms |
| linux/amd64, AMD Ryzen 5 3600, SHA extensions off | 1.29 ms | 2.53 ms | 1.24 ms | 2.34 ms |
| linux/amd64, AMD EPYC 9V74 (GitHub runner, 4 vCPU), SHA extensions | 0.73 ms | 1.48 ms | 0.70 ms | 1.36 ms |
| linux/arm64, Arm Neoverse-N2 (GitHub runner, 4 vCPU) | 0.65 ms | 1.11 ms | 0.60 ms | 1.13 ms |
| darwin/arm64, Apple M1 Pro | 0.43 ms | 0.73 ms | 0.40 ms | 0.74 ms |

Verification alone (`BenchmarkVerifyOp`, best of five runs of 200 iterations):

| Platform | 1 verification | 2 verifications |
|---|---:|---:|
| linux/amd64, AMD Ryzen 5 3600, SHA extensions | 0.51 ms | 1.05 ms |
| linux/amd64, AMD Ryzen 5 3600, SHA extensions off | 1.11 ms | 2.26 ms |
| linux/amd64, AMD EPYC 9V74 (GitHub runner), SHA extensions | 0.52 ms | 1.14 ms |
| linux/amd64, AMD EPYC 9V74 (GitHub runner), SHA extensions off | 1.08 ms | 2.18 ms |
| linux/arm64, Arm Neoverse-N2 (GitHub runner) | 0.45 ms | 0.89 ms |
| darwin/arm64, Apple M1 Pro | 0.31 ms | 0.63 ms |
| linux/arm64, VM on Apple M1 Pro | 0.33 ms | 0.67 ms |

Other figures:

- Decoding, stateless checks, and pricing of the largest op (`BenchmarkGuardedBucketOpDecode`) take 0.03 ms on linux/amd64.
- A full block executes in at most 19 ms on the slowest platform measured, and decodes in about 1 ms.
- Committing a block takes 17–26 ms on linux/amd64 for both guarded and empty blocks, mostly database writes.

## How `G_VERIFY` follows

The slowest configuration is linux/amd64 without SHA extensions, as on Intel
server processors before Ice Lake. There, an action costs 1.29 ms per
verification. At the ≈16.7 ns/gas (~60 Mgas/s) execution budget used by
current Ethereum repricing work, that is about 77,000 gas. `G_VERIFY` keeps a
2× margin over it: 150,000.

Failing signatures cost the same as valid ones, so the margin covers blocks
filled with failing actions too.

The total gas of an action is dominated by `G_BYTE`. A single-verification
action is charged about 1.79 M gas for about 1.3 ms of work, which is
0.7 ns/gas on the slowest platform.

## Conditions and limits

- **Hardware and load.** The linux/amd64 machine is a dedicated server
  (6 cores, 12 threads, 64 GB) that also runs a small test network. Load was
  about 1 during the SHA-extension run. The run without them shows load up to
  9: most of it is the benchmark's own parallel signing between blocks, which
  is not timed. Those figures may therefore be slightly high, which errs on
  the side of a larger `G_VERIFY`.
- **Caches.** Measurements run in one process on a fresh state database with
  warm process caches. Reads after a node restart (cold caches) were not
  measured separately. The guard actions read a handful of records, as other
  staking actions do.
- **Gas at the time of the linux/amd64 block run.** That run used
  `G_VERIFY = 30,000`, so its blocks held 14 single-verification actions
  instead of 13. The time per action does not depend on the price.
- **linux/arm64.** linux/arm64 was measured natively on a GitHub-hosted
  `ubuntu-24.04-arm` runner (Arm Neoverse-N2, which has the Armv8 SHA2
  instructions), and in a VM on Apple silicon. Both are faster than
  linux/amd64 without SHA extensions, so linux/arm64 does not set `G_VERIFY`.
  An arm64 core without the SHA2 instructions was not measured.
- **GitHub-hosted runners.** They are shared, 4-vCPU virtual machines. The
  runs used `qsb-bench.yml` in this directory, on the reference
  implementation at iotex-core#5059 head `828f57a` plus the ACVP tests
  (run 42837446143 of `envestcc/iotex-core`). Their figures agree with the
  dedicated server's but are noisier.
- **Emulation.** Emulated builds (for example, Rosetta 2) are not a
  calibration source.

## Raw results

`results/` holds the benchmark output. The `-micro` files are the Go
benchmarks; the `-block` files are the `qsb-perf` lines of
`TestBucketGuardBlockPerf`.

| File | Platform |
|---|---|
| `linux-amd64-ryzen5-3600-micro.txt`, `linux-amd64-ryzen5-3600-block.txt` | linux/amd64, AMD Ryzen 5 3600; sections `## sha-ni` and `## no-sha` |
| `darwin-arm64-m1pro-micro.txt`, `darwin-arm64-m1pro-block.txt` | darwin/arm64, Apple M1 Pro |
| `linux-arm64-vm-m1pro-micro.txt` | linux/arm64 VM on Apple M1 Pro |
| `linux-arm64-neoverse-n2-gha-micro.txt`, `linux-arm64-neoverse-n2-gha-block.txt` | linux/arm64, Arm Neoverse-N2, GitHub-hosted runner |
| `linux-amd64-epyc-9v74-gha-micro.txt`, `linux-amd64-epyc-9v74-gha-block.txt` | linux/amd64, AMD EPYC 9V74, GitHub-hosted runner; micro sections `## sha-ni` and `## no-sha` |

All runs use Go 1.25.14.
