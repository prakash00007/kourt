from pathlib import Path
import hashlib

from fastapi import UploadFile

from app.core.cache import RedisCacheService
from app.core.config import Settings
from app.core.exceptions import ServiceUnavailableError, ValidationError
from app.schemas.summary import SummaryResponse, SummarySections
from app.services.anonymizer import AnonymizerService
from app.services.llm import LLMService
from app.services.pdf_parser import PDFParser
from app.services.storage import StorageService
from app.utils.prompts import SUMMARY_PROMPT
from app.utils.text import truncate_text, clean_legal_text


class SummarizationService:
    def __init__(
        self,
        settings: Settings,
        llm_service: LLMService,
        cache_service: RedisCacheService,
        storage_service: StorageService,
        anonymizer_service: AnonymizerService,
    ):
        self.settings = settings
        self.llm_service = llm_service
        self.pdf_parser = PDFParser()
        self.cache = cache_service
        self.storage_service = storage_service
        self.anonymizer = anonymizer_service

    async def summarize_pdf(self, upload: UploadFile) -> tuple[SummaryResponse, str]:
        content = await upload.read()
        self._validate_upload(upload.filename, content)
        cache_key = hashlib.sha256(content).hexdigest()
        cached = await self.cache.get_json("summary", cache_key)
        if cached is not None:
            return SummaryResponse.model_validate(cached["response"]), cached["object_key"]

        self._validate_pdf_pages(content)
        object_key = await self.storage_service.upload_pdf(
            file_name=upload.filename or "uploaded-judgment.pdf",
            content=content,
            content_type=upload.content_type or "application/pdf",
        )
        raw_text = self.pdf_parser.extract_text_from_bytes(content)
        if len(clean_legal_text(raw_text).split()) < 80:
            raise ValidationError("The uploaded PDF does not contain enough extractable text for summarization.")

        anonymized = self.anonymizer.anonymize_text(raw_text)
        prompt = SUMMARY_PROMPT.format(text=truncate_text(anonymized.redacted_text, 3200))
        try:
            summary_text = await self.llm_service.complete(prompt, task="summarization")
            summary = self._parse_sections(self.anonymizer.deanonymize_text(summary_text, anonymized.mapping))
        except ServiceUnavailableError:
            summary = self._build_local_fallback_summary(raw_text)

        response = SummaryResponse(
            file_name=upload.filename or "uploaded-judgment.pdf",
            summary=summary,
            disclaimer=self.settings.disclaimer_text,
        )
        await self.cache.set_json(
            "summary",
            cache_key,
            {"response": response.model_dump(mode="json"), "object_key": object_key},
        )
        return response, object_key

    def _validate_upload(self, file_name: str | None, content: bytes) -> None:
        suffix = Path(file_name or "").suffix.lower()
        if suffix not in self.settings.allowed_upload_extensions:
            raise ValidationError("Unsupported file type. Please upload a PDF.")
        size_mb = len(content) / (1024 * 1024)
        if size_mb > self.settings.max_upload_size_mb:
            raise ValidationError(
                f"File is too large. Maximum allowed size is {self.settings.max_upload_size_mb} MB."
            )
        if not content.startswith(b"%PDF"):
            raise ValidationError("Invalid PDF file.")

    def _validate_pdf_pages(self, content: bytes) -> None:
        page_count = self.pdf_parser.get_page_count_from_bytes(content)
        if page_count > self.settings.max_upload_pages:
            raise ValidationError(
                f"PDF is too large. Maximum supported length is {self.settings.max_upload_pages} pages."
            )

    def _parse_sections(self, text: str) -> SummarySections:
        sections = {"facts": "", "issues": "", "judgment": "", "key_takeaways": ""}
        current_key = "facts"
        key_map = {
            "facts": "facts",
            "issues": "issues",
            "judgment": "judgment",
            "key takeaways": "key_takeaways",
        }

        for line in text.splitlines():
            lowered = line.strip().lower().strip(":")
            matched = False
            for heading, key in key_map.items():
                if lowered.startswith(heading):
                    current_key = key
                    remainder = line.split(":", 1)[1].strip() if ":" in line else ""
                    if remainder:
                        sections[current_key] += remainder + "\n"
                    matched = True
                    break
            if not matched:
                sections[current_key] += line.strip() + "\n"

        return SummarySections(
            facts=sections["facts"].strip() or "Not clearly identified from the uploaded judgment.",
            issues=sections["issues"].strip() or "Not clearly identified from the uploaded judgment.",
            judgment=sections["judgment"].strip() or "Not clearly identified from the uploaded judgment.",
            key_takeaways=sections["key_takeaways"].strip() or "Not clearly identified from the uploaded judgment.",
        )

    def _build_local_fallback_summary(self, text: str) -> SummarySections:
        cleaned = clean_legal_text(text)
        paragraphs = [paragraph.strip() for paragraph in cleaned.splitlines() if paragraph.strip()]
        facts = truncate_text(" ".join(paragraphs[:3]), 900)
        judgment = truncate_text(" ".join(paragraphs[-3:]), 900)

        issue_candidates = [
            paragraph
            for paragraph in paragraphs
            if "issue" in paragraph.lower() or "whether" in paragraph.lower() or "question" in paragraph.lower()
        ]
        issues = truncate_text(" ".join(issue_candidates[:3]), 700) if issue_candidates else (
            "The judgment raises issues that should be confirmed from the extracted text and the operative findings."
        )

        key_takeaways = "\n".join(
            [
                "Review the extracted facts and operative portion against the original PDF before relying on this summary.",
                "The core legal questions should be confirmed from the pleadings, issues framed, and final directions in the judgment.",
                "This is a local fallback summary generated because the external AI summarization service is unavailable.",
            ]
        )

        return SummarySections(
            facts=facts or "Not clearly identified from the uploaded judgment.",
            issues=issues,
            judgment=judgment or "Not clearly identified from the uploaded judgment.",
            key_takeaways=key_takeaways,
        )
