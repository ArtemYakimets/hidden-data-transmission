"""Security Device (UZ) — passive mode.

Forwards all TCP control messages and UDP data packets
from P1 to P2 without any modification or inspection.
"""

import argparse
import socket
import threading

from common import TCP_PORT, UDP_PORT


def parse_args():
    """Parse CLI arguments for the security device."""
    p = argparse.ArgumentParser(
        description="Security device (UZ) — passive forwarder",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--p2-host", default="192.168.56.12", help="Receiver (P2) IP")
    return p.parse_args()


def tcp_forward(p2_host):
    """Accept TCP from P1, relay every byte to P2 (unidirectional)."""
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


def udp_forward(p2_host):
    """Forward every UDP datagram from P1 to P2, preserving size."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", UDP_PORT))
    p2_addr = (p2_host, UDP_PORT)
    print(f"[UZ] UDP :{UDP_PORT} -> {p2_host}:{UDP_PORT}")

    count = 0
    while True:
        data, addr = sock.recvfrom(65535)
        sock.sendto(data, p2_addr)
        count += 1
        if count % 50 == 0:
            print(f"[UZ] Forwarded {count} UDP packets")


def main():
    args = parse_args()
    print(f"[UZ] Passive mode — forwarding to P2 at {args.p2_host}")

    threading.Thread(target=tcp_forward, args=(args.p2_host,),
                     daemon=True).start()
    try:
        udp_forward(args.p2_host)
    except KeyboardInterrupt:
        print("\n[UZ] Stopped")


if __name__ == "__main__":
    main()
