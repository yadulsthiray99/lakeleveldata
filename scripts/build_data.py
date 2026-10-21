"""Turn data/lakes/*.json (raw daily readings) into src/data/lakes.json: the per-lake numbers every page shows.

Everything here is computed from the stored readings; nothing is estimated. A lake whose newest reading is
more than STALE_DAYS old is left out of the build (its page would show an out-of-date "today" level).
"""
import json
import re
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DAY = re.compile(r"^\d{4}-\d\d-\d\d$")
STALE_DAYS = 10
SRC = {
    "twdb": ("Texas Water Development Board", "Water Data for Texas", "https://www.waterdatafortexas.org/reservoirs/individual/{hist}"),
    "hdb": ("U.S. Bureau of Reclamation", "Reclamation HDB", "https://www.usbr.gov/lc/region/g4000/riverops/"),
    "usgs": ("U.S. Geological Survey", "USGS Water Data", "https://waterdata.usgs.gov/monitoring-location/USGS-{id}/"),
    "cwms": ("U.S. Army Corps of Engineers", "USACE CWMS Data API", "https://cwms-data.usace.army.mil/"),
    "cdec": ("California Department of Water Resources", "California Data Exchange Center (CDEC)", "https://cdec.water.ca.gov/dynamicapp/QueryF?s={id}"),
}
MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()


def at(daily, keys, d: date, tol=3):
    """Reading on day d, or the closest earlier reading within tol days."""
    for i in range(tol + 1):
        k = (d - timedelta(days=i)).isoformat()
        if k in daily:
            return daily[k], k
    return None, None


def r2(x):
    return None if x is None else round(x, 2)


def build(l):
    raw = json.loads((ROOT / "data" / "lakes" / f"{l['slug']}.json").read_text(encoding="utf-8"))
    daily = {k: v for k, v in raw["daily"].items() if DAY.match(k)}
    keys = sorted(daily)
    if not keys:
        return None
    last_day = date.fromisoformat(keys[-1])
    latest = raw.get("latest") or {"value": daily[keys[-1]], "time": keys[-1]}
    if (date.today() - last_day).days > STALE_DAYS:
        print(f"STALE {l['slug']}: last reading {keys[-1]}")
        return None
    now = latest["value"]
    ref = last_day

    def change(days):
        v, k = at(daily, keys, ref - timedelta(days=days))
        return (r2(now - v), k) if v is not None else (None, None)

    year = [(k, daily[k]) for k in keys if k > (ref - timedelta(days=365)).isoformat()]
    lo = min(year, key=lambda x: x[1]); hi = max(year, key=lambda x: x[1])
    allk = [(k, daily[k]) for k in keys]
    lo3 = min(allk, key=lambda x: x[1]); hi3 = max(allk, key=lambda x: x[1])

    # full pool / target: TWDB conservation pool, USACE guide curve (today's target), or a published full pool
    full, full_src, guide_now = None, None, None
    if l["source"] == "twdb" and raw.get("conservation_pool_elevation"):
        full, full_src = raw["conservation_pool_elevation"], "top of conservation pool (TWDB)"
    elif l.get("full_pool"):
        full, full_src = l["full_pool"], l["full_pool_src"]
    guide = raw.get("guide") or {}
    if guide:
        g, _ = at(guide, sorted(guide), ref, tol=5)
        guide_now = r2(g)

    pf = raw.get("percent_full")
    pf_daily = raw.get("pf_daily") or {}
    pf_1y, _ = at(pf_daily, None, ref - timedelta(days=365)) if pf_daily else (None, None)
    storage = {k: v for k, v in (raw.get("storage") or {}).items() if DAY.match(k)}
    st_now = storage.get(max(storage)) if storage else None
    st_1y, _ = at(storage, None, ref - timedelta(days=365)) if storage else (None, None)

    # same calendar date in earlier years (up to 3)
    same = []
    for y in (1, 2, 3):
        try:
            d = ref.replace(year=ref.year - y)
        except ValueError:
            d = ref - timedelta(days=365 * y)
        v, k = at(daily, keys, d)
        if v is not None:
            same.append({"year": d.year, "value": v, "diff": r2(now - v)})

    # month averages for the last 12 complete-or-current months
    months = {}
    for k, v in year:
        months.setdefault(k[:7], []).append(v)
    monthly = [{"month": f"{MONTHS[int(m[5:]) - 1]} {m[:4]}", "avg": r2(sum(v) / len(v)), "low": min(v), "high": max(v), "days": len(v)}
               for m, v in sorted(months.items())][-12:]

    recent = []
    for k in keys[-31:]:
        recent.append({"date": k, "value": daily[k]})
    for i in range(1, len(recent)):
        recent[i]["chg"] = r2(recent[i]["value"] - recent[i - 1]["value"])
    recent = recent[1:][::-1]

    years = {}
    for k in keys:
        years.setdefault(k[:4], []).append((daily[k], k))
    yearly = [{"year": y, "low": min(v)[0], "low_date": min(v)[1], "high": max(v)[0], "high_date": max(v)[1],
               "avg": r2(sum(x[0] for x in v) / len(v)), "days": len(v)} for y, v in sorted(years.items(), reverse=True)]

    ch1, _ = change(1); ch7, _ = change(7); ch30, _ = change(30); ch365, k365 = change(365)
    trend = "steady" if ch7 is None or abs(ch7) < 0.1 else ("rising" if ch7 > 0 else "falling")
    agency, feed, url = SRC[l["source"]]
    url = url.format(hist=l.get("hist", ""), id=l["id"] if isinstance(l["id"], str) else "")
    gauge = l["id"] if isinstance(l["id"], str) else (l["id"][1] if l["source"] == "cwms" else f"{l['id'][0]} SDI {l['id'][1]}")
    return {
        "slug": l["slug"], "name": l["name"], "state": l["state"], "state_name": l["state_name"], "state_slug": l["state_slug"],
        "demand": l["demand"], "source": l["source"], "agency": agency, "feed": feed, "url": url, "gauge": gauge,
        "now": now, "time": latest["time"], "daily_only": bool(latest.get("daily_only")), "last_day": keys[-1],
        "ch1": ch1, "ch7": ch7, "ch30": ch30, "ch365": ch365, "trend": trend,
        "lo12": {"value": lo[1], "date": lo[0]}, "hi12": {"value": hi[1], "date": hi[0]},
        "lo3": {"value": lo3[1], "date": lo3[0]}, "hi3": {"value": hi3[1], "date": hi3[0]}, "first_day": keys[0],
        "full": full, "full_src": full_src, "vs_full": r2(now - full) if full else None,
        "guide": guide_now, "vs_guide": r2(now - guide_now) if guide_now else None,
        "pf": pf, "pf_1y": pf_1y, "capacity": raw.get("conservation_capacity"), "area": raw.get("area"),
        "dead_pool": raw.get("dead_pool_elevation"), "record": raw.get("record"),
        "storage": st_now, "storage_1y": st_1y,
        "same": same, "monthly": monthly, "yearly": yearly, "recent": recent,
        "chart": [[k, v] for k, v in year],
        "chart_guide": [[k, guide[k]] for k in sorted(guide) if k > (ref - timedelta(days=365)).isoformat()] if guide else [],
    }


def main():
    reg = json.load(open(ROOT / "data" / "registry.json", encoding="utf-8"))
    out, skipped = [], []
    for l in reg:
        p = ROOT / "data" / "lakes" / f"{l['slug']}.json"
        b = build(l) if p.exists() else None
        (out.append(b) if b else skipped.append(l["slug"]))
    out.sort(key=lambda x: -x["demand"])
    (ROOT / "src" / "data").mkdir(parents=True, exist_ok=True)
    built = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z")
    json.dump({"built": built, "lakes": out}, open(ROOT / "src" / "data" / "lakes.json", "w", encoding="utf-8"), separators=(",", ":"))
    print(f"{len(out)} lakes built, {len(skipped)} skipped: {skipped}")


if __name__ == "__main__":
    main()
