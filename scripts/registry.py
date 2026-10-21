"""Lake registry: which lakes we publish, where each one's data comes from, and search demand.

Writes data/registry.json. Demand = highest monthly US search volume among "<lake> ... level" keywords
(data/lake_level.csv + data/water_level.csv). Lakes with no measurable demand are left out on purpose.

full_pool is only set where the source publishes it (TWDB conservation pool) or where the operator's
published top-of-conservation-pool elevation is well established; CWMS guide curves are fetched live.
"""
import csv, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATES = {"TX": "Texas", "NM": "New Mexico", "NV": "Nevada", "AZ": "Arizona", "UT": "Utah", "CO": "Colorado", "CA": "California",
          "GA": "Georgia", "SC": "South Carolina", "NC": "North Carolina", "VA": "Virginia", "MO": "Missouri", "AR": "Arkansas",
          "OK": "Oklahoma", "KS": "Kansas", "KY": "Kentucky", "MS": "Mississippi", "AL": "Alabama", "FL": "Florida", "NY": "New York",
          "TN": "Tennessee"}

def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")

L = []
def add(name, state, source, sid, q, **kw):
    L.append({"name": name, "state": state, "source": source, "id": sid, "q": q, **kw})

# --- Texas (+ Elephant Butte NM) from TWDB: id = recent-conditions key; history CSV slug derived from it
for key, q in {
    "Travis": r"travis", "Canyon": r"^(?!.*choke).*\bcanyon lake\b|\blake canyon\b", "Medina": r"medina", "CorpusChristi": r"corpus christi|mathis",
    "ChokeCanyon": r"choke canyon", "ToledoBend": r"toledo bend", "SamRayburn": r"rayburn", "Buchanan": r"buchanan", "ElephantButte": r"elephant butte",
    "Amistad": r"amistad", "Falcon": r"falcon", "CedarCreek": r"cedar creek", "Texoma": r"texoma", "Brownwood": r"brownwood", "Texana": r"texana",
    "Somerville": r"somerville", "Fork": r"lake fork", "Belton": r"belton", "Georgetown": r"georgetown", "Lavon": r"lavon", "Limestone": r"limestone",
    "Conroe": r"conroe", "RichlandChambers": r"richland", "Livingston": r"livingston", "EagleMountain": r"eagle mountain", "Lewisville": r"lewisville",
    "WrightPatman": r"wright patman", "OHIvie": r"ivie", "Bridgeport": r"bridgeport", "StillhouseHollow": r"stillhouse", "HubbardCreek": r"hubbard creek",
    "Tawakoni": r"tawakoni", "Waco": r"lake waco|waco lake", "Meredith": r"meredith", "Palestine": r"palestine", "Grapevine": r"grapevine",
    "LyndonBJohnson": r"\blbj\b|lyndon b", "Whitney": r"whitney", "PossumKingdom": r"possum kingdom",
    "Granbury": r"granbury", "RayRoberts": r"ray roberts", "RayHubbard": r"ray hubbard", "Proctor": r"proctor",
    "Granger": r"granger", "Lake O' the Pines": r"o the pines|of the pines",
}.items():
    add(None, "TX", "twdb", key, q)

# --- Colorado River & other USBR reservoirs (Reclamation HDB: (server, site-datatype id), daily end-of-day elevation)
add("Lake Mead", "NV", "hdb", ("lchdb", 1930), r"\bmead\b|hoover dam", full_pool=1229, full_pool_src="Bureau of Reclamation full pool")
add("Lake Havasu", "AZ", "hdb", ("lchdb", 2101), r"havasu")
add("Lake Mohave", "NV", "hdb", ("lchdb", 2100), r"mohave")
add("Navajo Reservoir", "NM", "hdb", ("uchdb2", 1929), r"navajo (lake|reservoir)")
add("Flaming Gorge Reservoir", "UT", "hdb", ("uchdb2", 1927), r"flaming gorge")
add("Blue Mesa Reservoir", "CO", "hdb", ("uchdb2", 1923), r"blue mesa")

# --- USGS lake gauges (instantaneous values; 62614 = elevation above NGVD29, 62615 = NAVD88, 00062 = reservoir elevation)
add("Lake Powell", "AZ", "usgs", "09379900", r"\bpowell\b", full_pool=3700, full_pool_src="Bureau of Reclamation full pool")
add("Lake Lanier", "GA", "cwms", ("SAM", "Buford.Elev.Inst.1Hour.0.Raw-USGS"), r"lanier", guide=("SAM", "Buford.Elev-Guide Curve.Inst.15Minutes.0.Rev-PROJECT"), full_pool=1071, full_pool_src="U.S. Army Corps of Engineers full summer pool")
add("Kerr Lake", "VA", "usgs", "02079490", r"\bkerr\b|buggs island")
add("Falls Lake", "NC", "usgs", "02087182", r"falls lake|lake falls", full_pool=251.5, full_pool_src="U.S. Army Corps of Engineers normal pool")
add("Jordan Lake", "NC", "usgs", "02098197", r"jordan lake|lake jordan", full_pool=216, full_pool_src="U.S. Army Corps of Engineers normal pool")
add("Lake Murray", "SC", "usgs", "02168500", r"lake murray|murray lake")
add("Lake Champlain", "NY", "usgs", "04294413", r"champlain")
add("Cheney Reservoir", "KS", "usgs", "07144790", r"cheney")
add("Lake Seminole", "FL", "usgs", "02357500", r"seminole")
add("Walter F. George Lake", "GA", "usgs", "02343240", r"walter f|lake eufaula al|eufaula alabama|eufaula al\b")
add("Lake Marion", "SC", "usgs", "02171000", r"lake marion")
add("Lake Moultrie", "SC", "usgs", "02172000", r"moultrie")

# --- U.S. Army Corps of Engineers (CWMS Data API)
add("Lake Allatoona", "GA", "cwms", ("SAM", "Allatoona.Elev.Inst.1Hour.0.Raw-USGS"), r"allatoona", guide=("SAM", "Allatoona.Elev-Guide Curve.Inst.1Day.0.Rev-PROJECT"))
add("Lake Hartwell", "SC", "cwms", ("SAS", "Hartwell.Elev-Head.Inst.1Hour.0.Raw-SHEF_SAS"), r"hartwell", guide=("SAS", "Hartwell.Elev-GC.Inst.1Day.0.ARCHIVE-DAILY"))
add("Lake Thurmond", "SC", "cwms", ("SAS", "Thurmond.Elev-Head.Inst.1Hour.0.Raw-SHEF_SAS"), r"thurmond|clarks? hill", guide=("SAS", "Thurmond.Elev-GC.Inst.1Day.0.ARCHIVE-DAILY"))
add("Lake Russell", "SC", "cwms", ("SAS", "Russell.Elev-Head.Inst.1Hour.0.Raw-SHEF_SAS"), r"russell lake|lake russell", guide=("SAS", "Russell.Elev-GC.Inst.1Day.0.ARCHIVE-DAILY"))
add("Table Rock Lake", "MO", "cwms", ("SWL", "Table_Rock_Dam-Headwater.Elev.Inst.1Hour.0.Decodes-rev"), r"table rock", full_pool=915, full_pool_src="U.S. Army Corps of Engineers top of conservation pool")
add("Beaver Lake", "AR", "cwms", ("SWL", "Beaver_Dam-Headwater.Elev.Inst.1Hour.0.Decodes-rev"), r"beaver lake", full_pool=1120, full_pool_src="U.S. Army Corps of Engineers top of conservation pool")
add("Bull Shoals Lake", "AR", "cwms", ("SWL", "Bull_Shoals_Dam-Headwater.Elev.Inst.1Hour.0.Decodes-rev"), r"bull shoals", full_pool=654, full_pool_src="U.S. Army Corps of Engineers top of conservation pool")
add("Norfork Lake", "AR", "cwms", ("SWL", "Norfork_Dam-Headwater.Elev.Inst.1Hour.0.Decodes-rev"), r"norfork", full_pool=552, full_pool_src="U.S. Army Corps of Engineers top of conservation pool")
add("Greers Ferry Lake", "AR", "cwms", ("SWL", "GreersFerry_Dam-Headwater.Elev.Inst.1Hour.0.Decodes-rev"), r"greers ferry")
add("Keystone Lake", "OK", "cwms", ("SWT", "KEYS.Elev.Inst.1Hour.0.Ccp-Rev"), r"keystone")
add("Lake Eufaula", "OK", "cwms", ("SWT", "EUFA.Elev.Inst.1Hour.0.Ccp-Rev"), r"eufaula(?! al)(?! alabama)")
add("Oologah Lake", "OK", "cwms", ("SWT", "OOLO.Elev.Inst.1Hour.0.Ccp-Rev"), r"oologah")
add("Lake Tenkiller", "OK", "cwms", ("SWT", "TENK.Elev.Inst.1Hour.0.Ccp-Rev"), r"tenkiller")
add("Kaw Lake", "OK", "cwms", ("SWT", "KAWL.Elev.Inst.1Hour.0.Ccp-Rev"), r"\bkaw\b")
add("Grand Lake o' the Cherokees", "OK", "cwms", ("SWT", "PENS.Elev.Inst.1Hour.0.Ccp-Rev"), r"grand lake")
add("Fort Gibson Lake", "OK", "cwms", ("SWT", "FGIB.Elev.Inst.1Hour.0.Ccp-Rev"), r"fort gibson|ft gibson")
add("Nolin River Lake", "KY", "cwms", ("LRL", "Nolin-Lake.Elev.Inst.5Minutes.0.USGS-rev"), r"nolin")
add("Rough River Lake", "KY", "cwms", ("LRL", "Rough-Lake.Elev.Inst.15Minutes.0.USGS-rev"), r"rough river")
add("Barren River Lake", "KY", "cwms", ("LRL", "Barren-Lake.Elev.Inst.15Minutes.0.USGS-rev"), r"barren river")
add("Taylorsville Lake", "KY", "cwms", ("LRL", "Taylorsville-Lake.Elev.Inst.5Minutes.0.USGS-rev"), r"taylorsville")
add("Lake Cumberland", "KY", "cwms", ("LRN", "Wolf Creek Dam.Elev.Inst.1Hour.0.celrn-cwms-forecast"), r"cumberland")
add("Dale Hollow Lake", "TN", "cwms", ("LRN", "Dale Hollow Dam.Elev.Inst.1Hour.0.celrn-cwms-forecast"), r"dale hollow")
add("Center Hill Lake", "TN", "cwms", ("LRN", "Center Hill Dam.Elev.Inst.1Hour.0.celrn-cwms-forecast"), r"center hill")
add("Sardis Lake", "MS", "cwms", ("MVK", "Sardis Lake.Elev.Inst.1Hour.0.DCP-rev"), r"sardis", guide=("MVK", "Sardis Lake.Elev.Inst.1Hour.0.Guide Curve"))
add("Grenada Lake", "MS", "cwms", ("MVK", "Grenada Lake.Elev.Inst.1Hour.0.DCP-rev"), r"grenada", guide=("MVK", "Grenada Lake.Elev.Inst.1Hour.0.Guide Curve"))
add("Smith Lake", "AL", "cwms", ("SAM", "Smith.Elev.Inst.1Hour.0.Raw-APCO"), r"smith lake|lewis smith", guide=("SAM", "Smith.Elev.Inst.1Hour.0.GC-APCO"))
add("Weiss Lake", "AL", "cwms", ("SAM", "Weiss.Elev.Inst.1Hour.0.Raw-APCO"), r"weiss", guide=("SAM", "Weiss.Elev.Inst.1Hour.0.GC-APCO"))

# --- California (CDEC daily: sensor 6 = elevation, 15 = storage)
for sid, name, q in [("SHA", "Shasta Lake", r"shasta"), ("ORO", "Lake Oroville", r"oroville"), ("FOL", "Folsom Lake", r"folsom"),
                     ("BER", "Lake Berryessa", r"berryessa"), ("CSI", "Lake Casitas", r"casitas"), ("CLE", "Trinity Lake", r"trinity lake"),
                     ("NML", "New Melones Lake", r"new melones"), ("SNL", "San Luis Reservoir", r"san luis reservoir"),
                     ("MIL", "Millerton Lake", r"millerton"), ("PNF", "Pine Flat Lake", r"pine flat")]:
    add(name, "CA", "cdec", sid, q)


# Google Ads US volumes (DataForSEO, 2026-10-20) for lakes outside the 700-keyword research sample
MEASURED = {"Whitney Lake": 480, "Possum Kingdom Lake": 590, "Lake Granbury": 390, "Ray Roberts Lake": 390, "Lake Ray Hubbard": 480,
            "Proctor Lake": 390, "Granger Lake": 140, "Lake Mohave": 320, "Lake Seminole": 90, "Walter F. George Lake": 110,
            "Lake Moultrie": 590, "Lake Russell": 320, "Dale Hollow Lake": 390, "Center Hill Lake": 170, "Trinity Lake": 480,
            "New Melones Lake": 110, "San Luis Reservoir": 170, "Millerton Lake": 320, "Pine Flat Lake": 390,
            "Lake L. B. Johnson": 590, "Lake O the Pines": 390, "Lake Texoma": 2400}


def demand(q):
    rx, best = re.compile(q), 0
    for f in ("lake_level.csv", "water_level.csv"):
        for r in csv.DictReader(open(ROOT / "data" / f, encoding="utf-8")):
            k = r["keyword"].lower()
            if "level" in k and rx.search(k):
                best = max(best, int(r["volume"]))
    return best


if __name__ == "__main__":
    twdb = json.load(open(ROOT / "data" / "twdb_recent.json", encoding="utf-8"))
    out = []
    for l in L:
        if l["source"] == "twdb":
            t = twdb.get(l["id"])
            if not t:
                print("TWDB key not found:", l["id"]); continue
            l["name"] = t["full_name"]
            l["state"] = "NM" if l["id"] == "ElephantButte" else "TX"
            l["hist"] = re.sub(r"[^a-z]+", "-", re.sub(r"(?<!^)(?=[A-Z])", "-", l["id"]).lower()).strip("-")
        l["demand"] = max(demand(l["q"]), MEASURED.get(l["name"], 0))
        l["state_name"] = STATES[l["state"]]
        l["slug"] = slug(l["name"].replace("'", ""))
        l["state_slug"] = slug(l["state_name"])
        out.append(l)
    out.sort(key=lambda l: -l["demand"])
    keep = [l for l in out if l["demand"] >= 30]
    for l in out:
        print(f"{l['demand']:>6} {'' if l in keep else 'DROP'} {l['name']:<32} {l['state']} {l['source']}")
    json.dump(keep, open(ROOT / "data" / "registry.json", "w", encoding="utf-8"), indent=1)
    print(len(keep), "lakes kept of", len(out))
