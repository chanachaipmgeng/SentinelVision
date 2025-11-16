const express = require('express');
const companyController = require('../controllers/companyController');
const authenticateJWT = require('../middleware/auth');
const upload = require('../middleware/uploadMiddleware');

const router = express.Router();
// router.use(authenticateJWT);
router.get('/', companyController.getCompanys);
router.get('/:id', companyController.getCompanysByID);
router.put('/:id',upload.single('image'),companyController.updateCompany);
router.post('/', companyController.createCompany);
router.delete('/:id', companyController.deleteCompany);

module.exports = router;