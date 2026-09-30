// Push a reviewed plan (jira/plans/<date>.json) to Jira AFDS as worklogs, from inside a
// biplan-consulting.atlassian.net tab (the page's own sign-in; no token).
//
// DRY RUN BY DEFAULT. It only writes when window.JIRA_APPLY === true, and that is set only
// after the user has read the plan's .md report and said OK in chat.
//
// Before running: window.JIRA_PLAN = <the "entries" array of the plan json>.
// For each entry it first re-reads that issue's worklogs and skips the entry if its
// "[WS-xxx stem]" marker is already there (so a re-run or a half-finished run never
// duplicates), then POSTs the worklog and reads it back. Returns a compact summary; the
// detail stays in window.__jiraPush.
(async () => {
  const PLAN = window.JIRA_PLAN || [];
  const APPLY = window.JIRA_APPLY === true;
  const H = { Accept: "application/json", "Content-Type": "application/json" };
  const get = async (u) => { const r = await fetch(u, { headers: H }); if (!r.ok) throw new Error(r.status + " " + u); return r.json(); };
  const flat = (adf) => { const o = []; (function w(n) { if (!n) return; if (n.text) o.push(n.text); (n.content || []).forEach(w); })(adf); return o.join(" "); };
  const me = await get("/rest/api/3/myself");
  const seen = {};   // issue key -> set of markers already on it (mine only)
  const markersOn = async (key) => {
    if (seen[key]) return seen[key];
    const s = new Set();
    let at = 0, total = 1;
    while (at < total) {
      const j = await get(`/rest/api/3/issue/${key}/worklog?startAt=${at}&maxResults=100`);
      total = j.total; const page = j.worklogs || []; at += page.length; if (!page.length) break;
      page.filter(w => w.author && w.author.accountId === me.accountId)
        .forEach(w => (flat(w.comment).match(/\[WS-\d+ [a-z0-9_.-]+\]/g) || []).forEach(m => s.add(m)));
    }
    return (seen[key] = s);
  };
  const res = [];
  for (const e of PLAN) {
    if (!/^AFDS-\d+$/.test(e.ticket) || !e.marker || !(e.timeSpentSeconds > 0)) { res.push({ m: e.marker, r: "bad entry" }); continue; }
    if ((await markersOn(e.ticket)).has(e.marker)) { res.push({ m: e.marker, r: "already there" }); continue; }
    if (!APPLY) { res.push({ m: e.marker, r: "would push", t: e.ticket, h: e.timeSpentSeconds / 3600 }); continue; }
    const body = { started: e.started, timeSpentSeconds: e.timeSpentSeconds,
      comment: { type: "doc", version: 1, content: [{ type: "paragraph", content: [{ type: "text", text: e.comment }] }] } };
    const r = await fetch(`/rest/api/3/issue/${e.ticket}/worklog?notifyUsers=false&adjustEstimate=leave`,
      { method: "POST", headers: H, body: JSON.stringify(body) });
    if (!r.ok) { res.push({ m: e.marker, r: "FAILED " + r.status + " " + (await r.text()).slice(0, 120) }); continue; }
    const w = await r.json();
    const back = await get(`/rest/api/3/issue/${e.ticket}/worklog/${w.id}`);
    const ok = back.timeSpentSeconds === e.timeSpentSeconds && flat(back.comment).includes(e.marker);
    seen[e.ticket].add(e.marker);
    res.push({ m: e.marker, r: ok ? "pushed" : "PUSHED, READ-BACK MISMATCH", t: e.ticket, id: w.id });
  }
  window.__jiraPush = { at: new Date().toISOString(), apply: APPLY, res };
  const count = {}; res.forEach(x => { const k = x.r.split(" ")[0]; count[k] = (count[k] || 0) + 1; });
  const bad = res.filter(x => /FAILED|MISMATCH|bad/.test(x.r)).map(x => x.m + " " + x.r);
  return JSON.stringify({ apply: APPLY, entries: PLAN.length, count, bad });
})();
