// middleware/auth.js

const jwt = require('jsonwebtoken');
const secretKey = '***REMOVED***'; // Replace with your own secret key

const authenticateJWT = (req, res, next) => {
    try {
        const token = req.header('Authorization').replace('Bearer ', '');

        if (!token) {
            return res.status(401).json({ error: 'Access denied' });
        }
        const decoded = jwt.verify(token, secretKey);
        req.member = decoded; // Add the decoded token to the request
        next();
    } catch (err) {
        res.status(400).json({ error: 'Invalid token' });
    }
};

module.exports = authenticateJWT;