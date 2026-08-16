# Lacunas — o que a especificação ainda não sabe

> Regenerado pelo Revisor em 2026-08-16, após a segunda rodada. Substitui a versão de
> 2026-07-31 (21 críticas / 178 moderadas / 25 cosméticas), anterior a todas as respostas.

**794 marcadores 🔴 permanecem em 18 módulos.** Não são resíduo de trabalho inacabado —
são o que 206 perguntas não conseguiram alcançar contra ~11 100 afirmações marcadas.
**Apenas 9 carregam a nota explícita de não-endereçamento**; as demais ~785 são afirmações
que o Arqueólogo não pôde confirmar pelo código e que nenhuma pergunta tocou. Essa é a
forma honesta deste número: ele é dominado por *não perguntado*, não por *não respondido*.

---

## Severidade

### 🔴 Crítico — 0

*(**R1 — sinal das forças de strip espelhadas** constava aqui e foi **resolvido** em
2026-08-15. A premissa estava errada: `build_yduplicate_sign_map` mapeia nomes de
superfície para o `SgnDup` da carta `CONTROL` — uma **entrada** do arquivo `.avl` — e não
uma correção às forças de saída. Verificado contra o AVL 3.40: nenhum sinal por superfície
deve ser aplicado a forças, pois o AVL consome `IMAGS` internamente
(`src/aero.f:919-923, 1063-1071`; `src/getvm.f:88`). A função é um **segundo produtor** do
que `control_surface_mixing.py:45` já possui e é **removida** — ADR 0022 e ADR 0021.*

*Registrado em vez de apagado: o raciocínio que produziu R1 era sólido — forças de strip
**de fato** alimentam o dimensionamento de longarina via `/spanwise_loads_with_sizing`, e a
prática RC não tem ensaio de carga que pegasse um erro ali. Apenas o objeto estava errado.)*

### 🟠 Estrutural — 0

*(Uma versão anterior listava `WingLoftCreator.py` como órfão após `Q-CG-4`. Não é:
medido, é um `AbstractShapeCreator` regular emitido como `$TYPE` no JSON de plano gerado
(`cad_service.py:238`) e referenciado por nome em **4 planos de construção armazenados**.
Sua listagem sob `wing-tessellation` era um arquivamento incorreto; os donos reais são
`construction-plans/plan-execution/` e `cad-generation/wing-export-task/`.)*

### 🟡 Moderado — quatro módulos sub-perguntados

| Módulo | 🔴 | Perguntas | 🔴 por pergunta |
|---|---:|---:|---:|
| `construction-plans` | 100 | 9 | 11 |
| `versioning` | 96 | 8 | 12 |
| `cad-generation` | 75 | 6 | 12 |
| `mission-and-sizing` | 74 | 16 | 4 |

Não se fecham por fold-back. Precisam de **uma terceira rodada dirigida** — é a
recomendação, não um defeito.

### ⚪ Cosmético — instrumentação sem consumidor

Métricas de turno/token/ferramenta, tempo de loft, custo do surrogate, versão do AVL, taxa
de acerto de cache. Sob **ADR 0024** (desktop mono-usuário) não há audiência para nada
disso.

---

## Uma lacuna arquitetural, acima de todas as outras 🟢

**O passo ⑤ do laço fundamental não fecha, e a causa é o tipo de retorno.**

```python
# cad_designer/airplane/AbstractShapeCreator.py:49
def create_shape(self, input_shapes: dict[ShapeId, Workplane] = None,
                 **kwargs) -> dict[ShapeId, Workplane]:
```

Um plano devolve um mapa nome → `Workplane` e **nada mais**. Sem espaço para achados: nem
avisos, nem "esta longarina não manteve a folga da dobradiça", nem "o sólido saiu
não-manifold neste filete". A metade dos artefatos de ⑤ funciona; **a metade do retorno
não pode**, não por falta de fiação, mas porque **a interface não consegue carregá-la**.

Isso reenquadra vários itens como um só problema: `Q-VI-4` (detecção de sólido inutilizável)
precisa de caminho próprio exatamente por isso; o `DesignWarning` de `Q-CP-3` é emitido
pelo *serviço*, não pelo Creator que descobriu o problema; e `R2-03` (falhar em vez de
degradar) é em parte consequência disso — sem meio de relatar um resultado parcial com
fidelidade, abortar é a única opção honesta.

**Não é respondido aqui.** O que um Creator deve devolver afeta os 29 Creators e o
congelamento de `cad_designer` (ADR 0002). Ver [`architecture.md`](architecture.md) §0.

---

## Por módulo

| Módulo | 🔴 | não-endereçado explícito | perguntas | marcadores *moot* |
|---|---:|---:|---:|---:|
| `construction-plans` | 100 | 0 | 9 | — |
| `versioning` | 96 | 0 | 8 | — |
| `cad-generation` | 75 | 0 | 6 | 39 |
| `mission-and-sizing` | 74 | 0 | 16 | 2 |
| `aero-analysis` | 71 | 0 | 9 | — |
| `platform-core` | 65 | 0 | 7 | — |
| `frontend-workbench` | 60 | 0 | 9 | — |
| `openvsp-import` | 58 | 0 | 10 | — |
| `avl-integration` | 41 | 2 | 8 | 3 |
| `cad-designer-topology` | 37 | 1 | 5 | — |
| `powertrain` | 31 | 0 | 13 | — |
| `ai-copilot` | 21 | 5 | 15 | 1 |
| `aeroplane-core` | 18 | 0 | 10 | — |
| `wing-design` | 17 | 1 | 11 | — |
| `mass-and-balance` | 10 | 0 | 11 | 20 |
| `airfoil-catalog` | 7 | 0 | 9 | — |
| `fuselage-design` | 4 | 0 | 9 | 1 |
| `mcp-server` | 2 | 0 | 8 | — |

---

## O que deliberadamente **não** é lacuna

Duas units estão **aposentadas**, com banner, e seus marcadores constam como *moot*:
`mass-and-balance/weight-items/` (`Q-MB-1`) e `cad-generation/wing-tessellation/`
(`Q-CG-4`). As afirmações são verdadeiras; apenas não devem mais ser construídas.

E o **DXF** não é lacuna: nenhum Creator produz asas de nervura ainda, então não há o que
aninhar nem o que escrever. O formato chega **com** esse Creator — construí-lo antes daria
um escritor sem produtor, exatamente o estado inerte que `P-DEAD-0` proíbe.

---

*Relacionados: [`confidence-report.md`](confidence-report.md) ·
[`questions.md`](questions.md) · [`questions-round2.md`](questions-round2.md) ·
[`architecture.md`](architecture.md) §0*
