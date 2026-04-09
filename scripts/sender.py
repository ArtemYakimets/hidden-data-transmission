"""Sender (P1) with covert timing channel.

Model 2: fixed-length packets at random time intervals.
Variant 7: Example 8 — data encoded in inter-packet intervals.
Features: traffic buffering, dummy traffic generation.
"""

import argparse
import os
import random
import socket
import time

from common import (
    TCP_PORT, UDP_PORT,
    PACKET_SIZE, T_SHORT, T_LONG, THRESHOLD, JITTER,
    DEFAULT_BUFFER_SIZE, BURST_PAUSE, DEFAULT_DUMMY_COUNT,
    SYNC_DELAY,
    message_to_bits, send_control,
)


def parse_args():
    """Parse CLI arguments for sender."""
    p = argparse.ArgumentParser(
        description="Covert timing channel sender (P1)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("-m", "--message", type=str, help="Secret message text")
    src.add_argument("-f", "--file", type=str, help="File with secret data")

    p.add_argument("--uz-host", default="192.168.56.11", help="UZ IP address")
    p.add_argument("--pkt-size", type=int, default=PACKET_SIZE,
                   help="Fixed packet size in bytes (Model 2)")
    p.add_argument("--t-short", type=float, default=T_SHORT,
                   help="Interval for bit 0 (seconds)")
    p.add_argument("--t-long", type=float, default=T_LONG,
                   help="Interval for bit 1 (seconds)")
    p.add_argument("--jitter", type=float, default=JITTER,
                   help="Random jitter ± added to intervals")
    p.add_argument("--buffer-size", type=int, default=DEFAULT_BUFFER_SIZE,
                   help="Bits per burst (traffic buffering)")
    p.add_argument("--dummy-count", type=int, default=DEFAULT_DUMMY_COUNT,
                   help="Number of dummy packets after covert data")
    return p.parse_args()


def main():
    args = parse_args()

    if args.file:
        with open(args.file, "rb") as fh:
            secret = fh.read()
    else:
        secret = args.message.encode()

    bits = message_to_bits(secret)
    total_bits = len(bits)

    print(f"[P1] Packet size: {args.pkt_size} bytes (fixed)")
    print(f"[P1] T_short={args.t_short}s  T_long={args.t_long}s  "
          f"jitter=±{args.jitter}s  buffer={args.buffer_size}")
    print(f"[P1] Message: {len(secret)} bytes -> {total_bits} bits")

    # ── TCP control → UZ (with retry) ──
    tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    for attempt in range(1, 16):
        try:
            tcp.connect((args.uz_host, TCP_PORT))
            break
        except ConnectionRefusedError:
            print(f"[P1] UZ not ready, retrying ({attempt}/15) ...")
            time.sleep(2)
            tcp.close()
            tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    else:
        raise SystemExit("[!] Cannot connect to UZ")

    send_control(tcp, {
        "type": "start",
        "num_bits": total_bits,
        "num_bytes": len(secret),
        "pkt_size": args.pkt_size,
        "t_short": args.t_short,
        "t_long": args.t_long,
        "threshold": THRESHOLD,
        "buffer_size": args.buffer_size,
    })
    print(f"[P1] START sent, syncing {SYNC_DELAY}s ...")
    time.sleep(SYNC_DELAY)

    # ── UDP data → UZ ──
    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    dest = (args.uz_host, UDP_PORT)
    pkt_data = os.urandom(args.pkt_size)

    # Send initial sync packet
    udp.sendto(pkt_data, dest)
    print("[P1] Sync packet sent")

    # Phase 1: covert bits encoded in inter-packet intervals
    idx = 0
    while idx < total_bits:
        burst_end = min(idx + args.buffer_size, total_bits)
        for i in range(idx, burst_end):
            base = args.t_long if bits[i] == 1 else args.t_short
            interval = base + random.uniform(-args.jitter, args.jitter)
            interval = max(0.01, interval)
            time.sleep(interval)
            udp.sendto(os.urandom(args.pkt_size), dest)
        idx = burst_end

        if idx < total_bits:
            time.sleep(BURST_PAUSE)
            udp.sendto(os.urandom(args.pkt_size), dest)

        print(f"\r[P1] Sent {idx}/{total_bits} bits", end="", flush=True)

    print()

    # Phase 2: dummy packets with random intervals
    print(f"[P1] Sending {args.dummy_count} dummy packets ...")
    for _ in range(args.dummy_count):
        time.sleep(random.uniform(0.02, 0.2))
        udp.sendto(os.urandom(args.pkt_size), dest)

    time.sleep(0.5)
    send_control(tcp, {"type": "end"})
    tcp.close()
    udp.close()
    print(f"[P1] Done — {total_bits} covert bits + "
          f"{args.dummy_count} dummy packets sent")


if __name__ == "__main__":
    main()
