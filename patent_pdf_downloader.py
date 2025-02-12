import logging
import re
from typing import Optional, Tuple

import requests

# Set up logging.
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PatentPDFDownloader:
    """
    Download USPTO patent PDFs via direct links.

    Supported formats:
      • Utility patents:
          - 7-digit patents (pad with leading zeros if necessary)
          - 8-digit patents (use as provided)
      • Design patents:
          - Format: D###### (pad to 6 digits if needed)
      • Plant patents:
          - Format: PP##### (pad to 5 digits if needed)
      • Published patent applications:
          - Format: yyyy####### (year plus 7-digit application number)

    Note: Direct links work only for documents with less than 1000 pages.
    """

    BASE_URL = ("https://image-ppubs.uspto.gov/dirsearch-public/print/"
                "downloadPdf/")

    def __init__(self) -> None:
        self.session = requests.Session()

    def _normalize_patent_id(
        self, patent_id: str,
        patent_type: Optional[str] = None
    ) -> Tuple[str, str]:
        """
        Strip extraneous text and format the patent id as expected.

        Auto-detection (if patent_type is not provided):
          • If the cleaned string starts with "D" and the rest are digits,
            treat as a design patent.
          • If it starts with "PP", treat as a plant patent.
          • If numeric:
              - 7 or fewer digits → utility (pad to 7 digits)
              - 8 digits → utility
              - 11 digits with a valid 4-digit year → published application

        With an override, you can force one of: "utility", "design",
        "plant", or "application".

        Args:
            patent_id (str): The input identifier.
            patent_type (Optional[str]): Optional override for patent type.

        Returns:
            Tuple[str, str]: The normalized patent id and its type.

        Raises:
            ValueError: If normalization fails.
        """
        # Remove common words and extra whitespace.
        candidate = patent_id.upper()
        candidate = re.sub(r'\b(?:US|PATENT|NO\.?)\b', '', candidate)
        candidate = candidate.strip().replace(" ", "")

        # If an override is provided, use that.
        if patent_type:
            patent_type = patent_type.lower()
            if patent_type == "design":
                if candidate.startswith("D"):
                    candidate = candidate[1:]
                if not candidate.isdigit():
                    raise ValueError(
                        "Design patent id must contain digits after 'D'."
                    )
                norm = "D" + candidate.zfill(6)
                return norm, "design"
            if patent_type == "plant":
                if candidate.startswith("PP"):
                    candidate = candidate[2:]
                if not candidate.isdigit():
                    raise ValueError(
                        "Plant patent id must contain digits after 'PP'."
                    )
                norm = "PP" + candidate.zfill(5)
                return norm, "plant"
            if patent_type == "application":
                if len(candidate) < 4 or not candidate[:4].isdigit():
                    raise ValueError(
                        "Published application id must start with a 4-digit year."
                    )
                year = candidate[:4]
                num = candidate[4:]
                norm = year + num.zfill(7)
                return norm, "application"
            if patent_type == "utility":
                if not candidate.isdigit():
                    raise ValueError(
                        "Utility patent id must be numeric."
                    )
                if len(candidate) <= 7:
                    norm = candidate.zfill(7)
                elif len(candidate) == 8:
                    norm = candidate
                else:
                    raise ValueError(
                        "Utility patent id must be 7 or 8 digits long."
                    )
                return norm, "utility"
            raise ValueError("Invalid patent_type override provided.")

        # Auto-detection if no override was given.
        if candidate.startswith("D") and candidate[1:].isdigit():
            norm = "D" + candidate[1:].zfill(6)
            return norm, "design"
        if candidate.startswith("PP") and candidate[2:].isdigit():
            norm = "PP" + candidate[2:].zfill(5)
            return norm, "plant"
        if candidate.isdigit():
            if len(candidate) <= 7:
                norm = candidate.zfill(7)
                return norm, "utility"
            if len(candidate) == 8:
                norm = candidate
                return norm, "utility"
            if len(candidate) == 11 and candidate[:4].isdigit():
                year = int(candidate[:4])
                if 1800 <= year <= 2100:
                    # Ensure the application number is 7 digits.
                    num = candidate[4:].zfill(7)
                    norm = candidate[:4] + num
                    return norm, "application"
                raise ValueError("11-digit id with invalid year.")
            raise ValueError("Ambiguous numeric patent id length.")
        raise ValueError("Could not determine patent type from input. "
                         "Specify a patent_type override.")

    def _build_url(self, normalized_id: str) -> str:
        """
        Build the complete URL for downloading the patent PDF.

        Args:
            normalized_id (str): The normalized patent id.

        Returns:
            str: The direct download URL.
        """
        url = self.BASE_URL + normalized_id
        logger.debug("Built URL: %s", url)
        return url

    def download_pdf(
        self, patent_id: str, patent_type: Optional[str] = None,
        output_file: Optional[str] = None, timeout: int = 30
    ) -> bytes:
        """
        Download the patent PDF using the direct link format.

        Args:
            patent_id (str): The input patent identifier.
            patent_type (Optional[str]): Optional override for patent type.
                Accepted values: "utility", "design", "plant", "application".
            output_file (Optional[str]): If provided, save the PDF to this file.
            timeout (int): HTTP request timeout in seconds.

        Returns:
            bytes: The PDF content.

        Raises:
            requests.RequestException: For HTTP request errors.
            ValueError: If patent id normalization fails.
        """
        norm_id, det_type = self._normalize_patent_id(patent_id,
                                                      patent_type)
        url = self._build_url(norm_id)
        logger.info("Downloading PDF for %s (type: %s) from %s",
                    patent_id, det_type, url)
        try:
            response = self.session.get(url, timeout=timeout)
            response.raise_for_status()
        except requests.RequestException as e:
            logger.error("Failed to download PDF: %s", e)
            raise

        if output_file:
            try:
                with open(output_file, "wb") as f:
                    f.write(response.content)
                logger.info("PDF saved to %s", output_file)
            except Exception as e:
                logger.error("Failed to write PDF to file: %s", e)
                raise
        return response.content


if __name__ == "__main__":
    downloader = PatentPDFDownloader()

    # Example inputs covering various cases:
    examples = [
        # Utility patents.
        ("11235876", None),    # 8-digit utility patent.
        ("4321", "utility"),   # Will be padded to 7 digits.
        # Design patents.
        ("D123456", None),
        ("123456", "design"),  # Override to design.
        # Plant patents.
        ("PP123", "plant"),    # Will be padded to PP00123.
        # Published applications.
        ("2020123456", "application"),  # Pad application number.
        ("20201234567", None)  # Auto-detect as published application.
    ]

    for pid, ptype in examples:
        try:
            pdf_content = downloader.download_pdf(pid, ptype)
            logger.info("Downloaded %d bytes for patent id %s",
                        len(pdf_content), pid)
        except Exception as err:
            logger.error("Error processing %s: %s", pid, err)

