const { DataTypes } = require('sequelize');
const sequelize = require('../config/database');

const CompanyEmployee = sequelize.define('CompanyEmployee', {
    company_employee_id: {
        type: DataTypes.UUID,
        defaultValue: DataTypes.UUIDV4,
        primaryKey: true,
    },
    member_id: {
        type: DataTypes.UUID,
        allowNull: false,
        references: {
            model: 'member', // ชี้ไปที่ model Member
            key: 'member_id', // ใช้ member_id เป็น foreign key
        }
    },
    company_id: {
        type: DataTypes.UUID,
        allowNull: false,
        references: {
            model: 'company', // ชี้ไปที่ model Company
            key: 'company_id', // ใช้ company_id เป็น foreign key
        }
    },
    position_id: {
        type: DataTypes.UUID,
        allowNull: false,
        references: {
            model: 'position', // ชี้ไปที่ model Position
            key: 'position_id', // ใช้ position_id เป็น foreign key
        }
    },
    department_id: {
        type: DataTypes.UUID,
        allowNull: false,
        references: {
            model: 'department', // ชี้ไปที่ model Department
            key: 'department_id', // ใช้ department_id เป็น foreign key
        }
    },
    employee_id: {
        type: DataTypes.STRING,
        allowNull: false,
    },
    employment_start_date: {
        type: DataTypes.DATE,
        allowNull: false,
        defaultValue: DataTypes.NOW,
    },
    employment_end_date: {
        type: DataTypes.DATE,
        allowNull: true, // สามารถตั้งค่าให้ null ได้ในกรณีที่ยังทำงานอยู่
    },
    status: {
        type: DataTypes.INTEGER,
        allowNull: false,
        defaultValue: 1, // เช่น Active
    },
    created_at: {
        type: DataTypes.DATE,
        allowNull: false,
        defaultValue: DataTypes.NOW,
    },
    updated_at: {
        type: DataTypes.DATE,
        allowNull: false,
        defaultValue: DataTypes.NOW,
    },
}, {
    tableName: 'company_employee',
    timestamps: false,
    underscored: true,
});

// เชื่อมความสัมพันธ์ระหว่าง models
Member.hasMany(CompanyEmployee, { foreignKey: 'member_id' });
CompanyEmployee.belongsTo(Member, { foreignKey: 'member_id' });

Company.hasMany(CompanyEmployee, { foreignKey: 'company_id' });
CompanyEmployee.belongsTo(Company, { foreignKey: 'company_id' });

Position.hasMany(CompanyEmployee, { foreignKey: 'position_id' });
CompanyEmployee.belongsTo(Position, { foreignKey: 'position_id' });

Department.hasMany(CompanyEmployee, { foreignKey: 'department_id' });
CompanyEmployee.belongsTo(Department, { foreignKey: 'department_id' });

module.exports = CompanyEmployee;