# Perfis de pesquisa (YAML)

Cada ficheiro `.yaml` descreve **um estudo**: delimitação no Reddit, filtros do corpus e texto/regex do relatório (Fase 3). A validação “de verdade” é a mesma das ferramentas: `load_profile()` em [`research_profile.py`](../research_profile.py).

## Ficheiros de referência

| Ficheiro | Uso |
|----------|-----|
| [`examples/template_completo.yaml`](examples/template_completo.yaml) | Modelo com **todos** os blocos opcionais comentados; copie e adapte. |
| [`examples/minimo.yaml`](examples/minimo.yaml) | Exemplo mínimo válido. |
| [`examples/fofoca_algoritmica.yaml`](examples/fofoca_algoritmica.yaml) | Estudo original reprodutível. |
| [`schema/research_profile.schema.json`](schema/research_profile.schema.json) | JSON Schema (IDE / `check-jsonschema`). |

## Obrigatório vs opcional

Campos **obrigatórios** na raiz do YAML:

| Campo | Regra |
|--------|--------|
| `study_id` | Apenas `[a-zA-Z0-9_]+`. Define `data/raw/<id>_raw.jsonl`, Excel, logs e relatórios. |
| `theme_label` | Texto livre não vazio (rótulo humano do estudo). |
| `subreddits` | Lista não vazia de nomes sem `r/`. |
| `keyword_groups` | Mapa não vazio: cada grupo → lista não vazia de strings de busca. |

**Opcionais** (se omitidos, aplicam-se os defaults do código em `research_profile.py`):

| Bloco | Comportamento se omitido |
|--------|---------------------------|
| `search` | `time_filter: year`, 40 posts/busca, 20 comentários/post, delays 2–5 s, `headless_default: true`. |
| `filters` | `min_comments: 3`, `min_chars: 30`, padrões `creator_patterns` embutidos, listas de exclusão/inclusão vazias. |
| `analysis` | Títulos e vocabulário padrão da ferramenta; regexes de táticas/teorias padrão. |

## Campos só para documentação (opcionais)

O loader **ignora** chaves na raiz que não usa no pipeline; pode incluir, por exemplo:

- `notes`: texto longo (equipa, hipóteses, versão do protocolo).
- `metadata`: mapa livre (PI, projeto, ORCID, etc.) — útil para o teu arquivo; **não** é copiado automaticamente para cada linha do JSONL (só consta no YAML).

Estes campos aparecem no [JSON Schema](schema/research_profile.schema.json) para autocomplete; não são obrigatórios.

## Validar antes de correr o scraper

```bash
python scripts/validate_profile.py caminho/para/meu_perfil.yaml
```

Sem rede nem browser: falha com a mesma mensagem que `main.py` / `process.py` / `analise_corpus.py` ao carregar o perfil.

## JSON Schema no VS Code / Cursor

O repositório inclui [`.vscode/settings.json`](../.vscode/settings.json) com `yaml.schemas` apontando para `profiles/schema/research_profile.schema.json`. Com a extensão **YAML** (Red Hat), obténs validação e autocomplete nos perfis.

Validação em CI (opcional):

```bash
pip install check-jsonschema
check-jsonschema --schemafile profiles/schema/research_profile.schema.json profiles/examples/minimo.yaml
```
