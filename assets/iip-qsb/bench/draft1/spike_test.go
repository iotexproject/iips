package slhdsaspike

import (
	"bytes"
	"crypto/rand"
	"testing"

	"github.com/cloudflare/circl/sign/slhdsa"
)

var context = []byte("IOTEX-PQ-BUCKET-v1")
var message = []byte("staking bucket guard authorization")

var sets = []slhdsa.ID{
	slhdsa.SHA2_128s, slhdsa.SHA2_192s, slhdsa.SHA2_256s,
	slhdsa.SHAKE_128s, slhdsa.SHAKE_192s, slhdsa.SHAKE_256s,
	slhdsa.SHA2_192f, slhdsa.SHAKE_192f,
}

func TestSLHDSA(t *testing.T) {
	for _, id := range sets {
		t.Run(id.String(), func(t *testing.T) {
			pub, priv, err := slhdsa.GenerateKey(rand.Reader, id)
			if err != nil {
				t.Fatal(err)
			}
			other, _, err := slhdsa.GenerateKey(rand.Reader, id)
			if err != nil {
				t.Fatal(err)
			}
			pubBytes, err := pub.MarshalBinary()
			if err != nil {
				t.Fatal(err)
			}
			sig, err := slhdsa.SignDeterministic(&priv, slhdsa.NewMessage(message), context)
			if err != nil {
				t.Fatal(err)
			}
			t.Logf("public key: %d bytes; signature: %d bytes", len(pubBytes), len(sig))
			if !slhdsa.Verify(&pub, slhdsa.NewMessage(message), sig, context) {
				t.Fatal("deterministic signature rejected")
			}
			repeat, err := slhdsa.SignDeterministic(&priv, slhdsa.NewMessage(message), context)
			if err != nil {
				t.Fatal(err)
			}
			if !bytes.Equal(sig, repeat) {
				t.Fatal("deterministic signing changed the signature")
			}

			tamperedMessage := append([]byte(nil), message...)
			tamperedMessage[0] ^= 1
			if slhdsa.Verify(&pub, slhdsa.NewMessage(tamperedMessage), sig, context) {
				t.Fatal("tampered message accepted")
			}
			tamperedSig := append([]byte(nil), sig...)
			tamperedSig[0] ^= 1
			if slhdsa.Verify(&pub, slhdsa.NewMessage(message), tamperedSig, context) {
				t.Fatal("tampered signature accepted")
			}
			if slhdsa.Verify(&pub, slhdsa.NewMessage(message), sig, []byte("wrong context")) {
				t.Fatal("wrong context accepted")
			}
			if slhdsa.Verify(&other, slhdsa.NewMessage(message), sig, context) {
				t.Fatal("wrong public key accepted")
			}

			randomSig, err := slhdsa.SignRandomized(&priv, rand.Reader, slhdsa.NewMessage(message), context)
			if err != nil {
				t.Fatal(err)
			}
			if !slhdsa.Verify(&pub, slhdsa.NewMessage(message), randomSig, context) {
				t.Fatal("randomized signature rejected")
			}
			if bytes.Equal(sig, randomSig) {
				t.Fatal("randomized signature matched deterministic signature")
			}
		})
	}

	// These pairs have equal key and signature lengths, so rejection exercises
	// the hash family rather than an early length check.
	for _, pair := range [][2]slhdsa.ID{
		{slhdsa.SHA2_128s, slhdsa.SHAKE_128s},
		{slhdsa.SHA2_192s, slhdsa.SHAKE_192s},
		{slhdsa.SHA2_256s, slhdsa.SHAKE_256s},
		{slhdsa.SHA2_192f, slhdsa.SHAKE_192f},
	} {
		t.Run(pair[0].String()+"_as_"+pair[1].String(), func(t *testing.T) {
			pub, priv, err := slhdsa.GenerateKey(rand.Reader, pair[0])
			if err != nil {
				t.Fatal(err)
			}
			sig, err := slhdsa.SignDeterministic(&priv, slhdsa.NewMessage(message), context)
			if err != nil {
				t.Fatal(err)
			}
			serialized, err := pub.MarshalBinary()
			if err != nil {
				t.Fatal(err)
			}
			wrongFamily := slhdsa.PublicKey{ID: pair[1]}
			if err := wrongFamily.UnmarshalBinary(serialized); err != nil {
				t.Fatal(err)
			}
			if slhdsa.Verify(&wrongFamily, slhdsa.NewMessage(message), sig, context) {
				t.Fatal("cross-parameter signature accepted")
			}
		})
	}
}

var benchPub slhdsa.PublicKey
var benchPriv slhdsa.PrivateKey
var benchSig []byte
var benchOK bool

func BenchmarkSLHDSA(b *testing.B) {
	for _, id := range sets {
		b.Run(id.String(), func(b *testing.B) {
			b.Run("KeyGen", func(b *testing.B) {
				b.ReportAllocs()
				for i := 0; i < b.N; i++ {
					pub, priv, err := slhdsa.GenerateKey(rand.Reader, id)
					if err != nil {
						b.Fatal(err)
					}
					benchPub, benchPriv = pub, priv
				}
			})
			pub, priv, err := slhdsa.GenerateKey(rand.Reader, id)
			if err != nil {
				b.Fatal(err)
			}
			b.Run("Sign", func(b *testing.B) {
				b.ReportAllocs()
				for i := 0; i < b.N; i++ {
					sig, err := slhdsa.SignDeterministic(&priv, slhdsa.NewMessage(message), context)
					if err != nil {
						b.Fatal(err)
					}
					benchSig = sig
				}
			})
			sig, err := slhdsa.SignDeterministic(&priv, slhdsa.NewMessage(message), context)
			if err != nil {
				b.Fatal(err)
			}
			b.Run("Verify", func(b *testing.B) {
				b.ReportAllocs()
				for i := 0; i < b.N; i++ {
					ok := slhdsa.Verify(&pub, slhdsa.NewMessage(message), sig, context)
					if !ok {
						b.Fatal("valid signature rejected")
					}
					benchOK = ok
				}
			})
		})
	}
}
