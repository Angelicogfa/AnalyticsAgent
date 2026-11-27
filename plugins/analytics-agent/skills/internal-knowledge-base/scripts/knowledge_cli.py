#!/usr/bin/env python3
"""CLI determinística da camada knowledge/ com índice local SQLite FTS5 (BM25).

Subcomandos:
  - index: indexa todas as notas .md de knowledge/<dominio>/ por seção Markdown e lista PDFs sem fichamento.
  - search: busca FTS5 com ranking BM25, filtro opcional por domínio e saída JSON enxuta em arquivo.
  - status: mostra contagem por domínio, entradas do catálogo e PDFs pendentes em inbox/domínios.
  - register: adiciona/atualiza uma entrada em knowledge/catalog.json.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sqlite3
import sys
from pathlib import Path

DOMAINS = ["data-science", "statistics", "data-engineering", "analytics-bi", "mlops-backend"]


def resolve_workspace(workspace_arg: str = "") -> Path:
    if workspace_arg:
        return Path(workspace_arg).expanduser().resolve()
    for env_key in ("ANALYTICS_AGENT_WORKSPACE", "CLAUDE_PROJECT_DIR"):
        raw = os.environ.get(env_key, "").strip()
        if raw:
            return Path(raw).expanduser().resolve()
    cwd = Path.cwd()
    if any((cwd / marker).exists() for marker in ("knowledge", "specs", "contracts", "ops", ".git")):
        return cwd
    return Path(__file__).resolve().parents[4]


def kb_root(root: Path) -> Path:
    return root / "knowledge"


def db_path(root: Path) -> Path:
    return kb_root(root) / ".index" / "knowledge.db"


def parse_frontmatter(text: str) -> dict[str, str]:
    meta: dict[str, str] = {}
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if not m:
        return meta
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip().strip('"').strip("'")
    return meta


def chunk_markdown_by_heading(text: str) -> list[tuple[str, int, str]]:
    """Divide Markdown por cabeçalhos (## / ###) preservando linha inicial para citação exata."""
    lines = text.splitlines()
    chunks: list[tuple[str, int, str]] = []
    cur_heading = "Overview"
    cur_start = 1
    buf: list[str] = []

    for idx, line in enumerate(lines, start=1):
        if re.match(r"^#{1,3}\s+", line):
            if buf:
                body = "\n".join(buf).strip()
                if body:
                    chunks.append((cur_heading, cur_start, body))
            cur_heading = line.lstrip("#").strip()
            cur_start = idx
            buf = [line]
        else:
            buf.append(line)

    if buf:
        body = "\n".join(buf).strip()
        if body:
            chunks.append((cur_heading, cur_start, body))
    return chunks


def find_pending_pdfs(root: Path) -> list[dict]:
    kb = kb_root(root)
    if not kb.exists():
        return []
    cat_path = kb / "catalog.json"
    registered_sources: set[str] = set()
    if cat_path.exists():
        cat = json.loads(cat_path.read_text(encoding="utf-8"))
        for entry in cat.get("entries", []):
            sf = entry.get("sourceFile") or ""
            if sf:
                registered_sources.add(sf.replace("\\", "/").lower())

    pending: list[dict] = []
    for pdf in sorted(kb.rglob("*.pdf")):
        rel = str(pdf.relative_to(root)).replace("\\", "/")
        if rel.lower() not in registered_sources:
            pending.append(
                {
                    "path": rel,
                    "location": "inbox" if "/inbox/" in f"/{rel.lower()}" else pdf.parent.name,
                    "sizeBytes": pdf.stat().st_size,
                }
            )
    return pending


def init_db(conn: sqlite3.Connection) -> None:
    conn.execute("DROP TABLE IF EXISTS chunks_fts")
    conn.execute(
        """
        CREATE VIRTUAL TABLE chunks_fts USING fts5(
            kb_id,
            title,
            domain,
            tags,
            file_path,
            heading,
            start_line UNINDEXED,
            content,
            tokenize='unicode61 remove_diacritics 2'
        )
        """
    )


def cmd_index(args: argparse.Namespace) -> int:
    root = resolve_workspace(args.workspace)
    kb = kb_root(root)
    index_db = db_path(root)
    index_db.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(index_db))
    init_db(conn)

    files_indexed = 0
    chunks_indexed = 0
    by_domain: dict[str, int] = {d: 0 for d in DOMAINS}

    for domain in DOMAINS:
        d_dir = kb / domain
        if not d_dir.exists():
            continue
        for md in sorted(d_dir.rglob("*.md")):
            text = md.read_text(encoding="utf-8", errors="ignore")
            meta = parse_frontmatter(text)
            kb_id = meta.get("kb_id") or md.stem
            title = meta.get("title") or md.stem
            tags = meta.get("tags") or ""
            rel_path = str(md.relative_to(root)).replace("\\", "/")

            chunks = chunk_markdown_by_heading(text)
            for heading, start_line, body in chunks:
                conn.execute(
                    """
                    INSERT INTO chunks_fts
                        (kb_id, title, domain, tags, file_path, heading, start_line, content)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (kb_id, title, domain, tags, rel_path, heading, start_line, body),
                )
                chunks_indexed += 1
            files_indexed += 1
            by_domain[domain] += 1

    conn.commit()
    conn.close()

    pending_pdfs = find_pending_pdfs(root)
    report = {
        "generatedAtUtc": dt.datetime.now(dt.UTC).isoformat(),
        "indexDb": str(index_db.relative_to(root)).replace("\\", "/"),
        "filesIndexed": files_indexed,
        "chunksIndexed": chunks_indexed,
        "filesByDomain": by_domain,
        "pendingPdfsForDistillation": pending_pdfs,
    }

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"Índice FTS5 atualizado: {files_indexed} nota(s), {chunks_indexed} seção(ões), "
        f"{len(pending_pdfs)} PDF(s) pendente(s). Relatório: {out}"
    )
    return 0


def build_fts_query(raw_query: str) -> str:
    tokens = re.findall(r"[A-Za-zÀ-ÿ0-9_-]{2,}", raw_query)
    if not tokens:
        return ""
    return " OR ".join(f'"{t}"' for t in tokens)


def cmd_search(args: argparse.Namespace) -> int:
    root = resolve_workspace(args.workspace)
    index_db = db_path(root)
    if not index_db.exists():
        print("Erro: índice FTS5 não existe ainda. Execute o subcomando 'index' primeiro.", file=sys.stderr)
        return 1

    fts_query = build_fts_query(args.query)
    if not fts_query:
        print("Erro: consulta vazia ou sem termos válidos.", file=sys.stderr)
        return 1

    conn = sqlite3.connect(str(index_db))
    sql = """
        SELECT kb_id, title, domain, tags, file_path, heading, start_line,
               snippet(chunks_fts, 7, '[', ']', '...', 32) AS snippet,
               bm25(chunks_fts) AS rank
        FROM chunks_fts
        WHERE chunks_fts MATCH ?
    """
    params: list = [fts_query]
    if args.domain:
        sql += " AND domain = ?"
        params.append(args.domain)
    sql += " ORDER BY rank LIMIT ?"
    params.append(args.limit)

    rows = conn.execute(sql, params).fetchall()
    conn.close()

    hits = [
        {
            "kbId": r[0],
            "title": r[1],
            "domain": r[2],
            "tags": r[3],
            "filePath": r[4],
            "heading": r[5],
            "startLine": r[6],
            "snippet": r[7],
            "bm25Score": round(float(r[8]), 4),
        }
        for r in rows
    ]

    result = {
        "query": args.query,
        "domainFilter": args.domain or "all",
        "hitCount": len(hits),
        "hits": hits,
    }
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Busca na base knowledge/ retornou {len(hits)} resultado(s). Saída: {out}")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    root = resolve_workspace(args.workspace)
    kb = kb_root(root)
    cat_path = kb / "catalog.json"
    entries = (
        json.loads(cat_path.read_text(encoding="utf-8")).get("entries", [])
        if cat_path.exists()
        else []
    )
    pending = find_pending_pdfs(root)
    report = {
        "generatedAtUtc": dt.datetime.now(dt.UTC).isoformat(),
        "indexExists": db_path(root).exists(),
        "catalogEntries": len(entries),
        "pendingPdfs": pending,
    }
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"Status knowledge/: {len(entries)} entrada(s) catalogada(s), "
        f"{len(pending)} PDF(s) pendente(s). Saída: {out}"
    )
    return 0


def cmd_register(args: argparse.Namespace) -> int:
    root = resolve_workspace(args.workspace)
    cat_path = kb_root(root) / "catalog.json"
    cat_path.parent.mkdir(parents=True, exist_ok=True)
    data = (
        json.loads(cat_path.read_text(encoding="utf-8"))
        if cat_path.exists()
        else {"version": "1.0.0", "entries": []}
    )

    entry = {
        "kbId": args.kb_id.upper(),
        "title": args.title,
        "domain": args.domain,
        "sourceType": args.source_type,
        "sourceFile": args.source_file.replace("\\", "/"),
        "noteFile": args.note_file.replace("\\", "/"),
        "tags": [t.strip() for t in args.tags.split(",") if t.strip()],
        "status": "ACTIVE",
        "promotedToSkill": None,
        "promotedToRule": None,
        "addedAt": dt.date.today().isoformat(),
    }

    entries = [e for e in data.get("entries", []) if e.get("kbId") != entry["kbId"]]
    entries.append(entry)
    data["entries"] = sorted(entries, key=lambda e: e.get("kbId", ""))
    cat_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"registered": entry["kbId"], "catalog": str(cat_path)}, ensure_ascii=False))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="CLI da base de conhecimento interna (knowledge/).")
    sub = parser.add_subparsers(dest="command", required=True)

    p_idx = sub.add_parser("index", help="Indexar notas .md no SQLite FTS5 e detectar PDFs pendentes")
    p_idx.add_argument("--workspace", default="", help="Raiz do workspace alvo")
    p_idx.add_argument("--output", required=True)
    p_idx.set_defaults(func=cmd_index)

    p_src = sub.add_parser("search", help="Buscar conhecimento via FTS5/BM25")
    p_src.add_argument("--query", required=True)
    p_src.add_argument("--domain", choices=DOMAINS, default="")
    p_src.add_argument("--limit", type=int, required=True)
    p_src.add_argument("--workspace", default="", help="Raiz do workspace alvo")
    p_src.add_argument("--output", required=True)
    p_src.set_defaults(func=cmd_search)

    p_st = sub.add_parser("status", help="Consultar status do catálogo e PDFs pendentes")
    p_st.add_argument("--workspace", default="", help="Raiz do workspace alvo")
    p_st.add_argument("--output", required=True)
    p_st.set_defaults(func=cmd_status)

    p_reg = sub.add_parser("register", help="Registrar nota destilada em knowledge/catalog.json")
    p_reg.add_argument("--kb-id", required=True)
    p_reg.add_argument("--title", required=True)
    p_reg.add_argument("--domain", choices=DOMAINS, required=True)
    p_reg.add_argument("--source-type", default="pdf")
    p_reg.add_argument("--source-file", required=True)
    p_reg.add_argument("--note-file", required=True)
    p_reg.add_argument("--tags", default="")
    p_reg.add_argument("--workspace", default="", help="Raiz do workspace alvo")
    p_reg.set_defaults(func=cmd_register)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
