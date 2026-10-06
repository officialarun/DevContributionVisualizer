class AppError(Exception):
    status_code = 400
    code = "bad_request"

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class InvalidRepository(AppError):
    status_code = 400
    code = "invalid_repository"


class NotFound(AppError):
    status_code = 404
    code = "not_found"


class AlreadyRunning(AppError):
    status_code = 409
    code = "already_running"


class InvalidFilter(AppError):
    status_code = 422
    code = "invalid_filter"
