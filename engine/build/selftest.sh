#!/bin/bash
# selftest.sh - Demuestra que verify.py hace lo que dice, sin necesidad de leer Python.
#
# Uso:  bash build/selftest.sh
#
# Corre verify.py contra dos documentos de prueba y comprueba el resultado:
#   - cv-limpio.md          debe pasar (0 fallos)
#   - cv-con-violaciones.md debe detectar las 17 violaciones plantadas
# Y ats_check.py --selftest: un texto limpio pasa y cada fallo de lectura ATS
# plantado (ligaduras, letras espaciadas, contacto, secciones, orden, Skills,
# fechas, emails) se detecta.
# Y keyword_check.py --selftest: un caso limpio pasa y cada fallo de keywords
# plantado (no aparece, sin evidencia, sinonimo sin rastro, herramienta por
# sinonimo, cargo prohibido, gap sin motivo, estado desconocido, negrita que no
# es keyword) se detecta.
#
# Si este test pasa, verify.py esta haciendo su trabajo. Si falla, algo se rompio
# y NO hay que confiar en el hasta arreglarlo.

cd "$(dirname "$0")/.." || exit 1
# Fixtures follow the candidate (they hit real prohibitions): private zone, else the synthetic persona.
P="${HCB_PRIVATE_DIR:-../private}"; [ -d "$P/facts" ] || P="../examples/candidate"
FIX="$P/engine-fixtures"
ok=0
bad=0

echo "======================================================================"
echo "  TEST 1: un documento correcto NO debe dar fallos"
echo "======================================================================"
salida=$(python3 build/verify.py "$FIX/cv-limpio.md" 2>&1)
echo "$salida"
if echo "$salida" | grep -q "^0 fallos"; then
    echo "  --> CORRECTO: pasa limpio."
    ok=$((ok+1))
else
    echo "  --> PROBLEMA: deberia dar 0 fallos y no lo hace."
    bad=$((bad+1))
fi

echo
echo "======================================================================"
echo "  TEST 2: un documento con violaciones conocidas debe detectarlas"
echo "======================================================================"
echo "  El documento de prueba contiene, a proposito:"
echo "    - el apellido con acento"
echo "    - un em dash"
echo "    - el titulo prohibido 'Restaurant Manager'"
echo "    - el titulo prohibido 'Project Leader'"
echo "    - el framing prohibido 'within days'"
echo "    - dos anos inventados (1999 y 2001)"
echo "    - 'reduced operating costs by 75%' sin su base"
echo "    - el fallo de de-inflacion 'sole administrator of a live operational database'"
echo "    - '20 staff', que suma dos grupos que se solapan"
echo "    - ortografia estadounidense ('organized')"
echo "    - un rol australiano antes que uno chileno (orden de bloques)"
echo "    - 'team of five professionals' en vez de 'five engineers'"
echo

salida=$(python3 build/verify.py "$FIX/cv-con-violaciones.md" 2>&1)
echo "$salida"

esperados=("NAME" "EM-DASH" "TITLE" "FRAMING" "DATE" "PROHIBITION" "EN-AU" "CONTACT" "ORDER")
faltan=""
for e in "${esperados[@]}"; do
    echo "$salida" | grep -q "FAIL $e" || faltan="$faltan $e"
done

if [ -z "$faltan" ]; then
    echo "  --> CORRECTO: detecta las 9 categorias de fallo."
    ok=$((ok+1))
else
    echo "  --> PROBLEMA: no detecto estas categorias:$faltan"
    bad=$((bad+1))
fi

echo
echo "======================================================================"
echo "  TEST 3: ats_check.py detecta lo que un ATS o una IA leerian mal"
echo "======================================================================"
salida=$(python3 build/ats_check.py --selftest 2>&1)
rc=$?
echo "$salida"
if [ $rc -eq 0 ] && ! echo "$salida" | grep -q "MAL"; then
    echo "  --> CORRECTO: el texto limpio pasa y los 9 fallos plantados se detectan."
    ok=$((ok+1))
else
    echo "  --> PROBLEMA: ats_check.py no detecta todos los fallos de lectura."
    bad=$((bad+1))
fi

echo
echo "======================================================================"
echo "  TEST 4: keyword_check.py exige las keywords del aviso y sinonimos rastreables"
echo "======================================================================"
salida=$(python3 build/keyword_check.py --selftest 2>&1)
rc=$?
echo "$salida"
if [ $rc -eq 0 ] && ! echo "$salida" | grep -q "MAL"; then
    echo "  --> CORRECTO: el caso limpio pasa y los 9 fallos plantados se detectan."
    ok=$((ok+1))
else
    echo "  --> PROBLEMA: keyword_check.py no detecta todos los fallos de keywords."
    bad=$((bad+1))
fi

echo
echo "======================================================================"
if [ "$bad" -eq 0 ]; then
    echo "  RESULTADO: $ok de 4 tests correctos. verify.py, ats_check.py y keyword_check.py son fiables."
    exit 0
else
    echo "  RESULTADO: $bad test(s) fallando. NO confiar en verify.py, ats_check.py ni keyword_check.py."
    exit 1
fi
