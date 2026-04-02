"""Security Device (UZ) — passive and active countermeasure modes.

Modes:
  passive   — forward all traffic unchanged (lab 1)
  normalize — round UDP packet lengths to multiples of k (lab 3, scheme 1)
  pad       — pad all UDP packets to fixed length L (lab 3, scheme 2)
"""

import argparse
import os
import signal
import socket
import sys
import threading

from common import TCP_PORT, UDP_PORT, DEFAULT_L


def parse_args():
    """Parse CLI arguments for the security device."""
    p = argparse.ArgumentParser(
        description="Security device (UZ)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--p2-host", default="192.168.56.12", help="Receiver (P2) IP")
    p.add_argument("--mode", choices=["passive", "normalize", "pad"],
                   default="passive", help="Countermeasure mode")
    p.add_argument("--k", type=int, default=32,
                   help="Normalization step in bytes (normalize mode)")
    p.add_argument("--max-len", type=int, default=DEFAULT_L,
                   help="Fixed packet length (pad mode)")
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


def udp_forward(p2_host, mode, k, max_len):
    """Forward UDP packets, optionally applying countermeasures."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", UDP_PORT))
    p2_addr = (p2_host, UDP_PORT)
    print(f"[UZ] UDP :{UDP_PORT} -> {p2_host}:{UDP_PORT}")

    stats = {"count": 0, "orig": 0, "mod": 0}

    def _summary(signum=None, frame=None):
        """Print traffic statistics on SIGTERM."""
        c, ob, mb = stats["count"], stats["orig"], stats["mod"]
        overhead = (mb - ob) / max(ob, 1) * 100
        print(f"[UZ] === SUMMARY ===")
        print(f"[UZ] Mode: {mode}")
        print(f"[UZ] Packets forwarded: {c}")
        print(f"[UZ] Bytes original: {ob}")
        print(f"[UZ] Bytes after modification: {mb}")
        print(f"[UZ] Overhead: {overhead:.1f}%")
        if mode == "normalize":
            print(f"[UZ] Normalization step k={k}")
        elif mode == "pad":
            print(f"[UZ] Fixed length L={max_len}")
        sys.exit(0)

    signal.signal(signal.SIGTERM, _summary)

    while True:
        data, addr = sock.recvfrom(65535)
        orig_len = len(data)

        if mode == "normalize":
            target = ((orig_len + k - 1) // k) * k
            if target > orig_len:
                data = data + os.urandom(target - orig_len)
        elif mode == "pad":
            if orig_len < max_len:
                data = data + os.urandom(max_len - orig_len)

        stats["count"] += 1
        stats["orig"] += orig_len
        stats["mod"] += len(data)

        sock.sendto(data, p2_addr)


def main():
    args = parse_args()
    mode_label = {
        "passive": "passive (no modification)",
        "normalize": f"normalize (k={args.k})",
        "pad": f"pad (L={args.max_len})",
    }
    print(f"[UZ] Mode: {mode_label[args.mode]}")
    print(f"[UZ] Forwarding to P2 at {args.p2_host}")

    threading.Thread(target=tcp_forward, args=(args.p2_host,),
                     daemon=True).start()
    try:
        udp_forward(args.p2_host, args.mode, args.k, args.max_len)
    except KeyboardInterrupt:
        print("\n[UZ] Stopped")


if __name__ == "__main__":
    main()
