
import sqlite3

def setup_database(db_path="toString.db"):
	conn = sqlite3.connect(db_path)
	cursor = conn.cursor()

	cursor.execute('''
	CREATE TABLE IF NOT EXISTS messages (
		message_id INTEGER PRIMARY KEY,
		user_id INTEGER REFERENCES users(user_id),
		message TEXT,
		status INTEGER
	);
	''')

	cursor.execute('''
	CREATE TABLE IF NOT EXISTS messageBoard (
		id INTEGER,
		name TEXT,
		message_id INTEGER REFERENCES messages(message_id),
		private INTEGER,
		moderator INTEGER REFERENCES users(user_id)
	);
	''')

	conn.commit()
	conn.close()

if __name__ == "__main__":
	setup_database()
