"""The AI Daily Digest brand mark — one prism splitting one beam into many.

Single source of truth for the logo geometry. `make_icons.py` renders it into
the app icons and brand files; `cover.py` embeds it in the daily social cover.
"""

GRADIENT_DARK = (
    '<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">'
    '<stop offset="0" stop-color="#101d4d"/>'
    '<stop offset="0.55" stop-color="#2440b8"/>'
    '<stop offset="1" stop-color="#7c3aed"/>'
    '</linearGradient>'
)
GRADIENT_LIGHT = (
    '<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">'
    '<stop offset="0" stop-color="#ffffff"/>'
    '<stop offset="1" stop-color="#f2f4ff"/>'
    '</linearGradient>'
)

# The four refracted beams — one per audience the same story gets split across.
BEAMS = [
    ("M628 512 L888 404", "#38bdf8"),
    ("M640 566 L892 530", "#a78bfa"),
    ("M640 620 L892 656", "#fb7185"),
    ("M628 674 L888 782", "#fbbf24"),
]


def mark(ink: str) -> str:
    """The prism itself, drawn in `ink`, on a 1024×1024 canvas."""
    beams = "".join(
        f'<path d="{d}" stroke="{color}"/>' for d, color in BEAMS
    )
    return (
        f'<path d="M486 268 L742 712 L230 712 Z" fill="none" stroke="{ink}" '
        f'stroke-width="48" stroke-linejoin="round"/>'
        f'<rect x="130" y="470" width="248" height="44" rx="22" fill="{ink}"/>'
        f'<g stroke-linecap="round" stroke-width="44" fill="none">{beams}</g>'
    )


def logo_svg(theme: str = "dark", scale: float = 1.0) -> str:
    """Full-bleed logo. `scale` shrinks the mark for maskable icon safe zones."""
    if theme == "transparent":
        bg, defs, ink = "", "", "#ffffff"
    elif theme == "light":
        bg, defs, ink = '<rect width="1024" height="1024" fill="url(#bg)"/>', GRADIENT_LIGHT, "#101a3d"
    else:
        bg, defs, ink = '<rect width="1024" height="1024" fill="url(#bg)"/>', GRADIENT_DARK, "#ffffff"

    inner = mark(ink)
    if scale != 1.0:
        offset = 512 * (1 - scale)
        inner = f'<g transform="translate({offset:.1f},{offset:.1f}) scale({scale})">{inner}</g>'

    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024" '
        'width="1024" height="1024">'
        f'<defs>{defs}</defs>{bg}{inner}</svg>'
    )
