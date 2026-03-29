# 🐚 stzsh

> **Structured data superpowers for your Zsh shell.**
> Inspired by [Nushell](https://www.nushell.sh/), built for Zsh — load, filter, sort, explore, and visualize structured data right from your terminal.

```zsh
load users.csv | where age >= 25 | sort-by name | print_table
```

```
┌────┬──────────┬─────┬─────────┐
│ id │ name     │ age │ country │
├────┼──────────┼─────┼─────────┤
│  3 │ Alice    │  31 │ IL      │
│  1 │ Bob      │  25 │ US      │
│  7 │ Yael     │  28 │ IL      │
└────┴──────────┴─────┴─────────┘
```

---

## ✨ Features

- 📂 **Load** JSON, CSV, YAML, TOML, and plain tables in one command
- 🔍 **Filter** with `where` using `==`, `!=`, `>`, `<`, `like`, and more
- 🔃 **Sort**, **deduplicate**, and **select** columns with simple commands
- 📊 **Visualize** distributions with inline histogram bar charts
- 🖥️ **Explore** tables and trees interactively with keyboard navigation
- 🌐 **Fetch** JSON and XML APIs with the built-in `http` client
- 📰 **Read RSS/Atom feeds** formatted beautifully in your terminal
- 🔤 **BiDi support** — correct display of Hebrew and Arabic text
- 🔗 **Unix-pipe philosophy** — every command reads and writes JSON, chain anything

---

## 📦 Installation

### Oh My Zsh

```zsh
git clone https://github.com/yourname/stzsh ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/stzsh
```

Then add `stzsh` to your plugins in `~/.zshrc`:

```zsh
plugins=(... stzsh)
```

### Manual

```zsh
git clone https://github.com/yourname/stzsh ~/.stzsh
echo 'source ~/.stzsh/stzsh.plugin.zsh' >> ~/.zshrc
source ~/.zshrc
```

### Requirements

- **Zsh** 5.0+
- **Python** 3.8+
- Optional dependencies (only needed for specific formats):
  ```zsh
  pip install pyyaml   # for YAML support
  ```
  TOML is supported natively on Python 3.11+, or install `tomli` for older versions:
  ```zsh
  pip install tomli    # Python < 3.11 only
  ```

---

## 🚀 Quick Start

```zsh
# Load a CSV and pretty-print it
load data.csv | print_table

# Filter and sort
load data.csv | where status == active | sort-by name | print_table

# Explore interactively (press q to exit, enter for detail view)
load data.csv | explore_table

# Pull live data from an API
http GET https://api.github.com/repos/torvalds/linux/tags | print_table

# Read an RSS feed
http GET https://feeds.bbci.co.uk/news/rss.xml | show_rss --limit 10
```

---

## 📖 Command Reference

### 📂 Loading Data

#### `load <file> [--from FORMAT]`

Load a file into the pipeline. Format is auto-detected from the extension.

| Format | Extensions |
|--------|-----------|
| JSON   | `.json` |
| CSV    | `.csv` |
| YAML   | `.yml`, `.yaml` |
| TOML   | `.toml` |
| Table  | `.table` (space-separated) |

```zsh
load users.csv
load config.toml
load report.yml --from yaml
```

#### `parse_stzsh --input MODE`

Parse raw command output or text into structured JSON.

```zsh
# Parse a table from command output
ps aux | parse_stzsh --input table | sort-by %CPU | head -n 5 | print_table

# Parse with a named-group regex
cat access.log | parse_stzsh --input '(?P<ip>\S+) .* "(?P<method>\S+) (?P<path>\S+)'
```

---

### 🔍 Filtering & Selection

#### `where FIELD OPERATOR VALUE`

Filter records by condition.

| Operator | Meaning |
|----------|---------|
| `==`     | Equal (numeric or string) |
| `!=`     | Not equal |
| `>`  `<`  `>=`  `<=` | Numeric comparison |
| `like`   | Pattern match (`%` = wildcard, `_` = single char) |

```zsh
load products.csv | where price > 100
load users.csv    | where country like "%IL%"
load orders.csv   | where status != cancelled
```

#### `st-select FIELD [FIELD ...]`

Keep only the specified columns.

```zsh
load users.csv | st-select name email country | print_table
```

#### `distinct FIELD [FIELD ...]`

Remove duplicate rows based on the given fields.

```zsh
load logs.csv | distinct user_id | describe
```

---

### 🔃 Sorting & Shaping

#### `sort-by FIELD [--desc]`

Sort records by a field. Numeric-aware.

```zsh
load sales.csv | sort-by revenue --desc | head -n 10 | print_table
```

#### `head [-n N]` / `tail [-n N]`

Take the first or last N records (default: 10).

```zsh
load events.csv | sort-by timestamp | tail -n 5
```

---

### 📊 Analysis & Display

#### `describe`

Show all column names in the current dataset.

```zsh
load mystery.csv | describe
```

```
╭──────────────────╮
│ id               │
│ user             │
│ email            │
│ created_at       │
╰──────────────────╯
```

#### `histogram FIELD`

Show a frequency distribution of a field's values.

```zsh
load orders.csv | histogram status | print_table
```

```
┌───────────┬───────┬─────────┬───────────────────────────────┐
│ status    │ count │ percent │ frequency                     │
├───────────┼───────┼─────────┼───────────────────────────────┤
│ shipped   │   142 │  58.20% │ ████████████████████████████  │
│ pending   │    63 │  25.82% │ ████████████                  │
│ cancelled │    39 │  15.98% │ ███████                       │
└───────────┴───────┴─────────┴───────────────────────────────┘
```

#### `print_table [--less]`

Render any JSON pipeline as a formatted table. Use `--less` to page long output.

```zsh
load data.csv | where active == true | sort-by score --desc | print_table --less
```

---

### 🖥️ Interactive Exploration

#### `explore_table`

Full-screen interactive table browser. Supports sorting, column toggling, and row detail views. Outputs the current view as JSON when you exit, so you can keep piping.

| Key | Action |
|-----|--------|
| `↑` / `↓` | Navigate rows |
| `←` / `→` | Scroll columns |
| `Enter` | Full row detail view |
| `s` | Sort by current column |
| `c` | Show/hide columns |
| `q` | Exit and output results |

```zsh
load users.csv | explore_table | st-select name email | print_table
```

#### `explore_tree`

Interactive tree browser for hierarchical JSON data.

| Key | Action |
|-----|--------|
| `↑` / `↓` | Navigate nodes |
| `Enter` / `→` | Expand node |
| `←` | Collapse / go to parent |
| `q` | Exit |

```zsh
load project.json | explore_tree
```

```
▼ frontend
  ▼ components
    · Button.tsx
    · Modal.tsx
  ▶ pages
▶ backend
▶ docs
```

---

### 🌐 HTTP & APIs

#### `http METHOD URL [--header K:V] [--body JSON]`

Make HTTP requests. Responses are auto-parsed as JSON (or XML→JSON).

```zsh
# GET request
http GET https://api.github.com/repos/torvalds/linux/tags \
  | st-select name | head -n 5 | print_table

# POST with auth header and body
http POST https://api.example.com/users \
  --header "Authorization: Bearer $TOKEN" \
  --body '{"name": "Alice", "role": "admin"}'

# Interactive mode
http --interactive
```

#### `show_rss [--limit N] [--no-desc] [--width W]`

Display RSS or Atom feed items, piped from `http`.

```zsh
http GET https://feeds.bbci.co.uk/news/rss.xml | show_rss
http GET https://hnrss.org/frontpage            | show_rss --limit 5 --no-desc
http GET https://www.ynet.co.il/Integration/StoryRss2.xml | show_rss  # Hebrew ✓
```

```
BBC News
https://www.bbc.co.uk/news

  1. Scientists discover new deep-sea species
     2025-06-14 09:30 · Science
     https://www.bbc.com/news/science/...
     Researchers announced a major finding off the coast of New Zealand...

  2. Markets close higher amid trade optimism
     2025-06-14 11:45
     https://www.bbc.com/news/business/...
```

---

### 🔤 BiDi Text

#### `bidi [--rtl] [--ltr] [TEXT]`

Apply the Unicode Bidirectional Algorithm to correctly display Hebrew or Arabic text in a left-to-right terminal. Handles mixed RTL/LTR and preserves ANSI escape sequences.

```zsh
echo "Hello שלום world"  | bidi
bidi "مرحبا بالعالم"
bidi --rtl "some paragraph"
```

> **Note:** `show_rss` automatically applies BiDi to titles and descriptions — no extra piping needed.

---

## 🔗 Composing Pipelines

Because every command speaks JSON, you can chain them freely:

```zsh
# Top 5 countries by active user count
load users.csv \
  | where active == true \
  | histogram country \
  | head -n 5 \
  | print_table

# Explore a live API response interactively
http GET https://api.github.com/users/torvalds/repos \
  | where language == Python \
  | sort-by stargazers_count --desc \
  | explore_table

# Parse process list and find CPU hogs
ps aux \
  | parse_stzsh --input table \
  | sort-by %CPU --desc \
  | head -n 10 \
  | st-select PID %CPU %MEM COMMAND \
  | print_table

# Feed reader with Hebrew support
http GET https://www.ynet.co.il/Integration/StoryRss2.xml \
  | show_rss --limit 20
```

---

## 🗂️ Project Structure

```
stzsh/
├── stzsh.plugin.zsh     # Zsh function definitions
└── lib/
    ├── st_core.py        # Shared JSON I/O helpers
    ├── open_cmd.py       # load — file loading
    ├── parse_stzsh.py    # parse_stzsh — text → JSON
    ├── st_select.py      # st-select — column selection
    ├── where.py          # where — row filtering
    ├── sort_by.py        # sort-by — sorting
    ├── distinct.py       # distinct — deduplication
    ├── head_tail.py      # head / tail
    ├── describe.py       # describe — schema view
    ├── histogram.py      # histogram — frequency counts
    ├── print_table.py    # print_table — table renderer
    ├── explore_table.py  # explore_table — interactive table
    ├── explore_tree.py   # explore_tree — interactive tree
    ├── http_cmd.py       # http — HTTP client
    ├── show_rss.py       # show_rss — RSS/Atom reader
    └── bidi.py           # bidi — Unicode BiDi algorithm
```

---

## 🤝 Contributing

Pull requests welcome! Each command is a self-contained Python script in `lib/` — adding a new command is as simple as dropping a new `.py` file and registering a one-liner in `stzsh.plugin.zsh`.

---

## 📄 License

MIT
