"""Shared constants and utilities for covert timing channel.

Covert channel: Example 8 — encoding data in inter-packet intervals.
Model 2: fixed-length packets sent at random time intervals.
Bit 0 → short interval, Bit 1 → long interval.
"""

import json
import struct

# ── Network defaults ──
TCP_PORT = 9000
UDP_PORT = 9001

# ── Channel defaults ──
PACKET_SIZE = 512            # fixed packet length in bytes (Model 2)
T_SHORT = 0.05               # interval for bit 0 (seconds)
T_LONG = 0.15                # interval for bit 1 (seconds)
THRESHOLD = 0.10             # decoder threshold (seconds)
JITTER = 0.02                # ± random jitter added to intervals

DEFAULT_BUFFER_SIZE = 8      # bits per burst (traffic buffering)
BURST_PAUSE = 0.3            # pause between bursts
DEFAULT_DUMMY_COUNT = 20     # dummy packets after covert data

# ── Timing ──
SYNC_DELAY = 2.0             # seconds between START signal and first packet


# ─────────────────── Bit-level message conversion ───────────────────

def message_to_bits(data):
    """Convert bytes to a list of bits (ints 0/1)."""
    bits = []
    for byte in data:
        for i in range(7, -1, -1):
            bits.append((byte >> i) & 1)
    return bits


def bits_to_message(bits, num_bytes):
    """Convert list of bits back to bytes."""
    result = bytearray()
    for i in range(num_bytes):
        byte = 0
        for j in range(8):
            idx = i * 8 + j
            if idx < len(bits):
                byte = (byte << 1) | bits[idx]
            else:
                byte = byte << 1
        result.append(byte)
    return bytes(result)


# ──────────────── TCP control-message helpers ──────────────────────

def send_control(sock, msg):
    """Send length-prefixed JSON over TCP."""
    raw = json.dumps(msg).encode()
    sock.sendall(struct.pack("!I", len(raw)) + raw)


def recv_control(sock):
    """Receive length-prefixed JSON from TCP. Returns dict or None."""
    header = _recvn(sock, 4)
    if not header:
        return None
    size = struct.unpack("!I", header)[0]
    raw = _recvn(sock, size)
    if not raw:
        return None
    return json.loads(raw)


def _recvn(sock, n):
    """Receive exactly n bytes from sock."""
    buf = b""
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            return None
        buf += chunk
    return buf
