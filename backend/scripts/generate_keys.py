"""Generate an RS256 keypair for JWT signing (NFR-04).

Usage:
    python -m scripts.generate_keys [--out-dir keys]

In production, store the private key in a secrets manager (§3.7) rather than on
disk, and provide it via the JWT_PRIVATE_KEY / JWT_PUBLIC_KEY environment vars.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate an RS256 JWT keypair.")
    parser.add_argument("--out-dir", default="keys", help="Directory to write the PEM files to.")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    (out_dir / "jwt_private.pem").write_bytes(
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    (out_dir / "jwt_public.pem").write_bytes(
        key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    print(f"Wrote jwt_private.pem and jwt_public.pem to {out_dir.resolve()}")


if __name__ == "__main__":
    main()
