import hashlib
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

from foundation.g23_kernel_inventory import (
    BASE, KERNEL_KEY, InventoryError, _list, _config_requirements,
    inventory, _stream_sha256, _verified_pinned_receipt,
)
from foundation.g22_kernel_compat import GUEST_REQUIRED


def listing(keys=(), prefixes=()):
    ns="http://s3.amazonaws.com/doc/2006-03-01/"
    root=ET.Element("ListBucketResult", xmlns=ns)
    ET.SubElement(root, "IsTruncated").text="false"
    for key in keys:
        ET.SubElement(ET.SubElement(root,"Contents"),"Key").text=key
    for pre in prefixes:
        ET.SubElement(ET.SubElement(root,"CommonPrefixes"),"Prefix").text=pre
    return ET.tostring(root)

class FakeResponse:
    def __init__(self,url,data):
        self.url=url
        self.data=data
        self.status=200
        self.headers={"Content-Length":str(len(data))}
        self.idx=0
    def __enter__(self):return self
    def __exit__(self,*args):return None
    def geturl(self):return self.url
    def read(self,size=None):
        if size is None: size=len(self.data)
        chunk=self.data[self.idx:self.idx+size]
        self.idx+=len(chunk)
        return chunk

class FakeClient:
    def __init__(self,configs):self.configs=configs
    def open(self,url,timeout=None):
        if url not in self.configs:raise InventoryError("Unexpected test URL")
        return FakeResponse(url,self.configs[url])

class KernelInventoryTests(unittest.TestCase):
    def test_6_18_official_pair_is_inventory_only(self):
        build="firecracker-ci/20261012-abcdef012345/"
        key=build+"x86_64/vmlinux-6.18.4"
        elf=bytearray(256)
        elf[:6]=b"\x7fELF\x02\x01"
        elf[18:20]=(62).to_bytes(2,"little")
        cfg=("".join(k+"=y\n" for k in sorted(GUEST_REQUIRED))).encode()
        from urllib.parse import urlencode
        rooturl=BASE+"?"+urlencode({"list-type":"2","prefix":"firecracker-ci/","max-keys":"1000","delimiter":"/"})
        nested=BASE+"?"+urlencode({"list-type":"2","prefix":build+"x86_64/vmlinux-","max-keys":"1000"})
        url=BASE+"/"+key
        client=FakeClient({
            rooturl:listing(prefixes=[build]),
            nested:listing(keys=[key,key+".config"]),
            url:bytes(elf),
            url+".config":cfg,
        })
        result=inventory(client)
        self.assertEqual(result["kernelSha256"],hashlib.sha256(elf).hexdigest())
        self.assertEqual(result["configSha256"],hashlib.sha256(cfg).hexdigest())
        self.assertTrue(result["requiredConfigBuiltIn"])
        self.assertTrue(result["x86_64Elf"])
        self.assertFalse(result["operatorPinned"])
        self.assertFalse(result["kernelBuildProvenanceAuthenticated"])
        self.assertFalse(result["vmAdmissionAllowed"])

    def test_verify_exact_pinned_receipt_fails_on_hash_drift(self):
        import json
        from urllib.parse import urlencode
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            build="firecracker-ci/20261012-test/"
            key=build+"x86_64/vmlinux-6.18.51"
            elf=bytearray(256)
            elf[:6]=b"\x7fELF\x02\x01"
            elf[18:20]=(62).to_bytes(2,"little")
            cfg=("".join(k+"=y\n" for k in sorted(GUEST_REQUIRED))).encode()
            receipt=root/"receipt.json"
            record={
                "buildPrefix":build,"kernelKey":key,"configKey":key+".config",
                "kernelSha256":hashlib.sha256(elf).hexdigest(),
                "configSha256":hashlib.sha256(cfg).hexdigest(),
                "kernelBytes":len(elf), "vmAdmissionAllowed":False,
            }
            receipt.write_text(json.dumps(record))
            ok=FakeClient({BASE+"/"+key:bytes(elf),BASE+"/"+key+".config":cfg})
            report=_verified_pinned_receipt(ok,receipt)
            self.assertTrue(report["pinVerified"])
            self.assertFalse(report["operatorApproved"])
            self.assertFalse(report["guestBootVerified"])
            record["kernelSha256"]="0"*64
            receipt.write_text(json.dumps(record))
            with self.assertRaises(InventoryError):
                _verified_pinned_receipt(ok,receipt)

    def test_reject_unreviewed_keys_and_disabled_driver(self):
        self.assertFalse(KERNEL_KEY.fullmatch("firecracker-ci/latest/x86_64/vmlinux-6.18.4"))
        self.assertFalse(KERNEL_KEY.fullmatch("firecracker-ci/20261012-a/x86_64/vmlinux-../../etc"))
        cfg=("".join(k+("=n" if k=="CONFIG_EXT4_FS" else "=y")+"\n"
                     for k in sorted(GUEST_REQUIRED))).encode()
        okay, missing=_config_requirements(cfg)
        self.assertFalse(okay)
        self.assertIn("CONFIG_EXT4_FS",missing)

    def test_byte_limit_and_redirect_refusal(self):
        from foundation.g23_kernel_inventory import _NoRedirect
        import urllib.request
        redir=_NoRedirect()
        request=urllib.request.Request(BASE)
        self.assertIsNone(redir.redirect_request(
            request,None,302,"redirect",{}, "https://attacker.invalid/"))
