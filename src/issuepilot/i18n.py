"""The fixed text of the comment, in the languages IssuePilot ships.

Claude writes the analysis fields in the configured language itself; this module
only covers the labels and messages around them. A language without a table here
gets English labels around Claude's text.
"""

from __future__ import annotations

EN = {
    "kind": {
        "bug_analysis": "Bug analysis",
        "needs_info": "More information needed",
        "not_a_bug": "Looks like intended behaviour",
        "feature_request": "Feature request",
    },
    "confidence": {"high": "high", "medium": "medium", "low": "low"},
    "unverified_reason": {
        "outside_repository": "path points outside the repository",
        "file_not_found": "file not found",
        "empty_quote": "quote is empty",
        "quote_not_found": "quote not found in the file",
    },
    "confidence_label": "confidence",
    "confidence_lowered": " (lowered after checking)",
    "missing": "**Missing:**",
    "questions": "**Questions:**",
    "cause": "**Cause:**",
    "where": "**Where:**",
    "where_none": "**Where:** No verified location.",
    "fix": "**Suggestion:**",
    "unsure": "**Not sure about:**",
    "line_corrected": "Line numbers corrected during checking (the analysis said {start}-{end}).",
    "ref_not_found": "not found on GitHub",
    "confidence_lowered_note": "Confidence was lowered because of this.",
    "explanation": "Explanation",
    "evidence": "Evidence",
    "unverified": "Could not be verified",
    "related": "Related",
    "suggested_fixes": "Suggested fixes",
    "other_fixes": "Other options",
    "verification_steps": "How to verify",
    "assumptions": "Assumptions",
    "open_questions": "Open questions",
    "details_summary": "Evidence, verification steps and details",
    "turn": "{n} turn",
    "turns": "{n} turns",
    "seconds": "{n} s",
    "run_log": "run log",
    "read_only": "read-only, code not run",
    "failed_title": "Analysis failed",
    "reason": "**Reason:**",
    "failures": {
        "auth": (
            "Could not sign in to Claude. The `CLAUDE_CODE_OAUTH_TOKEN` secret may be invalid "
            "or expired: create a new token with `claude setup-token` and update the secret."
        ),
        "usage_limit": (
            "The Claude subscription's usage limit was reached. Re-run the workflow by hand "
            "once the limit resets."
        ),
        "max_turns": (
            "The investigation hit its step limit and stopped without a result. The issue may "
            "be too broad; try again with a narrower description."
        ),
        "budget": (
            "The investigation reached its spending limit (`max_cost_usd`) and stopped "
            "without a result. Raise the limit or narrow the issue, then re-run."
        ),
        "cancelled": "The investigation hit its time limit or was cancelled by hand.",
        "no_output": "Claude finished the investigation but did not return a result in the expected form.",
        "secret_detected": (
            "The analysis was not published: it contained a value that looks like a secret. "
            "The issue text may have steered the agent into revealing one. Check the run log "
            "and rotate tokens if needed."
        ),
        "not_started": (
            "The investigation could not start. Check that the `CLAUDE_CODE_OAUTH_TOKEN` secret "
            "is set, and look at the first error in the run log."
        ),
    },
}

TR = {
    "kind": {
        "bug_analysis": "Hata analizi",
        "needs_info": "Daha fazla bilgi gerekiyor",
        "not_a_bug": "Beklenen davranış gibi görünüyor",
        "feature_request": "Özellik isteği",
    },
    "confidence": {"high": "yüksek", "medium": "orta", "low": "düşük"},
    "unverified_reason": {
        "outside_repository": "yol repo dışını gösteriyor",
        "file_not_found": "dosya bulunamadı",
        "empty_quote": "alıntı boş",
        "quote_not_found": "alıntı dosyada bulunamadı",
    },
    "confidence_label": "güven",
    "confidence_lowered": " (kontrolden sonra düşürüldü)",
    "missing": "**Eksik olan:**",
    "questions": "**Sorular:**",
    "cause": "**Neden:**",
    "where": "**Nerede:**",
    "where_none": "**Nerede:** Doğrulanmış bir konum yok.",
    "fix": "**Öneri:**",
    "unsure": "**Emin olmadığım:**",
    "line_corrected": "Satır numarası kontrolde düzeltildi (analizde {start}-{end} yazıyordu).",
    "ref_not_found": "GitHub'da bulunamadı",
    "confidence_lowered_note": "Bu yüzden güven seviyesi düşürüldü.",
    "explanation": "Açıklama",
    "evidence": "Kanıtlar",
    "unverified": "Doğrulanamayanlar",
    "related": "İlgili kayıtlar",
    "suggested_fixes": "Çözüm önerileri",
    "other_fixes": "Diğer seçenekler",
    "verification_steps": "Doğrulama adımları",
    "assumptions": "Varsayımlar",
    "open_questions": "Açık sorular",
    "details_summary": "Kanıtlar, doğrulama adımları ve ayrıntılar",
    "turn": "{n} adım",
    "turns": "{n} adım",
    "seconds": "{n} sn",
    "run_log": "çalışma kaydı",
    "read_only": "salt okunur, kod çalıştırılmadı",
    "failed_title": "Analiz yapılamadı",
    "reason": "**Sebep:**",
    "failures": {
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
        "budget": (
            "Araştırma harcama sınırına (`max_cost_usd`) ulaştı ve sonuç üretmeden durdu. "
            "Sınırı yükseltin ya da issue'yu daraltıp yeniden çalıştırın."
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
    },
}

_TABLES = {"english": EN, "en": EN, "turkish": TR, "türkçe": TR, "tr": TR}


def text_for(language: str | None) -> dict:
    """The label table for a configured language name; English when there is none."""
    return _TABLES.get((language or "").strip().lower(), EN)
