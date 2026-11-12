import json,sys
d=json.load(open('nl.json')); C=d['comps']; N=d['nets']
pins={}
for n,nodes in N.items():
    for r,p,f,ty in nodes: pins.setdefault(r,[]).append((p,f,n.split('/')[-1]))
for r in sys.argv[1:]:
    print(r, C.get(r), sorted(pins.get(r,[]), key=lambda x:(len(x[0]),x[0])))
