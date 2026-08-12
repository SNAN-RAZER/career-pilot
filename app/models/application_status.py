from enum import Enum


class ApplicationStatus(str, Enum):

    PENDING = "PENDING"

    APPLIED = "APPLIED"

    INTERVIEW = "INTERVIEW"

    OFFER = "OFFER"

    REJECTED = "REJECTED"