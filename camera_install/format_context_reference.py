"""Observed constructor branch, not a PF format validator or converter."""


def constructor_selection(version: int) -> tuple[str, int]:
    """Empty-reference creation branch at ae00, not file opening."""
    if type(version) is not int or not 0 <= version <= 0xffff:
        raise ValueError('Require the observed unsigned 16-bit version field')
    if version & 0xff00 == 0x3000:
        return 'pf3FormatContext', version
    return 'baseFormatContext', 0x2001


def file_constructor_selection(version: int) -> tuple[str, int] | None:
    """File-open branch afbc; None means outside the three mapped branches."""
    if type(version) is not int or not 0 <= version <= 0xffff:
        raise ValueError('Require the observed unsigned 16-bit version field')
    family = version & 0xff00
    if family == 0x2000:
        return 'baseFormatContext', version
    if family in (0x3000, 0x4000):
        return 'pf3FormatContext', version
    return None
