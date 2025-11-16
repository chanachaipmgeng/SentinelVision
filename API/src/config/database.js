const { Sequelize } = require('sequelize');

const sequelize = new Sequelize('postgres', 'postgres', 'qwer1234', {
    host: 'localhost',
    dialect: 'postgres'
});

module.exports = sequelize;