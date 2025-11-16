const app = require('./app');
const connectDB = require('./utils/db');

const PORT = 5432 || 5000;

connectDB.connectDB()

app.listen(3000, () => {
  console.log(`Server running on port ${PORT}`);
});