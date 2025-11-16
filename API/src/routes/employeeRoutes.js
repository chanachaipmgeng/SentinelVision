const express = require('express');
const router = express.Router();
const companyEmployeeController = require('../controllers/companyEmployeeController');

// Route for getting all company employees
router.get('/', companyEmployeeController.getCompanyEmployees);

// Route for getting a company employee by ID
router.get('/:id', companyEmployeeController.getCompanyEmployeeByID);

// Route for creating a new company employee
router.post('/', companyEmployeeController.createCompanyEmployee);

// Route for updating a company employee
router.put('/:id', companyEmployeeController.updateCompanyEmployee);

// Route for deleting a company employee
router.delete('/:id', companyEmployeeController.deleteCompanyEmployee);

module.exports = router;