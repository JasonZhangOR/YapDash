"""Match configured keywords against the text output of the speech recognizer."""

import re
from collections import defaultdict
from functools import lru_cache

from pypinyin import Style, lazy_pinyin


HAN = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff]+")
NEAR_INITIALS = {"zh": "z", "ch": "c", "sh": "s", "l": "n"}
NASALS = {"ang": "an", "eng": "en", "ing": "in", "iang": "ian", "uang": "uan"}
INITIAL = re.compile(r"^(zh|ch|sh|[bpmfdtnlgkhjqxrzcsyw])")


def fold(text):
    return "".join(text.casefold().split())


def syllables(text):
    readings = lazy_pinyin(text, style=Style.TONE3, neutral_tone_with_five=True, errors=list)
    return tuple((value[:-1], value[-1]) if value[-1:] in ("1", "2", "3", "4", "5")
                 else (value, "") for value in readings)


def nearby_syllable(left, right):
    def parts(base):
        match = INITIAL.match(base)
        end = match.end() if match else 0
        return base[:end], base[end:]

    left_initial, left_final = parts(left)
    right_initial, right_final = parts(right)
    return (
        left_final == right_final
        and NEAR_INITIALS.get(left_initial, left_initial) == NEAR_INITIALS.get(right_initial, right_initial)
    ) or (
        left_initial == right_initial
        and NASALS.get(left_final, left_final) == NASALS.get(right_final, right_final)
    )


def sound_cost(actual, expected):
    base_edits = 0
    tone_edits = 0
    for (base, tone), (target, target_tone) in zip(actual, expected):
        if base != target:
            if tone != target_tone or not nearby_syllable(base, target):
                return None
            base_edits += 1
        tone_edits += tone != target_tone
    # Short terms need more corroboration. Single characters require identical tones.
    if len(expected) == 1 and (base_edits or tone_edits):
        return None
    if base_edits + tone_edits > 1:
        return None
    return 2 * base_edits + tone_edits


@lru_cache(maxsize=4)
def phonetic_index(words):
    by_length = defaultdict(list)
    for word in words:
        if HAN.fullmatch(word):
            by_length[len(word)].append((word, syllables(word)))
    return by_length


def match_words(text, words, sound_words, whole_tokens=()):
    """Return full display text and matching words, including pronunciation corrections."""
    compact = []
    offsets = []
    for offset, char in enumerate(text):
        if not char.isspace():
            folded = char.casefold()
            compact.append(folded)
            offsets.extend([offset] * len(folded))
    folded = "".join(compact)
    matches = set()
    exact_spans = set()
    for word in words:
        needle = fold(word)
        if not needle:
            continue
        start = folded.find(needle)
        while start != -1:
            left = offsets[start]
            right = offsets[start + len(needle) - 1] + 1
            neighbors = text[max(0, left - 1):left] + text[right:right + 1]
            if needle not in whole_tokens or not any(char.isascii() and char.isalnum() for char in neighbors):
                matches.add(word)
                exact_spans.update(range(left, right))
            start = folded.find(needle, start + 1)

    index = phonetic_index(tuple(sorted(sound_words)))
    if not index:
        return text, [word for word in words if word in matches]
    candidates = []
    single = re.fullmatch(r"[\s，。！？、,.!?；;]*([\u3400-\u4dbf\u4e00-\u9fff])[\s，。！？、,.!?；;]*", text)
    for phrase in HAN.finditer(text):
        readings = syllables(phrase.group())
        for size, targets in index.items():
            if size == 1 and not single:
                continue
            for start in range(phrase.start(), phrase.end() - size + 1):
                end = start + size
                if not exact_spans.isdisjoint(range(start, end)):
                    continue
                relative_start = start - phrase.start()
                sounds = readings[relative_start:relative_start + size]
                scores = [(cost, word) for word, expected in targets
                          if (cost := sound_cost(sounds, expected)) is not None]
                if not scores:
                    continue
                best = min(cost for cost, _ in scores)
                winners = [word for cost, word in scores if cost == best]
                if len(winners) == 1:
                    candidates.append((best, -size, start, end, winners[0]))

    replacements = {}
    for _, _, start, end, word in sorted(candidates):
        span = range(start, end)
        if exact_spans.isdisjoint(span):
            replacements[start] = (end, word)
            exact_spans.update(span)
            matches.add(word)
    for start, (end, word) in sorted(replacements.items(), reverse=True):
        text = text[:start] + word + text[end:]
    return text, [word for word in words if word in matches]
