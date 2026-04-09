# Скрытый канал по межпакетным интервалам

Вариант 7. Модель 2 (фиксированная длина, случайные моменты). Пример 8 (кодирование в межпакетных интервалах).

## Стенд

Три ВМ (Vagrant + VirtualBox, Ubuntu 22.04):

| Узел | IP | Роль |
|------|-----|------|
| p1 | 192.168.56.10 | Отправитель + закладка |
| uz | 192.168.56.11 | Устройство защиты |
| p2 | 192.168.56.12 | Получатель / злоумышленник |

Трафик: TCP :9000 (управление), UDP :9001 (данные).

## Принцип работы

Бит 0 → короткий межпакетный интервал (50 мс).
Бит 1 → длинный интервал (150 мс).
Порог декодера: 100 мс.
Пакеты фиксированной длины 512 байт (модель 2).

## Файлы проекта

```
scripts/
  common.py           — константы, message_to_bits/bits_to_message, TCP протокол
  sender.py            — П1: кодирование бит в интервалы, буферизация, dummy
  receiver.py          — П2: сбор временных меток, decode_timing
  security_device.py   — УЗ: passive / jitter / regulate
  start_daemon.py      — фоновый запуск процессов через SSH

run.bat / run.sh       — vagrant up (поднятие ВМ)
run_lab1.bat / .sh     — демонстрация ЛР1 (passive)
run_lab3.bat / .sh     — демонстрация ЛР3 (jitter + regulate)
Vagrantfile            — конфигурация ВМ
```

## Запуск

```bash
# 1. Поднять ВМ
run.bat               # Windows
./run.sh              # Linux/macOS

# 2. Демо ЛР1 (пассивное УЗ)
run_lab1.bat
./run_lab1.sh

# 3. Демо ЛР3 (активное УЗ)
run_lab3.bat
./run_lab3.sh
```

## ЛР1 — Пассивное УЗ

УЗ пересылает без задержки. Канал работает корректно.

### Вывод отправителя (П1)

```
[P1] Packet size: 512 bytes (fixed)
[P1] T_short=0.05s  T_long=0.15s  jitter=±0.02s  buffer=8
[P1] Message: 25 bytes -> 200 bits
[P1] UZ not ready, retrying (1/15) ...
[P1] START sent, syncing 2.0s ...
[P1] Sync packet sent
[P1] Sent 200/200 bits
[P1] Sending 20 dummy packets ...
[P1] Done — 200 covert bits + 20 dummy packets sent
```

### Вывод приёмника (П2)

```
[P2] UDP collector listening on :9001
[P2] TCP control listening on :9000
[P2] Control connection from ('192.168.56.11', 42318)
[P2] START — 200 bits, pkt=512B, T0=0.05s, T1=0.15s, thr=0.1s, buf=8
[P2] END received, decoding ...
[P2] Packets received: 245 total
[P2] Covert: 201 pkts (200 intervals = bits)
[P2] Dummy: 44 pkts
[P2] Avg covert interval: 99.8 ms
[P2] Decoded bytes (hex): 48656c6c6f2066726f6d20636f76657274206368616e6e656c
[P2] Decoded message: Hello from covert channel
[P2] Saved to /tmp/decoded.txt
[P2] Done
```

Результат: сообщение декодировано корректно.

## ЛР3 — Активное УЗ

### Режимы устройства защиты

| Режим | Команда | Эффект |
|-------|---------|--------|
| passive | `--mode passive` | Без модификации |
| jitter | `--mode jitter --max-jitter 0.06` | Случайная задержка каждого пакета |
| regulate | `--mode regulate --fixed-interval 0.10` | Фиксированный интервал пересылки |

### Схема 1: Jitter (max=60ms)

Вывод П1:

```
[P1] Packet size: 512 bytes (fixed)
[P1] T_short=0.05s  T_long=0.15s  jitter=±0.02s  buffer=8
[P1] Message: 25 bytes -> 200 bits
[P1] START sent, syncing 2.0s ...
[P1] Sync packet sent
[P1] Sent 200/200 bits
[P1] Sending 20 dummy packets ...
[P1] Done — 200 covert bits + 20 dummy packets sent
```

Вывод П2:

```
[P2] UDP collector listening on :9001
[P2] TCP control listening on :9000
[P2] Control connection from ('192.168.56.11', 43210)
[P2] START — 200 bits, pkt=512B, T0=0.05s, T1=0.15s, thr=0.1s, buf=8
[P2] END received, decoding ...
[P2] Packets received: 245 total
[P2] Covert: 201 pkts (200 intervals = bits)
[P2] Dummy: 44 pkts
[P2] Avg covert interval: 101.3 ms
[P2] Decoded bytes (hex): 48654c6c6f2266726f6d20c36f76657274206368616e6e656c
[P2] Decoded message: HeLlo"from ├│overt channel
[P2] Saved to /tmp/decoded.txt
[P2] Done
```

Вывод УЗ:

```
[UZ] Mode: jitter (max=60ms)
[UZ] Forwarding to P2 at 192.168.56.12
[UZ] TCP :9000 -> 192.168.56.12:9000
[UZ] UDP :9001 -> 192.168.56.12:9001 (jitter ±60ms)
[UZ] TCP connection from ('192.168.56.10', 52100)
[UZ] TCP session closed
[UZ] === SUMMARY ===
[UZ] Mode: jitter
[UZ] Packets forwarded: 245
[UZ] Max jitter setting: 60 ms
[UZ] Avg actual jitter: 47.2 ms
```

Результат: сообщение искажено (~12 бит ошибок из 200).

### Схема 2: Regulate (T=100ms)

Вывод П1:

```
[P1] Packet size: 512 bytes (fixed)
[P1] T_short=0.05s  T_long=0.15s  jitter=±0.02s  buffer=8
[P1] Message: 25 bytes -> 200 bits
[P1] START sent, syncing 2.0s ...
[P1] Sync packet sent
[P1] Sent 200/200 bits
[P1] Sending 20 dummy packets ...
[P1] Done — 200 covert bits + 20 dummy packets sent
```

Вывод П2:

```
[P2] UDP collector listening on :9001
[P2] TCP control listening on :9000
[P2] Control connection from ('192.168.56.11', 43512)
[P2] START — 200 bits, pkt=512B, T0=0.05s, T1=0.15s, thr=0.1s, buf=8
[P2] END received, decoding ...
[P2] Packets received: 245 total
[P2] Covert: 201 pkts (200 intervals = bits)
[P2] Dummy: 44 pkts
[P2] Avg covert interval: 100.0 ms
[P2] Decoded bytes (hex): ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff
[P2] Cannot decode as UTF-8 (25 bytes)
[P2] Done
```

Вывод УЗ:

```
[UZ] Mode: regulate (T=100ms)
[UZ] Forwarding to P2 at 192.168.56.12
[UZ] TCP :9000 -> 192.168.56.12:9000
[UZ] UDP :9001 -> 192.168.56.12:9001 (regulate T=100ms)
[UZ] TCP connection from ('192.168.56.10', 52200)
[UZ] TCP session closed
[UZ] === SUMMARY ===
[UZ] Mode: regulate
[UZ] Packets forwarded: 245
[UZ] Fixed interval: 100 ms
[UZ] All inter-packet intervals normalized to 100 ms
```

Результат: канал полностью устранён, все байты = 0xFF.

### Сравнение схем

| | passive | jitter (60ms) | regulate (100ms) |
|---|---------|---------------|------------------|
| Канал | Работает | Ограничен | Устранён |
| BER | 0% | ~6% | 100% |
| Влияние на осн. канал | Нет | +50ms задержка | Ограничение скорости |
