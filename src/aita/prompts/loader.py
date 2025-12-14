from dataclasses import dataclass
from pathlib import Path
from typing import Dict


@dataclass(frozen=True)
class PromptDef:
    slug: str
    name: str
    content: str
    path: Path


def load_prompts() -> Dict[str, PromptDef]:
    """Load prompts from the catalog directory and its subdirectories."""
    catalog_dir = Path(__file__).parent / "catalog"
    out: Dict[str, PromptDef] = {}
    for p in sorted(catalog_dir.rglob("*.md")):
        slug = p.stem
        name = slug.replace("_", " ").replace("-", " ").title()
        content = p.read_text(encoding="utf-8")
        out[slug] = PromptDef(slug=slug, name=name, content=content, path=p)
    return out
