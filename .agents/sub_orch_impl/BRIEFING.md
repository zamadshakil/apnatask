# BRIEFING — 2026-06-21T22:12:00+05:00

## Mission
Drive the implementation of the ApnaTask backend services from Milestones M1 to M6.

## 🔒 My Identity
- Archetype: teamwork_preview_orchestrator
- Roles: orchestrator, user_liaison, human_reporter, successor
- Working directory: E:\Zamad's Personal Agents Squad\apnatask\.agents\sub_orch_impl
- Original parent: main agent
- Original parent conversation ID: 0913873c-d911-4be6-ab90-ca857a6c47f3

## 🔒 My Workflow
- **Pattern**: Project
- **Scope document**: E:\Zamad's Personal Agents Squad\apnatask\PROJECT.md
1. **Decompose**: We will implement the existing milestones (M1 to M6) sequentially.
2. **Dispatch & Execute**:
   - **Direct (iteration loop)**: For each milestone, we run: Explorer -> Worker -> Reviewer -> Challenger -> Forensic Auditor loop.
3. **On failure** (in this order):
   - Retry: nudge stuck agent or re-send task
   - Replace: spawn fresh agent with partial progress
   - Skip: proceed without (only if non-critical)
   - Redistribute: split stuck agent's remaining work
   - Redesign: re-partition decomposition
   - Escalate: report to parent (sub-orchestrators only, last resort)
4. **Succession**: Self-succeed at 16 spawns.
- **Work items**:
  - M1: Base App Setup & Dockerization [in-progress]
  - M2: Geospatial Tracking & Matching [pending]
  - M3: WebSocket Bidding Server [pending]
  - M4: Celery Task Queue [pending]
  - M5: Mock Integration Modules [pending]
  - M6: Final E2E Pass & Hardening [pending]
- **Current phase**: 2B (Iteration Loop)
- **Current focus**: M1: Base App Setup & Dockerization (Iteration 2 - Fix integrity violations & bugs)

## 🔒 Key Constraints
- NEVER write, modify, or create source code files directly.
- NEVER run build/test commands yourself — require workers to do so.
- File-editing tools only for .md files in the .agents/ folder.
- Follow liveness checks and liveness deadlines (10 min heartbeat, 20 min replace).
- Auditor is NON-SKIPPABLE. Hard veto on integrity violation.
- Do NOT reuse a subagent after it has delivered its handoff — always spawn fresh.

## Current Parent
- Conversation ID: f783552f-76d2-4965-80f6-334ebea6e3eb
- Updated: yes

## Key Decisions Made
- Scaffolding the FastAPI application with docker-compose supporting postgres/postgis, redis, rabbitmq, and celery.

## Team Roster
| Agent | Type | Work Item | Status | Conv ID |
|-------|------|-----------|--------|---------|
| M1_Exp1 | teamwork_preview_explorer | M1 Exploration | completed | fea26e70-856c-4c16-8415-574c57bc7679 |
| M1_Exp2 | teamwork_preview_explorer | M1 Exploration | completed | 1ae7fbd8-2ed1-486e-8909-f98b45383bb8 |
| M1_Exp3 | teamwork_preview_explorer | M1 Exploration | completed | 71719734-7b1b-4ac0-b977-8cd6b562faa5 |
| M1_Wrk | teamwork_preview_worker | M1 Implementation | failed | 87c5f910-5eac-4612-b3f0-fef92789f442 |
| M1_Wrk2 | teamwork_preview_worker | M1 Replacement Worker | completed | cb1ffc8f-ed78-4ce6-a0a8-c94e4ab5c558 |
| M1_Rev1 | teamwork_preview_reviewer | M1 Review | pending | 59028021-dc6d-4218-b2a0-17134f779a9c |
| M1_Rev2 | teamwork_preview_reviewer | M1 Review | pending | 2467dc8b-2c45-459b-991e-bf43171f3bd8 |
| M1_Chl1 | teamwork_preview_challenger | M1 Verification | pending | bbc376f1-55f4-4df2-9d97-833a374d9931 |
| M1_Chl2 | teamwork_preview_challenger | M1 Verification | pending | 4310a48a-144c-489b-9c82-8983d48be875 |
| M1_Aud | teamwork_preview_auditor | M1 Auditing | pending | 2257889f-15d4-4767-96ce-971138c3fe13 |

## Succession Status
- Succession required: no
- Spawn count: 10 / 16
- Pending subagents: []
- Predecessor: none
- Successor: not yet spawned

## Active Timers
- Heartbeat cron: task-21
- Safety timer: none
- On succession: kill all timers before spawning successor
- On context truncation: run manage_task(Action="list") — re-create if missing

## Artifact Index
- E:\Zamad's Personal Agents Squad\apnatask\PROJECT.md — Global index: architecture, milestones, interfaces, code layout
