#Lets create a custom logger for the Document Portal application
import os
import logging
from datetime import datetime
import structlog

class CustomLogger:
    def __init__(self, log_dir="logs"):
        # Ensure logs directory exists
        self.logs_dir = os.path.join(os.getcwd(), log_dir)
        os.makedirs(self.logs_dir, exist_ok=True)

        # Timestamped log file (for persistence)
        log_file = f"{datetime.now().strftime('%m_%d_%Y_%H_%M_%S')}.log"
        self.log_file_path = os.path.join(self.logs_dir, log_file)

    def get_logger(self, name=__file__):
        logger_name = os.path.basename(name)

        # Configure logging for console + file (both JSON)

        # Create file handler for JSON logging in on the logs file
        file_handler = logging.FileHandler(self.log_file_path)
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(logging.Formatter("%(message)s"))  # Raw JSON lines

        # Create console handler for JSON logging in the console
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(logging.Formatter("%(message)s"))

        logging.basicConfig(
            level=logging.INFO,
            format="%(message)s",  # Structlog will handle JSON rendering
            handlers=[console_handler, file_handler]
        )

        # Configure structlog for JSON structured logging
        structlog.configure(
            processors=[
                structlog.processors.TimeStamper(fmt="iso", utc=True, key="timestamp"),
                structlog.processors.add_log_level,
                structlog.processors.EventRenamer(to="event"),
                structlog.processors.JSONRenderer()
            ],
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )

        return structlog.get_logger(logger_name)


# # --- Usage Example ---
if __name__ == "__main__":
    logger = CustomLogger().get_logger(__file__)
    logger.info("User uploaded a file", user_id=123, filename="report.pdf")
    logger.error("Failed to process PDF", error="File not found", user_id=123)





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