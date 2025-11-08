from dataclasses import dataclass
from pathlib import Path
from typing import Dict

@dataclass(frozen=True)
class PromptDef:
    slug: str
    name: str
    content: str
    path: Path

def _parse_markdown(text: str, filename: str) -> tuple[str, str]:
    lines = [l.rstrip() for l in text.splitlines()]
    i = 0
    while i < len(lines) and not lines[i].strip():
        i += 1
    
    if i < len(lines) and lines[i].startswith("#"):
        name = lines[i].lstrip("#").strip()
        i += 1
        content = "\n".join(lines[i:]).lstrip("\n")
    else:
        name = filename.replace("_", " ").replace("-", " ").title()
        content = text.strip()
    
    return name, content

def load_prompts() -> Dict[str, PromptDef]:
    """Load prompts from the catalog directory."""
    catalog_dir = Path(__file__).parent / "catalog"
    out: Dict[str, PromptDef] = {}
    for p in sorted(catalog_dir.glob("*.md")):
        name, content = _parse_markdown(p.read_text(encoding="utf-8"), p.stem)
        slug = p.stem
        out[slug] = PromptDef(slug=slug, name=name, content=content, path=p)
    return out

