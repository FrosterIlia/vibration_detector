#!/usr/bin/env python3
"""Quick and dirty test client for the STM32 pi_comm_task protocol.

Wiring: STM32 USART6 (PC6 = TX, PC7 = RX) <-> Pi UART (GPIO14 TX, GPIO15 RX), common GND.
UART: 115200 8N1.

Current protocol (single bytes):
  IDLE:      Pi 'S' -> STM 'A'   then   Pi 'G' (within 2 s) -> STM 'A', STM enters MEASURING
             anything else -> STM 'N'
  MEASURING: any byte sends the STM back to IDLE (no reply yet)

Usage:
  pip install pyserial
  python3 pi_comm.py [--port /dev/serial0]        # interactive
  python3 pi_comm.py start                         # just do the start handshake
  python3 pi_comm.py stop                          # send 'P' (back to IDLE)
"""
import argparse
import sys
import serial

START_READY = b"S"
START_GO = b"G"
STOP = b"P"
ACK = b"A"
NACK = b"N"


def send(ser, byte):
    ser.write(byte)
    ser.flush()
    reply = ser.read(1)  # returns b"" on timeout
    print(f"  sent {byte!r} -> got {reply!r}" + ("  (no reply)" if not reply else ""))
    return reply


def start(ser):
    ser.reset_input_buffer()
    print("Start handshake:")
    if send(ser, START_READY) != ACK:
        print("FAILED: no ACK to 'S'")
        return False
    if send(ser, START_GO) != ACK:
        print("FAILED: no ACK to 'G'")
        return False
    print("OK: STM should now be MEASURING")
    return True


def stop(ser):
    ser.reset_input_buffer()
    print("Stop:")
    send(ser, STOP)  # currently no reply expected
    print("STM should now be IDLE")


def interactive(ser):
    print("Commands: s = start handshake, p = stop, r <char> = raw byte, q = quit")
    while True:
        try:
            cmd = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if cmd == "s":
            start(ser)
        elif cmd == "p":
            stop(ser)
        elif cmd.startswith("r ") and len(cmd) >= 3:
            send(ser, cmd[2].encode())
        elif cmd == "q":
            break
        else:
            print("?")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", nargs="?", choices=["start", "stop"])
    ap.add_argument("--port", default="/dev/serial0")
    ap.add_argument("--baud", type=int, default=115200)
    args = ap.parse_args()

    with serial.Serial(args.port, args.baud, timeout=0.5) as ser:
        if args.cmd == "start":
            sys.exit(0 if start(ser) else 1)
        elif args.cmd == "stop":
            stop(ser)
        else:
            interactive(ser)


if __name__ == "__main__":
    main()
