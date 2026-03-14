CREATE TABLE IF NOT EXISTS recipe (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    target_sandwiches INTEGER NOT NULL DEFAULT 1500,
    target_enabled INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS ingredient (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    qty_per_sandwich REAL NOT NULL,
    unit TEXT NOT NULL,
    package_size REAL,
    package_unit TEXT,
    display_note TEXT
);

CREATE TABLE IF NOT EXISTS purchase (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    volunteer_name TEXT NOT NULL,
    volunteer_phone TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS purchase_item (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    purchase_id INTEGER NOT NULL REFERENCES purchase(id),
    ingredient_id INTEGER NOT NULL REFERENCES ingredient(id),
    quantity REAL NOT NULL
);

INSERT OR IGNORE INTO recipe (id, target_sandwiches, target_enabled) VALUES (1, 1500, 1);
