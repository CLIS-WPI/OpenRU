import json,sys,re
d=json.load(open('nl.json')); C=d['comps']; N=d['nets']
def short(n): return n.split('/')[-1]
pats=sys.argv[1:]
for name,nodes in sorted(N.items()):
    if any(re.search(p,name) for p in pats):
        print('NET',name)
        for r,p,f,ty in nodes:
            v=C.get(r,('','',''))
            print('   %s.%s(%s,%s) %s %s'%(r,p,f,ty,v[0],v[2]))
