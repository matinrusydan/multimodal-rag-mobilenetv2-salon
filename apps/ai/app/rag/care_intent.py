"""Explicit product distinctions; never infer a product type from ranking."""
import re


CONDITIONER=re.compile(r'\b(?:kondisioner|conditioner|konditioner|pelembap rambut)\b',re.I)
LEAVE_IN=re.compile(r'\bleave[\s-]?in\b|\b(?:tanpa|tidak perlu|tidak usah|tidak)\s+(?:di)?bilas\b',re.I)
RINSE=re.compile(r'\b(?:kondisioner|conditioner)\s+bilas\b|\byang\s+(?:perlu\s+)?dibilas\b|\brinse[\s-]?out\b',re.I)


def conditioner_kind(query):
    if re.search(r'\b(?:bukan|jangan)\s+(?:leave[\s-]?in|kondisioner bilas|conditioner bilas)\b',query,re.I):
        return 'unspecified'
    if CONDITIONER.search(query) and re.search(r'\b(?:apakah|perlukah|haruskah|bolehkah)\b',query,re.I) and re.search(r'\bdibilas\b',query,re.I):
        explicit=re.search(r'\bleave[\s-]?in\b|\btanpa bilas\b|\b(?:kondisioner|conditioner) bilas\b|\brinse[\s-]?out\b',query,re.I)
        if not explicit:return 'unspecified'
    leave=bool(LEAVE_IN.search(query));rinse=bool(RINSE.search(query))
    if leave and rinse:return 'both'
    if leave:return 'leave_in'
    if rinse:return 'rinse_out'
    return 'unspecified' if CONDITIONER.search(query) else None


def conditioner_clarification(query):
    if conditioner_kind(query)!='unspecified':return None
    # Descriptive comparisons can explain both kinds rather than choose one.
    if re.search(r'\b(?:perbedaan|bedanya|jenis|macam|apa itu|pengertian)\b',query,re.I):return None
    return dict(rule='conditioner_type_unspecified',reply=
        'Kondisioner yang Anda maksud **kondisioner bilas** atau **leave-in/tanpa bilas**? '
        'Petunjuk pemakaiannya perlu dibedakan. Tulis jenisnya dalam pertanyaan berikutnya, '
        'misalnya “Bagaimana memakai kondisioner bilas untuk rambut kering?” '
        'atau “Bagaimana memakai leave-in untuk rambut keriting?”.')


def unresolved_reference(query,known_service=False):
    product=re.search(r'\b(?:produk|krim|sampo|shampoo)\s+(?:ini|itu|tadi|tersebut)\b',query,re.I)
    service=re.search(r'\b(?:treatment|layanan|perawatan)\s+(?:ini|itu|tadi|tersebut)\b',query,re.I)
    if product:
        return dict(rule='product_reference_unspecified',reply=
            'Produk yang Anda maksud yang mana? Sebutkan jenis produk dan petunjuk pemakaian pada kemasannya '
            'yang ingin ditanyakan. Saya belum dapat memastikan cara pakai atau kecocokannya hanya dari sebutan “produk ini/itu”. '
            'Anda tidak perlu menyebut merek produk internal TIEN SALON.')
    if service and not known_service:
        return dict(rule='service_reference_unspecified',reply=
            'Layanan atau treatment yang Anda maksud yang mana? Sebutkan nama layanan dalam pertanyaan '
            'agar petunjuknya tidak tertukar. Untuk instruksi setelah treatment, konfirmasikan kepada staf yang menangani.')
    return None


def operational_care_query(query):
    """Expand terminology only in the operational selector profile, not BM25 baseline."""
    normalized=CONDITIONER.sub('kondisioner',query)
    if conditioner_kind(query) in {'leave_in','both'}:
        normalized+=' leave-in conditioner'
    elif CONDITIONER.search(query) and re.search(r'\b(?:perbedaan|bedanya|jenis|macam|apa itu|pengertian)\b',query,re.I):
        normalized+=' conditioner leave-in'
    return normalized


def compatible_product_evidence(query,document):
    if document.get('source_type')=='db':return True
    kind=conditioner_kind(query)
    if kind not in {'rinse_out','leave_in'}:return True
    section=document.get('section','')
    text=document.get('text','')
    is_leave=bool(LEAVE_IN.search(section))
    if kind=='rinse_out' and is_leave:return False
    # A general conditioner application excerpt cannot establish leave-in instructions.
    if kind=='leave_in' and CONDITIONER.search(section+' '+text) and not LEAVE_IN.search(section+' '+text):return False
    return True
