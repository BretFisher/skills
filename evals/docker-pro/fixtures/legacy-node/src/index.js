// Eval fixture for the docker-pro skill: the app behind a legacy Dockerfile.
const express = require("express");

const app = express();
app.get("/", (_req, res) => res.send("catalog"));
app.listen(3000, () => console.log("catalog-web on 3000"));
