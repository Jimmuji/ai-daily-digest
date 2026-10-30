"""One-off helper: render the brand mark into logo files and app icons.

Not part of the daily pipeline. Run it whenever the mark in `brandmark.py`
changes:  python scripts/make_icons.py
"""

from pathlib import Path

from brandmark import logo_svg
from cover import render_html


def _svg_page(svg: str) -> str:
    return ("<style>html,body{margin:0;padding:0}svg{display:block}</style>"
            + svg)


def _render(svg: str, out: Path, size: int) -> None:
    if render_html(_svg_page(svg), out, width=size, height=size):
        print(f"  {out.name} ({size}px)")


def main() -> None:
    root = Path(__file__).parent.parent
    brand = root / "brand"
    icons = root / "docs" / "icons"
    brand.mkdir(exist_ok=True)

    # Editable sources
    for theme in ("dark", "light", "transparent"):
        name = "logo-mark" if theme == "dark" else f"logo-mark-{theme}"
        (brand / f"{name}.svg").write_text(logo_svg(theme), encoding="utf-8")
    print(f"SVG sources → {brand}")

    # Social avatars (upload these to 小红书 / 微信 / X)
    _render(logo_svg("dark"), brand / "avatar-1024.png", 1024)
    _render(logo_svg("light"), brand / "avatar-light-1024.png", 1024)

    # PWA / home-screen icons
    for size in (192, 512):
        _render(logo_svg("dark"), icons / f"icon-{size}.png", size)
        # Maskable: 80% safe zone so Android's circle crop keeps the prism.
        _render(logo_svg("dark", scale=0.8),
                icons / f"icon-maskable-{size}.png", size)
    _render(logo_svg("dark"), icons / "apple-touch-icon.png", 180)


if __name__ == "__main__":
    main()
