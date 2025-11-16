const express = require('express');
const positionController = require('../controllers/positionController');
const authenticateJWT = require('../middleware/auth');
const upload = require('../middleware/uploadMiddleware');

const router = express.Router();
// router.use(authenticateJWT);
router.get('/', positionController.getPositions);
router.get('/:id', positionController.getPositionByID);
router.get('/company/:company_id', positionController.getPositionsByCompanyID);
router.post('/', positionController.createPosition);
router.put('/:id', positionController.updatePosition);
router.delete('/:id', positionController.deletePosition);


module.exports = router;