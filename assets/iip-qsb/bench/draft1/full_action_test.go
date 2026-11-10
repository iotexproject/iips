package slhdsaspike

import (
	"crypto/rand"
	"encoding/binary"
	"testing"

	"github.com/cloudflare/circl/sign/slhdsa"
)

const (
	fullActionChainID   = 4689
	fullActionAlgID     = 0x12
	fullActionOpUnstake = 1
)

func appendU32(b []byte, v uint32) []byte {
	var buf [4]byte
	binary.BigEndian.PutUint32(buf[:], v)
	return append(b, buf[:]...)
}

func appendU64(b []byte, v uint64) []byte {
	var buf [8]byte
	binary.BigEndian.PutUint64(buf[:], v)
	return append(b, buf[:]...)
}

func appendBytes(b, v []byte) []byte {
	b = appendU32(b, uint32(len(v)))
	return append(b, v...)
}

func appendBool(b []byte, v bool) []byte {
	if v {
		return append(b, 0x01)
	}
	return append(b, 0x00)
}

// callTranscript is the Draft 1 CALL transcript for a guarded UNSTAKE (see the
// note at the top of REPORT.md); the Draft 3 layout of §7 differs. It is a
// full-action proxy: it measures the dominant verify and signature-byte costs,
// not canonical proto encoding or the staking state transition.
func callTranscript() []byte {
	owner := make([]byte, 20)
	for i := range owner {
		owner[i] = 0x11
	}
	b := []byte("IOTX-QSB-CALL")
	b = appendU32(b, fullActionChainID)
	b = appendU64(b, 1) // bucket index
	b = append(b, owner...)
	b = appendU64(b, 1) // generation
	b = appendU64(b, 0) // nonce
	b = appendU64(b, 1_000_000)
	b = appendU32(b, fullActionOpUnstake)
	b = appendBytes(b, nil)  // recipient
	b = appendBytes(b, nil)  // newOwner
	b = appendBytes(b, nil)  // candidateName
	b = appendBytes(b, nil)  // expectedCandidateID
	b = appendU32(b, 0)      // duration
	b = appendBool(b, false) // autoStake
	b = appendBool(b, false) // hasNewGuard
	b = appendBool(b, false) // clearGuard
	return b
}

// acceptTranscript is the Draft 1 ACCEPT transcript for a BIND at generation 1.
func acceptTranscript(pub []byte) []byte {
	owner := make([]byte, 20)
	for i := range owner {
		owner[i] = 0x11
	}
	b := []byte("IOTX-QSB-ACCEPT")
	b = appendU32(b, fullActionChainID)
	b = appendU64(b, 1) // bucket index
	b = appendU64(b, 1) // newGeneration
	b = append(b, owner...)
	b = appendU32(b, fullActionAlgID)
	b = appendBytes(b, pub)
	b = appendU64(b, 0) // BIND deadline is 0
	return b
}

func TestFullActionTranscriptSizes(t *testing.T) {
	pub, priv, err := slhdsa.GenerateKey(rand.Reader, slhdsa.SHA2_192s)
	if err != nil {
		t.Fatal(err)
	}
	pubBytes, err := pub.MarshalBinary()
	if err != nil {
		t.Fatal(err)
	}
	call := callTranscript()
	accept := acceptTranscript(pubBytes)
	callSig, err := slhdsa.SignDeterministic(&priv, slhdsa.NewMessage(call), context)
	if err != nil {
		t.Fatal(err)
	}
	acceptSig, err := slhdsa.SignDeterministic(&priv, slhdsa.NewMessage(accept), context)
	if err != nil {
		t.Fatal(err)
	}
	if !slhdsa.Verify(&pub, slhdsa.NewMessage(call), callSig, context) {
		t.Fatal("CALL signature rejected")
	}
	if !slhdsa.Verify(&pub, slhdsa.NewMessage(accept), acceptSig, context) {
		t.Fatal("ACCEPT signature rejected")
	}
	t.Logf("CALL=%d bytes, ACCEPT=%d bytes, public key=%d bytes, signatures=%d/%d bytes",
		len(call), len(accept), len(pubBytes), len(callSig), len(acceptSig))
}

func BenchmarkFullAction(b *testing.B) {
	pub, priv, err := slhdsa.GenerateKey(rand.Reader, slhdsa.SHA2_192s)
	if err != nil {
		b.Fatal(err)
	}
	pubBytes, err := pub.MarshalBinary()
	if err != nil {
		b.Fatal(err)
	}
	call := callTranscript()
	accept := acceptTranscript(pubBytes)
	callSig, err := slhdsa.SignDeterministic(&priv, slhdsa.NewMessage(call), context)
	if err != nil {
		b.Fatal(err)
	}
	acceptSig, err := slhdsa.SignDeterministic(&priv, slhdsa.NewMessage(accept), context)
	if err != nil {
		b.Fatal(err)
	}

	b.Run("VerifyBindAccept+UnstakeCall", func(b *testing.B) {
		b.ReportAllocs()
		for i := 0; i < b.N; i++ {
			if !slhdsa.Verify(&pub, slhdsa.NewMessage(accept), acceptSig, context) {
				b.Fatal("valid ACCEPT rejected")
			}
			if !slhdsa.Verify(&pub, slhdsa.NewMessage(call), callSig, context) {
				b.Fatal("valid CALL rejected")
			}
		}
	})

	b.Run("Encode32KB", func(b *testing.B) {
		b.ReportAllocs()
		buf := make([]byte, 0, len(callSig)+len(acceptSig))
		for i := 0; i < b.N; i++ {
			buf = buf[:0]
			buf = append(buf, callSig...)
			buf = append(buf, acceptSig...)
		}
	})
}
