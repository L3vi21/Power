import threading
import time
import schedule

from pull_data import pull_data, archive_old_metered_data_files  # Your polling function
from app import app, refresh_data# Your Flask app

def run_data_cycle():
    pull_data()
    refresh_data()

def start_scheduler():
    # Schedule every 10 minutes
    print("⏰ Scheduler thread started")
    schedule.every(1).minutes.do(lambda: print("⏳ Scheduled task should run now"))
    schedule.every(1).minutes.do(run_data_cycle)

    #Running initial data pull at startup
    print("▶️ Running initial data pull")
    run_data_cycle()

    while True:
        schedule.run_pending()
        time.sleep(1)

def start_flask():
    print("⏰ Flask Scheduler thread started")
    app.run(host='0.0.0.0', port= 5000, debug= True, use_reloader= False)

if __name__ == "__main__":
    try:
        #Archive Preexisting data files in the directory
        archive_old_metered_data_files()

        run_data_cycle()
        #Start Flask in one thread
        flask_thread = threading.Thread(target=start_flask)
        flask_thread.daemon = True
        flask_thread.start()

        #Start scheduler in another
        scheduler_thread = threading.Thread(target=start_scheduler)
        scheduler_thread.daemon = True
        scheduler_thread.start()
        
    except Exception as e:
        print(f"A fatal error has occured during startup: {e}")



    # Start Flask app
    start_flask()
