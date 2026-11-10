"""Small helpers: ULID transaction IDs (H2)."""
import secrets
import time

_CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def ulid() -> str:
    """26-char Crockford base32 ULID: 48-bit millisecond timestamp + 80 random bits (2^80 values per ms)."""
    value = (int(time.time() * 1000) << 80) | secrets.randbits(80)
    out = []
    for _ in range(26):
        out.append(_CROCKFORD[value & 31])
        value >>= 5
    return "".join(reversed(out))


def new_tx_id() -> str:
    return "TX-" + ulid()
