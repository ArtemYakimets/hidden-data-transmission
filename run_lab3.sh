#!/usr/bin/env bash
# run_lab3.sh — Lab 3 demo: active security device countermeasures
# Runs two schemes sequentially and shows comparison.
set -e

MSG="Hello from covert channel"

echo "============================================="
echo "=== Lab 3: Active Security Device         ==="
echo "============================================="
echo ""
echo "Original message: \"$MSG\""
echo ""

# ─────────────────────────────────────────────────
# Scheme 1: Normalize packet lengths (k=32)
# ─────────────────────────────────────────────────
echo "--- Scheme 1: Normalize (k=32) ---"
echo "    Limits covert channel bandwidth"
echo ""

vagrant ssh p2 -c "pkill -f receiver.py 2>/dev/null; pkill -f start_daemon 2>/dev/null; rm -f /tmp/receiver.log /tmp/decoded.txt" 2>/dev/null || true
vagrant ssh uz -c "pkill -f security_device.py 2>/dev/null; pkill -f start_daemon 2>/dev/null; rm -f /tmp/uz.log" 2>/dev/null || true
sleep 2

echo "[1/3] Starting receiver ..."
vagrant ssh p2 -c "cd /home/vagrant/scripts && python3 start_daemon.py /tmp/receiver.log receiver.py -o /tmp/decoded.txt"
sleep 2

echo "[2/3] Starting security device (normalize, k=32) ..."
vagrant ssh uz -c "cd /home/vagrant/scripts && python3 start_daemon.py /tmp/uz.log security_device.py --mode normalize --k 32"
sleep 2

echo "[3/3] Sending message ..."
vagrant ssh p1 -c "cd /home/vagrant/scripts && python3 sender.py -m \"$MSG\""
echo ""

sleep 3
vagrant ssh uz -c "pkill -TERM -f security_device.py 2>/dev/null; sleep 1" 2>/dev/null || true

echo "--- Scheme 1: UZ stats ---"
vagrant ssh uz -c "cat /tmp/uz.log 2>/dev/null" || true
echo ""
echo "--- Scheme 1: Receiver output ---"
vagrant ssh p2 -c "cat /tmp/receiver.log 2>/dev/null" || true
echo ""

# ─────────────────────────────────────────────────
# Scheme 2: Pad all packets to L=1024
# ─────────────────────────────────────────────────
echo ""
echo "--- Scheme 2: Pad to fixed length (L=1024) ---"
echo "    Completely eliminates covert channel"
echo ""

vagrant ssh p2 -c "pkill -f receiver.py 2>/dev/null; pkill -f start_daemon 2>/dev/null; rm -f /tmp/receiver.log /tmp/decoded.txt" 2>/dev/null || true
vagrant ssh uz -c "pkill -f security_device.py 2>/dev/null; pkill -f start_daemon 2>/dev/null; rm -f /tmp/uz.log" 2>/dev/null || true
sleep 2

echo "[1/3] Starting receiver ..."
vagrant ssh p2 -c "cd /home/vagrant/scripts && python3 start_daemon.py /tmp/receiver.log receiver.py -o /tmp/decoded.txt"
sleep 2

echo "[2/3] Starting security device (pad, L=1024) ..."
vagrant ssh uz -c "cd /home/vagrant/scripts && python3 start_daemon.py /tmp/uz.log security_device.py --mode pad --max-len 1024"
sleep 2

echo "[3/3] Sending message ..."
vagrant ssh p1 -c "cd /home/vagrant/scripts && python3 sender.py -m \"$MSG\""
echo ""

sleep 3
vagrant ssh uz -c "pkill -TERM -f security_device.py 2>/dev/null; sleep 1" 2>/dev/null || true

echo "--- Scheme 2: UZ stats ---"
vagrant ssh uz -c "cat /tmp/uz.log 2>/dev/null" || true
echo ""
echo "--- Scheme 2: Receiver output ---"
vagrant ssh p2 -c "cat /tmp/receiver.log 2>/dev/null" || true
echo ""

echo "============================================="
echo "=== Lab 3 Complete                        ==="
echo "============================================="
