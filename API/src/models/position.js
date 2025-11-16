const { DataTypes } = require('sequelize');
const sequelize = require('../config/database');
const Company = require('./company'); // อ้างอิงถึง model Company ที่สร้างไว้ก่อนหน้านี้

const Position = sequelize.define('Position', {
    position_id: {
        type: DataTypes.UUID,
        defaultValue: DataTypes.UUIDV4,
        primaryKey: true,
    },
    position_name: {
        type: DataTypes.STRING,
        allowNull: false,
    },
    company_id: {
        type: DataTypes.UUID,
        allowNull: false,
        references: {
            model: Company, // ชี้ไปที่ model Company
            key: 'company_id', // ใช้ company_id เป็น foreign key
        }
    }
}, {
    tableName: 'position',
    timestamps: false,
    underscored: true,
});

// สร้าง association ระหว่าง Position และ Company
Company.hasMany(Position, { foreignKey: 'company_id', onDelete: 'CASCADE' });
Position.belongsTo(Company, { foreignKey: 'company_id' });

// (async () => {
//     try {
//         await sequelize.authenticate();
//         console.log('Connection has been established successfully.');

//         // Sync models (สร้างตารางถ้ายังไม่มี)
//         await sequelize.sync({ force: true }); // `force: true` จะ drop ตารางแล้วสร้างใหม่

//         // Insert sample data in Company
//         const company1 = await Company.create({
//             company_name: 'Example Company 1',
//             company_code: 'EX001',
//             address: '123 Example Street, City, Country',
//             latitude: '12.345678',
//             longitude: '98.765432',
//         });

//         // Insert sample data in Position
//         await Position.create({
//             position_name: 'Manager',
//             company_id: company1.company_id, // เชื่อมโยงกับ Company ผ่าน company_id
//         });

//         await Position.create({
//             position_name: 'Engineer',
//             company_id: company1.company_id, // เชื่อมโยงกับ Company ผ่าน company_id
//         });

//         console.log('Sample data for Company and Position inserted successfully!');

//     } catch (error) {
//         console.error('Error inserting sample data:', error);
//     } finally {
//         await sequelize.close();
//     }
// })();

module.exports = Position;