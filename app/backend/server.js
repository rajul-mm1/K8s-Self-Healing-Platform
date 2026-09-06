const express = require('express');
const cors = require('cors');
const { connectDB, mongoose } = require('./db');
const todosRouter = require('./routes/todos');

const app = express();
const PORT = process.env.PORT || 5000;

app.use(cors());
app.use(express.json());

// Liveness/readiness probe target.
// Reports 200 only when the MongoDB connection is actually established,
// so Kubernetes will not route traffic to a backend pod that can't reach its DB.
app.get('/health', (req, res) => {
  const dbState = mongoose.connection.readyState; // 1 = connected
  if (dbState === 1) {
    return res.status(200).json({ status: 'ok', db: 'connected' });
  }
  return res.status(503).json({ status: 'degraded', db: 'disconnected' });
});

app.use('/api/todos', todosRouter);

// Used only by scripts/crashloop.sh to deliberately crash the process
// and demonstrate CrashLoopBackOff remediation.
app.post('/api/debug/crash', (req, res) => {
  res.status(200).json({ status: 'crashing' });
  setTimeout(() => process.exit(1), 100);
});

async function start() {
  try {
    await connectDB();
    app.listen(PORT, () => console.log(`[server] listening on ${PORT}`));
  } catch (err) {
    console.error('[server] failed to start:', err.message);
    process.exit(1);
  }
}

start();
