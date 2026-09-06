const mongoose = require('mongoose');

const MONGO_URI = process.env.MONGO_URI || 'mongodb://mongodb:27017/tododb';

async function connectDB() {
  mongoose.set('strictQuery', true);
  await mongoose.connect(MONGO_URI, {
    serverSelectionTimeoutMS: 5000,
  });
  console.log('[db] connected to MongoDB');
}

module.exports = { connectDB, mongoose };
