## IIP 52: BLS Signature Aggregation for Block Signature Compression

```
IIP: 52
Title: BLS Signature Aggregation for Block Signature Compression
Author: Seedlet (zhi@iotex.io), Chen Chen (chenchen@iotex.io)
Type: Core
Category: Core
```

## Simple Summary

This proposal introduces Boneh–Lynn–Shacham (BLS) signature aggregation to compress the set of validator signatures required for block finality into a single aggregated signature, thereby reducing the size of the block footer and improving block propagation efficiency.

## Abstract

Currently, to finalize a block, the IoTeX consensus protocol requires more than 2/3 of selected delegates to sign it. These signatures are all stored individually in the block footer. Since each signature is ~65 bytes, this causes the block footer alone to consume over 2 KB, given that 24 consensus delegates participated, leading to large block sizes and slower propagation.

This proposal introduces the use of BLS signature aggregation, which allows all individual signatures to be compressed into a single 96-byte signature, with one accompanying bitmap or list of participating signer indices.

## Motivation

With this proposal, we achieve the following goals:

* Reduce block size, especially in environments with high delegate count.

* Improve network throughput and block propagation latency.

* Make room for more transactions per block without increasing total size.

* Future-proof consensus scalability as delegate numbers grow.

## Specification

The implementation of this proposal will be split into two phases:

1. Collect BLS public keys of delegates. Since the current crypto curve (Secp256k1) differs from BLS12-381, delegates must submit their BLS public keys:

* A new transaction type will be introduced for submitting BLS public keys.

* A new field will be added to delegate registration transaction.

2. Trigger the usage of BLS in consensus. The delegates who haven't submit their BLS public keys will be excluded from the active consensus delegate set.

## Rationale

* BLS aggregation compresses O(n) signatures to O(1), enabling scalability.

* Signature verification is fast and constant-time.

* Widely used in other blockchain platforms (e.g., Ethereum 2.0, Dfinity, Chia) to solve the same problem.

* IoTeX already uses elliptic curve cryptography, and integration of BLS is a natural extension.

#### Performance Analysis

* Storage Efficiency

|Metric|ECDSA|BLS|Improvement|
| --- | --- | --- | --- |
|**Individual Signature**|65 bytes|96 bytes|-47.7%|
|**Block Footer (24 delegates)**|2,328 bytes|100 bytes|**95.7% reduction**|
|**Composition**|24 × (32B pubkey + 65B sig)|4B bitmap + 96B agg sig|Storage optimization|
|**Scalability**|O(n) linear growth|O(1) constant size|Future-proof|
|**Bandwidth per Block**|2.3 KB signature data|0.1 KB signature data|**95.7% savings**|

  * Block Size: 2,228 bytes saved per block (95.7% reduction)

  * Network Efficiency: Dramatically reduced bandwidth usage during block sync

  * Future Scalability: Size remains constant regardless of delegate count increase
* Computational Performance

  * Individual Operation Benchmarks

|Operation|ECDSA (secp256k1)|BLS12-381|Performance Ratio|
| --- | --- | --- | --- |
|Sign|0.047ms|0.31ms|~6x slower|
|Verify|0.063ms|0.78ms|~12x slower|
|Aggregate Sign|N/A|0.38ms|N/A|
|Aggregate Verify|N/A|1.45ms|N/A|

    * Sign operation of BLS is 6 times slower than ECDSA, but the impact is minimal due to the small absolute value.

    * If the verifications of signatures are run in parallel, the overall computation time to produce a BLS will be 1.16ms (0.78ms verification time + 0.38ms signature aggregation time).

    * The aggregated signature verification speed is 12 times slower than ECDSA, but the impact is also not significant compared to the overall block verification time.

## Backwards Compatibility

This is a consensus-level change and is not backwards compatible. Two hardforks will be required:

* One for phase 1, BLS public key submission.

* Another for phase 2, activating BLS verification in consensus.

## Implementation

* Use the BLS12-381 curve, same as Ethereum 2.0.

* Leverage the BLST library, github.com/supranational/blst.

* Introduce:

  * New transaction type for delegates to submit BLS public key.

  * New field, BLS public key, in delegate registration transaction.

  * New fields, `aggregated signature` and `signer bitmap`, in block footer.
* Update explorer and ioctl to decode and display BLS signature.

### Copyright

Copyright and related rights waived via [CC0](https://creativecommons.org/publicdomain/zero/1.0/).
