const express = require('express');
const departmentController = require('../controllers/departmentController');
const authenticateJWT = require('../middleware/auth');
const upload = require('../middleware/uploadMiddleware');

const router = express.Router();
// router.use(authenticateJWT);
router.get('/', departmentController.getDepartments);
router.get('/:id', departmentController.getDepartmentByID);
router.get('/company/:company_id', departmentController.getDepartmentsByCompanyID);
router.post('/', departmentController.createDepartment);
router.put('/:id', departmentController.updateDepartment);
router.delete('/:id', departmentController.deleteDepartment);


module.exports = router;