import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from .constants import BASE32_ALPHABET
except ImportError:  # pragma: no cover - allows running as a script
    from app.constants import BASE32_ALPHABET

CHAR_TO_VAL = {ch: i for i, ch in enumerate(BASE32_ALPHABET)}

def decode_base32_custom(s: str) -> int:
    val = 0
    for ch in s.strip():
        try:
            digit = CHAR_TO_VAL[ch]
        except KeyError:
            raise ValueError(f"Invalid base32 character: {ch!r}")
        val = (val << 5) + digit   # same as val*32 + digit
    return val

def load_numbers(path: str | None = None):
    if path is None:
        path = Path(__file__).resolve().parent.parent / "numbers"
    else:
        path = Path(path)

    lines = path.read_text().splitlines()
    if len(lines) < 3:
        raise ValueError("numbers file must contain 3 lines: N, C, I")

    n_str, c_str, i_str = (x.strip() for x in lines[:3])

    N = decode_base32_custom(n_str)
    C = decode_base32_custom(c_str)
    I = decode_base32_custom(i_str)
    
    return N, C, I

N, C, I = load_numbers()



