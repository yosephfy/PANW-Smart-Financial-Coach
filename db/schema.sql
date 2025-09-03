-- Minimal schema for Smart Financial Coach

CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS accounts (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  name TEXT,
  type TEXT,
  institution TEXT,
  mask TEXT,
  FOREIGN KEY(user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS transactions (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  account_id TEXT,
  date DATE NOT NULL,
  amount NUMERIC NOT NULL, -- negative = expense; positive = income
  merchant TEXT,
  description TEXT,
  category TEXT,
  category_source TEXT, -- csv|mcc|regex|fallback
  category_provenance TEXT, -- e.g., mcc:5411 or regex:spotify
  is_recurring BOOLEAN DEFAULT FALSE,
  mcc TEXT,
  source TEXT, -- csv|plaid|synthetic
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(user_id) REFERENCES users(id),
  FOREIGN KEY(account_id) REFERENCES accounts(id)
);

CREATE TABLE IF NOT EXISTS subscriptions (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  merchant TEXT NOT NULL,
  avg_amount NUMERIC,
  cadence TEXT, -- monthly|weekly|yearly|unknown
  last_seen DATE,
  status TEXT, -- active|paused|canceled
  price_change_pct NUMERIC,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS goals (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  name TEXT,
  target_amount NUMERIC NOT NULL,
  target_date DATE,
  monthly_target NUMERIC,
  status TEXT, -- active|achieved|off_track
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS insights (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  type TEXT,
  title TEXT,
  body TEXT,
  severity TEXT, -- info|warn|critical
  data_json TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  read_at TIMESTAMP,
  FOREIGN KEY(user_id) REFERENCES users(id)
);

-- Helpful indexes
CREATE INDEX IF NOT EXISTS idx_txn_user_date ON transactions(user_id, date);
CREATE INDEX IF NOT EXISTS idx_txn_user_merchant ON transactions(user_id, merchant);
CREATE INDEX IF NOT EXISTS idx_txn_user_date_amount_merchant ON transactions(user_id, date, amount, merchant);
CREATE INDEX IF NOT EXISTS idx_sub_user_merchant ON subscriptions(user_id, merchant);
