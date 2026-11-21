import re

MAC_ERROR = (
    "Enter a 12-character MAC or hardware ID (0-9 and A-Z). "
    "Colons, dashes, and dots are allowed."
)
_SEPARATORS = re.compile(r"[:.\-\s]")
_NON_ID = re.compile(r"[^0-9A-Za-z]")


def normalize_mac(value: str) -> str:
    stripped = _SEPARATORS.sub("", value or "")
    id_only = _NON_ID.sub("", stripped)
    if len(id_only) != 12:
        bad = "".join(ch for ch in stripped if _NON_ID.match(ch))
        if bad:
            raise ValueError(f"{MAC_ERROR} Invalid character(s): {bad.upper()}.")
        raise ValueError(MAC_ERROR)
    id_only = id_only.upper()
    return ":".join(id_only[i : i + 2] for i in range(0, 12, 2))
