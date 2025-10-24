-- Import test user from production to local database
-- User: Алексей (telegram_id: 120962578)

-- Clear existing data for this user (if any)
DELETE FROM task_results WHERE user_id IN (SELECT id FROM users WHERE telegram_id = 120962578);
DELETE FROM progress WHERE user_id IN (SELECT id FROM users WHERE telegram_id = 120962578);
DELETE FROM payments WHERE telegram_id = 120962578;
DELETE FROM users WHERE telegram_id = 120962578;

-- Insert user
INSERT INTO users (
    telegram_id, username, first_name, last_name, email,
    has_access, is_admin, current_day, completed_days, liberation_code,
    created_at, updated_at, last_activity, course_started_at, course_completed_at
) VALUES (
    120962578, 'StepunR', 'Алексей', '░▓░', NULL,
    true, false, 1, 0, '___________',
    '2025-10-23 18:06:59.325136', '2025-10-24 09:56:38.105366',
    '2025-10-24 09:56:38.104648', '2025-10-23 23:32:21.000737', NULL
) RETURNING id;

-- Get user_id for further inserts
DO $$
DECLARE
    v_user_id INTEGER;
BEGIN
    SELECT id INTO v_user_id FROM users WHERE telegram_id = 120962578;

    -- Insert progress
    INSERT INTO progress (
        user_id, day_number, video_watched, brief_read, tasks_completed,
        total_tasks, completed_tasks, correct_answers, code_letter,
        started_at, completed_at
    ) VALUES (
        v_user_id, 1, true, true, false,
        0, 4, 4, '',
        '2025-10-23 23:06:49.621862', NULL
    );

    -- Insert task result
    INSERT INTO task_results (
        user_id, day_number, task_number, task_type, task_title,
        is_correct, attempts, user_answer, correct_answer,
        voice_file_id, voice_duration, recognized_text,
        created_at, completed_at
    ) VALUES (
        v_user_id, 1, 1, 'CHOICE', '',
        false, 10, 'D) Hi, I''m good.', 'A) Hi! Nice to meet you.',
        '', NULL, '',
        '2025-10-24 00:27:47.034249', NULL
    );
END $$;

-- Verify import
SELECT
    u.telegram_id, u.username, u.first_name, u.has_access, u.current_day,
    COUNT(DISTINCT p.id) as progress_records,
    COUNT(DISTINCT tr.id) as task_results
FROM users u
LEFT JOIN progress p ON p.user_id = u.id
LEFT JOIN task_results tr ON tr.user_id = u.id
WHERE u.telegram_id = 120962578
GROUP BY u.id, u.telegram_id, u.username, u.first_name, u.has_access, u.current_day;
