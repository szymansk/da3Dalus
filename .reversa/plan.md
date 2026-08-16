# Plano de Exploração — cad-modelling-service

> Criado pelo Reversa em 2026-07-30
> Marque cada tarefa com ✅ quando concluída.
> Você pode editar este plano antes de iniciar: adicione, remova ou reordene tarefas conforme necessário.

---

## Fase 1: Reconhecimento 🔍

- [x] **Scout** — Mapeamento de estrutura de pastas e tecnologias ✅
- [x] **Scout** — Análise de dependências e gerenciadores de pacotes ✅
- [x] **Scout** — Identificação de entry points, CI/CD e configurações ✅

## Decisão de organização das specs 🗂️

> Entre o Scout e o Arqueólogo, o Reversa pergunta como você quer organizar as specs (por módulo, caso de uso, endpoint, híbrida, por features ou customizada). A escolha fica persistida em `.reversa/config.toml` na seção `[specs]` e não será reperguntada em execuções futuras. Para reapresentar o menu, remova manualmente a seção.

## Fase 2: Escavação 🏗️

> Módulos identificados pelo Scout (18). Organização das specs: **hybrid**.
> Executados em clusters sequenciais pelo Arqueólogo (sem spawn simultâneo).

**Cluster A — Aircraft domain core** ✅
- [x] **Arqueólogo** — `aeroplane-core` ✅
- [x] **Arqueólogo** — `wing-design` ✅
- [x] **Arqueólogo** — `fuselage-design` ✅
- [x] **Arqueólogo** — `airfoil-catalog` ✅

**Cluster B — CAD generation & import** ✅
- [x] **Arqueólogo** — `cad-generation` ✅
- [x] **Arqueólogo** — `cad-designer-topology` ✅
- [x] **Arqueólogo** — `construction-plans` ✅
- [x] **Arqueólogo** — `openvsp-import` ✅

**Cluster C — Aero analysis** ✅
- [x] **Arqueólogo** — `aero-analysis` ✅
- [x] **Arqueólogo** — `avl-integration` ✅
- [x] **Arqueólogo** — `mission-and-sizing` ✅

**Cluster D — Mass, powertrain & versioning** ✅
- [x] **Arqueólogo** — `mass-and-balance` ✅
- [x] **Arqueólogo** — `powertrain` ✅
- [x] **Arqueólogo** — `versioning` ✅

**Cluster E — Platform, AI & frontend** ✅
- [x] **Arqueólogo** — `ai-copilot` ✅
- [x] **Arqueólogo** — `mcp-server` ✅
- [x] **Arqueólogo** — `platform-core` ✅
- [x] **Arqueólogo** — `frontend-workbench` ✅

## Fase 3: Interpretação 🧠

- [x] **Detetive** — Arqueologia Git e ADRs retroativos ✅ (18 ADRs)
- [x] **Detetive** — Regras de negócio implícitas e máquinas de estado ✅
- [x] **Detetive** — Matriz de permissões (RBAC/ACL) ✅
- [x] **Arquiteto** — Diagramas C4 (Contexto, Containers, Componentes) ✅
- [x] **Arquiteto** — ERD completo e integrações externas ✅
- [x] **Arquiteto** — Spec Impact Matrix ✅

## Fase 4: Geração 📝

- [x] **Redator** — Specs SDD por componente ✅ (18 módulos, hybrid; ~258 arquivos)
- [x] **Redator** — OpenAPI ✅ (`openapi/da3dalus-v2.yaml`, 3.1.0, 158 paths)
- [x] **Redator** — User Stories ✅ (10 flows)
- [x] **Redator** — Code/Spec Matrix ✅ (`traceability/code-spec-matrix.md`)

## Fase 5: Revisão ✅

- [x] **Revisor** — Revisão cruzada de specs ✅ (Codex opcional pulado; revisão própria)
- [x] **Revisor** — Resolução de lacunas com o usuário ✅ (`questions.md`, answer_mode=file → aguarda respostas)
- [x] **Revisor** — Resolução de lacunas ✅ (192/192 respondidas, entrevista 2026-08-13→15)
- [x] **Revisor** — Fold-back ✅ (80 units em 18 módulos; 2 units aposentadas)
- [x] **Revisor** — Matrizes validadas ✅ (`code-spec-matrix.md`, `spec-impact-matrix.md`)
- [x] **Revisor** — Relatório de confiança final ✅ (`confidence-report.md`, **84,0%** — era 74,2%)

---

## Agentes Independentes

> Execute estes agentes quando os recursos estiverem disponíveis — podem rodar em qualquer fase.

- [ ] **Visor** — Análise de interface via screenshots
- [ ] **Data Master** — Análise completa do banco de dados
- [ ] **Design System** — Extração de tokens de design
- [ ] **Tracer** — Análise dinâmica (requer sistema acessível)

---

## Próximo passo

Após o Time de Descoberta concluir e o `_reversa_sdd/` estar populado, você pode disparar um dos fluxos seguintes:

- `/reversa-migrate`: orquestrador do **Time de Migração** (Paradigm Advisor → Curator → Strategist → Designer → Screen Translator → Inspector). Gera as specs do sistema novo. Saída em `_reversa_sdd/migration/` e `_reversa_sdd/screens/`.
- `/reversa-reconstructor`: gera plano bottom-up para reimplementar o software a partir das specs do legado (uma tarefa por sessão).
