import threading
import time
import schedule

from pull_data import pull_data, archive_old_metered_data_files  # Your polling function
from app import app  # Your Flask app

def start_scheduler():
    # Schedule every 10 minutes
    print("⏰ Scheduler thread started")
    schedule.every(1).minutes.do(lambda: print("⏳ Scheduled task should run now"))
    schedule.every(1).minutes.do(pull_data)

    #Running initial data pull at startup
    print("▶️ Running initial data pull")
    pull_data()

    while True:
        schedule.run_pending()
        time.sleep(1)

def start_flask():
    app.run(host='0.0.0.0', port= 5000, debug= True, use_reloader= False)

if __name__ == "__main__":
    #Archieve any existing data files before reading
    archive_old_metered_data_files()

    #Start Flask in one thread
    flask_thread = threading.Thread(target=start_flask)
    flask_thread.daemon = True
    flask_thread.start()

    #Start scheduler in another
    scheduler_thread = threading.Thread(target=start_scheduler)
    scheduler_thread.daemon = True
    scheduler_thread.start()



    # Start Flask app
    start_flask()
