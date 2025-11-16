const express = require('express');
const userController = require('../controllers/userController');
const authenticateJWT = require('../middleware/auth');
const upload = require('../middleware/uploadMiddleware');

const router = express.Router();
// router.use(authenticateJWT);
router.get('/', userController.getUsers);
router.get('/:id', userController.getUsersByID);
router.put('/:id',upload.single('image'),userController.updateUser);
router.post('/', userController.createUser);
router.delete('/:id', userController.deleteUser);
router.post('/:id/face', upload.single('faceImage'), userController.addFace);
router.post('/:id/check-face', upload.single('faceImage'), userController.checkFace);

module.exports = router;