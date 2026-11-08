"""
C1–C3 del pre-registro de 2024 (§8) con la versión C: C2 = caída máxima ≥ 40 % en 12 meses con la alerta roja de
valoración extrema frente a sin ella; C3 = acierto de dirección (barata que bate a su ETF de sector o cara que queda
por detrás, a 12 m) por consistencia. mdd_12m de datos_reales va en % positivo.

    python3 tests/hacia_atras/c123.py <evidencias> <universo.tsv> '{"BK": "BNY", ...}' simbolo_2024 > c123.json
"""
import json,gzip,os,csv,sys
E=sys.argv[1]; U=sys.argv[2]; AL=json.loads(sys.argv[3]); col=sys.argv[4]
rr={r[col]:r for r in csv.DictReader(open(f"{E}/datos_reales/resultados_reales.csv"))}
def f(x):
    try: return float(x)
    except: return None
out={}
for grp in ("control","110"):
    syms=[r["symbol"] for r in csv.DictReader(open(U),delimiter="\t") if r["grupo"]==grp]
    con=sin=hc=hs=0; cons={"consistente":[0,0],"mixta":[0,0]}; lst=[]
    for s in syms:
        d=AL.get(s,s); p=f"{E}/corridas/C/{d}.json.gz"
        if not os.path.exists(p): continue
        a=json.load(gzip.open(p))
        if "__http_error__" in a: continue
        r=rr.get(s) or {}
        mdd=f(r.get("mdd_12m")); rel=f(r.get("rel_12m"))
        red=any("valoración extrema" in (x.get("reason") or "") for x in (a.get("alerts") or {}).get("red_flags") or [])
        if mdd is not None:
            big=mdd>=40.0   # mdd_12m en % positivo
            if red: con+=1; hc+=big; lst.append((d,round(mdd,3)))
            else: sin+=1; hs+=big
        v=a.get("verdict") or {}; lvl=v.get("price_level"); c=v.get("consistency")
        if c in cons and rel is not None and lvl in ("atractivo","exigente"):
            ok=(rel>0) if lvl=="atractivo" else (rel<0)
            cons[c][0]+=1; cons[c][1]+=ok
    out[grp]={"C2":{"con_alerta":con,"caidas_con":hc,"frec_con":hc/con if con else None,"sin_alerta":sin,"caidas_sin":hs,"frec_sin":hs/sin if sin else None,"empresas":lst},
              "C3":{k:{"n":v[0],"acierto":(v[1]/v[0] if v[0] else None)} for k,v in cons.items()}}
print(json.dumps(out,ensure_ascii=False,indent=1))
