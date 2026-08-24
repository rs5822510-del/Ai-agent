# Job Agent — Naukri + LinkedIn Auto-Apply

An agent that searches Naukri and LinkedIn for jobs matching your degree/skills,
**auto-applies when your skills clearly match**, and **emails you** when a job
is a partial match it's not confident about.

## ⚠️ Read this first
- LinkedIn and Naukri's Terms of Service prohibit automated bots. This tool
  automates *your own browser, logged into your own account* — it's your
  decision and your risk. LinkedIn in particular can flag/restrict accounts
  for bot-like behavior (too many actions too fast, unusual patterns).
- To reduce risk: don't run `--loop` unattended 24/7 at first, keep
  `max_applications_per_run` low (5–10), and watch the first few runs live.
- Multi-step LinkedIn application forms (screening questions) are **not**
  auto-filled — the agent deliberately backs out and notifies you instead,
  since guessing your answers to employer questions is risky.
- Selenium opens a real, visible Chrome window (not headless by default) —
  this is intentional so you can solve a CAPTCHA if one appears.

## Setup (10 minutes)

1. Install Python 3.10+ and Google Chrome.
2. In this folder, install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Open `config.yaml` and fill in:
   - Your degree, skills, and target roles under `profile` / `known_skills` / `target_roles`
   - Your Naukri and LinkedIn login (stored locally only, never sent anywhere but those sites)
   - Email settings for notifications — for Gmail, generate an **App Password**
     (Google Account → Security → 2-Step Verification → App Passwords), don't
     use your real Gmail password.
4. Adjust `matching.auto_apply_threshold` (default 0.75 = 75% of a job's
   detected required skills must be skills you know) and
   `min_notify_threshold` (default 0.35) to taste.

## Run it

```bash
python main.py            # single run, applies + notifies, then exits
python main.py --loop     # keeps running, checking every N minutes (see config)
```

## How matching works
`matcher.py` scans each job description for a vocabulary of common skills/tools
(Python, SQL, AWS, React, etc. — edit `SKILL_VOCAB` in that file to add your
field's specific tools) and compares them against `known_skills` in your config.

- **Above `auto_apply_threshold`** → tries to auto-apply (Naukri Quick Apply /
  LinkedIn single-step Easy Apply), then emails you a confirmation.
- **Between the two thresholds** → skips applying, emails you the job + which
  skills you're missing, so you decide.
- **Below `min_notify_threshold`** → ignored silently.

## Extending it
- Add more skills to `SKILL_VOCAB` in `matcher.py` for your specific field.
- Swap email notifications for WhatsApp/Telegram by replacing `notifier.py`.
- The Naukri/LinkedIn CSS selectors (`By.CLASS_NAME`, `By.CSS_SELECTOR`, etc.)
  **will break** whenever those sites redesign their pages — this is normal
  for any scraping tool and will need occasional small fixes.
