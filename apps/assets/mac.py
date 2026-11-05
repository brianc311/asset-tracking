import re

MAC_ERROR = "Enter a 12-digit MAC address."
_HEX = re.compile(r"[^0-9A-Fa-f]")


def normalize_mac(value: str) -> str:
    hex_only = _HEX.sub("", value or "")
    if len(hex_only) != 12:
        raise ValueError(MAC_ERROR)
    hex_only = hex_only.upper()
    return ":".join(hex_only[i : i + 2] for i in range(0, 12, 2))
