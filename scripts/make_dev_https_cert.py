"""Create a locally trusted HTTPS cert for run_dev_https.bat.

Werkzeug --cert-file adhoc is self-signed and usually omits the LAN IP, so Chrome
shows "Not secure" even on https://192.168.x.x:8444. This writes a small local CA
plus a server cert with localhost and current LAN IPs, then tries to trust the CA
in the Windows Current User Root store so the padlock can appear on this PC.
"""

from __future__ import annotations

import ipaddress
import socket
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

ROOT = Path(__file__).resolve().parent.parent
CERT_DIR = ROOT / ".certs"
CA_CERT = CERT_DIR / "dev-ca.pem"
CA_KEY = CERT_DIR / "dev-ca-key.pem"
SERVER_CERT = CERT_DIR / "dev.pem"
SERVER_KEY = CERT_DIR / "dev-key.pem"
CA_NAME = "Asset Tracking Dev CA"


def lan_ipv4_addresses() -> list[str]:
    hosts: set[str] = set()
    try:
        hostname = socket.gethostname()
        hosts.update(
            info[4][0]
            for info in socket.getaddrinfo(hostname, None, socket.AF_INET)
            if info[4][0] and not info[4][0].startswith("127.")
        )
    except OSError:
        pass
    try:
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        probe.connect(("8.8.8.8", 80))
        hosts.add(probe.getsockname()[0])
        probe.close()
    except OSError:
        pass
    return sorted(ip for ip in hosts if not ip.startswith("169."))


def _load_or_create_ca() -> tuple[x509.Certificate, rsa.RSAPrivateKey]:
    if CA_CERT.exists() and CA_KEY.exists():
        cert = x509.load_pem_x509_certificate(CA_CERT.read_bytes())
        key = serialization.load_pem_private_key(CA_KEY.read_bytes(), password=None)
        if cert.not_valid_after_utc > datetime.now(timezone.utc) + timedelta(days=30):
            return cert, key  # type: ignore[return-value]

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, CA_NAME)])
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(timezone.utc) - timedelta(minutes=5))
        .not_valid_after(datetime.now(timezone.utc) + timedelta(days=3650))
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=False,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=True,
                crl_sign=True,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .sign(key, hashes.SHA256())
    )
    CERT_DIR.mkdir(exist_ok=True)
    CA_KEY.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.TraditionalOpenSSL,
            serialization.NoEncryption(),
        )
    )
    CA_CERT.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    return cert, key


def _san_names() -> list[x509.GeneralName]:
    names: list[x509.GeneralName] = [
        x509.DNSName("localhost"),
        x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
    ]
    for ip in lan_ipv4_addresses():
        names.append(x509.IPAddress(ipaddress.ip_address(ip)))
    try:
        hostname = socket.gethostname().split(".")[0]
        if hostname and hostname.lower() != "localhost":
            names.append(x509.DNSName(hostname))
    except OSError:
        pass
    return names


def _server_sans_match(cert: x509.Certificate, wanted: list[x509.GeneralName]) -> bool:
    try:
        san = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
    except x509.ExtensionNotFound:
        return False
    have = set(str(n) for n in san)
    need = set(str(n) for n in wanted)
    return need <= have


def _load_or_create_server(
    ca_cert: x509.Certificate, ca_key: rsa.RSAPrivateKey
) -> None:
    wanted = _san_names()
    if SERVER_CERT.exists() and SERVER_KEY.exists():
        cert = x509.load_pem_x509_certificate(SERVER_CERT.read_bytes())
        if (
            cert.not_valid_after_utc > datetime.now(timezone.utc) + timedelta(days=7)
            and _server_sans_match(cert, wanted)
        ):
            return

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Asset Tracking Dev")])
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(ca_cert.subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(timezone.utc) - timedelta(minutes=5))
        .not_valid_after(datetime.now(timezone.utc) + timedelta(days=825))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(x509.SubjectAlternativeName(wanted), critical=False)
        .add_extension(
            x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]),
            critical=False,
        )
        .sign(ca_key, hashes.SHA256())
    )
    CERT_DIR.mkdir(exist_ok=True)
    SERVER_KEY.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.TraditionalOpenSSL,
            serialization.NoEncryption(),
        )
    )
    SERVER_CERT.write_bytes(cert.public_bytes(serialization.Encoding.PEM))


def trust_ca_on_windows() -> bool:
    if sys.platform != "win32":
        return False
    try:
        result = subprocess.run(
            ["certutil", "-user", "-addstore", "Root", str(CA_CERT)],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return False
    output = (result.stdout or "") + (result.stderr or "")
    if result.returncode == 0:
        print("Trusted the local CA in this Windows user account.")
        return True
    if "already" in output.lower() or "exist" in output.lower():
        print("Local CA is already trusted on this Windows user account.")
        return True
    print(output.strip() or "certutil could not trust the CA automatically.")
    print(f'  Trust it by hand: certutil -user -addstore Root "{CA_CERT}"')
    return False


def main() -> int:
    ca_cert, ca_key = _load_or_create_ca()
    _load_or_create_server(ca_cert, ca_key)
    trust_ca_on_windows()
    print()
    print("HTTPS certificate is ready (includes localhost and this PC's LAN IP).")
    print(f"  cert: {SERVER_CERT}")
    print(f"  key:  {SERVER_KEY}")
    for ip in lan_ipv4_addresses():
        print(f"  phone: https://{ip}:8444/")
    print()
    print("If Chrome still says Not secure, close every Chrome window and reopen.")
    print("A phone still shows Not secure until you install .certs/dev-ca.pem on it.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
