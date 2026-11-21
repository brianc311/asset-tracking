import re

MAC_ERROR = (
    "Enter a 12-digit MAC address (0-9 and A-F). "
    "Colons, dashes, and dots are allowed."
)
_SEPARATORS = re.compile(r"[:.\-\s]")
_NON_HEX = re.compile(r"[^0-9A-Fa-f]")


def normalize_mac(value: str) -> str:
    stripped = _SEPARATORS.sub("", value or "")
    hex_only = _NON_HEX.sub("", stripped)
    if len(hex_only) != 12:
        bad = "".join(ch for ch in stripped if _NON_HEX.match(ch))
        if bad:
            raise ValueError(f"{MAC_ERROR} Invalid character(s): {bad.upper()}.")
        raise ValueError(MAC_ERROR)
    hex_only = hex_only.upper()
    return ":".join(hex_only[i : i + 2] for i in range(0, 12, 2))
