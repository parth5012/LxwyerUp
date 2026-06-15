import os
import logging
from celery import Celery
from sqlmodel import Session
from playwright.sync_api import sync_playwright
from config import settings
from app.database import engine
from app.models import Case, FilingTaskState, DraftDocument
from datetime import datetime


logger =  logging.getLogger('app.tasks')
# Initialize Celery
celery_app = Celery("tasks", broker=settings.CELERY_BROKER_URL, backend=settings.CELERY_RESULT_BACKEND)

# Ensure Celery configurations
celery_app.conf.update(
    task_track_started=True,
    task_time_limit=300,
)

def log_task_progress(session: Session, task_state: FilingTaskState, message: str):
    """
    Utility helper to append timestamped logs to the background task state.
    """
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    task_state.logs += f"[{timestamp}] {message}\n"
    task_state.updated_at = datetime.utcnow()
    session.add(task_state)
    session.commit()

@celery_app.task(name="app.tasks.run_efiling_workflow")
def run_efiling_workflow(case_id: int, task_uuid: str):
    """
    Celery background worker: Launches Playwright, log in, fills court forms,
    uploads files, takes screen captures, and records e-filing success state.
    """
    # Initialize session
    with Session(engine) as session:
        # Load Case and Task State
        case = session.get(Case, case_id)
        task_state = session.query(FilingTaskState).filter(FilingTaskState.task_id == task_uuid).first()

        if not case or not task_state:
            return "Error: Case or TaskState not found."

        task_state.status = "PROGRESS"
        log_task_progress(session, task_state, "Task started. Spawning headless Playwright browser...")

        # Find the latest PDF draft
        draft = session.query(DraftDocument).filter(DraftDocument.case_id == case_id).order_by(DraftDocument.created_at.desc()).first()
        if not draft or not draft.file_path or not os.path.exists(draft.file_path):
            log_task_progress(session, task_state, "Error: No compiled draft document PDF found for e-filing.")
            task_state.status = "FAILURE"
            session.add(task_state)
            session.commit()
            return "Failure: Missing draft document."

        try:
            with sync_playwright() as p:
                log_task_progress(session, task_state, "Launching Chromium browser...")
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()

                # Target our local mock court portal endpoint
                mock_portal_url = f"http://localhost:{settings.PORT}/mock-court"
                log_task_progress(session, task_state, f"Navigating to Mock Court Portal: {mock_portal_url}")
                page.goto(mock_portal_url)
                page.wait_for_timeout(1000)

                # Step 1: Login Form
                log_task_progress(session, task_state, "Filling login credentials (Username: admin)...")
                page.fill("#username", "admin")
                page.fill("#password", "password123")
                
                # Take login screenshot
                login_screenshot = os.path.join(settings.STORAGE_DIR, "screenshots", f"{task_uuid}_1_login.png")
                page.screenshot(path=login_screenshot)
                task_state.screenshot_path = login_screenshot
                log_task_progress(session, task_state, "Login form filled. Submitting...")
                page.click("#submit-btn")
                page.wait_for_timeout(1500)

                # Step 2: Fill Claim Form
                log_task_progress(session, task_state, "Successfully logged in. Filling Case Details form...")
                page.fill("#case-title", case.title)
                page.fill("#claimant-name", case.claimant_name)
                page.fill("#respondent-name", case.respondent_name)
                page.fill("#claim-amount", str(case.dispute_amount))
                page.fill("#case-details", case.description)

                # Upload draft PDF file
                log_task_progress(session, task_state, f"Uploading draft PDF file: {os.path.basename(draft.file_path)}...")
                page.set_input_files("#file-upload", draft.file_path)

                form_screenshot = os.path.join(settings.STORAGE_DIR, "screenshots", f"{task_uuid}_2_form.png")
                page.screenshot(path=form_screenshot)
                task_state.screenshot_path = form_screenshot
                log_task_progress(session, task_state, "Filing details entered. Submitting case filing...")
                page.click("#submit-case-btn")
                page.wait_for_timeout(2000)

                # Step 3: Verify Success Response
                success_text = page.locator("#status-message").inner_text()
                if "Successfully Filed" in success_text:
                    log_task_progress(session, task_state, f"Court Response: {success_text}")
                    
                    final_screenshot = os.path.join(settings.STORAGE_DIR, "screenshots", f"{task_uuid}_3_success.png")
                    page.screenshot(path=final_screenshot)
                    task_state.screenshot_path = final_screenshot
                    
                    # Update states
                    task_state.status = "SUCCESS"
                    case.status = "Completed"
                    log_task_progress(session, task_state, "E-Filing workflow completed successfully. Case marked COMPLETED.")
                else:
                    log_task_progress(session, task_state, f"Error: Received unexpected court response: {success_text}")
                    task_state.status = "FAILURE"

                browser.close()

        except Exception as err:
            logger.error(f"Playwright execution error: {err}")
            log_task_progress(session, task_state, f"Browser Automation Crash Error: {str(err)}")
            task_state.status = "FAILURE"

        # Final Database Sync
        session.add(task_state)
        session.add(case)
        session.commit()

    return "Filing completed."
