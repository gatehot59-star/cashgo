# CASHGO

Ecosistema de automatizacion publicitaria con IA. Este repositorio contiene la
**Fase 0** implementada (auditoria publicitaria competitiva a partir de la Ad
Library oficial de Meta) y los documentos de decision de las otras tres
arquitecturas especificadas.

> ## El trabajo NO esta en `main`
>
> `main` contiene solo este archivo. Todo el codigo, la evidencia y los informes
> viven en la rama **`titan/auditoria-cashgo`**, en el Pull Request #1, sin
> mergear a proposito: mergear a la rama de la que otros clonan es una accion
> delicada que requiere decision humana.
>
> Si entraste por la URL raiz esperando encontrar el proyecto, **este aviso existe
> por un hallazgo de auditoria externa (D8, 2026-09-07)**: un auditor que llegaba
> aca concluia, razonablemente, que el repositorio estaba vacio.

## Por donde entrar

| Que busco | Donde |
|---|---|
| **Informe tecnico de auditoria** | [`02-INFORME-PARA-AUDITORIA.md`](https://github.com/gatehot59-star/cashgo/blob/titan/auditoria-cashgo/02-INFORME-PARA-AUDITORIA.md) |
| Como correr todo sin credenciales | seccion 12 del informe |
| El codigo de la Fase 0 | [`fase0/`](https://github.com/gatehot59-star/cashgo/tree/titan/auditoria-cashgo/fase0) y su [README](https://github.com/gatehot59-star/cashgo/blob/titan/auditoria-cashgo/fase0/README.md) |
| Salidas crudas de cada instrumento | [`evidencia/`](https://github.com/gatehot59-star/cashgo/tree/titan/auditoria-cashgo/evidencia) |
| Por que la Arquitectura 1 no es producto | [`00-AUDITORIA-CASHGO.md`](https://github.com/gatehot59-star/cashgo/blob/titan/auditoria-cashgo/00-AUDITORIA-CASHGO.md) |
| Contraste contra un blueprint externo | [`01-CONTRASTE-CON-BLUEPRINT-EXTERNO.md`](https://github.com/gatehot59-star/cashgo/blob/titan/auditoria-cashgo/01-CONTRASTE-CON-BLUEPRINT-EXTERNO.md) |
| Guardrails financieros (12 reglas) | [`ADR-CG-002-fusion-de-guardrails.md`](https://github.com/gatehot59-star/cashgo/blob/titan/auditoria-cashgo/ADR-CG-002-fusion-de-guardrails.md) |

## Estado, en una linea

La Fase 0 esta implementada y verificada contra fixtures por CI en maquina limpia.
Su comportamiento contra las APIs reales, la calidad semantica de su capa
cognitiva y su viabilidad comercial son estados **NO MEDIDOS**, declarados como
tales en la seccion 10 del informe.

## Verificacion rapida (sin credenciales, menos de un minuto)

```bash
git checkout titan/auditoria-cashgo
pip install -r fase0/requirements.txt
python3 -m fase0.fixtures.generar
python3 -m unittest discover -s fase0/tests -t . -v   # 128 tests
bash scripts/control_positivo_suite.sh                # 7/7 mutaciones cazadas
python3 scripts/manifiesto.py --verificar             # integridad de la evidencia
```
