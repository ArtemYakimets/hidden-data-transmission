"""Shared constants and utilities for covert channel communication.

Covert channel: Example 5 — encoding data in packet lengths.
L = max packet length, n = channel parameter (n divides L).
Alphabet size = L/n. Symbol i sent as packet with length in ((i-1)*n, i*n].
"""

import json
import random
import struct

# ── Network defaults ──
TCP_PORT = 9000
UDP_PORT = 9001

# ── Channel defaults ──
DEFAULT_L = 1024           # max packet length (bytes)
DEFAULT_N = 4              # channel parameter n  (L/n = 256 => 1 byte/symbol)
DEFAULT_INTERVAL = 0.5     # Model 3: fixed send interval (seconds)
DEFAULT_BUFFER_SIZE = 1    # symbols per burst (traffic buffering)
DEFAULT_DUMMY_RATE = 2.0   # avg dummy packets per interval

# ── Timing ──
SYNC_DELAY = 2.0           # seconds between START signal and first packet
BURST_DELAY = 0.05         # inter-packet delay inside a burst


# ─────────────────────── Encoding / Decoding ───────────────────────

def encode_symbol(symbol, n, L):
    """Return random packet length encoding *symbol* (0-indexed).

    Symbol s maps to 1-indexed i = s+1.  Packet length l ∈ ((i-1)*n, i*n].
    """
    i = symbol + 1
    lo = (i - 1) * n + 1
    hi = i * n
    if hi > L:
        raise ValueError(f"Symbol {symbol} exceeds L={L} with n={n}")
    return random.randint(lo, hi)


def decode_symbol(length, n):
    """Extract 0-indexed symbol from packet length."""
    return (length - 1) // n


# ─────────────── Message ↔ Symbol list conversion ─────────────────

def num_symbols_needed(num_bytes, alphabet_size):
    """How many symbols in base *alphabet_size* to represent *num_bytes* bytes."""
    if alphabet_size >= 256:
        return num_bytes
    max_val = (1 << (num_bytes * 8)) - 1
    if max_val == 0:
        return 1
    count, v = 0, max_val
    while v > 0:
        v //= alphabet_size
        count += 1
    return count


def message_to_symbols(data, alphabet_size):
    """Convert *data* bytes → list of symbols in [0, alphabet_size)."""
    if alphabet_size >= 256:
        return list(data)
    target = num_symbols_needed(len(data), alphabet_size)
    num = int.from_bytes(data, "big")
    symbols = []
    while num > 0:
        symbols.append(num % alphabet_size)
        num //= alphabet_size
    symbols.reverse()
    while len(symbols) < target:
        symbols.insert(0, 0)
    return symbols


def symbols_to_message(symbols, alphabet_size, num_bytes):
    """Convert symbol list back to *num_bytes* bytes."""
    if alphabet_size >= 256:
        return bytes(s & 0xFF for s in symbols[:num_bytes])
    num = 0
    for s in symbols:
        num = num * alphabet_size + s
    return num.to_bytes(num_bytes, "big")


# ──────────────── TCP control-message helpers ──────────────────────

def send_control(sock, msg):
    """Send length-prefixed JSON over TCP."""
    raw = json.dumps(msg).encode()
    sock.sendall(struct.pack("!I", len(raw)) + raw)


def recv_control(sock):
    """Receive length-prefixed JSON from TCP.  Returns dict or None."""
    header = _recvn(sock, 4)
    if not header:
        return None
    size = struct.unpack("!I", header)[0]
    raw = _recvn(sock, size)
    if not raw:
        return None
    return json.loads(raw)


def _recvn(sock, n):
    """Receive exactly *n* bytes from *sock*."""
    buf = b""
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            return None
        buf += chunk
    return buf
