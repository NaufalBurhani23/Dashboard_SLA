from typing import Optional
from datetime import datetime

class SLA1Validator:
    @staticmethod
    def is_denominator(reg_ts: Optional[datetime]) -> bool:
        """
        Denominator SLA 1 = Seluruh record dengan Tanggal & Jam Registrasi (P+Q) valid.
        """
        return reg_ts is not None