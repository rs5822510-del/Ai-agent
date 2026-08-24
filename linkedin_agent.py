"""
linkedin_agent.py
Logs into LinkedIn with YOUR credentials and attempts Easy Apply on
matching jobs. LinkedIn actively fights automation (CAPTCHAs, checkpoint
challenges, rate limits) — this can still get flagged or your account
restricted. Use slow_mode, don't run this 24/7, and expect to solve the
occasional manual CAPTCHA yourself.

Requires: pip install selenium webdriver-manager
"""

import time
import random
import urllib.parse
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

from matcher import score_job, decide_action
from notifier import notify_auto_applied, notify_needs_review


def human_pause(a=2.0, b=5.0):
    time.sleep(random.uniform(a, b))


def start_driver():
    options = Options()
    options.add_argument("--start-maximized")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    return driver


def _safe_type(driver, element, text, field_label):
    try:
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
        human_pause(0.3, 0.6)
        element.click()
        element.clear()
        element.send_keys(text)
    except Exception:
        print(f"[linkedin_agent] Normal typing failed for {field_label}, using JS fallback.")
        driver.execute_script(
            "arguments[0].value = arguments[1]; "
            "arguments[0].dispatchEvent(new Event('input', {bubbles: true}));",
            element, text
        )


def login(driver, email, password):
    driver.get("https://www.linkedin.com/login")
    human_pause(2, 3)

    username_selectors = [
        (By.XPATH, "//label[contains(., 'Email or phone')]/following::input[1]"),
        (By.XPATH, "//label[contains(., 'Email')]/following::input[1]"),
        (By.ID, "username"),
        (By.NAME, "session_key"),
        (By.CSS_SELECTOR, "input[autocomplete='username']"),
        (By.XPATH, "//input[@type='text' or @type='email']"),
    ]
    password_selectors = [
        (By.XPATH, "//label[contains(., 'Password')]/following::input[1]"),
        (By.ID, "password"),
        (By.NAME, "session_password"),
        (By.CSS_SELECTOR, "input[autocomplete='current-password']"),
        (By.XPATH, "//input[@type='password']"),
    ]

    username_field = None
    for by, value in username_selectors:
        try:
            username_field = WebDriverWait(driver, 12).until(
                EC.visibility_of_element_located((by, value))
            )
            break
        except Exception:
            continue

    if username_field is None:
        driver.save_screenshot("linkedin_debug.png")
        with open("linkedin_debug.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        print(f"[linkedin_agent] Could not find the email field on LinkedIn's login "
              f"page. Page title: '{driver.title}'. Current URL: {driver.current_url}. "
              f"Saved linkedin_debug.png and linkedin_debug.html in this folder for "
              f"debugging. Keeping browser open 20s too...")
        human_pause(20, 20)
        raise RuntimeError("LinkedIn login field not found — see message above")

    _safe_type(driver, username_field, email, "email field")

    password_field = None
    for by, value in password_selectors:
        try:
            password_field = driver.find_element(by, value)
            if password_field.is_displayed():
                break
        except Exception:
            continue

    if password_field is None:
        print(f"[linkedin_agent] Found email field but not password field. "
              f"Keeping browser open 20s so you can screenshot it...")
        human_pause(20, 20)
        raise RuntimeError("LinkedIn password field not found")

    _safe_type(driver, password_field, password, "password field")
    human_pause(1, 2)
    driver.find_element(By.XPATH, "//button[@type='submit']").click()
    human_pause(4, 6)


def search_jobs(driver, keyword, location=""):
    params = {"keywords": keyword, "location": location, "f_AL": "true"}
    url = "https://www.linkedin.com/jobs/search/?" + urllib.parse.urlencode(params)
    driver.get(url)
    human_pause(3, 6)

    jobs = []
    cards = driver.find_elements(By.CSS_SELECTOR, "div.job-card-container")
    for card in cards:
        try:
            title = card.find_element(By.CSS_SELECTOR, "a.job-card-list__title").text
            link = card.find_element(By.CSS_SELECTOR, "a.job-card-list__title").get_attribute("href")
            company = card.find_element(By.CSS_SELECTOR, "span.job-card-container__primary-description").text
            jobs.append({"title": title, "company": company, "url": link, "description": title})
        except Exception:
            continue
    return jobs


def try_easy_apply(driver, job_url):
    driver.get(job_url)
    human_pause(2, 4)
    try:
        easy_apply_btn = driver.find_element(By.XPATH, "//button[contains(., 'Easy Apply')]")
        easy_apply_btn.click()
        human_pause(2, 3)

        try:
            submit_btn = driver.find_element(By.XPATH, "//button[contains(@aria-label, 'Submit application')]")
            submit_btn.click()
            human_pause(2, 3)
            return True
        except Exception:
            driver.find_element(By.XPATH, "//button[@aria-label='Dismiss']").click()
            return False
    except Exception:
        return False


def run_linkedin_agent(cfg):
    li_cfg = cfg["platforms"]["linkedin"]
    if not li_cfg.get("enabled"):
        return

    driver = start_driver()
    login(driver, li_cfg["login_email"], li_cfg["login_password"])

    applied_count = 0
    max_apps = cfg["run"]["max_applications_per_run"]

    for role in cfg["profile"].get("target_roles", cfg.get("target_roles", [])):
        for loc in cfg["profile"]["preferred_locations"]:
            if applied_count >= max_apps:
                break
            jobs = search_jobs(driver, role, loc)
            for job in jobs:
                if applied_count >= max_apps:
                    break
                match = score_job(job["description"], cfg["known_skills"])
                action = decide_action(
                    match["match_ratio"],
                    cfg["matching"]["auto_apply_threshold"],
                    cfg["matching"]["min_notify_threshold"],
                )

                if action == "auto_apply":
                    applied = try_easy_apply(driver, job["url"])
                    if applied:
                        applied_count += 1
                        notify_auto_applied(cfg, job["title"], job["company"], job["url"], match)
                    else:
                        notify_needs_review(cfg, job["title"], job["company"], job["url"], match)
                elif action == "notify":
                    notify_needs_review(cfg, job["title"], job["company"], job["url"], match)

                human_pause(3, 6)

    driver.quit()
    print(f"[linkedin_agent] Done. Auto-applied to {applied_count} jobs.")