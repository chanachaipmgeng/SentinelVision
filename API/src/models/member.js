const { DataTypes } = require('sequelize');
const sequelize = require('../config/database');
const bcrypt = require('bcryptjs');

const Member = sequelize.define('Member', {
    member_id: {
        type: DataTypes.UUID,
        defaultValue: DataTypes.UUIDV4,
        primaryKey: true,
    },
    username: {
        type: DataTypes.STRING,
        allowNull: false,
        unique: true,
    },
    password_hash: {
        type: DataTypes.STRING,
        allowNull: false,
    },
    email: {
        type: DataTypes.STRING,
        allowNull: false,
        unique: true,
    },
    phone_number: {
        type: DataTypes.STRING,
        allowNull: true,
    },
    role: {
        type: DataTypes.INTEGER, // เปลี่ยนจาก NUMBER เป็น INTEGER สำหรับ Sequelize
        allowNull: false,
        defaultValue: 1,
    },
    status: {
        type: DataTypes.INTEGER, // เปลี่ยนจาก NUMBER เป็น INTEGER สำหรับ Sequelize
        allowNull: false,
        defaultValue: 1,
    },
    picture: {
        type: DataTypes.UUID,
        defaultValue: DataTypes.UUIDV4,
    },
    face_embedding: {
        type: DataTypes.TEXT, // เก็บ Face Embedding เป็น TEXT
        allowNull: true,      // สามารถตั้งค่าเป็น `false` ถ้าจำเป็นต้องใช้ใบหน้าเสมอ
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
    tableName: 'member',
    timestamps: false,
    underscored: true,
});

// Add a method to hash the password before saving the user
Member.beforeCreate(async (member) => {
    member.password_hash = await bcrypt.hash(member.password_hash, 10);
});

module.exports = Member;