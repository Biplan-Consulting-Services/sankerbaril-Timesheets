// Push a reviewed plan (jira/plans/<date>.json) to Jira AFDS as worklogs, from inside a
// biplan-consulting.atlassian.net tab (the page's own sign-in; no token).
//
// DRY RUN BY DEFAULT. It only writes when window.JIRA_APPLY === true, and that is set only
// after the user has read the plan's .md report and said OK in chat.
//
// Before running: window.JIRA_PLAN = <the "entries" array of the plan json>.
// Optional window.JIRA_LIMIT = n pushes only the first n entries still missing (a first
// one-entry run proves the format before the rest).
//
// The client reads these worklogs in its reports, so the comment is only the work
// description. The "[WS-xxx stem]" / "[FILL-xxx jira-fill]" marker that stops a double push
// lives in a hidden worklog property (key biplan.timesheet), not in the comment. Worklogs
// pushed before 2026-10-04 carried it in the comment instead; both are read.
// For each entry it first re-reads that issue's worklogs and skips the entry if its marker is
// already there (so a re-run or a half-finished run never duplicates), then POSTs the
// worklog and reads it back. Returns a compact summary; the detail stays in window.__jiraPush.
(async () => {
  const PLAN = window.JIRA_PLAN || [];
  const APPLY = window.JIRA_APPLY === true;
  const LIMIT = window.JIRA_LIMIT || Infinity;
  const PROP = "biplan.timesheet";
  const MARK = /\[(?:WS|FILL)-\d+ [a-z0-9_.-]+\]/g;
  const H = { Accept: "application/json", "Content-Type": "application/json" };
  const get = async (u) => { const r = await fetch(u, { headers: H }); if (!r.ok) throw new Error(r.status + " " + u); return r.json(); };
  const flat = (adf) => { const o = []; (function w(n) { if (!n) return; if (n.text) o.push(n.text); (n.content || []).forEach(w); })(adf); return o.join(" "); };
  const markerOf = (w) => ((w.properties || []).find(p => p.key === PROP) || {}).value;
  const me = await get("/rest/api/3/myself");
  const seen = {};   // issue key -> set of markers already on it (mine only)
  const markersOn = async (key) => {
    if (seen[key]) return seen[key];
    const s = new Set();
    let at = 0, total = 1;
    while (at < total) {
      const j = await get(`/rest/api/3/issue/${key}/worklog?startAt=${at}&maxResults=100&expand=properties`);
      total = j.total; const page = j.worklogs || []; at += page.length; if (!page.length) break;
      page.filter(w => w.author && w.author.accountId === me.accountId).forEach(w => {
        const p = markerOf(w); if (p && p.marker) s.add(p.marker);
        (flat(w.comment).match(MARK) || []).forEach(m => s.add(m));
      });
    }
    return (seen[key] = s);
  };
  const res = [];
  let pushed = 0;
  for (const e of PLAN) {
    if (!/^AFDS-\d+$/.test(e.ticket) || !e.marker || !(e.timeSpentSeconds > 0)) { res.push({ m: e.marker, r: "bad entry" }); continue; }
    if ((await markersOn(e.ticket)).has(e.marker)) { res.push({ m: e.marker, r: "already there" }); continue; }
    if (!APPLY) { res.push({ m: e.marker, r: "would push", t: e.ticket, h: e.timeSpentSeconds / 3600 }); continue; }
    if (pushed >= LIMIT) { res.push({ m: e.marker, r: "held (limit)" }); continue; }
    const body = { started: e.started, timeSpentSeconds: e.timeSpentSeconds,
      comment: { type: "doc", version: 1, content: [{ type: "paragraph", content: [{ type: "text", text: e.comment }] }] },
      properties: [{ key: PROP, value: { marker: e.marker } }] };
    const r = await fetch(`/rest/api/3/issue/${e.ticket}/worklog?notifyUsers=false&adjustEstimate=leave`,
      { method: "POST", headers: H, body: JSON.stringify(body) });
    if (!r.ok) { res.push({ m: e.marker, r: "FAILED " + r.status + " " + (await r.text()).slice(0, 120) }); continue; }
    pushed++;
    const w = await r.json();
    const back = await get(`/rest/api/3/issue/${e.ticket}/worklog/${w.id}?expand=properties`);
    const p = markerOf(back);
    const ok = back.timeSpentSeconds === e.timeSpentSeconds && flat(back.comment) === e.comment && p && p.marker === e.marker;
    seen[e.ticket].add(e.marker);
    res.push({ m: e.marker, r: ok ? "pushed" : "PUSHED, READ-BACK MISMATCH", t: e.ticket, id: w.id });
  }
  window.__jiraPush = { at: new Date().toISOString(), apply: APPLY, res };
  const count = {}; res.forEach(x => { const k = x.r.split(" ")[0]; count[k] = (count[k] || 0) + 1; });
  const bad = res.filter(x => /FAILED|MISMATCH|bad/.test(x.r)).map(x => x.m + " " + x.r);
  return JSON.stringify({ apply: APPLY, entries: PLAN.length, count, bad });
})();
