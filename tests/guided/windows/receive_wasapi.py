"""Receive a bounded WASAPI WAV recorded at the Windows guest render endpoint."""
import base64
import binascii
import gzip
import hashlib
import io


MAX_PCM = 16 * 1024 * 1024
MAX_COMPRESSED = 4 * 1024 * 1024


class LoopbackRecording:
    def __init__(self, header):
        size, digest = header.split()
        self.size = int(size)
        if not 44 < self.size <= MAX_PCM or len(bytes.fromhex(digest)) != 32:
            raise ValueError("Invalid WASAPI capture size or SHA-256")
        self.digest = digest
        self.compressed = bytearray()

    def append(self, line):
        offset, encoded = line.split()
        if len(self.compressed) != int(offset) or len(encoded) > 2048:
            raise ValueError("Invalid WASAPI record offset or length")
        try:
            chunk = base64.b64decode(encoded, validate=True)
        except binascii.Error as error:
            raise ValueError("Invalid WASAPI record encoding") from error
        if len(self.compressed) + len(chunk) > MAX_COMPRESSED:
            raise ValueError("Compressed WASAPI capture exceeds the transfer limit")
        self.compressed.extend(chunk)

    def save(self, path):
        with gzip.GzipFile(fileobj=io.BytesIO(self.compressed)) as stream:
            pcm = stream.read(self.size + 1)
        if len(pcm) != self.size or hashlib.sha256(pcm).hexdigest() != self.digest:
            raise ValueError("The received WASAPI recording does not match the guest SHA-256")
        path.write_bytes(pcm)
