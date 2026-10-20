"""Bounded live-catalog smoke checks. Optional two ChatGPT generations, no paid fallback."""
import argparse
import asyncio
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import time

import httpx

from app.config import settings
from app.rag.rag_service import RagService
from app.rag.live_services import load_services


def implementation_hashes():
    return {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(__file__).parent.glob('*.py')}


async def run(allow_model=False,check_proxy=False):
    software=implementation_hashes()
    records=await load_services()
    by_name={d['fields']['name']:d for d in records}
    first=by_name['Signature Hair Spa']['fields']
    blowout=by_name['Volume Blowout Styling']['fields']
    money=lambda value:'Rp'+f'{value:,}'.replace(',','.')
    cases=[
        ('single','Berapa harga dan durasi Volume Blowout Styling?','catalog_lookup',[money(blowout['price']),str(blowout['duration_min'])+' menit']),
        ('all','Sebutkan semua layanan yang tersedia di salon.','catalog_lookup',list(by_name)),
        ('count','Berapa jumlah layanan yang tersedia?','catalog_lookup',[f'**{len(records)} layanan**']),
        ('filter','Apa saja layanan dengan harga di bawah Rp300.000?','catalog_lookup',[]),
        ('comparison','Apa perbedaan harga reguler dan durasi Signature Hair Spa dibanding Scalp Detox Therapy?','catalog_lookup',[money(first['price']),money(by_name['Scalp Detox Therapy']['fields']['price'])]),
        ('ambiguous','Berapa biaya treatment itu?','policy_clarification',['yang mana']),
        ('prescription','Berapa dosis obat resep untuk ketombe?','policy_unavailable',['tidak dapat menentukan dosis','dokter']),
        ('aftercare','Setelah keratin boleh keramas kapan?','policy_unavailable',['belum dapat memastikan']),
        ('confidential','Merek keratin apa yang digunakan TIEN salon?','policy_unavailable',['tidak dipublikasikan']),
        ('unsupported','Bagaimana lintasan quasar intergalaktik?','policy_unavailable',['belum menemukan sumber']),
        ('history','Berapa harga keratin kemarin?','policy_unavailable',['Riwayat perubahan harga belum tersedia']),
        ('discount','Apakah ada diskon Signature Hair Spa?','policy_unavailable',['Informasi promo, diskon']),
        ('quoted_price','Apakah Keratin Smooth Treatment masih Rp690.000?','policy_unavailable',['Rp780.000','belum tersedia'])]
    if allow_model:
        cases += [('mixed','Berapa harga Signature Hair Spa dan bagaimana memakai kondisioner untuk rambut kering?','llm_success',[money(first['price'])]),
                  ('care','Bagaimana membatasi panas saat styling rambut?','llm_success',[])]
    service=RagService();results=[]
    for name,query,expected,substrings in cases:
        start=time.perf_counter()
        response=await service.answer(query,live_services=True,allow_web=False,include_trace=True)
        trace=response['_trace']
        checks=dict(execution_route=trace['generation_status']==expected,
                    required_literal_facts=all(term.casefold() in response['reply'].casefold() for term in substrings))
        if name=='filter':
            summary=json.loads(response['sources'][0]['snippet'])
            checks['filter_ids']=set(summary['matched_ids'])=={d['id'] for d in records if d['fields']['price']<300000}
        if expected=='llm_success':
            checks['has_attributed_source']=bool(response['sources'])
            checks['no_invalid_citation_indices']=not trace.get('citations',{}).get('invalid_citation_indices')
        if name=='mixed':
            checks['business_and_document_sources']=any(s['id']=='live:services:1' for s in response['sources']) and any(s['id'].startswith('care:') for s in response['sources'])
        results.append(dict(id=name,question=query,passed=all(checks.values()),checks=checks,
                            elapsed_seconds=time.perf_counter()-start,**response))
        print(json.dumps(dict(id=name,passed=results[-1]['passed'],generation_status=trace['generation_status'])),flush=True)
    proxy=[]
    if check_proxy:
        async with httpx.AsyncClient(timeout=80) as client:
            for query in (cases[0][1],cases[5][1],cases[6][1],cases[7][1]):
                start=time.perf_counter()
                response=await client.post(settings.api_base_url.rstrip('/')+'/api/chat',json={'message':query})
                data=response.json().get('data',{}) if response.status_code==200 else {}
                proxy.append(dict(question=query,status_code=response.status_code,
                                  passed=response.status_code==200 and bool(data.get('reply')),
                                  response=data,elapsed_seconds=time.perf_counter()-start))
    from app.rag.experiment_ir import rss_bytes
    if implementation_hashes()!=software:raise ValueError('Implementation changed during smoke checks')
    return dict(executed_at_utc=datetime.now(timezone.utc).isoformat(),
        status='checks_passed' if all(r['passed'] for r in results+proxy) else 'checks_failed',
        tests=len(results)+len(proxy),passed=sum(r['passed'] for r in results+proxy),
        model_calls_requested=2 if allow_model else 0,
        llm_successes=sum(r['_trace']['generation_status']=='llm_success' for r in results),
        business_source='live API; database not modified',initial_catalog=records,
        process_rss_after_checks_bytes=rss_bytes(),results=results,proxy_results=proxy,
        independent_citation_entailment_verified=False,
        answer_quality_benchmark=False,publication_ready=False,
        implementation_sha256=software,
        limitations=['Automatic route/literal-fact/source checks, not human semantic annotations.',
                     'Live data can change; initial catalog captured for interpreting literal checks.',
                     'No web crawl during smoke; HTTP robots behavior covered separately by mocked tests.',
                     'RSS is this local Python smoke process, not the API server peak or deployment performance.'])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--allow-model',action='store_true')
    parser.add_argument('--check-proxy',action='store_true')
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    if args.out.exists():parser.error('Use a new report file')
    report=asyncio.run(run(args.allow_model,args.check_proxy))
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_bytes((json.dumps(report,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
    print(json.dumps({k:report[k] for k in ('status','tests','passed','llm_successes')},indent=2))
    if report['status']!='checks_passed':raise SystemExit(2)


if __name__=='__main__':main()
