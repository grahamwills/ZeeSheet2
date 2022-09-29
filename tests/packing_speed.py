import time
from random import Random
from typing import List

import main


def random_text(rand: Random):
    return rand.choice([
        "abc",
        "def",
        "[X][X][X]",
        "a longer line of text",
        "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor "
        "incididunt ut labore et dolore magna aliqua. "
    ])


def random_row(table_columns, rand):
    return '- ' + ' | '.join(random_text(rand) for _ in range(table_columns))


def random_block(table_columns, table_rows, rand):
    n_rows = rand.choice(table_rows)
    return random_text(rand) + '\n\n' + '\n'.join(random_row(table_columns, rand) for _ in range(n_rows))


def make_sheet(section_columns: int, block_count, table_columns: int, table_rows: List[int]):
    rand = Random(13)
    header = f'.. page:: width=800 height=10000\n.. section:: columns={section_columns}\n\n'
    return header + '\n\n'.join(random_block(table_columns, table_rows, rand) for _ in range(block_count))


def time_build(text: str) -> float:
    print('Running ...', end='', flush=True)
    t0 = time.time_ns()
    bytes = main.Document(text).data()
    t = (time.time_ns() - t0) / 1e9
    print(f' done ({len(bytes)} bytes)')
    return t


if __name__ == '__main__':
    SECTION_COLUMNS = 3
    BLOCK_COUNT = 10
    TABLE_COLUMN = 2
    TABLE_ROWS = list(range(3, 9))

    text = make_sheet(SECTION_COLUMNS, BLOCK_COUNT, TABLE_COLUMN, TABLE_ROWS)

    N = 3
    times = [time_build(text) for _ in range(N)]
    median = times[N // 2]
    print(f"TIME = {median:>8.4f}s | section_cols={SECTION_COLUMNS}, blocks={BLOCK_COUNT}, "
          f"table_cols={TABLE_COLUMN}, table_rows={TABLE_ROWS}")
