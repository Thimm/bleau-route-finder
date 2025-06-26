def grade_to_numeric(grade):
    """Convert climbing grade to numeric value for sorting."""
    grade_map = {
        '1a': 1, '1b': 2, '1c': 3,
        '2a': 4, '2b': 5, '2c': 6,
        '3a': 7, '3b': 8, '3c': 9,
        '4a': 10, '4b': 11, '4c': 12,
        '5a': 13, '5b': 14, '5c': 15,
        '6a': 16, '6a+': 17, '6b': 18, '6b+': 19, '6c': 20, '6c+': 21,
        '7a': 22, '7a+': 23, '7b': 24, '7b+': 25, '7c': 26, '7c+': 27,
        '8a': 28, '8a+': 29, '8b': 30, '8b+': 31, '8c': 32, '8c+': 33,
        '9a': 34, '': 0
    }
    return grade_map.get(grade, 0)


def numeric_to_grade(numeric):
    """Convert numeric value back to climbing grade."""
    grade_map = {
        1: '1a', 2: '1b', 3: '1c',
        4: '2a', 5: '2b', 6: '2c',
        7: '3a', 8: '3b', 9: '3c',
        10: '4a', 11: '4b', 12: '4c',
        13: '5a', 14: '5b', 15: '5c',
        16: '6a', 17: '6a+', 18: '6b', 19: '6b+', 20: '6c', 21: '6c+',
        22: '7a', 23: '7a+', 24: '7b', 25: '7b+', 26: '7c', 27: '7c+',
        28: '8a', 29: '8a+', 30: '8b', 31: '8b+', 32: '8c', 33: '8c+',
        34: '9a', 0: ''
    }
    return grade_map.get(numeric, '') 