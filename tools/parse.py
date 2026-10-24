import sys, re, json, hashlib, logging, collections, pdfplumber
logging.disable(logging.WARNING)

CHECK, CROSS = "f2b46bb8", "5369a534"
OPT = re.compile(r"^([a-z])\.\s*(.*)$")

def size_class(s):
    if s > 26: return "num"
    if 20 < s < 23: return "q"
    if 17 < s < 20: return "a"
    return None

events = []
hashes = collections.Counter()
with pdfplumber.open(sys.argv[1]) as pdf:
    for pi, p in enumerate(pdf.pages):
        for cls in ("num", "q", "a"):
            sub = p.filter(lambda o, c=cls: o.get("object_type") != "char" or size_class(o["size"]) == c)
            for l in sub.extract_text_lines():
                events.append((pi, l["top"], l["x0"], cls, l["text"].strip()))
        for im in p.images:
            if round(im["width"]) != 12: continue
            h = hashlib.md5(im["stream"].get_data()).hexdigest()[:8]
            hashes[h] += 1
            events.append((pi, im["top"], im["x0"], "img", h))
events.sort(key=lambda e: (e[0], e[1], e[2]))
print("icon hashes:", dict(hashes), file=sys.stderr)

qs, cur, opt = [], None, None
for pi, top, x0, cls, t in events:
    if cls == "num":
        cur = {"n": int(t), "q": "", "opts": []}; qs.append(cur); opt = None
    elif cls == "q":
        cur["q"] = (cur["q"] + " " + t).strip()
    elif cls == "a":
        m = OPT.match(t)
        if m:
            opt = {"t": m.group(2), "ok": None}; cur["opts"].append(opt)
        else:
            opt["t"] += " " + t
    elif cls == "img":
        if opt is None or opt["ok"] is not None:
            print("orphan icon q", cur and cur["n"], "page", pi + 1, file=sys.stderr); continue
        opt["ok"] = (t == CHECK)

out, bad = [], []
for q in qs:
    opts = [re.sub(r"\s+", " ", o["t"]).strip() for o in q["opts"]]
    ok = [i for i, o in enumerate(q["opts"]) if o["ok"]]
    if not q["q"] or len(opts) < 2 or not ok or any(o["ok"] is None for o in q["opts"]):
        bad.append(q["n"])
    out.append({"id": q["n"], "q": re.sub(r"\s+", " ", q["q"]), "options": opts, "correct": ok})
print("questions:", len(out), "bad:", bad, file=sys.stderr)
print("ids ok:", [q["id"] for q in out] == list(range(1, len(out) + 1)), file=sys.stderr)
print("multi-correct:", sum(len(q["correct"]) > 1 for q in out), file=sys.stderr)
json.dump(out, open(sys.argv[2], "w"), ensure_ascii=False, indent=1)
