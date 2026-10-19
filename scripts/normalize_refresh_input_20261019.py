"""Normalize the OPC content-types namespace for the strict artifact reader.

This changes XML namespace serialization only, not worksheet content or features.
"""
import json,pathlib,zipfile,xml.etree.ElementTree as E
R=pathlib.Path(__file__).resolve().parents[1];P=R/'reports/deep_refresh_2026_10_19'
with zipfile.ZipFile(R/'Data.xlsx') as z:parts={n:z.read(n) for n in z.namelist()}
name='[Content_Types].xml';root=E.fromstring(parts[name]);ns='http://schemas.openxmlformats.org/package/2006/content-types'
E.register_namespace('',ns);parts[name]=E.tostring(root,encoding='utf-8',xml_declaration=True)
with zipfile.ZipFile(P/'staged/import.xlsx','w',zipfile.ZIP_DEFLATED) as z:
 for n,b in parts.items():z.writestr(n,b)
(P/'input_normalization.json').write_text(json.dumps({'part':name,'change':'default namespace serialization only; worksheet bytes unchanged'},indent=2),'utf-8')
print('Prepared import-compatible copy; worksheet contents unchanged.')
