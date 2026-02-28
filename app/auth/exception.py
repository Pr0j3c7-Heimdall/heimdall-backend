"""Auth 도메인 예외"""


class ProviderNotSupportedError(Exception):
    """지원하지 않는 OAuth provider"""


class AccountDeletedError(Exception):
    """탈퇴한 계정"""
