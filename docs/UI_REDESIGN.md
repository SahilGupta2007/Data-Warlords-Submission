# AgentIQ enterprise UI

The complete existing application is retained. The visual layer consists of:

- `dashboard/app.py`: early CSS injection, SVG sidebar navigation synchronized with all six native tab containers, KPI wrappers and themed charts. The native horizontal tab strip is hidden so the sidebar is the only navigation surface.
- `dashboard/enterprise_theme.py`: color tokens, responsive CSS and `apply_enterprise_theme(fig)`. The helper preserves trace data, marker sizes, hover templates, graph positions and explicit axis settings.
- `dashboard/agent/ai_strategist.py`: all 12 presets, responsive chart/finding panes, highlighted findings and the original SQL drawer. SQL generation, validation, repair, Groq calls and response parsing are unchanged.
- `.streamlit/config.toml`: native dark styling for widgets and canvas-rendered dataframes.

Start the complete pipeline and dashboard with the single project entry point:

```powershell
.venv/Scripts/python.exe run_all.py
```

The launcher reuses existing processed outputs. Pass `--rebuild` after changing source data, or `--pipeline-only` to rebuild without launching Streamlit.

The existing processed data, warehouse and Groq configuration remain prerequisites. No data pipeline rebuild is needed for this redesign. Restart an already running server after updating the shared theme module.

All tab content still executes and renders. Sidebar changes rerun the page to select the matching native tab container; AI results stay in session state, preventing repeat Groq calls merely from navigation. Chart wheel zoom is disabled and every responsive Plotly container clips overflow instead of creating a nested scroll area.

The installed source uses `openai/gpt-oss-20b`. That configuration was preserved, as were its prompts and parsing, rather than replacing it with the different model names in the design brief.

Validation:

```powershell
.venv/Scripts/python.exe -m unittest test_enterprise_ui test_ai_strategist -v
.venv/Scripts/python.exe verify_dashboard.py
```

Nine regression tests pass. Before/after comparisons preserve all 11 chart datasets rendered by the supplied data, including all 70 visual graph nodes and 65 edge hover targets. The current warehouse contains no velocity anomalies; its original conditional anomaly chart and detection logic remain intact. All analytical views and 12 legacy agent intents passed the existing health check. Desktop and 390px mobile browser checks cover navigation, drawer behavior, scrolling tables, export access, AI finding panes and SQL expansion. AI regression checks use controlled responses; live Groq availability and output quality were not tested.

`artifacts/agentiq-enterprise-source.zip` contains the complete application Python source, original pipeline modules, dependency list, native theme, documentation and tests. It excludes datasets, virtual environments and credentials; use it with the existing project data and environment.
