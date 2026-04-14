
import sqlite3

def setup_database(db_path="toString.db"):
	conn = sqlite3.connect(db_path)
	cursor = conn.cursor()

	# Create users table with role information
	cursor.execute('''
	CREATE TABLE IF NOT EXISTS users (
		user_id INTEGER PRIMARY KEY AUTOINCREMENT,
		username TEXT UNIQUE NOT NULL,
		password TEXT NOT NULL,
		role TEXT DEFAULT 'user',
		created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
	);
	''')

	# Create message boards
	cursor.execute('''
	CREATE TABLE IF NOT EXISTS messageBoard (
		board_id INTEGER PRIMARY KEY AUTOINCREMENT,
		name TEXT UNIQUE NOT NULL,
		description TEXT,
		creator_id INTEGER REFERENCES users(user_id),
		created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
	);
	''')

	# Create messages
	cursor.execute('''
	CREATE TABLE IF NOT EXISTS messages (
		message_id INTEGER PRIMARY KEY AUTOINCREMENT,
		user_id INTEGER REFERENCES users(user_id),
		board_id INTEGER REFERENCES messageBoard(board_id),
		message TEXT NOT NULL,
		created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
		updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
	);
	''')

	# Create board moderators (many-to-many relationship)
	cursor.execute('''
	CREATE TABLE IF NOT EXISTS board_moderators (
		moderator_id INTEGER PRIMARY KEY AUTOINCREMENT,
		user_id INTEGER REFERENCES users(user_id),
		board_id INTEGER REFERENCES messageBoard(board_id),
		assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
		UNIQUE(user_id, board_id)
	);
	''')

	# Create audit logs for tracking role changes and actions
	cursor.execute('''
	CREATE TABLE IF NOT EXISTS audit_logs (
		log_id INTEGER PRIMARY KEY AUTOINCREMENT,
		action TEXT NOT NULL,
		performed_by INTEGER REFERENCES users(user_id),
		target_user INTEGER REFERENCES users(user_id),
		board_id INTEGER REFERENCES messageBoard(board_id),
		details TEXT,
		timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
	);
	''')

	conn.commit()
	conn.close()

if __name__ == "__main__":
	setup_database()
