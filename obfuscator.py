#!/usr/bin/env python3
"""
Universal Python Repository Obfuscator (Option C: Centralized Native Engine)
----------------------------------------------------------------------------
Features:
  - Centralized Runtime (`pyshield_runtime/`): NO keys are stored in application files!
  - Native C-API Execution: Calls CPython's PyEval_EvalCode directly via ctypes.
  - Bypass Proof: builtins.exec is never used.
  - Dual Anti-Debugging: Detects sys.gettrace() and OS-level debuggers.
  - Cross-Platform: Works on Windows, Linux, macOS, Docker & Kubernetes with zero compilers.
  - Structure Preservation: Preserves directory hierarchy, file names, and non-code assets.
"""

import os
import sys
import shutil
import argparse
import hashlib
import hmac
import base64

IGNORE_DIRS = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    "venv",
    ".venv",
    ".idea",
    ".vscode",
    "dist",
    ".mypy_cache",
    ".tox",
    "pyshield_runtime",
}

# Template for all protected files in the repository.
# Notice: Absolutely NO secret key exists here!
APPLICATION_FILE_TEMPLATE = '''# Protected by PyShield Native Runtime
import pyshield_runtime as __psr__

__CIPHERTEXT__ = {ciphertext_b64!r}
__SIGNATURE__ = {signature_b64!r}

__psr__.run_secure(__CIPHERTEXT__, __SIGNATURE__, globals(), locals(), __file__)
'''

# The Central Runtime Engine placed into `pyshield_runtime/__init__.py`
RUNTIME_ENGINE_TEMPLATE = '''# PyShield Central Native Runtime Engine
# Handles dynamic key reconstruction, tamper verification, and native C-API execution.
import sys
import os
import base64
import hashlib
import hmac
import ctypes

# 1. Anti-Debugging Protections
if sys.gettrace() is not None:
    sys.exit("[!] Security Violation: Trace or Debugger detected.")

if sys.platform == "win32":
    try:
        if ctypes.windll.kernel32.IsDebuggerPresent():
            sys.exit("[!] Security Violation: Native debugger attached.")
    except Exception:
        pass

# 2. Vault Key Reconstruction
__MASK__ = {mask!r}
__VAULT_PAYLOAD__ = {vault_payload!r}

def _get_key():
    ks = bytearray()
    c = 0
    while len(ks) < len(__VAULT_PAYLOAD__):
        ks.extend(hashlib.sha256(__MASK__ + c.to_bytes(4, "big")).digest())
        c += 1
    return bytes(a ^ b for a, b in zip(__VAULT_PAYLOAD__, ks[:len(__VAULT_PAYLOAD__)]))

def _derive_stream(key, length):
    ks = bytearray()
    c = 0
    while len(ks) < length:
        ks.extend(hashlib.sha256(key + c.to_bytes(4, "big")).digest())
        c += 1
    return bytes(ks[:length])

# 3. Configure Native C-API Evaluation
_native_eval = ctypes.pythonapi.PyEval_EvalCode
_native_eval.restype = ctypes.py_object
_native_eval.argtypes = [ctypes.py_object, ctypes.py_object, ctypes.py_object]

def run_secure(ciphertext_b64, signature_b64, caller_globals, caller_locals, file_path="<protected>"):
    """Validates, decrypts in RAM, and executes code directly via CPython C-API."""
    key = _get_key()
    ciphertext = base64.b64decode(ciphertext_b64)
    expected_sig = base64.b64decode(signature_b64)

    # HMAC Tamper Check
    calculated_sig = hmac.new(key, ciphertext, hashlib.sha256).digest()
    if not hmac.compare_digest(calculated_sig, expected_sig):
        sys.exit("[!] Security Error: Code payload has been tampered with or corrupted.")

    # In-Memory Decryption
    keystream = _derive_stream(key, len(ciphertext))
    decrypted_code_str = bytes(c ^ k for c, k in zip(ciphertext, keystream)).decode("utf-8")

    # In-Memory Compilation to Code Object
    code_obj = compile(decrypted_code_str, file_path, "exec")

    # Wipe sensitive variables from RAM immediately
    del key, ciphertext, expected_sig, calculated_sig, keystream, decrypted_code_str

    # Execute directly in C-API (Bypasses builtins.exec!)
    _native_eval(code_obj, caller_globals, caller_locals)
'''


def _generate_keystream(key: bytes, length: int) -> bytes:
    keystream = bytearray()
    counter = 0
    while len(keystream) < length:
        block = hashlib.sha256(key + counter.to_bytes(4, "big")).digest()
        keystream.extend(block)
        counter += 1
    return bytes(keystream[:length])


def _encrypt(data: bytes, key: bytes) -> bytes:
    keystream = _generate_keystream(key, len(data))
    return bytes(p ^ k for p, k in zip(data, keystream))


def create_vault_payload(master_key: bytes) -> tuple[bytes, bytes]:
    """Scrambles master_key with a random mask to hide it in the runtime engine."""
    mask = os.urandom(32)
    keystream = _generate_keystream(mask, len(master_key))
    vault_payload = bytes(a ^ b for a, b in zip(master_key, keystream))
    return mask, vault_payload


def generate_runtime_package(dest_dir: str, master_key: bytes):
    """Generates the central pyshield_runtime package inside the destination."""
    runtime_dir = os.path.join(dest_dir, "pyshield_runtime")
    os.makedirs(runtime_dir, exist_ok=True)

    mask, vault_payload = create_vault_payload(master_key)

    runtime_init = os.path.join(runtime_dir, "__init__.py")
    with open(runtime_init, "w", encoding="utf-8") as f:
        f.write(RUNTIME_ENGINE_TEMPLATE.format(
            mask=mask,
            vault_payload=vault_payload
        ))


def obfuscate_single_file_content(source_code: str, master_key: bytes) -> str:
    """Encrypts source code and returns the application file content (without key)."""
    source_bytes = source_code.encode("utf-8")
    ciphertext = _encrypt(source_bytes, master_key)
    signature = hmac.new(master_key, ciphertext, hashlib.sha256).digest()

    ciphertext_b64 = base64.b64encode(ciphertext).decode("ascii")
    signature_b64 = base64.b64encode(signature).decode("ascii")

    return APPLICATION_FILE_TEMPLATE.format(
        ciphertext_b64=ciphertext_b64,
        signature_b64=signature_b64
    )


def obfuscate_directory(src_dir: str, dest_dir: str):
    """Obfuscates an entire repository using the central native runtime engine."""
    src_dir = os.path.abspath(src_dir)
    dest_dir = os.path.abspath(dest_dir)

    print(f"[*] Starting Repository Obfuscation (Option C: Central Native Engine):")
    print(f"    Source:      {src_dir}")
    print(f"    Destination: {dest_dir}\n")

    # Generate a single Master Vault Key for this entire project build
    master_key = os.urandom(32)

    # 1. Create the central pyshield_runtime package
    generate_runtime_package(dest_dir, master_key)
    print("  [+] Generated:   pyshield_runtime/ (Central Native Engine & Keystore)")

    py_count = 0
    asset_count = 0

    for root, dirs, files in os.walk(src_dir):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]

        rel_path = os.path.relpath(root, src_dir)
        target_dir = dest_dir if rel_path == "." else os.path.join(dest_dir, rel_path)

        for filename in files:
            src_file = os.path.join(root, filename)
            dest_file = os.path.join(target_dir, filename)

            if os.path.abspath(src_file) == os.path.abspath(__file__):
                continue

            if filename.endswith(".py"):
                with open(src_file, "r", encoding="utf-8") as f:
                    content = f.read()

                protected_code = obfuscate_single_file_content(content, master_key)
                os.makedirs(os.path.dirname(dest_file), exist_ok=True)
                with open(dest_file, "w", encoding="utf-8") as f:
                    f.write(protected_code)

                display_path = os.path.relpath(dest_file, dest_dir)
                print(f"  [+] Obfuscated:  {display_path} (No key in file)")
                py_count += 1
            else:
                os.makedirs(target_dir, exist_ok=True)
                shutil.copy2(src_file, dest_file)
                display_path = os.path.relpath(dest_file, dest_dir)
                print(f"  [->] Copied asset: {display_path}")
                asset_count += 1

    print(f"\n[+] Repository Obfuscation Complete!")
    print(f"    - Obfuscated Python files: {py_count}")
    print(f"    - Copied asset files:       {asset_count}")
    print(f"    - Output directory:         {dest_dir}")


def main():
    parser = argparse.ArgumentParser(
        description="Universal Python Repository Obfuscator (Option C: Central Native Engine)."
    )
    parser.add_argument("input", help="Path to Python file or repository folder to obfuscate")
    parser.add_argument("-o", "--output", default="dist", help="Output directory (default: dist/)")

    args = parser.parse_args()
    input_path = os.path.abspath(args.input)
    output_dir = os.path.abspath(args.output)

    if not os.path.exists(input_path):
        sys.exit(f"[!] Error: Input path does not exist: {input_path}")

    if os.path.isdir(input_path):
        obfuscate_directory(input_path, output_dir)
    else:
        # For a single file, create runtime package inside output_dir and obfuscate the file
        master_key = os.urandom(32)
        generate_runtime_package(output_dir, master_key)

        with open(input_path, "r", encoding="utf-8") as f:
            content = f.read()

        protected_code = obfuscate_single_file_content(content, master_key)
        filename = os.path.basename(input_path)
        dest_file = os.path.join(output_dir, filename)

        with open(dest_file, "w", encoding="utf-8") as f:
            f.write(protected_code)

        print(f"[*] Obfuscated single file: {dest_file}")
        print(f"[+] Central runtime created at: {os.path.join(output_dir, 'pyshield_runtime')}")


if __name__ == "__main__":
    main()
