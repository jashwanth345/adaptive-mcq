from uuid import UUID

from sqlalchemy import text

from ..auth.security import AuthError
from ..database import Database


class TeacherService:
    def __init__(self, database: Database):
        self.database = database

    def dashboard(self, owner: UUID):
        # One statement provides a consistent snapshot for counts and recent rows.
        with self.database.session() as session:
            return session.execute(
                text("""
                SELECT jsonb_build_object(
                  'counts', jsonb_build_object(
                    'courses', (SELECT count(*) FROM mcq.courses WHERE owner_id=:owner),
                    'materials', (SELECT count(*) FROM mcq.materials WHERE owner_id=:owner AND NOT archived),
                    'questions', (SELECT count(*) FROM mcq.questions WHERE owner_id=:owner AND NOT archived),
                    'assessments', (SELECT count(*) FROM mcq.assessments WHERE owner_id=:owner AND kind='classroom')),
                  'recent_assessments', coalesce((SELECT jsonb_agg(r ORDER BY r.created_at DESC,r.id DESC) FROM (
                    SELECT a.id,a.title,c.title AS course_title,a.state,a.created_at
                    FROM mcq.assessments a JOIN mcq.courses c ON c.id=a.course_id AND c.owner_id=a.owner_id
                    WHERE a.owner_id=:owner AND a.kind='classroom'
                    ORDER BY a.created_at DESC,a.id DESC LIMIT 5
                  ) r), '[]'::jsonb))
            """),
                {"owner": owner},
            ).scalar_one()

    def courses(self, owner: UUID, offset: int, limit: int):
        with self.database.session() as session:
            data = session.execute(
                text("""
                SELECT jsonb_build_object(
                  'total',(SELECT count(*) FROM mcq.courses WHERE owner_id=:owner),
                  'items',coalesce((SELECT jsonb_agg(r ORDER BY r.created_at DESC,r.id DESC) FROM (
                    SELECT c.id,c.title,c.created_at,
                      (SELECT count(*) FROM mcq.topics t WHERE t.course_id=c.id AND t.owner_id=:owner) AS topic_count
                    FROM mcq.courses c WHERE c.owner_id=:owner
                    ORDER BY c.created_at DESC,c.id DESC LIMIT :limit OFFSET :offset
                  ) r),'[]'::jsonb))
            """),
                {"owner": owner, "offset": offset, "limit": limit},
            ).scalar_one()
            return {**data, "offset": offset, "limit": limit}

    def detail(self, owner: UUID, course_id: UUID):
        with self.database.session() as session:
            row = (
                session.execute(
                    text("""
                SELECT c.id,c.title,c.created_at,
                  (SELECT count(*) FROM mcq.topics WHERE course_id=c.id AND owner_id=:owner) AS topic_count,
                  coalesce((SELECT jsonb_agg(t ORDER BY t.name,t.id) FROM (
                    SELECT id,name FROM mcq.topics WHERE course_id=c.id AND owner_id=:owner ORDER BY name,id LIMIT 100
                  ) t),'[]'::jsonb) AS topics
                FROM mcq.courses c WHERE c.id=:id AND c.owner_id=:owner
            """),
                    {"id": course_id, "owner": owner},
                )
                .mappings()
                .one_or_none()
            )
            if row is None:
                raise AuthError(404, "COURSE_NOT_FOUND", "Course not found.")
            return dict(row)

    def create(self, owner: UUID, title: str, course_id: UUID | None = None):
        with self.database.session() as session, session.begin():
            # Serialize this owner's short organization writes, including retries.
            # Does not need UPDATE rights or a table-wide lock.
            session.execute(
                text("SELECT pg_advisory_xact_lock(hashtextextended(:owner,6))"),
                {"owner": str(owner)},
            )
            if course_id is not None:
                found = session.execute(
                    text("SELECT id FROM mcq.courses WHERE id=:id AND owner_id=:owner"),
                    {"id": course_id, "owner": owner},
                ).scalar_one_or_none()
                if found is None:
                    raise AuthError(404, "COURSE_NOT_FOUND", "Course not found.")
                count = session.execute(
                    text("SELECT count(*) FROM mcq.topics WHERE course_id=:id AND owner_id=:owner"),
                    {"id": course_id, "owner": owner},
                ).scalar_one()
                if count >= 100:
                    raise AuthError(409, "TOPIC_LIMIT", "This course has reached its topic limit.")
                duplicate = session.execute(
                    text(
                        "SELECT id FROM mcq.topics WHERE owner_id=:owner AND course_id=:id AND lower(name)=lower(:title)"
                    ),
                    {"owner": owner, "id": course_id, "title": title},
                ).first()
                if duplicate:
                    raise AuthError(
                        409, "DUPLICATE_TOPIC", "This topic already exists in the course."
                    )
                row = (
                    session.execute(
                        text(
                            "INSERT INTO mcq.topics(owner_id,course_id,name) VALUES(:owner,:id,:title) RETURNING id,name"
                        ),
                        {"owner": owner, "id": course_id, "title": title},
                    )
                    .mappings()
                    .one()
                )
                kind = "topic"
            else:
                duplicate = session.execute(
                    text(
                        "SELECT id FROM mcq.courses WHERE owner_id=:owner AND lower(title)=lower(:title)"
                    ),
                    {"owner": owner, "title": title},
                ).first()
                if duplicate:
                    raise AuthError(
                        409, "DUPLICATE_COURSE", "You already have a course with this title."
                    )
                row = (
                    session.execute(
                        text(
                            "INSERT INTO mcq.courses(owner_id,title) VALUES(:owner,:title) RETURNING id,title,created_at,0 AS topic_count"
                        ),
                        {"owner": owner, "title": title},
                    )
                    .mappings()
                    .one()
                )
                kind = "course"
            session.execute(
                text(
                    "INSERT INTO mcq.audit_events(actor_id,event_type,entity_type,entity_id) VALUES(:owner,:event,:kind,:id)"
                ),
                {"owner": owner, "event": f"teacher.{kind}_created", "kind": kind, "id": row["id"]},
            )
            return dict(row)
