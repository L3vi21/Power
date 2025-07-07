import threading
import time
import schedule

from pull_data import pull_data  # Your polling function
from app import app  # Your Flask app

def start_scheduler():
    # Schedule every 10 minutes
    schedule.every(10).minutes.do(pull_data)

    # Immediately run it once at startup
    pull_data()

    while True:
        schedule.run_pending()
        time.sleep(1)

def start_flask():
    app.run(debug=True, use_reloader=False)

if __name__ == "__main__":
    # Start Modbus polling in a separate thread
    scheduler_thread = threading.Thread(target=start_scheduler)
    scheduler_thread.daemon = True
    scheduler_thread.start()

    # Start Flask app
    start_flask()
