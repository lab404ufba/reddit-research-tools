# Reddit Research Tools

Ferramenta para **montar corpus a partir do Reddit** com um **perfil de pesquisa** (YAML): cada estudo define `study_id`, tema legível, subreddits, grupos de palavras-chave, filtros de pós-processamento (exclusões, termos obrigatórios) e parâmetros do relatório da Fase 3. O caso original foi o estudo sobre **discursos de criadores sobre o algoritmo do TikTok** (“fofoca algorítmica”); a mesma pipeline serve para qualquer tema delimitado pelo pesquisador.

**Autores da pesquisa original:** Thiago Assumpção e Giovanni Della Dea  
**Instituição:** Universidade Federal da Bahia (UFBA)

---

## Visão geral

Pipeline em quatro fases (1–3 em linha de comando; 4 no Jupyter):

```
[Fase 1] Coleta bruta          →  data/raw/<study_id>_raw.jsonl
[Fase 2] Limpeza e estrutura   →  data/processed/<study_id>_corpus.xlsx
[Fase 3] Análise e relatório   →  reports/relatorio_<study_id>_YYYYMMDD_HHMM.md
[Fase 4] Visualização          →  notebooks/analise_resultados.ipynb
```

Perfil padrão (reprodutível, equivalente ao antigo `scraper/config.py`):  
[`profiles/examples/fofoca_algoritmica.yaml`](profiles/examples/fofoca_algoritmica.yaml).

Guia de campos **obrigatórios vs opcionais**, `notes` / `metadata` e validação:  
[`profiles/README.md`](profiles/README.md).

---

## Arquitetura

```
reddit-research-tools/
├── main.py                 # Fase 1 — scraper (Playwright)
├── process.py              # Fase 2 — funil + Excel
├── analise_corpus.py       # Fase 3 — relatório Markdown
├── paths.py                # Pastas + paths_for_study(study_id)
├── research_profile.py     # load_profile() + dataclasses do YAML
├── requirements.txt
├── scripts/
│   └── validate_profile.py # Valida YAML (sem browser)
├── profiles/
│   ├── README.md
│   ├── schema/
│   │   └── research_profile.schema.json
│   └── examples/
│       ├── template_completo.yaml
│       ├── fofoca_algoritmica.yaml
│       └── minimo.yaml
├── scraper/
│   ├── config.py           # Referência legada (comentada)
│   ├── browser.py
│   ├── reddit_scraper.py
│   └── storage.py
├── processor/
│   ├── loader.py
│   ├── cleaner.py
│   └── exporter.py
├── notebooks/
│   └── analise_resultados.ipynb
├── data/raw/               # JSONL (não versionado)
├── data/processed/         # Excel (não versionado)
├── logs/scraper_<study_id>.log
└── reports/
```

---

## Perfil YAML (`study_id`, tema, delimitadores)

| Campo | Descrição |
|--------|-------------|
| `study_id` | Identificador curto (só letras, números e `_`); define nomes de arquivo. |
| `theme_label` | Nome legível do estudo (metadados no JSONL/Excel e logs). |
| `subreddits` | Lista de comunidades (sem prefixo `r/`). |
| `keyword_groups` | Mapa `nome_do_grupo` → lista de strings de busca no Reddit. |
| `search` | `time_filter`, limites de posts/comentários, delays, `headless_default`. |
| `filters` | `min_comments`, `min_chars`, `creator_patterns`, `exclude_terms` (substring em título+corpo), `require_any_terms` (pelo menos um termo em título+corpo). |
| `analysis` | `report_title`, `report_subtitle`, `vocabulary_terms`, `tactics_pattern`, `theories_pattern` (regex, flags case-insensitive na compilação). |

Copie [`profiles/examples/minimo.yaml`](profiles/examples/minimo.yaml) ou o modelo comentado  
[`profiles/examples/template_completo.yaml`](profiles/examples/template_completo.yaml).

Validar o perfil antes da Fase 1 (sem rede nem browser):

```bash
python scripts/validate_profile.py profiles/examples/meu_perfil.yaml
```

No Cursor/VS Code, com a extensão **YAML**, o ficheiro  
[`profiles/schema/research_profile.schema.json`](profiles/schema/research_profile.schema.json)  
é associado automaticamente aos YAML em `profiles/**` (ver [`.vscode/settings.json`](.vscode/settings.json)).

---

## Fase 1 — Coleta bruta

Usa Playwright (Chromium) para buscar no Reddit **sem API oficial**.

```bash
pip install -r requirements.txt
playwright install chromium

# Perfil padrão = exemplo fofoca algorítmica
python main.py

python main.py --profile profiles/examples/minimo.yaml
python main.py --no-headless   # janela visível (debug)
```

Saída: `data/raw/<study_id>_raw.jsonl`, log em `logs/scraper_<study_id>.log`. Coleta incremental: IDs já presentes são ignorados ao rerodar.

Cada registro inclui `study_id` e `theme_label` no objeto `post`.

---

## Fase 2 — Limpeza e Excel

```bash
python process.py
python process.py --profile profiles/examples/minimo.yaml
python process.py --input data/raw/meu_estudo_raw.jsonl --output data/processed/meu_estudo_corpus.xlsx
```

Funil: deduplicação → mínimo de comentários → coluna `is_creator_suspect` → tamanho mínimo do texto → opcional `exclude_terms` → opcional `require_any_terms`.

Abas **Posts** e **Comentarios**; colunas extras **Study_ID** e **Theme**.

---

## Fase 3 — Relatório Markdown

```bash
python analise_corpus.py
python analise_corpus.py --profile profiles/examples/minimo.yaml
python analise_corpus.py --input data/processed/meu_estudo_corpus.xlsx --profile profiles/examples/minimo.yaml
```

O perfil define título/subtítulo do relatório, lista de termos para contagens e regexes de “táticas” e “teorias”. Arquivo: `reports/relatorio_<study_id>_<timestamp>.md`.

---

## Fase 4 — Notebook

```bash
cd notebooks
jupyter notebook analise_resultados.ipynb
```

A célula de carga de dados usa `profiles/examples/fofoca_algoritmica.yaml` para obter `study_id` e abrir `data/processed/<study_id>_corpus.xlsx`. Para outro estudo, altere `PROFILE_YAML` nessa célula (e rode Fases 1–2 com o mesmo perfil).

---

## Sequência sugerida

```bash
python main.py --profile profiles/examples/meu_perfil.yaml
python process.py --profile profiles/examples/meu_perfil.yaml
python analise_corpus.py --profile profiles/examples/meu_perfil.yaml
```

Depois abra o notebook e alinhe `PROFILE_YAML` ao mesmo arquivo.

---

## Ajustes rápidos

| Objetivo | Onde |
|----------|------|
| Obrigatório vs opcional, `notes` / `metadata` | [`profiles/README.md`](profiles/README.md) |
| Modelo YAML comentado | [`profiles/examples/template_completo.yaml`](profiles/examples/template_completo.yaml) |
| Validar perfil (sem browser) | `python scripts/validate_profile.py profiles/...yaml` |
| Subreddits, keywords, filtros, relatório | O seu `.yaml` em `profiles/` |
| Caminhos por estudo | Automáticos a partir de `study_id` (`paths.paths_for_study`) |
| Legado reprodutível | `profiles/examples/fofoca_algoritmica.yaml` |

---

## Ética e uso

- Respeite os [termos do Reddit](https://www.redditinc.com/policies) e políticas locais de dados pessoais.
- Use delays razoáveis (`search.delay_min` / `delay_max`); evite carga agressiva nos servidores.
- Destina-se a **pesquisa** e transparência metodológica; não armazene ou redistribua dados além do necessário ao seu estudo.

---

## Dependências

```
playwright>=1.44.0
pandas>=2.2.0
openpyxl>=3.1.0
pyyaml>=6.0.0
```
