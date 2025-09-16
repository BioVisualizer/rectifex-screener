import sys
import logging
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from main import MainWindow

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def run_test():
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    logging.info("Starting UI test.")

    def select_dax_and_scan():
        logging.info("Selecting DAX from dropdown.")
        dax_index = window.ticker_source_combo.findText("DAX")
        if dax_index == -1:
            logging.error("DAX not found in dropdown!")
            app.quit()
            return

        window.ticker_source_combo.setCurrentIndex(dax_index)

        logging.info("Clicking scan button.")
        window.scan_button.click()

        # Give the scan some time to start
        QTimer.singleShot(2000, check_scan_finished)

    def check_scan_finished():
        if window.is_scanning:
            logging.info("Scan is running, checking again in 1 second.")
            QTimer.singleShot(1000, check_scan_finished)
        else:
            logging.info("Scan finished.")
            verify_results()
            app.quit()

    def verify_results():
        row_count = window.results_table.rowCount()
        logging.info(f"Found {row_count} rows in the results table.")
        if row_count > 0:
            logging.info("Test PASSED: Table was populated.")
        else:
            logging.error("Test FAILED: Table is empty.")

    # Start the test after the event loop has started
    QTimer.singleShot(100, select_dax_and_scan)

    sys.exit(app.exec())

if __name__ == "__main__":
    run_test()
