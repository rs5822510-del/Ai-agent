"""
notifier.py
Sends professional, styled HTML emails when a job needs review, or
confirms an auto-apply. Falls back to plain text for email clients that
don't render HTML.
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def _greeting_name(cfg: dict) -> str:
    name = cfg.get("profile", {}).get("name", "").strip()
    if not name or name.lower().startswith("your name"):
        name = "Sir"
    return name


def _html_wrapper(title: str, accent_color: str, body_html: str) -> str:
    """Wraps content in a consistent, styled email template."""
    return f"""\
<html>
<body style="margin:0; padding:0; background-color:#f4f5f7; font-family: Segoe UI, Arial, sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#f4f5f7; padding: 30px 0;">
    <tr>
      <td align="center">
        <table width="600" cellpadding="0" cellspacing="0" style="background-color:#ffffff; border-radius:10px; overflow:hidden; box-shadow:0 2px 8px rgba(0,0,0,0.08);">

          <!-- Header -->
          <tr>
            <td style="background: linear-gradient(135deg, {accent_color}, #4b3fd6); padding: 28px 32px;">
              <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td style="font-size:32px; width:50px;">🤖</td>
                  <td style="color:#ffffff; font-size:20px; font-weight:600; padding-left:10px;">
                    Job AI Agent
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Title bar -->
          <tr>
            <td style="padding: 24px 32px 0 32px;">
              <h2 style="margin:0; color:#1a1a2e; font-size:19px;">{title}</h2>
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td style="padding: 16px 32px 32px 32px; color:#333333; font-size:15px; line-height:1.6;">
              {body_html}
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="background-color:#f9f9fb; padding:18px 32px; text-align:center; color:#9a9a9a; font-size:12px;">
              This is an automated message from your personal Job AI Agent.
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""


def _skill_tags(skills, bg, color):
    """Renders a list of skills as small colored pill tags."""
    if not skills:
        return "<span style='color:#999;'>None</span>"
    tags = "".join(
        f"<span style='display:inline-block; background:{bg}; color:{color}; "
        f"padding:4px 10px; border-radius:12px; font-size:13px; margin:2px 4px 2px 0;'>{s}</span>"
        for s in skills
    )
    return tags


def send_email(cfg: dict, subject: str, html_body: str, plain_body: str):
    email_cfg = cfg["notifications"]["email"]
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"Job AI Agent <{email_cfg['sender_email']}>"
    msg["To"] = email_cfg["recipient_email"]

    msg.attach(MIMEText(plain_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(email_cfg["smtp_server"], email_cfg["smtp_port"]) as server:
            server.starttls()
            server.login(email_cfg["sender_email"], email_cfg["sender_app_password"])
            server.send_message(msg)
        print(f"[notifier] Email sent: {subject}")
    except Exception as e:
        print(f"[notifier] FAILED to send email: {e}")


def notify_auto_applied(cfg, job_title, company, url, match_info):
    name = _greeting_name(cfg)
    subject = f"✅ Application Submitted — {job_title} at {company}"

    body_html = f"""
    <p>Dear {name} Sir,</p>
    <p>Your Job AI Agent has automatically submitted an application on your behalf. Details below:</p>

    <table width="100%" cellpadding="0" cellspacing="0" style="background:#f6fbf7; border-left:4px solid #2ecc71; border-radius:6px; margin:18px 0;">
      <tr><td style="padding:16px 20px;">
        <p style="margin:0 0 6px 0;"><strong>Position:</strong> {job_title}</p>
        <p style="margin:0 0 6px 0;"><strong>Company:</strong> {company}</p>
        <p style="margin:0 0 14px 0;"><strong>Match Score:</strong> {int(match_info['match_ratio']*100)}%</p>
        <p style="margin:0 0 6px 0;"><strong>Matched Skills:</strong></p>
        <div>{_skill_tags(match_info['matched_skills'], '#e6f7ec', '#1e8449')}</div>
      </td></tr>
    </table>

    <a href="{url}" style="display:inline-block; background:#2ecc71; color:#ffffff; text-decoration:none; padding:12px 22px; border-radius:6px; font-weight:600;">View Job Posting</a>

    <p style="margin-top:24px; color:#666;">No action is needed unless you wish to review the application further.</p>
    <p>Regards,<br>Job AI Agent</p>
    """

    plain_body = (
        f"Dear {name} Sir,\n\nApplied automatically to:\n{job_title} — {company}\n{url}\n"
        f"Matched skills: {', '.join(match_info['matched_skills'])}\n"
        f"Match score: {int(match_info['match_ratio']*100)}%\n\nRegards,\nJob AI Agent"
    )

    send_email(cfg, subject, _html_wrapper("Application Submitted ✅", "#2ecc71", body_html), plain_body)


def notify_needs_review(cfg, job_title, company, url, match_info):
    name = _greeting_name(cfg)
    subject = f"👀 Review Needed — {job_title} at {company}"

    body_html = f"""
    <p>Dear {name} Sir,</p>
    <p>Your Job AI Agent found a job that <strong>strongly matches</strong> your profile, but wants your confirmation before applying:</p>

    <table width="100%" cellpadding="0" cellspacing="0" style="background:#fff9f0; border-left:4px solid #f39c12; border-radius:6px; margin:18px 0;">
      <tr><td style="padding:16px 20px;">
        <p style="margin:0 0 6px 0;"><strong>Position:</strong> {job_title}</p>
        <p style="margin:0 0 6px 0;"><strong>Company:</strong> {company}</p>
        <p style="margin:0 0 14px 0;"><strong>Match Score:</strong> {int(match_info['match_ratio']*100)}%</p>
        <p style="margin:0 0 6px 0;"><strong>Matched Skills:</strong></p>
        <div style="margin-bottom:10px;">{_skill_tags(match_info['matched_skills'], '#e6f7ec', '#1e8449')}</div>
        <p style="margin:0 0 6px 0;"><strong>Skills You May Lack:</strong></p>
        <div>{_skill_tags(match_info['missing_skills'], '#fdeaea', '#c0392b')}</div>
      </td></tr>
    </table>

    <a href="{url}" style="display:inline-block; background:#f39c12; color:#ffffff; text-decoration:none; padding:12px 22px; border-radius:6px; font-weight:600;">View & Apply Manually</a>

    <p>Regards,<br>Job AI Agent</p>
    """

    plain_body = (
        f"Dear {name} Sir,\n\nJob needing review:\n{job_title} — {company}\n{url}\n"
        f"Matched skills: {', '.join(match_info['matched_skills']) or 'None'}\n"
        f"Missing skills: {', '.join(match_info['missing_skills'])}\n"
        f"Match score: {int(match_info['match_ratio']*100)}%\n\nRegards,\nJob AI Agent"
    )

    send_email(cfg, subject, _html_wrapper("Review Needed Before Applying 👀", "#f39c12", body_html), plain_body)


def notify_new_account_created(cfg, platform, username, password):
    name = _greeting_name(cfg)
    subject = f"🔐 New Account Created — {platform}"

    body_html = f"""
    <p>Dear {name} Sir,</p>
    <p>Your Job AI Agent created a new account on <strong>{platform}</strong> on your behalf. Please save these credentials securely:</p>

    <table width="100%" cellpadding="0" cellspacing="0" style="background:#f6f4ff; border-left:4px solid #6c5ce7; border-radius:6px; margin:18px 0;">
      <tr><td style="padding:16px 20px;">
        <p style="margin:0 0 6px 0;"><strong>Username:</strong> {username}</p>
        <p style="margin:0;"><strong>Password:</strong> {password}</p>
      </td></tr>
    </table>

    <p style="color:#666;">We recommend changing this password after your first manual login.</p>
    <p>Regards,<br>Job AI Agent</p>
    """

    plain_body = (
        f"Dear {name} Sir,\n\nNew account created on {platform}.\n"
        f"Username: {username}\nPassword: {password}\n\nRegards,\nJob AI Agent"
    )

    send_email(cfg, subject, _html_wrapper("New Account Created 🔐", "#6c5ce7", body_html), plain_body)