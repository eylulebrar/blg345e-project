import json
import sys
from collections import deque

REQUIRED_TOP_KEYS = {"atomic_propositions", "initial_states", "states"}
REQUIRED_STATE_KEYS = {"labels", "transitions"}

# JSON içinde aynı anahtar iki kez yazılırsa Python sessizce sonuncuyu alır.
# Bunu yakalamak için tekrar eden anahtarları burada topluyoruz.
duplicate_keys = []


def fail(prefix, message):
    """Hata mesajını stderr'e yazar ve programı 1 koduyla bitirir."""
    print(f"[{prefix}]: {message}", file=sys.stderr)
    sys.exit(1)


def parse_args(argv):
    """'./my_checker --parse <dosya>' kullanımını kontrol eder, dosya yolunu döndürür."""
    if len(argv) != 3 or argv[1] != "--parse":
        print("Usage: ./my_checker --parse <model.json>", file=sys.stderr)
        sys.exit(2)
    return argv[2]


# ---------------------------------------------------------------- 1. JSON okuma

def remember_duplicates(pairs):
    """json.load her nesneyi oluştururken bunu çağırır; tekrar eden anahtarları kaydeder."""
    obj = {}
    for key, value in pairs:
        if key in obj:
            duplicate_keys.append(key)
        obj[key] = value
    return obj


def load_json(path):
    """Dosyayı açar ve JSON olarak çözer. Hata olursa SYNTAX ERROR verir."""
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f, object_pairs_hook=remember_duplicates)
    except OSError as e:
        fail("SYNTAX ERROR", f"Cannot read file '{path}': {e.strerror}")
    except json.JSONDecodeError as e:
        fail("SYNTAX ERROR", f"Invalid JSON at line {e.lineno}, column {e.colno}: {e.msg}")


# ------------------------------------------------------------ 2. Şema kontrolü

def type_name(value):
    """Python tipini JSON'daki adıyla döndürür (hata mesajlarında kullanmak için)."""
    if isinstance(value, bool):      # bool, int'in alt sınıfı olduğu için önce kontrol edilmeli
        return "boolean"
    if isinstance(value, dict):
        return "object"
    if isinstance(value, list):
        return "array"
    if isinstance(value, str):
        return "string"
    if isinstance(value, (int, float)):
        return "number"
    if value is None:
        return "null"
    return type(value).__name__


def check_keys(obj, expected, where):
    """obj'nin anahtarları tam olarak expected kümesi mi? Eksik veya fazla varsa hata."""
    keys = set(obj.keys())
    missing = expected - keys
    extra = keys - expected
    if missing:
        fail("SCHEMA ERROR", f"{where} is missing required key(s): {', '.join(sorted(missing))}")
    if extra:
        fail("SCHEMA ERROR", f"{where} contains unexpected key(s): {', '.join(sorted(extra))}")


def check_string_list(value, where):
    """value bir liste mi ve her elemanı string mi?"""
    if not isinstance(value, list):
        fail("SCHEMA ERROR", f"{where} must be an array, got {type_name(value)}")
    for i, item in enumerate(value):
        if not isinstance(item, str):
            fail("SCHEMA ERROR", f"{where}[{i}] must be a string, got {type_name(item)}")


def validate_schema(data):
    """JSON'un ödevdeki standart şemaya birebir uyduğunu kontrol eder."""
    if not isinstance(data, dict):
        fail("SCHEMA ERROR", f"Top-level value must be an object, got {type_name(data)}")
    check_keys(data, REQUIRED_TOP_KEYS, "Top-level object")

    check_string_list(data["atomic_propositions"], "'atomic_propositions'")
    check_string_list(data["initial_states"], "'initial_states'")

    states = data["states"]
    if not isinstance(states, dict):
        fail("SCHEMA ERROR", f"'states' must be an object, got {type_name(states)}")

    for state_id, state in states.items():
        where = f"State '{state_id}'"
        if not isinstance(state, dict):
            fail("SCHEMA ERROR", f"{where} must be an object, got {type_name(state)}")
        check_keys(state, REQUIRED_STATE_KEYS, where)
        check_string_list(state["labels"], f"{where} 'labels'")
        check_string_list(state["transitions"], f"{where} 'transitions'")



# ---------------------------------------------------------- 3. Graf yapısı

class Node:
    """Kripke yapısındaki bir durum."""

    def __init__(self, state_id, labels):
        self.id = state_id            # benzersiz kimlik
        self.labels = set(labels)     # bu durumda doğru olan önermeler
        self.successors = []          # gidilebilen Node nesneleri (sıralı)


class KripkeGraph:
    """Adjacency list: her durum kimliği -> Node."""

    def __init__(self):
        self.nodes = {}
        self.initial = []

    def transition_count(self):
        return sum(len(node.successors) for node in self.nodes.values())


def build_nodes(data):
    """Her state için bir Node oluşturur. Kenarlar sonra bağlanır."""
    graph = KripkeGraph()
    for state_id, state in data["states"].items():
        graph.nodes[state_id] = Node(state_id, state["labels"])
    return graph


def link_transitions(graph, data):
    """Kenarları kimlikler yerine doğrudan Node referanslarıyla bağlar."""
    for state_id, state in data["states"].items():
        node = graph.nodes[state_id]
        node.successors = [graph.nodes[target] for target in state["transitions"]]
    graph.initial = [graph.nodes[s] for s in data["initial_states"]]


# ------------------------------------------------- 4. Anlamsal kontroller

def find_duplicate(items):
    """Listede tekrar eden ilk elemanı döndürür, yoksa None."""
    seen = set()
    for item in items:
        if item in seen:
            return item
        seen.add(item)
    return None


def validate_semantics(data):
    """Ödevdeki 6 anlamsal kuralı kontrol eder."""
    states = data["states"]
    props = data["atomic_propositions"]
    initial = data["initial_states"]

    # Kural 6: boş state uzayı
    if not states:
        fail("SEMANTIC ERROR", "Model declares no states ('states' is empty).")

    # Kural 5: tekrar eden önerme ve başlangıç durumu
    dup = find_duplicate(props)
    if dup is not None:
        fail("SEMANTIC ERROR", f"Atomic proposition '{dup}' is declared more than once.")
    dup = find_duplicate(initial)
    if dup is not None:
        fail("SEMANTIC ERROR", f"Initial state '{dup}' is listed more than once.")

    # Kural 4: geçersiz başlangıç durumları
    if not initial:
        fail("SEMANTIC ERROR", "'initial_states' must contain at least one state.")
    for s in initial:
        if s not in states:
            fail("SEMANTIC ERROR", f"Initial state '{s}' is not declared in 'states'.")

    declared_props = set(props)
    for state_id, state in states.items():
        labels = state["labels"]
        transitions = state["transitions"]

        # Kural 5: state içinde tekrar
        dup = find_duplicate(labels)
        if dup is not None:
            fail("SEMANTIC ERROR", f"State '{state_id}' has duplicate label '{dup}'.")
        dup = find_duplicate(transitions)
        if dup is not None:
            fail("SEMANTIC ERROR", f"State '{state_id}' has duplicate transition to '{dup}'.")

        # Kural 2: tanımsız etiket
        for label in labels:
            if label not in declared_props:
                fail("SEMANTIC ERROR",
                     f"State '{state_id}' uses undeclared atomic proposition '{label}'.")

        # Kural 3: çıkışı olmayan durum (transition totality)
        if not transitions:
            fail("SEMANTIC ERROR",
                 f"State '{state_id}' has no outgoing transitions (use a self-loop for deadlocks).")

        # Kural 1: var olmayan duruma giden geçiş
        for target in transitions:
            if target not in states:
                fail("SEMANTIC ERROR",
                     f"State '{state_id}' references undeclared state '{target}'.")


# ---------------------------------------------------- 5. Erişilebilirlik (BFS)

def reachable_states(graph):
    """Başlangıç durumlarından BFS ile erişilebilen durumların kümesini döndürür."""
    visited = set()
    queue = deque()
    for node in graph.initial:
        visited.add(node.id)
        queue.append(node)

    while queue:
        node = queue.popleft()
        for succ in node.successors:
            if succ.id not in visited:
                visited.add(succ.id)
                queue.append(succ)
    return visited

# ---------------------------------------------------------------------- main

def main():
    path = parse_args(sys.argv)

    # Aşama 1: okuma, şema, graf düğümleri
    data = load_json(path)
    validate_schema(data)
    graph = build_nodes(data)

    # Aşama 2: anlamsal doğrulama, sonra kenarları bağlama
    if duplicate_keys:
        fail("SEMANTIC ERROR", f"Duplicate key '{duplicate_keys[0]}' declared more than once.")
    validate_semantics(data)
    link_transitions(graph, data)

    # Aşama 3: erişilebilirlik
    reachable = reachable_states(graph)
    total = len(graph.nodes)

    print(f"[PARSER]: Loaded {path} successfully.")
    print(f"[METRICS]: Total declared states: {total}")
    print(f"[METRICS]: Total transitions found: {graph.transition_count()}")
    print(f"[REACHABILITY]: Reachable states from initial node(s): {len(reachable)}")
    print(f"[DIAGNOSTICS]: Unreachable states detected: {total - len(reachable)}")
    
if __name__ == "__main__":
    main()