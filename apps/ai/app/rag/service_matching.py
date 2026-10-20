"""Resolve exact catalog names and unambiguous aliases; never guess a price."""
import re

ALIASES=('hair spa','haircut','keratin','scalp detox','color gloss','blowout')


def match_services(query, records):
    text=' '.join(query.casefold().split())
    selected=[]
    for record in records:
        name=record['fields']['name'].casefold()
        if re.search(r'(?<!\w)'+re.escape(name)+r'(?!\w)',text):
            selected.append(record)
    for alias in ALIASES:
        if re.search(r'(?<!\w)'+re.escape(alias)+r'(?!\w)',text):
            candidates=[d for d in records if alias in d['fields']['name'].casefold()]
            if len(candidates)==1 and candidates[0] not in selected:
                selected.append(candidates[0])
    return selected
