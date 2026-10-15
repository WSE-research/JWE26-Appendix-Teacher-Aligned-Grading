#!/usr/bin/env python3
"""Read-only validation of this appendix repository; no analysis or network access."""
from pathlib import Path
from urllib.parse import unquote,urlparse
import csv,hashlib,json,re,sys
ROOT=Path(__file__).resolve().parents[1]
def check():
 manifest=json.loads((ROOT/'provenance.json').read_text())
 for name,digest in manifest['files'].items():
  p=ROOT/name
  assert p.is_file(),f'Missing file: {name}'
  assert hashlib.sha256(p.read_bytes()).hexdigest()==digest,f'Changed file: {name}'
 seen={p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*') if p.is_file() and '__pycache__' not in p.parts and '.git' not in p.parts and p!=ROOT/'provenance.json'}
 assert seen==set(manifest['files']),f'Inventory mismatch: {seen^set(manifest["files"])}'
 links=0
 for p in ROOT.rglob('*.md'):
  body=p.read_text()
  for target in re.findall(r'!?\[[^\n]*?\]\(([^)]+)\)',body):
   if urlparse(target).scheme:continue
   target=unquote(target);file,_,anchor=target.partition('#')
   dest=(p.parent/file).resolve() if file else p
   assert dest.is_relative_to(ROOT),f'Link escapes appendix: {p}: {target}'
   assert dest.exists(),f'Broken link: {p}: {target}'
   if anchor:
    assert re.search(r'<a id="'+re.escape(anchor)+r'"\s*>',dest.read_text()),f'Missing anchor: {p}: {target}'
   links+=1
 required={'01-predecessors.md':[], '02-source-comparisons.md':[], '04-methods.md':['a43','a44','a45','a46'], '05-teacher-alignment.md':['a51','a521','a524','a525'], '06-human-reference.md':[], '07-provenance.md':['a73']}
 for name,anchors in required.items():
  body=(ROOT/name).read_text()
  for anchor in anchors:assert f'<a id="{anchor}"></a>' in body,(name,anchor)
 for p in (ROOT/'tables').glob('*.csv'):
  rows=list(csv.reader(p.open(newline='')))
  assert rows and len(rows)>1,p
  assert len({len(r) for r in rows})==1,p
 schema=json.loads((ROOT/'prompts/judge-schema.json').read_text())
 assert schema['required']==['label','evidence'] and schema['additionalProperties'] is False
 assert schema['properties']['label']['enum']==['supports_correct','supports_incorrect','undetermined']
 assert not list(ROOT.glob('*.pdf')) and not list(ROOT.rglob('*.tex')),'PDF/TeX appendix entry point unexpectedly present'
 assert not any(p.name in ['labelling_pool.csv','partial_credit_adjudicated.csv'] or 'adjudication_protocol' in p.name for p in ROOT.rglob('*')),'Restricted-data file present'
 for p in [ROOT/'README.md',*ROOT.glob('0*.md')]:
  assert not re.search(r'PLACEHOLDER|\\(?:ArticleRef|claude|ref)\{|rare (?:for every|under)|&mdash;|—',p.read_text()),p
 print(json.dumps({'status':'PASS','files':len(seen),'local_links':links,'chapter_pages':7,'tables':len(list((ROOT/'tables').glob('*.csv'))),'diagram_figures':3,'analysis_source_files':len(list((ROOT/'reproduction').rglob('*.py'))),'raw_data_included':False},indent=2))
if __name__=='__main__':check()
