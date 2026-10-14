CREATE TABLE question_review_cards (
    username_key TEXT NOT NULL REFERENCES players(username_key) ON DELETE CASCADE,
    question_set_id BIGINT NOT NULL REFERENCES question_sets(id) ON DELETE CASCADE,
    question_key TEXT NOT NULL,
    card_json TEXT NOT NULL,
    PRIMARY KEY (username_key, question_set_id, question_key)
);
