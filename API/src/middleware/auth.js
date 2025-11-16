// middleware/auth.js

const jwt = require('jsonwebtoken');
const secretKey = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJtZW1iZXJfaWQiOiJkZjE0OWM4Ni02Njc0LTRmODItYTE0Yi05OWFjNmZjYjJjNjIiLCJ1c2VybmFtZSI6ImNoYW5hY2hhaSIsImlhdCI6MTcyNDYzNDI0NSwiZXhwIjoxNzI0NjM3ODQ1fQ.bxa0LGelFhlGGb8PSgNd1oq-QZKqaNKbLA6oMuzEEeo'; // Replace with your own secret key

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