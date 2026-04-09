"""Receiver (P2) — decodes covert timing channel.

Collects UDP packets and measures inter-packet intervals.
Covert packets arrive first; intervals encode bits:
  interval < threshold → bit 0
  interval >= threshold → bit 1
"""

import argparse
import socket
import threading
import time

from common import (
    TCP_PORT, UDP_PORT,
    SYNC_DELAY, THRESHOLD,
    bits_to_message, recv_control,
)


def parse_args():
    """Parse CLI arguments for the receiver."""
    p = argparse.ArgumentParser(
        description="Covert timing channel receiver (P2)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("-o", "--output", type=str,
                   help="Save decoded message to file")
    return p.parse_args()


class PacketCollector:
    """Background UDP listener that records arrival timestamps."""

    def __init__(self):
        self.timestamps = []
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
                self.timestamps.append(time.time())
            except OSError:
                break


def decode_timing(timestamps, num_bits, threshold, buffer_size):
    """Decode bits from inter-packet intervals.

    Accounts for burst structure: every buffer_size covert packets
    are followed by one burst-separator packet whose interval is
    skipped during decoding.
    """
    sorted_ts = sorted(timestamps)
    intervals = []
    for i in range(1, len(sorted_ts)):
        intervals.append(sorted_ts[i] - sorted_ts[i - 1])

    bits = []
    iv_idx = 0
    bits_in_burst = 0

    while len(bits) < num_bits and iv_idx < len(intervals):
        iv = intervals[iv_idx]
        iv_idx += 1

        bits.append(0 if iv < threshold else 1)
        bits_in_burst += 1

        # Skip burst-separator interval
        if bits_in_burst >= buffer_size and len(bits) < num_bits:
            iv_idx += 1
            bits_in_burst = 0

    while len(bits) < num_bits:
        bits.append(0)

    return bits, intervals


def main():
    args = parse_args()

    collector = PacketCollector()
    collector.start()
    print(f"[P2] UDP collector listening on :{UDP_PORT}")

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
            print(f"[P2] START — {params['num_bits']} bits, "
                  f"pkt={params['pkt_size']}B, "
                  f"T0={params['t_short']}s, T1={params['t_long']}s, "
                  f"thr={params['threshold']}s, buf={params['buffer_size']}")

        elif msg["type"] == "end":
            print("[P2] END received, decoding ...")
            collector.stop()
            time.sleep(0.2)

            threshold = params.get("threshold", THRESHOLD)
            bits, intervals = decode_timing(
                collector.timestamps,
                params["num_bits"],
                threshold,
                params["buffer_size"],
            )
            result = bits_to_message(bits, params["num_bytes"])

            total_pkts = len(collector.timestamps)
            covert_pkts = params["num_bits"] + 1
            dummy_pkts = max(0, total_pkts - covert_pkts)

            print(f"[P2] Packets received: {total_pkts} total")
            print(f"[P2] Covert: {covert_pkts} pkts "
                  f"({params['num_bits']} intervals = bits)")
            print(f"[P2] Dummy: {dummy_pkts} pkts")

            if intervals:
                covert_ivs = intervals[:params["num_bits"]]
                if covert_ivs:
                    avg_iv = sum(covert_ivs) / len(covert_ivs)
                    print(f"[P2] Avg covert interval: {avg_iv*1000:.1f} ms")

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
