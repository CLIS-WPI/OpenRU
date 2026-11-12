import sys, xml.etree.ElementTree as ET, re
t=ET.parse(sys.argv[1]).getroot()
comps={}
for c in t.find('components'):
    ref=c.get('ref'); val=c.findtext('value'); 
    fields={f.get('name'):f.text for f in c.iter('field')}
    lib=c.find('libsource'); comps[ref]=(val, lib.get('lib')+':'+lib.get('part') if lib is not None else '', fields.get('MPN',''))
nets={}; pinnet={}
for n in t.find('nets'):
    name=n.get('name'); nodes=[(x.get('ref'),x.get('pin'),x.get('pinfunction') or '',x.get('pintype') or '') for x in n]
    nets[name]=nodes
    for r,p,f,ty in nodes: pinnet[(r,p)]=(name,f,ty)
import json
json.dump({'comps':comps,'nets':nets},open(sys.argv[2],'w'))
print(len(comps),len(nets))
