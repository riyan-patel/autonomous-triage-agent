-- Build order step 7: human approve/reject decisions from the dashboard,
-- for actions the agent escalated (suggest mode) instead of acting on
-- automatically. One review per action.
CREATE TABLE reviews (
    id         SERIAL PRIMARY KEY,
    action_id  INTEGER NOT NULL REFERENCES actions(id) ON DELETE CASCADE,
    decision   TEXT NOT NULL CHECK (decision IN ('approved', 'rejected')),
    reviewer   TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (action_id)
);
