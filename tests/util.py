from typing import Dict, Tuple, List


def _join_nicely(lines: List[str]) -> str:
    # join and remove trailing new line
    base = ''.join(lines)
    return base[:-1]


def test_data() -> Dict[str, Tuple[str, str]]:
    with open('tests/rst_sample.txt', 'rt') as f:
        lines = f.readlines()

    result = {}

    name = None
    a = []
    b = []
    target = None

    for line in lines:
        if line.startswith('#'):
            if line.startswith('##'):
                if target is a:
                    # Other string
                    target = b
                else:
                    # Finished a section; record it
                    assert target is b
                    assert name
                    result[name] = _join_nicely(a), _join_nicely(b)
                    # Reset
                    name, a, b = None, [], []
            else:
                # Defines a new name
                assert not name
                idx = line.find('#', 3)
                name = line[2:idx].strip()
                target = a
        else:
            target.append(line)

    return result
