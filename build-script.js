// Copy logout.html template and replace with environment-specific values
const fs = require('fs');
const template = fs.readFileSync('frontend/public/logout.template.html', 'utf8');
const html = template.replace('__VITE_API_URL__', process.env.VITE_API_URL);
fs.writeFileSync('frontend/public/logout.html', html); 