#!/usr/bin/env python3
"""IIP-65 test vectors, computed with the Python standard library only.

Independent of the reference implementation (iotex-core PR #5059), whose tests
assert the same values. Writes JSON to stdout:

    python3 -I qsb_vectors.py > vectors.json
    python3 -I qsb_vectors.py --g-verify 30000 > vectors.json

Public keys need FIPS 205 key generation, which the standard library does not
have; the script derives the key seeds (OKM) and checks that each published
public key starts with its PK.seed.
"""
import argparse
import hashlib
import hmac
import json
import struct
import unicodedata

G_BASE, G_BYTE = 10_000, 100
ALG = 0x12  # SLH-DSA-SHA2-192s
SIG_LEN, PK_LEN = 16_224, 48


def u32(x): return struct.pack('>I', x)
def u64(x): return struct.pack('>Q', x)
def lp(x): return u32(len(x)) + x  # length-prefixed bytes
def flag(x): return b'\x01' if x else b'\x00'


# §7 qsbDomain
NETWORKS = {
    'mainnet': (1, 'b337983730981c2d50f114eed5da9dd20b83c8c5e130beefdb3001dc858cfe8b'),
    'testnet': (2, '5e31a9f95ca4de82bd6f5ed9b465c6474bba27f1c5d31747393a555ce1f41607'),
}


def qsb_domain(chain_id, genesis_hex):
    return hashlib.sha256(b'IoTeX-PQ-Bucket-Domain-v1' + u32(chain_id) + bytes.fromhex(genesis_hex)).digest()


DOMAIN = qsb_domain(*NETWORKS['mainnet'])
OWNER = b'\x11' * 20
PUB = bytes.fromhex('c3530472b05ab2c631028bf08d7fa740f87ccbe26c8290b286f8317dbc30787febe5366d8be38345ec93d0fca288459a')
ANCHOR_H, ANCHOR_HASH = 1000, b'\x33' * 32


# §7 transcripts
def call(bucket, gen, nonce, deadline, ah, ahash, op, recipient=b'', new_owner=b'', cand=b'', cand_id=b'',
         duration=0, auto=False, ng=None, clear=False, sponsor=b''):
    m = DOMAIN + u64(bucket) + OWNER + u64(gen) + u64(nonce) + u64(deadline) + u64(ah) + ahash + u32(op)
    m += lp(recipient) + lp(new_owner) + lp(cand) + lp(cand_id) + u32(duration) + flag(auto) + flag(ng is not None)
    if ng is not None:
        m += u32(ng[0]) + lp(ng[1])
    return m + flag(clear) + lp(sponsor)


def accept(bucket, new_gen, res_owner, alg, pk, call_hash):
    assert len(call_hash) == 64
    return DOMAIN + u64(bucket) + u64(new_gen) + res_owner + u32(alg) + lp(pk) + call_hash


def guard_key_id(alg, pk):
    return hashlib.sha256(u32(alg) + pk).digest()


# §8 canonical encoding C(m)
def varint(x):
    out = bytearray()
    while True:
        b = x & 0x7f
        x >>= 7
        if x:
            out.append(b | 0x80)
        else:
            out.append(b)
            return bytes(out)


def tag(num, wire_type): return varint(num << 3 | wire_type)
def fv(num, v): return b'' if v == 0 else tag(num, 0) + varint(v)
def fb(num, v): return b'' if len(v) == 0 else tag(num, 2) + varint(len(v)) + v
def fmsg(num, v): return tag(num, 2) + varint(len(v)) + v


ZERO_SIG, ZERO_PK = bytes(SIG_LEN), bytes(PK_LEN)
ADDR = b'\x44' * 20


def new_guard(): return fv(1, ALG) + fb(2, ZERO_PK) + fb(3, ZERO_SIG)


def op_bytes(o, recipient=b'', new_owner=b'', cand=b'', cand_id=b'', duration=0, auto=False, ng=None,
             clear=False, sponsor=b'', ah=ANCHOR_H):
    m = fv(1, 1) + fv(2, 1) + fv(3, 0) + fv(4, 1010) + fv(5, o)
    m += fb(6, recipient) + fb(7, new_owner) + fb(8, cand) + fb(9, cand_id) + fv(10, duration) + fv(11, int(auto))
    if ng is not None:
        m += fmsg(12, ng)
    m += fv(13, int(clear)) + fb(14, ZERO_SIG) + fb(15, sponsor) + fv(16, ah) + fb(17, ANCHOR_HASH)
    return m


SIZE_CASES = [
    ('BindBucketGuard', fv(1, 1) + fv(2, ALG) + fb(3, ZERO_PK) + fb(4, ZERO_SIG), 1),
    ('UNSTAKE', op_bytes(1), 1),
    ('WITHDRAW', op_bytes(2, recipient=ADDR), 1),
    ('TRANSFER + clearGuard', op_bytes(3, new_owner=ADDR, clear=True), 1),
    ('CHANGE_CANDIDATE (delegateab)', op_bytes(4, cand=b'delegateab', cand_id=ADDR), 1),
    ('RESTAKE (7 days, autoStake)', op_bytes(5, duration=7, auto=True), 1),
    ('ROTATE', op_bytes(6, ng=new_guard()), 2),
    ('TRANSFER + newGuard', op_bytes(3, new_owner=ADDR, ng=new_guard()), 2),
    ('UNSTAKE + sponsor', op_bytes(1, sponsor=b'\x22' * 20), 1),
    ('UNSTAKE, anchorHeight = 2^28', op_bytes(1, ah=1 << 28), 1),
    ('ROTATE with an empty newGuard (invalid; size only)', op_bytes(6, ng=b''), 2),
]


# §12 QSB-KDF-v1
def hkdf_sha512(ikm, salt, info, length):
    prk = hmac.new(salt, ikm, hashlib.sha512).digest()
    okm, t, i = b'', b'', 1
    while len(okm) < length:
        t = hmac.new(prk, t + info + bytes([i]), hashlib.sha512).digest()
        okm += t
        i += 1
    return okm[:length]


def kdf_okm(seed, vault, key):
    info = b'slh-dsa-sha2-192s' + u32(vault) + u32(key)
    return hkdf_sha512(seed, b'IoTeX-PQ-Bucket-KDF-v1', info, 72)


def bip39_seed(mnemonic, passphrase=''):
    m = unicodedata.normalize('NFKD', mnemonic).encode()
    salt = unicodedata.normalize('NFKD', 'mnemonic' + passphrase).encode()
    return hashlib.pbkdf2_hmac('sha512', m, salt, 2048)


TEST_SEED = bytes(range(64))
# Public keys from FIPS 205 key generation (slh_keygen_internal) over the OKM
# below, as asserted by TestDeriveQSBKeyVectors in the reference implementation.
KDF_SEED_CASES = [
    (0, 0, '19cefae20e485beb73cd3baf3c84b9e452018c51850faac1e419836bc96f267a5913d095b8d796eecf68f4ca43eed03f'),
    (3, 2, '4384023dc938bad1b2397fe831a94bd6215e8cfad1c7a2074147d24e68cc0c0f9f13216c66e524af9d77972dcf6e87c5'),
    (0, 1024, '953096e87852f078eb9e759930ffe901aa1d956c6275d3d5feaf66e629287fb976157c6263dbd4350a4263f9acc3311b'),
    (0, 4294967295, '758637538cc8ae78652d57d9b200c86bafb63c3735574f3713ab8d545e03293a93d9a9af340663f38d05211234002e31'),
]
MNEMONIC = ' '.join(['abandon'] * 23 + ['art'])
KDF_MNEMONIC_CASES = [
    ('', 'b06841df29502ec67c3160c530f7b7d26e0a76838cced6e77b545a16fb3d435ce5bac69926bc389a83d32a7c6f2876ee'),
    ('TREZOR', '34fbd17dc298c306ca1d49a7cc9624a201bb7e132434b190201d121d4fbd886a422c45c509e0d143edb350a1e1b1f417'),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--g-verify', type=int, default=30_000, help='G_VERIFY of the parameter version (§8)')
    args = ap.parse_args()

    def gas(size, k): return G_BASE + G_BYTE * size + k * args.g_verify

    rot = call(1, 1, 2, 1010, ANCHOR_H, ANCHOR_HASH, 6, ng=(ALG, PUB), sponsor=b'\x22' * 20)
    rot_hash = hashlib.sha512(rot).digest()

    kdf_seed = []
    for vault, key, pk in KDF_SEED_CASES:
        okm = kdf_okm(TEST_SEED, vault, key)
        assert pk.startswith(okm[48:72].hex()), (vault, key)
        kdf_seed.append({'vaultIndex': vault, 'keyIndex': key, 'okm': okm.hex(), 'publicKey': pk})
    kdf_mnemonic = []
    for passphrase, pk in KDF_MNEMONIC_CASES:
        seed = bip39_seed(MNEMONIC, passphrase)
        okm = kdf_okm(seed, 0, 0)
        assert pk.startswith(okm[48:72].hex()), passphrase
        kdf_mnemonic.append({'passphrase': passphrase, 'bip39Seed': seed.hex(), 'okm': okm.hex(), 'publicKey': pk})

    out = {
        'iip': 65,
        'parameters': {'G_BASE': G_BASE, 'G_BYTE': G_BYTE, 'G_VERIFY': args.g_verify},
        'qsbDomain': {name: {'chainID': cid, 'genesisHash': gh, 'qsbDomain': qsb_domain(cid, gh).hex()}
                      for name, (cid, gh) in NETWORKS.items()},
        'transcripts': {
            'inputs': 'mainnet qsbDomain; owner 0x11 x 20; anchor block 1000 with hash 0x33 x 32',
            'callUnstake': {
                'inputs': 'bucket 1, generation 1, nonce 0, deadline 1010, op UNSTAKE, no sponsor',
                'call': call(1, 1, 0, 1010, ANCHOR_H, ANCHOR_HASH, 1).hex(),
            },
            'acceptBind': {
                'inputs': 'bucket 1, new generation 1, algID 0x12, publicKey below, callHash 64 zero bytes',
                'publicKey': PUB.hex(),
                'accept': accept(1, 1, OWNER, ALG, PUB, bytes(64)).hex(),
            },
            'rotate': {
                'inputs': 'bucket 1, generation 1, nonce 2, deadline 1010, incoming key publicKey above, sponsor 0x22 x 20',
                'callHashSha512': rot_hash.hex(),
                'acceptSha256': hashlib.sha256(accept(1, 2, OWNER, ALG, PUB, rot_hash)).hexdigest(),
                'guardKeyID': guard_key_id(ALG, PUB).hex(),
            },
        },
        'canonicalSize': {
            'inputs': ('48-byte zero public key, 16,224-byte zero signature, bucket 1, generation 1, nonce 0, '
                       'deadline 1010, anchor block 1000 with hash 0x33 x 32, 0x44 x 20 for recipient, newOwner '
                       'and expectedCandidateID; sha256 is over C(m)'),
            'cases': [{'name': name, 'size': len(m), 'verifications': k, 'intrinsicGas': gas(len(m), k),
                       'sha256': hashlib.sha256(m).hexdigest()} for name, m, k in SIZE_CASES],
        },
        'kdf': {
            'testSeed': TEST_SEED.hex(),
            'seedCases': kdf_seed,
            'mnemonic': MNEMONIC,
            'mnemonicCases': kdf_mnemonic,
            'note': 'publicKey comes from FIPS 205 key generation over okm; okm[48:72] is PK.seed, its first half',
        },
    }
    print(json.dumps(out, indent=2))


if __name__ == '__main__':
    main()
