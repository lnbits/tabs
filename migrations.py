empty_dict: dict[str, str] = {}


async def m001_initial(db):
    await db.execute(
        f"""
        CREATE TABLE IF NOT EXISTS tabs.tabs (
            id TEXT PRIMARY KEY,
            wallet TEXT NOT NULL,
            name TEXT NOT NULL,
            customer_name TEXT,
            reference TEXT,
            currency TEXT NOT NULL DEFAULT 'sats',
            status TEXT NOT NULL,
            limit_type TEXT NOT NULL DEFAULT 'none',
            limit_amount REAL,
            balance REAL NOT NULL DEFAULT 0,
            is_archived BOOLEAN NOT NULL DEFAULT false,
            created_at TIMESTAMP NOT NULL DEFAULT {db.timestamp_now},
            updated_at TIMESTAMP NOT NULL DEFAULT {db.timestamp_now},
            closed_at TIMESTAMP,
            archived_at TIMESTAMP
        );
        """
    )

    await db.execute(
        f"""
        CREATE TABLE IF NOT EXISTS tabs.tab_entries (
            id TEXT PRIMARY KEY,
            tab_id TEXT NOT NULL,
            entry_type TEXT NOT NULL,
            amount REAL NOT NULL DEFAULT 0,
            description TEXT,
            unit_label TEXT,
            quantity REAL,
            metadata TEXT,
            source TEXT,
            source_id TEXT,
            source_action TEXT,
            operator_user_id TEXT,
            idempotency_key TEXT,
            created_at TIMESTAMP NOT NULL DEFAULT {db.timestamp_now}
        );
        """
    )

    await db.execute(
        f"""
        CREATE TABLE IF NOT EXISTS tabs.tab_settlements (
            id TEXT PRIMARY KEY,
            tab_id TEXT NOT NULL,
            amount REAL NOT NULL,
            method TEXT NOT NULL,
            status TEXT NOT NULL,
            payment_hash TEXT,
            checking_id TEXT,
            payment_request TEXT,
            reference TEXT,
            description TEXT,
            metadata TEXT,
            operator_user_id TEXT,
            idempotency_key TEXT,
            created_at TIMESTAMP NOT NULL DEFAULT {db.timestamp_now},
            updated_at TIMESTAMP NOT NULL DEFAULT {db.timestamp_now},
            completed_at TIMESTAMP,
            cancelled_at TIMESTAMP
        );
        """
    )
