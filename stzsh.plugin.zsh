STZSH_DIR="${0:A:h}"
function st-select()   { python3 "$STZSH_DIR/lib/st_select.py"   "$@" }
function sort-by()     { python3 "$STZSH_DIR/lib/sort_by.py"     "$@" }
function where()       { python3 "$STZSH_DIR/lib/where.py"       "$@" }
function print_table()  { python3 "$STZSH_DIR/lib/print_table.py"  "$@" }
function parse_stzsh()  { python3 "$STZSH_DIR/lib/parse_stzsh.py"  "$@" }
function describe()     { python3 "$STZSH_DIR/lib/describe.py"     "$@" }
function http()         { python3 "$STZSH_DIR/lib/http_cmd.py"     "$@" }
function head()         { python3 "$STZSH_DIR/lib/head_tail.py"    "$@" }
function tail()         { python3 "$STZSH_DIR/lib/head_tail.py"    "$@" }
function distinct()     { python3 "$STZSH_DIR/lib/distinct.py"     "$@" }
function load()         { python3 "$STZSH_DIR/lib/open_cmd.py"     "$@" }
function histogram()    { python3 "$STZSH_DIR/lib/histogram.py"    "$@" }
function explore_table() { python3 "$STZSH_DIR/lib/explore_table.py" "$@" }
function explore_tree()  { python3 "$STZSH_DIR/lib/explore_tree.py"  "$@" }
function bidi()          { python3 "$STZSH_DIR/lib/bidi.py"           "$@" }
function show_rss()      { python3 "$STZSH_DIR/lib/show_rss.py"       "$@" }
