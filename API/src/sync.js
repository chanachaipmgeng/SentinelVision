// sync.js

const sequelize = require('./config/database');
const Member = require('./models/member');



sequelize.sync({ force: false })
    .then(() => {
        console.log('Database & tables created!');
    })
    .catch(err => console.error('Unable to create the database:', err));