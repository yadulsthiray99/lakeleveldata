"""Fetch lake elevations for every lake in data/registry.json and merge them into data/lakes/<slug>.json.

Stored per lake: daily  {date: elevation ft}  (last reading of the local day, or the source's daily value)
                 latest {value, time}         (newest reading, ISO time with offset)
                 guide  {date: ft}            (USACE guide curve, where the district publishes one)
                 extra  {...}                 (TWDB: percent full, conservation pool, capacity, records)

Usage: python scripts/fetch_lakes.py [--backfill DAYS] [slug ...]
Default window is 45 days (incremental). A first run for a lake automatically backfills 3 years.
Sources: TWDB (Texas), USBR RISE, USGS, USACE CWMS, California CDEC. All public, no keys.
"""
import csv, io, json, re, sys, time, urllib.parse, urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DAY = re.compile(r"^\d{4}-\d\d-\d\d$")
STORE = ROOT / "data" / "lakes"
UA = {"User-Agent": "lakeleveldata-fetch/1.0"}  # CDEC returns an empty body for agents containing a URL
BACKFILL = 1100
# standard-time UTC offsets, used to bucket hourly readings into local days
TZ = {"TX": -6, "NM": -7, "NV": -8, "AZ": -7, "UT": -7, "CO": -7, "CA": -8, "GA": -5, "SC": -5, "NC": -5, "VA": -5, "MO": -6,
      "AR": -6, "OK": -6, "KS": -6, "KY": -5, "MS": -6, "AL": -6, "FL": -5, "NY": -5, "TN": -6}


def get(url, accept=None, tries=3):
    h = dict(UA)
    if accept:
        h["accept"] = accept
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=120) as f:
                return f.read()
        except Exception as e:
            if i == tries - 1:
                raise
            time.sleep(3 * (i + 1))


def day_key(s):
    """'2026-9-9 0:00' / '2026-09-09 00:00' -> '2026-09-09' (CDEC drops leading zeros on some stations)."""
    y, m, d = s.split()[0].split("-")
    return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"


def ok(v):
    return v is not None and v != -9999 and 0 < float(v) < 15000


def local_day(ts_utc: datetime, state):
    return (ts_utc + timedelta(hours=TZ[state])).date().isoformat()


def iso(ts_utc: datetime, state):
    return ts_utc.astimezone(timezone(timedelta(hours=TZ[state]))).isoformat(timespec="minutes")


# ---------------- sources: each returns (daily dict, latest dict|None, extra dict)
def twdb(l, start, recent):
    t = recent[l["id"]]
    extra = {k: t.get(k) for k in ("percent_full", "conservation_pool_elevation", "conservation_capacity", "conservation_storage",
                                   "dead_pool_elevation", "area", "volume")}
    daily = {}
    if True:  # full CSV every run: it is the only daily feed, and the period-of-record extremes come from it
        txt = get(f"https://www.waterdatafortexas.org/reservoirs/individual/{l['hist']}.csv").decode("utf-8")
        rows = [r for r in csv.DictReader(io.StringIO("\n".join(x for x in txt.splitlines() if not x.startswith("#"))))
                if r.get("water_level") not in (None, "")]
    for r in rows:
        if r["date"] >= start.isoformat():
            daily[r["date"]] = round(float(r["water_level"]), 2)
    if rows:  # records over the whole period of record (daily rows only; early years are monthly)
        lv = [(float(r["water_level"]), r["date"]) for r in rows]
        pf = [(float(r["percent_full"]), r["date"]) for r in rows if r.get("percent_full") not in (None, "")]
        lo, hi = min(lv), max(lv)
        extra["record"] = {"since": rows[0]["date"][:4], "low": lo[0], "low_date": lo[1], "high": hi[0], "high_date": hi[1]}
        if pf:
            extra["pf_daily"] = {r["date"]: float(r["percent_full"]) for r in rows if r["date"] >= start.isoformat() and r.get("percent_full")}
    latest = None
    if t.get("elevation") and t.get("timestamp"):
        latest = {"value": round(t["elevation"], 2), "time": t["timestamp"], "daily_only": True}
        daily.setdefault(t["timestamp"], round(t["elevation"], 2))
    return daily, latest, extra


def hdb(l, start):
    svr, sdi = l["id"]
    q = urllib.parse.urlencode({"svr": svr, "sdi": sdi, "tstp": "DY", "t1": start.isoformat() + "T00:00", "t2": date.today().isoformat() + "T00:00",
                                "table": "R", "mrid": 0, "format": "json"})
    d = json.loads(get("https://www.usbr.gov/pn-bin/hdb/hdb.pl?" + q))
    daily = {}
    for x in d["Series"][0]["Data"]:
        if x["v"] and ok(float(x["v"])):
            m, dd, y = x["t"].split()[0].split("/")
            daily[f"{y}-{int(m):02d}-{int(dd):02d}"] = round(float(x["v"]), 2)
    if not daily:
        return daily, None, {}
    last = max(daily)
    return daily, {"value": daily[last], "time": last, "daily_only": True}, {}


def rise(l, start):
    daily, page = {}, 1
    while True:
        q = urllib.parse.urlencode({"itemId": l["id"], "dateTime[after]": start.isoformat(), "order[dateTime]": "ASC", "itemsPerPage": 1000, "page": page})
        d = json.loads(get("https://data.usbr.gov/rise/api/result?" + q, "application/vnd.api+json"))
        for x in d["data"]:
            a = x["attributes"]
            if ok(a.get("result")):
                ts = datetime.fromisoformat(a["dateTime"])
                daily[local_day(ts, l["state"])] = round(float(a["result"]), 2)
        if len(d["data"]) < 1000:
            break
        page += 1
    if not daily:
        return daily, None, {}
    last = max(daily)
    return daily, {"value": daily[last], "time": last, "daily_only": True}, {}


def usgs(l, start):
    daily = {}
    for svc, extra_q in (("dv", "&statCd=00003"), ("iv", "")):
        s = start if svc == "dv" else date.today() - timedelta(days=7)
        url = f"https://waterservices.usgs.gov/nwis/{svc}/?format=json&sites={l['id']}&parameterCd=62614,62615,00062&startDT={s.isoformat()}{extra_q}"
        d = json.loads(get(url))
        series = sorted(d["value"]["timeSeries"], key=lambda t: ["62614", "00062", "62615"].index(t["variable"]["variableCode"][0]["value"]))
        if not series:
            continue
        vals = [v for v in series[0]["values"][0]["value"] if ok(float(v["value"]))]
        for v in vals:
            if svc == "dv":
                daily[v["dateTime"][:10]] = round(float(v["value"]), 2)
            else:
                daily[v["dateTime"][:10]] = round(float(v["value"]), 2)  # IV dateTime already carries the local offset
        if svc == "iv" and vals:
            latest = {"value": round(float(vals[-1]["value"]), 2), "time": vals[-1]["dateTime"][:16] + vals[-1]["dateTime"][-6:]}
    if len(daily) < 20 and start < date.today() - timedelta(days=30):  # gauge without daily means: use last IV reading of each day
        s = start
        while s < date.today():
            e = min(s + timedelta(days=120), date.today() + timedelta(days=1))
            d = json.loads(get(f"https://waterservices.usgs.gov/nwis/iv/?format=json&sites={l['id']}&parameterCd=62614,62615,00062&startDT={s.isoformat()}&endDT={e.isoformat()}"))
            series = sorted(d["value"]["timeSeries"], key=lambda t: ["62614", "00062", "62615"].index(t["variable"]["variableCode"][0]["value"]))
            for v in (series[0]["values"][0]["value"] if series else []):
                if ok(float(v["value"])):
                    daily[v["dateTime"][:10]] = round(float(v["value"]), 2)
            s = e
    if not daily:
        return daily, None, {}
    return daily, locals().get("latest") or {"value": daily[max(daily)], "time": max(daily), "daily_only": True}, {}


def cwms_series(office, name, start, state):
    out, latest, end = {}, None, datetime.now(timezone.utc) + timedelta(hours=1)
    begin = datetime.combine(start, datetime.min.time(), timezone.utc)
    while begin < end:  # 120-day chunks keep each response small
        stop = min(begin + timedelta(days=120), end)
        q = urllib.parse.urlencode({"office": office, "name": name, "begin": begin.strftime("%Y-%m-%dT%H:%M:%SZ"),
                                    "end": stop.strftime("%Y-%m-%dT%H:%M:%SZ"), "page-size": 50000})
        d = json.loads(get("https://cwms-data.usace.army.mil/cwms-data/timeseries?" + q, "application/json;version=2"))
        for ms, v, *_ in d.get("values") or []:
            if ok(v):
                ts = datetime.fromtimestamp(ms / 1000, timezone.utc)
                out[local_day(ts, state)] = round(float(v), 2)
                latest = (ts, round(float(v), 2))
        begin = stop
    return out, latest


def cwms(l, start):
    (office, name) = l["id"]
    daily, last = cwms_series(office, name, start, l["state"])
    extra = {}
    if l.get("guide"):
        try:
            g, _ = cwms_series(l["guide"][0], l["guide"][1], start, l["state"])
            extra["guide"] = g
        except Exception as e:
            print("   guide curve failed:", e)
    latest = {"value": last[1], "time": iso(last[0], l["state"])} if last else None
    return daily, latest, extra


def cdec(l, start):
    daily, extra = {}, {}
    for sensor, key in ((6, "elev"), (15, "storage")):
        q = urllib.parse.urlencode({"Stations": l["id"], "SensorNums": sensor, "dur_code": "D", "Start": start.isoformat(), "End": date.today().isoformat()})
        d = json.loads(get("https://cdec.water.ca.gov/dynamicapp/req/JSONDataServlet?" + q))
        vals = {day_key(r["date"]): r["value"] for r in d if r.get("value") is not None and r["value"] not in (-9999, -9998)}
        if key == "elev":
            daily = {k: round(float(v), 2) for k, v in vals.items() if ok(v)}
        else:
            extra["storage"] = {k: int(v) for k, v in vals.items() if v and v > 0}
    if not daily:
        return daily, None, extra
    last = max(daily)
    return daily, {"value": daily[last], "time": last, "daily_only": True}, extra


def main():
    args = sys.argv[1:]
    window = 45
    if "--backfill" in args:
        i = args.index("--backfill"); window = int(args[i + 1]); del args[i:i + 2]
    reg = json.load(open(ROOT / "data" / "registry.json", encoding="utf-8"))
    if args:
        reg = [l for l in reg if l["slug"] in args]
    STORE.mkdir(parents=True, exist_ok=True)
    recent = None
    fails = []
    for l in reg:
        path = STORE / f"{l['slug']}.json"
        old = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"daily": {}}
        days = window if old["daily"] else max(window, BACKFILL)
        start = date.today() - timedelta(days=days)
        try:
            if l["source"] == "twdb":
                if recent is None:
                    recent = json.loads(get("https://www.waterdatafortexas.org/reservoirs/recent-conditions.json"))
                daily, latest, extra = twdb(l, start, recent)
            else:
                daily, latest, extra = {"hdb": hdb, "rise": rise, "usgs": usgs, "cwms": cwms, "cdec": cdec}[l["source"]](l, start)
        except Exception as e:
            print(f"FAIL {l['slug']}: {e}"); fails.append(l["slug"]); continue
        if not daily:
            print(f"EMPTY {l['slug']}"); fails.append(l["slug"]); continue
        valid = DAY.match
        old["daily"] = {k: v for k, v in old["daily"].items() if valid(k)}
        merged = {**old["daily"], **daily}
        cutoff = (date.today() - timedelta(days=BACKFILL + 30)).isoformat()
        rec = {"daily": dict(sorted((k, v) for k, v in merged.items() if k >= cutoff))}
        rec["latest"] = latest or old.get("latest")
        for k, v in extra.items():
            if isinstance(v, dict) and k in ("guide", "storage", "pf_daily"):
                v = dict(sorted((dk, dv) for dk, dv in {**old.get(k, {}), **v}.items() if dk >= cutoff))
            rec[k] = v
        for k in ("guide", "storage", "pf_daily", "record", "percent_full"):
            if k not in rec and k in old:
                rec[k] = old[k]
        rec["fetched"] = datetime.now(timezone.utc).isoformat(timespec="minutes")
        path.write_text(json.dumps(rec, separators=(",", ":")), encoding="utf-8")
        print(f"ok {l['slug']:<32} {len(daily):>5} new days, latest {rec['latest']['value'] if rec['latest'] else '-'} @ {rec['latest']['time'] if rec['latest'] else '-'}")
        time.sleep(0.3)
    print(f"done: {len(reg) - len(fails)} ok, {len(fails)} failed {fails}")
    sys.exit(1 if len(fails) > len(reg) // 4 else 0)


if __name__ == "__main__":
    main()
