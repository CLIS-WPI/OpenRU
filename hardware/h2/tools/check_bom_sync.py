"""Check every schematic MPN field against FIXTURE_BOM.csv. Usage: python3 -I check_bom_sync.py <netlist.xml> <bom.csv>"""
import re, sys, csv, xml.etree.ElementTree as ET
r = ET.parse(sys.argv[1]).getroot()
sch = {c.get('ref'): {x.get('name'): x.text for x in c.iter('field')}.get('MPN') for c in r.iter('comp')}
bom = {ref: row for row in csv.DictReader(open(sys.argv[2])) for ref in row['ref'].split()
       if re.fullmatch(r'[A-Z]+\d+', ref) and not row['MPN'].startswith('PCB pad')}  # skip summary rows and bare pads
bad = [(k, sch.get(k), v['MPN']) for k, v in bom.items() if sch.get(k) != v['MPN']]
extra = sorted(k for k in set(sch) - set(bom) if not k.startswith('TP'))
print(f"{len(sch)} schematic parts, {len(bom)} BOM refs; MPN mismatches: {bad}; in schematic but not in BOM: {extra}")
sys.exit(1 if bad or extra else 0)
