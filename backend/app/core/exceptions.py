class AppError(Exception):
    def __init__(self, message: str, *, status_code: int = 500, code: str = "internal_error"):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code


class ValidationError(AppError):
    def __init__(self, message: str):
        super().__init__(message, status_code=400, code="validation_error")


class ServiceUnavailableError(AppError):
    def __init__(self, message: str = "The service is temporarily unavailable."):
        super().__init__(message, status_code=503, code="service_unavailable")


class RetrievalError(AppError):
    def __init__(self, message: str = "Unable to retrieve relevant legal context."):
        super().__init__(message, status_code=502, code="retrieval_error")


class NotFoundError(AppError):
    def __init__(self, message: str = "Resource not found."):
        super().__init__(message, status_code=404, code="not_found")
