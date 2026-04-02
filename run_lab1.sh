#!/usr/bin/env bash
# run_lab1.sh — Lab 1 demo: passive security device
set -e

MSG="Hello from covert channel"

echo "============================================="
echo "=== Lab 1: Passive Security Device        ==="
echo "============================================="
echo ""

echo "[0] Cleaning up ..."
vagrant ssh p2 -c "pkill -f receiver.py 2>/dev/null; pkill -f start_daemon 2>/dev/null; rm -f /tmp/receiver.log /tmp/decoded.txt" 2>/dev/null || true
vagrant ssh uz -c "pkill -f security_device.py 2>/dev/null; pkill -f start_daemon 2>/dev/null; rm -f /tmp/uz.log" 2>/dev/null || true
sleep 2

echo "[1/3] Starting receiver on P2 ..."
vagrant ssh p2 -c "cd /home/vagrant/scripts && python3 start_daemon.py /tmp/receiver.log receiver.py -o /tmp/decoded.txt"
sleep 2

echo "[2/3] Starting security device on UZ (passive) ..."
vagrant ssh uz -c "cd /home/vagrant/scripts && python3 start_daemon.py /tmp/uz.log security_device.py --mode passive"
sleep 2

echo "[3/3] Sending: \"$MSG\" ..."
echo ""
vagrant ssh p1 -c "cd /home/vagrant/scripts && python3 sender.py -m \"$MSG\""
echo ""

sleep 3
echo "========== Receiver log =========="
vagrant ssh p2 -c "cat /tmp/receiver.log 2>/dev/null" || true
echo ""
echo "========== Decoded =========="
vagrant ssh p2 -c "cat /tmp/decoded.txt 2>/dev/null" || echo "(empty)"
echo ""
echo "========== Lab 1 Done =========="

vagrant ssh uz -c "pkill -f security_device.py 2>/dev/null" 2>/dev/null || true
