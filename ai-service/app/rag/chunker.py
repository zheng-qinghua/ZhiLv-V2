"""把指南 .md 按二级/三级标题切块,产出带稳定 chunk_id 的记录。

chunk_id = md5(source|title|text):内容不变则 id 稳定,ingest 可重跑(幂等 upsert)。
city 由文件名推导:c_dali_guide 之类取关键词;匹配不上归 source 原名,不强求。
"""
from hashlib import md5
from pathlib import Path

from app.config import RAG_DATA_DIR

_CITY_MAP = {
    "dali": "大理",
    "chengdu": "成都",
    "xian": "西安",
}


def _city_of(source: str) -> str | None:
    s = source.lower()
    for key, name in _CITY_MAP.items():
        if key in s:
            return name
    return None


def split_guide(path: Path, source: str | None = None) -> list[dict]:
    """把一个 md 文件按标题切块,返回 [{chunk_id,source,city,title,chunk_index,text}]。"""
    source = source or path.stem
    city = _city_of(source)
    title = "文档开头"
    lines: list[str] = []
    out: list[dict] = []

    def flush(idx: int) -> None:
        text = "\n".join(lines).strip()
        lines.clear()
        if not text:
            return
        cid = md5(f"{source}|{title}|{text}".encode("utf-8")).hexdigest()
        out.append({
            "chunk_id": cid,
            "source": source,
            "city": city,
            "title": title,
            "chunk_index": idx,
            "text": text,
        })

    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("## ") or stripped.startswith("### "):
            flush(len(out))
            title = stripped.lstrip("#").strip()
        elif stripped:
            lines.append(stripped)
    flush(len(out))
    return out


def load_all_chunks(data_dir: Path | None = None) -> list[dict]:
    data_dir = data_dir or RAG_DATA_DIR
    records: list[dict] = []
    for md in sorted(data_dir.glob("*.md")):
        records.extend(split_guide(md))
    return records
