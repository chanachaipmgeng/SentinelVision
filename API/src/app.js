const express = require('express');
const cors = require('cors');
const { connectDB } = require('./utils/db');
const companyRoutes = require('./routes/companyRoutes');
const userRoutes = require('./routes/userRoutes');
const authRoutes = require('./routes/authRoutes');
const positionRoutes = require('./routes/positionRoutes');
const departmentRoutes = require('./routes/departmentRoutes');
const employeeRoutes = require('./routes/employeeRoutes');
const app = express();

app.use(cors({
    origin: 'http://localhost:4200', // Allow only this origin
    methods: ['GET', 'POST', 'PUT', 'DELETE'], // Allow only these HTTP methods
    allowedHeaders: ['Content-Type', 'Authorization'] // Allow only these headers
}));
app.use(express.json());
app.use('/api/member', userRoutes);
app.use('/api/company', companyRoutes);
app.use('/api/position', positionRoutes);
app.use('/api/department', departmentRoutes);
app.use('/api/company-employees', employeeRoutes);
app.use('/api/auth', authRoutes);


// เรียกใช้การเชื่อมต่อกับ PostgreSQL
connectDB();

module.exports = app;