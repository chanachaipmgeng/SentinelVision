const CompanyService = require('../services/userService');
const Company = require('../models/company');
const bcrypt = require('bcryptjs');
const saltRounds = 10; // Number of salt rounds for bcrypt

exports.getCompanys = async (req, res) => {
  try {
    const companys = await Company.findAll();
    res.status(200).json(companys);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
};

exports.getCompanysByID = async (req, res) => {
  try {
    const company = await Company.findByPk(req.params.id);
    if (company) {
      res.status(200).json(company);
    } else {
      res.status(404).json({ error: 'Company not found' });
    }
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
};



exports.createCompany = async (req, res) => {
  try {
    const { company_name, company_code, address, latitude , longitude } = req.body;
    const newCompany = await Company.create({
      company_name,
      company_code,
      address,
      latitude , longitude
    });
    res.status(201).json({ actionStatus: 'Success', message: 'Create Success!!', statusCode: 200, company: newCompany });
  } catch (err) {
    res.status(400).json({ error: err.message });
  }
};

exports.updateCompany = async (req, res) => {
  try {
    const { id } = req.params;
    const { company_name, company_code, address, latitude , longitude } = req.body;

    // Find the company by ID
    const company = await Company.findByPk(id);

    if (company) {
      // Update the company's details
      company.company_name = company_name || company.company_name;
      if (company_code) {
        const hashedPassword = await bcrypt.hash(company_code, saltRounds);
        company.company_code = hashedPassword;
      }
      company.address = address || company.address;
      company.latitude = latitude || company.latitude;
      company.longitude = longitude || company.longitude;
      company.updated_at = new Date(); // Update the timestamp

      // Save the updated company
      await company.save();

      res.status(200).json({ actionStatus: 'Success', message: 'Update Success!!', statusCode: 200, company: company });
    } else {
      res.status(404).json({ error: 'Company not found' });
    }
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
};

exports.deleteCompany = async (req, res) => {
  try {
    const { id } = req.params;

    // Find the company by ID
    const company = await Company.findByPk(id);

    if (company) {
      // Delete the company
      await company.destroy();
      res.status(200).json({ actionStatus: 'Success', message: 'Delete Success!!', statusCode: 200 }); // 204 No Content
    } else {
      res.status(404).json({ error: 'Company not found' });
    }
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
};