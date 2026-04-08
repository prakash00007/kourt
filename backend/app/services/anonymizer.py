import re
from dataclasses import dataclass

try:
    from presidio_analyzer import AnalyzerEngine, Pattern, PatternRecognizer
    PRESIDIO_AVAILABLE = True
except Exception:  # pragma: no cover
    AnalyzerEngine = None
    Pattern = None
    PatternRecognizer = None
    PRESIDIO_AVAILABLE = False


@dataclass
class AnonymizationResult:
    redacted_text: str
    mapping: dict[str, str]


class AnonymizerService:
    PHONE_RE = re.compile(r"(?<!\d)(?:\+91[\s-]?)?[6-9]\d{9}(?!\d)")
    EMAIL_RE = re.compile(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[A-Za-z]{2,}\b")
    AADHAAR_RE = re.compile(r"(?<!\d)\d{4}[\s-]?\d{4}[\s-]?\d{4}(?!\d)")
    PAN_RE = re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b")
    NAME_RE = re.compile(
        r"\b(?:Mr|Mrs|Ms|Dr|Shri|Smt|Advocate|Adv\.|Applicant|Respondent|Petitioner|Accused)\.?\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2}\b"
    )
    PLAIN_FULL_NAME_RE = re.compile(r"\b[A-Z][a-z]{2,}(?:\s+[A-Z][a-z]{2,}){1,2}\b")

    def __init__(self):
        self._analyzer = self._build_presidio()

    def anonymize_text(self, text: str) -> AnonymizationResult:
        mapping: dict[str, str] = {}
        counters = {"PHONE": 0, "EMAIL": 0, "AADHAAR": 0, "PAN": 0, "PERSON": 0}
        redacted = text

        for label, pattern in [
            ("AADHAAR", self.AADHAAR_RE),
            ("PAN", self.PAN_RE),
            ("EMAIL", self.EMAIL_RE),
            ("PHONE", self.PHONE_RE),
            ("PERSON", self.NAME_RE),
            ("PERSON", self.PLAIN_FULL_NAME_RE),
        ]:
            redacted = self._replace_pattern(redacted, pattern, label, mapping, counters)

        if self._analyzer is not None:
            redacted = self._replace_presidio_entities(redacted, mapping, counters)

        return AnonymizationResult(redacted_text=redacted, mapping=mapping)

    def deanonymize_text(self, text: str, mapping: dict[str, str]) -> str:
        restored = text
        for placeholder, original in sorted(mapping.items(), key=lambda item: len(item[0]), reverse=True):
            restored = restored.replace(placeholder, original)
        return restored

    def _replace_pattern(
        self,
        text: str,
        pattern: re.Pattern[str],
        label: str,
        mapping: dict[str, str],
        counters: dict[str, int],
    ) -> str:
        def replacer(match: re.Match[str]) -> str:
            value = match.group(0).strip()
            if value.startswith("<") and value.endswith(">"):
                return value
            existing = self._find_existing_placeholder(mapping, value)
            if existing:
                return existing
            counters[label] += 1
            placeholder = f"<{label}_{counters[label]}>"
            mapping[placeholder] = value
            return placeholder

        return pattern.sub(replacer, text)

    def _replace_presidio_entities(
        self,
        text: str,
        mapping: dict[str, str],
        counters: dict[str, int],
    ) -> str:
        results = self._analyzer.analyze(text=text, language="en")
        filtered = [item for item in results if item.entity_type in {"PERSON", "EMAIL_ADDRESS", "PHONE_NUMBER"}]
        for item in sorted(filtered, key=lambda entity: entity.start, reverse=True):
            value = text[item.start:item.end]
            label = "PERSON" if item.entity_type == "PERSON" else "EMAIL" if item.entity_type == "EMAIL_ADDRESS" else "PHONE"
            existing = self._find_existing_placeholder(mapping, value)
            if existing:
                placeholder = existing
            else:
                counters[label] += 1
                placeholder = f"<{label}_{counters[label]}>"
                mapping[placeholder] = value
            text = f"{text[:item.start]}{placeholder}{text[item.end:]}"
        return text

    def _find_existing_placeholder(self, mapping: dict[str, str], value: str) -> str | None:
        for placeholder, original in mapping.items():
            if original == value:
                return placeholder
        return None

    def _build_presidio(self):
        if not PRESIDIO_AVAILABLE:
            return None
        try:
            analyzer = AnalyzerEngine()
            analyzer.registry.add_recognizer(
                PatternRecognizer(
                    supported_entity="AADHAAR",
                    patterns=[Pattern(name="aadhaar_pattern", regex=self.AADHAAR_RE.pattern, score=0.85)],
                )
            )
            analyzer.registry.add_recognizer(
                PatternRecognizer(
                    supported_entity="PAN",
                    patterns=[Pattern(name="pan_pattern", regex=self.PAN_RE.pattern, score=0.85)],
                )
            )
            return analyzer
        except Exception:
            return None
