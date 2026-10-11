// Eval fixture for the docker-pro skill: a minimal Express app.
const express = require("express");

const app = express();
const port = process.env.PORT || 3000;

app.get("/healthz", (_req, res) => res.send("ok"));
app.get("/orders", (_req, res) => res.json([]));

app.listen(port, () => console.log(`orders-api listening on ${port}`));
