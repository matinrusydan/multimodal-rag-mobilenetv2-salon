"""Responses streaming via the app's own ChatGPT-plan grant; no paid-key fallback."""
from __future__ import annotations
import asyncio,json
import httpx
from app import chatgpt_auth
from app.config import settings


def available():
    profile=chatgpt_auth.load()
    return bool(profile.get('access_token') and chatgpt_auth.PLAN_SCOPE in profile.get('scopes',[]))


def output_text(response):
    return '\n'.join(c.get('text','') for item in response.get('output',[]) if item.get('type')=='message'
                     for c in item.get('content',[]) if c.get('type')=='output_text').strip()


async def response(input_items, *, model=None, tools=None, max_tokens=900):
    chosen=model or settings.chatgpt_model
    if not chosen:raise RuntimeError('Pilih AI_CHATGPT_MODEL dari python -m app.chatgpt_auth models')
    token=await asyncio.to_thread(chatgpt_auth.access_token)
    # Plan-usage preview rejects max_output_tokens and system message items.
    # max_tokens remains a caller hint only; provider does not promise a hard cap.
    items=[{**item,'role':'developer'} if item.get('role')=='system' else item for item in input_items]
    payload={'model':chosen,'input':items,'store':False,'stream':True}
    if tools:payload['tools']=[{'type':'namespace','name':'salon','description':'Read salon operational summaries','tools':tools}]
    completed=None
    text_deltas=[]
    done_items=[]
    async with httpx.AsyncClient(timeout=httpx.Timeout(60,connect=15)) as client:
        async with client.stream('POST',chatgpt_auth.RESOURCE+'/responses',
                                 headers={'Authorization':'Bearer '+token},json=payload) as stream:
            if stream.status_code>=400:
                raise RuntimeError('ChatGPT plan request failed (HTTP '+str(stream.status_code)+'); no paid fallback')
            async for line in stream.aiter_lines():
                if not line.startswith('data:'):continue
                value=line[5:].strip()
                if not value or value=='[DONE]':continue
                event=json.loads(value)
                if event.get('type')=='response.output_text.delta':
                    text_deltas.append(event.get('delta',''))
                if event.get('type')=='response.output_item.done' and isinstance(event.get('item'),dict):
                    done_items.append(event['item'])
                if event.get('type') in {'error','response.failed','response.incomplete'}:
                    raise RuntimeError('ChatGPT response did not complete')
                if event.get('type')=='response.completed':completed=event.get('response')
    if not completed or completed.get('status')!='completed':raise RuntimeError('ChatGPT stream ended without completed response')
    # Some streaming servers do not repeat completed output items in the final
    # envelope. Use emitted items/text only after completion is confirmed.
    if not completed.get('output') and done_items:
        completed={**completed,'output':done_items}
    if not output_text(completed) and text_deltas:
        completed={**completed,'output':[*completed.get('output',[]),
                    {'type':'message','role':'assistant','content':[{'type':'output_text','text':''.join(text_deltas)}]}]}
    return completed


async def generate(messages, *, model=None, max_tokens=900):
    result=await response(messages,model=model,max_tokens=max_tokens)
    text=output_text(result)
    if not text:raise RuntimeError('ChatGPT completed without answer text')
    return text
