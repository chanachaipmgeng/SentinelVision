const CompanyEmployee = require('../models/company_employee');
const Member = require('../models/member');
const Company = require('../models/company');
const Position = require('../models/position');
const Department = require('../models/department');

exports.getCompanyEmployees = async (req, res) => {
  try {
    const companyEmployees = await CompanyEmployee.findAll({
      include: [
        { model: Member, attributes: ['username', 'email'] },
        { model: Company, attributes: ['company_name'] },
        { model: Position, attributes: ['position_name'] },
        { model: Department, attributes: ['department_name'] }
      ]
    });
    res.status(200).json(companyEmployees);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
};

exports.getCompanyEmployeeByID = async (req, res) => {
  try {
    const companyEmployee = await CompanyEmployee.findByPk(req.params.id, {
      include: [
        { model: Member, attributes: ['username', 'email'] },
        { model: Company, attributes: ['company_name'] },
        { model: Position, attributes: ['position_name'] },
        { model: Department, attributes: ['department_name'] }
      ]
    });
    if (companyEmployee) {
      res.status(200).json(companyEmployee);
    } else {
      res.status(404).json({ error: 'Company Employee not found' });
    }
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
};

exports.createCompanyEmployee = async (req, res) => {
  try {
    const { member_id, company_id, position_id, department_id, employment_start_date, employment_end_date, status } = req.body;
    const newCompanyEmployee = await CompanyEmployee.create({
      member_id,
      company_id,
      position_id,
      department_id,
      employment_start_date,
      employment_end_date,
      status
    });
    res.status(201).json({ actionStatus: 'Success', message: 'Create Success!!', statusCode: 200, companyEmployee: newCompanyEmployee });
  } catch (err) {
    res.status(400).json({ error: err.message });
  }
};

exports.updateCompanyEmployee = async (req, res) => {
  try {
    const { id } = req.params;
    const { position_id, department_id, employment_end_date, status } = req.body;

    const companyEmployee = await CompanyEmployee.findByPk(id);

    if (companyEmployee) {
      companyEmployee.position_id = position_id || companyEmployee.position_id;
      companyEmployee.department_id = department_id || companyEmployee.department_id;
      companyEmployee.employment_end_date = employment_end_date || companyEmployee.employment_end_date;
      companyEmployee.status = status || companyEmployee.status;
      companyEmployee.updated_at = new Date();

      await companyEmployee.save();

      res.status(200).json({ actionStatus: 'Success', message: 'Update Success!!', statusCode: 200, companyEmployee });
    } else {
      res.status(404).json({ error: 'Company Employee not found' });
    }
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
};

exports.deleteCompanyEmployee = async (req, res) => {
  try {
    const { id } = req.params;

    const companyEmployee = await CompanyEmployee.findByPk(id);

    if (companyEmployee) {
      await companyEmployee.destroy();
      res.status(200).json({ actionStatus: 'Success', message: 'Delete Success!!', statusCode: 200 });
    } else {
      res.status(404).json({ error: 'Company Employee not found' });
    }
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
};
