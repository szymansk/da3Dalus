# Relatório de Confiança — da3Dalus / cad-modelling-service

> Gerado pelo Revisor em 2026-08-16, após a segunda rodada da entrevista de validação.
> Substitui o relatório de 74,2 % (2026-07-31), anterior a todas as respostas.

---

## Resumo Geral

| Nível | Quantidade | Percentual |
|-------|-----------|------------|
| 🟢 CONFIRMADO | 8 536 | 76,9 % |
| 🟡 INFERIDO   | 1 777 | 16,0 % |
| 🔴 LACUNA     | 794 | 7,1 % |
| **Total**     | **11 107** | 100 % |

**Confiança geral: 84,9 %** — `(🟢 + 0,5 × 🟡) / total`.

| | |
|---|---|
| Specs revisadas | 18 módulos, 62 units + raízes de módulo |
| Revisão cruzada | **não** — plugin do Codex indisponível nesta sessão |
| Perguntas geradas / respondidas | **206 / 206** (192 rodada 1 + 14 rodada 2) |
| Confiança anterior | 74,2 % |

---

## Por Spec

| Spec | 🟢 | 🟡 | 🔴 | Confiança |
|------|----|----|-----|-----------|
| `fuselage-design` | 349 | 29 | 3 | 95.4% |
| `wing-design` | 515 | 54 | 17 | 92.5% |
| `aeroplane-core` | 365 | 45 | 18 | 90.5% |
| `ai-copilot` | 482 | 67 | 21 | 90.4% |
| `powertrain` | 627 | 80 | 31 | 90.4% |
| `mass-and-balance` | 385 | 79 | 8 | 89.9% |
| `airfoil-catalog` | 456 | 122 | 7 | 88.4% |
| `avl-integration` | 463 | 75 | 42 | 86.3% |
| `openvsp-import` | 487 | 59 | 58 | 85.5% |
| `mission-and-sizing` | 761 | 152 | 74 | 84.8% |
| `cad-designer-topology` | 503 | 130 | 41 | 84.3% |
| `aero-analysis` | 511 | 84 | 71 | 83.0% |
| `cad-generation` | 498 | 88 | 74 | 82.1% |
| `platform-core` | 496 | 144 | 65 | 80.6% |
| `versioning` | 496 | 84 | 96 | 79.6% |
| `mcp-server` | 207 | 147 | 2 | 78.8% |
| `construction-plans` | 602 | 155 | 106 | 78.7% |
| `frontend-workbench` | 333 | 183 | 60 | 73.7% |

A dispersão (73 %–95 %) não é ruído: acompanha a cobertura de perguntas. A entrevista fez
206 perguntas contra ~11 100 afirmações marcadas, e a distribuição foi desigual —
`platform-core` tinha 197 lacunas para 7 perguntas `Q-PC`; `frontend-workbench`, 182 para
9. O fold-back não fecha o que nunca foi perguntado.

---

## Lacunas Pendentes 🔴

Itens que permaneceram sem confirmação após a revisão. **Nenhum é crítico ou estrutural.**

### Instrumentação sem consumidor
Métricas de turno/token/ferramenta, tempo de loft, custo de chamadas ao surrogate, versão
do AVL, taxa de acerto de cache. Sob **ADR 0024** (desktop mono-usuário) não há audiência.
Onde o mantenedor decidiu explicitamente, consta como *decidido-não-construir*; o restante
carrega *"Not addressed by the validation interview"*, para ler-se como **não perguntado**,
não como não respondido.

### Afirmações que nenhuma pergunta alcançou
O grosso de `construction-plans`, `versioning`, `platform-core` e `frontend-workbench` —
afirmações que o Arqueólogo não conseguiu confirmar pelo código e que nenhuma das 206
perguntas tocou. **Apenas 9 das 794** carregam a nota explícita de não-endereçamento; as
demais ~785 são dessa natureza.

### Duas units aposentadas — não são lacunas
`mass-and-balance/weight-items/` (`Q-MB-1`) e `cad-generation/wing-tessellation/`
(`Q-CG-4`) trazem um banner e seus marcadores estão como **moot**. As afirmações são
verdadeiras; simplesmente não devem mais ser construídas. Marcá-las 🟢 exageraria a
especificação; contá-las como lacuna exageraria o trabalho restante.

### Oito residuais abertos por decisão
Registrados em `questions.md` (registro residual R1–R8). **R1 foi resolvido** em
2026-08-15 — a premissa estava errada: `build_yduplicate_sign_map` é o `SgnDup` da carta
`CONTROL` (uma *entrada*), não uma correção de forças de strip; é um segundo produtor do
que `control_surface_mixing.py:45` já possui e será **removido** (ADR 0022 + ADR 0021).

---

## Recomendações

- [ ] **Fechar o passo ⑤ do laço fundamental** (`architecture.md` §0). Um plano retorna
      `dict[ShapeId, Workplane]` (`AbstractShapeCreator.py:49`) — sem espaço para achados,
      então defeitos revelados pela construção são descartados no `return`. Decidir o que
      um Creator devolve afeta os 29 Creators e o congelamento de `cad_designer`
      (ADR 0002). **É a única mudança estrutural que fecharia o laço.**
- [ ] **`platform-core`, `construction-plans`, `versioning`, `frontend-workbench`** ainda
      têm 12–15 marcadores vermelhos por pergunta de entrevista. Uma terceira rodada
      dirigida é a única via — dobrar o fold-back não os fecha.
- [ ] **Reexecutar a varredura de cobertura** em `code-spec-matrix.md`: seus percentuais
      agora são estimativas consistentes com 11 exclusões, não medições.
- [ ] **Ordenar as limpezas do ADR 0019 antes da geração do cliente TypeScript**
      (`Q-CC-11`), ou os vazamentos da API ficam cozidos no código gerado.
- [ ] **Avaliar se os gráficos 2-D precisam do build 3-D** do Plotly
      (`plotly.js-gl3d-dist-min`): cada contexto WebGL conta contra o limite rígido do
      navegador, o mesmo que torna crítico o descarte no `CadViewer` (`Q-FW-5`).

---

## Histórico de Reclassificações

Amostra representativa — o fold-back tocou ~10 300 marcadores em 18 módulos.

| De | Para | Afirmação | Evidência |
|----|------|-----------|-----------|
| 🔴 | 🟢 | `aeroplanes.name` permanece não-único; identidade é o UUID | `Q-AC-2` + medição: 9 de 29 aeronaves já compartilham nome; `aeroplane_clone_service.py:187` |
| 🔴 | 🟢 | Um nó com filhos **não pode** ser removido (RF-12 invertido) | `Q-AC-10` — mudança de comportamento, não confirmação |
| 🔴 | 🟢 | Bug #955 resolvido estruturalmente: o resolvedor pertence a `control_surface_mixing` | `Q-WD-1`; medição: 7 superfícies `ruddervator` em 3 aeronaves |
| 🔴 | 🟢 | `AvlBody`/`BFIL` nunca é construído; ASB é a autoridade para `Cnb` | `Q-AV-2`; `src/asetup.f:418-423`, `src/aero.f:1346-1365` |
| 🔴 | 🟢 | Mapa índice→nome é lido da saída do AVL, não persistido | `Q-AV-3`/`Q-AV-4`; `STITLE(N)` em `src/aoutput.f:168-174` |
| 🔴 | 🟢 | Autoria paramétrica de fuselagem **já existe** (FE + BE) | `Q-FD-8b`; `fuselage_service.py:63,103`; `PropertyForm.tsx:24,529-532,575` |
| 🔴 | 🟢 | CORS restrito a origens concretas | `R2-10`; `main.py:234-237`; `Q-FW-1` (SPA-direct **é** a arquitetura) |
| 🔴 | 🟡 | Roteador legado `endpoints/aeroplane.py` a remover | `Q-CC-6` — derivado de `P-DEAD-0`, **não** decisão do mantenedor |
| 🔴 | 🟡 | `units` descreve apenas o formato de fio; sem override de armazenamento | `Q-WD-2` — derivado do ADR 0019 |
| 🟡 | 🟢 | Nenhuma linha métrica em `wing_xsec_spares` | `Q-WD-7 ①` — medido: 47 linhas, todas ≥ 1,0 |
| 🟡 | 🟢 | Nenhum spar `normal` perde origem na leitura | `Q-WD-7 ②` — medido: 0 de 11 falham o predicado |
| 🟢 | 🟡 | `s_ref` deve ser lido do contexto gh-924, não reconstruído | ADR 0022 — contradição com o código real |
| 🔴 | ✅ | **R1** — sinal de forças espelhadas | premissa **errada**; `AbstractShapeCreator`/`SgnDup` é entrada, não saída |

---

*Relacionados: [`gaps.md`](gaps.md) · [`questions.md`](questions.md) (rodada 1) ·
[`questions-round2.md`](questions-round2.md) (rodada 2) ·
[`architecture.md`](architecture.md) §0 ·
[`traceability/code-spec-matrix.md`](traceability/code-spec-matrix.md)*
