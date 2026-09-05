class VeritasException(Exception):
    def __init__(
        self,
        message: str,
        status_code: int = 400,
        code: str = "VERITAS_ERROR",
    ):
        self.message = message
        self.status_code = status_code
        self.code = code

        super().__init__(message)


class ExternalServiceException(VeritasException):
    def __init__(
        self,
        message: str = "Serviço externo indisponível.",
        code: str = "EXTERNAL_SERVICE_ERROR",
    ):
        super().__init__(
            message=message,
            status_code=503,
            code=code,
        )
