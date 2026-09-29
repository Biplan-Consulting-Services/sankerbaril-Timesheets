"""Keep the Shift Console's live database in step with the timesheet CSVs.

The console page (shift-console.html) holds no data. It reads its artifact's db:
    meta/config                          {projects:[...], epics:[...], syncedAt}
    months/<csv-stem>__<YYYY-MM>         {project, month, syncedAt, rows:[{project,id,date,start,end,status,workstream,epic}]}
One document per project-month keeps the store far below its 5,000-document cap and makes an ordinary day a
single-document write.

    python tools/sync_console.py plan      # diff CSVs against the last sync; writes _sync/batch-N.json for ArtifactData
    python tools/sync_console.py commit "months/x__2026-09=3,meta/config=2"   # record versions the batch returned

`plan` never talks to the network: Claude sends the batch files with the ArtifactData tool (action "batch",
each file's array as `writes`), then records the returned versions with `commit`. The cache
(_sync/state.json) holds, per document, the content hash last written and its version, so an unchanged
month is never rewritten and every update is pinned with if_version.
"""
import csv, datetime, hashlib, json, os, sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # Timesheets/
SYNC = os.path.join(HERE, "_sync")
STATE = os.path.join(SYNC, "state.json")
MAX_BYTES = 200_000   # db limit is 256 KiB per document; keep headroom
BATCH = 50


def read_csv(name):
    with open(os.path.join(HERE, name), encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def stem(file):
    return os.path.splitext(file)[0]


def build():
    now = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M")
    projects = []
    for i, p in enumerate(read_csv("_projects.csv")):
        projects.append({"file": p["file"], "client": p["client"], "project": p["project"],
                         "billable": p["billable"].strip().lower() == "true",
                         "colorLight": p["color_light"] or None, "colorDark": p["color_dark"] or None, "order": i})
    epics = [{"project": e["project"], "key": e["key"], "label": e["label"], "order": int(e["order"])}
             for e in read_csv("_epics.csv")] if os.path.exists(os.path.join(HERE, "_epics.csv")) else []
    docs = {"meta/config": {"projects": projects, "epics": epics}}
    for p in projects:
        path = os.path.join(HERE, p["file"])
        if not os.path.exists(path):
            continue
        for r in read_csv(p["file"]):
            if not (r.get("id") and r.get("date")):
                continue
            row = {"project": p["project"], "id": r["id"], "date": r["date"], "start": r.get("start", ""),
                   "end": r.get("end") or "", "status": r.get("status", ""), "workstream": r.get("workstream", ""),
                   "epic": (r.get("epic") or "").strip()}
            key = "months/%s__%s" % (stem(p["file"]), r["date"][:7])
            d = docs.setdefault(key, {"project": p["project"], "month": r["date"][:7], "rows": []})
            d["rows"].append(row)
    for k, d in docs.items():
        size = len(json.dumps(d, ensure_ascii=False).encode("utf-8"))
        assert size < MAX_BYTES, "%s is %d bytes, over the per-document budget" % (k, size)
    return docs, now


def digest(d):
    return hashlib.sha256(json.dumps(d, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def load_state():
    return json.load(open(STATE, encoding="utf-8")) if os.path.exists(STATE) else {}


def plan():
    docs, now = build()
    state = load_state()
    os.makedirs(SYNC, exist_ok=True)
    for f in os.listdir(SYNC):
        if f.startswith("batch-"):
            os.remove(os.path.join(SYNC, f))
    docdir = os.path.join(SYNC, "docs")
    os.makedirs(docdir, exist_ok=True)
    for f in os.listdir(docdir):
        os.remove(os.path.join(docdir, f))
    writes, pending = [], {}
    for k in sorted(docs):
        h = digest(docs[k])
        if state.get(k, {}).get("hash") == h:
            continue
        coll, doc_id = k.rsplit("/", 1)
        # the body goes in its own file: batch entries take `file_path`, so the batch itself stays small
        body = os.path.join(docdir, "%s__%s.json" % (coll, doc_id))
        json.dump(dict(docs[k], syncedAt=now), open(body, "w", encoding="utf-8"), ensure_ascii=False)
        w = {"op": "set", "collection": coll, "doc_id": doc_id, "file_path": body}
        if state.get(k, {}).get("version"):
            w["if_version"] = state[k]["version"]
        writes.append(w)
        pending[k] = h
    gone = sorted(k for k in state if k not in docs)          # a month emptied by moving rows: report, never auto-delete
    for n in range(0, len(writes), BATCH):
        json.dump(writes[n:n + BATCH], open(os.path.join(SYNC, "batch-%d.json" % (n // BATCH + 1)), "w", encoding="utf-8"),
                  ensure_ascii=False)
    json.dump(pending, open(os.path.join(SYNC, "pending.json"), "w", encoding="utf-8"), indent=1)
    rows = sum(len(d.get("rows", [])) for d in docs.values())
    print("%d documents (%d rows); %d to write in %d batch file(s)%s" % (
        len(docs), rows, len(writes), (len(writes) + BATCH - 1) // BATCH,
        "; in the db but no longer in the CSVs: " + ", ".join(gone) if gone else ""))
    for w in writes:
        print("  %s/%s%s" % (w["collection"], w["doc_id"], "  (v%d)" % w["if_version"] if "if_version" in w else "  (new)"))


def commit(spec):
    pending = json.load(open(os.path.join(SYNC, "pending.json"), encoding="utf-8"))
    state = load_state()
    got = dict(x.rsplit("=", 1) for x in spec.split(",") if x.strip())
    missing = sorted(set(pending) - set(got))
    assert not missing, "no version given for: " + ", ".join(missing)
    for k, v in got.items():
        assert k in pending, "%s was not in the pending batch" % k
        state[k] = {"hash": pending[k], "version": int(v)}
    json.dump(state, open(STATE, "w", encoding="utf-8"), indent=1, sort_keys=True)
    os.remove(os.path.join(SYNC, "pending.json"))
    print("recorded %d versions" % len(got))


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "plan":
        plan()
    elif len(sys.argv) == 3 and sys.argv[1] == "commit":
        commit(sys.argv[2])
    else:
        print(__doc__)
