# Lets create a custom logger for the Document Portal application

import os                  # For working with directories and file paths
import logging             # Python’s built-in logging library
from datetime import datetime   # To generate timestamped log filenames
import structlog           # External library for structured (JSON) logging

class CustomLogger:
    def __init__(self, log_dir="logs"):
        # Ensure logs directory exists
        self.logs_dir = os.path.join(os.getcwd(), log_dir)   # Create absolute path to "logs" folder inside current working directory
        os.makedirs(self.logs_dir, exist_ok=True)            # Create "logs" folder if it doesn’t already exist

        # Timestamped log file (for persistence)
        log_file = f"{datetime.now().strftime('%m_%d_%Y_%H_%M_%S')}.log"  # Example: 09_15_2025_00_30_12.log
        self.log_file_path = os.path.join(self.logs_dir, log_file)        # Full path of log file inside logs directory

    def get_logger(self, name=__file__):    #here it might pass the full path of the file
        # Get just the filename part (e.g., custom_logger.py instead of full path)
        logger_name = os.path.basename(name)

        # Create file handler for logging to a file (file_handler configurations)
        file_handler = logging.FileHandler(self.log_file_path)   # Log file will be created inside logs/
        file_handler.setLevel(logging.INFO)                      # Minimum log level = INFO
        file_handler.setFormatter(logging.Formatter("%(message)s"))  # Output raw JSON lines only

        # Create console handler for logging to console (stdout)
        console_handler = logging.StreamHandler()     #StreamHandler to display the logs on terminal itself
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(logging.Formatter("%(message)s")) #Ensures only the log message (not Python’s default [INFO] logger-name: message) is shown.

        # Configure root logger with both handlers (console + file)
        logging.basicConfig(
            level=logging.INFO,       # Root logger level = INFO
            format="%(message)s",     # Structlog will override formatting to JSON
            handlers=[console_handler, file_handler]  #ch sends info to terminal and fh sends info to log file
        )

        # Configure structlog for JSON structured logging
        structlog.configure(
            processors=[
                structlog.processors.TimeStamper(fmt="iso", utc=True, key="timestamp"), # Add ISO timestamp
                structlog.processors.add_log_level,                                     # Include log level (info/error/etc.)
                structlog.processors.EventRenamer(to="event"),                          # Rename 'msg' to 'event'
                structlog.processors.JSONRenderer()                                     # Render output as JSON
            ],
            logger_factory=structlog.stdlib.LoggerFactory(),  # Integrates with Python’s logging (logging.basicConfig)
            cache_logger_on_first_use=True,                   # Cache for performance
        )

        # Return a structured logger instance
        return structlog.get_logger(logger_name)


# --- Usage Example ---
if __name__ == "__main__":
    logger = CustomLogger().get_logger(__file__)   # Create logger with current file name
    logger.info("User uploaded a file", user_id=123, filename="report.pdf")  
    # Produces JSON log with timestamp, level=info, event="User uploaded a file", user_id=123, filename=report.pdf

    logger.error("Failed to process PDF", error="File not found", user_id=123)
    # Produces JSON log with timestamp, level=error, event="Failed to process PDF", error="File not found", user_id=123






# --- IGNORE ---# 
# This code defines a custom logger for the Document Portal application using Python's logging function

# import os
# import logging
# from datetime import datetime
# import structlog

# class CustomLogger:

#     # define an initializer function
#     def __init__(self, log_dir="logs"):
#         # Ensure logs directory exists
#         self.logs_dir = os.path.join(os.getcwd(), log_dir)
#         os.makedirs(self.logs_dir, exist_ok=True)

#         # Timestamped log file (for persistence)
#         log_file = f"{datetime.now().strftime('%m_%d_%Y_%H_%M_%S')}.log"
#         self.log_file_path = os.path.join(self.logs_dir, log_file)

#         # Configure the logger
#         logging.basicConfig(
#             filename=self.log_file_path,
#             format="[ %(asctime)s ] %(levelname)s %(name)s (line:%(lineno)d) - %(message)s",
#             level=logging.INFO
#             )

#     # Define a function to get a logger instance
#     def get_logger(self, name=__file__):
#         # `__file__` is a special built-in variable in Python. It represents the current file path (e.g., '/user/project/app.py')
#         # Setting it as the default ensures that if no name is passed, the logger is automatically tied to the current file

#         # `os.path.basename(name)` extracts only the file name (e.g., 'app.py')
#         # This keeps the logger name clean and file-specific, avoiding long paths
#         return logging.getLogger(os.path.basename(name))


# if __name__ == "__main__":
#     # creating an instance/object of CustomLogger
#     custom_logger = CustomLogger()
#     # Getting a logger instance/objece for the current file
#     logger = custom_logger.get_logger(__file__)  #__file__ passes the current file along with path

#     # Log an example message
#     logger.info("Custom logger initialized successfully second time.")