"""Download openly available publisher PDFs and record provenance and failures."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urljoin, urlparse
import csv
import hashlib
import json
import re
import threading
import requests
from bs4 import BeautifulSoup
import pymupdf

ROOT = Path(__file__).resolve().parent
PAPERS = [
 (1,2026,'Design and Evaluation of a Retrieval-Augmented Generation LLM Chatbot with Structured Database Access','https://www.mdpi.com/2076-3417/16/7/3147'),
 (2,2024,'Design and Implementation of an Interactive Question-Answering System with Retrieval-Augmented Generation for Personalized Databases','https://www.mdpi.com/2076-3417/14/17/7995'),
 (3,2026,'Dual-Source Retrieval-Augmented Generation Chatbot for Women s Health HerCare Design and Multimethod Evaluation Study','https://formative.jmir.org/2026/1/e88549'),
 (4,2025,'Lisa a touristic chatbot for Lisbon','https://link.springer.com/article/10.1007/s40558-025-00339-x'),
 (5,2025,'RAGVA Engineering retrieval augmented generation-based virtual assistants in practice','https://doi.org/10.1016/j.jss.2025.112436'),
 (6,2026,'Design of a RAG-Based Customer Service Chatbot Enhanced with Knowledge Graph and GPT Evaluation','https://www.mdpi.com/2674-113X/5/2/15'),
 (7,2025,'Design and Performance Evaluation of LLM-Based RAG Pipelines for Chatbot Services in International Student Admissions','https://www.mdpi.com/2079-9292/14/15/3095'),
 (8,2026,'Implementation of Retrieval-Augmented Generation Method on Large Language Model for Development of Campus Service and Information Chatbot','https://jurnal.polbeng.ac.id/index.php/ISI/article/view/1484'),
 (9,2026,'Citation Graph-Based Multi-Hop Retrieval Optimization Using Hybrid RRF in a RAG System for Indonesian ITE Law Documents','https://jurnal.polibatam.ac.id/index.php/JAIC/article/view/14131'),
 (10,2026,'SES-RAG An Adaptive Framework with ModernBERT Segmentation and Generative-Alignment Expansion','https://www.mdpi.com/2076-3417/16/10/4849'),
 (11,2026,'TechDocRAG Relation-Preserving Retrieval-Augmented Generation for Technical Documents','https://www.mdpi.com/2673-2688/7/5/161'),
 (12,2026,'Evaluating LLM-Based Retrieval-Augmented Generation for Soil Science Question Answering','https://www.mdpi.com/2078-2489/17/9/859'),
 (13,2026,'Efficacy Evaluation and Optimization of RAG Knowledge Bases in the Oil and Gas Industry Using an LLM-as-a-Judge Mechanism','https://www.mdpi.com/1996-1073/19/17/4207'),
 (14,2026,'Dual index retrieval augmented generation for pedagogically aligned mathematics problem solving support','https://link.springer.com/article/10.1007/s10791-026-10432-2'),
 (15,2024,'BiomedRAG A retrieval augmented large language model for biomedicine','https://www.sciencedirect.com/science/article/pii/S1532046424001874'),
 (16,2025,'Retrieval-Augmented Generation Chatbot for Handling Customer Complaints in the Energy Sector','https://e-jurnal.pnl.ac.id/infomedia/article/view/7169'),
 (17,2026,'Implementation of Retrieval-Augmented Generation Based Chatbot for Export Company Customer Service Automation','https://ejournal.kresnamediapublisher.com/index.php/jri/article/view/590'),
 (18,2025,'Development and Evaluation of a Retrieval-Augmented Generation Chatbot for Orthopedic and Trauma Surgery Patient Education','https://ai.jmir.org/2025/1/e75262'),
 (19,2026,'Evaluating Retrieval Augmented Generation A Comprehensive Review of Evaluation Dimensions Question Types and Application','https://link.springer.com/article/10.1007/s42979-026-05134-x'),
 (20,2026,'Retrieval-augmented generation for natural language processing a survey','https://link.springer.com/article/10.1007/s10462-026-11605-7'),
 (21,2025,'A Systematic Literature Review of Retrieval-Augmented Generation Techniques Metrics and Challenges','https://www.mdpi.com/2504-2289/9/12/320'),
 (22,2026,'A Survey of conversational AI from rule based to generative and retrieval augmented generation chatbots','https://link.springer.com/article/10.1007/s44163-026-02373-y'),
 (23,2025,'A survey on retrieval-augmentation generation models for healthcare applications','https://link.springer.com/article/10.1007/s00521-025-11666-9'),
 (24,2025,'Retrieval-augmented generation for educational application A systematic survey','https://doi.org/10.1016/j.caeai.2025.100417'),
 (25,2025,'Retrieval-Augmented Generation','https://link.springer.com/article/10.1007/s12599-025-00945-3'),
 (26,2024,'RAGAs Automated Evaluation of Retrieval Augmented Generation','https://aclanthology.org/2024.eacl-demo.16/'),
 (27,2023,'Enabling Large Language Models to Generate Text with Citations','https://aclanthology.org/2023.emnlp-main.398/'),
]

locks = {}
for *_, url in PAPERS:
    locks.setdefault(urlparse(url).netloc, threading.Lock())

def download(paper):
    number, year, title, source = paper
    result = dict(number=number, year=year, title=title, source_url=source,
                  kind='conference' if number >= 26 else 'journal', status='unavailable',
                  filename='', pdf_url='', pages=0, sha256='', publisher_title='', attempts=[])
    slug = re.sub(r'[^A-Za-z0-9]+','-', title).strip('-')[:125]
    dest = ROOT / f'{number:02d}_{year}_{slug}.pdf'
    session = requests.Session()
    queue = [source]
    mdpi_assets = {
        1:('applsci','16','03147'),2:('applsci','14','07995'),
        6:('software','5','00015'),7:('electronics','14','03095'),
        10:('applsci','16','04849'),11:('ai','7','00161'),
        12:('information','17','00859'),13:('energies','19','04207'),
        21:('bdcc','9','00320'),
    }
    if number in mdpi_assets:
        journal, volume, article = mdpi_assets[number]
        stem=f'{journal}-{int(volume):02d}-{article}'
        queue.insert(0,f'https://mdpi-res.com/d_attachment/{journal}/{stem}/article_deploy/{stem}.pdf')
        queue.append(source.rstrip('/')+'/pdf')
    if number == 17:
        queue.insert(0,'https://ejournal.kresnamediapublisher.com/index.php/jri/article/download/590/432')
    if 'aclanthology.org' in source:
        queue.insert(0, source.rstrip('/')+'.pdf')
    if 'link.springer.com/article/' in source:
        queue.insert(0,source.replace('/article/','/content/pdf/')+'.pdf?download=1')
    if 'jmir.org/' in source:
        queue.insert(0,source.rstrip('/')+'/PDF?download=1')
        queue.append(source.rstrip('/')+'/PDF')
    seen = set()
    with locks[urlparse(source).netloc]:
        while queue and len(seen) < 7:
            url = queue.pop(0)
            if url in seen:
                continue
            seen.add(url)
            try:
                response = session.get(url,timeout=(15,40))
                result['attempts'].append({'url':url,'http_status':response.status_code})
                if not response.ok:
                    continue
                if response.content[:5] == b'%PDF-':
                    with pymupdf.open(stream=response.content,filetype='pdf') as doc:
                        if doc.is_encrypted or not len(doc):
                            continue
                        result['pages'] = len(doc)
                        result['first_page_excerpt'] = doc[0].get_text()[:1800]
                    dest.write_bytes(response.content)
                    result.update(status='downloaded',filename=dest.name,pdf_url=response.url,
                                  sha256=hashlib.sha256(response.content).hexdigest())
                    break
                soup = BeautifulSoup(response.text,'html.parser')
                if url == source:
                    result['publisher_title'] = soup.title.get_text(' ',strip=True) if soup.title else ''
                    result['publisher_publication_dates'] = [m.get('content','') for m in soup.find_all('meta')
                        if m.get('name','').lower() in ('citation_publication_date','citation_date','dc.date.issued')]
                candidates = []
                for meta in soup.find_all('meta'):
                    if meta.get('name','').lower() in ('citation_pdf_url','eprints.document_url') and meta.get('content'):
                        candidates.append(urljoin(response.url,meta['content']))
                for element in soup.select('a[href], iframe[src], embed[src], object[data]'):
                    href = element.get('href') or element.get('src') or element.get('data')
                    text = element.get_text(' ',strip=True).lower()
                    if href and ('.pdf' in href.lower() or '/article/download/' in href or
                                 ('pdf' in text and ('/article/view/' in href or 'download' in href))):
                        candidates.append(urljoin(response.url,href))
                # Normal public publisher PDF endpoint; never authenticate or bypass a paywall.
                if 'mdpi.com/' in response.url and url == source:
                    candidates.append(response.url.rstrip('/')+'/pdf')
                for candidate in dict.fromkeys(candidates):
                    host = urlparse(candidate).netloc.lower()
                    if any(bad in host for bad in ('arxiv.org','researchgate.net','sci-hub')):
                        continue
                    if candidate not in seen and candidate not in queue:
                        queue.append(candidate)
            except Exception as exc:
                result['attempts'].append({'url':url,'error':str(exc)[:250]})
    print(f'{number:02d}: {result["status"]} ({result["pages"]} pages)',flush=True)
    return result

def main():
    old=json.loads((ROOT/'manifest.json').read_text(encoding='utf-8')) if (ROOT/'manifest.json').exists() else []
    results=[r for r in old if r['status']=='downloaded' and (ROOT/r['filename']).exists()]
    done={r['number'] for r in results}
    with ThreadPoolExecutor(max_workers=4) as pool:
        for future in as_completed([pool.submit(download,p) for p in PAPERS if p[0] not in done]):
            results.append(future.result())
            (ROOT/'manifest.json').write_text(json.dumps(sorted(results,key=lambda x:x['number']),ensure_ascii=False,indent=2),encoding='utf-8')
    results.sort(key=lambda x:x['number'])
    with (ROOT/'manifest.csv').open('w',encoding='utf-8-sig',newline='') as f:
        fields=['number','year','title','kind','status','filename','source_url','pdf_url','pages','sha256']
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(results)
    count=sum(x['status']=='downloaded' for x in results)
    lines=['# Unduhan paper RAG 2021–2026','', 'Tanggal pengambilan: 20 Oktober 2026.',
           f'PDF berhasil diunduh: {count}/{len(results)}. Sumber: situs penerbit/jurnal asli.',
           'PDF diperiksa dapat dibuka; jumlah halaman dan SHA256 tersimpan dalam manifest.',
           'Tahun awal berasal dari daftar penelusuran; metadata penerbit dan tanggal yang ditemukan dicatat dalam manifest.json.',
           'Status unavailable menunjukkan unduhan belum tersedia melalui permintaan publik yang dicoba; bukan otomatis berarti berbayar.',
           'Tidak ada preprint atau akses melewati paywall yang digunakan.','',
           '| No. | Tahun | Judul | Status | Sumber |','|---|---|---|---|---|']
    lines += [f'| {r["number"]} | {r["year"]} | {r["title"]} | {r["status"]} | [Penerbit]({r["source_url"]}) |' for r in results]
    (ROOT/'README.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(f'COMPLETE: {count}/{len(results)} downloaded',flush=True)

if __name__ == '__main__':
    main()
