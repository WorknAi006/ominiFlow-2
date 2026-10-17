import net from "node:net";
import { spawn } from "node:child_process";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const nextBin = require.resolve("next/dist/bin/next");

const command = process.argv[2] || "dev";
const extraArgs = process.argv.slice(3);

function isPortAvailable(port) {
  return new Promise((resolve) => {
    const server = net.createServer();
    server.unref();
    server.once("error", () => resolve(false));
    server.listen({ port }, () => {
      server.close(() => resolve(true));
    });
  });
}

async function findAvailablePort(startPort, maxAttempts = 50) {
  let port = startPort;
  for (let i = 0; i < maxAttempts; i++) {
    if (await isPortAvailable(port)) {
      return port;
    }
    console.log(`[Omniflow Admin] Port ${port} is currently in use, checking port ${port + 1}...`);
    port++;
  }
  throw new Error(`Could not find an available port starting from ${startPort} (checked ${maxAttempts} ports)`);
}

async function main() {
  const preferredPort = parseInt(process.env.PORT || "3001", 10);
  const port = await findAvailablePort(preferredPort);

  if (port !== preferredPort) {
    console.log(`[Omniflow Admin] Note: Default port ${preferredPort} was busy -> Automatically switched to port ${port}`);
  }
  console.log(`[Omniflow Admin] Starting Next.js (${command}) on http://localhost:${port}\n`);

  process.env.PORT = String(port);

  const child = spawn(process.execPath, [nextBin, command, "-p", String(port), ...extraArgs], {
    stdio: "inherit",
    env: { ...process.env, PORT: String(port) },
  });

  const forwardSignal = (sig) => {
    if (child && !child.killed) {
      child.kill(sig);
    }
  };

  process.on("SIGINT", () => forwardSignal("SIGINT"));
  process.on("SIGTERM", () => forwardSignal("SIGTERM"));

  child.on("exit", (code, signal) => {
    process.exit(code ?? (signal ? 1 : 0));
  });
}

main().catch((err) => {
  console.error("[Omniflow Admin] Error starting server:", err);
  process.exit(1);
});
