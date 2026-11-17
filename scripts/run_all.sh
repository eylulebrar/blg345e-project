#!/bin/sh
# Runs my_checker on every model and test file, runs NuSMV on every .smv
# model, and stores all console outputs under report/outputs/ for the report.
#
# Usage (from the project root):   sh scripts/run_all.sh
# Requires NuSMV on the PATH.

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT" || exit 1
OUT=report/outputs
mkdir -p "$OUT/checker" "$OUT/nusmv"
MODELS="philosophers peterson abp railway elevator"

# --- 1. my_checker ---------------------------------------------------------
for f in models/*.json tests/*.json; do
    name=$(basename "$f" .json)
    {
        echo "\$ ./my_checker --parse $f"
        ./my_checker --parse "$f" 2>&1
        echo "(exit code: $?)"
    } > "$OUT/checker/$name.txt"
done
echo "my_checker outputs -> $OUT/checker/"

# --- 2. NuSMV --------------------------------------------------------------
if ! command -v NuSMV >/dev/null 2>&1; then
    echo "NuSMV not found on PATH, skipping NuSMV runs." >&2
    exit 1
fi
NuSMV -h 2>&1 | grep -m1 -i "NuSMV" > "$OUT/nusmv/version.txt"

# Runs one interactive command on a model; strips the banner and prompts.
nusmv_cmd() {
    printf 'go\n%s\nquit\n' "$2" | NuSMV -int "$1" 2>&1 \
        | grep -v '^\*\*\*' | sed 's/NuSMV > //g' | sed '/^[[:space:]]*$/d'
}

for m in $MODELS; do
    smv="models/$m.smv"
    {
        echo "\$ NuSMV -int $smv"
        for cmd in print_reachable_states check_invar check_ltlspec; do
            result=$(nusmv_cmd "$smv" "$cmd")
            if [ -n "$result" ]; then
                echo "NuSMV > $cmd"
                echo "$result"
            fi
        done
    } > "$OUT/nusmv/$m.txt"
    nusmv_cmd "$smv" "print_reachable_states -v" > "$OUT/nusmv/${m}_states.txt"
done
{
    echo "\$ NuSMV -int tests/switch_model.smv"
    echo "NuSMV > print_reachable_states"
    nusmv_cmd tests/switch_model.smv print_reachable_states
} > "$OUT/nusmv/switch_model.txt"
echo "NuSMV outputs -> $OUT/nusmv/"

# --- 3. Exact comparison of the reachable state sets -----------------------
: > "$OUT/nusmv/comparison.txt"
for m in $MODELS; do
    python3 scripts/compare_nusmv.py "$m" "$OUT/nusmv/${m}_states.txt" "models/$m.json" \
        >> "$OUT/nusmv/comparison.txt" 2>&1
done
cat "$OUT/nusmv/comparison.txt"
