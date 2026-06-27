from typing import Dict
from slugify import slugify  # You may need to install python-slugify

# Keep track of the mapping from the original input to the slug we generated.
_input_to_slug: Dict[str, str] = {}
# Track which input claimed a slug so we can detect collisions.
_slug_owner: Dict[str, str] = {}
# Keep the next suffix to try per base slug when collisions occur.
_slug_suffix_counter: Dict[str, int] = {}


def _next_available_slug(base_slug: str, inp: str) -> str:
    """
    Return `base_slug` if unused or already tied to the same input,
    otherwise append an incrementing suffix until a free slug is found.
    """
    owner = _slug_owner.get(base_slug)
    if owner is None or owner == inp:
        return base_slug

    suffix = _slug_suffix_counter.get(base_slug, 2)
    while True:
        candidate = f"{base_slug}_{suffix}"
        candidate_owner = _slug_owner.get(candidate)
        if candidate_owner is None or candidate_owner == inp:
            _slug_suffix_counter[base_slug] = suffix + 1
            return candidate
        suffix += 1


def aimms_slug(inp: str) -> str:
    """
    Convert an AIMMS identifier or display name into a slugified form that is safe for file and path usage.

    Ensures that two different inputs never share the same slug within the same process: a deterministic
    numeric suffix is appended when a collision is detected.

    :param inp: Input string to transform into a unique slug.
    :type inp: str
    :return: Slugified version of the input using underscores as separators; suffixed when needed to avoid collisions.
    :rtype: str
    """
    if inp in _input_to_slug:
        return _input_to_slug[inp]

    base_slug = slugify(inp, separator="_")
    unique_slug = _next_available_slug(base_slug, inp)

    _input_to_slug[inp] = unique_slug
    _slug_owner[unique_slug] = inp

    return unique_slug
