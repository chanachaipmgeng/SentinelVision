const multer = require('multer');
const { v4: uuidv4 } = require('uuid');
const path = require('path');

// Set storage options for multer
const storage = multer.diskStorage({
    destination: (req, file, cb) => {
        cb(null, 'uploads/'); // Directory where files will be saved
    },
    filename: (req, file, cb) => {
        const ext = path.extname(file.originalname); // Get the file extension
        const filename = `${uuidv4()}${ext}`; // Generate a UUID and append the file extension
        cb(null, filename); // Save the file with the UUID name
    }
});

// Create the multer instance
const upload = multer({ storage: storage });

module.exports = upload;