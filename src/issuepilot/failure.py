"""Name the reason an investigation produced no analysis.

Claude Code reports some failures as `subtype: success` with `is_error: true`
(a rejected token looked exactly like that in M1), so the job result alone is not
enough. The metrics come from the final `result` message of the run.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Failure:
    code: str
    message: str


MESSAGES = {
    "auth": (
        "Claude'a giriş yapılamadı. `CLAUDE_CODE_OAUTH_TOKEN` secret'ı geçersiz ya da "
        "süresi dolmuş olabilir: `claude setup-token` ile yeni bir token alıp secret'ı güncelleyin."
    ),
    "usage_limit": (
        "Claude aboneliğinin kullanım sınırına ulaşıldı. Sınır yenilendiğinde "
        "workflow'u elle yeniden çalıştırabilirsiniz."
    ),
    "max_turns": (
        "Araştırma adım sınırına ulaştı ve sonuç üretmeden durdu. Issue çok geniş "
        "olabilir; daha dar bir tarifle yeniden deneyin."
    ),
    "cancelled": "Araştırma zaman sınırına takıldı ya da elle iptal edildi.",
    "no_output": "Claude araştırmayı bitirdi ama beklenen biçimde bir sonuç vermedi.",
    "secret_detected": (
        "Analiz yayınlanmadı: içinde gizli anahtara benzeyen bir değer vardı. Issue metni "
        "agent'ı bir sırrı açığa çıkarmaya yönlendirmiş olabilir. Çalışma kaydını inceleyin "
        "ve gerekirse token'ları yenileyin."
    ),
    "not_started": (
        "Araştırma başlayamadı. `CLAUDE_CODE_OAUTH_TOKEN` secret'ının tanımlı olduğunu "
        "ve çalışma kaydındaki ilk hatayı kontrol edin."
    ),
}


def classify(investigate_result: str, metrics: dict | None) -> Failure:
    """investigate_result is the job result: success, failure, cancelled or skipped."""
    if investigate_result == "cancelled":
        return Failure("cancelled", MESSAGES["cancelled"])
    if not metrics:
        return Failure("not_started", MESSAGES["not_started"])

    status = metrics.get("api_error_status")
    text = (metrics.get("result") or "").lower()
    if status == 401 or "not logged in" in text or "authenticate" in text:
        code = "auth"
    elif status == 429 or "usage limit" in text or "rate limit" in text:
        code = "usage_limit"
    elif metrics.get("subtype") == "error_max_turns":
        code = "max_turns"
    else:
        code = "no_output"
    return Failure(code, MESSAGES[code])
