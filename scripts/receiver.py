"""Receiver (P2) / Attacker — decodes covert channel messages.

Collects UDP packets in arrival order. Covert packets are sent first
(at fixed intervals, Model 3), followed by dummy traffic. The receiver
takes the first N packets (by arrival time) and decodes their lengths.
"""

import argparse
import socket
import threading
import time

from common import (
    TCP_PORT, UDP_PORT,
    SYNC_DELAY,
    decode_symbol, symbols_to_message, recv_control,
)


def parse_args():
    """Parse CLI arguments for the receiver / attacker."""
    p = argparse.ArgumentParser(
        description="Covert channel receiver (P2 / attacker)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("-o", "--output", type=str,
                   help="Save decoded message to file")
    return p.parse_args()


class PacketCollector:
    """Background UDP listener that records (timestamp, length) pairs."""

    def __init__(self):
        self.packets = []
        self._running = False
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.bind(("0.0.0.0", UDP_PORT))

    def start(self):
        self._running = True
        threading.Thread(target=self._loop, daemon=True).start()

    def stop(self):
        self._running = False
        try:
            self._sock.close()
        except OSError:
            pass

    def _loop(self):
        while self._running:
            try:
                data, _ = self._sock.recvfrom(65535)
                self.packets.append((time.time(), len(data)))
            except OSError:
                break


def decode_covert(packets, num_symbols, n):
    """Decode covert symbols from the first *num_symbols* packets by time.

    Covert packets are sent before dummy traffic, so the earliest
    packets carry the hidden data.
    """
    sorted_pkts = sorted(packets, key=lambda p: p[0])
    decoded = []
    for i in range(min(num_symbols, len(sorted_pkts))):
        decoded.append(decode_symbol(sorted_pkts[i][1], n))
    while len(decoded) < num_symbols:
        decoded.append(0)
    return decoded


def main():
    args = parse_args()

    collector = PacketCollector()
    collector.start()
    print(f"[P2] UDP collector listening on :{UDP_PORT}")

    # TCP control server
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("0.0.0.0", TCP_PORT))
    srv.listen(1)
    print(f"[P2] TCP control listening on :{TCP_PORT}")

    conn, addr = srv.accept()
    print(f"[P2] Control connection from {addr}")

    params = None

    while True:
        msg = recv_control(conn)
        if not msg:
            break

        if msg["type"] == "start":
            params = msg
            print(f"[P2] START — {params['num_symbols']} symbols, "
                  f"L={params['L']}, n={params['n']}, "
                  f"T={params['interval']}s, buf={params['buffer_size']}")

        elif msg["type"] == "end":
            print("[P2] END received, decoding ...")
            collector.stop()
            time.sleep(0.2)

            alphabet = params["L"] // params["n"]
            symbols = decode_covert(
                collector.packets,
                params["num_symbols"],
                params["n"],
            )
            result = symbols_to_message(symbols, alphabet, params["num_bytes"])

            total_pkts = len(collector.packets)
            covert_pkts = params["num_symbols"]
            dummy_pkts = total_pkts - covert_pkts
            print(f"[P2] Packets: {total_pkts} total, "
                  f"{covert_pkts} covert, {dummy_pkts} dummy")

            print(f"[P2] Decoded bytes (hex): {result.hex()}")
            try:
                text = result.decode("utf-8")
                print(f"[P2] Decoded message: {text}")
            except UnicodeDecodeError:
                print(f"[P2] Cannot decode as UTF-8 ({len(result)} bytes)")

            if args.output:
                with open(args.output, "wb") as fh:
                    fh.write(result)
                print(f"[P2] Saved to {args.output}")

            break

    conn.close()
    srv.close()
    print("[P2] Done")


if __name__ == "__main__":
    main()
