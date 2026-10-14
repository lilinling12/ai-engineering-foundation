import tempfile
from pathlib import Path
import unittest
from unittest.mock import Mock
from foundation.g24_qemu_tcg import fixed_qemu_args, observe_guest, BootError
from foundation.g20_guest_serial import PREFIX


class QemuGuestTests(unittest.TestCase):
    def assets(self, root):
        result = [root / n for n in ("qemu-system-x86_64", "vmlinux", "rootfs.ext4")]
        for p in result:
            p.write_bytes(b"fixed synthetic test file")
        return result

    def test_software_tcg_only_no_net_and_readonly_rootfs(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            q, k, d = self.assets(root)
            args = fixed_qemu_args(q,k,d,root/"serial","b"*32)
            self.assertIn("tcg,thread=single", args)
            self.assertNotIn("-enable-kvm", args)
            self.assertIn("-nic", args)
            self.assertIn("none",args)
            self.assertIn("-no-user-config",args)
            self.assertTrue(any("readonly=on" in v for v in args))
            self.assertIn("virtio-blk-device,drive=rootdisk",args)

    def test_refuse_relative_or_existing_serial(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            q,k,d=self.assets(root)
            with self.assertRaises(BootError):
                fixed_qemu_args(q,k,d,Path("relative-serial"),"b"*32)
            serial=root/"serial"
            serial.write_text("stale")
            with self.assertRaises(BootError):
                fixed_qemu_args(q,k,d,serial,"b"*32)

    def test_safe_failure_classes_do_not_include_raw_guest_logs(self):
        from foundation.g24_qemu_tcg import classify_qemu_failure
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            serial=root/"serial"
            serial.write_text("VFS: Unable to mount root fs on unknown-block(0,0)\n")
            self.assertEqual(classify_qemu_failure(serial,root/"stderr"),
                             "root-filesystem-mount-error")
            serial.write_text("benign boot log\n")
            self.assertEqual(classify_qemu_failure(serial,root/"stderr"),
                             "none-classified")

    def test_real_marker_and_independent_cleanup_required(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            serial=root/"serial"
            nonce="c"*32
            proc=Mock()
            proc.poll.return_value=None
            seen=[]
            def run(argv,**kwargs):
                seen.append(kwargs)
                serial.write_bytes((PREFIX+" "+nonce+"\n").encode())
                return proc
            ok=observe_guest(("qemu","--fixed"),serial,nonce,
                             runner=run,stopper=lambda p:True,limit=1)
            self.assertEqual(ok,(True,True,"real-qemu-guest-userspace-marker"))
            self.assertEqual(set(seen[0]["env"]),{"PATH","HOME","LANG"})
            self.assertTrue(seen[0]["start_new_session"])
            serial.unlink()
            proc.poll.return_value=1
            denied=observe_guest(("qemu","--fixed"),serial,nonce,
                                 runner=lambda *a,**k:proc,
                                 stopper=lambda p:False,limit=1)
            self.assertFalse(denied[0])
            self.assertFalse(denied[1])
