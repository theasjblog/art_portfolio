from __future__ import annotations

import json
from pathlib import Path
from html import escape


ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "data" / "galleries.json"
GALLERY_INTROS_DIR = ROOT / "_content" / "gallery-intros"
MANIFEST_PATH = ROOT / "_generated" / "photo-manifest.js"
CATEGORY_CARDS_PATH = ROOT / "_generated" / "category-cards.qmd"
SITE_HEADER_PATH = ROOT / "_generated" / "site-header.html"
LEGACY_GALLERY_PAGE_GLOB = "gallery-*.qmd"


def load_galleries() -> list[dict[str, object]]:
    if not DATA_PATH.exists():
        return []

    payload = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    galleries = payload.get("galleries", [])

    normalized: list[dict[str, object]] = []
    for gallery in galleries:
        images = []
        for image in gallery.get("images", []):
            if not image.get("thumb") or not image.get("full"):
                continue
            images.append(
                {
                    "thumb": image["thumb"],
                    "full": image["full"],
                    "title": image.get("title", ""),
                    "caption": image.get("caption", ""),
                    "order": image.get("order"),
                }
            )

        if not gallery.get("slug") or not gallery.get("label") or not images:
            continue

        images.sort(key=image_sort_key)
        home_thumbnail = gallery.get("home_thumbnail") or images[0]["thumb"]
        normalized.append(
            {
                "slug": gallery["slug"],
                "label": gallery["label"],
                "order": gallery.get("order"),
                "home_thumbnail": home_thumbnail,
                "images": images,
            }
        )

    normalized.sort(key=gallery_sort_key)
    return normalized


def gallery_sort_key(gallery: dict[str, object]) -> tuple[float, str, str]:
    order = gallery.get("order")
    normalized_order = float(order) if isinstance(order, (int, float)) else float("inf")
    label = str(gallery.get("label", "")).lower()
    slug = str(gallery.get("slug", "")).lower()
    return (normalized_order, label, slug)


def image_sort_key(image: dict[str, object]) -> tuple[float, str, str, str]:
    order = image.get("order")
    normalized_order = float(order) if isinstance(order, (int, float)) else float("inf")
    title = str(image.get("title", "")).lower()
    thumb = str(image.get("thumb", "")).lower()
    full = str(image.get("full", "")).lower()
    return (normalized_order, title, thumb, full)


def main() -> None:
    galleries = load_galleries()
    payload = json.dumps(galleries, separators=(",", ":"))
    write_if_changed(MANIFEST_PATH, f"window.photoCategories={payload};\n")
    write_if_changed(CATEGORY_CARDS_PATH, build_category_cards(galleries))
    write_if_changed(SITE_HEADER_PATH, build_site_header(galleries))
    write_category_gallery_pages(galleries)


def build_category_cards(categories: list[dict[str, object]]) -> str:
    fragments: list[str] = ["```{=html}", '<div class="category-grid">']

    for category in categories:
        slug = str(category["slug"])
        label = escape(str(category["label"]))
        preview_src = escape(str(category["home_thumbnail"]))
        href = f"./{slug}.html"

        fragments.extend(
            [
                f'<a class="category-card" href="{escape(href)}" aria-label="Open {label} gallery">',
                f'<img src="{preview_src}" alt="{label} preview image" loading="lazy">',
                '<div class="category-card__body">',
                f'<div class="category-card__title">{label}</div>',
                "</div>",
                "</a>",
            ]
        )

    fragments.extend(["</div>", "```"])
    return "\n".join(fragments) + "\n"


def build_site_header(categories: list[dict[str, object]]) -> str:
    fragments = [
        '<header class="site-header">',
        '  <div class="site-header__inner">',
        '    <a class="site-header__home" href="index.html" aria-label="Back to home">',
        '      <img src="assets/images/site/logo.png" alt="" class="site-header__logo">',
        "    </a>",
        '    <nav class="site-header__nav" aria-label="Primary navigation">',
        '      <a class="site-header__link" href="about.html">About Me</a>',
        '    <details class="site-menu">',
        '      <summary class="site-menu__summary">Galleries</summary>',
        '      <div class="site-menu__panel">',
    ]

    for category in categories:
        slug = escape(str(category["slug"]))
        label = escape(str(category["label"]))
        fragments.append(
            f'        <a class="site-menu__item" href="{slug}.html">{label}</a>'
        )

    fragments.extend(
        [
            "      </div>",
            "    </details>",
            "    </nav>",
            "  </div>",
            "</header>",
        ]
    )

    return "\n".join(fragments) + "\n"


def write_category_gallery_pages(categories: list[dict[str, object]]) -> None:
    slugs = {str(category["slug"]) for category in categories}
    managed_files = {f"{slug}.qmd" for slug in slugs}
    static_pages = {"index.qmd", "about.qmd"}

    for existing_page in ROOT.glob(LEGACY_GALLERY_PAGE_GLOB):
        existing_page.unlink()

    for existing_page in ROOT.glob("*.qmd"):
        if existing_page.name not in static_pages and existing_page.name not in managed_files:
            existing_page.unlink()

    for category in categories:
        slug = str(category["slug"])
        label = str(category["label"])
        page_path = ROOT / f"{slug}.qmd"
        write_if_changed(page_path, build_gallery_page(slug, label))


def write_if_changed(path: Path, content: str) -> None:
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return
    path.write_text(content, encoding="utf-8")


def build_gallery_page(slug: str, label: str) -> str:
    safe_label = label.replace('"', '\\"')
    gallery_intro = build_gallery_intro(slug, label)

    return f"""---
title: "{safe_label} Gallery"
page-layout: full
---

{gallery_intro}

::: {{.gallery-shell}}
<div id="photo-grid" class="photo-grid" aria-label="{safe_label} photo gallery"></div>
<p id="gallery-empty" class="gallery-empty" hidden>No images found for this category.</p>
<p class="gallery-backlink-wrap"><a class="gallery-toolbar__back" href="index.html">Back to Home</a></p>

<dialog id="gallery-modal" class="gallery-modal">
  <form method="dialog" class="gallery-modal__form">
    <button class="gallery-modal__close" aria-label="Close image viewer">Close</button>
  </form>
  <img id="modal-image" class="gallery-modal__image" alt="Expanded selected photograph">
</dialog>

<script src="_generated/photo-manifest.js"></script>

<script>
const categorySlug = "{slug}";
const categories = window.photoCategories ?? [];
const activeCategory = categories.find((category) => category.slug === categorySlug);
const photoGrid = document.getElementById("photo-grid");
const modal = document.getElementById("gallery-modal");
const modalImage = document.getElementById("modal-image");
const galleryEmpty = document.getElementById("gallery-empty");

function openPhoto(category, imageData) {{
  modalImage.src = imageData.full;
  modalImage.alt = imageData.title || `${{category.label}} photograph`;
  if (typeof modal.showModal === "function") {{
    modal.showModal();
  }}
}}

(activeCategory?.images ?? []).forEach((imageData) => {{
  const button = document.createElement("button");
  button.type = "button";
  button.className = "photo-thumb";
  button.dataset.full = imageData.full;
  button.setAttribute("aria-label", imageData.title || "Open image in {safe_label}");

  const image = document.createElement("img");
  image.src = imageData.thumb;
  image.alt = imageData.title || `${{activeCategory.label}} thumbnail`;
  image.loading = "lazy";

  button.append(image);
  button.addEventListener("click", () => openPhoto(activeCategory, imageData));
  photoGrid.appendChild(button);
}});

if (!activeCategory || activeCategory.images.length === 0) {{
  galleryEmpty.hidden = false;
}}

modal.addEventListener("click", (event) => {{
  if (event.target === modal) {{
    modal.close();
  }}
}});
</script>
:::
"""


def build_gallery_intro(slug: str, label: str) -> str:
    intro_path = GALLERY_INTROS_DIR / f"{slug}.md"
    if intro_path.exists():
        include_path = intro_path.relative_to(ROOT).as_posix()
        return f"{{{{< include {include_path} >}}}}"
    return f'<p class="gallery-description">Click any image to load the larger version from {label}.</p>'


if __name__ == "__main__":
    main()
