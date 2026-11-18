#!/usr/bin/env python3
"""Quick and dirty test client for the STM32 pi_comm_task protocol.

Wiring: STM32 USART6 (PC6 = TX, PC7 = RX) <-> Pi UART (GPIO14 TX, GPIO15 RX), common GND.
UART: 115200 8N1.

Current protocol (single bytes):
  IDLE:      Pi 'S' -> STM 'A'   then   Pi 'G' (within 2 s) -> STM 'A', STM enters MEASURING
             anything else -> STM 'N'


Usage:
  pip install pyserial
  python3 pi_comm.py [--port /dev/serial0]        # interactive
  python3 pi_comm.py start                         # just do the start handshake
  python3 pi_comm.py stop                          # send 'P' (back to IDLE)
"""
import argparse
import sys
import serial
import time
import struct

START = b"S"
STOP = b"P"
REQ_LEN = b"L"
REQ_PSD = b"D"
CLEAR = b"C"
ACK = b"A"
NACK = b"N"

# PSD settings (must match the STM: SAMPLING_RATE, N_FFT)
FS = 3200
N_FFT = 4096
HZ_PER_BIN = FS / N_FFT     # 0.78125 Hz


def send(ser, byte, msg_len):
    ser.write(byte)
    ser.flush()
    reply = ser.read(msg_len)  # returns b"" on timeout
    print(f"  sent {byte!r} -> got {reply!r}" + ("  (no reply)" if not reply else ""))
    return reply


def start(ser):
    ser.reset_input_buffer()
    print("Start handshake:")
    if send(ser, START, 1) != ACK:
        print("FAILED: no ACK to START_READY")
        return False
    print("OK: STM should now be MEASURING")
    return True


def stop(ser):
    ser.reset_input_buffer()
    print("Stop handshake:")
    if send(ser, STOP, 1) != ACK:
        print("FAILED: no ACK to Stop")
        return False
    print("STM should now be REPORTING")
    return True; 

def get_psd(ser):
    ser.reset_input_buffer()
    print("Get PSD LEN:")

    length = send(ser, REQ_LEN, 4)
    if length == NACK or len(length) != 4:
        print("FAILED: STM didnt send length")
        return False

    length = int.from_bytes(length, "little")   # b'\x0c\x60\x00\x00' -> 24588

    # PSD takes ~2.1 s at 115200 baud, so stretch the read timeout for this one
    old_timeout = ser.timeout
    ser.timeout = length * 10 / ser.baudrate * 2 + 1
    psd = send(ser, REQ_PSD, length)
    ser.timeout = old_timeout

    if psd == NACK or len(psd) != length:
        print("FAILED: STM didnt send PSD (got " + str(len(psd)) + " of " + str(length) + " bytes)")
        return False

    if send(ser, CLEAR, 1) != ACK:
        print("Clear Failed: STM no ACK")
        return False

    # raw bytes -> floats, float32 little-endian, psd_out[3][N_BINS] (x, y, z)
    n_bins = length // 4 // 3
    vals = struct.unpack("<" + str(length // 4) + "f", psd)
    psd = [vals[0:n_bins], vals[n_bins:2*n_bins], vals[2*n_bins:3*n_bins]]

    print("PSD Succsefully transferred")
    print("\nLength = " + str(length))
    print_histogram(psd)

    return psd, length


def print_histogram(psd, n_bands=32, width=50):
    # groups the PSD bins into n_bands frequency bands and prints a bar per band
    # bin 0 (DC / gravity) is skipped so it doesnt swamp everything else
    for axis, name in enumerate(["X", "Y", "Z"]):
        bins = psd[axis][1:]
        per_band = len(bins) // n_bands

        bands = []
        for b in range(n_bands):
            bands.append(sum(bins[b * per_band:(b + 1) * per_band]))

        peak = max(bands)
        if peak <= 0:
            peak = 1

        peak_bin = bins.index(max(bins)) + 1
        print("\n" + name + " axis  (peak bin at " + f"{peak_bin * HZ_PER_BIN:.1f}" + " Hz)")

        for b in range(n_bands):
            f_lo = (1 + b * per_band) * HZ_PER_BIN
            f_hi = (1 + (b + 1) * per_band) * HZ_PER_BIN
            bar = "#" * int(bands[b] / peak * width)
            print(f"{f_lo:7.1f}-{f_hi:7.1f} Hz | {bar:<{width}} {bands[b]:.3g}")


def interactive(ser):
    print("Commands: s = start handshake, p = stop, r <char> = raw byte, q = quit, l = get_psd, h = redraw histogram")
    last_psd = None
    while True:
        try:
            cmd = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if cmd == "s":
            start(ser)
        elif cmd == "p":
            stop(ser)
        elif cmd == "l":
            result = get_psd(ser)
            if result:
                last_psd = result[0]
        elif cmd == "h":
            if last_psd:
                print_histogram(last_psd)
            else:
                print("No PSD yet, run l first")
        elif cmd.startswith("r ") and len(cmd) >= 3:
            send(ser, cmd[2].encode(), 1)
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

    with serial.Serial(args.port, args.baud, timeout=2) as ser:
        if args.cmd == "start":
            sys.exit(0 if start(ser) else 1)
        elif args.cmd == "stop":
            stop(ser)
        else:
            interactive(ser)


if __name__ == "__main__":
    main()
