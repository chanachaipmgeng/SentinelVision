const { DataTypes } = require('sequelize');
const sequelize = require('../config/database');
const Company = require('./company'); // อ้างอิงถึง model Company ที่สร้างไว้ก่อนหน้านี้

const Department = sequelize.define('Department', {
    department_id: {
        type: DataTypes.UUID,
        defaultValue: DataTypes.UUIDV4,
        primaryKey: true,
    },
    department_name: {
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
    tableName: 'department',
    timestamps: false,
    underscored: true,
});

// สร้าง association ระหว่าง Department และ Company
Company.hasMany(Department, { foreignKey: 'company_id', onDelete: 'CASCADE' });
Department.belongsTo(Company, { foreignKey: 'company_id' });

// (async () => {
//     try {
//         await sequelize.authenticate();
//         console.log('Connection has been established successfully.');

//         // Sync models (สร้างตารางถ้ายังไม่มี)
//         await sequelize.sync({ force: true }); // `force: true` จะ drop ตารางแล้วสร้างใหม่

//         // Insert sample data in Company

//         // Insert sample data in Department
//         await Department.create({
//             department_name: 'Manager',
//             company_id: '94c2558c-35c3-4509-b313-624e3fa06295', // เชื่อมโยงกับ Company ผ่าน company_id
//         });

//         await Department.create({
//             department_name: 'Engineer',
//             company_id: '94c2558c-35c3-4509-b313-624e3fa06295', // เชื่อมโยงกับ Company ผ่าน company_id
//         });

//         console.log('Sample data for Company and Department inserted successfully!');

//     } catch (error) {
//         console.error('Error inserting sample data:', error);
//     } finally {
//         await sequelize.close();
//     }
// })();

module.exports = Department;