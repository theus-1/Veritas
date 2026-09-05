"""Compare explicit denials without treating keyword overlap as contradiction."""
import re
import unicodedata

from app.models.evidence import EvidenceVerdictEnum as Verdict


def normalize(text: str) -> str:
    text = "".join(c for c in unicodedata.normalize("NFKD", text.lower()) if not unicodedata.combining(c))
    text = re.sub(r"#(?=fake\b|fato\b)", "", text)
    # Same referent in the voting-machine example, including unaccented input.
    return re.sub(r"\burna eletronica\b", "urna", text)


LABEL = re.compile(
    r"^(?:e\s+)?(?P<label>falso|falsa|fake|verdadeiro|verdadeira|fato)"
    r"(?:\s+que\s+|\s*:\s*|\s+(?=(?:o\s+|a\s+)?(?:video|foto|imagem)\b))"
)
ARTICLES = {"a", "o", "as", "os", "um", "uma"}


def proposition(text: str):
    text = normalize(text).strip()
    if "?" in text:
        return None
    label = LABEL.match(text)
    denied = False
    if label:
        denied = label["label"] in {"falso", "falsa", "fake"}
        text = text[label.end():].strip()
    # Media authenticity is a separate proposition from whether an event occurred.
    media = re.match(r"^(?:o |a )?(video|foto|imagem) de\s+", text)
    if media:
        # Normalize only known reflexive action forms in media descriptions.
        # Keep the media prefix, entities, destinations, dates and negation intact.
        text = re.sub(r"\bse (?:jogou|jogando)\b", "reflexivo_jogar", text)
    # Avoid questions, reported allegations, hypotheticals and compound clauses.
    if re.search(r"\b(se|talvez|supostamente|teria|seria|poderia|boato|alega|diz|disse|afirma|que|mas|porem|e)\b", text):
        return None
    if re.search(r"\bnao (?:so|apenas)\b", text):
        return None
    words = re.findall(r"\w+", text)
    if words.count("nao") > 1:
        return None
    negated = "nao" in words
    words = tuple(word for word in words if word not in ARTICLES and word != "nao")
    if len(words) < 2:
        return None
    return words, denied != negated


def compare_explicit(claim: str, title: str, snippet: str):
    left = proposition(claim)
    if left is None:
        return None
    outcomes = set()
    has_label = False
    for part in (title, snippet):
        # Keep decimal points inside measurements; question marks stay in clauses.
        for sentence in re.split(r"(?<!\d)\.|\.(?!\d)|[!;]+", part):
            sentence = sentence.strip()
            labeled = bool(LABEL.match(normalize(sentence)))
            has_label |= labeled
            right = proposition(sentence)
            if right is None or left[0] != right[0]:
                continue
            explicit = labeled or "nao" in normalize(sentence).split() or "nao" in normalize(claim).split()
            if explicit:
                outcomes.add(Verdict.CONTRADICTS if left[1] != right[1] else Verdict.SUPPORTS)
    if len(outcomes) == 1:
        return outcomes.pop()
    if outcomes or has_label:
        # Conflicting statements or a check of a different proposition cannot vote.
        return Verdict.NEUTRAL
    return None
