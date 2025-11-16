(async () => {
    try {
        await sequelize.authenticate();
        console.log('Connection has been established successfully.');

        // Insert sample data
        await Company.create({
            company_name: 'Example Company 1',
            company_code: 'EX001',
            address: '123 Example Street, City, Country',
            latitude: '12.345678',
            longitude: '98.765432',
            picture: DataTypes.UUIDV4(), // Or provide your own UUID
        });

        await Company.create({
            company_name: 'Example Company 2',
            company_code: 'EX002',
            address: '456 Another Street, City, Country',
            latitude: '23.456789',
            longitude: '87.654321',
            picture: DataTypes.UUIDV4(), // Or provide your own UUID
        });

        console.log('Sample data inserted successfully!');

    } catch (error) {
        console.error('Error inserting sample data:', error);
    } finally {
        await sequelize.close();
    }
})();