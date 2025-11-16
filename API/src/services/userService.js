const db = require('../utils/db');

exports.getAllUsers = async () => {
  const result = await db.query('SELECT * FROM member');
  return result.rows;
};