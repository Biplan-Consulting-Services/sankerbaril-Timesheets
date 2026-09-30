// READ-ONLY. Pull the signed-in user's worklogs on Jira project AFDS, from inside a
// biplan-consulting.atlassian.net tab (the page's own sign-in; no token).
//
// Run it in that tab (Claude does it through claude-in-chrome's javascript tool, or paste it in
// the DevTools console). The full pull stays in the page as window.__jiraPull. What
// reconciliation needs is small and comes back in parts (the tool's output is cut near
// 1,000 characters): jiraPart("days") -> "YYYY-MM-DD=hours ...", jiraPart("markers") -> the
// "[WS-xxx stem]" tags already in Jira, jiraPart("issues", n) -> "KEY|summary" lines, 20 per part.
// Claude saves them as Timesheets/jira/pulls/<YYYY-MM-DD>.json (see jira/README.md).
//
// Each worklog keeps its comment text, which is where pushed worklogs carry their
// "[WS-xxx <csv-stem>]" marker - that marker is how reconciliation knows a timesheet row is
// already in Jira, so nothing is ever pushed twice.
(async () => {
  const PROJECT = "AFDS";
  const SINCE = window.JIRA_SINCE || "2026-08-01";          // set window.JIRA_SINCE first to narrow the pull
  const H = { Accept: "application/json" };
  const get = async (u) => { const r = await fetch(u, { headers: H }); if (!r.ok) throw new Error(r.status + " " + u); return r.json(); };
  const me = await get("/rest/api/3/myself");
  let issues = [], token = null, guard = 0;
  do {
    const body = { jql: `project = ${PROJECT} AND worklogDate >= "${SINCE}" ORDER BY key`, fields: ["summary", "status"], maxResults: 100 };
    if (token) body.nextPageToken = token;
    const r = await fetch("/rest/api/3/search/jql", { method: "POST", headers: { ...H, "Content-Type": "application/json" }, body: JSON.stringify(body) });
    if (!r.ok) throw new Error("search " + r.status + " " + (await r.text()).slice(0, 200));
    const j = await r.json();
    issues = issues.concat(j.issues || []);
    token = j.nextPageToken || null;
  } while (token && ++guard < 20);
  const startedAfter = new Date(SINCE + "T00:00:00-04:00").getTime();
  const flat = (adf) => { const out = []; (function walk(n) { if (!n) return; if (n.text) out.push(n.text); (n.content || []).forEach(walk); })(adf); return out.join(" "); };
  const logs = [];
  for (const is of issues) {
    let at = 0, total = 1;
    while (at < total) {
      const j = await get(`/rest/api/3/issue/${is.key}/worklog?startAt=${at}&maxResults=100&startedAfter=${startedAfter}`);
      total = j.total; const page = j.worklogs || []; at += page.length; if (!page.length) break;
      page.forEach(w => logs.push({ key: is.key, id: w.id, mine: !!(w.author && w.author.accountId === me.accountId),
        started: w.started, seconds: w.timeSpentSeconds, comment: flat(w.comment).slice(0, 300) }));
    }
  }
  const data = { pulledAt: new Date().toISOString(), project: PROJECT, since: SINCE, me: me.displayName, tz: me.timeZone,
    issues: issues.map(i => ({ key: i.key, summary: i.fields.summary, status: i.fields.status && i.fields.status.name })), logs };
  window.__jiraPull = data;
  const mine = logs.filter(l => l.mine);
  window.jiraPart = (part, n = 0) => {
    if (part === "days") {
      const by = {}; mine.forEach(l => { const d = l.started.slice(0, 10); by[d] = (by[d] || 0) + l.seconds / 3600; });
      return Object.keys(by).sort().map(d => d + "=" + by[d].toFixed(2)).join(" ");
    }
    if (part === "markers") {   // tags written by jira_push.js: "[WS-107 pioneer-transformer-workflow-automation]"
      const m = []; mine.forEach(l => (l.comment.match(/\[WS-\d+ [a-z0-9_.-]+\]/g) || []).forEach(t => m.push(t.slice(1, -1) + "@" + l.key)));
      return m.join(" ") || "(none)";
    }
    if (part === "issues") return data.issues.slice(n * 20, n * 20 + 20).map(i => i.key + "|" + (i.summary || "").slice(0, 38)).join("\n");
    return "parts: days, markers, issues";
  };
  return JSON.stringify({ issues: data.issues.length, logs: logs.length, mine: mine.length,
    first: mine.map(l => l.started).sort()[0], last: mine.map(l => l.started).sort().slice(-1)[0] });
})();
