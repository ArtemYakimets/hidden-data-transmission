"""Receiver (P2) / Attacker — decodes covert channel messages.

Collects UDP packets with timestamps, then uses timing analysis
to separate covert packets from dummy traffic and reconstruct
the hidden message from packet lengths.
"""

import argparse
import bisect
import socket
import threading
import time

from common import (
    TCP_PORT, UDP_PORT,
    SYNC_DELAY, BURST_DELAY,
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


def decode_covert(packets, num_symbols, n, interval, buffer_size, t0):
    """Extract covert symbols from captured packets using timing analysis.

    Covert packets arrive at predictable times (fixed interval, Model 3).
    Dummy packets arrive at random times and are filtered out.
    """
    sorted_pkts = sorted(packets, key=lambda p: p[0])
    times = [p[0] for p in sorted_pkts]

    # Burst delay: smaller of default or value that prevents burst overlap
    bd = (min(BURST_DELAY, interval / max(buffer_size, 1) / 3)
          if buffer_size > 1 else 0)
    tolerance = interval * 0.35

    decoded = []
    used = set()

    for si in range(num_symbols):
        burst_idx = si // buffer_size
        pos_in_burst = si % buffer_size
        expected = t0 + burst_idx * interval + pos_in_burst * bd

        # Binary-search + small window for nearest packet
        idx = bisect.bisect_left(times, expected)
        best, best_diff = None, float("inf")
        for c in range(max(0, idx - 10), min(len(sorted_pkts), idx + 10)):
            if c in used:
                continue
            d = abs(times[c] - expected)
            if d < best_diff:
                best_diff = d
                best = c

        if best is not None and best_diff < tolerance:
            decoded.append(decode_symbol(sorted_pkts[best][1], n))
            used.add(best)
        else:
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
    t0 = None

    while True:
        msg = recv_control(conn)
        if not msg:
            break

        if msg["type"] == "start":
            params = msg
            t0 = time.time() + SYNC_DELAY
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
                params["interval"],
                params["buffer_size"],
                t0,
            )
            result = symbols_to_message(symbols, alphabet, params["num_bytes"])

            total_pkts = len(collector.packets)
            covert_pkts = params["num_symbols"]
            dummy_pkts = total_pkts - covert_pkts
            print(f"[P2] Packets: {total_pkts} total, "
                  f"{covert_pkts} covert, {dummy_pkts} dummy")

            try:
                text = result.decode("utf-8")
                print(f"[P2] Decoded message: {text}")
            except UnicodeDecodeError:
                print(f"[P2] Decoded {len(result)} bytes (binary data)")

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
