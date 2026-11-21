#!/usr/bin/env python3
"""
select_evidence.py - Elige de cada cargo los logros que mejor responden a ESTE aviso.

El banco (facts/evidence.yaml) guarda todos los logros de cada trabajo. El CV
solo puede mostrar unos pocos por cargo. Este script rankea TODO el banco
contra lo que pide el aviso y decide que entra, para que la seleccion no
dependa de la memoria de quien redacta ni del orden en que se armo el CV.

Uso:
    python3 build/select_evidence.py out/<carpeta>/targets.yaml   # escribe evidence-log.md y selection.json
    python3 build/select_evidence.py --tags                       # vocabulario de capabilities

targets.yaml (lo escribe la Pasada 1, paso 4):
    application: "Bank of us, Program Officer"
    capabilities:            # etiquetas de evidence.yaml, peso 1 a 3
      program-coordination: 3
    max_per_role:            # opcional. Cupos por bloque (por defecto abajo)
      origin: 4
    bullet_budget: 12        # opcional. Vinetas en todo el CV (por defecto 12, lo aplica fit.py)
    include_roles: [fach]    # opcional. Roles `optional: true` que si entran
    prefer:  [id]            # opcional. Fuerza IN (decision de criterio, con motivo)
    exclude: [id]            # opcional. Fuerza OUT (decision de criterio, con motivo)

Unidades: dos logros con `merge_with` en evidence.yaml son una sola historia y
se escriben en una sola vineta. Compiten y ocupan cupo como una unidad.
`always_include: true` en evidence.yaml = el candidato pidio que aparezca siempre.
"""
import sys
import json
import difflib
from collections import Counter, defaultdict
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("Falta PyYAML:  pip3 install pyyaml")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from candidate import FACTS, NAME, NAME_NEVER, CV_STEM  # noqa: E402  private/ facts (see candidate.py)

# Cupos de vinetas por cargo segun su bloque. Los fija la regla de los 7 segundos
# (rules/cv.md), no la antiguedad. Chile carga la tesis del CV ("Venderse").
# Un rol concurrente no entra por defecto: se pide en targets.yaml si el aviso lo necesita.
# build/fit.py recorta despues si el CV pasa de 12 vinetas o de 2 paginas.
DEFAULT_CAPS = {"origin": 4, "australia": 2, "international": 1, "concurrent": 0, "academic": 0}
DEPTH_RANK = {"direct": 0, "transferable": 1, "adjacent": 2}

# Cobertura: cuando una unidad entra, las capabilities que cubre pesan esto para
# las siguientes. Evita llenar el CV con logros que prueban lo mismo.
DECAY = 0.5
NEAR_TIE = 1.0   # diferencia de ganancia por debajo de la cual se avisa empate


def load():
    ev = yaml.safe_load((FACTS / "evidence.yaml").read_text(encoding="utf-8"))["evidence"]
    rd = yaml.safe_load((FACTS / "roles.yaml").read_text(encoding="utf-8"))
    roles = {r["id"]: r for r in rd["roles"]}
    blocks = rd.get("experience_order", {}).get("blocks", [])
    return ev, roles, blocks


def group_of(role_id, roles):
    r = roles.get(role_id)
    if r is None:
        return "academic"
    if r.get("concurrent_with"):
        return "concurrent"
    return r.get("block", "academic")


def build_units(items):
    """Agrupa items unidos por merge_with (simetrico) en unidades."""
    parent = {e["id"]: e["id"] for e in items}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for e in items:
        m = e.get("merge_with")
        if m and m in parent:
            parent[find(e["id"])] = find(m)
    groups = defaultdict(list)
    for e in items:
        groups[find(e["id"])].append(e)
    return list(groups.values())


def main():
    ev, roles, blocks = load()
    verified = [e for e in ev if e.get("status") == "verified"]
    vocab = Counter(t for e in verified for t in (e.get("capabilities") or []))

    if "--tags" in sys.argv:
        for tag, n in vocab.most_common():
            print(f"{n:3d}  {tag}")
        return

    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        sys.exit(__doc__)
    tpath = Path(args[0])
    T = yaml.safe_load(tpath.read_text(encoding="utf-8")) or {}
    weights = T.get("capabilities") or {}
    caps = {**DEFAULT_CAPS, **(T.get("max_per_role") or {})}
    include = set(T.get("include_roles") or [])
    prefer, exclude = set(T.get("prefer") or []), set(T.get("exclude") or [])

    # Etiquetas pedidas que no existen: un error de tipeo dejaria logros fuera.
    for t in [t for t in weights if t not in vocab]:
        near = difflib.get_close_matches(t, vocab.keys(), n=3)
        print(f"AVISO: '{t}' no existe en evidence.yaml. Parecidas: {', '.join(near) or 'ninguna'}")

    pool = []
    for e in verified:
        r = roles.get(e.get("role"))
        if r and r.get("optional") and e.get("role") not in include:
            continue
        pool.append(e)

    units = []
    for members in build_units(pool):
        rid = members[0].get("role")
        tags = sorted({t for m in members for t in (m.get("capabilities") or []) if t in weights})
        units.append({
            "ids": [m["id"] for m in members],
            "role": rid,
            "group": group_of(rid, roles),
            "tags": tags,
            "base": sum(weights[t] for t in tags),
            "depth": min(DEPTH_RANK.get(m.get("match_depth_default"), 3) for m in members),
            "always": any(m.get("always_include") for m in members),
            "prefer": any(m["id"] in prefer for m in members),
            "exclude": any(m["id"] in exclude for m in members),
            "claim": " + ".join(m["claim"] for m in members),
        })

    order = {b: i for i, b in enumerate(blocks + ["concurrent", "academic"])}
    w = dict(weights)
    used = Counter()
    chosen = {}   # indice de unidad -> (ganancia al entrar, motivo)

    def gain(u):
        return sum(w[t] for t in u["tags"])

    def take(i, why):
        u = units[i]
        chosen[i] = (gain(u), why)
        used[u["role"]] += 1
        for t in u["tags"]:
            w[t] *= DECAY

    # 1. Obligatorios: lo que el candidato pidio siempre, y lo preferido en targets.yaml.
    for i, u in enumerate(units):
        if (u["always"] or u["prefer"]) and not u["exclude"]:
            take(i, "pedido por el candidato (always_include)" if u["always"] else "prefer en targets.yaml")

    # 2. Cobertura greedy: entra la unidad con mayor ganancia marginal con cupo.
    ties = {}
    while True:
        cands = []
        for i, u in enumerate(units):
            if i in chosen or u["exclude"] or used[u["role"]] >= caps.get(u["group"], 0):
                continue
            g = gain(u)
            if g > 0:
                cands.append((g, -order.get(u["group"], 99), -u["depth"], -i, i))
        if not cands:
            break
        cands.sort(reverse=True)
        best = cands[0]
        rivals = [c for c in cands[1:] if units[c[4]]["role"] == units[best[4]]["role"] and best[0] - c[0] < NEAR_TIE]
        if rivals:
            ties[best[4]] = [units[c[4]]["ids"] for c in rivals]
        take(best[4], "seleccion por cobertura")

    # Un empate solo importa si el rival termino fuera.
    ties = {i: [r for r in rs if not any(set(r) == set(units[j]['ids']) for j in chosen)]
            for i, rs in ties.items()}
    ties = {i: rs for i, rs in ties.items() if rs}

    # ---- evidence-log.md (para el candidato) ----
    role_ids = sorted({u["role"] for u in units},
                      key=lambda rid: (order.get(group_of(rid, roles), 99), str(rid)))
    lines = [f"# Evidence log: {T.get('application', tpath.parent.name)}", "",
             "Todo el banco verificado, rankeado contra lo que pide el aviso.",
             "IN = entra al CV. OUT = queda en el banco, con el motivo.",
             f"Cobertura: cada capability ya cubierta pesa x{DECAY} para la unidad siguiente.", "",
             "Pesos del aviso: " + ", ".join(f"{t} {x}" for t, x in sorted(weights.items(), key=lambda x: -x[1])), ""]
    for rid in role_ids:
        grp = group_of(rid, roles)
        title = roles[rid]["title_on_documents"] if rid in roles else f"{rid} (academico)"
        lines += [f"## {title}  [{grp}, cupo {caps.get(grp, 0)}]", ""]
        mine = [i for i, u in enumerate(units) if u["role"] == rid]
        mine.sort(key=lambda i: (i not in chosen, -chosen.get(i, (0,))[0], -units[i]["base"]))
        for i in mine:
            u = units[i]
            if i in chosen:
                state, why = "IN ", f"{chosen[i][1]}, ganancia {chosen[i][0]:.1f}"
            elif u["exclude"]:
                state, why = "OUT", "exclude en targets.yaml"
            elif u["base"] == 0:
                state, why = "OUT", "no toca nada de lo que pide el aviso"
            elif caps.get(grp, 0) == 0:
                state, why = "OUT", "sin seccion en el CV para este grupo"
            else:
                state, why = "OUT", "fuera de cupo: otras unidades del cargo aportan mas"
            lines.append(f"- **{state}** `{u['base']:2d}` `{' + '.join(u['ids'])}`")
            lines.append(f"  - {u['claim'][:150]}")
            lines.append(f"  - coincide con: {', '.join(u['tags']) or '-'}. {why}")
            if i in ties:
                lines.append(f"  - **EMPATE** con {ties[i]}: decision de criterio. Fijarla con prefer/exclude en targets.yaml.")
        lines.append("")
    (tpath.parent / "evidence-log.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    # ---- selection.json (para fit.py y para quien redacta) ----
    sel = {"application": T.get("application"), "bullet_budget": T.get("bullet_budget"), "units": [
        {"ids": units[i]["ids"], "role": units[i]["role"], "gain": round(chosen[i][0], 2),
         "always": units[i]["always"] or units[i]["prefer"]}
        for i in sorted(chosen, key=lambda i: -chosen[i][0])]}
    (tpath.parent / "selection.json").write_text(json.dumps(sel, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    for rid in role_ids:
        title = roles[rid]["title_on_documents"] if rid in roles else f"{rid} (academico)"
        ins = [" + ".join(units[i]["ids"]) for i in sorted(chosen, key=lambda i: -chosen[i][0]) if units[i]["role"] == rid]
        n = sum(1 for u in units if u["role"] == rid)
        print(f"{title:30s} unidades={n:2d} entran={len(ins)}  {' | '.join(ins)}")
    if ties:
        print(f"\n{len(ties)} empate(s) marcados en el log: decision de criterio.")
    print(f"\nDetalle: {tpath.parent / 'evidence-log.md'}  |  para fit.py: {tpath.parent / 'selection.json'}")


if __name__ == "__main__":
    main()
