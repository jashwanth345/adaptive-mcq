from uuid import UUID

from sqlalchemy import text

from ..auth.security import AuthError
from ..database import Database


class StudentService:
    def __init__(self, database: Database):
        self.database = database

    def dashboard(self, student: UUID):
        with self.database.session() as session:
            result = session.execute(
                text("""
                SELECT jsonb_build_object(
                  'preferences',jsonb_build_object('preferred_difficulty',p.preferred_difficulty),
                  'counts',jsonb_build_object(
                    'courses',(SELECT count(*) FROM mcq.course_memberships WHERE student_id=:student AND active),
                    'materials',(SELECT count(*) FROM mcq.materials WHERE owner_id=:student AND NOT archived),
                    'submitted_attempts',(SELECT count(*) FROM mcq.attempts WHERE student_id=:student AND state='submitted'),
                    'feedback',(SELECT count(*) FROM mcq.feedback WHERE student_id=:student)),
                  'courses',coalesce((SELECT jsonb_agg(c ORDER BY c.joined_at DESC,c.id DESC) FROM (
                    SELECT c.id,c.title,m.joined_at FROM mcq.course_memberships m
                    JOIN mcq.courses c ON c.id=m.course_id
                    WHERE m.student_id=:student AND m.active ORDER BY m.joined_at DESC,c.id DESC LIMIT 6
                  ) c),'[]'::jsonb))
                FROM mcq.student_profiles p WHERE p.user_id=:student
            """),
                {"student": student},
            ).scalar_one_or_none()
            if result is None:
                raise AuthError(
                    503, "STUDENT_PROFILE_UNAVAILABLE", "Student profile is unavailable."
                )
            return result

    def attempts(self, student: UUID, offset: int, limit: int):
        with self.database.session() as session:
            result = session.execute(
                text("""
                SELECT jsonb_build_object(
                  'total',(SELECT count(*) FROM mcq.attempts WHERE student_id=:student),
                  'items',coalesce((SELECT jsonb_agg(a ORDER BY a.started_at DESC,a.id DESC) FROM (
                    SELECT t.id,a.title,a.kind,t.state,t.attempt_number,t.started_at,t.submitted_at
                    FROM mcq.attempts t JOIN mcq.assessments a ON a.id=t.assessment_id
                    WHERE t.student_id=:student ORDER BY t.started_at DESC,t.id DESC LIMIT :limit OFFSET :offset
                  ) a),'[]'::jsonb))
            """),
                {"student": student, "limit": limit, "offset": offset},
            ).scalar_one()
            return {**result, "offset": offset, "limit": limit}

    def preferences(self, student: UUID, difficulty: str):
        with self.database.session() as session, session.begin():
            result = (
                session.execute(
                    text("""
                UPDATE mcq.student_profiles SET preferred_difficulty=:difficulty
                WHERE user_id=:student RETURNING preferred_difficulty
            """),
                    {"student": student, "difficulty": difficulty},
                )
                .mappings()
                .one_or_none()
            )
            if result is None:
                raise AuthError(
                    503, "STUDENT_PROFILE_UNAVAILABLE", "Student profile is unavailable."
                )
            session.execute(
                text("""
                INSERT INTO mcq.audit_events(actor_id,event_type,entity_type,entity_id)
                VALUES(:student,'student.preferences_saved','student_profile',:student)
            """),
                {"student": student},
            )
            return dict(result)
