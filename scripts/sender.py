"""Sender (P1) with embedded covert channel bookmark.

Model 3: random-length packets at fixed time intervals.
Variant 3 features: traffic buffering, dummy traffic generation.
Covert channel: Example 5 — data encoded in packet lengths (parameter n).
"""

import argparse
import os
import random
import socket
import time

from common import (
    TCP_PORT, UDP_PORT,
    DEFAULT_L, DEFAULT_N, DEFAULT_INTERVAL,
    DEFAULT_BUFFER_SIZE, DEFAULT_DUMMY_RATE,
    SYNC_DELAY, BURST_DELAY,
    encode_symbol, message_to_symbols, send_control,
)


def parse_args():
    """Parse CLI arguments for sender / bookmark."""
    p = argparse.ArgumentParser(
        description="Covert channel sender (P1 + bookmark)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("-m", "--message", type=str, help="Secret message text")
    src.add_argument("-f", "--file", type=str, help="File with secret data")

    p.add_argument("--uz-host", default="192.168.56.11", help="UZ IP address")
    p.add_argument("-L", type=int, default=DEFAULT_L,
                   help="Max packet length in bytes")
    p.add_argument("-n", type=int, default=DEFAULT_N,
                   help="Channel parameter n (must divide L)")
    p.add_argument("-T", "--interval", type=float, default=DEFAULT_INTERVAL,
                   help="Fixed send interval in seconds (Model 3)")
    p.add_argument("--buffer-size", type=int, default=DEFAULT_BUFFER_SIZE,
                   help="Symbols per burst (traffic buffering)")
    p.add_argument("--dummy-rate", type=float, default=DEFAULT_DUMMY_RATE,
                   help="Avg dummy packets per covert packet")
    return p.parse_args()


def main():
    args = parse_args()

    # ── Read secret message ──
    if args.file:
        with open(args.file, "rb") as fh:
            secret = fh.read()
    else:
        secret = args.message.encode()

    L, n = args.L, args.n
    if L % n != 0:
        raise SystemExit(f"[!] n={n} must divide L={L}")

    alphabet = L // n
    symbols = message_to_symbols(secret, alphabet)
    total = len(symbols)

    print(f"[*] L={L}  n={n}  alphabet={alphabet}  "
          f"interval={args.interval}s  buffer={args.buffer_size}")
    print(f"[*] Message: {len(secret)} bytes -> {total} symbols")

    # ── TCP control → UZ (with retry) ──
    tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    for attempt in range(1, 16):
        try:
            tcp.connect((args.uz_host, TCP_PORT))
            break
        except ConnectionRefusedError:
            print(f"[*] UZ not ready, retrying ({attempt}/15) ...")
            time.sleep(2)
            tcp.close()
            tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    else:
        raise SystemExit("[!] Cannot connect to UZ — is security_device.py running?")

    send_control(tcp, {
        "type": "start",
        "num_symbols": total,
        "num_bytes": len(secret),
        "L": L,
        "n": n,
        "interval": args.interval,
        "buffer_size": args.buffer_size,
    })
    print(f"[*] START sent, syncing {SYNC_DELAY}s ...")
    time.sleep(SYNC_DELAY)

    # ── UDP data → UZ ──
    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    dest = (args.uz_host, UDP_PORT)

    # Phase 1: covert packets at fixed intervals (Model 3)
    t0 = time.time()
    idx = 0
    burst_num = 0

    while idx < total:
        target_time = t0 + burst_num * args.interval
        while time.time() < target_time:
            time.sleep(0.005)

        count = min(args.buffer_size, total - idx)
        for j in range(count):
            pkt_len = encode_symbol(symbols[idx], n, L)
            udp.sendto(os.urandom(pkt_len), dest)
            idx += 1
            if j < count - 1:
                time.sleep(BURST_DELAY)

        burst_num += 1
        print(f"\r[*] Sent {idx}/{total} symbols", end="", flush=True)

    print()

    # Phase 2: trailing dummy packets (mask end of transmission)
    num_dummies = max(1, int(total * args.dummy_rate))
    print(f"[*] Sending {num_dummies} dummy packets ...")
    for _ in range(num_dummies):
        time.sleep(random.uniform(0.02, 0.15))
        udp.sendto(os.urandom(random.randint(1, L)), dest)

    time.sleep(0.5)
    send_control(tcp, {"type": "end"})
    tcp.close()
    udp.close()
    print(f"[*] Done — {total} covert + {num_dummies} dummy packets sent")


if __name__ == "__main__":
    main()
