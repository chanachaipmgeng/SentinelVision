const Position = require('../models/position');
const Company = require('../models/company');

// Get all positions
exports.getPositions = async (req, res) => {
    try {
        const positions = await Position.findAll({
            include: {
                model: Company,
                attributes: ['company_name', 'company_code'], // เลือกแสดงข้อมูลที่ต้องการจาก Company
            },
        });
        res.status(200).json(positions);
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
};

// Get position by ID
exports.getPositionByID = async (req, res) => {
    try {
        const position = await Position.findByPk(req.params.id, {
            include: {
                model: Company,
                attributes: ['company_name', 'company_code'], // แสดงข้อมูลที่เกี่ยวข้องกับ Company
            },
        });

        if (position) {
            res.status(200).json(position);
        } else {
            res.status(404).json({ error: 'Position not found' });
        }
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
};

exports.getPositionsByCompanyID = async (req, res) => {
    try {
        const { company_id } = req.params;

        // ตรวจสอบว่ามี company_id อยู่หรือไม่
        const company = await Company.findByPk(company_id);
        if (!company) {
            return res.status(404).json({ error: 'Company not found' });
        }

        // ดึงข้อมูล positions ที่เชื่อมโยงกับ company_id
        const positions = await Position.findAll({
            where: { company_id },
            attributes: ['position_id','position_name'], // ดึงเฉพาะ field position_name
        });

        res.status(200).json(positions);
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
};
// Create new position
exports.createPosition = async (req, res) => {
    try {
        const { position_name, company_id } = req.body;

        // ตรวจสอบว่ามี company_id อยู่หรือไม่
        const company = await Company.findByPk(company_id);
        if (!company) {
            return res.status(404).json({ error: 'Company not found' });
        }

        const newPosition = await Position.create({
            position_name,
            company_id, // ใช้ company_id เพื่อเชื่อมโยงกับตาราง Company
        });

        res.status(201).json({ actionStatus: 'Success', message: 'Position created successfully!', statusCode: 200, position: newPosition });
    } catch (err) {
        res.status(400).json({ error: err.message });
    }
};

// Update position
exports.updatePosition = async (req, res) => {
    try {
        const { id } = req.params;
        const { position_name, company_id } = req.body;

        // Find the position by ID
        const position = await Position.findByPk(id);

        if (position) {
            // ตรวจสอบว่ามี company_id อยู่หรือไม่ถ้าต้องการอัปเดต
            if (company_id) {
                const company = await Company.findByPk(company_id);
                if (!company) {
                    return res.status(404).json({ error: 'Company not found' });
                }
                position.company_id = company_id;
            }

            // Update the position's details
            position.position_name = position_name || position.position_name;
            await position.save();

            res.status(200).json({ actionStatus: 'Success', message: 'Position updated successfully!', statusCode: 200, position: position });
        } else {
            res.status(404).json({ error: 'Position not found' });
        }
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
};

// Delete position
exports.deletePosition = async (req, res) => {
    try {
        const { id } = req.params;

        // Find the position by ID
        const position = await Position.findByPk(id);

        if (position) {
            // Delete the position
            await position.destroy();
            res.status(200).json({ actionStatus: 'Success', message: 'Position deleted successfully!', statusCode: 200 });
        } else {
            res.status(404).json({ error: 'Position not found' });
        }
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
};
