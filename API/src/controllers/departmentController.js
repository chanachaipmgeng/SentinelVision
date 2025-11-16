const Department = require('../models/department');
const Company = require('../models/company');

// Get all departments
exports.getDepartments = async (req, res) => {
    try {
        const departments = await Department.findAll({
            include: {
                model: Company,
                attributes: ['company_name', 'company_code'], // เลือกแสดงข้อมูลที่ต้องการจาก Company
            },
        });
        res.status(200).json(departments);
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
};

// Get department by ID
exports.getDepartmentByID = async (req, res) => {
    try {
        const department = await Department.findByPk(req.params.id, {
            include: {
                model: Company,
                attributes: ['company_name', 'company_code'], // แสดงข้อมูลที่เกี่ยวข้องกับ Company
            },
        });

        if (department) {
            res.status(200).json(department);
        } else {
            res.status(404).json({ error: 'Department not found' });
        }
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
};

exports.getDepartmentsByCompanyID = async (req, res) => {
    try {
        const { company_id } = req.params;

        // ตรวจสอบว่ามี company_id อยู่หรือไม่
        const company = await Company.findByPk(company_id);
        if (!company) {
            return res.status(404).json({ error: 'Company not found' });
        }

        // ดึงข้อมูล departments ที่เชื่อมโยงกับ company_id
        const departments = await Department.findAll({
            where: { company_id },
            attributes: ['department_id','department_name'], // ดึงเฉพาะ field department_name
        });

        res.status(200).json(departments);
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
};
// Create new department
exports.createDepartment = async (req, res) => {
    try {
        const { department_name, company_id } = req.body;

        // ตรวจสอบว่ามี company_id อยู่หรือไม่
        const company = await Company.findByPk(company_id);
        if (!company) {
            return res.status(404).json({ error: 'Company not found' });
        }

        const newDepartment = await Department.create({
            department_name,
            company_id, // ใช้ company_id เพื่อเชื่อมโยงกับตาราง Company
        });

        res.status(201).json({ actionStatus: 'Success', message: 'Department created successfully!', statusCode: 200, department: newDepartment });
    } catch (err) {
        res.status(400).json({ error: err.message });
    }
};

// Update department
exports.updateDepartment = async (req, res) => {
    try {
        const { id } = req.params;
        const { department_name, company_id } = req.body;

        // Find the department by ID
        const department = await Department.findByPk(id);

        if (department) {
            // ตรวจสอบว่ามี company_id อยู่หรือไม่ถ้าต้องการอัปเดต
            if (company_id) {
                const company = await Company.findByPk(company_id);
                if (!company) {
                    return res.status(404).json({ error: 'Company not found' });
                }
                department.company_id = company_id;
            }

            // Update the department's details
            department.department_name = department_name || department.department_name;
            await department.save();

            res.status(200).json({ actionStatus: 'Success', message: 'Department updated successfully!', statusCode: 200, department: department });
        } else {
            res.status(404).json({ error: 'Department not found' });
        }
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
};

// Delete department
exports.deleteDepartment = async (req, res) => {
    try {
        const { id } = req.params;

        // Find the department by ID
        const department = await Department.findByPk(id);

        if (department) {
            // Delete the department
            await department.destroy();
            res.status(200).json({ actionStatus: 'Success', message: 'Department deleted successfully!', statusCode: 200 });
        } else {
            res.status(404).json({ error: 'Department not found' });
        }
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
};
