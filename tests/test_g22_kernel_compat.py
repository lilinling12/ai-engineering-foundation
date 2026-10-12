import hashlib
from pathlib import Path
import tempfile
import unittest

from foundation.g22_kernel_compat import (
    GUEST_REQUIRED, KernelPreflightDenied, inspect_kernel_config,
)


def sha(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def files(root: Path, overrides=None, *, machine=62, config_extra=""):
    header = bytearray(256)
    header[:4] = b"\x7fELF"
    header[4] = 2
    header[5] = 1
    header[18:20] = machine.to_bytes(2,"little")
    kernel = root/"vmlinux"
    kernel.write_bytes(header)
    kernel.chmod(0o600)
    fields = {key:"y" for key in GUEST_REQUIRED}
    if overrides:
        fields.update(overrides)
    config = root/".config"
    config.write_text("".join(k+"="+v+"\n" for k,v in sorted(fields.items())) + config_extra)
    config.chmod(0o600)
    return kernel,sha(bytes(header)),config,sha(config.read_bytes())


class GuestKernelCompatibilityTests(unittest.TestCase):
    def test_accept_exact_x86_64_elf_and_claimed_builtin_config(self):
        with tempfile.TemporaryDirectory() as temp:
            result = inspect_kernel_config(*files(Path(temp)))
            self.assertFalse(result.kernel_booted)
            self.assertFalse(result.config_is_kernel_authenticated)
            self.assertEqual(result.requirements,tuple(sorted(GUEST_REQUIRED)))

    def test_reject_missing_or_module_only_boot_drivers(self):
        for disabled in ("CONFIG_EXT4_FS","CONFIG_VIRTIO_BLK",
                         "CONFIG_KVM_GUEST","CONFIG_SERIAL_8250_CONSOLE",
                         "CONFIG_ACPI","CONFIG_PCI","CONFIG_BINFMT_ELF"):
            for value in ("n","m"):
                with self.subTest(flag=disabled,value=value), tempfile.TemporaryDirectory() as temp:
                    args = files(Path(temp), {disabled:value})
                    with self.assertRaises(KernelPreflightDenied):
                        inspect_kernel_config(*args)

    def test_reject_wrong_machine_arch_and_modified_digests(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            args=files(root,machine=183)
            with self.assertRaises(KernelPreflightDenied):
                inspect_kernel_config(*args)
            args=files(root)
            with self.assertRaises(KernelPreflightDenied):
                inspect_kernel_config(args[0],"0"*64,args[2],args[3])
            with self.assertRaises(KernelPreflightDenied):
                inspect_kernel_config(args[0],args[1],args[2],"f"*64)

    def test_reject_duplicate_keys_untrusted_permissions_and_symlinks(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            args=files(root,config_extra="CONFIG_EXT4_FS=y\n")
            with self.assertRaises(KernelPreflightDenied):
                inspect_kernel_config(*args)
            args=files(root)
            args[2].chmod(0o666)
            with self.assertRaises(KernelPreflightDenied):
                inspect_kernel_config(*args)
            args[2].chmod(0o600)
            shortcut=root/"linked"
            shortcut.symlink_to(args[2])
            with self.assertRaises(KernelPreflightDenied):
                inspect_kernel_config(args[0],args[1],shortcut,args[3])
