"""Institución, cuentas y grupos de demostración."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, utcnow
from app.modules.common.enums import Role, UserStatus
from app.modules.identity.models import (
    Institution,
    Researcher,
    Student,
    Teacher,
    TeacherGroupAssignment,
    User,
)


async def ensure_institution(
    db: AsyncSession,
    *,
    code: str,
    name: str,
    required_parties: list[str] | None = None,
    retention_days: int | None = 1095,
) -> Institution:
    row = await db.scalar(select(Institution).where(Institution.code == code))
    if row is None:
        row = Institution(
            code=code,
            name=name,
            country="CO",
            consent_policy={"required_parties": required_parties or ["STUDENT", "GUARDIAN"]},
            retention_days=retention_days,
        )
        db.add(row)
        await db.flush()
    return row


async def ensure_user(
    db: AsyncSession,
    *,
    email: str | None,
    username: str | None,
    password: str,
    role: Role,
    institution_id: uuid.UUID | None,
    status: UserStatus = UserStatus.ACTIVE,
) -> User:
    stmt = select(User)
    stmt = stmt.where(func.lower(User.email) == email.lower()) if email else stmt.where(User.username == username)
    user = await db.scalar(stmt)
    if user is None:
        user = User(
            email=email.lower() if email else None,
            username=username,
            password_hash=hash_password(password),
            role=role.value,
            status=status.value,
            institution_id=institution_id,
            password_changed_at=utcnow(),
        )
        db.add(user)
        await db.flush()
    return user


async def create_admin(db: AsyncSession, *, email: str, password: str) -> User:
    return await ensure_user(db, email=email, username=None, password=password, role=Role.ADMIN, institution_id=None)


async def create_teacher(
    db: AsyncSession,
    *,
    email: str,
    password: str,
    institution: Institution,
    groups: list[tuple[str, str]],
) -> Teacher:
    user = await ensure_user(
        db,
        email=email,
        username=None,
        password=password,
        role=Role.TEACHER,
        institution_id=institution.id,
    )
    teacher = await db.scalar(select(Teacher).where(Teacher.user_id == user.id))
    if teacher is None:
        count = await db.scalar(
            select(func.count()).select_from(Teacher).where(Teacher.institution_id == institution.id)
        )
        teacher = Teacher(
            user_id=user.id,
            institution_id=institution.id,
            display_code=f"TEA-{(count or 0) + 1:03d}",
        )
        db.add(teacher)
        await db.flush()
        for grade, group_code in groups:
            db.add(
                TeacherGroupAssignment(
                    teacher_id=teacher.id,
                    institution_id=institution.id,
                    grade=grade,
                    group_code=group_code,
                )
            )
        await db.flush()
    return teacher


async def create_researcher(
    db: AsyncSession, *, email: str, password: str, institution: Institution | None
) -> Researcher:
    user = await ensure_user(
        db,
        email=email,
        username=None,
        password=password,
        role=Role.RESEARCHER,
        institution_id=institution.id if institution else None,
    )
    researcher = await db.scalar(select(Researcher).where(Researcher.user_id == user.id))
    if researcher is None:
        count = await db.scalar(select(func.count()).select_from(Researcher))
        researcher = Researcher(
            user_id=user.id,
            institution_id=institution.id if institution else None,
            display_code=f"RES-{(count or 0) + 1:03d}",
        )
        db.add(researcher)
        await db.flush()
    return researcher


async def create_student(
    db: AsyncSession,
    *,
    username: str,
    password: str,
    institution: Institution,
    grade: str,
    group_code: str,
    research_status: str = "ELIGIBLE",
) -> Student:
    user = await ensure_user(
        db,
        email=None,
        username=username,
        password=password,
        role=Role.STUDENT,
        institution_id=institution.id,
        status=UserStatus.ACTIVE if research_status == "ELIGIBLE" else UserStatus.PENDING_CONSENT,
    )
    student = await db.scalar(select(Student).where(Student.user_id == user.id))
    if student is None:
        count = await db.scalar(
            select(func.count()).select_from(Student).where(Student.institution_id == institution.id)
        )
        student = Student(
            user_id=user.id,
            institution_id=institution.id,
            participant_code=f"STU-{(count or 0) + 1:03d}",
            grade=grade,
            group_code=group_code,
            research_status=research_status,
        )
        db.add(student)
        await db.flush()
    return student
