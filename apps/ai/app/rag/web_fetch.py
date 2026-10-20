"""Bounded HTTP article fetcher. No browser, stealth or challenge bypass."""
import asyncio
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import time
from weakref import WeakKeyDictionary
from urllib.parse import urljoin,urlsplit
from urllib.robotparser import RobotFileParser

import httpx

AGENT='TIENSalonResearchBot'
ALLOWED_HOSTS={'www.alodokter.com','alodokter.com'}
_LAST_FETCH={}
_LOCKS=WeakKeyDictionary()


def allowed_url(url):
    parsed=urlsplit(url)
    return (parsed.scheme=='https' and parsed.hostname in ALLOWED_HOSTS
            and not parsed.username and not parsed.password and parsed.port in {None,443})


class ArticleText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack=[];self.body=[];self.article=[];self.main=[]

    def handle_starttag(self,tag,attrs):
        if tag not in {'br','img','hr','input','meta','link','source','wbr','area','base','embed','param','track','col'}:
            self.stack.append(tag)
        if tag in {'p','br','div','h1','h2','h3','li'}:self.handle_data('\n')

    def handle_endtag(self,tag):
        if tag in self.stack:
            at=len(self.stack)-1-self.stack[::-1].index(tag)
            self.stack=self.stack[:at]
        if tag in {'p','div','h1','h2','h3','li'}:self.handle_data('\n')

    def handle_data(self,text):
        if set(self.stack)&{'script','style','nav','header','footer','aside','form','noscript','svg'}:return
        if 'body' in self.stack:self.body.append(text)
        if 'main' in self.stack:self.main.append(text)
        if 'article' in self.stack:self.article.append(text)

    def text(self):
        parts=self.article or self.main or self.body
        return '\n'.join(' '.join(line.split()) for line in ''.join(parts).splitlines() if line.strip())


async def read_limited(client,url,limit):
    async with client.stream('GET',url) as response:
        content=bytearray()
        async for chunk in response.aiter_bytes():
            content.extend(chunk)
            if len(content)>limit:raise ValueError('HTTP content exceeds size limit')
        return response.status_code,dict(response.headers),bytes(content)


async def _fetch(url,client):
    for _ in range(4):
        if not allowed_url(url):raise ValueError('Web source or redirect is outside the HTTPS allowlist')
        parsed=urlsplit(url)
        robots_url=f'https://{parsed.netloc}/robots.txt'
        status,headers,raw=await read_limited(client,robots_url,256000)
        robots=RobotFileParser(robots_url)
        if status in {404,410}:
            robots.parse([])
        elif status==200 and 'html' not in headers.get('content-type','').casefold():
            robots.parse(raw.decode('utf-8',errors='replace').splitlines())
        else:
            raise ValueError('Robots rules unavailable; article not fetched')
        if not robots.can_fetch(AGENT,url):raise ValueError('Robots rules disallow article fetch')
        delay=max(1.5,float(robots.crawl_delay(AGENT) or robots.crawl_delay('*') or 0))
        rate=robots.request_rate(AGENT) or robots.request_rate('*')
        if rate and rate.requests:delay=max(delay,rate.seconds/rate.requests)
        if delay>10:raise ValueError('Robots crawl interval exceeds request budget')
        locks=_LOCKS.setdefault(asyncio.get_running_loop(),{})
        async with locks.setdefault(parsed.netloc,asyncio.Lock()):
            remaining=delay-(time.monotonic()-_LAST_FETCH.get(parsed.netloc,0))
            if remaining>0:await asyncio.sleep(remaining)
            _LAST_FETCH[parsed.netloc]=time.monotonic()
            status,headers,content=await read_limited(client,url,1500000)
        if status in {301,302,303,307,308}:
            url=urljoin(url,headers.get('location',''))
            continue  # Destination robots and allowlist checked before fetching it.
        if status!=200:raise ValueError('Article fetch failed: HTTP '+str(status))
        if 'html' not in headers.get('content-type','').casefold():raise ValueError('Expected HTML article')
        parser=ArticleText();parser.feed(content.decode('utf-8',errors='replace'))
        text=parser.text()
        if len(text)<100:raise ValueError('No substantive article text')
        if any(marker in text.casefold() for marker in ('verify you are human','checking your browser','access denied','just a moment...')):
            raise ValueError('Challenge or blocked page; no bypass attempted')
        return dict(text=text,url=url,fetched_at=datetime.now(timezone.utc).isoformat(),
                    robots_url=robots_url,robots_sha256=hashlib.sha256(raw).hexdigest(),
                    content_sha256=hashlib.sha256(content).hexdigest(),fetch_method='http_robots_checked',
                    review_status='external_unreviewed')
    raise ValueError('Too many article redirects')


async def fetch_article(url,*,client=None,timeout=12):
    if client is not None:return await asyncio.wait_for(_fetch(url,client),timeout)
    async with httpx.AsyncClient(timeout=8,follow_redirects=False,
        headers={'User-Agent':AGENT+'/1.0','Accept':'text/html,text/plain'}) as session:
        return await asyncio.wait_for(_fetch(url,session),timeout)
