"""Inventory one actual Firecracker-published x86_64 vmlinux + .config pair.

NON-TRUSTED discovery only. Official public S3 objects are mutable and not
authenticated release artifacts. Never execute, boot or promote these bytes.
The exact object's key, SHA256 and status are output only as review evidence.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import re
import ssl
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

from .__main__ import ROOT
from .g22_kernel_compat import GUEST_REQUIRED

BASE = "https://s3.amazonaws.com/spec.ccfc.min"
BUCKET_PREFIX = "firecracker-ci/"
BUILD_PREFIX = re.compile(r"^firecracker-ci/[0-9]{8}-[A-Za-z0-9_.-]+/$")
KERNEL_KEY = re.compile(
    r"^(firecracker-ci/[0-9]{8}-[A-Za-z0-9_.-]+/x86_64/)"
    r"(vmlinux-6\.18\.[0-9]{1,3})$"
)
MAX_XML = 4 * 1024 * 1024
MAX_CONFIG = 2 * 1024 * 1024
MAX_BINARY = 256 * 1024 * 1024


class InventoryError(RuntimeError):
    pass


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _client():
    return urllib.request.build_opener(
        urllib.request.ProxyHandler({}), _NoRedirect(),
        urllib.request.HTTPSHandler(context=ssl.create_default_context()),
    )


def _read_bounded(client, url: str, limit: int) -> bytes:
    with client.open(url, timeout=25) as resp:
        if resp.geturl() != url or resp.status != 200:
            raise InventoryError("Unexpected official asset origin/response")
        length = resp.headers.get("Content-Length")
        if length and int(length) > limit:
            raise InventoryError("Asset larger than safety cap")
        raw = resp.read(limit + 1)
    if len(raw) > limit:
        raise InventoryError("Asset larger than safety cap")
    return raw


def _list(client, prefix: str, *, delimiter: str | None = None) -> tuple[list[str], list[str]]:
    keys: list[str] = []
    prefixes: list[str] = []
    cursor = None
    for _ in range(8):
        params = {"list-type": "2", "prefix": prefix, "max-keys": "1000"}
        if delimiter is not None:
            params["delimiter"] = delimiter
        if cursor:
            params["continuation-token"] = cursor
        url = BASE + "?" + urllib.parse.urlencode(params)
        response = _read_bounded(client, url, MAX_XML)
        try:
            doc = ET.fromstring(response)
        except ET.ParseError as exc:
            raise InventoryError("Malformed official object listing") from exc
        namespace = {"s": doc.tag.partition("}")[0].lstrip("{")} if "}" in doc.tag else {}
        tag = (lambda x: "s:" + x) if namespace else (lambda x: x)
        keys.extend(el.text or "" for el in doc.findall(
            tag("Contents") + "/" + tag("Key"), namespace))
        prefixes.extend(el.text or "" for el in doc.findall(
            tag("CommonPrefixes") + "/" + tag("Prefix"), namespace))
        truncated = doc.findtext(tag("IsTruncated"), namespaces=namespace)
        if truncated != "true":
            return keys, prefixes
        cursor = doc.findtext(tag("NextContinuationToken"), namespaces=namespace)
        if not cursor:
            raise InventoryError("Truncated listing without continuation token")
    raise InventoryError("Inventory pagination exceeded safety cap")


def _stream_sha256(client, key: str) -> tuple[str, int, bytes]:
    if not KERNEL_KEY.fullmatch(key):
        raise InventoryError("Kernel key outside reviewed naming profile")
    url = BASE + "/" + urllib.parse.quote(key, safe="/")
    h = hashlib.sha256()
    total = 0
    header = b""
    with client.open(url, timeout=90) as response:
        if response.geturl() != url or response.status != 200:
            raise InventoryError("Unexpected kernel download destination")
        size = response.headers.get("Content-Length")
        if size and int(size) > MAX_BINARY:
            raise InventoryError("Kernel exceeds allowed download size")
        while True:
            data = response.read(min(1024 * 1024, MAX_BINARY - total + 1))
            if not data:
                break
            total += len(data)
            if total > MAX_BINARY:
                raise InventoryError("Kernel exceeds allowed download size")
            if len(header) < 64:
                header = (header + data)[:64]
            h.update(data)
    return h.hexdigest(), total, header


def _config_requirements(raw: bytes) -> tuple[bool, list[str]]:
    try:
        text = raw.decode("ascii")
    except UnicodeError:
        return False, sorted(GUEST_REQUIRED)
    values = {}
    for line in text.splitlines():
        if line.startswith("CONFIG_"):
            k, sep, v = line.partition("=")
            if not sep or k in values:
                return False, sorted(GUEST_REQUIRED)
            values[k] = v
    missing = sorted(k for k in GUEST_REQUIRED if values.get(k) != "y")
    return not missing, missing


def inventory(client=None) -> dict:
    client = client if client is not None else _client()
    _, roots = _list(client, BUCKET_PREFIX, delimiter="/")
    builds = sorted(x for x in roots if BUILD_PREFIX.fullmatch(x))
    if not builds:
        raise InventoryError("No reviewed-shape public Firecracker CI build prefix")
    # Look through latest three official dated builds in case the most recent
    # build does not publish a 6.18 vmlinux + .config pair.
    selected = None
    for build in reversed(builds[-3:]):
        keys, _ = _list(client, build + "x86_64/vmlinux-")
        possible = sorted(
            (KERNEL_KEY.fullmatch(k).group(2), k) for k in keys
            if KERNEL_KEY.fullmatch(k)
        )
        for _, kernel in reversed(possible):
            if kernel + ".config" in keys:
                selected = (build, kernel, kernel + ".config")
                break
        if selected is not None:
            break
    if selected is None:
        raise InventoryError("No exact 6.18 vmlinux/config object pair")
    build, kernel_key, config_key = selected
    config_url = BASE + "/" + urllib.parse.quote(config_key, safe="/")
    raw_config = _read_bounded(client, config_url, MAX_CONFIG)
    compatible, missing = _config_requirements(raw_config)
    config_sha = hashlib.sha256(raw_config).hexdigest()
    kernel_sha, kernel_bytes, hdr = _stream_sha256(client, kernel_key)
    correct_elf = (
        len(hdr) >= 20 and hdr[:4] == b"\x7fELF" and
        hdr[4:6] == b"\x02\x01" and int.from_bytes(hdr[18:20], "little") == 62
    )
    return {
        "contract": "foundation.firecracker-kernel-discovery/v0",
        "assessment": "official-public-CI-candidate-UNTRUSTED-NOT-BOOTED",
        "observedAt": datetime.now(timezone.utc).isoformat(),
        "source": "firecracker-public-ci-s3",
        "buildPrefix": build,
        "kernelKey": kernel_key,
        "configKey": config_key,
        "kernelSha256": kernel_sha,
        "configSha256": config_sha,
        "kernelBytes": kernel_bytes,
        "x86_64Elf": correct_elf,
        "requiredConfigBuiltIn": compatible,
        "missingRequiredOptions": missing,
        "operatorPinned": False,
        "kernelBuildProvenanceAuthenticated": False,
        "guestBootVerified": False,
        "vmAdmissionAllowed": False,
    }


def _verified_pinned_receipt(client=None, receipt_path: Path | None = None) -> dict:
    """Re-download immutable *named* S3 objects and fail on any hash drift.

    Source identity and checksums are only data integrity here, NOT signatures.
    The pinned receipt was first seen in a GitHub-hosted unsigned CI artifact.
    """
    path = receipt_path or (ROOT / "docs" / "g23-pinned-kernel-receipt.json")
    try:
        expected = json.loads(path.read_text(encoding="utf-8"))
        key = expected["kernelKey"]
        config_key = expected["configKey"]
        if (not KERNEL_KEY.fullmatch(key) or config_key != key + ".config" or
                expected["buildPrefix"] != key.split("x86_64/")[0] or
                not re.fullmatch(r"[0-9a-f]{64}", expected["kernelSha256"]) or
                not re.fullmatch(r"[0-9a-f]{64}", expected["configSha256"])):
            raise InventoryError("Kernel pin receipt shape invalid")
        client = client if client is not None else _client()
        config_raw = _read_bounded(
            client, BASE + "/" + urllib.parse.quote(config_key, safe="/"), MAX_CONFIG)
        config_digest = hashlib.sha256(config_raw).hexdigest()
        kernel_digest, kernel_bytes, hdr = _stream_sha256(client, key)
        if (config_digest != expected["configSha256"] or
                kernel_digest != expected["kernelSha256"] or
                kernel_bytes != expected["kernelBytes"]):
            raise InventoryError("Public CI kernel bytes no longer match pinned receipt")
        compatible, missing = _config_requirements(config_raw)
        correct_elf = (len(hdr) >= 20 and hdr[:6] == b"\x7fELF\x02\x01"
                       and int.from_bytes(hdr[18:20], "little") == 62)
        if not compatible or not correct_elf:
            raise InventoryError("Pinned kernel/config no longer meet reviewed profile")
        return {
            **expected,
            "assessment": "pinned-SHA256-object-bytes-confirmed-NOT-attested-NOT-booted",
            "recheckedAt": datetime.now(timezone.utc).isoformat(),
            "pinVerified": True,
            "kernelBuildProvenanceAuthenticated": False,
            "operatorApproved": False,
            "guestBootVerified": False, "vmAdmissionAllowed": False,
            "missingRequiredOptions": missing,
        }
    except (OSError, KeyError, ValueError, TypeError) as exc:
        if isinstance(exc, InventoryError):
            raise
        raise InventoryError("Kernel receipt unreadable/invalid") from exc


def main(argv=None) -> int:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--pinned", action="store_true",
                        help="Verify exactly the already-received SHA256-pinned 6.18.51 object pair")
    opts = parser.parse_args(argv)
    target = ROOT / "artifacts" / "g23-official-kernel-inventory.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        record = _verified_pinned_receipt() if opts.pinned else inventory()
        target.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
        print(json.dumps({
            "assessment": record["assessment"],
            "kernelKey": record["kernelKey"],
            "kernelSha256": record["kernelSha256"],
            "pinVerified": record.get("pinVerified", False),
            "requiredConfigBuiltIn": record.get("requiredConfigBuiltIn", True),
            "guestBootVerified": False,
        }))
        return 0 if (record.get("pinVerified", False)
                     if opts.pinned else
                     record["requiredConfigBuiltIn"] and record["x86_64Elf"]) else 3
    except (InventoryError, OSError, ValueError, ET.ParseError,
            urllib.error.URLError) as exc:
        target.write_text(json.dumps({
            "contract": "foundation.firecracker-kernel-discovery/v0",
            "assessment": "discovery-blocked",
            "reason": type(exc).__name__,
            "guestBootVerified": False, "vmAdmissionAllowed": False,
        }, indent=2) + "\n")
        print('{"assessment":"discovery-blocked","guestBootVerified":false}')
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
