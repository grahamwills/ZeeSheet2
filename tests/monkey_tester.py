import random

import structure.validate

BLOCKS = [
    'one', 'two', 'three', 'four', 'five', '\n', '-', '*', '=====', ' ',
]

MIN_N = 5
MAX_N = 20
P_SPACE = 0.25


def random_phrase() -> str:
    r = random.randrange(MIN_N, MAX_N)
    parts = []
    for i in range(1, r):
        parts.append(random.choice(BLOCKS))
        if random.random() < P_SPACE:
            parts.append(' ')
    return ''.join(parts)


if __name__ == '__main__':
    for _ in range(0, 10000):
        phrase = random_phrase()
        try:
            result = structure.validate.build_sheet(phrase)
        except:
            print("Failed\n----------------------------------------------")
            print(phrase)
            print("----------------------------------------------")
