import re

def test_DAG_regex(pattern, strings):
    """
    Tests a regex pattern against a list of strings and prints the results.
    """
    # We use re.fullmatch to ensure the entire string matches the pattern
    regex = re.compile(pattern)
    print(f"--- Testing Pattern: {pattern} ---\n")
    test_cases = [
        "D -> Y",
        "Z <-> {D, Y}",
        "Z -> {D, Y}",
        "{A, B} <- Y",
        "{A, B} <-> Y",
        "{A, B} -> {D, Y}",
        "{A, B} <- {D, Y}",
        "{A, B} <-> {D, Y}",
        "{A, B} <-< {D, Y}",
    ]


    for i, s in enumerate(strings):
        match = regex.fullmatch(s.strip())
        if match:
            # The groups will be [LHS, Arrow, RHS]
            lhs, arrow, rhs = match.groups()
            print(f"✅ Case {i+1}: '{s}' -> MATCH")
            print(f"   - LHS:   '{lhs}'")
            print(f"   - Arrow: '{arrow}'")
            print(f"   - RHS:   '{rhs}'\n")
        else:
            print(f"❌ Case {i+1}: '{s}' -> NO MATCH\n")


