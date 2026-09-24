
from sqlalchemy import (
    BigInteger,
    Integer,
    Numeric,
    Text,
    TIMESTAMP,
    ForeignKey,
    func,
)

from sqlalchemy.dialects.postgresql import (
    JSONB,
)

from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
)


class Base(
    DeclarativeBase
):
    pass


class Job(Base):

    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
    )

    title: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
    )

    required_skills: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )

    preferred_skills: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )

    required_experience_years: Mapped[float | None] = mapped_column(
        Numeric(6, 2),
        nullable=True,
    )

    required_education: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )

    created_at: Mapped[object] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class Candidate(Base):

    __tablename__ = "candidates"

    id: Mapped[str] = mapped_column(
        Text,
        primary_key=True,
    )

    filename: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    skills: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )

    education: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )

    experience_years: Mapped[float | None] = mapped_column(
        Numeric(6, 2),
        nullable=True,
    )

    created_at: Mapped[object] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class ScreeningResult(Base):

    __tablename__ = "screening_results"

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
    )

    batch_id: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    job_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "jobs.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    candidate_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey(
            "candidates.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    match_score: Mapped[float | None] = mapped_column(
        Numeric(6, 4),
    )

    semantic_score: Mapped[float | None] = mapped_column(
        Numeric(6, 4),
    )

    skill_score: Mapped[float | None] = mapped_column(
        Numeric(6, 4),
    )

    experience_score: Mapped[float | None] = mapped_column(
        Numeric(6, 4),
    )

    prescreen_status: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    cluster: Mapped[int | None] = mapped_column(
        Integer,
    )

    positive_factors: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )

    review_flags: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )

    similar_resumes: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )

    full_result: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    created_at: Mapped[object] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class ScreeningSkill(Base):

    __tablename__ = "screening_skills"

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
    )

    screening_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "screening_results.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    skill_name: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    skill_status: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    created_at: Mapped[object] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
