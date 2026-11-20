import logging
import struct

import numpy as np
import serial

START = b"S"
CAPTURE = b"T"
STOP = b"P"
REQ_LEN = b"L"
REQ_PSD = b"D"
CLEAR = b"C"
ACK = b"A"
NACK = b"N"

# must match SAMPLING_RATE and N_FFT in the STM firmware
FS = 3200
N_FFT = 4096
N_BINS = N_FFT // 2 + 1
HZ_PER_BIN = FS / N_FFT
AXIS_NUMBER = 3
PSD_BYTES = AXIS_NUMBER * N_BINS * 4
# must match CAPTURE_MAX in the STM firmware
CAPTURE_SECONDS = 10

POLL_INTERVAL = 0.01
ACK_TIMEOUT = 2.0
LEN_TIMEOUT = 5.0


class AccelerometerError(Exception):
    pass


class AccelerometerSerial:
    def __init__(self, reactor, port="/dev/serial0", baud=115200):
        self.reactor = reactor
        self.port = port
        self.baudrate = baud
        self.serial = None

    def _ensure_open(self):
        if self.serial is not None and self.serial.is_open:
            return
        try:
            self.serial = serial.Serial(self.port, self.baudrate, timeout=0)
        except serial.SerialException as e:
            self.serial = None
            raise AccelerometerError(
                f"Cannot open accelerometer port {self.port}: {e}")

    def _read(self, msg_len, timeout):
        buf = bytearray()
        deadline = self.reactor.monotonic() + timeout
        while len(buf) < msg_len:
            waiting = self.serial.in_waiting
            if waiting:
                buf += self.serial.read(min(waiting, msg_len - len(buf)))
                continue
            now = self.reactor.monotonic()
            if now >= deadline:
                break
            self.reactor.pause(now + POLL_INTERVAL)
        return bytes(buf)

    def send(self, byte, msg_len, timeout=ACK_TIMEOUT):
        self._ensure_open()
        self.serial.write(byte)
        self.serial.flush()
        reply = self._read(msg_len, timeout)
        logging.info("accelerometer: sent %r -> got %d byte(s)",
                     byte, len(reply))
        return reply

    def _command(self, byte, name):
        self._ensure_open()
        self.serial.reset_input_buffer()
        if self.send(byte, 1) != ACK:
            raise AccelerometerError(f"No ACK to {name}")

    def start_cmd(self):
        self._command(START, "START")

    def stop_cmd(self):
        self._command(STOP, "STOP")

    def start_capture(self):
        self._command(CAPTURE, "CAPTURE")

    def _fetch(self):
        self._ensure_open()
        self.serial.reset_input_buffer()

        raw_len = self.send(REQ_LEN, 4, LEN_TIMEOUT)
        if len(raw_len) != 4:
            raise AccelerometerError(
                f"STM didn't send length (got {raw_len!r})")
        # b'\x0c\x60\x00\x00' -> 24588
        length = int.from_bytes(raw_len, "little")

        timeout = length * 10 / self.baudrate * 2 + 1
        raw = self.send(REQ_PSD, length, timeout)
        if len(raw) != length:
            raise AccelerometerError(
                f"STM didn't send all data (got {len(raw)} of {length} bytes)")

        if self.send(CLEAR, 1) != ACK:
            raise AccelerometerError("Clear failed: STM no ACK")
        return raw

    def get_psd(self):
        raw = self._fetch()
        if len(raw) != PSD_BYTES:
            raise AccelerometerError(
                f"Unexpected PSD length {len(raw)}, expected {PSD_BYTES} "
                f"({AXIS_NUMBER} axes x {N_BINS} bins x 4 bytes); "
                f"check FS/N_FFT against the firmware")

        # raw bytes -> float32 little-endian, psd_out[3][N_BINS] (x, y, z)
        vals = struct.unpack(f"<{AXIS_NUMBER * N_BINS}f", raw)
        return [list(vals[a * N_BINS:(a + 1) * N_BINS])
                for a in range(AXIS_NUMBER)]

    def get_capture(self):
        raw = self._fetch()
        if len(raw) % 6:
            raise AccelerometerError(f"Bad capture length {len(raw)}")
        # int16 mg, one (x, y, z) row per sample
        return np.frombuffer(raw, dtype="<i2").reshape(-1, 3)

    def abort(self):
        for byte, name in ((STOP, "STOP"), (CLEAR, "CLEAR")):
            try:
                self._command(byte, name)
            except Exception as e:
                logging.info("accelerometer abort: %s", e)
