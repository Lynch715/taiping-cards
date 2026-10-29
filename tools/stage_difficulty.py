"""Difficulty targets from docs/07 sections 3, 4.1 and 5.4."""

def target(row):
    chapter, order = int(row['chapter']), int(row['order'])
    if not 1 <= chapter <= 8 or not 1 <= order <= 6:
        raise ValueError('Invalid chapter/order')
    lo, hi = (95, 100) if order == 1 else (85, 95) if order < 4 else (70, 85) if order < 6 else (55, 70)
    if row['stage_id'] in {'qing_1_3', 'qing_2_3', 'qing_2_5'}:
        return .5, .65
    if chapter >= 3:
        if row['history_result'] not in {'胜', '败'}:
            raise ValueError('history_result must be 胜 or 败')
        if row['history_result'] == '败':
            lo, hi = max(50, lo - 10), max(50, hi - 10)
    return lo / 100, hi / 100
