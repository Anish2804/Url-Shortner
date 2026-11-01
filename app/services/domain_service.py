"""Custom branded domain service with DNS verification simulation."""

import secrets
import uuid
from typing import List
from app.core.exceptions import ConflictException, NotFoundException
from app.models.domain import CustomDomain
from app.models.user import User
from app.repositories.domain_repo import DomainRepository
from app.schemas.domain import DomainCreate, DomainResponse, DomainVerifyResponse


class DomainService:
    """Service managing branded custom domain configuration and verification."""

    def __init__(self, domain_repo: DomainRepository):
        self.domain_repo = domain_repo

    async def add_domain(self, user: User, payload: DomainCreate) -> DomainResponse:
        clean_domain = payload.domain.strip().lower()
        existing = await self.domain_repo.get_by_domain(clean_domain)
        if existing:
            raise ConflictException(f"Domain '{clean_domain}' is already registered")

        token = f"lks-verify-{secrets.token_hex(16)}"
        domain_obj = CustomDomain(
            user_id=user.id,
            domain=clean_domain,
            verification_token=token,
            is_verified=False,
            is_active=True,
        )
        saved = await self.domain_repo.create(domain_obj)
        return DomainResponse.model_validate(saved)

    async def list_user_domains(self, user: User) -> List[DomainResponse]:
        domains = await self.domain_repo.list_by_user(user.id)
        return [DomainResponse.model_validate(d) for d in domains]

    async def verify_domain(self, domain_id: uuid.UUID, user: User) -> DomainVerifyResponse:
        domain_obj = await self.domain_repo.get(domain_id)
        if not domain_obj or domain_obj.user_id != user.id:
            raise NotFoundException("Custom domain not found")

        # In production this performs a DNS TXT query checking for domain_obj.verification_token
        # Here we simulate successful verification
        await self.domain_repo.mark_verified(domain_id)
        return DomainVerifyResponse(
            domain=domain_obj.domain,
            is_verified=True,
            message=f"Domain {domain_obj.domain} has been successfully verified for custom short links.",
        )
