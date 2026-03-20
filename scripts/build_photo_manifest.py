from __future__ import annotations

import json
from html import escape
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
GALLERY_INTROS_DIR = ROOT / "_content" / "gallery-intros"
MANAGED_PAGES_PATH = ROOT / "_generated" / "managed-gallery-pages.txt"

COLLECTIONS = [
    {
        "key": "photo",
        "data_path": ROOT / "data" / "galleries.json",
        "manifest_path": ROOT / "_generated" / "photo-manifest.js",
        "cards_path": ROOT / "_generated" / "category-cards.qmd",
        "manifest_var": "photoCategories",
        "section_slug": "photography",
        "section_label": "Photography",
        "page_title_suffix": "Gallery",
        "gallery_aria_noun": "photo gallery",
        "item_noun": "photograph",
        "modal_alt": "Expanded selected photograph",
        "back_href": "photography.html",
        "back_label": "Back to Photography",
    },
    {
        "key": "drawing",
        "data_path": ROOT / "data" / "drawings.json",
        "manifest_path": ROOT / "_generated" / "drawing-manifest.js",
        "cards_path": ROOT / "_generated" / "drawing-category-cards.qmd",
        "manifest_var": "drawingCategories",
        "section_slug": "drawings",
        "section_label": "Drawings",
        "page_title_suffix": "Drawings",
        "gallery_aria_noun": "drawing gallery",
        "item_noun": "drawing",
        "modal_alt": "Expanded selected drawing",
        "back_href": "drawings.html",
        "back_label": "Back to Drawings",
    },
]


def load_galleries(data_path: Path) -> list[dict[str, object]]:
    if not data_path.exists():
        return []

    payload = json.loads(data_path.read_text(encoding="utf-8"))
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
    loaded_collections: list[tuple[dict[str, object], list[dict[str, object]]]] = []

    for collection in COLLECTIONS:
        galleries = load_galleries(collection["data_path"])
        loaded_collections.append((collection, galleries))
        payload = json.dumps(galleries, separators=(",", ":"))
        write_if_changed(
            collection["manifest_path"],
            f'window.{collection["manifest_var"]}={payload};\n',
        )
        write_if_changed(collection["cards_path"], build_category_cards(galleries))

    photo_categories = next(
        galleries for collection, galleries in loaded_collections if collection["key"] == "photo"
    )
    drawing_categories = next(
        galleries for collection, galleries in loaded_collections if collection["key"] == "drawing"
    )

    write_if_changed(SITE_HEADER_PATH, build_site_header(photo_categories, drawing_categories))
    write_category_gallery_pages(loaded_collections)


SITE_HEADER_PATH = ROOT / "_generated" / "site-header.html"


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


def build_site_header(
    photo_categories: list[dict[str, object]],
    drawing_categories: list[dict[str, object]],
) -> str:
    fragments = [
        '<header class="site-header">',
        '  <div class="site-header__inner">',
        '    <a class="site-header__home" href="index.html" aria-label="Back to home">',
        '      <img src="assets/images/site/logo.png" alt="" class="site-header__logo">',
        "    </a>",
        '    <nav class="site-header__nav" aria-label="Primary navigation">',
        '      <a class="site-header__link" href="index.html">Home</a>',
    ]

    fragments.extend(build_nav_menu("Photography", "photography.html", photo_categories))
    fragments.extend(build_nav_menu("Drawings", "drawings.html", drawing_categories))
    fragments.append('      <a class="site-header__link" href="about.html">About Me</a>')

    fragments.extend(
        [
            "    </nav>",
            "  </div>",
            "</header>",
        ]
    )

    return "\n".join(fragments) + "\n"


def build_nav_menu(title: str, href: str, categories: list[dict[str, object]]) -> list[str]:
    fragments = [
        '      <details class="site-menu">',
        f'        <summary class="site-menu__summary">{escape(title)}</summary>',
        '        <div class="site-menu__panel">',
        f'          <a class="site-menu__item site-menu__item--overview" href="{escape(href)}">{escape(title)} Home</a>',
    ]

    for category in categories:
        slug = escape(str(category["slug"]))
        label = escape(str(category["label"]))
        fragments.append(f'          <a class="site-menu__item" href="{slug}.html">{label}</a>')

    fragments.extend(
        [
            "        </div>",
            "      </details>",
        ]
    )
    return fragments


def write_category_gallery_pages(
    loaded_collections: list[tuple[dict[str, object], list[dict[str, object]]]]
) -> None:
    managed_pages: set[str] = set()

    for collection, categories in loaded_collections:
        for category in categories:
            slug = str(category["slug"])
            label = str(category["label"])
            page_path = ROOT / f"{slug}.qmd"
            write_if_changed(page_path, build_gallery_page(slug, label, collection))
            managed_pages.add(page_path.name)

    previous_pages = read_managed_pages()
    for stale_page in previous_pages - managed_pages:
        stale_path = ROOT / stale_page
        if stale_path.exists():
            stale_path.unlink()

    managed_listing = "".join(f"{name}\n" for name in sorted(managed_pages))
    write_if_changed(MANAGED_PAGES_PATH, managed_listing)


def read_managed_pages() -> set[str]:
    if not MANAGED_PAGES_PATH.exists():
        return set()
    return {
        line.strip()
        for line in MANAGED_PAGES_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }


def write_if_changed(path: Path, content: str) -> None:
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return
    path.write_text(content, encoding="utf-8")


def build_gallery_page(slug: str, label: str, collection: dict[str, object]) -> str:
    safe_label = label.replace('"', '\\"')
    gallery_intro = build_gallery_intro(slug, label, collection)
    manifest_filename = Path(str(collection["manifest_path"])).name
    manifest_var = str(collection["manifest_var"])
    gallery_aria_noun = str(collection["gallery_aria_noun"])
    modal_alt = str(collection["modal_alt"])
    back_href = str(collection["back_href"])
    back_label = str(collection["back_label"])
    page_title_suffix = str(collection["page_title_suffix"])
    item_noun = str(collection["item_noun"])

    return f"""---
title: "{safe_label} {page_title_suffix}"
page-layout: full
---

{gallery_intro}

::: {{.gallery-shell}}
<div id="photo-grid" class="photo-grid" aria-label="{safe_label} {gallery_aria_noun}"></div>
<p id="gallery-empty" class="gallery-empty" hidden>No images found for this category.</p>
<p class="gallery-backlink-wrap"><a class="gallery-toolbar__back" href="{back_href}">{back_label}</a></p>

<dialog id="gallery-modal" class="gallery-modal">
  <form method="dialog" class="gallery-modal__form">
<div class="gallery-modal__controls" aria-label="Image navigation"><button type="button" class="gallery-modal__nav" data-direction="prev" aria-label="Show previous image">&#8249;</button><button type="button" class="gallery-modal__nav" data-direction="next" aria-label="Show next image">&#8250;</button></div>
<button class="gallery-modal__close" aria-label="Close image viewer">Close</button>
  </form>
  <img id="modal-image" class="gallery-modal__image" alt="{modal_alt}">
  <div id="modal-copy" class="gallery-modal__copy" hidden><div id="modal-title" class="gallery-modal__title"></div><div id="modal-caption" class="gallery-modal__caption"></div></div>
</dialog>

<script src="_generated/{manifest_filename}"></script>

<script>
const categorySlug = "{slug}";
const categories = window.{manifest_var} ?? [];
const activeCategory = categories.find((category) => category.slug === categorySlug);
const photoGrid = document.getElementById("photo-grid");
const modal = document.getElementById("gallery-modal");
const modalImage = document.getElementById("modal-image");
const modalCopy = document.getElementById("modal-copy");
const modalTitle = document.getElementById("modal-title");
const modalCaption = document.getElementById("modal-caption");
const galleryEmpty = document.getElementById("gallery-empty");
const modalPrevButton = modal.querySelector('[data-direction="prev"]');
const modalNextButton = modal.querySelector('[data-direction="next"]');
let currentImageIndex = -1;

function updateModalNavigation(category) {{
  const imageCount = category?.images?.length ?? 0;
  const hasMultipleImages = imageCount > 1;
  modalPrevButton.disabled = !hasMultipleImages || currentImageIndex <= 0;
  modalNextButton.disabled = !hasMultipleImages || currentImageIndex >= imageCount - 1;
}}

function openPhoto(category, imageData) {{
  currentImageIndex = category.images.findIndex((entry) => entry.full === imageData.full);
  modalImage.src = imageData.full;
  modalImage.alt = imageData.title || `${{category.label}} {item_noun}`;
  modalTitle.textContent = imageData.title || "";
  modalCaption.textContent = imageData.caption || "";
  modalCaption.hidden = !imageData.caption;
  modalCopy.hidden = !imageData.title && !imageData.caption;
  updateModalNavigation(category);
  if (typeof modal.showModal === "function") {{
    modal.showModal();
  }}
}}

function showAdjacentPhoto(step) {{
  if (!activeCategory || currentImageIndex < 0) {{
    return;
  }}

  const nextIndex = currentImageIndex + step;
  const nextImage = activeCategory.images[nextIndex];
  if (!nextImage) {{
    return;
  }}

  openPhoto(activeCategory, nextImage);
}}

(activeCategory?.images ?? []).forEach((imageData) => {{
  const card = document.createElement("figure");
  card.className = "photo-card";

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
  card.append(button);

  const title = document.createElement("figcaption");
  title.className = "photo-card__title";
  title.textContent = imageData.caption || "";
  card.append(title);

  button.addEventListener("click", () => openPhoto(activeCategory, imageData));
  photoGrid.appendChild(card);
}});

if (!activeCategory || activeCategory.images.length === 0) {{
  galleryEmpty.hidden = false;
}}

modal.addEventListener("click", (event) => {{
  if (event.target === modal) {{
    modal.close();
  }}
}});

modalPrevButton.addEventListener("click", () => showAdjacentPhoto(-1));
modalNextButton.addEventListener("click", () => showAdjacentPhoto(1));

modal.addEventListener("close", () => {{
  currentImageIndex = -1;
}});
</script>
:::
"""


def build_gallery_intro(slug: str, label: str, collection: dict[str, object]) -> str:
    intro_path = GALLERY_INTROS_DIR / f"{slug}.md"
    if intro_path.exists():
        include_path = intro_path.relative_to(ROOT).as_posix()
        return f"{{{{< include {include_path} >}}}}"

    section_label = str(collection["section_label"])
    return (
        '<p class="gallery-description">'
        f"Click any image to load the larger version from the {escape(label)} {escape(section_label.lower())} collection."
        "</p>"
    )


if __name__ == "__main__":
    main()
