import json, urllib.request, urllib.parse
UA={"User-Agent":"lakeleveldata-build/1.0","accept":"application/json;version=2"}
def get(u):
    with urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=90) as f: return json.load(f)
Q=[("Lanier","SAM","Buford"),("Allatoona","SAM","Allatoona"),("Hartwell","SAS","Hartwell"),("Thurmond","SAS","Thurmond"),("Russell","SAS","Russell"),
("Table Rock","SWL","Table_Rock"),("Beaver","SWL","Beaver"),("Bull Shoals","SWL","Bull_Shoals"),("Norfork","SWL","Norfork"),("Greers Ferry","SWL","Greers"),
("Kerr","SAW","Kerr"),("Falls","SAW","Falls"),("Jordan","SAW","Jordan"),("Truman","NWK","Truman"),("Stockton","NWK","Stockton"),("Perry","NWK","Perry"),("Milford","NWK","Milford"),
("Keystone","SWT","Keystone"),("Eufaula","SWT","Eufaula"),("Oologah","SWT","Oologah"),("Tenkiller","SWT","Tenkiller"),("Kaw","SWT","Kaw"),("Grand","SWT","Pensacola"),("Texoma","SWT","Denison"),("Fort Gibson","SWT","Gibson"),
("Nolin","LRL","Nolin"),("Rough River","LRL","Rough"),("Barren River","LRL","Barren"),("Taylorsville","LRL","Taylorsville"),("Cumberland","LRN","Wolf"),("Dale Hollow","LRN","Dale"),("Center Hill","LRN","Center"),("Percy Priest","LRN","Priest"),
("Okeechobee","SAJ","Okee"),("Sardis","MVK","Sardis"),("Grenada","MVK","Grenada"),("Lake Lewis Smith","SAM","Smith"),("Weiss","SAM","Weiss")]
out={}
for lake,off,pat in Q:
    try:
        d=get("https://cwms-data.usace.army.mil/cwms-data/catalog/TIMESERIES?"+urllib.parse.urlencode({"office":off,"like":f"{pat}.*Elev.*","page-size":200}))
        names=[e["name"] for e in d.get("entries",[])]
    except Exception as e: names=[]; print(lake,"ERR",e)
    pick=[n for n in names if "Tailwater" not in n and "Guide" not in n and "-GC" not in n and ".Inst." in n and ("1Hour" in n or "15Minutes" in n or "~1Day" in n)]
    gc=[n for n in names if "Guide" in n or "-GC" in n]
    out[lake]={"office":off,"cand":pick[:6],"guide":gc[:3]}
    print(f"{lake:<14}{off} {len(names):>3} | {pick[:3]} | GC {gc[:1]}")
json.dump(out,open("data/cwms_candidates.json","w"),indent=1)
