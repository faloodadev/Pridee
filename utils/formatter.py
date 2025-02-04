import re
from datetime import timedelta
from typing import Sequence, Set, Union, Any
from boltons.iterutils import remap
from discord.utils import remove_markdown
from functools import lru_cache

CAPITAL_WORD = re.compile(r"([A-Z][a-z]+)")
CAPITAL_LETTERS = re.compile(r"([A-Z]+)")
VOWELS = set('aeiou')

class plural:
    def __init__(self, value: Union[str, int, list], md: str = ""):
        self.value = value
        self.markdown = md

    def __format__(self, format_spec: str) -> str:
        v = self._get_value()
        singular, _, plural = format_spec.partition("|")
        plural = plural or f"{singular}s"
        return f"{self.markdown}{v:,}{self.markdown} {plural if abs(v) != 1 else singular}"

    def _get_value(self) -> int:
        if isinstance(self.value, str):
            return int(self.value.split(" ", 1)[-1]) if self.value.startswith(("CREATE", "DELETE")) else int(self.value)
        elif isinstance(self.value, list):
            return len(self.value)
        return self.value

@lru_cache(maxsize=128)
def vowel(value: str) -> str:
    """Cached vowel checker for common words."""
    return f"{'an' if value[0].lower() in VOWELS else 'a'} {value}"

def duration(value: float, ms: bool = True) -> str:
    """Optimized duration formatter."""
    multiplier = 1000 if ms else 1
    h = int((value / (multiplier * 60 * 60)) % 24)
    m = int((value / (multiplier * 60)) % 60)
    s = int((value / multiplier) % 60)

    parts = []
    if h:
        parts.append(f"{h}:")
    parts.append(f"{str(m).zfill(2)}:")
    parts.append(f"{str(s).zfill(2)}")
    
    return "".join(parts)

def human_join(seq: Sequence[str], delim: str = ", ", final: str = "or") -> str:
    """Optimized human-readable join."""
    size = len(seq)
    if size <= 1:
        return seq[0] if size else ""
    if size == 2:
        return f"{seq[0]} {final} {seq[1]}"
    return f"{delim.join(seq[:-1])} {final} {seq[-1]}"

def codeblock(text: str, lang: str = "") -> str:
    return f"```{lang}\n{text}\n```"

@lru_cache(maxsize=256)
def shorten(value: str, length: int = 24) -> str:
    """Cached string shortener for common strings."""
    if len(value) > length:
        value = f"{value[:length-2]}..".strip()
    return remove_markdown(value.translate(str.maketrans("", "", "[]()")))

@lru_cache(maxsize=128)
def snake_cased(s: str) -> str:
    """Cached snake case converter for common strings."""
    return "_".join(
        CAPITAL_WORD.sub(r" \1", CAPITAL_LETTERS.sub(r" \1", s.replace("-", " "))).split()
    ).lower()

def snake_cased_dict(
    obj: dict,
    remove_nulls: bool = True,
    all_nulls: bool = False,
    discard_keys: Set[str] = set()
) -> dict:
    """Optimized dictionary key converter."""
    def _visit(p: Any, k: Any, v: Any) -> Union[tuple[str, Any], bool]:
        k = snake_cased(str(k))
        if k in discard_keys or (remove_nulls and ((not v and all_nulls) or v == "")):
            return False
        return (k, v)

    return remap(obj, visit=_visit)

def short_timespan(
    num_seconds: Union[float, timedelta],
    max_units: int = 3,
    delim: str = ""
) -> str:
    """Optimized timespan formatter."""
    if isinstance(num_seconds, timedelta):
        num_seconds = num_seconds.total_seconds()

    units = (
        ("y", 31536000),
        ("w", 604800),   
        ("d", 86400),     
        ("h", 3600),      
        ("m", 60),       
        ("s", 1),       
    )

    parts = []
    for unit, div in units:
        if num_seconds >= div:
            val = int(num_seconds // div)
            num_seconds %= div
            parts.append(f"{val}{unit}")
            if len(parts) == max_units:
                break

    return delim.join(parts) 