"""
naukri_agent.py
Logs into Naukri with YOUR credentials, searches your target roles,
scores each result, and either "Quick Apply"s or flags it for review.

Requires: pip install selenium webdriver-manager
Run with your own Chrome browser + your own Naukri account.
"""

import time
import random
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

from matcher import score_job, decide_action
from notifier import notify_auto_applied, notify_needs_review


def human_pause(a=1.5, b=3.5):
    time.sleep(random.uniform(a, b))


def start_driver(headless=False):
    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--start-maximized")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    return driver


def login(driver, email, password):
    driver.get("https://www.naukri.com/nlogin/login")
    human_pause(2, 3)
    try:
        username_field = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.ID, "usernameField"))
        )
        username_field.send_keys(email)
        driver.find_element(By.ID, "passwordField").send_keys(password)
        human_pause(1, 2)
        driver.find_element(By.XPATH, "//button[@type='submit']").click()
        human_pause(3, 5)
    except Exception as e:
        print(f"[naukri_agent] Could not find login fields — Naukri may have "
              f"changed their page layout, or shown a CAPTCHA. "
              f"Current page title: '{driver.title}'. Error: {e}")
        raise


def search_jobs(driver, keyword, location=""):
    query = keyword.replace(" ", "-")
    url = f"https://www.naukri.com/{query}-jobs-in-{location.lower()}" if location else f"https://www.naukri.com/{query}-jobs"
    driver.get(url)
    human_pause(3, 5)

    job_cards = driver.find_elements(By.CLASS_NAME, "cust-job-tuple")
    print(f"[naukri_agent] Searched '{keyword}' in '{location}' — found {len(job_cards)} job cards on page.")
    jobs = []
    for card in job_cards:
        try:
            title_el = card.find_element(By.CLASS_NAME, "title")
            title = title_el.text
            link = title_el.get_attribute("href")
            company = card.find_element(By.CLASS_NAME, "comp-name").text
            try:
                jd_snippet = card.find_element(By.CLASS_NAME, "job-desc").text
            except Exception:
                jd_snippet = ""
            jobs.append({"title": title, "company": company, "url": link, "description": jd_snippet})
        except Exception:
            continue
    return jobs


def try_quick_apply(driver, job_url):
    """Opens the job and clicks Quick Apply if available. Returns True if applied."""
    driver.get(job_url)
    human_pause(2, 4)
    try:
        apply_btn = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.ID, "apply-button"))
        )
        btn_text = apply_btn.text.lower()
        if "apply" in btn_text:
            apply_btn.click()
            human_pause(2, 3)
            return True
    except Exception:
        pass
    return False


def run_naukri_agent(cfg):
    n_cfg = cfg["platforms"]["naukri"]
    if not n_cfg.get("enabled"):
        return

    driver = start_driver(headless=False)
    login(driver, n_cfg["login_email"], n_cfg["login_password"])

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
                match = score_job(job["description"] or job["title"], cfg["known_skills"])
                action = decide_action(
                    match["match_ratio"],
                    cfg["matching"]["auto_apply_threshold"],
                    cfg["matching"]["min_notify_threshold"],
                )
                print(f"[naukri_agent]   '{job['title']}' @ {job['company']} — "
                      f"match={int(match['match_ratio']*100)}% action={action} "
                      f"matched={match['matched_skills']}")

                if action == "auto_apply":
                    applied = try_quick_apply(driver, job["url"])
                    if applied:
                        applied_count += 1
                        notify_auto_applied(cfg, job["title"], job["company"], job["url"], match)
                    else:
                        # couldn't auto apply (e.g. needs external form) -> fall back to notify
                        notify_needs_review(cfg, job["title"], job["company"], job["url"], match)
                elif action == "notify":
                    notify_needs_review(cfg, job["title"], job["company"], job["url"], match)
                # action == "skip" -> ignore silently

                human_pause(2, 4)

    driver.quit()
    print(f"[naukri_agent] Done. Auto-applied to {applied_count} jobs.")
