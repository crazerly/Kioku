CREATE TABLE IF NOT EXISTS decks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    parent_deck_id INTEGER,
    FOREIGN KEY (parent_deck_id) REFERENCES decks(id)
);

CREATE TABLE IF NOT EXISTS card_types (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    fields TEXT NOT NULL,
    template_front TEXT,
    template_back TEXT,
    modified_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS cards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    card_type_id INTEGER,
    deck_id INTEGER,
    fields TEXT NOT NULL,
    card_ord INTEGER,
    is_active BOOLEAN DEFAULT 1,
    created_at INTEGER NOT NULL,
    next_due INTEGER,
    template_front TEXT,
    template_back TEXT,
    tags TEXT,
    FOREIGN KEY (card_type_id) REFERENCES card_types(id),
    FOREIGN KEY (deck_id) REFERENCES decks(id)
);