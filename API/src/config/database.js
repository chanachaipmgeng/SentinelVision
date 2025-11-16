const { Sequelize } = require('sequelize');

const sequelize = new Sequelize('postgres', 'postgres', '***REMOVED***', {
    host: 'localhost',
    dialect: 'postgres'
});

module.exports = sequelize;