"""Perturbation engine for robustness testing.

Provides functions to create perturbed versions of prompts for
testing model robustness under various input modifications.
"""

from __future__ import annotations

import random
import re
from typing import Any

from evals.aviation_domain import SEMANTIC_EQUIVALENCES, NEARBY_AIRPORT_PAIRS


def paraphrase(prompt: str) -> str:
    """Rephrase the prompt while preserving meaning."""
    replacements = [
        ("What were the contributing factors", "What factors contributed to"),
        ("Analyze this", "Provide an analysis of this"),
        ("What was the", "Describe the"),
        ("go-around", "missed approach"),
        ("TCAS RA", "TCAS Resolution Advisory"),
        ("unstable approach", "unstabilized approach"),
        ("Was the decision appropriate", "Was the decision justified"),
        ("What procedures were not followed", "Which procedures were violated"),
        ("runway excursion", "departure from the runway surface"),
        ("Contributing factors", "Causal factors"),
        ("Assess this", "Evaluate this"),
    ]
    result = prompt
    applied = False
    for old, new in replacements:
        if old.lower() in result.lower() and not applied:
            pattern = re.compile(re.escape(old), re.IGNORECASE)
            result = pattern.sub(new, result, count=1)
            applied = True

    # If no replacement was found, add a minor rephrase
    if not applied:
        result = "Please provide your expert analysis: " + result

    return result


def inject_typo(prompt: str, target: str | None = None) -> str:
    """Inject a typo into the prompt, optionally targeting a specific string."""
    if target and target in prompt:
        typo = _make_typo(target)
        return prompt.replace(target, typo, 1)

    # Auto-detect ICAO codes and introduce typo
    icao_pattern = re.compile(r'\bK[A-Z]{3}\b')
    matches = icao_pattern.findall(prompt)
    if matches:
        target_code = random.choice(matches)
        typo = _make_typo(target_code)
        return prompt.replace(target_code, typo, 1)

    # Fallback: swap two adjacent characters in a word
    words = prompt.split()
    if len(words) > 3:
        idx = random.randint(1, len(words) - 2)
        word = words[idx]
        if len(word) > 3:
            pos = random.randint(1, len(word) - 2)
            word = word[:pos] + word[pos + 1] + word[pos] + word[pos + 2:]
            words[idx] = word
    return " ".join(words)


def inject_distractor(prompt: str, distractor: str | None = None) -> str:
    """Inject an irrelevant distractor into the prompt."""
    if distractor is None:
        distractors = [
            "Note: KSEA runway 16C/34C was also active during this period.",
            "Additionally, a Boeing 787 was holding on taxiway M.",
            "NOTAM: ILS RWY 09L GP OTS at KORD.",
            "Unrelated: Runway 27R at KBOS was closed for maintenance.",
            "A VFR aircraft was operating in the pattern at a nearby airport.",
        ]
        distractor = random.choice(distractors)

    # Insert distractor in the middle of the prompt
    sentences = prompt.split(". ")
    if len(sentences) > 1:
        mid = len(sentences) // 2
        sentences.insert(mid, distractor)
        return ". ".join(sentences)

    return prompt + " " + distractor


def swap_synonym(prompt: str, synonyms: dict[str, list[str]] | None = None) -> str:
    """Replace a term with its semantic equivalent."""
    synonyms = synonyms or SEMANTIC_EQUIVALENCES

    for canonical, equivalents in synonyms.items():
        for equiv in equivalents:
            if equiv.lower() in prompt.lower():
                # Pick a different equivalent
                others = [e for e in equivalents if e.lower() != equiv.lower()]
                if others:
                    replacement = random.choice(others)
                    pattern = re.compile(re.escape(equiv), re.IGNORECASE)
                    return pattern.sub(replacement, prompt, count=1)

    return prompt


def swap_nearby_airport(
    prompt: str,
    airport_pairs: list[tuple[str, str]] | None = None,
) -> str:
    """Swap an airport code with a nearby airport."""
    pairs = airport_pairs or NEARBY_AIRPORT_PAIRS

    for a, b in pairs:
        if a in prompt:
            return prompt.replace(a, b, 1)
        if b in prompt:
            return prompt.replace(b, a, 1)

    return prompt


def inject_conflicting_metar(prompt: str) -> str:
    """Inject conflicting weather data into the prompt."""
    conflicts = [
        "However, another weather source reported clear skies and visibility greater than 10SM.",
        "Note: A conflicting METAR from 30 minutes prior showed winds 360 at 5 knots, visibility 10SM.",
        "An ATIS recording from the same period indicated VMC conditions with CAVU.",
        "A pilot report from the same timeframe described calm winds and unlimited visibility.",
    ]
    return prompt + " " + random.choice(conflicts)


def _make_typo(text: str) -> str:
    """Create a plausible typo in a string."""
    if len(text) < 3:
        return text

    typo_type = random.choice(["swap", "substitute", "delete"])

    if typo_type == "swap" and len(text) > 2:
        pos = random.randint(1, len(text) - 2)
        return text[:pos] + text[pos + 1] + text[pos] + text[pos + 2:]
    elif typo_type == "substitute":
        pos = random.randint(0, len(text) - 1)
        # Substitute with a nearby letter
        char = text[pos]
        if char.isalpha():
            offset = random.choice([-1, 1])
            new_char = chr(ord(char) + offset)
            if new_char.isalpha():
                return text[:pos] + new_char + text[pos + 1:]
    elif typo_type == "delete" and len(text) > 3:
        pos = random.randint(1, len(text) - 2)
        return text[:pos] + text[pos + 1:]

    return text


# Mapping of perturbation type names to functions
PERTURBATION_FUNCTIONS = {
    "paraphrase": lambda p, _: paraphrase(p),
    "typo": lambda p, t: inject_typo(p, t),
    "distractor_injection": lambda p, d: inject_distractor(p, d),
    "synonym": lambda p, _: swap_synonym(p),
    "nearby_airport_swap": lambda p, _: swap_nearby_airport(p),
    "conflicting_metar": lambda p, _: inject_conflicting_metar(p),
}


def apply_perturbation(
    prompt: str,
    perturbation_type: str,
    target: str | None = None,
) -> str:
    """Apply a named perturbation to a prompt."""
    func = PERTURBATION_FUNCTIONS.get(perturbation_type)
    if func is None:
        raise ValueError(
            f"Unknown perturbation type: {perturbation_type}. "
            f"Available: {list(PERTURBATION_FUNCTIONS.keys())}"
        )
    return func(prompt, target)
