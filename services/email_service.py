"""
Universal Email Delivery Service for ScholarPilot AI.
Primary provider: Resend API (HTTP REST API, no SMTP blocked ports).
Fallback provider: Gmail / Custom SMTP.
Local test fallback: Safe mock delivery logger.

Includes:
- Email Service Abstraction Layer (EmailService class)
- Inbox Deliverability Optimization (SPF / DKIM / DMARC / List-Unsubscribe / Precedence)
- 4 High-Conversion Responsive HTML Templates with Plain Text Fallbacks:
  1. New Scholarship Match Alert
  2. Scholarship Deadline Reminder
  3. Welcome & Profile Confirmation
  4. Weekly Curated Scholarship Digest
"""

import os
import json
import base64
import logging
import asyncio
import smtplib
from datetime import datetime, timezone
from email.message import EmailMessage
from typing import Optional, List, Dict, Any, Tuple
import httpx

from services.security_utils import sanitize_email_header

logger = logging.getLogger("scholarpilot.email")

RESEND_API_URL = "https://api.resend.com/emails"

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
DAILY_QUOTA_FILE = os.path.join(DATA_DIR, "daily_email_quota.json")
MAX_DAILY_EMAILS = 85  # Strict safety cap below Resend's 100/day hard limit


class DailyEmailTracker:
    """
    Enforces a strict daily email cap (safety cap at 85 emails/day against Resend's 100/day limit).
    Tracks UTC date to prevent quota exhaustion and circuit-breaker tripping.
    """
    @staticmethod
    def _get_today_utc() -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    @classmethod
    def get_quota_status(cls) -> Dict[str, Any]:
        today = cls._get_today_utc()
        data = {"date": today, "sent_count": 0, "daily_cap": MAX_DAILY_EMAILS, "remaining": MAX_DAILY_EMAILS}
        if os.path.exists(DAILY_QUOTA_FILE):
            try:
                with open(DAILY_QUOTA_FILE, "r", encoding="utf-8") as f:
                    stored = json.load(f)
                    if stored.get("date") == today:
                        count = stored.get("sent_count", 0)
                        data["sent_count"] = count
                        data["remaining"] = max(0, MAX_DAILY_EMAILS - count)
            except Exception as e:
                logger.warning(f"Error reading daily quota file: {e}")
        return data

    @classmethod
    def can_send_email(cls) -> bool:
        status = cls.get_quota_status()
        return status["sent_count"] < MAX_DAILY_EMAILS

    @classmethod
    def record_email_sent(cls) -> int:
        os.makedirs(DATA_DIR, exist_ok=True)
        today = cls._get_today_utc()
        status = cls.get_quota_status()
        new_count = status["sent_count"] + 1
        record = {
            "date": today,
            "sent_count": new_count,
            "daily_cap": MAX_DAILY_EMAILS,
            "remaining": max(0, MAX_DAILY_EMAILS - new_count),
            "last_sent_at": datetime.now(timezone.utc).isoformat()
        }
        try:
            tmp = f"{DAILY_QUOTA_FILE}.tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(record, f, indent=2)
            os.replace(tmp, DAILY_QUOTA_FILE)
        except Exception as e:
            logger.error(f"Error writing daily email quota: {e}")
        return new_count

_last_dispatch_meta: Dict[str, Any] = {
    "success": False,
    "provider": None,
    "recipient": None,
    "error_detail": None,
    "hint": None,
    "raw_resend_error": None
}


def get_last_dispatch_meta() -> Dict[str, Any]:
    """Returns the diagnostic metadata from the last email dispatch attempt."""
    return dict(_last_dispatch_meta)


# =====================================================================
# HTML EMAIL TEMPLATES & PLAIN TEXT GENERATION ("ACADEMIC HORIZON" SYSTEM)
# =====================================================================

def _email_wrapper(title: str, preheader: str, body_html: str, cta_url: str = "", cta_text: str = "") -> str:
    """Wraps template body in a resilient, responsive email design in the official EduAtlas 3-color brand identity."""
    cta_block = ""
    if cta_url and cta_text:
        cta_block = f"""
        <table border="0" cellpadding="0" cellspacing="0" width="100%" style="margin: 28px 0;">
          <tr>
            <td align="center">
              <a href="{cta_url}" target="_blank" style="background: linear-gradient(135deg, #16324F, #0D1F31); color: #F4F1EA; text-decoration: none; padding: 14px 30px; border-radius: 8px; font-weight: bold; font-size: 15px; display: inline-block; box-shadow: 0 4px 14px rgba(22,50,79,0.35); border: 1px solid #B99050;">
                {cta_text} &larr;
              </a>
            </td>
          </tr>
        </table>
        """

    return f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta http-equiv="X-UA-Compatible" content="IE=edge">
  <title>{title}</title>
  <style>
    body, table, td, p, a {{ font-family: 'Cairo', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; }}
    body {{ margin: 0; padding: 0; background-color: #0B1724; color: #F4F1EA; }}
    .container {{ max-width: 600px; margin: 0 auto; background-color: #111E2E; border: 1px solid rgba(185,144,80,0.3); border-radius: 12px; overflow: hidden; }}
    .header {{ background: linear-gradient(135deg, #16324F 0%, #0D1F31 100%); padding: 24px 20px; text-align: center; border-bottom: 1px solid rgba(185,144,80,0.3); }}
    .content {{ padding: 28px 24px; direction: rtl; text-align: right; line-height: 1.7; font-size: 15px; color: #F4F1EA; }}
    .badge {{ display: inline-block; padding: 4px 12px; border-radius: 9999px; font-size: 12px; font-weight: bold; }}
    .badge-gold {{ background: rgba(185,144,80,0.2); border: 1px solid #B99050; color: #F4F1EA; }}
    .badge-terracotta {{ background: rgba(200,100,70,0.2); border: 1px solid #C86446; color: #F4F1EA; }}
    .card {{ background-color: #162638; border: 1px solid rgba(185,144,80,0.25); border-radius: 10px; padding: 18px; margin: 18px 0; }}
    .footer {{ background-color: #0B1724; padding: 20px 24px; text-align: center; font-size: 12px; color: #94A3B8; border-top: 1px solid rgba(185,144,80,0.2); }}
    .footer a {{ color: #B99050; text-decoration: none; font-weight: 600; }}
    .bidi-ltr {{ display: inline-block; direction: ltr !important; unicode-bidi: isolate; font-family: monospace; }}
  </style>
</head>
<body style="margin: 0; padding: 20px 0; background-color: #0B1724;">
  <span style="display:none;font-size:1px;color:#0B1724;line-height:1px;max-height:0px;max-width:0px;opacity:0;overflow:hidden;">
    {preheader}
  </span>
  <table border="0" cellpadding="0" cellspacing="0" width="100%">
    <tr>
      <td align="center">
        <div class="container" style="max-width: 600px; background-color: #111E2E; border: 1px solid rgba(185,144,80,0.3); border-radius: 12px;">
          <!-- Unified Header Banner: EduAtlas Cartographic Compass -->
          <div class="header" style="background: linear-gradient(135deg, #16324F 0%, #0D1F31 100%); padding: 24px 20px; text-align: center; border-bottom: 1px solid rgba(185,144,80,0.3); border-top-left-radius: 12px; border-top-right-radius: 12px;">
            <table border="0" cellpadding="0" cellspacing="0" width="100%">
              <tr>
                <td align="center">
                  <div style="display: inline-block; margin-bottom: 6px;">
                    <span style="font-size: 22px; font-weight: 900; color: #FFFFFF; letter-spacing: -0.5px;">
                      Edu<span style="color: #C86446;">Atlas</span>
                    </span>
                    <span style="font-size: 11px; background: rgba(185,144,80,0.25); color: #F4F1EA; border: 1px solid #B99050; padding: 2px 8px; border-radius: 999px; font-weight: bold; margin-right: 6px;">
                      رادار المنح الذكي
                    </span>
                  </div>
                  <div style="font-size: 11px; color: #B99050; font-weight: 500;">
                    نظام الملاحة والرادار الأكاديمي للقبول والمنح العالمية
                  </div>
                </td>
              </tr>
            </table>
          </div>
          <div class="content" style="padding: 28px 24px; color: #F4F1EA; direction: rtl; text-align: right;">
            {body_html}
            {cta_block}
          </div>
          <!-- Unified Footer Links -->
          <div class="footer" style="padding: 20px 24px; font-size: 12px; color: #94A3B8; text-align: center; border-top: 1px solid rgba(185,144,80,0.2);">
            <p style="margin: 0 0 10px 0; line-height: 1.6;">تصلك هذه الرسالة بناءً على اشتراكك المعتمد في رادار EduAtlas للمنح الدراسية الدولية.</p>
            <p style="margin: 0; line-height: 1.8;">
              <a href="https://eduatlas-irxv.onrender.com/dashboard" style="color: #B99050;">لوحة تحكم المنح</a> &bull;
              <a href="https://eduatlas-irxv.onrender.com/assistant" style="color: #C86446;">المستشار الذكي واستوديو الوثائق</a> &bull;
              <a href="https://eduatlas-irxv.onrender.com/#radarSection" style="color: #F4F1EA;">دليل المنح المفتوحة</a>
            </p>
          </div>
        </div>
      </td>
    </tr>
  </table>
 </body>
</html>"""


def render_smart_radar_digest_template(
    student_name: str,
    matches: List[Dict[str, Any]],
    student_profile: Optional[Dict[str, Any]] = None
) -> Tuple[str, str]:
    """
    Renders the consolidated 'Smart Radar Digest Email' aggregating multiple newly discovered matches
    into a single email per scan in the official EduAtlas brand identity.
    """
    count = len(matches)
    card_html_blocks = []
    plain_text_blocks = []

    for idx, item in enumerate(matches, start=1):
        sch = item.get("scholarship") or item
        title = sch.get("name") or sch.get("title", f"منحة دراسية #{idx}")
        score = int(item.get("match_score") or sch.get("match_score") or 88)
        country = sch.get("country", "")
        univ = sch.get("university", "")
        degree = sch.get("degree", "جميع المراحل")
        deadline = sch.get("deadline_display") or sch.get("deadline", "قريباً")
        coverage = sch.get("coverage", "تمويل كامل")
        link = sch.get("link") or sch.get("official_link", "https://eduatlas-irxv.onrender.com")
        reasons = item.get("reasons") or item.get("strengths") or sch.get("reasons") or [
            f"متوافقة مع تخصصك ومرحلتك الدراسية ({degree})",
            f"مفتوحة للتقديم مع كوتا داعمة للطلبة الفلسطينيين في {country}"
        ]
        reasons_items = "".join([f"<li style='margin-bottom:4px; color:#E2E8F0;'>{r}</li>" for r in reasons[:2]])

        card_html_blocks.append(f"""
        <div style="background:#162638; border:1px solid rgba(185,144,80,0.3); border-top:3px solid #B99050; border-radius:10px; padding:18px; margin-bottom:18px; box-shadow:0 4px 12px rgba(0,0,0,0.2);">
          <table border="0" cellpadding="0" cellspacing="0" width="100%" style="margin-bottom:10px;">
            <tr>
              <td align="right">
                <span style="background:#16324F; color:#F4F1EA; font-weight:bold; font-size:12px; padding:4px 10px; border-radius:6px; display:inline-block; border:1px solid #B99050;">
                  🎯 نسبة التطابق: {score}%
                </span>
              </td>
              <td align="left">
                <span style="color:#C86446; font-size:12px; font-weight:bold;">
                  ⏰ الموعد: {deadline}
                </span>
              </td>
            </tr>
          </table>
          <h3 style="color:#FFFFFF; margin:8px 0 6px 0; font-size:16px; font-weight:bold;">{title}</h3>
          <p style="color:#B99050; font-size:13px; margin:0 0 10px 0;">
            📍 {country} {f'— {univ}' if univ else ''} &bull; 🎓 {degree} &bull; 💰 {coverage}
          </p>
          <ul style="padding-right:18px; margin:0 0 14px 0; font-size:13px; line-height:1.6; color:#E2E8F0;">
            {reasons_items}
          </ul>
          <div style="text-align:left;">
            <a href="{link}" target="_blank" style="background:linear-gradient(135deg, #16324F, #0D1F31); color:#F4F1EA; text-decoration:none; padding:8px 18px; border-radius:6px; font-size:13px; font-weight:bold; display:inline-block; border:1px solid #B99050;">
              عرض التفاصيل والتقديم &larr;
            </a>
          </div>
        </div>
        """)

        plain_text_blocks.append(
            f"{idx}. {title} ({score}% تطابق)\n"
            f"   الدولة: {country} | المرحلة: {degree} | الموعد: {deadline}\n"
            f"   الرابط: {link}\n"
        )

    all_cards_html = "\n".join(card_html_blocks)
    name = student_name or (student_profile.get("full_name") if student_profile else None) or "عزيزي الطالب"

    body_html = f"""
    <div style="text-align:center; margin-bottom:24px;">
      <div style="display:inline-block; background:#16324F; color:#B99050; padding:6px 16px; border-radius:999px; font-size:12px; font-weight:bold; margin-bottom:12px; border:1px solid rgba(185,144,80,0.4);">
        ⚡ تقرير رادار EduAtlas الموحد
      </div>
      <h2 style="color:#FFFFFF; margin:0 0 8px 0; font-size:22px; font-weight:800;">
        مرحباً {name}، رصدنا لك {count} فرص دراسية جديدة!
      </h2>
      <p style="color:#CBD5E1; font-size:14px; margin:0; line-height:1.6;">
        تم العثور على هذه الفرص الجديدة ومطابقتها آلياً مع سجلك الأكاديمي وتخصصك. جمعناها لك في تقرير ذكي واحد لحفظ وقتك:
      </p>
    </div>

    {all_cards_html}

    <div style="background:#0D1F31; border:1px solid rgba(185,144,80,0.3); border-radius:8px; padding:14px; text-align:center; margin-top:20px;">
      <p style="color:#F4F1EA; font-size:13px; margin:0; font-weight:bold;">
        💡 نصيحة EduAtlas: جهّز مسودة خطاب الدافع (SOP) واستخرج كشوف الدرجات مبكراً لتفادي ضغط المواعيد النهائية.
      </p>
    </div>
    """

    subject = f"🎯 رادار EduAtlas الذكي: تم رصد {count} فرص دراسية جديدة متطابقة مع ملفك" if count > 1 else f"🎯 رادار EduAtlas: تم رصد فرصة دراسية جديدة متطابقة ({matches[0].get('name', matches[0].get('title', ''))})"
    preheader = f"اكتشف رادار EduAtlas {count} منح دراسية جديدة متوافقة مع ملفك الأكاديمي."

    html = _email_wrapper(
        title=subject,
        preheader=preheader,
        body_html=body_html,
        cta_url="https://eduatlas-irxv.onrender.com/dashboard",
        cta_text="فتح لوحة التحكم ومتابعة المنح"
    )

    plain_text = (
        f"{subject}\n\n"
        f"مرحباً {name}،\n"
        f"قام رادار EduAtlas برصد {count} فرص دراسية جديدة تطابق ملفك الأكاديمي:\n\n"
        + "\n".join(plain_text_blocks)
        + "\nتفضل بزيارة لوحة التحكم: https://eduatlas-irxv.onrender.com/dashboard\n"
    )

    return html, plain_text


def render_new_match_template(
    student_name: str,
    scholarship: Dict[str, Any],
    match_score: int = 90,
    reasons: Optional[List[str]] = None
) -> Tuple[str, str]:
    """1. New Scholarship Match Alert Template (HTML + Plain text) with Mixed-Direction Text Protection."""
    title = scholarship.get("name") or scholarship.get("title", "منحة دراسية جديدة")
    country = scholarship.get("country", "")
    university = scholarship.get("university", "")
    degree = scholarship.get("degree", "جميع المراحل")
    deadline = scholarship.get("deadline_display") or scholarship.get("deadline", "قريباً")
    coverage = scholarship.get("coverage", "تمويل كامل")
    link = scholarship.get("link", "https://scholarpilot-ai-mkac.onrender.com")

    # Match Score color scheme based on prompt
    badge_class = "badge-emerald" if match_score >= 85 else ("badge-violet" if match_score >= 70 else "badge-amber")
    score_color = "#10B981" if match_score >= 85 else ("#8B5CF6" if match_score >= 70 else "#F59E0B")

    reasons_list = reasons or [
        f"المستوى الدراسي المطلوب: {degree}",
        f"الدولة المستهدفة: {country}",
        f"نسبة القبول التقديرية بناءً على سجلك الأكاديمي: {match_score}%"
    ]
    reasons_html = "".join([f"<li style='margin-bottom:6px; color:#CBD5E1;'>{r}</li>" for r in reasons_list])

    body_html = f"""
    <div style="text-align: center; margin-bottom: 22px;">
      <span class="badge {badge_class}" style="padding: 5px 14px; font-size: 13px;">
        🎯 رصد تطابق أكاديمي بنسبة <span class="bidi-ltr" style="font-weight: 800; color:{score_color};">{match_score}%</span>
      </span>
      <h2 style="color: #FFFFFF; margin: 14px 0 6px 0; font-size: 21px; font-weight: 800;">مرحباً {student_name or 'عزيزي الطالب'}، وجدنا لك فرصة مميزة!</h2>
      <p style="color: #94A3B8; font-size: 14px; margin: 0;">قام رادار المنح باكتشاف فرصة دراسية تطابق ملفك الأكاديمي ومعاييرك المسجلة بدقة عالية.</p>
    </div>

    <div class="card" style="background:#1E293B; border:1px solid #334155; border-radius:10px; padding:18px; margin:18px 0;">
      <h3 style="color:#60A5FA; margin:0 0 14px 0; font-size:18px; font-weight:800;">
        <span class="bidi-ltr">{title}</span>
      </h3>
      <table border="0" cellpadding="5" cellspacing="0" width="100%" style="font-size:14px; color:#CBD5E1;">
        <tr>
          <td width="32%" style="color:#94A3B8;">🌍 الدولة / الجامعة:</td>
          <td><strong>{country}</strong> {f'&bull; <span class="bidi-ltr">(' + university + ')</span>' if university else ''}</td>
        </tr>
        <tr>
          <td style="color:#94A3B8;">📜 المرحلة الدراسية:</td>
          <td><strong>{degree}</strong></td>
        </tr>
        <tr>
          <td style="color:#94A3B8;">💰 التغطية المالية:</td>
          <td><span style="color:#34D399; font-weight:bold;">{coverage}</span></td>
        </tr>
        <tr>
          <td style="color:#94A3B8;">⏰ الموعد النهائي:</td>
          <td><span class="bidi-ltr" style="color:#F59E0B; font-weight:bold;">{deadline}</span></td>
        </tr>
      </table>
    </div>

    <div style="margin: 20px 0;">
      <h4 style="color:#FFFFFF; margin:0 0 10px 0; font-size:15px; font-weight:700;">لماذا تم ترشيح هذه المنحة لملفك الأكاديمي؟</h4>
      <ul style="padding-right: 20px; margin: 0;">
        {reasons_html}
      </ul>
    </div>
    """

    html = _email_wrapper(
        title=f"🎯 فرصة منحة جديدة: {title}",
        preheader=f"منحة جديدة مطابقة لملفك الأكاديمي بنسبة {match_score}%: {title}",
        body_html=body_html,
        cta_url=link,
        cta_text="التقديم عبر البوابة الرسمية للمنحة"
    )

    plain_text = f"""مرحباً {student_name or 'عزيزي الطالب'}،

🎯 وجدنا لك منحة دراسية مطابقة لملفك الأكاديمي بنسبة {match_score}%:
المنحة: {title}
الدولة: {country} ({university})
المرحلة: {degree}
التمويل: {coverage}
الموعد النهائي: {deadline}

للتقديم الرسمي عبر بوابة المنحة:
{link}

لوحة التحكم والمستشار الذكي:
https://scholarpilot-ai-mkac.onrender.com/dashboard

ScholarPilot AI - مستشارك الأكاديمي
"""
    return html, plain_text


def render_deadline_reminder_template(
    student_name: str,
    scholarship: Dict[str, Any],
    days_left: int = 7,
    milestone: str = "تجهيز الوثائق النهائية",
    community_highlight: Optional[Dict[str, Any]] = None
) -> Tuple[str, str]:
    """2. Scholarship Deadline Reminder Template enriched with countdown alerts and mixed-direction wrap."""
    title = scholarship.get("name") or scholarship.get("title", "المنحة المحفوظة")
    country = scholarship.get("country", "")
    deadline = scholarship.get("deadline_display") or scholarship.get("deadline", "قريباً")
    link = scholarship.get("link", "https://scholarpilot-ai-mkac.onrender.com")

    # Rose Danger if < 7 days, Amber Warning if < 30 days
    if days_left < 7:
        badge_html = f'<span class="badge badge-rose" style="padding:5px 14px; font-size:13px;">🚨 تنبيه حرج: متبقي <span class="bidi-ltr">{days_left}</span> أيام فقط على الإغلاق</span>'
        deadline_color = "#EF4444"
    else:
        badge_html = f'<span class="badge badge-amber" style="padding:5px 14px; font-size:13px;">⚠️ تذكير بالموعد النهائي: متبقي <span class="bidi-ltr">{days_left}</span> يوماً</span>'
        deadline_color = "#F59E0B"

    # If no community highlight was explicitly passed, attempt to fetch from community service
    if community_highlight is None:
        try:
            from services.community_service import community_service
            sch_id = scholarship.get("id") or title
            community_highlight = community_service.get_scholarship_tips_highlight(str(sch_id))
        except Exception:
            community_highlight = None

    community_html = ""
    community_plain = ""
    if community_highlight and community_highlight.get("golden_tip"):
        tip = community_highlight["golden_tip"]
        author = community_highlight.get("author_name", "باحث مقبول")
        uni = community_highlight.get("university", "")
        year = community_highlight.get("acceptance_year", "")
        author_info = f"{author} ({uni} - {year})" if uni else author

        community_html = f"""
        <div class="card" style="background:#0F172A; border-right:4px solid #38BDF8; border-radius:8px; padding:16px; margin:18px 0; border:1px solid #1E293B;">
          <div style="color:#38BDF8; font-weight:bold; font-size:14px; margin-bottom:6px;">
            💡 نصيحة ذهبية من مجتمع المقبولين في <span class="bidi-ltr">{title}</span>:
          </div>
          <p style="margin:0; color:#E2E8F0; font-size:13px; line-height:1.6;">
            &ldquo;{tip}&rdquo;
          </p>
          <div style="color:#94A3B8; font-size:12px; margin-top:8px;">
            &mdash; <span class="bidi-ltr">{author_info}</span>
          </div>
        </div>
        """
        community_plain = f"""
💡 نصيحة من طالب تم قبوله سابقاً في هذه المنحة:
"{tip}" — {author_info}
"""

    body_html = f"""
    <div style="text-align: center; margin-bottom: 20px;">
      {badge_html}
      <h2 style="color: #FFFFFF; margin: 12px 0 6px 0; font-size: 20px; font-weight:800;">تنبيه اقتراب إغلاق باب التقديم الرسمي</h2>
      <p style="color: #94A3B8; font-size: 14px; margin: 0;">منحة <span class="bidi-ltr font-latin">{title}</span> تقترب من الموعد النهائي المحدد (<span class="bidi-ltr" style="color:{deadline_color}; font-weight:bold;">{deadline}</span>).</p>
    </div>

    <div class="card" style="background:#1E293B; border:1px solid #334155; border-radius:8px; padding:18px; margin:18px 0;">
      <h3 style="color:#F59E0B; margin:0 0 10px 0; font-size:16px; font-weight:700;">خطوة التجهيز الموصى بها حالياً: {milestone}</h3>
      <p style="margin:0 0 12px 0; color:#CBD5E1; font-size:14px;">
        لضمان قبول طلبك وتفادي الضغط التقني في الساعات الأخيرة، ننصحك برفع الوثائق التالية عبر بوابة التقديم:
      </p>
      <ul style="padding-right: 20px; margin: 0; color:#CBD5E1; font-size:14px;">
        <li>كشف العلامات المترجم والمصدق رسميّاً.</li>
        <li>خطاب الدوافع (<span class="bidi-ltr">Statement of Purpose</span>) بعد مراجعته في استوديو الوثائق بالذكاء الاصطناعي.</li>
        <li>رسالتا التوصية الأكاديميتان وتأكيد معلومات الأساتذة.</li>
      </ul>
    </div>
    {community_html}
    """

    html = _email_wrapper(
        title=f"⚠️ تذكير موعد نهائي: {title} (متبقي {days_left} أيام)",
        preheader=f"متبقي {days_left} أيام على إغلاق منحة {title} - أكمل تقديمك الآن",
        body_html=body_html,
        cta_url=link,
        cta_text="فتح بوابة التقديم الرسمية واستكمال الطلب"
    )

    plain_text = f"""مرحباً {student_name or 'عزيزي الطالب'}،

⚠️ تذكير اقتراب الموعد النهائي:
منحة: {title} ({country})
متبقي: {days_left} أيام فقط
الموعد النهائي: {deadline}
المرحلة الحالية: {milestone}
{community_plain}
رابط بوابة التقديم:
{link}

ScholarPilot AI - مستشارك الأكاديمي
"""
    return html, plain_text


def render_welcome_template(
    student_name: str,
    email: str,
    profile: Optional[Dict[str, Any]] = None
) -> Tuple[str, str]:
    """3. Welcome Email Template."""
    profile = profile or {}
    degree = profile.get("degree", "بكالوريوس / ماجستير")
    gpa = profile.get("gpa", "85%")
    country = profile.get("country", "فلسطين")
    majors = ", ".join(profile.get("majors", ["تكنولوجيا المعلومات"]))

    body_html = f"""
    <div style="text-align: center; margin-bottom: 20px;">
      <span class="badge badge-emerald" style="padding: 5px 14px; font-size: 13px;">
        🎉 أهلاً بك في ScholarPilot AI
      </span>
      <h2 style="color: #FFFFFF; margin: 12px 0 6px 0; font-size: 21px; font-weight:800;">تم تفعيل نظام رادار واقتناص المنح بنجاح!</h2>
      <p style="color: #94A3B8; font-size: 14px; margin: 0;">أهلاً بك يا {student_name or 'عزيزي الطالب'}. تم حفظ معاييرك الأكاديمية بنجاح.</p>
    </div>

    <div class="card" style="background:#1E293B; border:1px solid #334155; border-radius:10px; padding:18px; margin:18px 0;">
      <h3 style="color:#60A5FA; margin:0 0 12px 0; font-size:16px; font-weight:700;">ملفك الأكاديمي المسجل:</h3>
      <table border="0" cellpadding="5" cellspacing="0" width="100%" style="font-size:14px; color:#CBD5E1;">
        <tr><td width="35%" style="color:#94A3B8;">المرحلة:</td><td><strong>{degree}</strong></td></tr>
        <tr><td style="color:#94A3B8;">المعدل:</td><td><span class="bidi-ltr" style="font-weight:bold; color:#34D399;">{gpa}</span></td></tr>
        <tr><td style="color:#94A3B8;">التخصصات المستهدفة:</td><td><span class="bidi-ltr">{majors}</span></td></tr>
        <tr><td style="color:#94A3B8;">الدولة الحالية:</td><td>{country}</td></tr>
      </table>
    </div>

    <div style="margin: 20px 0; color:#CBD5E1; font-size:14px;">
      <p><strong style="color:#FFFFFF;">ما الذي سيحدث الآن؟</strong></p>
      <ul style="padding-right: 20px;">
        <li>سيقوم رادار الذكاء الاصطناعي بمطابقة كل منحة جديدة فور فتحها مع ملفك.</li>
        <li>ستصلك تقارير أسبوعية بأفضل الفرص المتاحة وتنبيهات المواعيد الحرجة.</li>
        <li>يمكنك في أي وقت استخدام استوديو الوثائق الذكي لكتابة وتصدير خطابات الدافع ورسائل التوصية.</li>
      </ul>
    </div>
    """

    html = _email_wrapper(
        title="🎉 أهلاً بك في ScholarPilot AI - تم تفعيل حسابك",
        preheader="تم تفعيل حسابك الأكاديمي في ScholarPilot AI ورادار المنح جاهز لتنبيهك",
        body_html=body_html,
        cta_url="https://scholarpilot-ai-mkac.onrender.com/dashboard",
        cta_text="زيارة لوحة التحكم واستكشاف المنح"
    )

    plain_text = f"""أهلاً بك {student_name or 'عزيزي الطالب'} في ScholarPilot AI!

تم تفعيل حسابك وتثبيت معايير ملفك الأكاديمي:
- المرحلة: {degree}
- المعدل: {gpa}
- التخصصات: {majors}

سيعمل النظام آلياً على إرسال تنبيهات المنح المطابقة فور صدورها.

لوحة التحكم:
https://scholarpilot-ai-mkac.onrender.com/dashboard

ScholarPilot AI
"""
    return html, plain_text


def render_weekly_digest_template(
    student_name: str,
    top_matches: List[Dict[str, Any]],
    closing_soon: Optional[List[Dict[str, Any]]] = None,
    advice: str = ""
) -> Tuple[str, str]:
    """4. Weekly Scholarship Digest Template."""
    matches_html = ""
    for item in top_matches[:4]:
        name = item.get("name", "منحة دراسية")
        country = item.get("country", "")
        deadline = item.get("deadline_display") or item.get("deadline", "قريباً")
        score = item.get("matchScore") or item.get("match_score", 90)
        link = item.get("link", "https://scholarpilot-ai-mkac.onrender.com")
        matches_html += f"""
        <div style="background:#1E293B; border:1px solid #334155; border-radius:8px; padding:14px; margin-bottom:12px;">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
            <strong style="color:#FFFFFF; font-size:15px;"><span class="bidi-ltr">{name}</span></strong>
            <span class="badge badge-emerald" style="padding:2px 8px; font-size:11px;"><span class="bidi-ltr">{score}% تطابق</span></span>
          </div>
          <div style="color:#94A3B8; font-size:13px; margin:4px 0;">🌍 {country} &bull; ⏰ الموعد: <span class="bidi-ltr" style="color:#F59E0B; font-weight:bold;">{deadline}</span></div>
          <a href="{link}" target="_blank" style="color:#60A5FA; font-size:13px; text-decoration:none; font-weight:bold;">رابط البوابة الرسمية للمنحة &larr;</a>
        </div>
        """

    closing_html = ""
    if closing_soon:
        closing_items = "".join([f"<li style='margin-bottom:4px;'><strong><span class='bidi-ltr'>{c.get('name')}</span></strong> ({c.get('country')}) - ينتهي <span class='bidi-ltr'>{c.get('deadline_display')}</span></li>" for c in closing_soon[:3]])
        closing_html = f"""
        <div style="background:#451A03; border:1px solid #78350F; border-radius:8px; padding:14px; margin:18px 0; color:#FEF3C7; font-size:14px;">
          <strong style="color:#FBBF24;">⏳ منح توشك على الإغلاق هذا الأسبوع:</strong>
          <ul style="padding-right:20px; margin:8px 0 0 0;">
            {closing_items}
          </ul>
        </div>
        """

    advice_block = ""
    if advice:
        advice_block = f"""
        <div class="card" style="background:#1E293B; border-right:4px solid #2563EB; padding:14px; margin:18px 0;">
          <strong style="color:#93C5FD; font-size:14px;">💡 نصيحة المستشار الذكي للأسبوع:</strong>
          <p style="margin:6px 0 0 0; color:#CBD5E1; font-size:13px;">{advice}</p>
        </div>
        """

    body_html = f"""
    <div style="text-align: center; margin-bottom: 20px;">
      <span class="badge badge-blue" style="padding: 5px 14px; font-size: 13px;">
        📬 النشرة الأسبوعية الموجهة
      </span>
      <h2 style="color: #FFFFFF; margin: 12px 0 6px 0; font-size: 21px; font-weight:800;">حصاد المنح الدراسية المفتوحة هذا الأسبوع</h2>
      <p style="color: #94A3B8; font-size: 14px; margin: 0;">إليك قائمة الفرص الأكثر تطابقاً مع تخصصك واهتماماتك الدراسية المسجلة.</p>
    </div>

    <div style="margin: 18px 0;">
      <h3 style="color:#FFFFFF; font-size:16px; margin:0 0 12px 0; font-weight:700;">أعلى الفرص تطابقاً مع ملفك:</h3>
      {matches_html}
    </div>

    {closing_html}
    {advice_block}
    """

    html = _email_wrapper(
        title="📬 نشرة المنح الأسبوعية - ScholarPilot AI",
        preheader=f"حصاد المنح الأسبوعي: تم رصد {len(top_matches)} منح مطابقة لملفك",
        body_html=body_html,
        cta_url="https://scholarpilot-ai-mkac.onrender.com",
        cta_text="استعراض كامل المنح في رادار المنح المفتوحة"
    )

    plain_text = f"""مرحباً {student_name or 'عزيزي الطالب'}،

إليك ملخص نشرة المنح الأسبوعية من ScholarPilot AI:
تم رصد {len(top_matches)} فرصة جديدة مطابقة لملفك.

يمكنك استعراض كل الفرص والتقديم عليها مباشرة من خلال:
https://scholarpilot-ai-mkac.onrender.com

ScholarPilot AI
"""
    return html, plain_text


def render_document_package_template(
    student_name: str,
    scholarship_name: str,
    document_type: str,
    document_content: str,
    checklist_status: Optional[List[str]] = None
) -> Tuple[str, str]:
    """5. AI Document Studio Package Email Template."""
    doc_type_clean = document_type or "خطاب الدافع (Motivation Letter)"
    sch_clean = scholarship_name or "المنحة الأكاديمية المستهدفة"

    checklist_items = checklist_status or [
        "المقدمة وبيان الشغف بالتخصص (Hook & Purpose)",
        "التميز الأكاديمي والمشاريع الملموسة (Academic Highlights)",
        "أسباب اختيار الجامعة والبرنامج (Institution Alignment)",
        "الرؤية المستقبلية والأثر بعد التخرج (Future Vision & Impact)"
    ]
    checklist_html = "".join([f"<li style='margin-bottom:6px; color:#34D399;'>&#10003; {item}</li>" for item in checklist_items])

    # Convert linebreaks in document content for readable email presentation
    formatted_content = document_content.replace("\n", "<br>")

    body_html = f"""
    <div style="text-align: center; margin-bottom: 20px;">
      <span class="badge badge-violet" style="padding: 5px 14px; font-size: 13px;">
        ✨ استوديو الوثائق بالذكاء الاصطناعي &bull; حزمة المستندات الرسمية
      </span>
      <h2 style="color: #FFFFFF; margin: 12px 0 6px 0; font-size: 21px; font-weight:800;">حزمة وثائق التقديم: {doc_type_clean}</h2>
      <p style="color: #94A3B8; font-size: 14px; margin: 0;">مرحباً {student_name or 'عزيزي الطالب'}، تم تجهيز مسودتك الأكاديمية المخصصة لمنحة <span class="bidi-ltr font-latin">{sch_clean}</span>.</p>
    </div>

    <!-- Quality Checklist Card -->
    <div class="card" style="background:#1E293B; border:1px solid #334155; border-radius:10px; padding:16px; margin:16px 0;">
      <h4 style="color:#C4B5FD; margin:0 0 10px 0; font-size:14px; font-weight:bold;">معايير الجودة والتدقيق المستوفاة:</h4>
      <ul style="padding-right: 20px; margin: 0; font-size: 13px;">
        {checklist_html}
      </ul>
    </div>

    <!-- Official Document Box (dir=ltr for English SOP text) -->
    <div style="background: #0B1120; border: 1px solid #334155; border-radius: 10px; padding: 22px; margin: 20px 0; direction: ltr; text-align: left; font-family: 'Plus Jakarta Sans', 'Inter', -apple-system, sans-serif; font-size: 14px; line-height: 1.8; color: #F8FAFC;">
      <div style="border-bottom: 1px solid #334155; padding-bottom: 12px; margin-bottom: 16px; display: flex; justify-content: space-between; align-items: center;">
        <strong style="color: #60A5FA; font-size: 15px;">{doc_type_clean}</strong>
        <span style="color: #94A3B8; font-size: 12px;">Candidate: {student_name or 'Applicant'}</span>
      </div>
      <div>
        {formatted_content}
      </div>
    </div>

    <div style="margin: 20px 0; color:#CBD5E1; font-size:13px; line-height: 1.6;">
      <p><strong style="color:#FFFFFF;">نصائح التقديم النهائي:</strong></p>
      <ul style="padding-right: 20px; margin: 0;">
        <li>قم بمراجعة الفقرات وإضافة تجاربك الشخصية وأسماء أساتذتك المشرفين.</li>
        <li>يمكنك تصدير الملف كـ PDF أو DOCX مباشرة من استوديو الوثائق بالمنصة.</li>
        <li>تأكد من إرسال الطلب قبل الموعد النهائي المحدد للمنحة بـ 48 ساعة على الأقل.</li>
      </ul>
    </div>
    """

    html = _email_wrapper(
        title=f"📄 حزمة وثائق التقديم: {doc_type_clean} - {sch_clean}",
        preheader=f"مسودة {doc_type_clean} جاهزة ومخصصة لمنحة {sch_clean}",
        body_html=body_html,
        cta_url="https://scholarpilot-ai-mkac.onrender.com/assistant",
        cta_text="فتح استوديو الوثائق وتعديل المسودة مباشرة"
    )

    plain_text = f"""مرحباً {student_name or 'عزيزي الطالب'}،

إليك حزمة وثائق التقديم الأكاديمية الخاصة بك:
الوثيقة: {doc_type_clean}
المنحة المستهدفة: {sch_clean}

نص الوثيقة:
----------------------------------------
{document_content}
----------------------------------------

يمكنك متابعة التعديل والتصدير إلى PDF و DOCX عبر استوديو الوثائق:
https://scholarpilot-ai-mkac.onrender.com/assistant

ScholarPilot AI - مستشارك الأكاديمي
"""
    return html, plain_text


# =====================================================================
# EMAIL SERVICE CLASS (ABSTRACTION LAYER)
# =====================================================================

class EmailService:
    """Enterprise-grade Email Delivery Abstraction Layer supporting Resend and SMTP."""

    def __init__(self):
        self.resend_api_key = os.getenv("RESEND_API_KEY")
        self.from_email = os.getenv("RESEND_FROM_EMAIL") or os.getenv("SENDER_EMAIL") or "ScholarPilot AI <onboarding@resend.dev>"

    async def dispatch_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
        custom_headers: Optional[Dict[str, str]] = None
    ) -> bool:
        """Dispatches an email with deliverability headers and automated provider fallback."""
        return await dispatch_email(
            to_email=to_email,
            subject=subject,
            html_content=html_content,
            text_content=text_content,
            attachments=attachments,
            custom_headers=custom_headers
        )

    async def send_new_match_alert(
        self,
        student_email: str,
        student_name: str,
        scholarship: Dict[str, Any],
        match_score: int = 90,
        reasons: Optional[List[str]] = None
    ) -> bool:
        """Sends a high-conversion new match alert email."""
        html, text = render_new_match_template(student_name, scholarship, match_score, reasons)
        title = scholarship.get("name") or scholarship.get("title", "منحة دراسية جديدة")
        return await self.dispatch_email(
            to_email=student_email,
            subject=f"🎯 فرصة منحة جديدة مطابقة لملفك الأكاديمي: {title}",
            html_content=html,
            text_content=text
        )

    async def send_deadline_reminder(
        self,
        student_email: str,
        student_name: str,
        scholarship: Dict[str, Any],
        days_left: int = 7,
        milestone: str = "تجهيز الوثائق النهائية"
    ) -> bool:
        """Sends an urgent deadline reminder email."""
        html, text = render_deadline_reminder_template(student_name, scholarship, days_left, milestone)
        title = scholarship.get("name") or scholarship.get("title", "المنحة المحفوظة")
        return await self.dispatch_email(
            to_email=student_email,
            subject=f"⚠️ تذكير موعد نهائي: متبقي {days_left} أيام للتقديم على منحة {title}",
            html_content=html,
            text_content=text
        )

    async def send_welcome_email(
        self,
        student_email: str,
        student_name: str,
        profile: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Sends a welcome confirmation email upon registration/subscription."""
        html, text = render_welcome_template(student_name, student_email, profile)
        return await self.dispatch_email(
            to_email=student_email,
            subject="🎉 أهلاً بك في ScholarPilot AI - تم تفعيل نظام رادار المنح بنجاح",
            html_content=html,
            text_content=text
        )

    async def send_weekly_digest(
        self,
        student_email: str,
        student_name: str,
        top_matches: List[Dict[str, Any]],
        closing_soon: Optional[List[Dict[str, Any]]] = None,
        advice: str = ""
    ) -> bool:
        """Sends the weekly curated digest email."""
        html, text = render_weekly_digest_template(student_name, top_matches, closing_soon, advice)
        return await self.dispatch_email(
            to_email=student_email,
            subject="📬 حصاد المنح الأسبوعية المفتوحة والمطابقة لملفك - ScholarPilot AI",
            html_content=html,
            text_content=text
        )

    async def send_smart_radar_digest(
        self,
        student_email: str,
        student_name: str,
        matches: List[Dict[str, Any]],
        student_profile: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Sends a single consolidated Smart Radar Digest email aggregating newly discovered matches."""
        html, text = render_smart_radar_digest_template(student_name, matches, student_profile)
        count = len(matches)
        sch_name = matches[0].get("name", matches[0].get("title", "")) if count == 1 else ""
        subject = f"🎯 رادار EduAtlas الذكي: تم رصد {count} فرص دراسية جديدة متطابقة مع ملفك" if count > 1 else f"🎯 رادار EduAtlas: تم رصد فرصة دراسية جديدة متطابقة ({sch_name})"
        return await self.dispatch_email(
            to_email=student_email,
            subject=subject,
            html_content=html,
            text_content=text
        )

    async def send_document_package(
        self,
        student_email: str,
        student_name: str,
        scholarship_name: str,
        document_type: str,
        document_content: str,
        checklist_status: Optional[List[str]] = None
    ) -> bool:
        """Sends official drafted application documents directly to student's inbox."""
        html, text = render_document_package_template(
            student_name=student_name,
            scholarship_name=scholarship_name,
            document_type=document_type,
            document_content=document_content,
            checklist_status=checklist_status
        )
        doc_type_clean = document_type or "خطاب الدافع"
        return await self.dispatch_email(
            to_email=student_email,
            subject=f"📄 استوديو الوثائق: مسودة {doc_type_clean} لمنحة {scholarship_name}",
            html_content=html,
            text_content=text
        )


# Global singleton instance
email_service = EmailService()


# =====================================================================
# CORE DISPATCH FUNCTION (PRESERVED FOR BACKWARD COMPATIBILITY)
# =====================================================================

async def dispatch_email(
    to_email: str,
    subject: str,
    html_content: str,
    text_content: Optional[str] = None,
    attachments: Optional[List[Dict[str, Any]]] = None,
    custom_headers: Optional[Dict[str, str]] = None
) -> bool:
    """
    Dispatches an email through Resend (primary cloud provider) or Gmail SMTP (fallback).
    Optimized for deliverability with SPF/DKIM compliance headers, List-Unsubscribe,
    strict daily quota cap enforcement (85 emails/day), and rate limiting (max 2 req/sec).
    attachments format: [{"filename": "report.csv", "content_bytes": b"..."}]
    """
    global _last_dispatch_meta

    # Strict rate-limiting for Resend API compliance (max 2 requests/sec)
    await asyncio.sleep(0.55)

    resend_api_key = os.getenv("RESEND_API_KEY")
    resend_from_env = os.getenv("RESEND_FROM_EMAIL", "").strip()
    if resend_from_env and "@gmail.com" not in resend_from_env.lower():
        sender_name_email = resend_from_env
    else:
        sender_name_email = "EduAtlas <onboarding@resend.dev>"

    clean_to = sanitize_email_header(to_email)
    clean_sub = sanitize_email_header(subject)

    _last_dispatch_meta = {
        "success": False,
        "provider": None,
        "recipient": clean_to,
        "error_detail": None,
        "hint": None,
        "raw_resend_error": None
    }

    # Standard deliverability headers (SPF/DKIM friendly, CAN-SPAM compliant)
    deliverability_headers = {
        "List-Unsubscribe": "<https://eduatlas-irxv.onrender.com/dashboard>, <mailto:unsubscribe@eduatlas.ai>",
        "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
        "Precedence": "bulk",
        "X-Auto-Response-Suppress": "OOF, AutoReply",
        "X-Entity-Ref-ID": f"ea_{int(os.times().system * 1000)}"
    }
    if custom_headers:
        deliverability_headers.update(custom_headers)

    # 1. Primary Cloud Provider: Resend HTTP REST API (Port 443)
    if resend_api_key and len(resend_api_key.strip()) > 5:
        if not DailyEmailTracker.can_send_email():
            logger.warning(
                f"⚠️ Resend daily email safety cap ({MAX_DAILY_EMAILS} emails/day) reached. "
                "Skipping Resend dispatch to protect quota and prevent exhaustion."
            )
            _last_dispatch_meta["hint"] = "resend_daily_quota_exhausted"
            _last_dispatch_meta["error_detail"] = "تم الوصول إلى الحد اليومي الآمن لإرسال البريد (85 بريد/يوم)."
        else:
            logger.info(f"Dispatching email to {clean_to} via Resend API (Quota: {DailyEmailTracker.get_quota_status()['sent_count']}/{MAX_DAILY_EMAILS})...")
            headers = {
                "Authorization": f"Bearer {resend_api_key.strip()}",
                "Content-Type": "application/json"
            }

            resend_attachments = []
            if attachments:
                for att in attachments:
                    raw_bytes = att.get("content_bytes", b"")
                    if isinstance(raw_bytes, str):
                        raw_bytes = raw_bytes.encode("utf-8")
                    b64_content = base64.b64encode(raw_bytes).decode("utf-8")
                    resend_attachments.append({
                        "filename": att.get("filename", "attachment.txt"),
                        "content": b64_content
                    })

            payload: Dict[str, Any] = {
                "from": sender_name_email,
                "to": [clean_to],
                "subject": clean_sub,
                "html": html_content,
                "headers": deliverability_headers
            }
            if text_content:
                payload["text"] = text_content
            if resend_attachments:
                payload["attachments"] = resend_attachments

            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    res = await client.post(RESEND_API_URL, headers=headers, json=payload)
                    if res.status_code in [200, 201]:
                        sent_num = DailyEmailTracker.record_email_sent()
                        logger.info(f"✅ Delivered successfully to {clean_to} via Resend API (ID: {res.json().get('id')}) [Day Total: {sent_num}/{MAX_DAILY_EMAILS}]")
                        _last_dispatch_meta["success"] = True
                        _last_dispatch_meta["provider"] = "Resend API"
                        return True
                    else:
                        err_text = res.text
                        logger.warning(f"Resend API returned HTTP {res.status_code}: {err_text}")
                        _last_dispatch_meta["raw_resend_error"] = err_text
                        if "only send testing emails to your own email" in err_text:
                            _last_dispatch_meta["error_detail"] = (
                                "حساب Resend المجاني التجريبي مخصص للإرسال لبريد المالك فقط. "
                                "للإرسال لأي طالب في العالم عبر Render، يرجى تفعيل مفتاح Brevo API أو توثيق دومين في Resend."
                            )
                            _last_dispatch_meta["hint"] = "resend_sandbox_restriction"
                        else:
                            _last_dispatch_meta["error_detail"] = f"Resend API ({res.status_code}): {err_text[:160]}"
            except Exception as e:
                logger.warning(f"Resend API dispatch error: {e}")
                _last_dispatch_meta["error_detail"] = f"فشل اتصال Resend: {str(e)[:160]}"

    # 2. Secondary Cloud Provider: Brevo HTTP REST API (Port 443 - Unrestricted on Render)
    brevo_api_key = os.getenv("BREVO_API_KEY")
    if brevo_api_key and len(brevo_api_key.strip()) > 5:
        logger.info(f"Dispatching email to {clean_to} via Brevo HTTP REST API...")
        brevo_sender_email = os.getenv("BREVO_SENDER_EMAIL") or os.getenv("SENDER_EMAIL") or "scholarpilot.ai@gmail.com"
        brevo_sender_name = os.getenv("BREVO_SENDER_NAME") or "ScholarPilot AI"
        brevo_payload = {
            "sender": {"name": brevo_sender_name, "email": brevo_sender_email},
            "to": [{"email": clean_to}],
            "subject": clean_sub,
            "htmlContent": html_content
        }
        if text_content:
            brevo_payload["textContent"] = text_content
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res_b = await client.post(
                    "https://api.brevo.com/v3/smtp/email",
                    headers={"api-key": brevo_api_key.strip(), "Content-Type": "application/json"},
                    json=brevo_payload
                )
                if res_b.status_code in [200, 201]:
                    logger.info(f"✅ Delivered successfully to {clean_to} via Brevo HTTP API!")
                    _last_dispatch_meta["success"] = True
                    _last_dispatch_meta["provider"] = "Brevo HTTP API"
                    _last_dispatch_meta["error_detail"] = None
                    return True
                else:
                    logger.warning(f"Brevo API error {res_b.status_code}: {res_b.text}")
                    _last_dispatch_meta["error_detail"] = f"Brevo API ({res_b.status_code}): {res_b.text[:160]}"
        except Exception as eb:
            logger.warning(f"Brevo HTTP API dispatch exception: {eb}")

    # 3. Tertiary Provider: Universal SMTP (Works locally or on non-blocking hosts)
    smtp_user = os.getenv("SENDER_EMAIL") or os.getenv("EMAIL_USER")
    smtp_pass = os.getenv("GMAIL_APP_PASSWORD") or os.getenv("EMAIL_PASS") or os.getenv("SMTP_PASS")
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com").strip()
    try:
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
    except ValueError:
        smtp_port = 587

    if smtp_user and smtp_pass:
        smtp_pass = smtp_pass.replace(" ", "").strip()
        provider_name = "Gmail SMTP" if "gmail" in smtp_host.lower() else f"SMTP ({smtp_host})"
        logger.info(f"Dispatching email to {clean_to} via {provider_name} [{smtp_host}:{smtp_port}]...")
        msg = EmailMessage()
        msg["Subject"] = clean_sub
        msg["From"] = sanitize_email_header(f"ScholarPilot AI <{smtp_user}>")
        msg["To"] = clean_to

        for hk, hv in deliverability_headers.items():
            msg[hk] = hv

        if text_content:
            msg.set_content(text_content)
        else:
            msg.set_content("Please view this email in an HTML-compatible client.")
        msg.add_alternative(html_content, subtype="html")

        if attachments:
            for att in attachments:
                raw_bytes = att.get("content_bytes", b"")
                filename = att.get("filename", "attachment.csv")
                subtype = "csv" if filename.endswith(".csv") else "plain"
                msg.add_attachment(raw_bytes, maintype="text", subtype=subtype, filename=filename)

        try:
            with smtplib.SMTP(smtp_host, smtp_port, timeout=5) as server:
                server.starttls()
                server.login(smtp_user, smtp_pass)
                server.send_message(msg)
                logger.info(f"✅ Delivered successfully to {clean_to} via {provider_name} TLS!")
                _last_dispatch_meta["success"] = True
                _last_dispatch_meta["provider"] = provider_name
                _last_dispatch_meta["error_detail"] = None
                return True
        except Exception as e:
            err_msg = str(e)
            logger.error(f"SMTP TLS ({smtp_host}:{smtp_port}) failed: {e}")
            if "101" in err_msg or "unreachable" in err_msg.lower():
                _last_dispatch_meta["error_detail"] = "خادم الاستضافة Render يحظر منافذ SMTP (Port 587/465). يرجى استخدام Brevo API أو توثيق دومين Resend."
            else:
                _last_dispatch_meta["error_detail"] = f"فشل إرسال SMTP: {err_msg[:160]}"

    # 3. Fallback: If in production with RESEND_API_KEY configured and failed, report delivery failure
    if resend_api_key or os.getenv("RENDER"):
        logger.error(f"❌ Delivery to {clean_to} failed: Resend/SMTP could not deliver email.")
        if not _last_dispatch_meta["error_detail"]:
            _last_dispatch_meta["error_detail"] = "تعذر إرسال البريد عبر المزودين المتاحين."
        return False

    # 4. Local/Dev fallback logger
    logger.info(f"[DEV MOCK DISPATCH] Email to {clean_to} | Subject: '{clean_sub}' | (No RESEND_API_KEY or SMTP credentials configured).")
    _last_dispatch_meta["success"] = True
    _last_dispatch_meta["provider"] = "Dev Mock"
    return True


def get_email_provider_info() -> Dict[str, str]:
    """Returns current active email provider and status for health checks."""
    resend_key = os.getenv("RESEND_API_KEY", "").strip()
    if resend_key and len(resend_key) > 5:
        sender = os.getenv("RESEND_FROM_EMAIL") or "ScholarPilot AI <onboarding@resend.dev>"
        return {"provider": "Resend (HTTP REST API)", "sender": sender, "status": "active"}

    smtp_user = os.getenv("SENDER_EMAIL") or os.getenv("EMAIL_USER")
    smtp_pass = os.getenv("GMAIL_APP_PASSWORD") or os.getenv("EMAIL_PASS")
    if smtp_user and smtp_pass:
        return {"provider": "Gmail SMTP", "sender": smtp_user, "status": "active"}

    return {"provider": "Mock / Dev Logger", "sender": "local", "status": "dev_mode"}
