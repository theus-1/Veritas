import re

from sqlalchemy.orm import Session

from app.models.analysis import Analysis
from app.models.claim import Claim
from app.models.evidence import Evidence, EvidenceVerdictEnum
from app.schemas.search import SearchResult
from app.services.explicit_verdict import compare_explicit


class EvidenceService:

    STOPWORDS = {
        "a", "à", "às", "ao", "aos", "as", "com", "como", "da", "das", "de",
        "do", "dos", "e", "em", "entre", "foi", "foram", "na", "nas", "no",
        "nos", "o", "os", "ou", "para", "por", "que", "se", "sem", "sobre",
        "um", "uma", "uns", "umas",
    }

    GENERIC_WORDS = {
        "afirma", "afirmou", "afirmação", "ano", "anos", "aconteceu",
        "acontece", "acontecer", "resultado", "resultados", "partida",
        "partidas", "jogo", "jogos", "vitória", "vitórias", "venceu",
        "vence", "vencer", "ganhou", "ganha", "ganhar", "país", "pessoa",
        "pessoas", "disse", "diz", "segundo", "sobre", "novo", "nova",
        "novos", "novas",
    }

    ACTION_GROUPS = [
        {
            "venceu", "vence", "vencer", "ganhou", "ganha", "ganhar",
            "derrotou", "derrota", "derrotar",
        },
        {
            "perdeu", "perde", "perder", "foi derrotado", "foi derrotada",
        },
        {
            "cresceu", "cresce", "crescimento", "aumentou", "aumenta",
            "aumento", "avançou", "avança", "subiu", "sobe", "alta",
        },
        {
            "caiu", "cai", "queda", "diminuiu", "diminui", "redução", "recuou", "recua", "reduziu",
        },
    ]

    NEGATION_WORDS = {
        "não",
        "nunca",
        "jamais",
        "nem",
    }

    MIN_RELEVANCE = 0.20
    MAX_EVIDENCES_PER_CLAIM = 5

    def prepare_results(
        self,
        claim_text: str,
        results: list[SearchResult],
    ) -> list[SearchResult]:
        if not results:
            return []

        # Primeiro ordenamos pela relevância
        # local.
        #
        # Assim, caso a mesma URL apareça
        # repetida, conservamos a versão
        # considerada mais relevante.

        ranked = sorted(
            results,
            key=lambda result: (
                self.calculate_relevance(
                    claim_text,
                    result,
                )
            ),
            reverse=True,
        )

        unique = {}

        for result in ranked:
            if not result.url:
                continue

            if result.url in unique:
                continue

            unique[result.url] = result

        return list(
            unique.values()
        )[
            :self.MAX_EVIDENCES_PER_CLAIM
        ]

    def create_evidences(
        self,
        db: Session,
        analysis: Analysis,
        claim: Claim,
        results: list[SearchResult],
        assessments=None,
    ):
        evidences = []

        for index, result in enumerate(
            results
        ):
            # =========================================
            # Avaliação local padrão
            # =========================================

            relevance = (
                self.calculate_relevance(
                    claim.text,
                    result,
                )
            )

            verdict = (
                self.determine_verdict(
                    claim.text,
                    result,
                )
            )

            reason = None

            # =========================================
            # Gemini substitui avaliação heurística
            # =========================================

            if assessments is not None:
                if index >= len(assessments):
                    raise ValueError(
                        "Quantidade de avaliações "
                        "do Gemini não corresponde "
                        "às evidências."
                    )

                assessment = assessments[index]

                relevance = self.calibrate_relevance(assessment.relevance)

                verdict = (
                    EvidenceVerdictEnum(
                        assessment.verdict
                    )
                )

                reason = (
                    assessment.reason.strip()
                    if assessment.reason
                    else None
                )

            # =========================================
            # Criação da evidência
            # =========================================

            evidence = Evidence(
                analysis_id=analysis.id,
                claim_id=claim.id,
                source_name=result.source_name,
                source_url=result.url,
                title=result.title,
                relevance=relevance,
                verdict=verdict.value,
                reason=reason,
            )

            evidences.append(
                evidence
            )

        # =========================================
        # Prioridade:
        #
        # directional > neutral
        # maior relevância > menor relevância
        # =========================================

        evidences.sort(
            key=lambda evidence: (
                evidence.verdict
                == EvidenceVerdictEnum
                .NEUTRAL
                .value,
                -evidence.relevance,
            )
        )

        # =========================================
        # Deduplicação por URL
        # =========================================

        unique = {}

        for evidence in evidences:
            unique.setdefault(
                evidence.source_url,
                evidence,
            )

        evidences = list(
            unique.values()
        )[
            :self.MAX_EVIDENCES_PER_CLAIM
        ]

        # =========================================
        # Persistência
        # =========================================

        for evidence in evidences:
            db.add(
                evidence
            )

        db.commit()

        for evidence in evidences:
            db.refresh(
                evidence
            )

        return evidences

    def calculate_relevance(
        self,
        claim_text: str,
        result: SearchResult,
    ) -> float:
        claim_words = self._extract_words(claim_text)

        if not claim_words:
            return 0.0

        title_words = self._extract_words(result.title)
        snippet_words = self._extract_words(result.snippet)

        specific_words = {
            word
            for word in claim_words
            if word not in self.GENERIC_WORDS
        }

        if not specific_words:
            specific_words = claim_words

        title_matches = specific_words.intersection(title_words)
        snippet_matches = specific_words.intersection(snippet_words)

        title_score = len(title_matches) / len(specific_words)
        snippet_score = len(snippet_matches) / len(specific_words)

        relevance = (
            title_score * 0.70
            + snippet_score * 0.30
        )

        return self.calibrate_relevance(relevance)

    @staticmethod
    def calibrate_relevance(relevance: float) -> float:
        # Lexical overlap and model scores are not measured probabilities.
        # Preserve the decision threshold, compress only the overconfident tail.
        value = max(0.0, min(relevance, 1.0))
        return round(value if value <= 0.9 else 0.9 + (value - 0.9) * 0.2, 2)

    def determine_verdict(
        self,
        claim_text: str,
        result: SearchResult,
    ) -> EvidenceVerdictEnum:
        relevance = self.calculate_relevance(
            claim_text,
            result,
        )

        # Evidência pouco relevante não pode ser usada
        # para afirmar ou negar uma claim.
        if relevance < self.MIN_RELEVANCE:
            return EvidenceVerdictEnum.NEUTRAL

        explicit_verdict = compare_explicit(claim_text, result.title, result.snippet)
        if explicit_verdict is not None:
            return explicit_verdict

        numeric_verdict = self._compare_measurements(claim_text, result)
        if numeric_verdict is not None:
            return numeric_verdict

        claim_text_normalized = claim_text.lower()

        claim_has_negation = self._has_negation(
            claim_text_normalized
        )

        claim_relation = self._extract_relation(
            claim_text_normalized
        )

        evidence_parts = [
            result.title,
            result.snippet,
        ]

        evidence_relations = []

        for part in evidence_parts:
            if not part:
                continue

            sentences = re.split(
                r"[.!?;]+",
                part.lower(),
            )

            for sentence in sentences:
                sentence = sentence.strip()

                if not sentence:
                    continue

                relation = self._extract_relation(
                    sentence
                )

                if relation:
                    sentence_has_negation = self._has_negation(
                        sentence
                    )

                    evidence_relations.append(
                        (
                            relation,
                            sentence_has_negation,
                        )
                    )

        if claim_relation:
            for evidence_relation, evidence_has_negation in evidence_relations:

                relation_verdict = self._compare_relations(
                    claim_relation,
                    evidence_relation,
                )

                if relation_verdict == EvidenceVerdictEnum.CONTRADICTS:
                    return EvidenceVerdictEnum.CONTRADICTS

                if relation_verdict == EvidenceVerdictEnum.SUPPORTS:
                    if claim_has_negation != evidence_has_negation:
                        return EvidenceVerdictEnum.CONTRADICTS

                    return EvidenceVerdictEnum.SUPPORTS

            if evidence_relations:
                return EvidenceVerdictEnum.NEUTRAL

        claim_action = self._find_action(
            claim_text_normalized
        )

        evidence_action = None
        evidence_has_negation = False

        for part in evidence_parts:
            if not part:
                continue

            action = self._find_action(
                part.lower()
            )

            if action:
                evidence_action = action
                evidence_has_negation = self._has_negation(
                    part.lower()
                )
                break

        if claim_action is None or evidence_action is None:
            return EvidenceVerdictEnum.NEUTRAL

        if self._actions_are_opposite(
            claim_action,
            evidence_action,
        ):
            return EvidenceVerdictEnum.CONTRADICTS

        if self._actions_are_equivalent(
            claim_action,
            evidence_action,
        ):
            if claim_has_negation != evidence_has_negation:
                return EvidenceVerdictEnum.CONTRADICTS

            return EvidenceVerdictEnum.SUPPORTS

        return EvidenceVerdictEnum.NEUTRAL

    def _normalize_context(self, text: str) -> str:
        text = text.lower()
        text = re.sub(r"produto interno bruto", "pib", text)
        text = re.sub(r"\bpib brasileiro\b", "pib do brasil", text)
        for number, word in enumerate(("primeiro", "segundo", "terceiro", "quarto"), 1):
            text = re.sub(rf"\b{number}[º°o]?\s*(?:trimestre|tri)\b", f"{word} trimestre", text)
        return text

    def _measurement(self, text: str):
        text = self._normalize_context(text)
        actions = self.ACTION_GROUPS[2] | self.ACTION_GROUPS[3]
        pattern = r"\b(" + "|".join(sorted(actions, key=len, reverse=True)) + r")\b"
        matches = list(re.finditer(pattern, text))
        # Multiple predicates need syntactic disambiguation; do not guess.
        if len(matches) != 1:
            return None
        match = matches[0]
        subject = self._extract_words(text[:match.start()]) - {"taxa"}
        if not subject:
            return None
        years = re.findall(r"\b(?:19|20)\d{2}\b", text)
        period = re.search(
            r"(primeiro|segundo|terceiro|quarto) (trimestre|semestre)"
            r"|\b(?:janeiro|fevereiro|março|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro)\b",
            text,
        )
        basis = None
        if re.search(r"ano anterior|anual|interanual", text):
            basis = "annual"
        elif re.search(r"trimestre anterior|primeiro trimestre|trimestral", text[period.end():] if period else text):
            basis = "quarterly"
        percentages = re.findall(r"(-?\d+(?:[.,]\d+)?)\s*%", text[match.end():])
        value = float(percentages[0].replace(",", ".")) if len(percentages) == 1 else None
        return subject, match.group() in self.ACTION_GROUPS[2], years[:1], period.group() if period else None, basis, value, self._has_negation(text)

    def _compare_measurements(self, claim: str, result: SearchResult):
        left = self._measurement(claim)
        if left is None:
            # An economic predicate must not fall through to generic verb matching.
            words = self._extract_words(claim)
            if words & (self.ACTION_GROUPS[2] | self.ACTION_GROUPS[3]):
                return EvidenceVerdictEnum.NEUTRAL
            return None
        outcomes = set()
        for part in (result.title, result.snippet):
            for sentence in re.split(r"(?<!\d)\.|\.(?!\d)|[!?;]+", part):
                right = self._measurement(sentence)
                if right is None:
                    continue
                subject, up, years, period, basis, value, negated = right
                if subject != left[0]:
                    continue
                if left[2] and years and left[2] != years:
                    continue
                if left[3] and period and left[3] != period:
                    continue
                if left[4] and basis and left[4] != basis:
                    continue
                # Missing an explicitly claimed date does not establish that event.
                if (left[2] and not years) or (left[3] and not period):
                    continue
                if left[6] or negated:
                    if left[1] == up and left[5] == value and left[6] != negated:
                        outcomes.add(EvidenceVerdictEnum.CONTRADICTS)
                    continue
                if left[1] != up:
                    outcomes.add(EvidenceVerdictEnum.CONTRADICTS)
                elif left[5] is not None and value is not None:
                    outcomes.add(EvidenceVerdictEnum.SUPPORTS if abs(left[5] - value) <= 0.05 else EvidenceVerdictEnum.CONTRADICTS)
                elif left[5] is None:
                    outcomes.add(EvidenceVerdictEnum.SUPPORTS)
        return outcomes.pop() if len(outcomes) == 1 else EvidenceVerdictEnum.NEUTRAL

    def _extract_relation(
        self,
        text: str,
    ) -> tuple[str, str, str] | None:

        sentences = re.split(
            r"[.!?;]+",
            text.lower(),
        )

        winning_actions = {
            "venceu",
            "vence",
            "vencer",
            "ganhou",
            "ganha",
            "ganhar",
            "derrotou",
            "derrota",
            "derrotar",
        }

        losing_actions = {
            "perdeu",
            "perde",
            "perder",
        }

        for sentence in sentences:
            sentence = re.sub(
                r"[^\w\s]",
                " ",
                sentence,
            )

            words = sentence.split()

            if not words:
                continue

            for index, word in enumerate(words):

                if word in winning_actions:
                    if index == 0:
                        continue

                    subject_index = index - 1

                    while (
                        subject_index >= 0
                        and (
                            words[subject_index] in self.STOPWORDS
                            or words[subject_index] in self.NEGATION_WORDS
                        )
                    ):
                        subject_index -= 1

                    if subject_index < 0:
                        continue

                    subject = self._clean_entity(
                        words[subject_index]
                    )

                    object_words = words[index + 1:]

                    stop_object = {
                        "por",
                        "com",
                        "na",
                        "no",
                        "nas",
                        "nos",
                        "pela",
                        "pelo",
                        "pelas",
                        "pelos",
                        "em",
                    }

                    cleaned_object_words = []

                    for object_word in object_words:
                        if object_word in stop_object:
                            break

                        if object_word in self.NEGATION_WORDS:
                            continue

                        if object_word in self.STOPWORDS:
                            continue

                        cleaned_object_words.append(
                            object_word
                        )

                        if len(cleaned_object_words) >= 3:
                            break

                    if not cleaned_object_words:
                        continue

                    object_entity = self._clean_entity(
                        " ".join(cleaned_object_words)
                    )

                    if not subject or not object_entity:
                        continue

                    return (
                        subject,
                        "WIN",
                        object_entity,
                    )

                if word in losing_actions:
                    if index == 0:
                        continue

                    subject_index = index - 1

                    while (
                        subject_index >= 0
                        and (
                            words[subject_index] in self.STOPWORDS
                            or words[subject_index] in self.NEGATION_WORDS
                        )
                    ):
                        subject_index -= 1

                    if subject_index < 0:
                        continue

                    subject = self._clean_entity(
                        words[subject_index]
                    )

                    remaining_words = words[index + 1:]

                    if "para" in remaining_words:
                        separator_index = remaining_words.index(
                            "para"
                        )

                        object_words = remaining_words[
                            separator_index + 1:
                        ]

                    elif "contra" in remaining_words:
                        separator_index = remaining_words.index(
                            "contra"
                        )

                        object_words = remaining_words[
                            separator_index + 1:
                        ]

                    else:
                        object_words = remaining_words

                    stop_object = {
                        "por",
                        "com",
                        "na",
                        "no",
                        "nas",
                        "nos",
                        "pela",
                        "pelo",
                        "pelas",
                        "pelos",
                        "em",
                    }

                    cleaned_object_words = []

                    for object_word in object_words:
                        if object_word in stop_object:
                            break

                        if object_word in self.STOPWORDS:
                            continue

                        cleaned_object_words.append(
                            object_word
                        )

                        if len(cleaned_object_words) >= 3:
                            break

                    if not cleaned_object_words:
                        continue

                    object_entity = self._clean_entity(
                        " ".join(cleaned_object_words)
                    )

                    if not subject or not object_entity:
                        continue

                    return (
                        subject,
                        "LOSE",
                        object_entity,
                    )

        return None

    def _clean_entity(
        self,
        entity: str,
    ) -> str:

        words = entity.lower().split()

        words = [
            word
            for word in words
            if (
                word not in self.STOPWORDS
                and word not in {
                    "pela",
                    "pelo",
                    "pelas",
                    "pelos",
                }
            )
        ]

        return " ".join(words).strip()

    def _compare_relations(
        self,
        claim_relation: tuple[str, str, str],
        evidence_relation: tuple[str, str, str],
    ) -> EvidenceVerdictEnum | None:

        claim_subject, claim_action, claim_object = claim_relation

        evidence_subject, evidence_action, evidence_object = (
            evidence_relation
        )

        same_direction = (
            claim_subject == evidence_subject
            and claim_object == evidence_object
        )

        reversed_direction = (
            claim_subject == evidence_object
            and claim_object == evidence_subject
        )

        if same_direction:
            if claim_action == evidence_action:
                return EvidenceVerdictEnum.SUPPORTS

            if (
                claim_action == "WIN"
                and evidence_action == "LOSE"
            ) or (
                claim_action == "LOSE"
                and evidence_action == "WIN"
            ):
                return EvidenceVerdictEnum.CONTRADICTS

        if reversed_direction:
            if claim_action == "WIN":
                if evidence_action == "WIN":
                    return EvidenceVerdictEnum.CONTRADICTS

                if evidence_action == "LOSE":
                    return EvidenceVerdictEnum.SUPPORTS

            if claim_action == "LOSE":
                if evidence_action == "LOSE":
                    return EvidenceVerdictEnum.CONTRADICTS

                if evidence_action == "WIN":
                    return EvidenceVerdictEnum.SUPPORTS

        return None

    def _find_action(
        self,
        text: str,
    ) -> str | None:

        normalized_text = re.sub(
            r"[^\w\s]",
            " ",
            text.lower(),
        )

        words = normalized_text.split()

        for action_group in self.ACTION_GROUPS:
            for action in action_group:

                action_words = action.split()

                if len(action_words) == 1:
                    if action in words:
                        return action

                else:
                    phrase = " ".join(action_words)

                    if phrase in normalized_text:
                        return action

        return None

    def _actions_are_equivalent(
        self,
        first_action: str,
        second_action: str,
    ) -> bool:

        for group in self.ACTION_GROUPS:
            if (
                first_action in group
                and second_action in group
            ):
                return True

        return False

    def _actions_are_opposite(
        self,
        first_action: str,
        second_action: str,
    ) -> bool:

        winning_actions = {
            "venceu",
            "vence",
            "vencer",
            "ganhou",
            "ganha",
            "ganhar",
            "derrotou",
            "derrota",
            "derrotar",
        }

        losing_actions = {
            "perdeu",
            "perde",
            "perder",
            "foi derrotado",
            "foi derrotada",
        }

        return (
            (
                first_action in winning_actions
                and second_action in losing_actions
            )
            or
            (
                first_action in losing_actions
                and second_action in winning_actions
            )
        )

    def _has_negation(
        self,
        text: str,
    ) -> bool:

        words = self._extract_words(
            text,
            include_stopwords=True,
        )

        return bool(
            words.intersection(
                self.NEGATION_WORDS
            )
        )

    def _extract_words(
        self,
        text: str,
        include_stopwords: bool = False,
    ) -> set[str]:

        text = self._normalize_context(text)

        text = re.sub(
            r"[^\w\s]",
            " ",
            text,
        )

        words = text.split()

        if include_stopwords:
            return {
                word
                for word in words
                if len(word) > 2
            }

        return {
            word
            for word in words
            if (
                word not in self.STOPWORDS
                and len(word) > 2
            )
        }
