import json, sys

def byte_len(s):
    return sum(2 if ord(c) > 127 else 1 for c in s)

decisions = json.load(open(sys.argv[1] if len(sys.argv) > 1 else '/tmp/11st_ai_decisions.json', encoding='utf-8'))
bad = []
for d in decisions:
    nb = byte_len(d['product_name'])
    pc = len(d['promo_text'])
    ok = nb <= 50 and pc <= 20
    print(f"{d['prd_no']} | name={nb}byte promo={pc}char {'OK' if ok else '!! 초과'} | {d['product_name']}")
    if not ok:
        bad.append(d['prd_no'])
print()
print(f"검증 완료: {len(decisions)}건, 초과 {len(bad)}건", bad)
