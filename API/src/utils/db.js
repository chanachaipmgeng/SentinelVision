const { Pool } = require('pg');
require('dotenv').config();

const pool = new Pool({
  user: "postgres",
  host: "localhost",
  database: "postgres",
  password: "***REMOVED***",
  port: 5432,
});

const connectDB = async () => {
  try {
    await pool.connect();
    console.log('PostgreSQL connected successfully');
  } catch (error) {
    console.error('PostgreSQL connection error:', error);
    process.exit(1);
  }
};

module.exports = {
  connectDB,
  query: (text, params) => pool.query(text, params),
};