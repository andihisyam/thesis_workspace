const { spawn } = require("node:child_process");
const path = require("node:path");

const host = process.env.HOST || "0.0.0.0";
const port = process.env.PORT || "1234";
const persistence = process.env.YPERSISTENCE || path.join(__dirname, "data");

const command = process.platform === "win32" ? "npx.cmd" : "npx";
const child = spawn(command, ["y-websocket"], {
  stdio: "inherit",
  env: {
    ...process.env,
    HOST: host,
    PORT: port,
    YPERSISTENCE: persistence,
  },
});

child.on("exit", (code) => process.exit(code ?? 0));
child.on("error", (error) => {
  console.error(error);
  process.exit(1);
});
