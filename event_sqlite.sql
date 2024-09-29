-- For experience purpose, integrated the SQLite DB

-- Create the Events table
CREATE TABLE scrape_events (
    event_id UUID NOT NULL,
    event_name VARCHAR(250) NOT NULL,
    website_uri VARCHAR(256) NOT NULL,
    parent_id UUID NULL,
    file_blob_path VARCHAR(256),
    start_date TIMESTAMP NOT NULL,
    end_date TIMESTAMP NULL,
    durations INT NULL,
    status VARCHAR(20) NOT NULL,
    is_active BOOLEAN NOT NULL,
    recipient_delivery BOOLEAN NOT NULL,
    counted_products INTEGER DEFAULT 0 NOT NULL,
    event_metadata JSONB,
    CONSTRAINT pk_event PRIMARY KEY (event_id)
);

ALTER TABLE scrape_events ADD COLUMN user_id UUID REFERENCES users(user_id) NOT NULL;

-- Create the Users table
CREATE TABLE users (
    user_id UUID NOT NULL,
    username VARCHAR(255) NOT NULL,
    hashed_password VARCHAR(256) NOT NULL,
    email VARCHAR(150) UNIQUE NOT NULL,
    first_name VARCHAR(150) NOT NULL,
    last_name VARCHAR(150) NOT NULL,
    is_active BOOLEAN NOT NULL,
    is_admin BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT pk_user PRIMARY KEY (user_id)
);

-- Create the Transactions table
CREATE TABLE transactions (
    transaction_id UUID NOT NULL,
    transaction_date TIMESTAMP NOT NULL,
    column_name VARCHAR(256) NOT NULL,
    existing_value VARCHAR(256) NOT NULL,
    update_value VARCHAR NOT NULL,
    blob_filename VARCHAR(256) NOT NULL,
    event_id UUID REFERENCES scrape_events(event_id) NOT NULL,
    user_id UUID REFERENCES users(user_id) NOT NULL,
    CONSTRAINT pk_transaction PRIMARY KEY (transaction_id)
);