"""Pure parsing of a Satisfactory ``.sav`` file into a small, normalized subset.

No I/O and no framework types — everything works on ``bytes`` so it can be unit
tested against synthetic fixtures. See the package docstring for the parsing
strategy and its deliberate limits.
"""

from __future__ import annotations

import re
import struct
import zlib
from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from app.errors import ValidationFailedError

# .NET ``DateTime`` epoch; save timestamps are ticks (100 ns) since this instant.
_DOTNET_EPOCH = datetime(1, 1, 1, tzinfo=UTC)

# zlib streams begin with 0x78 and one of these second bytes (compression level).
_ZLIB_SECOND_BYTES = frozenset({0x01, 0x5E, 0x9C, 0xDA})

# Actor instance names look like ``Build_ConstructorMk1_C_2147476374``. The class
# is the ``Build_..._C`` prefix; the trailing integer is the runtime instance id.
# Non-greedy middle so the first ``_C_<id>`` boundary ends the class.
_INSTANCE_RE = re.compile(rb"(Build_[A-Za-z0-9_]+?_C)_\d{4,}")

# Reject obviously non-save input early. Header versions have stayed small; a
# value outside this range means we are not looking at a save header.
_MAX_HEADER_VERSION = 100


class SaveParseError(ValidationFailedError):
    """The uploaded bytes are not a parseable Satisfactory save."""


@dataclass(frozen=True)
class SaveHeader:
    """The uncompressed metadata block at the start of a ``.sav`` file."""

    header_version: int
    save_version: int
    build_version: int
    map_name: str
    session_name: str
    play_duration_seconds: int
    saved_at: datetime | None
    session_visibility: int | None


@dataclass(frozen=True)
class ParsedSave:
    """Everything this app extracts from a save file."""

    header: SaveHeader
    #: ``Build_..._C`` class name -> number of distinct actor instances.
    building_counts: Counter[str] = field(default_factory=Counter)
    #: Bytes of decompressed body actually inflated (diagnostic / honesty).
    body_bytes: int = 0


def _read_fstring(buf: bytes, off: int) -> tuple[str, int]:
    """Read an Unreal ``FString`` (length-prefixed, null-terminated) at *off*.

    A negative length denotes UTF-16LE (count is in characters); a positive
    length denotes UTF-8 (count is in bytes). Returns the string and new offset.
    """
    (length,) = struct.unpack_from("<i", buf, off)
    off += 4
    if length == 0:
        return "", off
    if length < 0:
        byte_len = (-length) * 2
        raw = buf[off : off + byte_len]
        off += byte_len
        return raw.decode("utf-16-le", "replace").rstrip("\x00"), off
    raw = buf[off : off + length]
    off += length
    return raw.decode("utf-8", "replace").rstrip("\x00"), off


def _ticks_to_datetime(ticks: int) -> datetime | None:
    """Convert .NET ``DateTime`` ticks to a UTC datetime, or ``None`` if invalid."""
    if ticks <= 0:
        return None
    try:
        return _DOTNET_EPOCH + timedelta(microseconds=ticks // 10)
    except (OverflowError, ValueError):
        return None


def parse_header(data: bytes) -> SaveHeader:
    """Parse the save header.

    Only the leading fields (stable across versions) are read; optional trailing
    fields are ignored. Raises :class:`SaveParseError` if the bytes do not look
    like a save header.
    """
    if len(data) < 20:
        raise SaveParseError("File is too small to be a Satisfactory save")
    try:
        header_version, save_version, build_version = struct.unpack_from("<iii", data, 0)
        if not (0 < header_version <= _MAX_HEADER_VERSION) or save_version <= 0:
            raise SaveParseError("Unrecognized save header (bad version fields)")
        off = 12
        map_name, off = _read_fstring(data, off)
        _map_options, off = _read_fstring(data, off)
        session_name, off = _read_fstring(data, off)
        (play_duration,) = struct.unpack_from("<i", data, off)
        off += 4
        (ticks,) = struct.unpack_from("<q", data, off)
        off += 8
        visibility: int | None = None
        try:
            (visibility,) = struct.unpack_from("<b", data, off)
        except struct.error:
            visibility = None
    except (struct.error, IndexError) as exc:
        raise SaveParseError("Malformed save header") from exc

    return SaveHeader(
        header_version=header_version,
        save_version=save_version,
        build_version=build_version,
        map_name=map_name,
        session_name=session_name,
        play_duration_seconds=max(0, play_duration),
        saved_at=_ticks_to_datetime(ticks),
        session_visibility=visibility,
    )


def decompress_body(data: bytes) -> bytes:
    """Inflate every zlib stream in *data* and concatenate the results.

    Scanning for zlib streams (rather than parsing exact chunk framing) keeps the
    reader robust across save-format versions. Returns an empty ``bytes`` if no
    stream inflates.
    """
    out = bytearray()
    i = 0
    n = len(data)
    while i < n - 1:
        if data[i] == 0x78 and data[i + 1] in _ZLIB_SECOND_BYTES:
            decompressor = zlib.decompressobj()
            try:
                chunk = decompressor.decompress(data[i:])
            except zlib.error:
                i += 1
                continue
            if chunk:
                out += chunk
                consumed = (n - i) - len(decompressor.unused_data)
                i += max(consumed, 1)
                continue
        i += 1
    return bytes(out)


def extract_building_counts(body: bytes) -> Counter[str]:
    """Count distinct building actor instances by ``Build_..._C`` class name."""
    seen: set[bytes] = set()
    counts: Counter[str] = Counter()
    for match in _INSTANCE_RE.finditer(body):
        full = match.group(0)
        if full in seen:
            continue
        seen.add(full)
        counts[match.group(1).decode("ascii", "replace")] += 1
    return counts


def parse_save(data: bytes) -> ParsedSave:
    """Parse *data* (raw ``.sav`` bytes) into a :class:`ParsedSave`.

    The header is parsed strictly; a body that fails to decompress degrades to
    an empty building set rather than raising, so metadata is still surfaced.
    """
    header = parse_header(data)
    body = decompress_body(data)
    counts = extract_building_counts(body) if body else Counter()
    return ParsedSave(header=header, building_counts=counts, body_bytes=len(body))
