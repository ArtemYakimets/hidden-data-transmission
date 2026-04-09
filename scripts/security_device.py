"""Security Device (UZ) — passive and active countermeasure modes.

Modes:
  passive  — forward all traffic unchanged (lab 1)
  jitter   — add random delay to UDP packets (lab 3, scheme 1)
  regulate — buffer and retransmit at fixed interval (lab 3, scheme 2)
"""

import argparse
import os
import queue
import signal
import socket
import sys
import threading
import time

from common import TCP_PORT, UDP_PORT


def parse_args():
    """Parse CLI arguments for the security device."""
    p = argparse.ArgumentParser(
        description="Security device (UZ)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--p2-host", default="192.168.56.12", help="Receiver (P2) IP")
    p.add_argument("--mode", choices=["passive", "jitter", "regulate"],
                   default="passive", help="Countermeasure mode")
    p.add_argument("--max-jitter", type=float, default=0.06,
                   help="Max random delay in seconds (jitter mode)")
    p.add_argument("--fixed-interval", type=float, default=0.10,
                   help="Fixed retransmit interval in seconds (regulate mode)")
    return p.parse_args()


def tcp_forward(p2_host):
    """Relay TCP control messages from P1 to P2 unchanged."""
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("0.0.0.0", TCP_PORT))
    srv.listen(1)
    print(f"[UZ] TCP :{TCP_PORT} -> {p2_host}:{TCP_PORT}")

    while True:
        src, addr = srv.accept()
        print(f"[UZ] TCP connection from {addr}")
        try:
            dst = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            dst.connect((p2_host, TCP_PORT))
        except ConnectionRefusedError:
            print("[UZ] P2 TCP connection refused")
            src.close()
            continue

        try:
            while True:
                data = src.recv(4096)
                if not data:
                    break
                dst.sendall(data)
        except (ConnectionResetError, BrokenPipeError, OSError):
            pass
        finally:
            src.close()
            dst.close()
            print("[UZ] TCP session closed")


def udp_forward_passive(p2_host, stats):
    """Forward UDP packets without modification."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", UDP_PORT))
    p2_addr = (p2_host, UDP_PORT)
    print(f"[UZ] UDP :{UDP_PORT} -> {p2_host}:{UDP_PORT}")

    while True:
        data, addr = sock.recvfrom(65535)
        stats["count"] += 1
        sock.sendto(data, p2_addr)


def udp_forward_jitter(p2_host, max_jitter, stats):
    """Forward UDP packets with random delay added."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", UDP_PORT))
    p2_addr = (p2_host, UDP_PORT)
    print(f"[UZ] UDP :{UDP_PORT} -> {p2_host}:{UDP_PORT} (jitter ±{max_jitter*1000:.0f}ms)")

    def _delayed_send(data, delay):
        time.sleep(delay)
        sock.sendto(data, p2_addr)

    while True:
        data, addr = sock.recvfrom(65535)
        stats["count"] += 1
        delay = abs(random.gauss(0, max_jitter))
        stats["total_jitter"] += delay
        threading.Thread(target=_delayed_send, args=(data, delay),
                         daemon=True).start()


def udp_forward_regulate(p2_host, fixed_interval, stats):
    """Buffer UDP packets and retransmit at fixed intervals."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", UDP_PORT))
    p2_addr = (p2_host, UDP_PORT)
    print(f"[UZ] UDP :{UDP_PORT} -> {p2_host}:{UDP_PORT} "
          f"(regulate T={fixed_interval*1000:.0f}ms)")

    pkt_queue = queue.Queue()

    def _receiver():
        while True:
            data, addr = sock.recvfrom(65535)
            pkt_queue.put(data)
            stats["count"] += 1

    threading.Thread(target=_receiver, daemon=True).start()

    while True:
        try:
            data = pkt_queue.get(timeout=5.0)
            sock.sendto(data, p2_addr)
            time.sleep(fixed_interval)
        except queue.Empty:
            pass


import random


def main():
    args = parse_args()
    mode_label = {
        "passive": "passive (no modification)",
        "jitter": f"jitter (max={args.max_jitter*1000:.0f}ms)",
        "regulate": f"regulate (T={args.fixed_interval*1000:.0f}ms)",
    }
    print(f"[UZ] Mode: {mode_label[args.mode]}")
    print(f"[UZ] Forwarding to P2 at {args.p2_host}")

    stats = {"count": 0, "total_jitter": 0.0}

    def _summary(signum=None, frame=None):
        """Print traffic statistics on SIGTERM."""
        c = stats["count"]
        print(f"[UZ] === SUMMARY ===")
        print(f"[UZ] Mode: {args.mode}")
        print(f"[UZ] Packets forwarded: {c}")
        if args.mode == "jitter":
            avg_j = stats["total_jitter"] / max(c, 1) * 1000
            print(f"[UZ] Max jitter setting: {args.max_jitter*1000:.0f} ms")
            print(f"[UZ] Avg actual jitter: {avg_j:.1f} ms")
        elif args.mode == "regulate":
            print(f"[UZ] Fixed interval: {args.fixed_interval*1000:.0f} ms")
            print(f"[UZ] All inter-packet intervals normalized to "
                  f"{args.fixed_interval*1000:.0f} ms")
        sys.exit(0)

    signal.signal(signal.SIGTERM, _summary)

    threading.Thread(target=tcp_forward, args=(args.p2_host,),
                     daemon=True).start()
    try:
        if args.mode == "passive":
            udp_forward_passive(args.p2_host, stats)
        elif args.mode == "jitter":
            udp_forward_jitter(args.p2_host, args.max_jitter, stats)
        elif args.mode == "regulate":
            udp_forward_regulate(args.p2_host, args.fixed_interval, stats)
    except KeyboardInterrupt:
        print("\n[UZ] Stopped")


if __name__ == "__main__":
    main()
