#!/usr/bin/env bash
# run.sh — Start all VMs for the covert channel lab stand.
# After VMs are up, use run_lab1.sh or run_lab3.sh to run demos.
set -e

echo "=== Starting VMs ==="
vagrant up
echo ""
echo "VMs ready. Next steps:"
echo "  ./run_lab1.sh           — Lab 1: passive security device"
echo "  ./run_lab3.sh           — Lab 3: active countermeasures"
