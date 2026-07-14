"""One-off curriculum lesson persistence."""


def update_lesson_session(
    conn,
    *,
    lesson_session_id,
    should_update_date,
    lesson_date,
    should_update_times,
    start_time,
    end_time,
    should_update_room,
    room,
    should_update_lesson_name,
    lesson_name,
    should_update_topic,
    topic,
    status,
):
    conn.execute(
        """
        UPDATE msi_v2.lesson_sessions
        SET session_date = CASE WHEN %s THEN %s ELSE session_date END,
            start_time = CASE WHEN %s THEN %s::time ELSE start_time END,
            end_time = CASE WHEN %s THEN %s::time ELSE end_time END,
            room = CASE WHEN %s THEN %s ELSE room END,
            source_label = CASE WHEN %s THEN %s ELSE source_label END,
            source_topic = CASE WHEN %s THEN %s ELSE source_topic END,
            status = COALESCE(NULLIF(%s, ''), status),
            updated_at = now()
        WHERE id = %s
        """,
        (
            bool(should_update_date), lesson_date,
            bool(should_update_times), start_time,
            bool(should_update_times), end_time,
            bool(should_update_room), room,
            bool(should_update_lesson_name), lesson_name,
            bool(should_update_topic), topic,
            status or "", int(lesson_session_id),
        ),
    )


__all__ = ["update_lesson_session"]
