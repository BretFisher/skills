const express = require("express");
const { createClient } = require("redis");

// Redis runs as the "redis" Service in the same namespace.
const redis = createClient({
  socket: { host: process.env.REDIS_HOST || "redis", port: Number(process.env.REDIS_PORT || 6379) },
});

const app = express();

app.get("/healthz", async (_req, res) => {
  res.status(redis.isReady ? 200 : 503).send(redis.isReady ? "ok" : "starting");
});

app.get("/", async (_req, res) => {
  const hits = await redis.incr("hits");
  res.send(`hits: ${hits}`);
});

redis.connect().then(() => app.listen(3000));
