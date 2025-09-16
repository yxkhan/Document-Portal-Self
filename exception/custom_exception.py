import sys                     # Provides access to interpreter-specific functions (used for exception info)
import traceback               # Used to extract and format detailed stack trace information
from typing import Optional, cast  # For type hints: Optional = value or None, cast = type hinting helper


# Custom Exception Class for Document Portal
class DocumentPortalException(Exception):

    def __init__(self, error_message, error_details: Optional[object] = None):
        """
        error_message: Custom message or exception object
        error_details: Can be sys (to call sys.exc_info()), an Exception instance, or None
        """

        # Normalize error_message → ensure it's always a string
        if isinstance(error_message, BaseException):   # If it's an Exception object
            norm_msg = str(error_message)              # Convert to string
        else:
            norm_msg = str(error_message)              # If it's plain text, convert to string anyway

        # Initialize placeholders for exception info
        exc_type = exc_value = exc_tb = None

        # Case-1: If error_details is None → capture current exception context
        if error_details is None:
            exc_type, exc_value, exc_tb = sys.exc_info()

        # Case-2: If error_details has "exc_info" method (like sys module)
        else:
            if hasattr(error_details, "exc_info"):  #has attribute? checks whether error_details has exc_info method
                exc_info_obj = cast(sys, error_details)         # Tell type checker it's sys
                exc_type, exc_value, exc_tb = exc_info_obj.exc_info()  # Extract current exception details

            # Case-3: If error_details itself is an Exception object
            elif isinstance(error_details, BaseException):
                exc_type, exc_value, exc_tb = type(error_details), error_details, error_details.__traceback__

            # Case-4: Fallback → same as Case-1
            else:
                exc_type, exc_value, exc_tb = sys.exc_info()

        # Navigate traceback chain to reach the last frame (deepest error location)
        last_tb = exc_tb
        while last_tb and last_tb.tb_next:
            last_tb = last_tb.tb_next

        # Store filename and line number of the error. If no traceback is available, fallback to <unknown> and -1.
        self.file_name = last_tb.tb_frame.f_code.co_filename if last_tb else "<unknown>"
        self.lineno = last_tb.tb_lineno if last_tb else -1
        self.error_message = norm_msg

        # Generate pretty traceback string if available
        if exc_type and exc_tb:
            self.traceback_str = ''.join(traceback.format_exception(exc_type, exc_value, exc_tb))
        else:
            self.traceback_str = ""

        # Initialize base Exception with the stringified version of this custom exception
        #Ensures that when Python internally handles this exception, it already has your formatted message stored.
        super().__init__(self.__str__())

    def __str__(self):
        """
        Defines what is shown when str(exception) is called.
        Includes file, line number, and custom message.
        Optionally appends full traceback.
        """
        base = f"Error in [{self.file_name}] at line [{self.lineno}] | Message: {self.error_message}"
        if self.traceback_str:   # If traceback is captured, include it
            return f"{base}\nTraceback:\n{self.traceback_str}"
        return base              # Otherwise, just return the base error message

    def __repr__(self):
        """
        Defines developer-friendly representation (used in debugger or logs).
        This is the shorter, debug-only string you’d see if you print the object directly in a Python shell.
        """
        return f"DocumentPortalException(file={self.file_name!r}, line={self.lineno}, message={self.error_message!r})"


# Demo usage (only runs when this file is executed directly, not when imported)
if __name__ == "__main__":

    # Demo-1: Division by zero (ZeroDivisionError) → wrapped in DocumentPortalException
    try:
        a = 1 / 0   # Will raise ZeroDivisionError
    except Exception as e:
        # Raise custom exception with original exception as context
        raise DocumentPortalException("Division failed", e) from e

    # Demo-2: Example with ValueError (commented out)
    # try:
    #     a = int("abc")  # Will raise ValueError
    # except ValueError as e:
    #     raise DocumentPortalException("Failed while processing document", e)
    #
    # # Old pattern with sys (still supported)
    # except Exception as e:
    #     raise DocumentPortalException(e, sys)
