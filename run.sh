#!/usr/bin/env bash
# run.sh — Automated launcher for the covert channel lab stand.
# Usage:
#   ./run.sh                         # sends default message
#   ./run.sh Hello world             # sends "Hello world"
#   ./run.sh --raw -f secret.txt     # forward raw args to sender.py
set -e

# ── Parse arguments ──
if [ "$1" = "--raw" ]; then
    shift
    SENDER_ARGS="$*"
elif [ $# -gt 0 ]; then
    SENDER_ARGS="-m \"$*\""
else
    SENDER_ARGS='-m "Hello from covert channel"'
fi

echo "=== Covert Channel Lab Stand ==="
echo ""

# ── 1. Ensure VMs are running ──
echo "[1/5] Starting VMs (may take a few minutes on first run) ..."
vagrant up
echo ""

# ── 2. Kill leftover processes from previous runs ──
echo "[2/5] Cleaning up previous runs ..."
vagrant ssh p2 -c "pkill -f receiver.py 2>/dev/null; pkill -f start_daemon 2>/dev/null; rm -f /tmp/receiver.log /tmp/decoded.txt" 2>/dev/null || true
vagrant ssh uz -c "pkill -f security_device.py 2>/dev/null; pkill -f start_daemon 2>/dev/null; rm -f /tmp/uz.log" 2>/dev/null || true
sleep 1

# ── 3. Start receiver (P2) via daemon helper ──
echo "[3/5] Starting receiver on P2 ..."
vagrant ssh p2 -c "cd /home/vagrant/scripts && python3 start_daemon.py /tmp/receiver.log receiver.py -o /tmp/decoded.txt"
sleep 2

# ── 4. Start security device (UZ) via daemon helper ──
echo "[4/5] Starting security device on UZ ..."
vagrant ssh uz -c "cd /home/vagrant/scripts && python3 start_daemon.py /tmp/uz.log security_device.py"
sleep 2

# ── 5. Run sender (P1) — blocks until transmission completes ──
echo "[5/5] Sending covert message ..."
echo ""
vagrant ssh p1 -c "cd /home/vagrant/scripts && python3 sender.py $SENDER_ARGS"
echo ""

# ── Collect results ──
sleep 3
echo "========== Receiver log =========="
vagrant ssh p2 -c "cat /tmp/receiver.log 2>/dev/null" || true
echo ""
echo "========== Decoded message =========="
vagrant ssh p2 -c "cat /tmp/decoded.txt 2>/dev/null" || echo "(binary or empty)"
echo ""
echo "=== Done ==="
