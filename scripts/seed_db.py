"""
One-time DB seed script.

Run AFTER `alembic upgrade head`:
    python scripts/seed_db.py

Creates:
  - Default company (tenant root)
  - Admin user
  - Standard employee user

Safe to re-run — checks for existing records before inserting.
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy import select

from app.auth.auth import hash_password
from app.core.config import settings
from app.core.logger import get_logger
from app.db.engine import AsyncSessionLocal
from app.db.models.company import Company, CompanyPlan
from app.db.models.user import User, UserRole

logger = get_logger(__name__)


async def seed() -> None:
    async with AsyncSessionLocal() as db:
        # ── Company ───────────────────────────────────────────────────────────
        result = await db.execute(select(Company).where(Company.slug == "default"))
        company = result.scalar_one_or_none()

        if company is None:
            company = Company(
                name="Enterprise AI Demo",
                slug="default",
                plan=CompanyPlan.PRO.value,
                is_active=True,
            )
            db.add(company)
            await db.flush()
            logger.info("seed.company_created", slug="default", company_id=str(company.id))
        else:
            logger.info("seed.company_exists", company_id=str(company.id))

        # ── Admin user ────────────────────────────────────────────────────────
        result = await db.execute(
            select(User).where(User.username == "admin", User.company_id == company.id)
        )
        if result.scalar_one_or_none() is None:
            admin = User(
                company_id=company.id,
                email="admin@enterprise-ai.com",
                username="admin",
                hashed_password=hash_password("admin123"),
                role=UserRole.ADMIN.value,
                is_active=True,
            )
            db.add(admin)
            logger.info("seed.admin_created")

        # ── Standard user ─────────────────────────────────────────────────────
        result = await db.execute(
            select(User).where(User.username == "employee1", User.company_id == company.id)
        )
        if result.scalar_one_or_none() is None:
            employee = User(
                company_id=company.id,
                email="employee1@enterprise-ai.com",
                username="employee1",
                hashed_password=hash_password("emp123"),
                role=UserRole.EMPLOYEE.value,
                is_active=True,
            )
            db.add(employee)
            logger.info("seed.employee_created")

        await db.commit()
        logger.info("seed.complete")
        print("\n✅ Database seeded successfully.")
        print(f"   Company : default")
        print(f"   Admin   : admin     / admin123")
        print(f"   Employee: employee1 / emp123\n")


if __name__ == "__main__":
    asyncio.run(seed())
